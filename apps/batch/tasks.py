"""
Celery tasks for batch growth assimilation.

This module contains asynchronous tasks for recomputing actual daily states
when operational events occur (growth samples, transfers, treatments, mortality).

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

Performance:
- Typical task: 100-500ms for 5-day window
- Large batch: 2-5 seconds for full lifecycle
- Worker pool: 4-8 workers recommended for production

Issue: #112 - Phase 4 (Event-Driven Recompute)
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

