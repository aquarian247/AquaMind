"""
Treatment models for health monitoring.

This module defines models related to treatments.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from simple_history.models import HistoricalRecords

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container
from .vaccination import VaccinationType

User = get_user_model()


class Treatment(models.Model):
    """Model for recording treatments applied to batches."""
    TREATMENT_TYPES = (
        ('medication', 'Medication'),
        ('vaccination', 'Vaccination'),
        ('physical', 'Physical Treatment'),
        ('other', 'Other'),
    )
    OUTCOME_CHOICES = (
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('partial', 'Partially Successful'),
        ('unsuccessful', 'Unsuccessful'),
    )

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='treatments',
        help_text="The batch receiving the treatment."
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='treatments',
        help_text="The specific container, if applicable."
    )
    batch_assignment = models.ForeignKey(
        BatchContainerAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='treatments',
        help_text="The specific batch-container assignment, if applicable."
    )
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='treatments',
        help_text="User who recorded the treatment."
    )
    treatment_date = models.DateTimeField(default=timezone.now)
    treatment_type = models.CharField(
        max_length=20, choices=TREATMENT_TYPES,
        help_text="Type of treatment administered."
    )
    vaccination_type = models.ForeignKey(
        VaccinationType, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='treatments',
        help_text="Specific vaccination type, if applicable."
    )
    description = models.TextField(
        help_text="Description of the treatment."
    )
    dosage = models.CharField(
        max_length=100, blank=True,
        help_text="Dosage of medication or treatment."
    )
    duration_days = models.PositiveIntegerField(
        default=0,
        help_text="Duration of treatment in days."
    )
    withholding_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Withholding period in days."
    )
    outcome = models.CharField(
        max_length=20, choices=OUTCOME_CHOICES, default='pending',
        help_text="Outcome of the treatment."
    )

    class Meta:
        ordering = ['-treatment_date']
        verbose_name_plural = "Treatments"

    history = HistoricalRecords()

    def __str__(self):
        """Return a string representation of the treatment."""
        return f"{self.get_treatment_type_display()} on {self.treatment_date.strftime('%Y-%m-%d')}"

    @property
    def withholding_end_date(self):
        """Calculate the end date of the withholding period.

        Returns:
            datetime.date or None: The end date of the withholding period, 
                                     or None if no withholding period is set.
        """
        if self.withholding_period_days > 0:
            return self.treatment_date.date() + timedelta(days=self.withholding_period_days)
        return None
