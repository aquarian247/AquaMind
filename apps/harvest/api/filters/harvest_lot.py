"""Filter sets for harvest lots."""

import django_filters as filters
from django_filters import rest_framework as rest_filters

from apps.harvest.models import HarvestLot


class HarvestLotFilterSet(rest_filters.FilterSet):
    """Filters supporting harvest lot list queries."""

    grade = filters.CharFilter(
        field_name="product_grade__code",
        lookup_expr="iexact",
        label="Product grade code",
    )

    class Meta:
        model = HarvestLot
        fields = {
            "event": ["exact"],
            "product_grade": ["exact"],
        }
