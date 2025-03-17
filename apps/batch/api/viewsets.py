"""
ViewSets for the batch app API.

These ViewSets provide the CRUD operations for batch-related models.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.batch.api.serializers import (
    SpeciesSerializer,
    LifeCycleStageSerializer,
    BatchSerializer,
    BatchTransferSerializer,
    MortalityEventSerializer,
    GrowthSampleSerializer
)


class SpeciesViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Species instances."""
    
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'scientific_name']
    search_fields = ['name', 'scientific_name', 'description']
    ordering_fields = ['name', 'scientific_name', 'created_at']
    ordering = ['name']


class LifeCycleStageViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing LifeCycleStage instances."""
    
    queryset = LifeCycleStage.objects.all()
    serializer_class = LifeCycleStageSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'species', 'order']
    search_fields = ['name', 'description', 'species__name']
    ordering_fields = ['species__name', 'order', 'name', 'created_at']
    ordering = ['species__name', 'order']


class BatchViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Batch instances."""
    
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch_number', 'species', 'lifecycle_stage', 'container', 'status']
    search_fields = [
        'batch_number', 
        'species__name', 
        'lifecycle_stage__name', 
        'container__name',
        'notes'
    ]
    ordering_fields = [
        'batch_number', 
        'start_date', 
        'species__name', 
        'lifecycle_stage__name', 
        'biomass_kg',
        'population_count',
        'created_at'
    ]
    ordering = ['-created_at']


class BatchTransferViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing BatchTransfer instances."""
    
    queryset = BatchTransfer.objects.all()
    serializer_class = BatchTransferSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'source_batch', 
        'destination_batch', 
        'transfer_type', 
        'source_lifecycle_stage', 
        'destination_lifecycle_stage',
        'source_container',
        'destination_container'
    ]
    search_fields = [
        'source_batch__batch_number', 
        'destination_batch__batch_number',
        'notes'
    ]
    ordering_fields = [
        'transfer_date', 
        'source_batch__batch_number',
        'transfer_type',
        'created_at'
    ]
    ordering = ['-transfer_date']


class MortalityEventViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing MortalityEvent instances."""
    
    queryset = MortalityEvent.objects.all()
    serializer_class = MortalityEventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'date', 'cause']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['date', 'batch__batch_number', 'count', 'created_at']
    ordering = ['-date']


class GrowthSampleViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing GrowthSample instances."""
    
    queryset = GrowthSample.objects.all()
    serializer_class = GrowthSampleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'sample_date']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['sample_date', 'batch__batch_number', 'avg_weight_g', 'created_at']
    ordering = ['-sample_date']
