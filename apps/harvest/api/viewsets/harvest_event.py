"""Viewsets for harvest event endpoints."""

from rest_framework import filters
from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes

from apps.harvest.api.filters import HarvestEventFilterSet
from apps.harvest.api.serializers import HarvestEventSerializer
from apps.harvest.models import HarvestEvent


@extend_schema_view(
    list=extend_schema(
        summary="List harvest events",
        description="Retrieve harvest events with optional filtering by batch, assignment, destination, date range, or document reference.",
        parameters=[
            OpenApiParameter(
                name="batch",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter events by batch ID.",
            ),
            OpenApiParameter(
                name="assignment",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter events by assignment ID.",
            ),
            OpenApiParameter(
                name="dest_geography",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter events by destination geography ID.",
            ),
            OpenApiParameter(
                name="dest_subsidiary",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter events by destination subsidiary code.",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Include events on or after this ISO 8601 timestamp.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Include events on or before this ISO 8601 timestamp.",
            ),
            OpenApiParameter(
                name="document_ref",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter events whose document reference contains this value (case-insensitive).",
            ),
        ],
    )
)
class HarvestEventViewSet(ReadOnlyModelViewSet):
    """Read-only access to harvest events."""

    queryset = (
        HarvestEvent.objects.select_related(
            "batch",
            "assignment__container",
            "dest_geography",
        )
        .order_by("-event_date", "-id")
    )
    serializer_class = HarvestEventSerializer
    filterset_class = HarvestEventFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = (
        "event_date",
        "batch__batch_number",
        "created_at",
        "updated_at",
    )
    ordering = ("-event_date", "-id")
    search_fields = (
        "document_ref",
        "batch__batch_number",
        "assignment__container__name",
    )
