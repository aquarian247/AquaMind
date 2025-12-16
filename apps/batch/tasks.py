"""
Celery tasks for batch growth assimilation and live forward projections.

This module contains asynchronous tasks for:
1. Recomputing actual daily states when operational events occur
2. Computing live forward projections (nightly scheduled task)

Architecture:
- Lightweight signal handlers enqueue tasks (don't block requests)
- Celery workers execute heavy computation in background
- Redis provides task queue and deduplication
- Tasks are idempotent (safe to run multiple times)

Usage:
    # From signal handler
    recompute_assignment_window.delay(assignment_id, start_date, end_date)

    # From management command
    recompute_batch_window.delay(batch_id, start_date, end_date)

    # Nightly live forward projection (via Celery Beat)
    compute_all_live_forward_projections.delay()

Performance:
- Typical task: 100-500ms for 5-day window
- Large batch: 2-5 seconds for full lifecycle
- Live projection: 200-500ms per assignment (full horizon)
- Worker pool: 4-8 workers recommended for production

Issue: #112 - Phase 4 (Event-Driven Recompute)
Issue: Live Forward Projection Feature
"""
import logging
from datetime import date, timedelta
from typing import Dict, Optional

from celery import shared_task
from django.core.cache import cache
from django.db import transaction

from apps.batch.models import BatchContainerAssignment, Batch
from apps.batch.services.growth_assimilation import (
    GrowthAssimilationEngine,
    recompute_batch_assignments
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Deduplication Helpers
# ------------------------------------------------------------------

def get_dedup_key(assignment_id: int, trigger_date: date) -> str:
    """
    Generate Redis key for deduplication tracking.
    
    Key format: "growth_assimilation:dedup:{assignment_id}:{date}"
    
    Args:
        assignment_id: BatchContainerAssignment ID
        trigger_date: Date that triggered the recompute
        
    Returns:
        Redis key string
    """
    return f"growth_assimilation:dedup:{assignment_id}:{trigger_date.isoformat()}"


def should_enqueue_task(assignment_id: int, trigger_date: date, ttl_seconds: int = 300) -> bool:
    """
    Check if task should be enqueued (deduplication).
    
    Multiple events on the same day (e.g., 2 growth samples) should only
    trigger one recompute task. Uses Redis SET with TTL for tracking.
    
    Args:
        assignment_id: BatchContainerAssignment ID
        trigger_date: Date that triggered the recompute
        ttl_seconds: TTL for dedup key (default 5 minutes)
        
    Returns:
        True if task should be enqueued, False if already queued
    """
    key = get_dedup_key(assignment_id, trigger_date)
    
    # Try to set key with NX (only if not exists)
    # cache.add() returns True if key was set, False if already exists
    was_set = cache.add(key, '1', timeout=ttl_seconds)
    
    if not was_set:
        logger.debug(
            f"Deduplication: Skipping task for assignment {assignment_id} "
            f"on {trigger_date} (already queued)"
        )
    
    return was_set


# ------------------------------------------------------------------
# Task: Assignment-Level Recompute
# ------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def recompute_assignment_window(
    self,
    assignment_id: int,
    start_date: str,
    end_date: str
) -> Dict:
    """
    Recompute actual daily states for a single assignment in a date window.
    
    This is the primary task triggered by operational events (growth samples,
    transfers, treatments). Computes states for a small window around the event.
    
    Args:
        assignment_id: BatchContainerAssignment ID
        start_date: ISO format date string (YYYY-MM-DD)
        end_date: ISO format date string (YYYY-MM-DD)
        
    Returns:
        dict with:
            - success: bool
            - states_created: int
            - states_updated: int
            - assignment_id: int
            - date_range: str
            
    Raises:
        Retry: If task fails (automatic retry with exponential backoff)
    """
    try:
        # Parse dates
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        logger.info(
            f"[Task {self.request.id}] Recomputing assignment {assignment_id} "
            f"window: {start} to {end}"
        )
        
        # Get assignment
        try:
            assignment = BatchContainerAssignment.objects.select_related(
                'batch', 'container'
            ).get(id=assignment_id)
        except BatchContainerAssignment.DoesNotExist:
            logger.error(f"Assignment {assignment_id} not found")
            return {
                'success': False,
                'error': 'Assignment not found',
                'assignment_id': assignment_id,
            }
        
        # Run engine
        with transaction.atomic():
            engine = GrowthAssimilationEngine(assignment)
            result = engine.recompute_range(start, end)
        
        logger.info(
            f"✅ [Task {self.request.id}] Completed assignment {assignment_id}: "
            f"created={result['rows_created']}, updated={result['rows_updated']}"
        )
        
        return {
            'success': True,
            'rows_created': result['rows_created'],
            'rows_updated': result['rows_updated'],
            'assignment_id': assignment_id,
            'date_range': f"{start} to {end}",
        }
        
    except Exception as exc:
        logger.error(
            f"❌ [Task {self.request.id}] Failed assignment {assignment_id}: {exc}",
            exc_info=True
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=exc)


# ------------------------------------------------------------------
# Task: Batch-Level Recompute
# ------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def recompute_batch_window(
    self,
    batch_id: int,
    start_date: str,
    end_date: str
) -> Dict:
    """
    Recompute actual daily states for ALL assignments of a batch.
    
    Used for:
    - Batch-level events (mortality - affects all assignments)
    - Nightly catch-up jobs
    - Admin-triggered full recompute
    
    Args:
        batch_id: Batch ID
        start_date: ISO format date string (YYYY-MM-DD)
        end_date: ISO format date string (YYYY-MM-DD)
        
    Returns:
        dict with:
            - success: bool
            - batch_id: int
            - assignments_processed: int
            - total_states_created: int
            - total_states_updated: int
            - date_range: str
            
    Raises:
        Retry: If task fails (automatic retry with exponential backoff)
    """
    try:
        # Parse dates
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        logger.info(
            f"[Task {self.request.id}] Recomputing batch {batch_id} "
            f"window: {start} to {end}"
        )
        
        # Get batch
        try:
            batch = Batch.objects.get(id=batch_id)
        except Batch.DoesNotExist:
            logger.error(f"Batch {batch_id} not found")
            return {
                'success': False,
                'error': 'Batch not found',
                'batch_id': batch_id,
            }
        
        # Run batch-level recompute
        with transaction.atomic():
            result = recompute_batch_assignments(batch_id, start, end)
        
        logger.info(
            f"✅ [Task {self.request.id}] Completed batch {batch.batch_number}: "
            f"assignments={result['assignments_processed']}, "
            f"created={result['total_rows_created']}, "
            f"updated={result['total_rows_updated']}"
        )
        
        return {
            'success': True,
            'batch_id': batch_id,
            'assignments_processed': result['assignments_processed'],
            'total_rows_created': result['total_rows_created'],
            'total_rows_updated': result['total_rows_updated'],
            'date_range': f"{start} to {end}",
        }
        
    except Exception as exc:
        logger.error(
            f"❌ [Task {self.request.id}] Failed batch {batch_id}: {exc}",
            exc_info=True
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=exc)


# ------------------------------------------------------------------
# Helper: Enqueue with Deduplication
# ------------------------------------------------------------------

def enqueue_recompute_with_deduplication(
    assignment_id: int,
    trigger_date: date,
    window_days: int = 2
) -> Optional[str]:
    """
    Enqueue assignment recompute task with deduplication.
    
    This is the primary function called by signal handlers. It checks if a
    task is already queued for this assignment/date and only enqueues if not.
    
    Args:
        assignment_id: BatchContainerAssignment ID
        trigger_date: Date that triggered the recompute (e.g., sample date)
        window_days: Number of days before/after trigger to recompute (default 2)
        
    Returns:
        Task ID if enqueued, None if deduplicated
        
    Example:
        # From signal handler
        enqueue_recompute_with_deduplication(
            assignment_id=sample.assignment.id,
            trigger_date=sample.sample_date,
            window_days=2
        )
    """
    # Check deduplication
    if not should_enqueue_task(assignment_id, trigger_date):
        return None
    
    # Calculate window
    start_date = trigger_date - timedelta(days=window_days)
    end_date = trigger_date + timedelta(days=window_days)
    
    # Enqueue task
    result = recompute_assignment_window.delay(
        assignment_id,
        start_date.isoformat(),
        end_date.isoformat()
    )
    
    logger.info(
        f"📋 Enqueued task {result.id} for assignment {assignment_id} "
        f"(trigger={trigger_date}, window={start_date} to {end_date})"
    )
    
    return result.id


# ------------------------------------------------------------------
# Helper: Enqueue Batch Recompute
# ------------------------------------------------------------------

def enqueue_batch_recompute(
    batch_id: int,
    trigger_date: date,
    window_days: int = 1
) -> str:
    """
    Enqueue batch-level recompute task (no deduplication).
    
    Used for batch-level events (mortality) that affect all assignments.
    No deduplication since batch-level events are less frequent.
    
    Args:
        batch_id: Batch ID
        trigger_date: Date that triggered the recompute
        window_days: Number of days before/after trigger (default 1)
        
    Returns:
        Task ID
        
    Example:
        # From mortality event signal
        enqueue_batch_recompute(
            batch_id=mortality_event.batch.id,
            trigger_date=mortality_event.event_date,
            window_days=1
        )
    """
    # Calculate window
    start_date = trigger_date - timedelta(days=window_days)
    end_date = trigger_date + timedelta(days=window_days)

    # Enqueue task
    result = recompute_batch_window.delay(
        batch_id,
        start_date.isoformat(),
        end_date.isoformat()
    )

    logger.info(
        f"📋 Enqueued batch task {result.id} for batch {batch_id} "
        f"(trigger={trigger_date}, window={start_date} to {end_date})"
    )

    return result.id


# ------------------------------------------------------------------
# Task: Live Forward Projection (Nightly)
# ------------------------------------------------------------------

@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def compute_all_live_forward_projections(self) -> Dict:
    """
    Compute live forward projections for all active assignments.

    This is the main scheduled task, typically run nightly at 03:00 UTC
    after ActualDailyAssignmentState data is updated.

    For each active assignment:
    1. Compute projections from latest actual state to scenario end
    2. Store in LiveForwardProjection hypertable
    3. Update ContainerForecastSummary for dashboards

    Guardrails:
    - Skips assignments without pinned scenario
    - Skips assignments without actual state data
    - Idempotent (safe to run multiple times per day)

    Returns:
        Dict with stats (assignments_processed, total_rows, errors)

    Schedule (via Celery Beat):
        'compute-live-projections': {
            'task': 'apps.batch.tasks.compute_all_live_forward_projections',
            'schedule': crontab(hour=3, minute=0),  # 03:00 UTC daily
        }
    """
    from django.db.models import Q
    from django.utils import timezone
    from apps.batch.models import BatchContainerAssignment
    from apps.batch.services.live_projection_engine import LiveProjectionEngine

    logger.info("[Task] Starting nightly live forward projection computation")

    computed_date = timezone.now().date()

    # Get active assignments for active batches with pinned scenarios
    active_assignments = BatchContainerAssignment.objects.filter(
        is_active=True,
        batch__status='ACTIVE',
    ).filter(
        # Must have a pinned scenario or at least one scenario
        Q(batch__pinned_projection_run__isnull=False) |
        Q(batch__scenarios__isnull=False)
    ).select_related(
        'batch__pinned_projection_run__scenario__tgc_model__profile',
        'batch__pinned_projection_run__scenario__mortality_model',
        'container'
    ).distinct()

    stats = {
        'assignments_processed': 0,
        'assignments_skipped': 0,
        'total_rows_created': 0,
        'errors': [],
        'computed_date': computed_date.isoformat(),
    }

    for assignment in active_assignments:
        try:
            engine = LiveProjectionEngine(assignment)
            result = engine.compute_and_store(computed_date=computed_date)

            if result.get('success'):
                stats['assignments_processed'] += 1
                stats['total_rows_created'] += result.get('rows_created', 0)
            else:
                stats['assignments_skipped'] += 1
                if result.get('error'):
                    stats['errors'].append({
                        'assignment_id': assignment.id,
                        'error': result['error'],
                    })

        except Exception as e:
            logger.error(
                f"Error computing projection for assignment {assignment.id}: "
                f"{e}", exc_info=True
            )
            stats['errors'].append({
                'assignment_id': assignment.id,
                'error': str(e),
            })

    logger.info(
        f"✅ [Task] Live projection complete: "
        f"{stats['assignments_processed']} processed, "
        f"{stats['total_rows_created']} rows created, "
        f"{len(stats['errors'])} errors"
    )

    return stats


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def compute_assignment_live_projection(
    self,
    assignment_id: int,
    computed_date: Optional[str] = None
) -> Dict:
    """
    Compute live forward projection for a single assignment.

    Use this for on-demand projection updates (e.g., after significant
    growth sample or manual trigger).

    Args:
        assignment_id: BatchContainerAssignment ID
        computed_date: ISO date string (default: today)

    Returns:
        Dict with stats (success, rows_created, etc.)
    """
    from django.utils import timezone
    from apps.batch.models import BatchContainerAssignment
    from apps.batch.services.live_projection_engine import LiveProjectionEngine

    logger.info(
        f"[Task] Computing live projection for assignment {assignment_id}"
    )

    try:
        assignment = BatchContainerAssignment.objects.select_related(
            'batch__pinned_projection_run__scenario__tgc_model__profile',
            'batch__pinned_projection_run__scenario__mortality_model',
            'container'
        ).get(id=assignment_id)
    except BatchContainerAssignment.DoesNotExist:
        logger.error(f"Assignment {assignment_id} not found")
        return {
            'success': False,
            'error': 'Assignment not found',
            'assignment_id': assignment_id,
        }

    # Parse computed_date if provided
    if computed_date:
        from datetime import date as date_cls
        comp_date = date_cls.fromisoformat(computed_date)
    else:
        comp_date = timezone.now().date()

    try:
        engine = LiveProjectionEngine(assignment)
        result = engine.compute_and_store(computed_date=comp_date)

        logger.info(
            f"✅ [Task] Projection complete for assignment {assignment_id}: "
            f"{result.get('rows_created', 0)} rows"
        )

        return result

    except Exception as e:
        logger.error(
            f"Error computing projection for assignment {assignment_id}: {e}",
            exc_info=True
        )
        raise self.retry(exc=e)

