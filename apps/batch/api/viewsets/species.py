"""
Species and LifeCycleStage viewsets.

These viewsets provide CRUD operations for species and lifecycle stage management.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import Species, LifeCycleStage
from apps.batch.api.serializers import SpeciesSerializer, LifeCycleStageSerializer
from apps.batch.api.filters.species import SpeciesFilter, LifeCycleStageFilter


class SpeciesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing aquaculture Species.

    Provides CRUD operations for species, including filtering by name
    and scientific name, searching across name, scientific name, and description,
    and ordering by name, scientific name, or creation date.
    """
    # NOTE: Authentication temporarily disabled in development to allow
    # the React frontend (which currently has no login flow) to access
    # these endpoints.  Re-enable once frontend auth is implemented.
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    filterset_class = SpeciesFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'scientific_name']
    search_fields = ['name', 'scientific_name', 'description']
    ordering_fields = ['name', 'scientific_name', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class LifeCycleStageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Species Life Cycle Stages.

    Provides CRUD operations for life cycle stages, specific to a species.
    Allows filtering by name, species, and order.
    Supports searching across name, description, and species name.
    Ordering can be done by species name, order, name, or creation date.
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = LifeCycleStage.objects.all()
    serializer_class = LifeCycleStageSerializer
    filterset_class = LifeCycleStageFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'species', 'order']
    search_fields = ['name', 'description', 'species__name']
    ordering_fields = ['species__name', 'order', 'name', 'created_at']
    ordering = ['species__name', 'order']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
