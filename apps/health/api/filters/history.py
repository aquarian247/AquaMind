"""
History filters for Health models.

These filters provide date range, user, and change type filtering
for historical records across health models with historical tracking.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.health.models import (
    JournalEntry,
    LiceCount,
    LiceType,
    MortalityRecord,
    Treatment,
    HealthLabSample
)


class JournalEntryHistoryFilter(HistoryFilter):
    """Filter class for JournalEntry historical records."""

    class Meta:
        model = JournalEntry.history.model
        fields = ['batch', 'container', 'category', 'severity', 'resolution_status']


class LiceCountHistoryFilter(HistoryFilter):
    """Filter class for LiceCount historical records."""

    class Meta:
        model = LiceCount.history.model
        fields = ['batch', 'container', 'lice_type']


class LiceTypeHistoryFilter(HistoryFilter):
    """Filter class for LiceType historical records."""

    class Meta:
        model = LiceType.history.model
        fields = ['species', 'gender', 'development_stage', 'is_active']


class MortalityRecordHistoryFilter(HistoryFilter):
    """Filter class for MortalityRecord historical records."""

    class Meta:
        model = MortalityRecord.history.model
        fields = ['batch', 'container', 'reason']


class TreatmentHistoryFilter(HistoryFilter):
    """Filter class for Treatment historical records."""

    class Meta:
        model = Treatment.history.model
        fields = ['batch', 'container', 'treatment_type']


class HealthLabSampleHistoryFilter(HistoryFilter):
    """Filter class for HealthLabSample historical records."""

    class Meta:
        model = HealthLabSample.history.model
        fields = ['batch_container_assignment', 'sample_type', 'recorded_by']
