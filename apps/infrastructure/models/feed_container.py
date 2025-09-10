"""
FeedContainer model for the infrastructure app.

This module defines the FeedContainer model, which represents feed storage units
linked to areas or halls.
"""

from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.area import Area


class FeedContainer(models.Model):
    """
    Feed storage units linked to areas or halls.
    Examples: feed silos, feed barges, etc.
    """
    CONTAINER_TYPES = [
        ('SILO', 'Silo'),
        ('BARGE', 'Barge'),
        ('TANK', 'Tank'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    container_type = models.CharField(max_length=20, choices=CONTAINER_TYPES)
    
    # A feed container can be linked to either a hall or an area, but not both
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='feed_containers', null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='feed_containers', null=True, blank=True)
    
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Capacity in kg")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(hall__isnull=False, area__isnull=True) |
                    models.Q(hall__isnull=True, area__isnull=False)
                ),
                name="feed_container_in_either_hall_or_area"
            )
        ]
        ordering = ['name']

    history = HistoricalRecords()
    
    def clean(self):
        """Validate the feed container model.

        Ensures that the feed container is linked to either a hall or a sea area,
        but not both.

        Raises:
            ValidationError: If the container is linked to both or neither location.
        """
        if self.hall and self.area:
            raise ValidationError("Feed container cannot be linked to both a hall and a sea area")
        if not self.hall and not self.area:
            raise ValidationError("Feed container must be linked to either a hall or a sea area")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        location = self.hall.name if self.hall else self.area.name
        return f"{self.name} ({self.get_container_type_display()} at {location})"
