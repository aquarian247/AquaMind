"""Harvest event model definition."""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.users.models import Subsidiary


class HarvestEvent(models.Model):
    """Represents an operational harvest event."""

    event_date = models.DateTimeField(db_index=True)
    batch = models.ForeignKey(
        "batch.Batch",
        on_delete=models.PROTECT,
        related_name="harvest_events",
    )
    assignment = models.ForeignKey(
        "batch.BatchContainerAssignment",
        on_delete=models.PROTECT,
        related_name="harvest_events",
    )
    dest_geography = models.ForeignKey(
        "infrastructure.Geography",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="destination_harvest_events",
    )
    dest_subsidiary = models.CharField(
        max_length=3,
        choices=Subsidiary.choices,
        null=True,
        blank=True,
    )
    document_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-event_date", "batch_id"]
        indexes = [
            models.Index(fields=["event_date", "batch"]),
            models.Index(fields=["dest_subsidiary"]),
        ]

    def __str__(self) -> str:
        """Return string representation for admin and logs."""

        batch_number = getattr(self.batch, "batch_number", self.batch_id)
        timestamp = self.event_date.strftime("%Y-%m-%d %H:%M")
        return f"HarvestEvent({batch_number} @ {timestamp})"
