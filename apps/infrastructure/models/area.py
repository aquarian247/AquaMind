"""
Area model for the infrastructure app.

This module defines the Area model, which represents sea areas with geo-positioning
for farming operations.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.infrastructure.models.geography import Geography


class Area(models.Model):
    """
    Sea areas with geo-positioning for farming operations.
    """
    name = models.CharField(max_length=100)
    geography = models.ForeignKey(Geography, on_delete=models.PROTECT, related_name='areas')
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
    max_biomass = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Maximum biomass capacity in kg"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.geography.name})"
