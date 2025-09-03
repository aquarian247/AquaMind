"""
BatchContainerAssignment model for the batch app.

This model tracks which portions of batches are in which containers,
enabling multiple batches per container and portions of a batch to be in
multiple containers simultaneously.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.batch.models.species import LifeCycleStage
from apps.infrastructure.models import Container


class BatchContainerAssignment(models.Model):
    """
    Tracks which portions of batches are in which containers.
    This enables multiple batches to be in one container and portions of a batch to be in
    multiple containers simultaneously. It also supports tracking of mixed populations.
    It explicitly tracks the lifecycle stage for the fish in this specific assignment.
    """
    # Import Batch here to avoid circular import
    from apps.batch.models.batch import Batch
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='batch_assignments')
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='container_assignments')
    lifecycle_stage = models.ForeignKey(LifeCycleStage, on_delete=models.PROTECT, related_name='container_assignments')
    population_count = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    avg_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average weight in grams per fish at the time of this specific assignment or update."
    )
    biomass_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total biomass in kilograms. Calculated if population_count and avg_weight_g are provided."
    )
    assignment_date = models.DateField()
    departure_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this specific assignment ended (e.g., fish moved out or population became zero)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this assignment is current/active")
    last_weighing_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the most recent growth sample (weighing) for this assignment"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-assignment_date']
        constraints = [
            models.UniqueConstraint(
                fields=['batch', 'container'],
                condition=models.Q(is_active=True),
                name='unique_active_batch_container'
            )
        ]
    
    def __str__(self):
        return f"{self.batch.batch_number} in {self.container.name} ({self.population_count} fish)"
    
    def save(self, *args, **kwargs):
        """
        Overrides the default save method.

        Calculates biomass_kg if population_count and avg_weight_g are provided.
        """
        if self.population_count is not None and self.avg_weight_g is not None and self.avg_weight_g > Decimal('0'):
            self.biomass_kg = (Decimal(str(self.population_count)) * Decimal(str(self.avg_weight_g))) / Decimal('1000')
        else:
            # Ensure biomass_kg is set, especially for new instances if avg_weight_g is not provided
            # or if population is zero, to avoid NOT NULL constraint violations if the field isn't already set.
            if not hasattr(self, 'biomass_kg') or self.biomass_kg is None:
                 self.biomass_kg = Decimal('0.00')
        
        super().save(*args, **kwargs)
