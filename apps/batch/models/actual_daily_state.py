"""
ActualDailyAssignmentState model for batch growth assimilation - Issue #112.

This model stores the computed daily state for each batch-container assignment,
including actual weight, population, biomass, and provenance information.

Designed as a TimescaleDB hypertable for efficient time-series storage and querying.
Falls back to regular PostgreSQL table when TimescaleDB is unavailable.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class ActualDailyAssignmentState(models.Model):
    """
    Daily computed state for a batch-container assignment.
    
    This hypertable stores the day-by-day actual state computed by assimilating:
    - Growth samples (anchor points)
    - Measured weights from transfers/vaccinations
    - TGC-based growth calculations
    - Actual temperature, mortality, and feed data
    
    Provenance tracking ensures transparency about data sources and confidence.
    """
    
    # Import here to avoid circular dependency
    from apps.batch.models.assignment import BatchContainerAssignment
    from apps.batch.models.batch import Batch
    from apps.batch.models.species import LifeCycleStage
    from apps.infrastructure.models import Container
    
    # Note: id is still the primary key, but TimescaleDB will partition on date
    # This allows the model to work as both a hypertable and regular table
    
    # Relationships
    assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.CASCADE,
        related_name='daily_states',
        db_index=True,
        help_text="Batch-container assignment this state belongs to"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='daily_states',
        db_index=True,
        help_text="Batch (denormalized for efficient querying)"
    )
    container = models.ForeignKey(
        Container,
        on_delete=models.CASCADE,
        related_name='daily_states',
        db_index=True,
        help_text="Container (denormalized for efficient querying)"
    )
    lifecycle_stage = models.ForeignKey(
        LifeCycleStage,
        on_delete=models.PROTECT,
        related_name='daily_states',
        help_text="Lifecycle stage on this date"
    )
    
    # Time dimension (partition key for TimescaleDB)
    date = models.DateField(
        db_index=True,
        help_text="The date for this daily state"
    )
    day_number = models.PositiveIntegerField(
        help_text="Days since batch start (1, 2, 3, ...)"
    )
    
    # Computed metrics
    avg_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Computed average weight in grams"
    )
    population = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Computed population count"
    )
    biomass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Computed biomass in kilograms (population * avg_weight / 1000)"
    )
    
    # Environmental and operational data
    temp_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Temperature in Celsius (measured, interpolated, or from profile)"
    )
    mortality_count = models.PositiveIntegerField(
        default=0,
        help_text="Daily mortality count (actual or modeled)"
    )
    feed_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Daily feed in kilograms (actual or none)"
    )
    observed_fcr = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Observed Feed Conversion Ratio (if calculable)"
    )
    
    # Anchor type (if this day is an anchor point)
    ANCHOR_TYPE_CHOICES = [
        ('growth_sample', 'Growth Sample'),
        ('transfer', 'Transfer with Measured Weight'),
        ('vaccination', 'Vaccination with Weighing'),
        ('manual', 'Manual Admin Anchor'),
    ]
    
    anchor_type = models.CharField(
        max_length=20,
        choices=ANCHOR_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Type of anchor if this is an anchor point"
    )
    
    # Provenance (JSON fields for transparency)
    sources = models.JSONField(
        default=dict,
        help_text="Data sources for each component (temp: measured|interpolated|profile, weight: measured|tgc_computed, etc.)"
    )
    confidence_scores = models.JSONField(
        default=dict,
        help_text="Confidence scores (0-1) for each component based on data quality and recency"
    )
    
    # Metadata
    last_computed_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this state was last computed"
    )
    
    class Meta:
        db_table = 'batch_actualdailyassignmentstate'
        # Composite unique constraint: one state per assignment per date
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'date'],
                name='unique_assignment_date'
            )
        ]
        # Indexes for efficient querying
        indexes = [
            models.Index(fields=['assignment', 'date'], name='idx_assignment_date'),
            models.Index(fields=['batch', 'date'], name='idx_batch_date'),
            models.Index(fields=['date'], name='idx_date'),
            models.Index(fields=['anchor_type'], name='idx_anchor_type'),
        ]
        ordering = ['date']
        verbose_name = 'Actual Daily Assignment State'
        verbose_name_plural = 'Actual Daily Assignment States'
    
    def __str__(self):
        return f"{self.assignment.batch.batch_number} - {self.container.name} - Day {self.day_number} ({self.date})"
    
    @property
    def confidence_overall(self):
        """Calculate overall confidence as minimum of all confidence scores."""
        if not self.confidence_scores:
            return 0.0
        return min(self.confidence_scores.values()) if self.confidence_scores else 0.0
    
    @property
    def days_since_anchor(self):
        """Calculate days since last anchor point (for this assignment)."""
        # This would need to query backwards to find the last anchor
        # Implementation deferred to Phase 3 (computation engine)
        return None

