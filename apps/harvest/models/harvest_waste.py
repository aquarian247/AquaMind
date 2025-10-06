"""Harvest waste model definition."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class HarvestWaste(models.Model):
    """Represents waste or by-products generated during a harvest."""

    event = models.ForeignKey(
        "harvest.HarvestEvent",
        on_delete=models.CASCADE,
        related_name="waste_entries",
    )
    category = models.CharField(max_length=50)
    weight_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-event__event_date", "category"]

    def __str__(self) -> str:
        return f"HarvestWaste(event={self.event_id}, category={self.category})"
