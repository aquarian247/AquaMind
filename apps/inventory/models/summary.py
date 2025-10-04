"""
Batch feeding summary model for the inventory app.
"""
from django.db import models
from django.db.models import Sum, Avg

from apps.batch.models import Batch
from .feeding import FeedingEvent
from apps.inventory.utils import TimestampedModelMixin, DecimalFieldMixin


class ContainerFeedingSummary(TimestampedModelMixin, models.Model):
    """
    Container-level feeding data and FCR calculations.

    Tracks individual container performance for operational intelligence.
    Container FCRs are aggregated to batch level for management reporting.
    """
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='container_feeding_summaries'
    )
    container_assignment = models.ForeignKey(
        'batch.BatchContainerAssignment',
        on_delete=models.CASCADE,
        related_name='feeding_summaries'
    )
    period_start = models.DateField(help_text="Start date of the summary period")
    period_end = models.DateField(help_text="End date of the summary period")

    # Feed data
    total_feed_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Total feed used in this container during the period (kg)"
    )

    # Biomass and growth data
    starting_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Biomass at start of period (kg)"
    )
    ending_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Biomass at end of period (kg)"
    )
    growth_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Growth during the period (kg)"
    )

    # FCR calculation
    fcr = DecimalFieldMixin.positive_decimal_field(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Feed Conversion Ratio for this container (total_feed_kg / growth_kg)"
    )

    # Confidence and quality indicators
    confidence_level = models.CharField(
        max_length=20,
        choices=[
            ('VERY_HIGH', 'Very High (< 10 days since weighing)'),
            ('HIGH', 'High (10-20 days since weighing)'),
            ('MEDIUM', 'Medium (20-40 days since weighing)'),
            ('LOW', 'Low (> 40 days since weighing)'),
        ],
        default='MEDIUM',
        help_text="Confidence level based on time since last weighing"
    )
    estimation_method = models.CharField(
        max_length=20,
        choices=[
            ('MEASURED', 'Direct measurement from weighing events'),
            ('INTERPOLATED', 'Estimated from growth trends between weighings'),
        ],
        null=True,
        blank=True,
        help_text="How the FCR value was calculated"
    )

    # Metadata
    data_points = models.PositiveIntegerField(
        default=0,
        help_text="Number of feeding events contributing to this summary"
    )

    class Meta:
        ordering = ['container_assignment', '-period_end']
        verbose_name_plural = "Container feeding summaries"
        unique_together = ['container_assignment', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['batch', 'period_start', 'period_end']),
            models.Index(fields=['container_assignment', 'period_start']),
        ]

    def __str__(self):
        return (
            f"{self.container_assignment} feeding summary: "
            f"{self.period_start} to {self.period_end}"
        )

    @property
    def container_name(self):
        """Get container name for display purposes."""
        return self.container_assignment.container.name


class BatchFeedingSummary(TimestampedModelMixin, models.Model):
    """
    Aggregated feeding data for batches over specific periods.

    Now calculated as weighted average of container-level FCRs for operational intelligence.
    This provides management-level summaries while enabling drill-down to container performance.
    """
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='feeding_summaries'
    )
    period_start = models.DateField(help_text="Start date of the summary period")
    period_end = models.DateField(help_text="End date of the summary period")

    # Aggregated feed data
    total_feed_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Total feed used across all containers (kg)"
    )
    average_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Average biomass of the batch during this period (kg)"
    )
    average_feeding_percentage = DecimalFieldMixin.percentage_field(
        null=True,
        blank=True,
        help_text="Average feeding percentage across containers"
    )

    # Aggregated biomass and growth
    total_starting_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Total batch biomass at start of period (kg)"
    )
    total_ending_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Total batch biomass at end of period (kg)"
    )
    total_growth_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Total batch growth during the period (kg)"
    )

    # Weighted FCR calculation
    weighted_avg_fcr = DecimalFieldMixin.positive_decimal_field(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weighted average FCR across all containers"
    )

    # Legacy FCR field (kept for backward compatibility)
    fcr = DecimalFieldMixin.positive_decimal_field(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="DEPRECATED: Use weighted_avg_fcr instead"
    )

    # Aggregation metadata
    container_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of containers contributing to this summary"
    )
    total_feed_consumed_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Total feed consumed (same as total_feed_kg for consistency)"
    )
    total_biomass_gain_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Total biomass gain (same as total_growth_kg for consistency)"
    )

    # Overall confidence and quality indicators
    overall_confidence_level = models.CharField(
        max_length=20,
        choices=[
            ('VERY_HIGH', 'Very High (< 10 days since weighing)'),
            ('HIGH', 'High (10-20 days since weighing)'),
            ('MEDIUM', 'Medium (20-40 days since weighing)'),
            ('LOW', 'Low (> 40 days since weighing)'),
        ],
        default='MEDIUM',
        help_text="Overall confidence level (worst case across containers)"
    )
    estimation_method = models.CharField(
        max_length=20,
        choices=[
            ('MEASURED', 'All containers have direct measurements'),
            ('MIXED', 'Some containers use interpolation'),
            ('INTERPOLATED', 'Most containers use interpolation'),
        ],
        null=True,
        blank=True,
        help_text="Overall estimation method across containers"
    )

    class Meta:
        ordering = ['batch', '-period_end']
        verbose_name_plural = "Batch feeding summaries"
        unique_together = ['batch', 'period_start', 'period_end']

    def __str__(self):
        return (
            f"{self.batch} feeding summary: {self.period_start} to {self.period_end}"
        )

    @classmethod
    def generate_for_batch(cls, batch, start_date, end_date):
        """
        Generate a feeding summary for a batch in the specified period.

        Args:
            batch: The Batch instance to generate a summary for
            start_date: The start date of the period (inclusive)
            end_date: The end date of the period (inclusive)

        Returns:
            BatchFeedingSummary instance or None if no feeding events exist
        """
        # Get feeding events in the period
        feeding_events = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=start_date,
            feeding_date__lte=end_date
        )

        # If no events, return None
        if not feeding_events.exists():
            return None

        # Calculate total feed
        total_feed = feeding_events.aggregate(total=Sum('amount_kg'))['total'] or 0

        # Calculate average biomass
        avg_biomass = feeding_events.aggregate(avg=Avg('batch_biomass_kg'))['avg']

        # Calculate average feeding percentage
        avg_feeding_pct = feeding_events.aggregate(
            avg=Avg('feeding_percentage')
        )['avg']

        # Try to calculate growth (need start and end biomass measurements)
        growth = None
        # Check if we have at least one feeding event at the start and end
        if (feeding_events.order_by('feeding_date').exists() and 
                feeding_events.order_by('-feeding_date').exists()):
            start_biomass = (
                feeding_events.order_by('feeding_date').first().batch_biomass_kg
            )
            end_biomass = (
                feeding_events.order_by('-feeding_date').first().batch_biomass_kg
            )
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
                'total_growth_kg': growth,
                # Use the more precise fcr field
                'total_feed_consumed_kg': total_feed,
                'total_biomass_gain_kg': growth,
                'fcr': fcr
            }
        )

        return summary
