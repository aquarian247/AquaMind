"""
Transport carrier viewset for infrastructure API.
"""

from rest_framework import filters, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.infrastructure.api.serializers.transport_carrier import (
    TransportCarrierSerializer,
)
from apps.infrastructure.models import TransportCarrier


class TransportCarrierViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """CRUD endpoint for logistics transport carriers (trucks/vessels)."""

    queryset = TransportCarrier.objects.select_related("geography").all()
    serializer_class = TransportCarrierSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["carrier_type", "geography", "active"]
    search_fields = ["name", "license_plate", "imo_number", "captain_contact"]
    ordering_fields = ["name", "carrier_type", "capacity_m3", "created_at"]
    ordering = ["name"]
