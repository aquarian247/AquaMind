"""
Feed purchase model for the inventory app.
"""
from django.db import models
from django.core.validators import MinValueValidator

from .feed import Feed
from apps.inventory.utils import TimestampedModelMixin, DecimalFieldMixin


class FeedPurchase(TimestampedModelMixin, models.Model):
    """
    Records feed purchase history for inventory tracking.
    """
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name='purchases')
    purchase_date = models.DateField()
    quantity_kg = DecimalFieldMixin.positive_decimal_field(
        min_value=0.01,
        help_text="Amount of feed purchased in kilograms"
    )
    cost_per_kg = DecimalFieldMixin.positive_decimal_field(
        min_value=0.01,
        help_text="Cost per kilogram"
    )
    supplier = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100, blank=True, help_text="Supplier's batch number")
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"{self.feed} - {self.quantity_kg}kg purchased on {self.purchase_date}"
