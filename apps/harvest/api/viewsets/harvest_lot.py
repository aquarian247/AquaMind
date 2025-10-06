"""Viewsets for harvest lot endpoints."""

from rest_framework import filters
from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes

from apps.harvest.api.filters import HarvestLotFilterSet
from apps.harvest.api.serializers import HarvestLotSerializer
from apps.harvest.models import HarvestLot


@extend_schema_view(
    list=extend_schema(
        summary="List harvest lots",
        description="Retrieve harvest lots with optional filtering by event or product grade.",
        parameters=[
            OpenApiParameter(
                name="event",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter lots by harvest event ID.",
            ),
            OpenApiParameter(
                name="product_grade",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter lots by product grade ID.",
            ),
            OpenApiParameter(
                name="grade",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter lots by product grade code (case insensitive).",
            ),
        ],
    )
)
class HarvestLotViewSet(ReadOnlyModelViewSet):
    """Read-only access to harvest lots."""

    queryset = (
        HarvestLot.objects.select_related(
            "event",
            "event__batch",
            "product_grade",
        )
        .order_by("-event__event_date", "-id")
    )
    serializer_class = HarvestLotSerializer
    filterset_class = HarvestLotFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = (
        "event__event_date",
        "product_grade__code",
        "live_weight_kg",
        "created_at",
        "updated_at",
    )
    ordering = ("-event__event_date", "-id")
    search_fields = (
        "product_grade__code",
        "product_grade__name",
        "event__document_ref",
    )
