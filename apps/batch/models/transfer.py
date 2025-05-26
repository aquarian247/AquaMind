"""
BatchTransfer model for the batch app.

This model records transfers of fish batches between containers, lifecycle stage transitions,
batch splits, and batch merges.
"""
from django.db import models, transaction
from apps.batch.models.species import LifeCycleStage


class BatchTransfer(models.Model):
    """
    Records transfers of fish batches between containers, lifecycle stage transitions,
    batch splits, and batch merges. Enhanced to support multi-population containers and
    mixed batch scenarios.
    """
    # Import Batch and BatchContainerAssignment here to avoid circular import
    from apps.batch.models.batch import Batch
    from apps.batch.models.assignment import BatchContainerAssignment
    
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
                from apps.batch.models.assignment import BatchContainerAssignment
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
