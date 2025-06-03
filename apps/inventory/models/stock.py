"""
Feed stock model for the inventory app.
"""
from django.db import models

from .feed import Feed
from apps.infrastructure.models import FeedContainer
from apps.inventory.utils import UpdatedModelMixin, DecimalFieldMixin


class FeedStock(UpdatedModelMixin, models.Model):
    """
    Tracks current feed inventory levels in feed containers.
    """
    feed = models.ForeignKey(
        Feed, 
        on_delete=models.PROTECT, 
        related_name='stock_levels'
    )
    feed_container = models.ForeignKey(
        FeedContainer, 
        on_delete=models.CASCADE, 
        related_name='feed_stocks'
    )
    current_quantity_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Current amount of feed in stock (kg)"
    )
    reorder_threshold_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Threshold for reordering (kg)"
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['feed', 'feed_container']

    def __str__(self):
        return (
            f"{self.feed} in {self.feed_container.name}: {self.current_quantity_kg}kg"
        )

    def needs_reorder(self):
        """Check if the current stock level is below the reorder threshold."""
        return self.current_quantity_kg <= self.reorder_threshold_kg
