"""
Mortality models for health monitoring.

This module defines models related to mortality records and lice counts.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.batch.models import Batch
from apps.infrastructure.models import Container

User = get_user_model()


class MortalityReason(models.Model):
    """Model for categorizing reasons for mortality events."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Mortality Reasons"
        ordering = ['name']

    def __str__(self):
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

    def __str__(self):
        return f"Mortality of {self.count} on {self.event_date.strftime('%Y-%m-%d')}"


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

    def __str__(self):
        total_count = self.adult_female_count + self.adult_male_count + self.juvenile_count
        return f"Lice Count: {total_count} on {self.count_date.strftime('%Y-%m-%d')}"

    @property
    def average_per_fish(self):
        """Calculate the average number of lice per fish."""
        if self.fish_sampled > 0:
            total_lice = self.adult_female_count + self.adult_male_count + self.juvenile_count
            return total_lice / self.fish_sampled
        return 0
