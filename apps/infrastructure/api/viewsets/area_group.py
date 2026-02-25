"""
AreaGroup viewset for the infrastructure app.

This module defines the viewset for hierarchical sea area groups.
"""

from rest_framework import viewsets, filters
from django_filters import FilterSet
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.infrastructure.models.area_group import AreaGroup
from apps.infrastructure.api.serializers.area_group import AreaGroupSerializer


class AreaGroupFilter(FilterSet):
    """Custom filterset for AreaGroup to support __in lookups."""

    class Meta:
        model = AreaGroup
        fields = {
            "name": ["exact", "icontains"],
            "code": ["exact", "icontains"],
            "geography": ["exact", "in"],
            "parent": ["exact", "in", "isnull"],
            "active": ["exact"],
        }


class AreaGroupViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Area Groups.

    Area groups provide optional hierarchical grouping for sea areas:
    Geography -> AreaGroup -> Area -> Containers.
    """

    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = AreaGroup.objects.all()
    serializer_class = AreaGroupSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AreaGroupFilter
    search_fields = ["name", "code", "geography__name", "parent__name"]
    ordering_fields = ["name", "code", "geography__name", "parent__name", "created_at"]
    ordering = ["name"]

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
