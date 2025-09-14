"""
Growth sample viewsets.

These viewsets provide CRUD operations for growth sample management.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import GrowthSample
from apps.batch.api.serializers import GrowthSampleSerializer
from apps.batch.api.filters.growth import GrowthSampleFilter


class GrowthSampleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Growth Samples from aquaculture batches.

    Growth samples record the average weight of organisms in a batch (or a specific
    container assignment of a batch) on a particular date. This data is essential
    for tracking growth, calculating feed conversion ratios, and making management decisions.
    This endpoint provides full CRUD operations for growth samples.

    **Filtering:**
    - `assignment__batch`: ID of the batch associated with the growth sample (via BatchContainerAssignment).
    - `sample_date`: Exact date of the sample.

    **Searching:**
    - `batch__batch_number`: Batch number of the associated batch. (Searches through the related Batch model via the assignment)
    - `notes`: Notes associated with the growth sample.

    **Ordering:**
    - `sample_date` (default: descending)
    - `batch__batch_number`: Batch number of the associated batch. (Orders based on the related Batch model via the assignment)
    - `avg_weight_g`: Average weight in grams.
    - `created_at`
    """
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = GrowthSample.objects.all()
    serializer_class = GrowthSampleSerializer
    filterset_class = GrowthSampleFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment__batch', 'sample_date']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['sample_date', 'batch__batch_number', 'avg_weight_g', 'created_at']
    ordering = ['-sample_date']

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
