"""
Mortality viewsets for health monitoring.

This module defines viewsets for mortality-related models, including
MortalityReason, MortalityRecord, and LiceCount.
"""

from rest_framework import viewsets, permissions

from apps.health.models import MortalityReason, MortalityRecord, LiceCount
from apps.health.api.serializers import (
    MortalityReasonSerializer, 
    MortalityRecordSerializer, 
    LiceCountSerializer
)
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class MortalityReasonViewSet(StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Mortality Reasons.
    
    Provides CRUD operations for mortality reasons used in mortality records.
    """
    queryset = MortalityReason.objects.all()
    serializer_class = MortalityReasonSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'name': ['exact', 'icontains']
    }
    
    # Override filter_queryset to add custom filtering for category
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        
        # Manual filtering for category
        category = self.request.query_params.get('category')
        
        if category is not None:
            queryset = queryset.filter(category=category)
            
        return queryset
    search_fields = ['name', 'description']


class MortalityRecordViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                            StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Mortality Records.
    
    Provides CRUD operations for mortality records, which track fish deaths
    and their causes.
    """
    queryset = MortalityRecord.objects.all()
    serializer_class = MortalityRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    # Update select_related_fields to match the model's actual fields
    select_related_fields = ['batch', 'container', 'reason']
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'reason__id': ['exact'],
        'count': ['exact', 'gte', 'lte']
    }
    
    # Override filter_queryset to add custom filtering for related fields
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        
        # Get query parameters
        batch_id = self.request.query_params.get('batch_id')
        container_id = self.request.query_params.get('container_id')
        mortality_date_exact = self.request.query_params.get('mortality_date')
        mortality_date_gte = self.request.query_params.get('mortality_date__gte')
        mortality_date_lte = self.request.query_params.get('mortality_date__lte')
        recorded_by_id = self.request.query_params.get('recorded_by_id')
        
        # Apply filters if parameters are provided
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        if container_id:
            queryset = queryset.filter(container_id=container_id)
        if mortality_date_exact:
            queryset = queryset.filter(mortality_date=mortality_date_exact)
        if mortality_date_gte:
            queryset = queryset.filter(mortality_date__gte=mortality_date_gte)
        if mortality_date_lte:
            queryset = queryset.filter(mortality_date__lte=mortality_date_lte)
        if recorded_by_id:
            queryset = queryset.filter(recorded_by=recorded_by_id)
            
        return queryset
    search_fields = ['notes']


class LiceCountViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                      StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Lice Counts.
    
    Provides CRUD operations for lice counts, which track sea lice infestations
    in fish populations.
    """
    queryset = LiceCount.objects.all()
    serializer_class = LiceCountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = ['user']
    
    # StandardFilterMixin configuration
    # Removed all potentially invalid filterset_fields
    filterset_fields = {
        'count_date': ['exact', 'gte', 'lte'],
        'user__id': ['exact']
    }
    
    # Override filter_queryset to add custom filtering for related fields
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        
        # Manual filtering for batch, container, fish_count and lice_count
        batch_id = self.request.query_params.get('batch_id')
        container_id = self.request.query_params.get('container_id')
        fish_count = self.request.query_params.get('fish_count')
        lice_count = self.request.query_params.get('lice_count')
        
        if batch_id:
            queryset = queryset.filter(batch_container_assignment__batch_id=batch_id)
        if container_id:
            queryset = queryset.filter(batch_container_assignment__container_id=container_id)
        if fish_count is not None:
            queryset = queryset.filter(fish_count=fish_count)
        if lice_count is not None:
            queryset = queryset.filter(lice_count=lice_count)
            
        return queryset
    search_fields = ['notes']
