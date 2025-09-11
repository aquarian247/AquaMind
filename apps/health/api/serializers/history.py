"""
History serializers for Health models.

These serializers provide read-only access to historical records
for health models with historical tracking, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.health.models import (
    JournalEntry,
    LiceCount,
    MortalityRecord,
    Treatment,
    HealthLabSample
)


class JournalEntryHistorySerializer(HistorySerializer):
    """History serializer for JournalEntry model."""

    class Meta:
        model = JournalEntry.history.model
        fields = '__all__'


class LiceCountHistorySerializer(HistorySerializer):
    """History serializer for LiceCount model."""

    class Meta:
        model = LiceCount.history.model
        fields = '__all__'


class MortalityRecordHistorySerializer(HistorySerializer):
    """History serializer for MortalityRecord model."""

    class Meta:
        model = MortalityRecord.history.model
        fields = '__all__'


class TreatmentHistorySerializer(HistorySerializer):
    """History serializer for Treatment model."""

    class Meta:
        model = Treatment.history.model
        fields = '__all__'


class HealthLabSampleHistorySerializer(HistorySerializer):
    """History serializer for HealthLabSample model."""

    class Meta:
        model = HealthLabSample.history.model
        fields = '__all__'
