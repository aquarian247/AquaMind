"""
Treatment viewsets for health monitoring.

This module defines viewsets for treatment-related models, including
VaccinationType and Treatment.
"""

from rest_framework import viewsets, permissions

from apps.health.models import VaccinationType, Treatment
from apps.health.api.serializers import VaccinationTypeSerializer, TreatmentSerializer
from apps.health.api.permissions import IsHealthContributor, IsTreatmentEditor
from aquamind.api.mixins import RBACFilterMixin
from aquamind.utils.history_mixins import HistoryReasonMixin
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class VaccinationTypeViewSet(HistoryReasonMixin, StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Vaccination Types.
    
    Provides CRUD operations for vaccination types used in treatments.
    Access is restricted to health contributors (VET/QA/Admin).
    
    RBAC Enforcement:
    - Permission: IsHealthContributor (VET/QA/Admin)
    - No geographic filtering (vaccination types are global reference data)
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = VaccinationType.objects.all()
    serializer_class = VaccinationTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'name': ['exact', 'icontains'],
        'manufacturer': ['exact', 'icontains']
    }
    search_fields = ['name', 'manufacturer', 'dosage', 'description']


class TreatmentViewSet(RBACFilterMixin, HistoryReasonMixin, UserAssignmentMixin, 
                      OptimizedQuerysetMixin, StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Treatments.
    
    Provides CRUD operations for treatments, which track medical interventions
    for fish populations. Write access is restricted to Veterinarians and
    Administrators only. QA personnel have read-only access.
    
    RBAC Enforcement:
    - Permission: IsTreatmentEditor (VET/Admin write, QA read-only)
    - Geographic Filtering: Users only see treatments for batches in their geography
    - Object-level Validation: Prevents creating/updating treatments outside user's scope
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    queryset = Treatment.objects.all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTreatmentEditor]
    
    # RBAC configuration - filter by geography through batch
    geography_filter_fields = [
        'batch__batch_assignments__container__area__geography',
        'batch__batch_assignments__container__hall__freshwater_station__geography'
    ]
    
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
