"""
Treatment viewsets for health monitoring.

This module defines viewsets for treatment-related models, including
VaccinationType and Treatment.
"""

from rest_framework import viewsets, permissions

from apps.health.models import VaccinationType, Treatment
from apps.health.api.serializers import VaccinationTypeSerializer, TreatmentSerializer
from aquamind.utils.history_mixins import HistoryReasonMixin
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class VaccinationTypeViewSet(HistoryReasonMixin, StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Vaccination Types.
    
    Provides CRUD operations for vaccination types used in treatments.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = VaccinationType.objects.all()
    serializer_class = VaccinationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'name': ['exact', 'icontains'],
        'manufacturer': ['exact', 'icontains']
    }
    search_fields = ['name', 'manufacturer', 'dosage', 'description']


class TreatmentViewSet(HistoryReasonMixin, UserAssignmentMixin, OptimizedQuerysetMixin, 
                      StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Treatments.
    
    Provides CRUD operations for treatments, which track medical interventions
    for fish populations.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = Treatment.objects.all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['batch', 'container', 'batch_assignment', 'vaccination_type', 'user']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'batch__id': ['exact'],
        'container__id': ['exact'],
        'batch_assignment__id': ['exact'],
        'treatment_date': ['exact', 'gte', 'lte'],
        'treatment_type': ['exact'],
        'vaccination_type__id': ['exact'],
        'withholding_period_days': ['exact', 'gte', 'lte'],
        'outcome': ['exact', 'icontains'],
        'user__id': ['exact']
    }
    
    search_fields = ['description', 'dosage', 'outcome']
