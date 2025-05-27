"""
Treatment viewsets for health monitoring.

This module defines viewsets for treatment-related models, including
VaccinationType and Treatment.
"""

from rest_framework import viewsets, permissions

from apps.health.models import VaccinationType, Treatment
from apps.health.api.serializers import VaccinationTypeSerializer, TreatmentSerializer
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class VaccinationTypeViewSet(StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Vaccination Types.
    
    Provides CRUD operations for vaccination types used in treatments.
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


class TreatmentViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                      StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Treatments.
    
    Provides CRUD operations for treatments, which track medical interventions
    for fish populations.
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
    
    # Override filter_queryset to add custom filtering for calculated fields
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        
        # Get query parameters for withholding_end_date
        withholding_end_date = self.request.query_params.get('withholding_end_date')
        withholding_end_date_gte = self.request.query_params.get('withholding_end_date__gte')
        withholding_end_date_lte = self.request.query_params.get('withholding_end_date__lte')
        
        # Apply filters if parameters are provided
        if withholding_end_date:
            # Since withholding_end_date is calculated, we need to filter on treatment_date + withholding_period_days
            # This is a simplification - for exact filtering, we'd need a more complex query
            queryset = queryset.filter(withholding_end_date=withholding_end_date)
        if withholding_end_date_gte:
            queryset = queryset.filter(withholding_end_date__gte=withholding_end_date_gte)
        if withholding_end_date_lte:
            queryset = queryset.filter(withholding_end_date__lte=withholding_end_date_lte)
            
        return queryset
    search_fields = ['description', 'dosage', 'outcome']
