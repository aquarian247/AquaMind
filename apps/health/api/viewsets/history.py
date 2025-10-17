"""
History viewsets for Health models.

These viewsets provide read-only access to historical records
for all health models with filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.health.models import (
    JournalEntry,
    LiceCount,
    LiceType,
    MortalityRecord,
    Treatment,
    HealthLabSample
)
from ..serializers.history import (
    JournalEntryHistorySerializer,
    LiceCountHistorySerializer,
    LiceTypeHistorySerializer,
    MortalityRecordHistorySerializer,
    TreatmentHistorySerializer,
    HealthLabSampleHistorySerializer
)
from ..filters.history import (
    JournalEntryHistoryFilter,
    LiceCountHistoryFilter,
    LiceTypeHistoryFilter,
    MortalityRecordHistoryFilter,
    TreatmentHistoryFilter,
    HealthLabSampleHistoryFilter
)


class JournalEntryHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for JournalEntry historical records."""
    queryset = JournalEntry.history.all()
    serializer_class = JournalEntryHistorySerializer
    filterset_class = JournalEntryHistoryFilter


class LiceCountHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for LiceCount historical records."""
    queryset = LiceCount.history.all()
    serializer_class = LiceCountHistorySerializer
    filterset_class = LiceCountHistoryFilter


class LiceTypeHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for LiceType historical records."""
    queryset = LiceType.history.all()
    serializer_class = LiceTypeHistorySerializer
    filterset_class = LiceTypeHistoryFilter


class MortalityRecordHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for MortalityRecord historical records."""
    queryset = MortalityRecord.history.all()
    serializer_class = MortalityRecordHistorySerializer
    filterset_class = MortalityRecordHistoryFilter


class TreatmentHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Treatment historical records."""
    queryset = Treatment.history.all()
    serializer_class = TreatmentHistorySerializer
    filterset_class = TreatmentHistoryFilter


class HealthLabSampleHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for HealthLabSample historical records."""
    queryset = HealthLabSample.history.all()
    serializer_class = HealthLabSampleHistorySerializer
    filterset_class = HealthLabSampleHistoryFilter
