from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.infrastructure.models import Container, Area, Hall


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


class Batch(models.Model):
    """
    Fish batches that are tracked through their lifecycle.
    """
    BATCH_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
    ]
    
    batch_number = models.CharField(max_length=50, unique=True)
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name='batches')
    lifecycle_stage = models.ForeignKey(LifeCycleStage, on_delete=models.PROTECT, related_name='batches')
    container = models.ForeignKey(Container, on_delete=models.PROTECT, related_name='batches')
    status = models.CharField(max_length=20, choices=BATCH_STATUS_CHOICES, default='ACTIVE')
    population_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2)
    avg_weight_g = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Batch {self.batch_number} - {self.species.name} ({self.lifecycle_stage.name})"
    
    def save(self, *args, **kwargs):
        # Calculate biomass from population count and average weight if not provided
        if not self.biomass_kg and self.population_count and self.avg_weight_g:
            self.biomass_kg = (self.population_count * self.avg_weight_g) / 1000
        # Calculate average weight from biomass and population count if not provided
        elif not self.avg_weight_g and self.biomass_kg and self.population_count:
            self.avg_weight_g = (self.biomass_kg * 1000) / self.population_count
        super().save(*args, **kwargs)


class BatchTransfer(models.Model):
    """
    Records transfers of fish batches between containers, or lifecycle stage transitions.
    """
    TRANSFER_TYPE_CHOICES = [
        ('CONTAINER', 'Container Transfer'),
        ('LIFECYCLE', 'Lifecycle Stage Change'),
        ('SPLIT', 'Batch Split'),
        ('MERGE', 'Batch Merge'),
    ]
    
    source_batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='transfers_out')
    destination_batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='transfers_in', null=True, blank=True)
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES)
    transfer_date = models.DateField()
    source_count = models.PositiveIntegerField(help_text="Population count before transfer")
    transferred_count = models.PositiveIntegerField(help_text="Number of fish transferred")
    mortality_count = models.PositiveIntegerField(default=0, help_text="Number of mortalities during transfer")
    source_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Biomass before transfer in kg")
    transferred_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Biomass transferred in kg")
    source_lifecycle_stage = models.ForeignKey(
        LifeCycleStage, 
        on_delete=models.PROTECT, 
        related_name='transfers_as_source',
        help_text="Lifecycle stage before transfer"
    )
    destination_lifecycle_stage = models.ForeignKey(
        LifeCycleStage, 
        on_delete=models.PROTECT, 
        related_name='transfers_as_destination',
        null=True, 
        blank=True,
        help_text="New lifecycle stage after transfer"
    )
    source_container = models.ForeignKey(
        Container, 
        on_delete=models.PROTECT, 
        related_name='transfers_as_source',
        help_text="Container before transfer"
    )
    destination_container = models.ForeignKey(
        Container, 
        on_delete=models.PROTECT, 
        related_name='transfers_as_destination',
        null=True, 
        blank=True,
        help_text="New container after transfer"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Transfer {self.transfer_type}: {self.source_batch.batch_number} on {self.transfer_date}"


class MortalityEvent(models.Model):
    """
    Records mortality events within a batch.
    """
    MORTALITY_CAUSE_CHOICES = [
        ('DISEASE', 'Disease'),
        ('HANDLING', 'Handling'),
        ('PREDATION', 'Predation'),
        ('ENVIRONMENTAL', 'Environmental'),
        ('UNKNOWN', 'Unknown'),
        ('OTHER', 'Other'),
    ]
    
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='mortality_events')
    event_date = models.DateField()
    count = models.PositiveIntegerField(help_text="Number of mortalities")
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Estimated biomass lost in kg")
    cause = models.CharField(max_length=20, choices=MORTALITY_CAUSE_CHOICES, default='UNKNOWN')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Mortality events"
    
    def __str__(self):
        return f"Mortality in {self.batch.batch_number} on {self.event_date}: {self.count} fish ({self.get_cause_display()})"


class GrowthSample(models.Model):
    """
    Growth samples taken from a batch to track growth metrics.
    """
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='growth_samples')
    sample_date = models.DateField()
    sample_size = models.PositiveIntegerField(help_text="Number of fish sampled")
    avg_weight_g = models.DecimalField(max_digits=10, decimal_places=2, help_text="Average weight in grams")
    avg_length_cm = models.DecimalField(max_digits=10, decimal_places=2, help_text="Average length in centimeters", null=True, blank=True)
    std_deviation_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Standard deviation of weight")
    std_deviation_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Standard deviation of length")
    min_weight_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum weight in grams")
    max_weight_g = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum weight in grams")
    condition_factor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Condition factor (K)")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['batch', '-sample_date']
    
    def __str__(self):
        return f"Growth sample for {self.batch.batch_number} on {self.sample_date}"
    
    def calculate_condition_factor(self):
        """
        Calculate the condition factor (K) using the formula: K = 100 * weight(g) / length(cm)^3
        """
        if self.avg_weight_g and self.avg_length_cm and self.avg_length_cm > 0:
            self.condition_factor = 100 * self.avg_weight_g / (self.avg_length_cm ** 3)
        return self.condition_factor
    
    def save(self, *args, **kwargs):
        # Calculate condition factor if not provided
        if not self.condition_factor and self.avg_weight_g and self.avg_length_cm:
            self.calculate_condition_factor()
        super().save(*args, **kwargs)
