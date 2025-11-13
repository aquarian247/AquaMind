"""Filters for feed purchase endpoints."""
from django_filters import rest_framework as rest_filters

from apps.inventory.models import FeedPurchase


class FeedPurchaseFilter(rest_filters.FilterSet):
    """FilterSet for FeedPurchase queries."""

    start_date = rest_filters.DateFilter(field_name="purchase_date", lookup_expr="gte")
    end_date = rest_filters.DateFilter(field_name="purchase_date", lookup_expr="lte")

    class Meta:
        model = FeedPurchase
        fields = ["feed", "supplier", "purchase_date", "start_date", "end_date"]
