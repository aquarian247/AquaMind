"""
ContainerType model for the infrastructure app.

This module defines the ContainerType model, which represents types of containers
used in aquaculture operations.
"""

from django.db import models
from simple_history.models import HistoricalRecords


class ContainerType(models.Model):
    """
    Types of containers used in aquaculture operations.
    Examples: tanks, pens, trays for eggs, etc.
    """
    CONTAINER_CATEGORIES = [
        ('TANK', 'Tank'),
        ('PEN', 'Pen'),
        ('TRAY', 'Tray'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CONTAINER_CATEGORIES)
    max_volume_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
