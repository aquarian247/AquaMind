"""
ViewSets for the Broodstock Management app.

This module contains ViewSets for all broodstock models with comprehensive
filtering, searching, ordering, and custom actions.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.broodstock.models import (
    MaintenanceTask, BroodstockFish, FishMovement, BreedingPlan,
    BreedingTraitPriority, BreedingPair, EggProduction, EggSupplier,
    ExternalEggBatch, BatchParentage
)
from apps.broodstock.serializers import (
    MaintenanceTaskSerializer, BroodstockFishSerializer, FishMovementSerializer,
    BreedingPlanSerializer, BreedingTraitPrioritySerializer, BreedingPairSerializer,
    EggProductionSerializer, EggSupplierSerializer, ExternalEggBatchSerializer,
    BatchParentageSerializer, EggProductionDetailSerializer
)


class MaintenanceTaskViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for maintenance tasks. Uses HistoryReasonMixin to capture audit change reasons."""

    user_field = 'created_by'
    queryset = MaintenanceTask.objects.all()
    serializer_class = MaintenanceTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['container', 'task_type', 'completed_date']
    search_fields = ['notes', 'container__name']
    ordering_fields = ['scheduled_date', 'created_at']
    ordering = ['-scheduled_date']
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue maintenance tasks."""
        overdue_tasks = self.get_queryset().filter(
            completed_date__isnull=True,
            scheduled_date__lt=timezone.now()
        )
        serializer = self.get_serializer(overdue_tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a maintenance task as completed."""
        task = self.get_object()
        if task.completed_date:
            return Response(
                {'error': 'Task is already completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task.completed_date = timezone.now()
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)


class BroodstockFishViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for broodstock fish with HistoryReasonMixin providing audit change reasons."""

    queryset = BroodstockFish.objects.all()
    serializer_class = BroodstockFishSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['container', 'health_status']
    search_fields = ['id', 'container__name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related('container')
    
    @action(detail=False, methods=['get'])
    def healthy(self, request):
        """Get all healthy broodstock fish."""
        healthy_fish = self.get_queryset().filter(health_status='healthy')
        serializer = self.get_serializer(healthy_fish, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='container_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the container to list broodstock fish for.',
                required=True,
            ),
        ],
        responses=BroodstockFishSerializer(many=True),
    )
    @action(detail=False, methods=['get'])
    def by_container(self, request):
        """Get fish grouped by container."""
        container_id = request.query_params.get('container_id')
        if not container_id:
            return Response(
                {'error': 'container_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        fish = self.get_queryset().filter(container_id=container_id)
        serializer = self.get_serializer(fish, many=True)
        return Response(serializer.data)


class FishMovementViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for fish movements leveraging HistoryReasonMixin for audit change reasons."""

    user_field = 'moved_by'
    queryset = FishMovement.objects.all()
    serializer_class = FishMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fish', 'from_container', 'to_container', 'movement_date']
    search_fields = ['notes', 'fish__id']
    ordering_fields = ['movement_date', 'created_at']
    ordering = ['-movement_date']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related(
            'fish', 'from_container', 'to_container', 'moved_by'
        )
    
    @action(detail=False, methods=['post'])
    def bulk_transfer(self, request):
        """Transfer multiple fish between containers."""
        fish_ids = request.data.get('fish_ids', [])
        from_container_id = request.data.get('from_container_id')
        to_container_id = request.data.get('to_container_id')
        notes = request.data.get('notes', '')
        
        if not all([fish_ids, from_container_id, to_container_id]):
            return Response(
                {'error': 'fish_ids, from_container_id, and to_container_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movements = []
        with transaction.atomic():
            for fish_id in fish_ids:
                movement_data = {
                    'fish': fish_id,
                    'from_container': from_container_id,
                    'to_container': to_container_id,
                    'notes': notes
                }
                serializer = self.get_serializer(data=movement_data)
                serializer.is_valid(raise_exception=True)
                movement = serializer.save(moved_by=request.user)
                movements.append(movement)
        
        serializer = self.get_serializer(movements, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BreedingPlanViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for breeding plans with HistoryReasonMixin-driven audit change reasons."""

    user_field = 'created_by'
    queryset = BreedingPlan.objects.all()
    serializer_class = BreedingPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['start_date', 'end_date']
    search_fields = ['name', 'objectives', 'geneticist_notes', 'breeder_instructions']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_queryset(self):
        """Optimize queryset with prefetch_related."""
        return super().get_queryset().prefetch_related('trait_priorities')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all currently active breeding plans."""
        now = timezone.now()
        active_plans = self.get_queryset().filter(
            start_date__lte=now,
            end_date__gte=now
        )
        serializer = self.get_serializer(active_plans, many=True)
        return Response(serializer.data)


class BreedingTraitPriorityViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for breeding trait priorities with HistoryReasonMixin auditing support."""

    queryset = BreedingTraitPriority.objects.all()
    serializer_class = BreedingTraitPrioritySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['plan', 'trait_name']
    ordering_fields = ['priority_weight', 'created_at']
    ordering = ['-priority_weight']


class BreedingPairViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for breeding pairs leveraging HistoryReasonMixin to capture audit change reasons."""

    queryset = BreedingPair.objects.all()
    serializer_class = BreedingPairSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['plan', 'male_fish', 'female_fish', 'pairing_date']
    search_fields = ['male_fish__id', 'female_fish__id']
    ordering_fields = ['pairing_date', 'created_at']
    ordering = ['-pairing_date']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related(
            'plan', 'male_fish', 'female_fish'
        )
    
    @action(detail=True, methods=['post'])
    def record_progeny(self, request, pk=None):
        """Record progeny count for a breeding pair."""
        pair = self.get_object()
        progeny_count = request.data.get('progeny_count')
        
        if not progeny_count:
            return Response(
                {'error': 'progeny_count is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pair.progeny_count = progeny_count
        pair.save()
        serializer = self.get_serializer(pair)
        return Response(serializer.data)


class EggSupplierViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for egg suppliers using HistoryReasonMixin for audit change reasons."""

    queryset = EggSupplier.objects.all()
    serializer_class = EggSupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_details', 'certifications']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class EggProductionViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for egg production with HistoryReasonMixin ensuring audit change reasons."""

    queryset = EggProduction.objects.all()
    serializer_class = EggProductionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_type', 'pair', 'destination_station', 'production_date']
    search_fields = ['egg_batch_id']
    ordering_fields = ['production_date', 'egg_count', 'created_at']
    ordering = ['-production_date']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related(
            'pair', 'destination_station'
        ).prefetch_related('batch_assignments')
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action."""
        if self.action == 'retrieve':
            return EggProductionDetailSerializer
        return super().get_serializer_class()
    
    @action(detail=False, methods=['post'])
    def produce_internal(self, request):
        """
        Create internal egg production from a breeding pair.
        
        Delegates to EggManagementService for proper validation including:
        - Active breeding plan validation
        - Fish health status checks
        - Automatic progeny count updates
        - Unique batch ID generation
        """
        from apps.broodstock.services.egg_management_service import EggManagementService
        from apps.broodstock.models import BreedingPair
        from apps.infrastructure.models import FreshwaterStation
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        pair_id = request.data.get('pair_id')
        egg_count = request.data.get('egg_count')
        destination_station_id = request.data.get('destination_station_id')
        
        # Basic required field validation
        if not all([pair_id, egg_count]):
            return Response(
                {'error': 'pair_id and egg_count are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate egg count is positive
        try:
            egg_count = int(egg_count)
            if egg_count <= 0:
                return Response(
                    {'error': 'egg_count must be positive.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'egg_count must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get breeding pair
        try:
            breeding_pair = BreedingPair.objects.select_related(
                'plan', 'male_fish', 'female_fish'
            ).get(id=pair_id)
        except BreedingPair.DoesNotExist:
            return Response(
                {'error': f'Breeding pair with id {pair_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get destination station if provided
        destination_station = None
        if destination_station_id:
            try:
                destination_station = FreshwaterStation.objects.get(id=destination_station_id)
            except FreshwaterStation.DoesNotExist:
                return Response(
                    {'error': f'Freshwater station with id {destination_station_id} not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Delegate to service with proper validation
        try:
            egg_production = EggManagementService.produce_internal_eggs(
                breeding_pair=breeding_pair,
                egg_count=egg_count,
                destination_station=destination_station
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return serialized response
        serializer = EggProductionDetailSerializer(egg_production)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def acquire_external(self, request):
        """
        Create external egg acquisition.
        
        Delegates to EggManagementService for proper validation including:
        - Duplicate batch number prevention
        - Atomic transaction handling
        - Unique batch ID generation
        """
        from apps.broodstock.services.egg_management_service import EggManagementService
        from apps.broodstock.models import EggSupplier
        from apps.infrastructure.models import FreshwaterStation
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        supplier_id = request.data.get('supplier_id')
        batch_number = request.data.get('batch_number')
        egg_count = request.data.get('egg_count')
        provenance_data = request.data.get('provenance_data', '')
        destination_station_id = request.data.get('destination_station_id')
        
        # Basic required field validation
        if not all([supplier_id, batch_number, egg_count]):
            return Response(
                {'error': 'supplier_id, batch_number, and egg_count are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate egg count is positive
        try:
            egg_count = int(egg_count)
            if egg_count <= 0:
                return Response(
                    {'error': 'egg_count must be positive.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'egg_count must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get supplier
        try:
            supplier = EggSupplier.objects.get(id=supplier_id)
        except EggSupplier.DoesNotExist:
            return Response(
                {'error': f'Egg supplier with id {supplier_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get destination station if provided
        destination_station = None
        if destination_station_id:
            try:
                destination_station = FreshwaterStation.objects.get(id=destination_station_id)
            except FreshwaterStation.DoesNotExist:
                return Response(
                    {'error': f'Freshwater station with id {destination_station_id} not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Delegate to service with proper validation (includes duplicate check)
        try:
            egg_production, external_batch = EggManagementService.acquire_external_eggs(
                supplier=supplier,
                batch_number=batch_number,
                egg_count=egg_count,
                provenance_data=provenance_data,
                destination_station=destination_station
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return serialized response with external batch data
        serializer = EggProductionDetailSerializer(egg_production)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExternalEggBatchViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for external egg batches using HistoryReasonMixin for audit change reasons."""

    queryset = ExternalEggBatch.objects.all()
    serializer_class = ExternalEggBatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'egg_production']
    search_fields = ['batch_number', 'provenance_data']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related(
            'supplier', 'egg_production'
        )


class BatchParentageViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for batch parentage with HistoryReasonMixin ensuring audit change reasons."""

    queryset = BatchParentage.objects.all()
    serializer_class = BatchParentageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['batch', 'egg_production', 'assignment_date']
    ordering_fields = ['assignment_date', 'created_at']
    ordering = ['-assignment_date']
    
    def get_queryset(self):
        """Optimize queryset with select_related."""
        return super().get_queryset().select_related(
            'batch', 'egg_production'
        )
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='batch_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the batch to retrieve lineage information for.',
                required=True,
            ),
        ],
        responses=BatchParentageSerializer(many=True),
    )
    @action(detail=False, methods=['get'])
    def lineage(self, request):
        """Get complete lineage for a batch."""
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {'error': 'batch_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parentages = self.get_queryset().filter(batch_id=batch_id)
        serializer = self.get_serializer(parentages, many=True)
        return Response(serializer.data)
