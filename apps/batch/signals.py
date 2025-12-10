"""
Signal handlers for batch lifecycle management.

This module contains signal handlers that manage:
1. Automatic batch status transitions (existing)
2. Growth assimilation recompute triggers (Issue #112 Phase 4)

Signal Flow:
    Event (GrowthSample, TransferAction, etc.) 
    → Signal handler (lightweight, just enqueues task)
    → Celery task (heavy computation in background)
    → ActualDailyAssignmentState updated
    
Test Data Generation:
    Set SKIP_CELERY_SIGNALS=1 environment variable to disable Celery
    task enqueueing during bulk data generation (prevents Redis connection spam).
"""
import logging
import os
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.batch.models import (
    BatchContainerAssignment,
    GrowthSample,
    TransferAction,
    MortalityEvent,
)

logger = logging.getLogger(__name__)


def _should_skip_celery_signals():
    """
    Check if Celery signals should be skipped.
    
    Supports both environment variable (for scripts) and Django settings (for tests).
    This function is called each time to support @override_settings in tests.
    
    Returns:
        bool: True if signals should be skipped
    """
    # Check environment variable first (for data generation scripts)
    if os.environ.get('SKIP_CELERY_SIGNALS') == '1':
        return True
    
    # Check Django settings (for @override_settings in tests)
    from django.conf import settings
    return getattr(settings, 'SKIP_CELERY_SIGNALS', False) == '1'


# Legacy constant for backwards compatibility (use _should_skip_celery_signals() instead)
SKIP_CELERY_SIGNALS = os.environ.get('SKIP_CELERY_SIGNALS') == '1'


@receiver(post_save, sender=BatchContainerAssignment)
def check_batch_completion_on_assignment_change(sender, instance, **kwargs):
    """
    Automatically mark a batch as COMPLETED when all its container
    assignments are inactive.

    This signal is triggered whenever a BatchContainerAssignment is saved.
    It checks if:
    1. The assignment was just deactivated (is_active=False)
    2. All other assignments for the same batch are also inactive
    3. If both conditions are true, sets batch status to COMPLETED and
       sets actual_end_date

    Args:
        sender: The model class (BatchContainerAssignment)
        instance: The saved BatchContainerAssignment instance
        **kwargs: Additional signal arguments

    Business Logic:
        - When the LAST active assignment for a batch is deactivated
        - Set batch.actual_end_date = latest departure_date from all
          assignments
        - Set batch.status = 'COMPLETED'
        - Ensures batches are automatically marked complete after full
          harvest

    Examples:
        - Batch has 3 assignments, all harvested → status changes to
          COMPLETED
        - Batch has 2 assignments, only 1 harvested → status remains
          ACTIVE
        - Batch manually terminated → status can still be set to
          TERMINATED manually
    """
    # Only proceed if this assignment was just deactivated
    if not instance.is_active:
        batch = instance.batch

        # Skip if batch is already completed or terminated
        if batch.status in ['COMPLETED', 'TERMINATED']:
            logger.debug(
                f"Batch {batch.batch_number} already {batch.status}, "
                f"skipping completion check"
            )
            return

        # Check if any assignments are still active for this batch
        active = batch.batch_assignments.filter(is_active=True).exists()

        if not active:
            # All assignments are inactive - batch is complete!
            logger.info(
                f"All assignments for batch {batch.batch_number} are "
                f"inactive. Marking batch as COMPLETED."
            )

            # Get the latest departure date as the actual end date
            # This represents when the last fish left the last container
            latest_departure = batch.batch_assignments.aggregate(
                Max('departure_date')
            )['departure_date__max']

            # If departure_date wasn't set, fall back to updated_at
            if not latest_departure:
                logger.warning(
                    f"No departure_date found for batch "
                    f"{batch.batch_number} assignments. "
                    f"Using latest updated_at as fallback."
                )
                latest_update = batch.batch_assignments.aggregate(
                    Max('updated_at')
                )['updated_at__max']
                if latest_update:
                    latest_departure = latest_update.date()
                else:
                    latest_departure = instance.updated_at.date()

            # Update batch status and end date
            batch.actual_end_date = latest_departure
            batch.status = 'COMPLETED'
            batch.save(update_fields=['actual_end_date', 'status'])

            logger.info(
                f"✓ Batch {batch.batch_number} marked as COMPLETED with "
                f"actual_end_date={latest_departure}"
            )


# ------------------------------------------------------------------
# Growth Assimilation Recompute Signals (Issue #112 Phase 4)
# ------------------------------------------------------------------

@receiver(post_save, sender=GrowthSample)
def on_growth_sample_saved(sender, instance, created, **kwargs):
    """
    Trigger growth assimilation recompute when growth sample is created.
    
    Growth samples are anchors - they reset the weight calculation and affect
    interpolation on both sides (before and after the sample date).
    
    Window: [sample_date - 2, sample_date + 2]
    
    Rationale:
        - 2 days before: Re-interpolate leading up to anchor
        - 2 days after: Re-interpolate from anchor forward
    
    Args:
        sender: GrowthSample model class
        instance: The saved GrowthSample instance
        created: True if new instance, False if update
        **kwargs: Additional signal arguments
    """
    # Skip during test data generation (env var check)
    if _should_skip_celery_signals():
        return
    
    if not created:
        # Only trigger on new samples, not updates
        logger.debug(f"Skipping recompute for GrowthSample update (id={instance.id})")
        return
    
    try:
        # Import here to avoid circular imports
        from apps.batch.tasks import enqueue_recompute_with_deduplication
        
        assignment = instance.assignment
        sample_date = instance.sample_date
        
        logger.debug(
            f"Growth sample created for assignment {assignment.id} "
            f"(batch={assignment.batch.batch_number}, date={sample_date}, "
            f"avg_weight={instance.avg_weight_g}g)"
        )
        
        # Enqueue recompute task (with deduplication)
        task_id = enqueue_recompute_with_deduplication(
            assignment_id=assignment.id,
            trigger_date=sample_date,
            window_days=2
        )
        
        if task_id:
            logger.info(
                f"📋 Enqueued growth assimilation task {task_id} for "
                f"assignment {assignment.id} after growth sample "
                f"(window: {sample_date} ± 2 days)"
            )
    except Exception as e:
        # Gracefully handle Celery/Redis unavailability (e.g., in CI tests)
        logger.warning(
            f"Could not enqueue growth assimilation task for assignment "
            f"{instance.assignment.id}: {e}. This is normal in test/CI environments "
            f"without Redis/Celery running."
        )


@receiver(post_save, sender=TransferAction)
def on_transfer_completed(sender, instance, created, **kwargs):
    """
    Trigger recompute when transfer with measured weight completes.
    
    TransferActions with measured weights are anchors. Only trigger if:
    1. Transfer has measured_avg_weight_g set
    2. Transfer status is COMPLETED
    
    Window: [execution_date - 2, execution_date + 2]
    
    Note: Field name is 'actual_execution_date' not 'execution_date' per
    handover doc field name gotchas.
    
    Args:
        sender: TransferAction model class
        instance: The saved TransferAction instance
        created: True if new instance, False if update
        **kwargs: Additional signal arguments
    """
    # Skip during test data generation (env var check)
    if _should_skip_celery_signals():
        return
    
    # Check if this transfer has measured weight
    if not instance.measured_avg_weight_g:
        logger.debug(
            f"Skipping recompute for TransferAction {instance.id} "
            f"(no measured weight)"
        )
        return
    
    # Check if transfer is completed
    if instance.status != 'COMPLETED':
        logger.debug(
            f"Skipping recompute for TransferAction {instance.id} "
            f"(status={instance.status}, not COMPLETED)"
        )
        return
    
    try:
        # Import here to avoid circular imports
        from apps.batch.tasks import enqueue_recompute_with_deduplication
        
        # Get source assignment (where fish came from)
        source_assignment = instance.source_assignment
        if not source_assignment:
            logger.warning(
                f"TransferAction {instance.id} has no source_assignment, "
                f"skipping recompute"
            )
            return
        
        # Use actual_execution_date (field name gotcha from handover)
        execution_date = instance.actual_execution_date
        if not execution_date:
            logger.warning(
                f"TransferAction {instance.id} has no actual_execution_date, "
                f"skipping recompute"
            )
            return
        
        logger.debug(
            f"Transfer completed with measured weight for assignment "
            f"{source_assignment.id} (batch={source_assignment.batch.batch_number}, "
            f"date={execution_date}, avg_weight={instance.measured_avg_weight_g}g)"
        )
        
        # Enqueue recompute task (with deduplication)
        task_id = enqueue_recompute_with_deduplication(
            assignment_id=source_assignment.id,
            trigger_date=execution_date,
            window_days=2
        )
        
        if task_id:
            logger.info(
                f"📋 Enqueued growth assimilation task {task_id} for "
                f"assignment {source_assignment.id} after transfer "
                f"(window: {execution_date} ± 2 days)"
            )
    except Exception as e:
        # Gracefully handle Celery/Redis unavailability
        logger.warning(
            f"Could not enqueue growth assimilation task after transfer "
            f"{instance.id}: {e}. Normal in test/CI without Redis/Celery."
        )


@receiver(post_save, sender=MortalityEvent)
def on_mortality_event(sender, instance, created, **kwargs):
    """
    Trigger batch-level recompute for mortality event.
    
    MortalityEvent is batch-level (not assignment-level per handover doc).
    This affects all assignments, so we trigger a batch-level recompute.
    
    Window: [event_date - 1, event_date + 1]
    
    Rationale:
        - Smaller window than growth samples (mortality is incremental)
        - Only need to update population counts, not weights
    
    Args:
        sender: MortalityEvent model class
        instance: The saved MortalityEvent instance
        created: True if new instance, False if update
        **kwargs: Additional signal arguments
    """
    # Skip during test data generation (env var check)
    if _should_skip_celery_signals():
        return
    
    if not created:
        # Only trigger on new events, not updates
        logger.debug(f"Skipping recompute for MortalityEvent update (id={instance.id})")
        return
    
    try:
        # Import here to avoid circular imports
        from apps.batch.tasks import enqueue_batch_recompute
        
        batch = instance.batch
        event_date = instance.event_date
        
        logger.debug(
            f"Mortality event created for batch {batch.batch_number} "
            f"(date={event_date}, count={instance.count})"
        )
        
        # Enqueue batch-level recompute task (no deduplication needed)
        task_id = enqueue_batch_recompute(
            batch_id=batch.id,
            trigger_date=event_date,
            window_days=1
        )
        
        logger.info(
            f"📋 Enqueued batch-level growth assimilation task {task_id} for "
            f"batch {batch.batch_number} after mortality event "
            f"(window: {event_date} ± 1 day)"
        )
    except Exception as e:
        # Gracefully handle Celery/Redis unavailability
        logger.warning(
            f"Could not enqueue batch recompute task after mortality event "
            f"{instance.id}: {e}. Normal in test/CI without Redis/Celery."
        )


# ------------------------------------------------------------------
# PlannedActivity Completion Signal (Issue #112 Phase 8)
# ------------------------------------------------------------------

def on_planned_activity_completed(sender, instance, **kwargs):
    """
    Trigger growth assimilation recompute when PlannedActivity is completed.
    
    When a PlannedActivity with activity_type in (TRANSFER, VACCINATION, SAMPLING)
    is marked as COMPLETED, this signal triggers a recompute to anchor the
    daily state series with any measured weights from the completed activity.
    
    Window: [completed_at.date() - 2, completed_at.date() + 2]
    
    Bidirectional flow:
        - Forward: Daily state calculations trigger PlannedActivity creation (via templates)
        - Backward: Completed PlannedActivities anchor daily state series (this signal)
    
    Note: Only triggers when status CHANGES to COMPLETED, not on subsequent saves
    of an already-completed activity. Uses _original_status tracking from model.
    
    Args:
        sender: PlannedActivity model class
        instance: The saved PlannedActivity instance
        **kwargs: Additional signal arguments (created, etc.)
    """
    # Skip during test data generation (env var check)
    if _should_skip_celery_signals():
        return
    
    # Only trigger when status CHANGES to COMPLETED (not on every save of completed activity)
    # This prevents unnecessary recomputes when editing notes or other fields
    original_status = getattr(instance, '_original_status', None)
    status_just_changed_to_completed = (
        instance.status == 'COMPLETED' and 
        original_status is not None and 
        original_status != 'COMPLETED'
    )
    
    # Also trigger for newly created activities that are immediately COMPLETED
    created = kwargs.get('created', False)
    newly_created_as_completed = created and instance.status == 'COMPLETED'
    
    if not (status_just_changed_to_completed or newly_created_as_completed):
        logger.debug(
            f"Skipping recompute for PlannedActivity {instance.id} "
            f"(status={instance.status}, original={original_status}, created={created})"
        )
        return
    
    # Only trigger for activity types that can have measured weights
    ANCHOR_ACTIVITY_TYPES = ['TRANSFER', 'VACCINATION', 'SAMPLING']
    if instance.activity_type not in ANCHOR_ACTIVITY_TYPES:
        logger.debug(
            f"Skipping recompute for PlannedActivity {instance.id} "
            f"(activity_type={instance.activity_type}, not an anchor type)"
        )
        return
    
    try:
        # Import here to avoid circular imports
        from apps.batch.tasks import enqueue_batch_recompute
        
        batch = instance.batch
        
        # Use completed_at date, or due_date as fallback
        # Handle both datetime objects (from DB) and date objects (from tests/manual creation)
        if instance.completed_at:
            trigger_date = (
                instance.completed_at.date() 
                if hasattr(instance.completed_at, 'date') 
                else instance.completed_at
            )
        else:
            trigger_date = instance.due_date
        
        logger.debug(
            f"PlannedActivity completed for batch {batch.batch_number} "
            f"(type={instance.activity_type}, date={trigger_date})"
        )
        
        # Enqueue batch-level recompute task
        task_id = enqueue_batch_recompute(
            batch_id=batch.id,
            trigger_date=trigger_date,
            window_days=2
        )
        
        logger.info(
            f"📋 Enqueued growth assimilation task {task_id} for "
            f"batch {batch.batch_number} after {instance.activity_type} activity "
            f"completed (window: {trigger_date} ± 2 days)"
        )
    except Exception as e:
        # Gracefully handle Celery/Redis unavailability
        logger.warning(
            f"Could not enqueue recompute task after PlannedActivity "
            f"{instance.id} completion: {e}. Normal in test/CI without Redis/Celery."
        )


def register_planning_signals():
    """
    Register signals for the planning app.
    
    This function should be called from the batch app's ready() method
    to avoid import issues. It connects to the PlannedActivity model
    from the planning app if available.
    """
    try:
        from apps.planning.models import PlannedActivity
        
        # Connect the signal handler
        post_save.connect(
            on_planned_activity_completed,
            sender=PlannedActivity,
            dispatch_uid='planned_activity_completion_recompute'
        )
        
        logger.info("Registered PlannedActivity completion signal for growth assimilation")
    except ImportError:
        logger.debug("Planning app not available - skipping PlannedActivity signal registration")