"""
Feeding event model for the inventory app.
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container
from .feed import Feed
from .stock import FeedStock
from apps.inventory.utils import TimestampedModelMixin, DecimalFieldMixin, validate_stock_quantity, calculate_feeding_percentage


class FeedingEvent(TimestampedModelMixin, models.Model):
    """
    Records individual feeding events for batches.
    Links to batch, container, and feed type with amounts and calculations.
    """
    FEEDING_METHOD_CHOICES = [
        ('MANUAL', 'Manual'),
        ('AUTOMATIC', 'Automatic Feeder'),
        ('BROADCAST', 'Broadcast'),
    ]
    
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='feeding_events')
    batch_assignment = models.ForeignKey(
        BatchContainerAssignment, 
        on_delete=models.PROTECT, 
        related_name='feeding_events',
        null=True,
        blank=True,
        help_text="The specific batch-container assignment this feeding applies to"
    )
    container = models.ForeignKey(
        Container, 
        on_delete=models.PROTECT, 
        related_name='feeding_events',
        help_text="Container where feeding occurred"
    )
    feed = models.ForeignKey(
        Feed, 
        on_delete=models.PROTECT, 
        related_name='feeding_events',
        help_text="Feed type used"
    )
    feed_stock = models.ForeignKey(
        FeedStock, 
        on_delete=models.SET_NULL, 
        related_name='feeding_events',
        null=True,
        blank=True,
        help_text="Stock source for this feed"
    )
    feeding_date = models.DateField()
    feeding_time = models.TimeField()
    amount_kg = DecimalFieldMixin.positive_decimal_field(
        min_value=0.01,
        help_text="Amount of feed used in kilograms"
    )
    batch_biomass_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Estimated batch biomass at time of feeding (kg)"
    )
    feeding_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Feed amount as percentage of biomass"
    )
    feed_conversion_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated FCR for this feeding event"
    )
    method = models.CharField(
        max_length=20, 
        choices=FEEDING_METHOD_CHOICES, 
        default='MANUAL'
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-feeding_date', '-feeding_time']
    
    def calculate_feeding_percentage(self):
        """
        Calculate feeding percentage based on amount and batch biomass.
        
        Returns:
            Feeding percentage as a Decimal, or None if biomass is not available
        """
        if not self.batch or not hasattr(self.batch, 'biomass_kg') or not self.batch.biomass_kg:
            return None
        
        return calculate_feeding_percentage(self.amount_kg, self.batch.biomass_kg)
    
    def validate_stock_quantity(self):
        """
        Validate that there is enough stock for this feeding event.
        
        Returns:
            True if valid, False otherwise
        """
        return validate_stock_quantity(self.feed_stock, self.amount_kg)
    
    def save(self, *args, **kwargs):
        """
        Override save to calculate feeding percentage and update feed stock.
        """
        # Calculate feeding percentage if biomass is provided
        self.feeding_percentage = self.calculate_feeding_percentage()
        
        # Update feed stock if provided
        if self.feed_stock and hasattr(self, '_original_amount_kg'):
            # If this is an update, restore the original amount to the stock first
            if self._original_amount_kg:
                self.feed_stock.current_quantity_kg += self._original_amount_kg
            
            # Subtract the new amount
            self.feed_stock.current_quantity_kg -= self.amount_kg
            self.feed_stock.save()
        elif self.feed_stock:
            # For new records, just subtract the amount
            self.feed_stock.current_quantity_kg -= self.amount_kg
            self.feed_stock.save()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.feed} for {self.batch} on {self.feeding_date} ({self.amount_kg} kg)"
