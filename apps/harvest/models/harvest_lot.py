"""Harvest lot model definition."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class HarvestLot(models.Model):
    """Represents graded output from a harvest event."""

    event = models.ForeignKey(
        "harvest.HarvestEvent",
        on_delete=models.CASCADE,
        related_name="lots",
    )
    product_grade = models.ForeignKey(
        "harvest.ProductGrade",
        on_delete=models.PROTECT,
        related_name="lots",
    )
    live_weight_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
    )
    gutted_weight_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    fillet_weight_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    unit_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-event__event_date", "product_grade__code"]

    def __str__(self) -> str:
        """Return string representation for admin and logs."""

        return f"HarvestLot(event={self.event_id}, grade={self.product_grade_id})"
