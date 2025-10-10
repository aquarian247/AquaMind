"""
History viewsets for Inventory models.

These viewsets provide read-only access to historical records
for inventory models with filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.inventory.models import FeedingEvent
from ..serializers.history import FeedingEventHistorySerializer
from ..filters.history import FeedingEventHistoryFilter


class FeedingEventHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for FeedingEvent historical records."""
    queryset = FeedingEvent.history.all()
    serializer_class = FeedingEventHistorySerializer
    filterset_class = FeedingEventHistoryFilter
