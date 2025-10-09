"""
Batch composition viewsets.

These viewsets provide CRUD operations for batch composition management.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from aquamind.utils.history_mixins import HistoryReasonMixin

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import BatchComposition
from apps.batch.api.serializers import BatchCompositionSerializer
from apps.batch.api.filters.composition import BatchCompositionFilter


class BatchCompositionViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Compositions.

    This endpoint defines the composition of a 'mixed' batch, detailing what
    percentage and quantity (population/biomass) of it comes from various
    'source' batches. This is crucial for traceability when batches are merged.
    Provides full CRUD operations for batch composition records. Uses
    HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `mixed_batch`: ID of the resulting mixed batch.
    - `source_batch`: ID of a source batch contributing to the mixed batch.

    **Searching:**
    - `mixed_batch__batch_number`: Batch number of the mixed batch.
    - `source_batch__batch_number`: Batch number of the source batch.

    **Ordering:**
    - `mixed_batch__batch_number` (default)
    - `source_batch__batch_number`
    - `percentage` (default)
    - `population_count`
    - `biomass_kg`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = BatchComposition.objects.all()
    serializer_class = BatchCompositionSerializer
    filterset_class = BatchCompositionFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mixed_batch', 'source_batch']
    search_fields = ['mixed_batch__batch_number', 'source_batch__batch_number']
    ordering_fields = [
        'mixed_batch__batch_number',
        'source_batch__batch_number',
        'percentage',
        'population_count',
        'biomass_kg'
    ]
    ordering = ['mixed_batch__batch_number', 'percentage']

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
