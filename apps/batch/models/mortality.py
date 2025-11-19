"""
MortalityEvent model for the batch app.

This model records mortality events within a batch, including count, cause, and description.
"""
from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords


class MortalityEvent(models.Model):
    """
    Records mortality events within a batch.
    
    Container-specific mortality tracking via assignment FK ensures precise 
    location granularity and eliminates need for proration in growth calculations.
    """
    # Import Batch here to avoid circular import
    from apps.batch.models.batch import Batch
    from apps.batch.models.assignment import BatchContainerAssignment
    
    MORTALITY_CAUSE_CHOICES = [
        ('DISEASE', 'Disease'),
        ('HANDLING', 'Handling'),
        ('PREDATION', 'Predation'),
        ('ENVIRONMENTAL', 'Environmental'),
        ('UNKNOWN', 'Unknown'),
        ('OTHER', 'Other'),
    ]
    
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='mortality_events')
    assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        related_name='mortality_events',
        null=True,
        blank=True,
        help_text="Container-specific assignment where mortality occurred"
    )
    event_date = models.DateField()
    count = models.PositiveIntegerField(help_text="Number of mortalities")
    biomass_kg = models.DecimalField(max_digits=10, decimal_places=2, help_text="Estimated biomass lost in kg")
    cause = models.CharField(max_length=20, choices=MORTALITY_CAUSE_CHOICES, default='UNKNOWN')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add history tracking
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Mortality events"
    
    def clean(self):
        """Validate that assignment belongs to batch if both are provided."""
        super().clean()
        if self.assignment and self.batch:
            if self.assignment.batch_id != self.batch_id:
                raise ValidationError({
                    'assignment': f'Assignment must belong to batch {self.batch.batch_number}'
                })
    
    def __str__(self):
        if self.assignment:
            return f"Mortality in {self.batch.batch_number} (Container {self.assignment.container.name}) on {self.event_date}: {self.count} fish ({self.get_cause_display()})"
        return f"Mortality in {self.batch.batch_number} on {self.event_date}: {self.count} fish ({self.get_cause_display()})"
