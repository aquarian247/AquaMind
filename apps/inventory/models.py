from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Avg

from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container, FeedContainer


class Feed(models.Model):
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
    protein_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Protein content percentage"
    )
    fat_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Fat content percentage"
    )
    carbohydrate_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Carbohydrate content percentage"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Feed"
    
    def __str__(self):
        return f"{self.brand} - {self.name} ({self.get_size_category_display()})"


class FeedPurchase(models.Model):
    """
    Records feed purchase history for inventory tracking.
    """
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name='purchases')
    purchase_date = models.DateField()
    quantity_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)],
        help_text="Amount of feed purchased in kilograms"
    )
    cost_per_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)],
        help_text="Cost per kilogram"
    )
    supplier = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100, blank=True, help_text="Supplier's batch number")
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"{self.feed} - {self.quantity_kg}kg purchased on {self.purchase_date}"


class FeedStock(models.Model):
    """
    Tracks current feed inventory levels in feed containers.
    """
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name='stock_levels')
    feed_container = models.ForeignKey(FeedContainer, on_delete=models.CASCADE, related_name='feed_stocks')
    current_quantity_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Current amount of feed in stock (kg)"
    )
    reorder_threshold_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Threshold for reordering (kg)"
    )
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['feed', 'feed_container']
    
    def __str__(self):
        return f"{self.feed} in {self.feed_container} - {self.current_quantity_kg}kg"
    
    @property
    def needs_reorder(self):
        return self.current_quantity_kg <= self.reorder_threshold_kg


class FeedingEvent(models.Model):
    """
    Records individual feeding events for batches.
    Links to batch, container, and feed type with amounts and calculations.
    """
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='feeding_events')
    batch_assignment = models.ForeignKey(
        BatchContainerAssignment, 
        on_delete=models.PROTECT, 
        related_name='feeding_events',
        help_text="The specific batch-container assignment at time of feeding"
    )
    container = models.ForeignKey(Container, on_delete=models.PROTECT, related_name='feeding_events')
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT, related_name='feeding_events')
    feed_stock = models.ForeignKey(
        FeedStock, 
        on_delete=models.PROTECT, 
        related_name='feeding_events',
        null=True,
        blank=True,
        help_text="The feed stock this feeding was drawn from"
    )
    feeding_date = models.DateField()
    feeding_time = models.TimeField()
    amount_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)],
        help_text="Amount of feed used in kilograms"
    )
    batch_biomass_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Batch biomass at time of feeding in kilograms"
    )
    feeding_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Feeding as percentage of biomass"
    )
    feed_conversion_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Feed Conversion Ratio (FCR)"
    )
    method = models.CharField(
        max_length=50, 
        choices=[('MANUAL', 'Manual'), ('AUTOMATIC', 'Automatic')],
        default='MANUAL'
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='recorded_feeding_events',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-feeding_date', '-feeding_time']
    
    def save(self, *args, **kwargs):
        # Calculate feeding percentage if not provided
        if not self.feeding_percentage and self.batch_biomass_kg and self.amount_kg:
            self.feeding_percentage = (self.amount_kg / self.batch_biomass_kg) * 100
        
        # Update feed stock if specified
        if self.feed_stock and not self._state.adding:
            # Get the original instance
            original = FeedingEvent.objects.get(pk=self.pk)
            # Calculate the difference in amount
            amount_diff = self.amount_kg - original.amount_kg
            # Update stock quantity
            if amount_diff != 0:
                self.feed_stock.current_quantity_kg -= amount_diff
                self.feed_stock.save()
        elif self.feed_stock and self._state.adding:
            # Decrement stock for new feeding events
            self.feed_stock.current_quantity_kg -= self.amount_kg
            self.feed_stock.save()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Feeding for {self.batch} on {self.feeding_date} ({self.amount_kg} kg)"


class BatchFeedingSummary(models.Model):
    """
    Aggregated feeding data for batches over specific periods.
    Helps track FCR and total feed usage over time.
    """
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='feeding_summaries')
    period_start = models.DateField()
    period_end = models.DateField()
    total_feed_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Total feed used in this period (kg)"
    )
    average_biomass_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Average biomass during period (kg)"
    )
    average_feeding_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Average feeding percentage during period"
    )
    feed_conversion_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Feed Conversion Ratio for this period"
    )
    growth_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Biomass growth during period (kg)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['batch', '-period_end']
        verbose_name_plural = "Batch feeding summaries"
        unique_together = ['batch', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.batch} feeding summary {self.period_start} to {self.period_end}"
    
    @classmethod
    def generate_for_batch(cls, batch, start_date, end_date):
        """Generate a feeding summary for a batch in the specified period."""
        # Get all feeding events for this batch in the period
        feeding_events = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=start_date,
            feeding_date__lte=end_date
        )
        
        if not feeding_events.exists():
            return None
        
        # Calculate total feed used
        total_feed = feeding_events.aggregate(total=Sum('amount_kg'))['total'] or 0
        
        # Calculate average biomass (using feeding event biomass records)
        avg_biomass = feeding_events.aggregate(avg=Avg('batch_biomass_kg'))['avg'] or 0
        
        # Calculate average feeding percentage
        avg_feeding_pct = feeding_events.aggregate(avg=Avg('feeding_percentage'))['avg']
        
        # Try to calculate growth (need start and end biomass measurements)
        growth = None
        # Check if we have at least one feeding event at the start and end
        if feeding_events.order_by('feeding_date').exists() and feeding_events.order_by('-feeding_date').exists():
            start_biomass = feeding_events.order_by('feeding_date').first().batch_biomass_kg
            end_biomass = feeding_events.order_by('-feeding_date').first().batch_biomass_kg
            growth = end_biomass - start_biomass
        
        # Calculate FCR if we have growth data
        fcr = None
        if growth and growth > 0:
            fcr = total_feed / growth
        
        # Create or update the summary
        summary, created = cls.objects.update_or_create(
            batch=batch,
            period_start=start_date,
            period_end=end_date,
            defaults={
                'total_feed_kg': total_feed,
                'average_biomass_kg': avg_biomass,
                'average_feeding_percentage': avg_feeding_pct,
                'feed_conversion_ratio': fcr,
                'growth_kg': growth
            }
        )
        
        return summary