"""Filter sets for harvest events."""

import django_filters as filters
from django_filters import rest_framework as rest_filters

from apps.harvest.models import HarvestEvent


class HarvestEventFilterSet(rest_filters.FilterSet):
    """Filters supporting harvest event list queries."""

    date_from = filters.DateTimeFilter(
        field_name="event_date",
        lookup_expr="gte",
        label="Event date from",
    )
    date_to = filters.DateTimeFilter(
        field_name="event_date",
        lookup_expr="lte",
        label="Event date to",
    )
    document_ref = filters.CharFilter(
        field_name="document_ref",
        lookup_expr="icontains",
        label="Document reference contains",
    )

    class Meta:
        model = HarvestEvent
        fields = {
            "batch": ["exact"],
            "assignment": ["exact"],
            "dest_geography": ["exact"],
            "dest_subsidiary": ["exact"],
        }
