"""Filter set for finance harvest facts."""

import django_filters as filters

from apps.finance.models import FactHarvest


class FactHarvestFilterSet(filters.FilterSet):
    """Filters supporting fact harvest list queries."""

    company = filters.NumberFilter(
        field_name="dim_company_id",
        label="Finance company identifier",
    )
    site = filters.NumberFilter(
        field_name="dim_site_id",
        label="Finance site identifier",
    )
    batch = filters.NumberFilter(
        field_name="dim_batch_id",
        label="Originating batch identifier",
    )
    grade = filters.CharFilter(
        field_name="product_grade__code",
        lookup_expr="iexact",
        label="Product grade code",
    )
    date_from = filters.DateTimeFilter(
        field_name="event_date",
        lookup_expr="gte",
        label="Start of event date range (inclusive)",
    )
    date_to = filters.DateTimeFilter(
        field_name="event_date",
        lookup_expr="lte",
        label="End of event date range (inclusive)",
    )

    class Meta:
        model = FactHarvest
        fields = [
            "company",
            "site",
            "batch",
            "grade",
            "date_from",
            "date_to",
        ]
