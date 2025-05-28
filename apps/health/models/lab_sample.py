"""
Lab sample models for health monitoring.

This module defines models related to lab samples, including sample types
and health lab samples.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.batch.models import BatchContainerAssignment


class SampleType(models.Model):
    """
    Model for defining types of samples taken for health or quality monitoring.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Sample Types"

    def __str__(self):
        """Return a string representation of the sample type."""
        return self.name


class HealthLabSample(models.Model):
    """
    Represents a lab sample taken from a batch in a specific container
    at a specific point in time, and its results.
    """
    batch_container_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,  # Protect if results are linked
        related_name='lab_samples',
        help_text="The specific batch-container assignment active when the sample was taken."
    )
    sample_type = models.ForeignKey(
        SampleType,  # Changed from HealthSampleType to match existing model
        on_delete=models.PROTECT,
        related_name='lab_samples',
        help_text="Type of sample taken (e.g., skin mucus, water sample)."
    )
    sample_date = models.DateField(
        help_text="Date the sample was physically taken. Crucial for historical linkage."
    )
    date_sent_to_lab = models.DateField(
        null=True, blank=True,
        help_text="Date the sample was sent to the laboratory."
    )
    date_results_received = models.DateField(
        null=True, blank=True,
        help_text="Date the results were received from the laboratory."
    )
    lab_reference_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="External reference ID from the laboratory."
    )
    findings_summary = models.TextField(
        null=True, blank=True,
        help_text="Qualitative summary of the lab findings."
    )
    quantitative_results = models.JSONField(
        null=True, blank=True,
        help_text="Structured quantitative results (e.g., {'param': 'value', 'unit': 'cfu/ml'})."
    )
    attachment = models.FileField(
        upload_to='health/lab_samples/%Y/%m/',
        null=True, blank=True,
        help_text="File attachment for the lab report (e.g., PDF)."
    )
    notes = models.TextField(
        null=True, blank=True,
        help_text="Additional notes or comments by the veterinarian."
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,  # User might be deactivated
        related_name='recorded_lab_samples',
        help_text="User who recorded this lab sample result."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sample_date', '-created_at']
        verbose_name = "Health Lab Sample"
        verbose_name_plural = "Health Lab Samples"

    def __str__(self):
        """Return a string representation of the health lab sample."""
        identifier = self.lab_reference_id if self.lab_reference_id else str(self.pk)
        if self.batch_container_assignment and \
           self.batch_container_assignment.batch and \
           self.batch_container_assignment.container:
            return (
                f"Sample {identifier} for Batch "
                f"{self.batch_container_assignment.batch.batch_number} "
                f"in Container {self.batch_container_assignment.container.name} "
                f"on {self.sample_date}"
            )
        return f"Sample {identifier} on {self.sample_date} (assignment details missing)"

    def clean(self):
        """Validate the HealthLabSample instance data."""
        super().clean()
        if self.sample_date and self.date_sent_to_lab and self.sample_date > self.date_sent_to_lab:
            raise ValidationError({'sample_date': "Sample date cannot be after the date sent to lab."})
        if self.date_sent_to_lab and self.date_results_received and self.date_results_received < self.date_sent_to_lab:
            raise ValidationError(
                {'date_results_received': "Date results received cannot be before the date sent to lab."}
            )

    def get_attachment_upload_path(instance, filename):
        """
        Generate file path for new attachments.

        Args:
            instance: The HealthLabSample instance.
            filename: The original filename of the attachment.

        Returns:
            str: The generated file path.
        """
        # This method is not currently used but kept for future reference
        return f'health/lab_samples/{instance.sample_date.year}/{instance.sample_date.month}/{filename}'
