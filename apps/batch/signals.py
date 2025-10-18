"""
Signal handlers for batch lifecycle management.

This module contains signal handlers that manage the automatic transition
of batch status based on container assignment states.
"""
import logging
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.batch.models import BatchContainerAssignment

logger = logging.getLogger(__name__)


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