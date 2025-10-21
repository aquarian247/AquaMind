"""
History serializers for Batch models.

These serializers provide read-only access to historical records
for all batch models, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    MortalityEvent,
    GrowthSample
)


class BatchHistorySerializer(HistorySerializer):
    """History serializer for Batch model."""

    class Meta:
        model = Batch.history.model
        fields = '__all__'


class BatchContainerAssignmentHistorySerializer(HistorySerializer):
    """History serializer for BatchContainerAssignment model."""

    class Meta:
        model = BatchContainerAssignment.history.model
        fields = '__all__'


class MortalityEventHistorySerializer(HistorySerializer):
    """History serializer for MortalityEvent model."""

    class Meta:
        model = MortalityEvent.history.model
        fields = '__all__'


class GrowthSampleHistorySerializer(HistorySerializer):
    """History serializer for GrowthSample model."""

    class Meta:
        model = GrowthSample.history.model
        fields = '__all__'
