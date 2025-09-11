"""
History filters for Batch models.

These filters provide date range, user, and change type filtering
for historical records across all batch models.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)


class BatchHistoryFilter(HistoryFilter):
    """Filter class for Batch historical records."""

    class Meta:
        model = Batch.history.model
        fields = ['batch_number', 'species', 'lifecycle_stage', 'status', 'batch_type']


class BatchContainerAssignmentHistoryFilter(HistoryFilter):
    """Filter class for BatchContainerAssignment historical records."""

    class Meta:
        model = BatchContainerAssignment.history.model
        fields = ['batch', 'container', 'lifecycle_stage']


class BatchTransferHistoryFilter(HistoryFilter):
    """Filter class for BatchTransfer historical records."""

    class Meta:
        model = BatchTransfer.history.model
        fields = ['source_batch', 'destination_batch', 'transfer_type']


class MortalityEventHistoryFilter(HistoryFilter):
    """Filter class for MortalityEvent historical records."""

    class Meta:
        model = MortalityEvent.history.model
        fields = ['batch', 'cause']


class GrowthSampleHistoryFilter(HistoryFilter):
    """Filter class for GrowthSample historical records."""

    class Meta:
        model = GrowthSample.history.model
        fields = ['assignment__batch', 'assignment__container']
