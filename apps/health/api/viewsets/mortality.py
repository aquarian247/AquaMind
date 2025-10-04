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


class MortalityRecordViewSet(OptimizedQuerysetMixin,
                            StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Mortality Records.

    Provides CRUD operations for mortality records, which track fish deaths
    and their causes.

    Note: UserAssignmentMixin removed as MortalityRecord has no user field.
    """
    queryset = MortalityRecord.objects.all()
    serializer_class = MortalityRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    # OptimizedQuerysetMixin configuration
    select_related_fields = ['batch', 'container', 'reason']

    # StandardFilterMixin configuration
    filterset_fields = {
        'event_date': ['exact', 'gte', 'lte'],
        'batch': ['exact'],
        'container': ['exact'],
        'reason': ['exact'],
        'count': ['exact', 'gte', 'lte']
    }

    search_fields = ['notes']


class LiceCountViewSet(UserAssignmentMixin, OptimizedQuerysetMixin,
                      StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Lice Counts.

    Provides CRUD operations for lice counts, which track sea lice infestations
    in fish populations.

    Note: UserAssignmentMixin is appropriate here as LiceCount has a user field.
    """
    queryset = LiceCount.objects.all()
    serializer_class = LiceCountSerializer
    permission_classes = [permissions.IsAuthenticated]

    # OptimizedQuerysetMixin configuration
    select_related_fields = ['user', 'batch', 'container']

    # StandardFilterMixin configuration - using only actual model fields
    filterset_fields = {
        'count_date': ['exact', 'gte', 'lte'],
        'batch': ['exact'],
        'container': ['exact'],
        'user': ['exact'],
        'fish_sampled': ['exact', 'gte', 'lte'],
        'adult_female_count': ['exact', 'gte', 'lte'],
        'adult_male_count': ['exact', 'gte', 'lte'],
        'juvenile_count': ['exact', 'gte', 'lte']
    }

    search_fields = ['notes']

