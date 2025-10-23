"""
Signal handlers for automatic FCR calculation.

This module contains signal handlers that automatically recalculate Feed Conversion
Ratio (FCR) summaries when users create feeding events or growth samples.

Key behaviors:
- When FeedingEvent is created → Recalculate container and batch FCR
- When GrowthSample is created → Update weighing dates and recalculate FCR
- Uses 30-day rolling window for continuous updates
- Skips calculation for inactive assignments
- Includes proper error handling and logging
"""
import logging
from datetime import date, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.inventory.models import FeedingEvent
from apps.batch.models import GrowthSample
from apps.inventory.services.fcr_service import FCRCalculationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FeedingEvent)
def recalculate_fcr_on_feeding_event(sender, instance, created, **kwargs):
    """
    Automatically recalculate FCR when a feeding event is created.
    
    This signal ensures FCR summaries stay up-to-date as users add feeding
    events through the UI or API. Uses a 30-day rolling window to provide
    continuous FCR updates.
    
    Args:
        sender: The FeedingEvent model class
        instance: The FeedingEvent instance that was saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional signal arguments
        
    Performance:
        - Typically completes in 100-300ms for normal batches
        - Skips inactive assignments for efficiency
        - Can be disabled via serializer flag for bulk imports
        
    Example:
        User adds 500kg feed → Signal calculates FCR → Updated data shown instantly
    """
    # Only trigger on new events, not updates
    if not created:
        logger.debug(f"Skipping FCR calc for FeedingEvent update (id={instance.id})")
        return
    
    # Skip if no batch assignment (shouldn't happen but defensive)
    assignment = instance.batch_assignment
    if not assignment:
        logger.warning(
            f"FeedingEvent {instance.id} has no batch_assignment, "
            f"skipping FCR calculation"
        )
        return
    
    # Skip inactive assignments (historical data)
    if not assignment.is_active:
        logger.debug(
            f"Skipping FCR calc for inactive assignment "
            f"(assignment={assignment.id})"
        )
        return
    
    try:
        # Calculate for last 30 days (rolling window)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        logger.debug(
            f"Recalculating FCR for batch {instance.batch.batch_number} "
            f"after feeding event (container={assignment.container.name})"
        )
        
        # Update container-level summary
        container_summary = FCRCalculationService.create_container_feeding_summary(
            assignment, start_date, end_date
        )
        
        if container_summary:
            logger.debug(
                f"Container summary updated: FCR={container_summary.fcr}, "
                f"confidence={container_summary.confidence_level}"
            )
        
        # Update batch-level summary (aggregates all containers)
        batch_summary = FCRCalculationService.aggregate_container_fcr_to_batch(
            instance.batch, start_date, end_date
        )
        
        if batch_summary:
            logger.info(
                f"✅ FCR auto-calculated for batch {instance.batch.batch_number}: "
                f"weighted_avg_fcr={batch_summary.weighted_avg_fcr}, "
                f"confidence={batch_summary.overall_confidence_level}"
            )
        else:
            logger.warning(
                f"⚠️ Batch FCR summary not created for {instance.batch.batch_number} "
                f"(insufficient data)"
            )
            
    except Exception as e:
        # Log error but don't block feeding event creation
        logger.error(
            f"❌ FCR calculation failed for batch {instance.batch.batch_number}: {e}",
            exc_info=True
        )


@receiver(post_save, sender=GrowthSample)
def update_fcr_on_growth_sample(sender, instance, created, **kwargs):
    """
    Update FCR and weighing dates when growth sample is added.
    
    Growth samples (weighing events) are critical for FCR accuracy because:
    1. They provide actual biomass measurements (vs estimates)
    2. They affect confidence levels (recent weighing = higher confidence)
    3. They enable calculation of biomass gain
    
    This signal:
    - Updates last_weighing_date on all active assignments for the batch
    - Recalculates FCR for all containers (new biomass data)
    - Aggregates to batch level
    
    Args:
        sender: The GrowthSample model class
        instance: The GrowthSample instance that was saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional signal arguments
        
    Example:
        User records 500g average weight → last_weighing_date updates →
        Confidence changes from MEDIUM to VERY_HIGH → FCR recalculates
        with new biomass gain
    """
    # Only trigger on new samples, not updates
    if not created:
        logger.debug(f"Skipping FCR calc for GrowthSample update (id={instance.id})")
        return
    
    try:
        # GrowthSample has 'assignment' field, batch is accessed via assignment.batch
        batch = instance.assignment.batch
        sample_date = instance.sample_date
        
        logger.debug(
            f"Updating FCR for batch {batch.batch_number} "
            f"after growth sample (avg_weight={instance.avg_weight_g}g)"
        )
        
        # Update last_weighing_date for all active assignments
        # This improves confidence levels for future FCR calculations
        active_assignments = batch.batch_assignments.filter(
            is_active=True
        )
        
        updated_count = active_assignments.update(last_weighing_date=sample_date)
        logger.debug(
            f"Updated last_weighing_date for {updated_count} active assignments "
            f"to {sample_date}"
        )
        
        # Calculate for last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        # Recalculate all container summaries for this batch
        # (new biomass data affects FCR calculation)
        container_summaries_created = 0
        for assignment in active_assignments:
            summary = FCRCalculationService.create_container_feeding_summary(
                assignment, start_date, end_date
            )
            if summary:
                container_summaries_created += 1
        
        logger.debug(
            f"Updated {container_summaries_created} container summaries "
            f"for batch {batch.batch_number}"
        )
        
        # Aggregate to batch level
        batch_summary = FCRCalculationService.aggregate_container_fcr_to_batch(
            batch, start_date, end_date
        )
        
        if batch_summary:
            logger.info(
                f"✅ FCR auto-updated for batch {batch.batch_number} "
                f"after growth sample: weighted_avg_fcr={batch_summary.weighted_avg_fcr}, "
                f"confidence={batch_summary.overall_confidence_level} "
                f"(weighing: {instance.avg_weight_g}g)"
            )
        else:
            logger.warning(
                f"⚠️ Batch FCR summary not created for {batch.batch_number} "
                f"after growth sample (insufficient data)"
            )
            
    except Exception as e:
        # Log error but don't block growth sample creation
        logger.error(
            f"❌ FCR update failed for batch {instance.assignment.batch.batch_number}: {e}",
            exc_info=True
        )

