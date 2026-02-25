"""
Container viewset for the infrastructure app.

This module defines the viewset for the Container model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.infrastructure.models.container import Container
from apps.infrastructure.api.serializers.container import ContainerSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated


class ContainerFilter(FilterSet):
    """Custom filterset for Container model to support __in lookups."""

    class Meta:
        model = Container
        fields = {
            'name': ['exact'],
            'container_type': ['exact'],
            'container_type__category': ['exact'],
            'hall': ['exact', 'in'],
            'area': ['exact', 'in'],
            'carrier': ['exact', 'in'],
            'carrier__carrier_type': ['exact'],
            'parent_container': ['exact', 'in', 'isnull'],
            'hierarchy_role': ['exact'],
            'active': ['exact']
        }

class ContainerViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Containers within the aquaculture facility.

    Containers represent physical units (e.g., tanks, ponds, cages) used for
    holding aquatic organisms. They are associated with a specific container type,
    and can be located within a Hall and an Area. This endpoint allows for
    full CRUD operations on Container instances. Uses HistoryReasonMixin to capture
    audit change reasons.

    **Filtering:**
    - `name`: Filter by the exact name of the container.
    - `container_type`: Filter by the ID of the ContainerType.
    - `container_type__category`: Filter by container type category (TANK/PEN/TRAY/OTHER).
    - `hall`: Filter by the ID of the parent Hall.
    - `hall__in`: Filter by multiple Hall IDs (comma-separated).
    - `area`: Filter by the ID of the parent Area.
    - `area__in`: Filter by multiple Area IDs (comma-separated).
    - `carrier`: Filter by linked transport carrier ID.
    - `carrier__in`: Filter by multiple transport carrier IDs.
    - `carrier__carrier_type`: Filter by carrier type (TRUCK/VESSEL).
    - `parent_container`: Filter by parent container ID.
    - `parent_container__in`: Filter by multiple parent container IDs.
    - `parent_container__isnull`: Filter top-level containers (`true`) vs children (`false`).
    - `hierarchy_role`: Filter by hierarchy role (HOLDING/STRUCTURAL).
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by container name (partial matches).
    - `container_type__name`: Search by the name of the ContainerType.
    - `hall__name`: Search by the name of the parent Hall.
    - `area__name`: Search by the name of the parent Area.
    - `carrier__name`: Search by the name of the linked transport carrier.
    - `parent_container__name`: Search by parent container name.

    **Ordering:**
    - `name` (default)
    - `container_type__name`
    - `parent_container__name`
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ContainerFilter
    search_fields = ['name', 'container_type__name', 'hall__name', 'area__name', 'carrier__name', 'parent_container__name']
    ordering_fields = ['name', 'container_type__name', 'carrier__name', 'parent_container__name', 'created_at']
    ordering = ['name']

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
