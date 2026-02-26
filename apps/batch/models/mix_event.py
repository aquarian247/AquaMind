"""
Mix event models for container-scoped batch mixing.

These models capture physical mixing events at container level and preserve
traceability of source assignment contributions.
"""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class BatchMixEvent(models.Model):
    """
    Container-scoped event describing when fish were physically mixed.
    """

    mixed_batch = models.ForeignKey(
        "batch.Batch",
        on_delete=models.CASCADE,
        related_name="mix_events",
        help_text="Resulting mixed batch created/updated by this mix event.",
    )
    container = models.ForeignKey(
        "infrastructure.Container",
        on_delete=models.PROTECT,
        related_name="mix_events",
        help_text="Container where mixing physically occurred.",
    )
    workflow_action = models.ForeignKey(
        "batch.TransferAction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mix_events",
        help_text="Transfer action that triggered this mix, when applicable.",
    )
    mixed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-mixed_at", "-id"]
        indexes = [
            models.Index(fields=["mixed_batch", "mixed_at"]),
            models.Index(fields=["container", "mixed_at"]),
        ]

    def __str__(self):
        return (
            f"MixEvent #{self.id} in {self.container.name} "
            f"for {self.mixed_batch.batch_number} at {self.mixed_at}"
        )


class BatchMixEventComponent(models.Model):
    """
    Source contribution for a container-scoped mix event.
    """

    mix_event = models.ForeignKey(
        BatchMixEvent,
        on_delete=models.CASCADE,
        related_name="components",
    )
    source_assignment = models.ForeignKey(
        "batch.BatchContainerAssignment",
        on_delete=models.PROTECT,
        related_name="mix_event_components",
        help_text="Assignment contributing fish to this mix event.",
    )
    source_batch = models.ForeignKey(
        "batch.Batch",
        on_delete=models.PROTECT,
        related_name="mix_event_contributions",
        help_text="Batch identity for this component (snapshot for analytics).",
    )
    population_count = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Fish count contributed from this source.",
    )
    biomass_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Biomass contributed from this source in kilograms.",
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Percentage share of total mixed population at event time.",
    )
    is_transferred_in = models.BooleanField(
        default=False,
        help_text="True when this component came from the action's transferred fish.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-population_count", "-id"]
        indexes = [
            models.Index(fields=["mix_event", "source_batch"]),
            models.Index(fields=["source_assignment"]),
        ]

    def clean(self):
        super().clean()
        if self.source_assignment_id and self.source_batch_id:
            if self.source_assignment.batch_id != self.source_batch_id:
                raise ValidationError(
                    {"source_batch": "source_batch must match source_assignment.batch"}
                )

    def __str__(self):
        return (
            f"{self.source_batch.batch_number}: {self.population_count} fish "
            f"({self.percentage}%) in mix event #{self.mix_event_id}"
        )
