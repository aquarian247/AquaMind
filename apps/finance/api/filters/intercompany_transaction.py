"""Filter set for intercompany transaction endpoints."""

import django_filters as filters
from django.db.models import Q

from apps.finance.models import IntercompanyTransaction


class IntercompanyTransactionFilterSet(filters.FilterSet):
    """Filters supporting intercompany transaction list queries."""

    state = filters.CharFilter(
        field_name="state",
        lookup_expr="iexact",
        label="Transaction state",
    )
    company = filters.NumberFilter(
        method="filter_company",
        label="Matches either from or to finance company ID",
    )
    date_from = filters.DateFilter(
        field_name="posting_date",
        lookup_expr="gte",
        label="Start of posting date range (inclusive)",
    )
    date_to = filters.DateFilter(
        field_name="posting_date",
        lookup_expr="lte",
        label="End of posting date range (inclusive)",
    )

    class Meta:
        model = IntercompanyTransaction
        fields = ["state", "company", "date_from", "date_to"]

    def filter_company(self, queryset, name, value):  # pylint: disable=unused-argument
        return queryset.filter(
            Q(policy__from_company_id=value) | Q(policy__to_company_id=value)
        )
