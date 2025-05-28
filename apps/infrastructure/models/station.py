"""
FreshwaterStation model for the infrastructure app.

This module defines the FreshwaterStation model, which represents freshwater
stations with geo-positioning for early lifecycle stages.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.infrastructure.models.geography import Geography


class FreshwaterStation(models.Model):
    """
    Freshwater stations with geo-positioning for early lifecycle stages.
    """
    STATION_TYPES = [
        ('FRESHWATER', 'Freshwater'),
        ('BROODSTOCK', 'Broodstock'),
    ]
    
    name = models.CharField(max_length=100)
    station_type = models.CharField(max_length=20, choices=STATION_TYPES)
    geography = models.ForeignKey(Geography, on_delete=models.PROTECT, related_name='stations')
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude (automatically set when location is selected on map)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude (automatically set when location is selected on map)"
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_station_type_display()})"
