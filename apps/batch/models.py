from django.db import models, transaction
from django.db.models import Sum, F
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.infrastructure.models import Container, Area, Hall
import decimal

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


class BatchContainerAssignment(models.Model):
    """
    Tracks which portions of batches are in which containers.
    This enables multiple batches to be in one container and portions of a batch to be in
    multiple containers simultaneously. It also supports tracking of mixed populations.
    It explicitly tracks the lifecycle stage for the fish in this specific assignment.
    """
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

    def save(self, *args, **kwargs):

        # We are interested in logic that runs when a new transfer is created.
        is_new = self.pk is None
        super().save(*args, **kwargs) # Save first to get a PK if new, and ensure data is valid.

        if is_new and self.source_assignment:
            with transaction.atomic():
                # Lock the source_assignment row to prevent race conditions if multiple transfers happen.
                # Note: select_for_update() needs to be called on a queryset.
                assignment_to_update = BatchContainerAssignment.objects.select_for_update().get(pk=self.source_assignment.pk)
                
                # Reduce population from source assignment
                reduction = self.transferred_count + (self.mortality_count or 0)
                assignment_to_update.population_count -= reduction
                
                if assignment_to_update.population_count <= 0:
                    assignment_to_update.population_count = 0 # Ensure it doesn't go negative
                    if not assignment_to_update.departure_date: # Only set if not already set
                        assignment_to_update.departure_date = self.transfer_date
                    assignment_to_update.is_active = False
                
                assignment_to_update.save()



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
    Growth samples taken from a batch within a specific container assignment
    to track growth metrics at a point in time.
    """
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
