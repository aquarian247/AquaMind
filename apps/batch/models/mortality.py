"""
MortalityEvent model for the batch app.

This model records mortality events within a batch, including count, cause, and description.
"""
from django.db import models
from simple_history.models import HistoricalRecords


class MortalityEvent(models.Model):
    """
    Records mortality events within a batch.
    """
    # Import Batch here to avoid circular import
    from apps.batch.models.batch import Batch
    
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

    # Add history tracking
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Mortality events"
    
    def __str__(self):
        return f"Mortality in {self.batch.batch_number} on {self.event_date}: {self.count} fish ({self.get_cause_display()})"
