"""
BatchComposition model for the batch app.

This model tracks the composition of mixed batches, recording the percentages
and relationships between the original source batches and the new mixed batch.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class BatchComposition(models.Model):
    """
    Tracks the composition of mixed batches.
    When batches are mixed in a container, this model records the percentages
    and relationships between the original source batches and the new mixed batch.
    """
    # Import Batch here to avoid circular import
    from apps.batch.models.batch import Batch
    
    mixed_batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='components')
    source_batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='mixed_into')
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage of this source batch in the mixed batch"
    )
    population_count = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Number of fish from this source batch in the mixed batch"
    )
    biomass_kg = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Biomass from this source batch in the mixed batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-percentage']
        verbose_name_plural = "Batch compositions"
    
    def __str__(self):
        return f"{self.source_batch.batch_number} ({self.percentage}%) in {self.mixed_batch.batch_number}"
