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

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

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
from aquamind.utils.history_mixins import HistoryReasonMixin

class SpeciesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing aquaculture Species.

    Provides CRUD operations for species, including filtering by name
    and scientific name, searching across name, scientific name, and description,
    and ordering by name, scientific name, or creation date.
    """
    # NOTE: Authentication temporarily disabled in development to allow
    # the React frontend (which currently has no login flow) to access
    # these endpoints.  Re-enable once frontend auth is implemented.
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'scientific_name']
    search_fields = ['name', 'scientific_name', 'description']
    ordering_fields = ['name', 'scientific_name', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class LifeCycleStageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Species Life Cycle Stages.

    Provides CRUD operations for life cycle stages, specific to a species.
    Allows filtering by name, species, and order.
    Supports searching across name, description, and species name.
    Ordering can be done by species name, order, name, or creation date.
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
    queryset = LifeCycleStage.objects.all()
    serializer_class = LifeCycleStageSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'species', 'order']
    search_fields = ['name', 'description', 'species__name']
    ordering_fields = ['species__name', 'order', 'name', 'created_at']
    ordering = ['species__name', 'order']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class BatchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for comprehensive management of aquaculture Batches.

    Provides full CRUD operations for batches, including detailed filtering,
    searching, and ordering capabilities. Batches represent groups of aquatic
    organisms managed together through their lifecycle.

    **Filtering:**
    - `batch_number`: Exact match.
    - `species`: Exact match by Species ID.
    - `lifecycle_stage`: Exact match by LifeCycleStage ID.
    - `status`: Exact match by status string (e.g., 'ACTIVE', 'PLANNED').
    - `batch_type`: Exact match by type string (e.g., 'PRODUCTION', 'EXPERIMENTAL').

    **Searching:**
    - `batch_number`: Partial match.
    - `species__name`: Partial match on the related Species name.
    - `lifecycle_stage__name`: Partial match on the related LifeCycleStage name.
    - `notes`: Partial match on the batch notes.
    - `batch_type`: Partial match on the batch type.

    **Ordering:**
    - `batch_number`
    - `start_date`
    - `species__name`
    - `lifecycle_stage__name`
    - `created_at` (default: descending)
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
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

    def list(self, request, *args, **kwargs):
        """
        Retrieve a list of batches.

        Supports filtering by fields like `batch_number`, `species`, `lifecycle_stage`, `status`, and `batch_type`.
        Supports searching across `batch_number`, `species__name`, `lifecycle_stage__name`, `notes`, and `batch_type`.
        Supports ordering by `batch_number`, `start_date`, `species__name`, `lifecycle_stage__name`, and `created_at`.
        """
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Create a new batch.

        Requires details such as `batch_number`, `species`, `lifecycle_stage`, `status`, `batch_type`, and `start_date`.
        `expected_end_date` will default to 30 days after `start_date` if not provided.
        """
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
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
    """
    API endpoint for managing Batch Transfers.

    Batch transfers record the movement of organisms between batches or changes
    in their lifecycle stage or container assignment within the same batch.
    This endpoint provides full CRUD operations for batch transfers.

    **Filtering:**
    - `source_batch`: ID of the source batch.
    - `destination_batch`: ID of the destination batch.
    - `transfer_type`: Type of transfer (e.g., 'SPLIT', 'MERGE', 'MOVE', 'LIFECYCLE_CHANGE').
    - `source_lifecycle_stage`: ID of the source lifecycle stage.
    - `destination_lifecycle_stage`: ID of the destination lifecycle stage.
    - `source_assignment`: ID of the source batch container assignment.
    - `destination_assignment`: ID of the destination batch container assignment.

    **Searching:**
    - `source_batch__batch_number`: Batch number of the source batch.
    - `destination_batch__batch_number`: Batch number of the destination batch.
    - `notes`: Notes associated with the transfer.

    **Ordering:**
    - `transfer_date` (default: descending)
    - `source_batch__batch_number`
    - `transfer_type`
    - `created_at`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
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

class MortalityEventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Mortality Events in aquaculture batches.

    Mortality events record the number of deaths in a batch on a specific date,
    along with the suspected cause and any relevant notes. This endpoint
    provides full CRUD operations for mortality events.

    **Filtering:**
    - `batch`: ID of the batch associated with the mortality event.
    - `event_date`: Exact date of the mortality event.
    - `cause`: Suspected cause of mortality (e.g., 'DISEASE', 'PREDATION', 'HANDLING').

    **Searching:**
    - `batch__batch_number`: Batch number of the associated batch.
    - `notes`: Notes associated with the mortality event.

    **Ordering:**
    - `event_date` (default: descending)
    - `batch__batch_number`
    - `count` (number of mortalities)
    - `created_at`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
    queryset = MortalityEvent.objects.all()
    serializer_class = MortalityEventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'event_date', 'cause']
    # Use the correct model field name "description" instead of the
    # non-existent "notes" to avoid FieldError during search filtering
    search_fields = ['batch__batch_number', 'description']
    ordering_fields = ['event_date', 'batch__batch_number', 'count', 'created_at']
    ordering = ['-event_date']

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

class BatchContainerAssignmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Container Assignments.

    This endpoint handles the assignment of batches (or parts of batches)
    to specific containers (e.g., tanks, ponds, cages) at a given point in time.
    It records the population count and biomass within that container.
    Provides full CRUD operations for these assignments.

    An assignment can be marked as inactive when a batch is moved out of a container.

    **Filtering:**
    - `batch`: ID of the assigned batch.
    - `container`: ID of the assigned container.
    - `is_active`: Boolean indicating if the assignment is currently active.
    - `assignment_date`: Exact date of the assignment.

    **Searching:**
    - `batch__batch_number`: Batch number of the assigned batch.
    - `container__name`: Name of the assigned container.

    **Ordering:**
    - `assignment_date` (default: descending)
    - `batch__batch_number`
    - `container__name`
    - `population_count`
    - `biomass_kg`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
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

    def apply_location_filters(self, queryset, request):
        """
        Apply location-based filters to the BatchContainerAssignment queryset.

        Filters supported:
        - geography: Filter by Geography ID (through hall->station or area)
        - area: Filter by Area ID (direct container area)
        - station: Filter by FreshwaterStation ID (through hall)
        - hall: Filter by Hall ID (direct container hall)
        - container_type: Filter by ContainerType category slug (TANK, PEN, TRAY, OTHER)

        Returns filtered queryset or raises ValidationError for invalid IDs.
        """
        filters_applied = Q()

        # Geography filter (affects both hall and area containers)
        geography_id = request.query_params.get('geography')
        if geography_id:
            try:
                geography_id = int(geography_id)
                # Validate geography exists
                from apps.infrastructure.models import Geography
                if not Geography.objects.filter(id=geography_id).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'geography': 'Geography not found'})
                # Filter containers that are either in halls of stations in this geography
                # OR directly in areas in this geography
                filters_applied &= (
                    Q(container__hall__freshwater_station__geography_id=geography_id) |
                    Q(container__area__geography_id=geography_id)
                )
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'geography': 'Invalid geography ID'})

        # Area filter (only affects containers directly in areas)
        area_id = request.query_params.get('area')
        if area_id:
            try:
                area_id = int(area_id)
                # Validate area exists
                from apps.infrastructure.models import Area
                if not Area.objects.filter(id=area_id).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'area': 'Area not found'})
                filters_applied &= Q(container__area_id=area_id)
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'area': 'Invalid area ID'})

        # Station filter (only affects containers in halls)
        station_id = request.query_params.get('station')
        if station_id:
            try:
                station_id = int(station_id)
                # Validate station exists
                from apps.infrastructure.models import FreshwaterStation
                if not FreshwaterStation.objects.filter(id=station_id).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'station': 'Freshwater station not found'})
                filters_applied &= Q(container__hall__freshwater_station_id=station_id)
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'station': 'Invalid freshwater station ID'})

        # Hall filter (only affects containers in halls)
        hall_id = request.query_params.get('hall')
        if hall_id:
            try:
                hall_id = int(hall_id)
                # Validate hall exists
                from apps.infrastructure.models import Hall
                if not Hall.objects.filter(id=hall_id).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'hall': 'Hall not found'})
                filters_applied &= Q(container__hall_id=hall_id)
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'hall': 'Invalid hall ID'})

        # Container type filter (by category)
        container_type = request.query_params.get('container_type')
        if container_type:
            # Validate that the category exists
            from apps.infrastructure.models import ContainerType
            if not ContainerType.objects.filter(category=container_type.upper()).exists():
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'container_type': f'Invalid container type. Must be one of: {[choice[0] for choice in ContainerType.CONTAINER_CATEGORIES]}'
                })
            filters_applied &= Q(container__container_type__category=container_type.upper())

        return queryset.filter(filters_applied) if filters_applied else queryset

    # ------------------------------------------------------------------ #
    # Aggregated summary endpoint                                        #
    # ------------------------------------------------------------------ #
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(30))
    @extend_schema(
        operation_id="batch-container-assignments-summary",
        summary="Get aggregated summary of batch container assignments",
        description="Returns aggregated metrics for batch container assignments with optional location-based filtering.",
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status (default: true). Set to false to include inactive assignments.",
                required=False,
                default=True,
            ),
            OpenApiParameter(
                name="geography",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by geography ID. Affects containers in both halls and areas within this geography.",
                required=False,
            ),
            OpenApiParameter(
                name="area",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by area ID. Only affects containers directly assigned to this area.",
                required=False,
            ),
            OpenApiParameter(
                name="station",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by freshwater station ID. Only affects containers in halls within this station.",
                required=False,
            ),
            OpenApiParameter(
                name="hall",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by hall ID. Only affects containers directly in this hall.",
                required=False,
            ),
            OpenApiParameter(
                name="container_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by container type category. Valid values: TANK, PEN, TRAY, OTHER.",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "active_biomass_kg": {"type": "number", "description": "Total biomass in kg for active assignments"},
                    "count": {"type": "integer", "description": "Total number of assignments matching filters"},
                },
                "required": ["active_biomass_kg", "count"],
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "geography": {"type": "array", "items": {"type": "string"}},
                    "area": {"type": "array", "items": {"type": "string"}},
                    "station": {"type": "array", "items": {"type": "string"}},
                    "hall": {"type": "array", "items": {"type": "string"}},
                    "container_type": {"type": "array", "items": {"type": "string"}},
                },
                "description": "Validation error for invalid filter parameters",
            },
        },
        examples=[
            {
                "summary": "Default summary (all active assignments)",
                "value": {
                    "active_biomass_kg": 1250.5,
                    "count": 45,
                },
            },
            {
                "summary": "Filtered by geography",
                "parameters": {"geography": 1},
                "value": {
                    "active_biomass_kg": 750.0,
                    "count": 28,
                },
            },
            {
                "summary": "Filtered by container type",
                "parameters": {"container_type": "TANK"},
                "value": {
                    "active_biomass_kg": 950.2,
                    "count": 32,
                },
            },
        ],
    )
    def summary(self, request):
        """
        Return aggregated metrics about batch-container assignments with optional location filtering.

        Query Parameters
        ----------------
        is_active : bool (default ``true``)
            If ``true`` (default) aggregates only active assignments.
            If ``false`` aggregates inactive assignments.
        geography : int
            Filter by geography ID (affects containers in halls and areas).
        area : int
            Filter by area ID (containers directly in this area).
        station : int
            Filter by freshwater station ID (containers in halls of this station).
        hall : int
            Filter by hall ID (containers directly in this hall).
        container_type : str
            Filter by container type category (TANK, PEN, TRAY, OTHER).

        Response Schema
        ---------------
        {
            "active_biomass_kg": number,
            "count": integer
        }
        """
        is_active_param = request.query_params.get("is_active", "true").lower()
        is_active = is_active_param != "false"

        assignments = self.get_queryset().filter(is_active=is_active)

        # Apply location filters
        assignments = self.apply_location_filters(assignments, request)

        aggregates = assignments.aggregate(
            active_biomass_kg=Sum("biomass_kg"),
            count=Count("id"),
        )

        return Response(
            {
                "active_biomass_kg": float(aggregates["active_biomass_kg"] or 0),
                "count": aggregates["count"] or 0,
            }
        )

class BatchCompositionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Compositions.

    This endpoint defines the composition of a 'mixed' batch, detailing what
    percentage and quantity (population/biomass) of it comes from various
    'source' batches. This is crucial for traceability when batches are merged.
    Provides full CRUD operations for batch composition records.

    **Filtering:**
    - `mixed_batch`: ID of the resulting mixed batch.
    - `source_batch`: ID of a source batch contributing to the mixed batch.

    **Searching:**
    - `mixed_batch__batch_number`: Batch number of the mixed batch.
    - `source_batch__batch_number`: Batch number of the source batch.

    **Ordering:**
    - `mixed_batch__batch_number` (default)
    - `source_batch__batch_number`
    - `percentage` (default)
    - `population_count`
    - `biomass_kg`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    
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

class GrowthSampleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Growth Samples from aquaculture batches.

    Growth samples record the average weight of organisms in a batch (or a specific
    container assignment of a batch) on a particular date. This data is essential
    for tracking growth, calculating feed conversion ratios, and making management decisions.
    This endpoint provides full CRUD operations for growth samples.

    **Filtering:**
    - `assignment__batch`: ID of the batch associated with the growth sample (via BatchContainerAssignment).
    - `sample_date`: Exact date of the sample.

    **Searching:**
    - `batch__batch_number`: Batch number of the associated batch. (Searches through the related Batch model via the assignment)
    - `notes`: Notes associated with the growth sample.

    **Ordering:**
    - `sample_date` (default: descending)
    - `batch__batch_number`: Batch number of the associated batch. (Orders based on the related Batch model via the assignment)
    - `avg_weight_g`: Average weight in grams.
    - `created_at`
    """
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = GrowthSample.objects.all()
    serializer_class = GrowthSampleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assignment__batch', 'sample_date']
    search_fields = ['batch__batch_number', 'notes']
    ordering_fields = ['sample_date', 'batch__batch_number', 'avg_weight_g', 'created_at']
    ordering = ['-sample_date']

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
