"""
History filters for Inventory models.

These filters provide date range, user, and change type filtering
for historical records across inventory models with historical tracking.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.inventory.models import FeedingEvent


class FeedingEventHistoryFilter(HistoryFilter):
    """Filter class for FeedingEvent historical records."""

    class Meta:
        model = FeedingEvent.history.model
        fields = ['batch', 'feed', 'method']
