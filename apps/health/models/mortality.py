"""
Mortality models for health monitoring.

This module defines models related to mortality records and lice counts.
"""

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
import logging

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container

User = get_user_model()
logger = logging.getLogger(__name__)


class MortalityReason(models.Model):
    """Model for categorizing reasons for mortality events."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Mortality Reasons"
        ordering = ['name']

    def __str__(self):
        """Return a string representation of the mortality reason."""
        return self.name


class MortalityRecord(models.Model):
    """Model for recording mortality events."""
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='mortality_records',
        help_text="The batch experiencing mortality."
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mortality_records',
        help_text="The specific container, if applicable."
    )
    event_date = models.DateTimeField(default=timezone.now)
    count = models.PositiveIntegerField(
        help_text="Number of fish that died."
    )
    reason = models.ForeignKey(
        MortalityReason, on_delete=models.PROTECT,
        related_name='mortality_records',
        help_text="Reason for the mortality."
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the mortality event."
    )

    class Meta:
        ordering = ['-event_date']
        verbose_name_plural = "Mortality Records"

    history = HistoricalRecords()

    def __str__(self):
        """Return a string representation of the mortality record."""
        return f"Mortality of {self.count} on {self.event_date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        """Override save to reduce batch population when mortality is recorded."""
        is_new = self.pk is None
        super().save(*args, **kwargs)  # Save first to get PK

        if is_new:
            with transaction.atomic():
                # Find active assignments for this batch and container
                assignments_query = BatchContainerAssignment.objects.filter(
                    batch=self.batch,
                    is_active=True
                )

                if self.container:
                    assignments_query = assignments_query.filter(container=self.container)

                assignments = list(assignments_query.select_for_update())

                if not assignments:
                    logger.warning(
                        f"No active assignments found for mortality record {self.id}. "
                        f"Batch: {self.batch.id}, Container: {self.container.id if self.container else 'None'}"
                    )
                    return

                # Distribute mortality across assignments proportionally
                total_population = sum(a.population_count for a in assignments)
                if total_population == 0:
                    logger.warning(
                        f"All assignments have zero population for mortality record {self.id}. "
                        f"Cannot apply mortality."
                    )
                    return

                remaining_mortality = self.count
                updated_assignments = []

                # If only one assignment, apply all mortality to it
                if len(assignments) == 1:
                    mortality_distribution = {assignments[0].id: min(self.count, assignments[0].population_count)}
                    remaining_mortality = 0  # All mortality applied
                else:
                    # Calculate proportional mortality for each assignment
                    mortality_distribution = {}
                    for assignment in assignments:
                        mortality_portion = int((assignment.population_count / total_population) * self.count)
                        # Ensure at least 1 if the assignment has population
                        mortality_portion = max(1, mortality_portion) if assignment.population_count > 0 else 0
                        mortality_distribution[assignment.id] = min(mortality_portion, assignment.population_count)

                    # Adjust distribution to match total mortality
                    total_distributed = sum(mortality_distribution.values())
                    if total_distributed < self.count:
                        # Distribute remaining mortality to assignments with remaining capacity
                        remaining_to_distribute = self.count - total_distributed
                        for assignment in assignments:
                            if remaining_to_distribute <= 0:
                                break
                            available_capacity = assignment.population_count - mortality_distribution[assignment.id]
                            if available_capacity > 0:
                                additional = min(remaining_to_distribute, available_capacity)
                                mortality_distribution[assignment.id] += additional
                                remaining_to_distribute -= additional

                    # Update remaining_mortality for the final adjustment logic
                    remaining_mortality = self.count - sum(mortality_distribution.values())

                # Apply the mortality to assignments
                for assignment in assignments:
                    mortality_portion = mortality_distribution[assignment.id]

                    # Ensure we don't reduce below zero
                    original_population = assignment.population_count
                    new_population = max(0, assignment.population_count - mortality_portion)

                    # Log if population would have gone negative
                    if original_population - mortality_portion < 0:
                        logger.warning(
                            f"Mortality would drive assignment population negative. "
                            f"Assignment {assignment.id}: {original_population} - {mortality_portion} = {original_population - mortality_portion}. "
                            f"Clamped to 0. Mortality Record ID: {self.id}"
                        )

                    assignment.population_count = new_population

                    # Mark assignment as inactive if population reaches zero
                    if assignment.population_count == 0 and not assignment.departure_date:
                        assignment.departure_date = self.event_date.date()
                        assignment.is_active = False

                    updated_assignments.append(assignment)

                # If we still have remaining mortality and this is container-specific,
                # apply to all assignments equally
                if remaining_mortality > 0:
                    for assignment in updated_assignments:
                        if remaining_mortality <= 0:
                            break
                        if assignment.population_count > 0:
                            reduction = min(remaining_mortality, assignment.population_count)
                            assignment.population_count -= reduction
                            remaining_mortality -= reduction

                            if assignment.population_count == 0 and not assignment.departure_date:
                                assignment.departure_date = self.event_date.date()
                                assignment.is_active = False

                # Save all updated assignments
                for assignment in updated_assignments:
                    if assignment.population_count != BatchContainerAssignment.objects.get(pk=assignment.pk).population_count:
                        assignment.save()

                # Log if mortality count exceeded available population
                if remaining_mortality > 0:
                    logger.error(
                        f"Mortality count ({self.count}) exceeded total available population "
                        f"({total_population}) for batch {self.batch.id}. "
                        f"Remaining unapplied mortality: {remaining_mortality}. "
                        f"Mortality Record ID: {self.id}"
                    )


class LiceCount(models.Model):
    """Model for recording sea lice counts."""
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='lice_counts',
        help_text="The batch being counted."
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lice_counts',
        help_text="The specific container, if applicable."
    )
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='lice_counts',
        help_text="User who performed the count."
    )
    count_date = models.DateTimeField(default=timezone.now)
    adult_female_count = models.PositiveIntegerField(
        help_text="Number of adult female lice counted."
    )
    adult_male_count = models.PositiveIntegerField(
        help_text="Number of adult male lice counted."
    )
    juvenile_count = models.PositiveIntegerField(
        help_text="Number of juvenile lice counted."
    )
    fish_sampled = models.PositiveIntegerField(
        help_text="Number of fish sampled for the count."
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the lice count."
    )

    class Meta:
        ordering = ['-count_date']
        verbose_name_plural = "Lice Counts"

    history = HistoricalRecords()

    def __str__(self):
        """Return a string representation of the lice count."""
        total_count = self.adult_female_count + self.adult_male_count + self.juvenile_count
        return f"Lice Count: {total_count} on {self.count_date.strftime('%Y-%m-%d')}"

    @property
    def average_per_fish(self):
        """Calculate the average number of lice per fish.

        Returns:
            float: The average number of lice per fish, or 0 if no fish were sampled.
        """
        if self.fish_sampled > 0:
            total_lice = self.adult_female_count + self.adult_male_count + self.juvenile_count
            return total_lice / self.fish_sampled
        return 0
