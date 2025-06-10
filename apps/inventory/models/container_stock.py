"""
Feed container stock model for FIFO inventory tracking.
"""
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator

from apps.infrastructure.models import FeedContainer
from .purchase import FeedPurchase
from apps.inventory.utils import TimestampedModelMixin, DecimalFieldMixin


class FeedContainerStock(TimestampedModelMixin, models.Model):
    """
    Tracks feed batches in containers for FIFO inventory management.
    
    This model maintains the FIFO order by tracking when feed batches
    are added to containers and their remaining quantities.
    """
    feed_container = models.ForeignKey(
        FeedContainer,
        on_delete=models.CASCADE,
        related_name='feed_batch_stocks',
        help_text="Feed container where this batch is stored"
    )
    feed_purchase = models.ForeignKey(
        FeedPurchase,
        on_delete=models.PROTECT,
        related_name='container_stocks',
        help_text="Original purchase batch this stock comes from"
    )
    quantity_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Remaining quantity of this feed batch in the container (kg)"
    )
    entry_date = models.DateTimeField(
        help_text="Date and time when this feed batch was added to the container"
    )
    
    class Meta:
        ordering = ['feed_container', 'entry_date']  # FIFO order
        verbose_name = "Feed Container Stock"
        verbose_name_plural = "Feed Container Stocks"
        indexes = [
            models.Index(fields=['feed_container', 'entry_date']),
            models.Index(fields=['feed_purchase']),
        ]
    
    def __str__(self):
        return (
            f"{self.feed_purchase.feed.name} batch {self.feed_purchase.batch_number} "
            f"in {self.feed_container.name}: {self.quantity_kg}kg"
        ) 