"""
Batch viewsets.

These viewsets provide CRUD operations for batch management and analytics.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import Batch
from apps.batch.api.serializers import BatchSerializer
from apps.batch.api.filters.batch import BatchFilter
from .mixins import BatchAnalyticsMixin


class BatchViewSet(BatchAnalyticsMixin, viewsets.ModelViewSet):
    """
    API endpoint for comprehensive management of aquaculture Batches.

    Provides full CRUD operations for batches, including detailed filtering,
    searching, and ordering capabilities. Batches represent groups of aquatic
    organisms managed together through their lifecycle.

    **Filtering:**
    - `batch_number`: Exact match.
    - `species`: Exact match by Species ID.
    - `species__in`: Filter by multiple Species IDs (comma-separated).
    - `lifecycle_stage`: Exact match by LifeCycleStage ID.
    - `lifecycle_stage__in`: Filter by multiple LifeCycleStage IDs (comma-separated).
    - `status`: Exact match by status string (e.g., 'ACTIVE', 'PLANNED').
    - `batch_type`: Exact match by type string (e.g., 'PRODUCTION', 'EXPERIMENTAL').

    **Searching:**
    - `batch_number`: Partial match.
    - `species__name`: Partial match on the related Species name.
    - `lifecycle_stage__name`: Partial match on the related LifeCycleStage name.
    - `notes`: Partial match on the batch notes.
    - `batch_type`: Partial match on the batch type.

    **Ordering:**
    - `batch_number`
    - `start_date`
    - `species__name`
    - `lifecycle_stage__name`
    - `created_at` (default: descending)
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    filterset_class = BatchFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'batch_number',
        'species__name',
        'lifecycle_stage__name',
        'notes',
        'batch_type'
    ]
    ordering_fields = [
        'batch_number',
        'start_date',
        'species__name',
        'lifecycle_stage__name',
        # 'biomass_kg', # Removed, consider annotation for ordering by calculated field
        # 'population_count', # Removed, consider annotation for ordering by calculated field
        'created_at'
    ]
    ordering = ['-created_at']

    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of batches.

        Supports filtering by fields like `batch_number`, `species`, `lifecycle_stage`, `status`, and `batch_type`.
        Supports searching across `batch_number`, `species__name`, `lifecycle_stage__name`, `notes`, and `batch_type`.
        Supports ordering by `batch_number`, `start_date`, `species__name`, `lifecycle_stage__name`, and `created_at`.
        """
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new batch.

        Requires details such as `batch_number`, `species`, `lifecycle_stage`, `status`, `batch_type`, and `start_date`.
        `expected_end_date` will default to 30 days after `start_date` if not provided.
        """
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
