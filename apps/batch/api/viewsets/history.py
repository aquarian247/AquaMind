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

    def get_operation_id(self, request=None, action=None):
        """Generate unique operation ID to resolve Spectacular collisions."""
        if action == 'list':
            return 'listBatchBatchHistory'
        elif action == 'retrieve':
            return 'retrieveBatchBatchHistory'
        return super().get_operation_id(request, action)


class BatchContainerAssignmentHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BatchContainerAssignment historical records."""
    queryset = BatchContainerAssignment.history.all()
    serializer_class = BatchContainerAssignmentHistorySerializer
    filterset_class = BatchContainerAssignmentHistoryFilter

    def get_operation_id(self, request=None, action=None):
        """Generate unique operation ID to resolve Spectacular collisions."""
        if action == 'list':
            return 'listBatchContainerAssignmentHistory'
        elif action == 'retrieve':
            return 'retrieveBatchContainerAssignmentHistory'
        return super().get_operation_id(request, action)


class BatchTransferHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BatchTransfer historical records."""
    queryset = BatchTransfer.history.all()
    serializer_class = BatchTransferHistorySerializer
    filterset_class = BatchTransferHistoryFilter

    def get_operation_id(self, request=None, action=None):
        """Generate unique operation ID to resolve Spectacular collisions."""
        if action == 'list':
            return 'listBatchBatchTransferHistory'
        elif action == 'retrieve':
            return 'retrieveBatchBatchTransferHistory'
        return super().get_operation_id(request, action)


class MortalityEventHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for MortalityEvent historical records."""
    queryset = MortalityEvent.history.all()
    serializer_class = MortalityEventHistorySerializer
    filterset_class = MortalityEventHistoryFilter

    def get_operation_id(self, request=None, action=None):
        """Generate unique operation ID to resolve Spectacular collisions."""
        if action == 'list':
            return 'listBatchMortalityEventHistory'
        elif action == 'retrieve':
            return 'retrieveBatchMortalityEventHistory'
        return super().get_operation_id(request, action)


class GrowthSampleHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for GrowthSample historical records."""
    queryset = GrowthSample.history.all()
    serializer_class = GrowthSampleHistorySerializer
    filterset_class = GrowthSampleHistoryFilter

    def get_operation_id(self, request=None, action=None):
        """Generate unique operation ID to resolve Spectacular collisions."""
        if action == 'list':
            return 'listBatchGrowthSampleHistory'
        elif action == 'retrieve':
            return 'retrieveBatchGrowthSampleHistory'
        return super().get_operation_id(request, action)
