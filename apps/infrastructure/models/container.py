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
from apps.infrastructure.models.transport_carrier import TransportCarrier


class Container(models.Model):
    """
    Containers that hold fish, such as tanks, pens, or trays.
    Can be in a hall (within a station) or in a sea area.
    """
    HIERARCHY_ROLES = [
        ("HOLDING", "Holding"),
        ("STRUCTURAL", "Structural"),
    ]

    name = models.CharField(max_length=100)
    container_type = models.ForeignKey(
        ContainerType, 
        on_delete=models.PROTECT, 
        related_name='containers'
    )
    
    # A container can be located in a hall, an area, or a transport carrier.
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
    carrier = models.ForeignKey(
        TransportCarrier,
        on_delete=models.SET_NULL,
        related_name="tanks",
        null=True,
        blank=True,
    )
    parent_container = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="child_containers",
        null=True,
        blank=True,
    )
    hierarchy_role = models.CharField(
        max_length=20,
        choices=HIERARCHY_ROLES,
        default="HOLDING",
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
                    models.Q(
                        hall__isnull=False,
                        area__isnull=True,
                        carrier__isnull=True,
                    )
                    | models.Q(
                        hall__isnull=True,
                        area__isnull=False,
                        carrier__isnull=True,
                    )
                    | models.Q(
                        hall__isnull=True,
                        area__isnull=True,
                        carrier__isnull=False,
                    )
                ),
                name="container_in_hall_area_or_carrier"
            )
        ]
    
    def clean(self):
        """Validate the container model.
        
        1. Ensure container is in one location context (hall, area, or carrier)
        2. Ensure container volume doesn't exceed container type's maximum volume
        
        Raises:
            ValidationError: If any validation constraints are violated
        """
        # Validate that container has exactly one location context.
        location_refs = [self.hall_id, self.area_id, self.carrier_id]
        populated_locations = [ref for ref in location_refs if ref is not None]
        if len(populated_locations) != 1:
            raise ValidationError(
                "Container must be linked to exactly one of hall, area, or carrier"
            )

        if self.parent_container:
            if self.parent_container_id == self.id:
                raise ValidationError("Container cannot reference itself as parent")
            if self.parent_container.hierarchy_role != "STRUCTURAL":
                raise ValidationError(
                    "Parent container must use hierarchy role STRUCTURAL"
                )

            parent_location = (
                self.parent_container.hall_id,
                self.parent_container.area_id,
                self.parent_container.carrier_id,
            )
            this_location = (self.hall_id, self.area_id, self.carrier_id)
            if parent_location != this_location:
                raise ValidationError(
                    "Child container must share hall/area/carrier with parent container"
                )

            # Defensive cycle guard for parent_container chains.
            seen_ids = {self.id} if self.id else set()
            node = self.parent_container
            while node:
                if node.id in seen_ids:
                    raise ValidationError("Container parent hierarchy cannot contain cycles")
                if node.id:
                    seen_ids.add(node.id)
                node = node.parent_container
            
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
        if self.hall:
            location = self.hall.name
        elif self.area:
            location = self.area.name
        elif self.carrier:
            location = self.carrier.name
        else:  # pragma: no cover - guarded by model constraints
            location = "Unassigned"
        return f"{self.name} ({self.container_type.name} in {location})"
