"""
Transport carrier model for logistics assets.

This model represents movable transport assets such as trucks and vessels.
Carrier tanks are represented by infrastructure Container records linked via FK.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.geography import Geography


class TransportCarrier(models.Model):
    """Movable transport asset used in station-to-sea logistics."""

    CARRIER_TYPE_CHOICES = [
        ("TRUCK", "Truck"),
        ("VESSEL", "Vessel"),
    ]

    name = models.CharField(max_length=100, unique=True)
    carrier_type = models.CharField(max_length=20, choices=CARRIER_TYPE_CHOICES)
    geography = models.ForeignKey(
        Geography,
        on_delete=models.PROTECT,
        related_name="transport_carriers",
    )
    capacity_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    license_plate = models.CharField(max_length=32, blank=True)
    imo_number = models.CharField(max_length=20, blank=True)
    captain_contact = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_carrier_type_display()})"
