"""Viewset for finance harvest facts."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, permissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.finance.api.filters import FactHarvestFilterSet
from apps.finance.api.pagination import FinancePagination
from apps.finance.api.permissions import IsFinanceUser
from apps.finance.api.serializers import FactHarvestSerializer
from apps.finance.models import FactHarvest


@extend_schema_view(
    list=extend_schema(
        summary="List finance harvest facts",
        description="Retrieve projected harvest facts with optional filters.",
        parameters=[
            OpenApiParameter(
                name="company",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by finance company ID.",
            ),
            OpenApiParameter(
                name="site",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by finance site ID.",
            ),
            OpenApiParameter(
                name="batch",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by originating batch ID.",
            ),
            OpenApiParameter(
                name="grade",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by product grade code (case insensitive).",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Inclusive lower bound for event date.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description="Inclusive upper bound for event date.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Ordering fields, e.g. '-event_date' or 'event_date'.",
            ),
        ],
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(
                name="fact_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique finance fact identifier.",
            )
        ]
    ),
)
class FactHarvestViewSet(ReadOnlyModelViewSet):
    """Read-only access to finance harvest facts."""

    serializer_class = FactHarvestSerializer
    lookup_field = "fact_id"
    lookup_url_kwarg = "fact_id"
    filterset_class = FactHarvestFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = (
        "event_date",
        "quantity_kg",
        "unit_count",
        "fact_id",
    )
    ordering = ("-event_date", "-fact_id")
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    pagination_class = FinancePagination

    def get_queryset(self):
        return (
            FactHarvest.objects.select_related(
                "dim_company",
                "dim_company__geography",
                "dim_site",
                "dim_site__company",
                "product_grade",
            )
            .order_by("-event_date", "-fact_id")
        )
