"""
History viewsets for Batch models.

These viewsets provide read-only access to historical records
for all batch models with filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.batch.api.serializers.history import (
    BatchHistorySerializer,
    BatchContainerAssignmentHistorySerializer,
    BatchTransferHistorySerializer,
    MortalityEventHistorySerializer,
    GrowthSampleHistorySerializer
)
from apps.batch.api.filters.history import (
    BatchHistoryFilter,
    BatchContainerAssignmentHistoryFilter,
    BatchTransferHistoryFilter,
    MortalityEventHistoryFilter,
    GrowthSampleHistoryFilter
)


class BatchHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Batch historical records."""
    queryset = Batch.history.all()
    serializer_class = BatchHistorySerializer
    filterset_class = BatchHistoryFilter


class BatchContainerAssignmentHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BatchContainerAssignment historical records."""
    queryset = BatchContainerAssignment.history.all()
    serializer_class = BatchContainerAssignmentHistorySerializer
    filterset_class = BatchContainerAssignmentHistoryFilter


class BatchTransferHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BatchTransfer historical records."""
    queryset = BatchTransfer.history.all()
    serializer_class = BatchTransferHistorySerializer
    filterset_class = BatchTransferHistoryFilter


class MortalityEventHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for MortalityEvent historical records."""
    queryset = MortalityEvent.history.all()
    serializer_class = MortalityEventHistorySerializer
    filterset_class = MortalityEventHistoryFilter


class GrowthSampleHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for GrowthSample historical records."""
    queryset = GrowthSample.history.all()
    serializer_class = GrowthSampleHistorySerializer
    filterset_class = GrowthSampleHistoryFilter
