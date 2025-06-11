"""
Container model for the infrastructure app.

This module defines the Container model, which represents containers that hold fish,
such as tanks, pens, or trays.
"""

from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.area import Area


class Container(models.Model):
    """
    Containers that hold fish, such as tanks, pens, or trays.
    Can be in a hall (within a station) or in a sea area.
    """
    name = models.CharField(max_length=100)
    container_type = models.ForeignKey(
        ContainerType, 
        on_delete=models.PROTECT, 
        related_name='containers'
    )
    
    # A container can be in either a hall or an area, but not both
    hall = models.ForeignKey(
        Hall, 
        on_delete=models.CASCADE, 
        related_name='containers',
        null=True, 
        blank=True
    )
    area = models.ForeignKey(
        Area, 
        on_delete=models.CASCADE, 
        related_name='containers',
        null=True, 
        blank=True
    )
    
    volume_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    max_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2)
    feed_recommendations_enabled = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(hall__isnull=False, area__isnull=True) | 
                    models.Q(hall__isnull=True, area__isnull=False)
                ),
                name="container_in_either_hall_or_area"
            )
        ]
    
    def clean(self):
        """Validate the container model.
        
        1. Ensure container is either in a hall or area (not both)
        2. Ensure container volume doesn't exceed container type's maximum volume
        
        Raises:
            ValidationError: If any validation constraints are violated
        """
        # Validate that container is in either a hall or an area, not both
        if self.hall and self.area:
            raise ValidationError("Container cannot be in both a hall and a sea area")
        if not self.hall and not self.area:
            raise ValidationError("Container must be in either a hall or a sea area")
            
        # Validate that volume doesn't exceed container type's maximum volume
        if self.container_type and self.volume_m3:
            if self.volume_m3 > self.container_type.max_volume_m3:
                raise ValidationError({
                    'volume_m3': f'Container volume ({self.volume_m3} m³) cannot exceed the maximum volume '
                               f'for this container type ({self.container_type.max_volume_m3} m³)'
                })
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        location = self.hall.name if self.hall else self.area.name
        return f"{self.name} ({self.container_type.name} in {location})"
