"""
IndividualGrowthObservation model for the batch app.

This model records measurements for individual fish sampled during
growth sampling, enabling detailed tracking and statistical analysis of
growth patterns.
"""
from django.db import models
from simple_history.models import HistoricalRecords


class IndividualGrowthObservation(models.Model):
    """Records measurements for a single fish in a growth sample."""
    # Import GrowthSample here to avoid circular import
    from apps.batch.models.growth import GrowthSample

    growth_sample = models.ForeignKey(
        GrowthSample,
        on_delete=models.CASCADE,
        related_name='individual_observations',
        help_text="The growth sample this observation belongs to."
    )
    fish_identifier = models.CharField(
        max_length=50,
        help_text="Identifier for the fish (e.g., sequential number)."
    )
    weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Weight in grams."
    )
    length_cm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Length in centimeters."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = [['growth_sample', 'fish_identifier']]
        ordering = ['growth_sample', 'fish_identifier']
        verbose_name = "Individual Growth Observation"
        verbose_name_plural = "Individual Growth Observations"

    def __str__(self):
        """
        Return a string representation of the individual growth
        observation.
        """
        sample_id = self.growth_sample.id
        return f"Fish #{self.fish_identifier} (Sample: {sample_id})"

