"""Django filter sets for finance core endpoints."""

import django_filters

from apps.finance_core.models import BudgetEntry, ValuationRun


class BudgetEntryFilterSet(django_filters.FilterSet):
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = BudgetEntry
        fields = ["budget", "account", "cost_center", "month"]


class ValuationRunFilterSet(django_filters.FilterSet):
    year = django_filters.NumberFilter(field_name="year")
    month = django_filters.NumberFilter(field_name="month")

    class Meta:
        model = ValuationRun
        fields = ["company", "operating_unit", "status", "budget", "year", "month"]
