"""
Species and LifeCycleStage models for the batch app.

These models define the fish species that are managed in the aquaculture system
and their lifecycle stages (egg, fry, parr, smolt, etc.).
"""
from django.db import models


class Species(models.Model):
    """
    Fish species that are managed in the aquaculture system.
    """
    name = models.CharField(max_length=100, unique=True)
    scientific_name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    optimal_temperature_min = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum optimal temperature in °C"
    )
    optimal_temperature_max = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum optimal temperature in °C"
    )
    optimal_oxygen_min = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum optimal oxygen level in mg/L"
    )
    optimal_ph_min = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum optimal pH level"
    )
    optimal_ph_max = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum optimal pH level"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Species"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LifeCycleStage(models.Model):
    """
    Lifecycle stages of fish in the aquaculture system.
    Examples: egg, alevin, fry, parr, smolt, post-smolt, adult.
    """
    name = models.CharField(max_length=100, unique=True)
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='lifecycle_stages')
    order = models.PositiveSmallIntegerField(help_text="Order in lifecycle (1, 2, 3, etc.)")
    description = models.TextField(blank=True)
    expected_weight_min_g = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum expected weight in grams"
    )
    expected_weight_max_g = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum expected weight in grams"
    )
    expected_length_min_cm = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Minimum expected length in centimeters"
    )
    expected_length_max_cm = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum expected length in centimeters"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['species', 'order']
        unique_together = ['species', 'order']
    
    def __str__(self):
        return f"{self.species.name} - {self.name} (Stage {self.order})"
