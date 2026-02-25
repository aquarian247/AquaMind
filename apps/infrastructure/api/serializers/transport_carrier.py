"""
Transport carrier serializer for infrastructure API.
"""

from rest_framework import serializers

from apps.infrastructure.api.serializers.base import (
    NamedModelSerializer,
    TimestampedModelSerializer,
)
from apps.infrastructure.models import Geography, TransportCarrier


class TransportCarrierSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for truck/vessel transport carriers."""

    geography = serializers.PrimaryKeyRelatedField(
        queryset=Geography.objects.all(),
        help_text="Geography the carrier belongs to.",
    )
    geography_name = serializers.StringRelatedField(
        source="geography",
        read_only=True,
        help_text="Geography name.",
    )

    class Meta:
        model = TransportCarrier
        fields = [
            "id",
            "name",
            "carrier_type",
            "geography",
            "geography_name",
            "capacity_m3",
            "license_plate",
            "imo_number",
            "captain_contact",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "geography_name")
