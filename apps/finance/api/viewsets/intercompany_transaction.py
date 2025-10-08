"""Viewset for intercompany transactions."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, permissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.finance.api.filters import IntercompanyTransactionFilterSet
from apps.finance.api.pagination import FinancePagination
from apps.finance.api.permissions import IsFinanceUser
from apps.finance.api.serializers import IntercompanyTransactionSerializer
from apps.finance.models import IntercompanyTransaction

@extend_schema_view(
    list=extend_schema(
        summary="List intercompany transactions",
        description="Retrieve detected intercompany transactions with optional filters.",
        parameters=[
            OpenApiParameter(
                name="state",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by transaction state (pending, exported, posted).",
            ),
            OpenApiParameter(
                name="company",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by finance company ID participating in the policy.",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Inclusive lower bound for posting date.",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Inclusive upper bound for posting date.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Ordering fields, e.g. '-posting_date'.",
            ),
        ],
    ),
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter(
                name="tx_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Unique intercompany transaction identifier.",
            )
        ]
    ),
)
class IntercompanyTransactionViewSet(ReadOnlyModelViewSet):
    """Read-only access to intercompany transactions."""

    serializer_class = IntercompanyTransactionSerializer
    lookup_field = "tx_id"
    lookup_url_kwarg = "tx_id"
    filterset_class = IntercompanyTransactionFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = (
        "posting_date",
        "created_at",
        "updated_at",
        "tx_id",
    )
    ordering = ("-posting_date", "-tx_id")
    permission_classes = [permissions.IsAuthenticated, IsFinanceUser]
    pagination_class = FinancePagination

    def get_queryset(self):
        return (
            IntercompanyTransaction.objects.select_related(
                "policy",
                "policy__from_company",
                "policy__from_company__geography",
                "policy__to_company",
                "policy__to_company__geography",
                "policy__product_grade",
                "event",
            )
            .order_by("-posting_date", "-tx_id")
        )
