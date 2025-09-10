"""
Hall model for the infrastructure app.

This module defines the Hall model, which represents halls within stations
that contain containers.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.station import FreshwaterStation


class Hall(models.Model):
    """
    Halls within stations that contain containers.
    """
    name = models.CharField(max_length=100)
    freshwater_station = models.ForeignKey(
        FreshwaterStation, 
        on_delete=models.CASCADE, 
        related_name='halls'
    )
    description = models.TextField(blank=True)
    area_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} (in {self.freshwater_station.name})"
