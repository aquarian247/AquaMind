"""
Geography model for the infrastructure app.

This module defines the Geography model, which represents regions of operation
such as Faroe Islands or Scotland.
"""

from django.db import models
from simple_history.models import HistoricalRecords


class Geography(models.Model):
    """
    Define regions of operation (e.g., Faroe Islands, Scotland).
    Used for region-based access control and operations.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Geographies"
        ordering = ['name']

    history = HistoricalRecords()
    
    def __str__(self):
        return self.name
