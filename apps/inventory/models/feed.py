"""
Feed model for the inventory app.
"""
from django.db import models

from apps.inventory.utils import (
    TimestampedModelMixin, ActiveModelMixin, DecimalFieldMixin
)


class Feed(TimestampedModelMixin, ActiveModelMixin, models.Model):
    """
    Feed types used in aquaculture operations.
    Tracks feed types, brands, and nutritional composition.
    """
    FEED_SIZE_CHOICES = [
        ('MICRO', 'Micro'),
        ('SMALL', 'Small'),
        ('MEDIUM', 'Medium'),
        ('LARGE', 'Large'),
    ]

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    size_category = models.CharField(max_length=20, choices=FEED_SIZE_CHOICES)
    pellet_size_mm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pellet size in millimeters"
    )
    protein_percentage = DecimalFieldMixin.percentage_field(
        null=True,
        blank=True,
        help_text="Protein content percentage"
    )
    fat_percentage = DecimalFieldMixin.percentage_field(
        null=True,
        blank=True,
        help_text="Fat content percentage"
    )
    carbohydrate_percentage = DecimalFieldMixin.percentage_field(
        null=True,
        blank=True,
        help_text="Carbohydrate content percentage"
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Feed"

    def __str__(self):
        return (
            f"{self.brand} - {self.name} ({self.get_size_category_display()})"
        )
