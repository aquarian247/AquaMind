"""
Batch feeding summary model for the inventory app.
"""
from django.db import models
from django.db.models import Sum, Avg

from apps.batch.models import Batch
from .feeding import FeedingEvent
from apps.inventory.utils import TimestampedModelMixin, DecimalFieldMixin


class BatchFeedingSummary(TimestampedModelMixin, models.Model):
    """
    Aggregated feeding data for batches over specific periods.
    Helps track FCR and total feed usage over time.
    """
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.CASCADE, 
        related_name='feeding_summaries'
    )
    period_start = models.DateField(help_text="Start date of the summary period")
    period_end = models.DateField(help_text="End date of the summary period")
    total_feed_kg = DecimalFieldMixin.positive_decimal_field(
        help_text="Total feed used in kg during the period"
    )
    average_biomass_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Average batch biomass during the period (kg)"
    )
    average_feeding_percentage = DecimalFieldMixin.percentage_field(
        null=True,
        blank=True,
        help_text="Average feeding percentage during the period"
    )
    feed_conversion_ratio = DecimalFieldMixin.positive_decimal_field(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Feed Conversion Ratio for the period"
    )
    growth_kg = DecimalFieldMixin.positive_decimal_field(
        null=True,
        blank=True,
        help_text="Growth during the period (kg)"
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
                'feed_conversion_ratio': fcr,
                'growth_kg': growth
            }
        )

        return summary
