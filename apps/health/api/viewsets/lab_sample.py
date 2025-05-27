"""
Lab sample viewsets for health monitoring.

This module defines viewsets for lab sample models, including
SampleType and HealthLabSample.
"""

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.health.models import SampleType, HealthLabSample
from apps.health.api.serializers import SampleTypeSerializer, HealthLabSampleSerializer
from ..mixins import UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin


class SampleTypeViewSet(StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Sample Types.
    
    Provides CRUD operations for sample types used in lab testing.
    """
    queryset = SampleType.objects.all()
    serializer_class = SampleTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'name': ['exact', 'icontains']
    }
    search_fields = ['name', 'description']


class HealthLabSampleViewSet(UserAssignmentMixin, OptimizedQuerysetMixin, 
                            StandardFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Health Lab Samples.
    
    Provides CRUD operations and filtering for lab samples. Handles creation
    with historical batch-container assignment lookup based on the sample date.
    """
    queryset = HealthLabSample.objects.all().order_by('-sample_date', '-created_at')
    serializer_class = HealthLabSampleSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # To support file uploads
    user_field = 'recorded_by'  # Override the default user field name
    
    # OptimizedQuerysetMixin configuration
    select_related_fields = [
        'batch_container_assignment__batch',
        'batch_container_assignment__container',
        'sample_type',
        'recorded_by'
    ]
    
    # StandardFilterMixin configuration
    filterset_fields = {
        'batch_container_assignment__batch__id': ['exact'],
        'batch_container_assignment__container__id': ['exact'],
        'sample_type__id': ['exact'],
        'sample_date': ['exact', 'gte', 'lte'],
        'lab_reference_id': ['exact', 'icontains'],
        'recorded_by__id': ['exact']
    }
    search_fields = ['findings_summary', 'notes', 'lab_reference_id']
    
    def get_queryset(self):
        """
        Optionally restricts the returned samples based on query parameters.
        
        Extends the OptimizedQuerysetMixin's get_queryset method to add
        additional filtering based on query parameters.
        """
        queryset = super().get_queryset()
        
        # Additional filtering options
        batch_id = self.request.query_params.get('batch_id')
        container_id = self.request.query_params.get('container_id')
        sample_type_id = self.request.query_params.get('sample_type_id')
        
        if batch_id:
            queryset = queryset.filter(batch_container_assignment__batch_id=batch_id)
        if container_id:
            queryset = queryset.filter(batch_container_assignment__container_id=container_id)
        if sample_type_id:
            queryset = queryset.filter(sample_type_id=sample_type_id)
        
        return queryset
