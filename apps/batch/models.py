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
    Note: Batches are no longer directly tied to containers. Instead, use BatchContainerAssignment
    to track batch portions across containers, which allows multiple batches per container and
    portions of batches across different containers.
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
    # Total population count across all containers
    population_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Total biomass across all containers
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2)
    avg_weight_g = models.DecimalField(max_digits=10, decimal_places=2)
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
        # Calculate biomass from population count and average weight if not provided
        if not self.biomass_kg and self.population_count and self.avg_weight_g:
            self.biomass_kg = (self.population_count * self.avg_weight_g) / 1000
        # Calculate average weight from biomass and population count if not provided
        elif not self.avg_weight_g and self.biomass_kg and self.population_count:
            self.avg_weight_g = (self.biomass_kg * 1000) / self.population_count
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


class BatchContainerAssignment(models.Model):
    """
    Tracks which portions of batches are in which containers.
    This enables multiple batches to be in one container and portions of a batch to be in
    multiple containers simultaneously. It also supports tracking of mixed populations.
    """
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='container_assignments')
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='batch_assignments')
    population_count = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2)
    assignment_date = models.DateField()
    is_active = models.BooleanField(default=True, help_text="Whether this assignment is current/active")
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
        # Calculate biomass if not provided but count and weight are available
        if not self.biomass_kg and self.population_count:
            self.biomass_kg = (self.population_count * self.batch.avg_weight_g) / 1000
        super().save(*args, **kwargs)


class BatchComposition(models.Model):
    """
    Tracks the composition of mixed batches.
    When batches are mixed in a container, this model records the percentages
    and relationships between the original source batches and the new mixed batch.
    """
    mixed_batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='components')
    source_batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='mixed_into')
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
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


class BatchTransfer(models.Model):
    """
    Records transfers of fish batches between containers, lifecycle stage transitions,
    batch splits, and batch merges. Enhanced to support multi-population containers and
    mixed batch scenarios.
    """
    TRANSFER_TYPE_CHOICES = [
        ('CONTAINER', 'Container Transfer'),   # Move fish between containers
        ('LIFECYCLE', 'Lifecycle Stage Change'),  # Change stage but not container
        ('SPLIT', 'Batch Split'),            # Divide batch across containers
        ('MERGE', 'Batch Merge'),            # Combine batches in a container
        ('MIXED_TRANSFER', 'Mixed Batch Transfer')  # Transfer mixed population
    ]
    
    source_batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='transfers_out')
    destination_batch = models.ForeignKey(
        Batch, 
        on_delete=models.PROTECT, 
        related_name='transfers_in', 
        null=True, 
        blank=True,
        help_text="Destination batch for merges or new batch for splits; may be null for simple transfers"
    )
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES)
    transfer_date = models.DateField()
    
    # Source/destination assignment entries for tracking specific container assignments
    source_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        related_name='transfers_as_source',
        null=True,  # Allow null for migration purposes
        blank=True,
        help_text="Source batch-container assignment"
    )
    destination_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        related_name='transfers_as_destination',
        null=True,
        blank=True,
        help_text="Destination batch-container assignment"
    )
    
    # Transfer details
    source_count = models.PositiveIntegerField(help_text="Population count before transfer")
    transferred_count = models.PositiveIntegerField(help_text="Number of fish transferred")
    mortality_count = models.PositiveIntegerField(default=0, help_text="Number of mortalities during transfer")
    source_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Biomass before transfer in kg")
    transferred_biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Biomass transferred in kg")
    
    # Lifecycle information
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
    
    # Container information is now derived from source_assignment and destination_assignment
    
    # Was this a mixing of populations (emergency case)?
    is_emergency_mixing = models.BooleanField(
        default=False,
        help_text="Whether this was an emergency mixing of different batches"
    )
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transfer_date', '-created_at']
    
    def __str__(self):
        return f"Transfer {self.get_transfer_type_display()}: {self.source_batch.batch_number} on {self.transfer_date}"


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
