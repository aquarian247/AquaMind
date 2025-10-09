"""
Mortality event viewsets.

These viewsets provide CRUD operations for mortality event management.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from aquamind.utils.history_mixins import HistoryReasonMixin

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import MortalityEvent
from apps.batch.api.serializers import MortalityEventSerializer
from apps.batch.api.filters.mortality import MortalityEventFilter


class MortalityEventViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Mortality Events in aquaculture batches.

    Mortality events record the number of deaths in a batch on a specific date,
    along with the suspected cause and any relevant notes. This endpoint
    provides full CRUD operations for mortality events. Uses HistoryReasonMixin
    to capture audit change reasons.

    **Filtering:**
    - `batch`: ID of the batch associated with the mortality event.
    - `batch__in`: Filter by multiple Batch IDs (comma-separated).
    - `event_date`: Exact date of the mortality event.
    - `cause`: Suspected cause of mortality (e.g., 'DISEASE', 'PREDATION', 'HANDLING').

    **Searching:**
    - `batch__batch_number`: Batch number of the associated batch.
    - `notes`: Notes associated with the mortality event.

    **Ordering:**
    - `event_date` (default: descending)
    - `batch__batch_number`
    - `count` (number of mortalities)
    - `created_at`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = MortalityEvent.objects.all()
    serializer_class = MortalityEventSerializer
    filterset_class = MortalityEventFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Use the correct model field name "description" instead of the
    # non-existent "notes" to avoid FieldError during search filtering
    search_fields = ['batch__batch_number', 'description']
    ordering_fields = ['event_date', 'batch__batch_number', 'count', 'created_at']
    ordering = ['-event_date']

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
