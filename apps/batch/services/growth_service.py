"""
Growth Sample Service for Batch App

Handles growth sample related operations including updating assignment weighing dates.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from typing import Optional

from apps.batch.models import GrowthSample, BatchContainerAssignment


class GrowthSampleService:
    """Service for handling growth sample operations."""

    @classmethod
    def update_assignment_weighing_dates(cls, growth_sample: GrowthSample) -> None:
        """
        Update last_weighing_date for all active assignments of the batch.

        Args:
            growth_sample: The growth sample that was created/updated
        """
        # Update all active container assignments for this batch
        BatchContainerAssignment.objects.filter(
            batch=growth_sample.batch,
            is_active=True
        ).update(last_weighing_date=growth_sample.date)

    @classmethod
    def get_latest_weighing_date(cls, batch) -> Optional[GrowthSample]:
        """
        Get the most recent growth sample date for a batch.

        Args:
            batch: The batch to get latest weighing date for

        Returns:
            GrowthSample or None: The most recent growth sample
        """
        return GrowthSample.objects.filter(
            batch=batch
        ).order_by('-date').first()


# Signal handlers
@receiver(post_save, sender=GrowthSample)
def update_assignment_on_growth_sample_save(sender, instance, created, **kwargs):
    """
    Update BatchContainerAssignment last_weighing_date when a GrowthSample is saved.

    This ensures that confidence calculations always have access to the most
    recent weighing date for each assignment.
    """
    if created or instance.date:  # Only update if it's a new sample or has a date
        GrowthSampleService.update_assignment_weighing_dates(instance)
