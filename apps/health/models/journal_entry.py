"""
Journal Entry model for health monitoring.

This module defines the JournalEntry model which is used to record health observations
and actions related to fish batches or containers.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.batch.models import Batch
from apps.infrastructure.models import Container

User = get_user_model()


class JournalEntry(models.Model):
    """
    Model for recording health observations and actions related to fish batches
    or containers.
    """
    CATEGORY_CHOICES = (
        ('observation', 'Observation'),
        ('issue', 'Issue'),
        ('action', 'Action'),
        ('diagnosis', 'Diagnosis'),
        ('treatment', 'Treatment'),
        ('vaccination', 'Vaccination'),
        ('sample', 'Sample'),
    )
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='journal_entries',
        help_text="The batch associated with this journal entry."
    )
    container = models.ForeignKey(
        Container, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='journal_entries',
        help_text="The specific container, if applicable."
    )
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='journal_entries',
        help_text="User who created the entry."
    )
    entry_date = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default='low', blank=True, null=True
    )
    description = models.TextField()
    resolution_status = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Journal Entries"
        ordering = ['-entry_date']

    def __str__(self):
        return (
            f"{self.get_category_display()} - "
            f"{self.entry_date.strftime('%Y-%m-%d')}"
        )
