"""
ViewSets for the batch app API.

These ViewSets provide the CRUD operations for batch-related models.
"""
from django.db.models import Avg, Max, Min, Count, F, ExpressionWrapper, fields, Sum, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    BatchComposition,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.batch.api.serializers import (
    SpeciesSerializer,
    LifeCycleStageSerializer,
    BatchSerializer,
    BatchContainerAssignmentSerializer,
    BatchCompositionSerializer,
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
    filterset_fields = ['batch_number', 'species', 'lifecycle_stage', 'status', 'batch_type']
    search_fields = [
        'batch_number', 
        'species__name', 
        'lifecycle_stage__name', 
        'notes',
        'batch_type'
    ]
    ordering_fields = [
        'batch_number', 
        'start_date', 
        'species__name', 
        'lifecycle_stage__name', 
        # 'biomass_kg', # Removed, consider annotation for ordering by calculated field
        # 'population_count', # Removed, consider annotation for ordering by calculated field
        'created_at'
    ]
    ordering = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def growth_analysis(self, request, pk=None):
        """
        Calculate and return growth analysis metrics for a batch over time.
        
        Returns metrics like:
        - Growth rate over time
        - Weight gain trends
        - SGR (Specific Growth Rate)
        - TGC (Thermal Growth Coefficient) if temperature data is available
        
        URL: /api/v1/batch/batches/{pk}/growth_analysis/
        """
        batch = self.get_object()
        
        # Get all growth samples for this batch, ordered by sample_date
        growth_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('sample_date')
        
        if not growth_samples.exists():
            return Response(
                {'detail': 'No growth samples available for this batch.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Initialize response data structure
        result = {
            'batch_number': batch.batch_number,
            'species': batch.species.name,
            'lifecycle_stage': batch.lifecycle_stage.name,
            'start_date': batch.start_date,
            'current_avg_weight': batch.calculated_avg_weight_g, # Updated to use calculated property
            'growth_metrics': [],
            'summary': {}
        }
        
        # Process growth samples to calculate metrics
        prev_sample = None
        sgr_values = []
        weight_data = []
        
        for sample in growth_samples:
            sample_data = {
                'date': sample.sample_date,
                'avg_weight_g': float(sample.avg_weight_g),
                'avg_length_cm': float(sample.avg_length_cm) if sample.avg_length_cm else None,
                'condition_factor': float(sample.condition_factor) if sample.condition_factor else None,
            }
            
            # Add weight gain and SGR if we have a previous sample
            if prev_sample:
                days_diff = (sample.sample_date - prev_sample.sample_date).days
                if days_diff > 0:
                    # Calculate weight gain
                    weight_gain = sample.avg_weight_g - prev_sample.avg_weight_g
                    sample_data['weight_gain_g'] = float(weight_gain)
                    
                    # Calculate daily growth rate
                    daily_growth = weight_gain / days_diff
                    sample_data['daily_growth_g'] = float(daily_growth)
                    
                    # Calculate SGR (Specific Growth Rate)
                    # SGR = (ln(W2) - ln(W1)) / (t2 - t1) * 100
                    if prev_sample.avg_weight_g > 0:
                        import math
                        sgr = (math.log(float(sample.avg_weight_g)) - 
                               math.log(float(prev_sample.avg_weight_g))) / days_diff * 100
                        sample_data['sgr'] = round(sgr, 2)
                        sgr_values.append(sgr)
            
            weight_data.append(float(sample.avg_weight_g))
            result['growth_metrics'].append(sample_data)
            prev_sample = sample
        
        # Calculate summary statistics
        if growth_samples.count() > 1:
            first_sample = growth_samples.first()
            last_sample = growth_samples.last()
            total_days = (last_sample.sample_date - first_sample.sample_date).days
            
            if total_days > 0:
                total_weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g
                
                result['summary'] = {
                    'total_weight_gain_g': float(total_weight_gain),
                    'avg_daily_growth_g': float(total_weight_gain / total_days),
                    'samples_count': growth_samples.count(),
                    'measurement_period_days': total_days,
                    'avg_sgr': round(sum(sgr_values) / len(sgr_values), 2) if sgr_values else None,
                    'min_weight_g': min(weight_data),
                    'max_weight_g': max(weight_data)
                }
        
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def performance_metrics(self, request, pk=None):
        """
        Calculate and return performance metrics for a batch.
        
        Includes:
        - Mortality rates
        - Growth efficiency
        - Density metrics
        - Current status summary
        
        URL: /api/v1/batch/batches/{pk}/performance_metrics/
        """
        batch = self.get_object()
        
        # Initialize response data structure
        result = {
            'batch_number': batch.batch_number,
            'species': batch.species.name,
            'lifecycle_stage': batch.lifecycle_stage.name,
            'start_date': batch.start_date,
            'days_active': (timezone.now().date() - batch.start_date).days,
            'current_metrics': {
                'population_count': batch.population_count,
                'biomass_kg': float(batch.biomass_kg),
                'avg_weight_g': float(batch.avg_weight_g)
            },
        }
        
        # Calculate mortality metrics
        total_mortality = batch.mortality_events.aggregate(
            total_count=Sum('count'),
            total_biomass=Sum('biomass_kg')
        )
        
        if total_mortality['total_count']:
            # Get initial population (current + mortality)
            initial_population = batch.population_count + total_mortality['total_count']
            result['mortality_metrics'] = {
                'total_count': total_mortality['total_count'],
                'total_biomass_kg': float(total_mortality['total_biomass'] or 0),
                'mortality_rate': round((total_mortality['total_count'] / initial_population) * 100, 2),
            }
            
            # Get mortality by cause
            mortality_by_cause = batch.mortality_events.values('cause').annotate(
                count=Sum('count'),
                biomass=Sum('biomass_kg')
            ).order_by('-count')
            
            result['mortality_metrics']['by_cause'] = [
                {
                    'cause': item['cause'],
                    'count': item['count'],
                    'biomass_kg': float(item['biomass'] or 0),
                    'percentage': round((item['count'] / total_mortality['total_count']) * 100, 2)
                }
                for item in mortality_by_cause
            ]
        else:
            result['mortality_metrics'] = {
                'total_count': 0,
                'total_biomass_kg': 0,
                'mortality_rate': 0,
                'by_cause': []
            }
        
        # Calculate container metrics
        active_assignments = batch.container_assignments.filter(is_active=True)
        if active_assignments.exists():
            containers_data = []
            for assignment in active_assignments:
                # Calculate density
                if assignment.container.volume_m3:
                    density = assignment.biomass_kg / assignment.container.volume_m3
                else:
                    density = None
                
                containers_data.append({
                    'container_name': assignment.container.name,
                    'population': assignment.population_count,
                    'biomass_kg': float(assignment.biomass_kg),
                    'density_kg_m3': round(float(density), 2) if density else None,
                    'assignment_date': assignment.assignment_date
                })
            
            result['container_metrics'] = containers_data
        
        # Get growth metrics if available
        latest_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('-sample_date')[:5]
        if latest_samples.exists():
            growth_data = []
            for sample in latest_samples:
                growth_data.append({
                    'date': sample.sample_date,
                    'avg_weight_g': float(sample.avg_weight_g),
                    'sample_size': sample.sample_size,
                    'condition_factor': float(sample.condition_factor) if sample.condition_factor else None
                })
            
            result['recent_growth_samples'] = growth_data
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """
        Compare metrics between multiple batches.
        
        Query parameters:
        - batch_ids: Comma-separated list of batch IDs to compare
        - metrics: Comma-separated list of metrics to include (default: all)
          Options: growth, mortality, biomass, all
        
        Example URL: /api/v1/batch/batches/compare/?batch_ids=1,2,3&metrics=growth,mortality
        """
        batch_ids = request.query_params.get('batch_ids', '')
        metrics = request.query_params.get('metrics', 'all').lower()
        
        if not batch_ids:
            return Response(
                {'detail': 'batch_ids parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            batch_id_list = [int(id.strip()) for id in batch_ids.split(',')]
        except ValueError:
            return Response(
                {'detail': 'Invalid batch_ids format. Use comma-separated integers.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batches = Batch.objects.filter(id__in=batch_id_list)
        if not batches.exists():
            return Response(
                {'detail': 'No batches found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Process requested metrics
        include_growth = metrics in ('all', 'growth')
        include_mortality = metrics in ('all', 'mortality')
        include_biomass = metrics in ('all', 'biomass')
        
        # Initialize response with batch basic info
        result = {
            'batches': [
                {
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'species': batch.species.name,
                    'lifecycle_stage': batch.lifecycle_stage.name,
                    'status': batch.status,
                    'start_date': batch.start_date,
                    'days_active': (timezone.now().date() - batch.start_date).days,
                }
                for batch in batches
            ],
        }
        
        # Add growth metrics if requested
        if include_growth:
            growth_metrics = []
            
            for batch in batches:
                # Get first and last growth samples
                batch_growth_samples = GrowthSample.objects.filter(assignment__batch=batch).order_by('sample_date')
                first_sample = batch_growth_samples.first()
                last_sample = batch_growth_samples.last()
                
                batch_growth = {
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'current_avg_weight_g': float(batch.calculated_avg_weight_g),
                }
                
                if first_sample and last_sample and first_sample != last_sample:
                    days = (last_sample.sample_date - first_sample.sample_date).days
                    if days > 0:
                        weight_gain = last_sample.avg_weight_g - first_sample.avg_weight_g
                        daily_growth = weight_gain / days
                        
                        # Calculate SGR
                        import math
                        sgr = (math.log(float(last_sample.avg_weight_g)) - 
                              math.log(float(first_sample.avg_weight_g))) / days * 100
                        
                        batch_growth.update({
                            'initial_weight_g': float(first_sample.avg_weight_g),
                            'final_weight_g': float(last_sample.avg_weight_g),
                            'weight_gain_g': float(weight_gain),
                            'days': days,
                            'daily_growth_g': float(daily_growth),
                            'sgr': round(sgr, 2)
                        })
                
                growth_metrics.append(batch_growth)
            
            result['growth_comparison'] = growth_metrics
        
        # Add mortality metrics if requested
        if include_mortality:
            mortality_metrics = []
            
            for batch in batches:
                mortality_data = batch.mortality_events.aggregate(
                    total_count=Sum('count'),
                    total_biomass=Sum('biomass_kg')
                )
                
                batch_mortality = {
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'total_mortality': mortality_data['total_count'] or 0,
                    'mortality_biomass_kg': float(mortality_data['total_biomass'] or 0),
                }
                
                # Calculate mortality rate
                if mortality_data['total_count']:
                    initial_population = batch.calculated_population_count + mortality_data['total_count']
                    batch_mortality['mortality_rate'] = round(
                        (mortality_data['total_count'] / initial_population) * 100, 2
                    )
                else:
                    batch_mortality['mortality_rate'] = 0.0
                
                mortality_metrics.append(batch_mortality)
            
            result['mortality_comparison'] = mortality_metrics
        
        # Add biomass metrics if requested
        if include_biomass:
            biomass_metrics = []
            
            for batch in batches:
                # Get container assignments
                assignments = batch.batch_assignments.filter(is_active=True)
                
                # Calculate total volume if container has volume data
                total_volume = 0
                containers_with_volume = 0
                
                for assignment in assignments:
                    if assignment.container.volume_m3:
                        total_volume += assignment.container.volume_m3
                        containers_with_volume += 1
                
                batch_biomass = {
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'current_biomass_kg': float(batch.calculated_biomass_kg),
                    'population_count': batch.calculated_population_count,
                }
                
                # Add density if we have container volume
                if containers_with_volume > 0:
                    avg_density = batch.calculated_biomass_kg / total_volume
                    batch_biomass['avg_density_kg_m3'] = round(float(avg_density), 2)
                
                biomass_metrics.append(batch_biomass)
            
            result['biomass_comparison'] = biomass_metrics
        
        return Response(result)


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
        'source_assignment',
        'destination_assignment'
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
    filterset_fields = ['batch', 'event_date', 'cause']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['event_date', 'batch__batch_number', 'count', 'created_at']
    ordering = ['-event_date']


class BatchContainerAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing BatchContainerAssignment instances."""
    
    queryset = BatchContainerAssignment.objects.all()
    serializer_class = BatchContainerAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'container', 'is_active', 'assignment_date']
    search_fields = ['batch__batch_number', 'container__name']
    ordering_fields = [
        'assignment_date', 
        'batch__batch_number', 
        'container__name', 
        'population_count', 
        'biomass_kg'
    ]
    ordering = ['-assignment_date']


class BatchCompositionViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing BatchComposition instances."""
    
    queryset = BatchComposition.objects.all()
    serializer_class = BatchCompositionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mixed_batch', 'source_batch']
    search_fields = ['mixed_batch__batch_number', 'source_batch__batch_number']
    ordering_fields = [
        'mixed_batch__batch_number', 
        'source_batch__batch_number', 
        'percentage', 
        'population_count', 
        'biomass_kg'
    ]
    ordering = ['mixed_batch__batch_number', 'percentage']


class GrowthSampleViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing GrowthSample instances."""
    
    queryset = GrowthSample.objects.all()
    serializer_class = GrowthSampleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'sample_date']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['sample_date', 'batch__batch_number', 'avg_weight_g', 'created_at']
    ordering = ['-sample_date']
