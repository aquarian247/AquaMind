"""
Signal handlers for the planning app.

Handles automatic activity generation from templates and workflow completion
synchronization.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.batch.models import Batch, BatchTransferWorkflow
from .models import ActivityTemplate, PlannedActivity


@receiver(post_save, sender=Batch)
def auto_generate_activities_from_templates(sender, instance, created, **kwargs):
    """Auto-generate planned activities when a new batch is created."""
    if not created:
        return  # Only run for new batches

    # Get the default scenario for this batch (if exists)
    # Note: Batches may not always have scenarios initially
    try:
        # Try to get baseline scenario (field may not exist in all versions)
        default_scenario = instance.scenarios.filter(is_baseline=True).first()
    except Exception:
        # If is_baseline field doesn't exist, get first scenario or batch.pinned_scenario
        default_scenario = (
            getattr(instance, 'pinned_scenario', None) or instance.scenarios.first()
        )

    if not default_scenario:
        return  # No scenario to attach activities to
    
    # Get all active templates with DAY_OFFSET trigger
    templates = ActivityTemplate.objects.filter(
        is_active=True,
        trigger_type='DAY_OFFSET'
    )
    
    # Generate activities
    for template in templates:
        template.generate_activity(
            scenario=default_scenario,
            batch=instance
        )


def _find_matching_transfer_activity(workflow):
    candidates = PlannedActivity.objects.filter(
        batch=workflow.batch,
        activity_type='TRANSFER',
        status__in=['PENDING', 'IN_PROGRESS'],
        transfer_workflow__isnull=True,
    )
    if not candidates.exists():
        return None

    target_date = workflow.planned_start_date or workflow.actual_completion_date
    if target_date:
        activity = min(
            candidates,
            key=lambda activity: abs((activity.due_date - target_date).days),
        )
        if abs((activity.due_date - target_date).days) > 3:
            return None
        return activity

    return candidates.order_by('due_date').first()


@receiver(post_save, sender=BatchTransferWorkflow)
def sync_workflow_completion_to_activity(sender, instance, created, **kwargs):
    """Update linked planned activity when workflow completes."""
    if created:
        return  # Only run on updates

    if instance.status == 'COMPLETED':
        activity = instance.planned_activity

        # Fallback: link workflow to closest pending transfer activity for same batch
        if not activity:
            activity = _find_matching_transfer_activity(instance)
            if activity:
                activity.transfer_workflow = instance
                activity.save(update_fields=['transfer_workflow', 'updated_at'])

        if activity and activity.status != 'COMPLETED':
            # Use the workflow's completed_by, or fall back to initiated_by
            completing_user = instance.completed_by or instance.initiated_by
            activity.mark_completed(user=completing_user)

