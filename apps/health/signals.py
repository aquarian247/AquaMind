"""
Signal handlers for health events affecting growth assimilation.

This module contains signal handlers for health-related events that can
serve as anchors for batch growth assimilation (Issue #112 Phase 4).

Currently handles:
- Treatment with weighing (vaccinations, etc.)

Future: Could add other health events as needed.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.health.models import Treatment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Treatment)
def on_treatment_with_weighing(sender, instance, created, **kwargs):
    """
    Trigger growth assimilation recompute for treatments with weighing.
    
    Treatments (e.g., vaccinations) often include weighing fish. These
    measured weights serve as anchors for growth assimilation.
    
    Only trigger if:
    1. Treatment has includes_weighing = True
    2. Treatment is new (not update)
    
    Window: [treatment_date - 2, treatment_date + 2]
    
    Note: Treatment model has links to HealthSamplingEvent which contains
    IndividualFishObservation records with actual weights (per handover doc).
    
    Args:
        sender: Treatment model class
        instance: The saved Treatment instance
        created: True if new instance, False if update
        **kwargs: Additional signal arguments
    """
    if not created:
        # Only trigger on new treatments, not updates
        logger.debug(f"Skipping recompute for Treatment update (id={instance.id})")
        return
    
    # Check if treatment includes weighing
    if not instance.includes_weighing:
        logger.debug(
            f"Skipping recompute for Treatment {instance.id} "
            f"(includes_weighing=False)"
        )
        return
    
    try:
        # Import here to avoid circular imports
        from apps.batch.tasks import enqueue_recompute_with_deduplication
        
        # Get batch container assignment
        # Treatment has FK to batch_container_assignment
        assignment = instance.batch_container_assignment
        if not assignment:
            logger.warning(
                f"Treatment {instance.id} has no batch_container_assignment, "
                f"skipping recompute"
            )
            return
        
        # Get treatment date
        treatment_date = instance.treatment_date
        if not treatment_date:
            logger.warning(
                f"Treatment {instance.id} has no treatment_date, "
                f"skipping recompute"
            )
            return
        
        logger.debug(
            f"Treatment with weighing created for assignment {assignment.id} "
            f"(batch={assignment.batch.batch_number}, date={treatment_date}, "
            f"treatment_type={instance.treatment_type})"
        )
        
        # Enqueue recompute task (with deduplication)
        task_id = enqueue_recompute_with_deduplication(
            assignment_id=assignment.id,
            trigger_date=treatment_date,
            window_days=2
        )
        
        if task_id:
            logger.info(
                f"📋 Enqueued growth assimilation task {task_id} for "
                f"assignment {assignment.id} after treatment with weighing "
                f"(window: {treatment_date} ± 2 days)"
            )
    except Exception as e:
        # Gracefully handle Celery/Redis unavailability
        logger.warning(
            f"Could not enqueue growth assimilation task after treatment "
            f"{instance.id}: {e}. Normal in test/CI without Redis/Celery."
        )

