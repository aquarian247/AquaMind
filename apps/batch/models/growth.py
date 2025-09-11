"""
GrowthSample model for the batch app.

This model records growth samples taken from a batch within a specific container assignment
to track growth metrics at a point in time.
"""
from django.db import models
import decimal
from decimal import Decimal
from simple_history.models import HistoricalRecords


class GrowthSample(models.Model):
    """
    Growth samples taken from a batch within a specific container assignment
    to track growth metrics at a point in time.
    """
    # Import BatchContainerAssignment here to avoid circular import
    from apps.batch.models.assignment import BatchContainerAssignment
    
    assignment = models.ForeignKey(BatchContainerAssignment, on_delete=models.CASCADE, related_name='growth_samples', help_text="The specific container assignment this sample was taken from")
    sample_date = models.DateField()
    sample_size = models.PositiveIntegerField(help_text="Number of fish sampled")
    avg_weight_g = models.DecimalField(max_digits=10, decimal_places=2, help_text="Average weight (g) calculated from individual measurements if provided, otherwise manually entered.")
    avg_length_cm = models.DecimalField(max_digits=10, decimal_places=2, help_text="Average length (cm) calculated from individual measurements if provided, otherwise manually entered.", null=True, blank=True)
    std_deviation_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Standard deviation of weight (g) calculated from individual measurements if provided.")
    std_deviation_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Standard deviation of length (cm) calculated from individual measurements if provided.")
    min_weight_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum weight in grams")
    max_weight_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum weight in grams")
    condition_factor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Average Condition Factor (K) calculated from individual measurements if provided.")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add history tracking
    history = HistoricalRecords()

    class Meta:
        ordering = ['assignment', '-sample_date']

    def __str__(self):
        return f"Growth sample for Assignment {self.assignment.id} (Batch: {self.assignment.batch.batch_number}) on {self.sample_date}"

    def calculate_condition_factor(self):
        """
        Calculate the condition factor (K) using the formula: K = 100 * weight(g) / length(cm)^3
        Ensures calculation only happens if required fields are present and valid.
        Returns the calculated factor or None.
        """
        try:
            if self.avg_weight_g is not None and self.avg_length_cm is not None and self.avg_length_cm > 0:
                weight = decimal.Decimal(self.avg_weight_g)
                length = decimal.Decimal(self.avg_length_cm)
                k_factor = (100 * weight / (length ** 3)).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
                return k_factor
        except (TypeError, decimal.InvalidOperation, decimal.DivisionByZero):
            pass
        return None

    def save(self, *args, **kwargs):
        """
        Overrides the default save method.

        Automatically calculates the condition_factor using the calculate_condition_factor
        method if it hasn't been explicitly provided and avg_weight_g and avg_length_cm are available.
        """
        if self.condition_factor is None:
            calculated_k = self.calculate_condition_factor()
            if calculated_k is not None:
                self.condition_factor = calculated_k

        super().save(*args, **kwargs)
