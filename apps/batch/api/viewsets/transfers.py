"""
Batch transfer viewsets.

These viewsets provide CRUD operations for batch transfer management.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import BatchTransfer
from apps.batch.api.serializers import BatchTransferSerializer
from apps.batch.api.filters.transfers import BatchTransferFilter


class BatchTransferViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Transfers.

    Batch transfers record the movement of organisms between batches or changes
    in their lifecycle stage or container assignment within the same batch.
    This endpoint provides full CRUD operations for batch transfers.

    **Filtering:**
    - `source_batch`: ID of the source batch.
    - `destination_batch`: ID of the destination batch.
    - `transfer_type`: Type of transfer (e.g., 'SPLIT', 'MERGE', 'MOVE', 'LIFECYCLE_CHANGE').
    - `source_lifecycle_stage`: ID of the source lifecycle stage.
    - `destination_lifecycle_stage`: ID of the destination lifecycle stage.
    - `source_assignment`: ID of the source batch container assignment.
    - `destination_assignment`: ID of the destination batch container assignment.

    **Searching:**
    - `source_batch__batch_number`: Batch number of the source batch.
    - `destination_batch__batch_number`: Batch number of the destination batch.
    - `notes`: Notes associated with the transfer.

    **Ordering:**
    - `transfer_date` (default: descending)
    - `source_batch__batch_number`
    - `transfer_type`
    - `created_at`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = BatchTransfer.objects.all()
    serializer_class = BatchTransferSerializer
    filterset_class = BatchTransferFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'source_batch',
        'destination_batch',
        'transfer_type',
        'source_lifecycle_stage',
        'destination_lifecycle_stage',
        'source_assignment',
        'destination_assignment'
    ]
    search_fields = [
        'source_batch__batch_number',
        'destination_batch__batch_number',
        'notes'
    ]
    ordering_fields = [
        'transfer_date',
        'source_batch__batch_number',
        'transfer_type',
        'created_at'
    ]
    ordering = ['-transfer_date']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
