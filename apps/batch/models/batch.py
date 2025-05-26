"""
Batch model for the batch app.

The Batch model represents fish batches that are tracked through their lifecycle.
"""
from django.db import models
from decimal import Decimal
from django.db.models import Sum, F

from apps.batch.models.species import Species, LifeCycleStage
from apps.infrastructure.models import Container


class Batch(models.Model):
    """
    Fish batches that are tracked through their lifecycle.
    Note: Batches are no longer directly tied to containers. Instead, use BatchContainerAssignment
    to track batch portions across containers, which allows multiple batches per container and
    portions of batches across different containers simultaneously. It also supports tracking of mixed populations.
    """
    BATCH_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
    ]
    
    BATCH_TYPE_CHOICES = [
        ('STANDARD', 'Standard'),
        ('MIXED', 'Mixed Population'),
    ]
    
    batch_number = models.CharField(max_length=50, unique=True)
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name='batches')
    lifecycle_stage = models.ForeignKey(LifeCycleStage, on_delete=models.PROTECT, related_name='batches')
    status = models.CharField(max_length=20, choices=BATCH_STATUS_CHOICES, default='ACTIVE')
    batch_type = models.CharField(max_length=20, choices=BATCH_TYPE_CHOICES, default='STANDARD')
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        batch_type_str = " (Mixed)" if self.batch_type == "MIXED" else ""
        return f"Batch {self.batch_number} - {self.species.name} ({self.lifecycle_stage.name}){batch_type_str}"
    
    def save(self, *args, **kwargs):
        """
        Overrides the default save method.
        (Original calculation logic removed as these fields are now properties)
        """
        super().save(*args, **kwargs)
        
    @property
    def containers(self):
        """Return all containers this batch is currently in"""
        return Container.objects.filter(
            batchcontainerassignment__batch=self,
            batchcontainerassignment__is_active=True
        ).distinct()
    
    @property
    def is_mixed(self):
        """Check if this batch is a mixed population"""
        return self.batch_type == 'MIXED'
        
    @property
    def component_batches(self):
        """Get the original component batches if this is a mixed batch"""
        if not self.is_mixed:
            return []
        return [comp.source_batch for comp in self.components.all()]

    @property
    def calculated_population_count(self):
        """Calculates total population from active assignments."""
        # Ensure we are summing from BatchContainerAssignment model
        # Assuming 'container_assignments' is the related_name from Batch to BatchContainerAssignment
        return self.batch_assignments.filter(is_active=True).aggregate(
            total_pop=Sum('population_count')
        )['total_pop'] or 0

    @property
    def calculated_avg_weight_g(self):
        """Calculates the weighted average weight from active assignments."""
        active_assignments = self.batch_assignments.filter(is_active=True, population_count__gt=0, avg_weight_g__isnull=False)
        
        # Calculate Sum(population_count * avg_weight_g)
        total_weighted_sum_result = active_assignments.aggregate(
            weighted_sum=Sum(F('population_count') * F('avg_weight_g'))
        )
        total_weighted_sum = total_weighted_sum_result['weighted_sum']
        
        # Calculate Sum(population_count)
        total_population_result = active_assignments.aggregate(
            total_pop=Sum('population_count')
        )
        total_population = total_population_result['total_pop']

        if total_population and total_weighted_sum is not None and total_population > 0:
            return Decimal(total_weighted_sum) / Decimal(total_population)
        return Decimal('0.00')

    @property
    def calculated_biomass_kg(self):
        """Calculates total biomass from calculated population and average weight."""
        pop_count = self.calculated_population_count
        avg_w = self.calculated_avg_weight_g
        # Ensure avg_w is compared appropriately, it will be Decimal('0.00') if no assignments
        if pop_count > 0 and avg_w > Decimal('0.00'):
            return (Decimal(pop_count) * Decimal(avg_w)) / Decimal(1000)
        return Decimal('0.00')
