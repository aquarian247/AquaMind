"""
Feed purchase viewset for the inventory app.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, F, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.inventory.api.filters.purchase import FeedPurchaseFilter
from apps.inventory.api.serializers.purchase import FeedPurchaseSerializer
from apps.inventory.models import FeedPurchase


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """
    Helper to convert common truthy/falsey strings into booleans.
    """
    if value is None:
        return default

    value_normalized = value.strip().lower()
    if value_normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if value_normalized in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _quantize_decimal(
    value: Decimal | None, places: str = "0.01", allow_none: bool = False
) -> float | None:
    """
    Convert a Decimal value to a float with the provided precision.
    """
    if value is None:
        return None if allow_none else 0.0

    return float(Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP))


class FeedPurchaseViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for FeedPurchase model.

    Provides CRUD operations for feed purchase records. Uses HistoryReasonMixin
    to capture audit change reasons.
    """

    queryset = FeedPurchase.objects.all()
    serializer_class = FeedPurchaseSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = FeedPurchaseFilter
    search_fields = ["supplier", "batch_number", "notes"]
    ordering_fields = ["purchase_date", "quantity_kg", "cost_per_kg"]
    ordering = ["-purchase_date"]

    @extend_schema(
        operation_id="feed-purchases-summary",
        summary="Aggregate feed purchase totals",
        description=(
            "Return aggregated totals for feed purchases applying the same filters "
            "as the standard list endpoint. Supports optional breakdowns grouped by "
            "supplier and/or feed."
        ),
        parameters=[
            OpenApiParameter(
                name="feed",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by feed ID.",
            ),
            OpenApiParameter(
                name="supplier",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by supplier name (exact match).",
            ),
            OpenApiParameter(
                name="purchase_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter by exact purchase date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter purchases on or after this date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter purchases on or before this date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search suppliers, batch numbers, or notes (matches list endpoint).",
            ),
            OpenApiParameter(
                name="include_supplier_breakdown",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Set to true to include totals grouped by supplier.",
            ),
            OpenApiParameter(
                name="include_feed_breakdown",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Set to true to include totals grouped by feed.",
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_quantity_kg": {
                        "type": "number",
                        "description": "Total quantity purchased in kilograms.",
                    },
                    "total_spend": {
                        "type": "number",
                        "description": "Total spend across all purchases in the result set.",
                    },
                    "average_cost_per_kg": {
                        "type": "number",
                        "nullable": True,
                        "description": "Average cost per kilogram for the result set.",
                    },
                    "supplier_breakdown": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "supplier": {"type": "string"},
                                "total_quantity_kg": {"type": "number"},
                                "total_spend": {"type": "number"},
                                "average_cost_per_kg": {
                                    "type": "number",
                                    "nullable": True,
                                },
                            },
                        },
                    },
                    "feed_breakdown": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "feed_id": {"type": "integer"},
                                "feed_name": {"type": "string"},
                                "total_quantity_kg": {"type": "number"},
                                "total_spend": {"type": "number"},
                                "average_cost_per_kg": {
                                    "type": "number",
                                    "nullable": True,
                                },
                            },
                        },
                    },
                },
            },
        },
        examples=[
            OpenApiExample(
                name="Summary with breakdowns",
                value={
                    "total_quantity_kg": 3200.0,
                    "total_spend": 8640.0,
                    "average_cost_per_kg": 2.7,
                    "supplier_breakdown": [
                        {
                            "supplier": "Ocean Feeders Ltd",
                            "total_quantity_kg": 1200.0,
                            "total_spend": 3240.0,
                            "average_cost_per_kg": 2.7,
                        }
                    ],
                    "feed_breakdown": [
                        {
                            "feed_id": 42,
                            "feed_name": "NorthSea Grower",
                            "total_quantity_kg": 2000.0,
                            "total_spend": 5400.0,
                            "average_cost_per_kg": 2.7,
                        }
                    ],
                },
            )
        ],
    )
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Return aggregated feed purchase totals using the standard queryset filters.
        """

        queryset = self.filter_queryset(self.get_queryset())

        aggregates = queryset.aggregate(
            total_quantity_kg=Sum("quantity_kg"),
            total_spend=Sum(
                F("quantity_kg") * F("cost_per_kg"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            ),
        )

        total_quantity = aggregates["total_quantity_kg"] or Decimal("0")
        total_spend = aggregates["total_spend"] or Decimal("0")
        average_cost = (
            (total_spend / total_quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_quantity
            else None
        )

        include_supplier_breakdown = _parse_bool(
            request.query_params.get("include_supplier_breakdown")
        )
        include_feed_breakdown = _parse_bool(
            request.query_params.get("include_feed_breakdown")
        )

        supplier_breakdown = []
        if include_supplier_breakdown:
            supplier_breakdown = [
                {
                    "supplier": row["supplier"],
                    "total_quantity_kg": _quantize_decimal(row["total_quantity_kg"]),
                    "total_spend": _quantize_decimal(row["total_spend"]),
                    "average_cost_per_kg": _quantize_decimal(
                        (
                            row["total_spend"] / row["total_quantity_kg"]
                            if row["total_quantity_kg"]
                            else None
                        ),
                        allow_none=True,
                    ),
                }
                for row in queryset.values("supplier")
                .annotate(
                    total_quantity_kg=Sum("quantity_kg"),
                    total_spend=Sum(
                        F("quantity_kg") * F("cost_per_kg"),
                        output_field=DecimalField(max_digits=20, decimal_places=2),
                    ),
                )
                .order_by("supplier")
            ]

        feed_breakdown = []
        if include_feed_breakdown:
            feed_breakdown = [
                {
                    "feed_id": row["feed_id"],
                    "feed_name": row["feed__name"],
                    "total_quantity_kg": _quantize_decimal(row["total_quantity_kg"]),
                    "total_spend": _quantize_decimal(row["total_spend"]),
                    "average_cost_per_kg": _quantize_decimal(
                        (
                            row["total_spend"] / row["total_quantity_kg"]
                            if row["total_quantity_kg"]
                            else None
                        ),
                        allow_none=True,
                    ),
                }
                for row in queryset.values("feed_id", "feed__name")
                .annotate(
                    total_quantity_kg=Sum("quantity_kg"),
                    total_spend=Sum(
                        F("quantity_kg") * F("cost_per_kg"),
                        output_field=DecimalField(max_digits=20, decimal_places=2),
                    ),
                )
                .order_by("feed__name")
            ]

        response_data = {
            "total_quantity_kg": _quantize_decimal(total_quantity),
            "total_spend": _quantize_decimal(total_spend),
            "average_cost_per_kg": _quantize_decimal(average_cost, allow_none=True),
            "supplier_breakdown": supplier_breakdown,
            "feed_breakdown": feed_breakdown,
        }

        return Response(response_data)
