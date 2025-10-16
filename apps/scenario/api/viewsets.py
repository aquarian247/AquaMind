"""
ViewSets for the Scenario Planning API.

Provides REST endpoints for scenario management and data entry operations.
"""
import io
import csv
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Count, Avg, F
from django.db.models.functions import Mod
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.scenario.models import (
    TemperatureProfile, TGCModel, FCRModel, MortalityModel,
    Scenario, BiologicalConstraints, ScenarioModelChange
)
from apps.scenario.services import BulkDataImportService, DateRangeInputService
from apps.scenario.services.calculations import ProjectionEngine
# Import serializers directly from the serializers.py file
from apps.scenario.api.serializers import (
    BatchInitializationSerializer,
    BiologicalConstraintsSerializer,
    BulkDateRangeSerializer,
    CSVTemplateRequestSerializer,
    CSVUploadSerializer,
    DataValidationResultSerializer,
    FCRModelSerializer,
    MortalityModelSerializer,
    ProjectionChartSerializer,
    ScenarioComparisonSerializer,
    ScenarioDuplicateSerializer,
    ScenarioProjectionSerializer,
    ScenarioSerializer,
    TemperatureProfileSerializer,
    TGCModelSerializer,
)


class TemperatureProfileViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for temperature profiles with audit trail support."""
    
    queryset = TemperatureProfile.objects.annotate(
        reading_count=Count('readings')
    )
    serializer_class = TemperatureProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_csv(self, request):
        """
        Upload temperature data from CSV file.
        
        Expected CSV format:
        date,temperature
        2024-01-01,8.5
        2024-01-02,8.7
        """
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get validated data
        csv_file = serializer.validated_data['file']
        profile_name = serializer.validated_data['profile_name']
        validate_only = serializer.validated_data['validate_only']
        
        # Convert uploaded file to StringIO
        file_content = csv_file.read().decode('utf-8')
        csv_io = io.StringIO(file_content)
        
        # Process with service
        service = BulkDataImportService()
        success, result = service.import_temperature_data(
            csv_io, profile_name, validate_only
        )
        
        # Return validation result
        result_serializer = DataValidationResultSerializer(data=result)
        result_serializer.is_valid()
        
        return Response(
            result_serializer.data,
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['post'])
    def bulk_date_ranges(self, request):
        """
        Create temperature profile from date ranges.
        
        Example request:
        {
            "profile_name": "Winter 2024",
            "ranges": [
                {"start_date": "2024-01-01", "end_date": "2024-01-31", "value": 8.5},
                {"start_date": "2024-02-01", "end_date": "2024-02-28", "value": 9.0}
            ],
            "merge_adjacent": true,
            "fill_gaps": true,
            "interpolation_method": "linear"
        }
        """
        serializer = BulkDateRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract data
        data = serializer.validated_data
        
        # Process with service
        service = DateRangeInputService()
        
        # Add ranges
        for range_data in data['ranges']:
            service.add_range(
                range_data['start_date'],
                range_data['end_date'],
                range_data['value']
            )
        
        # Merge if requested
        if data['merge_adjacent']:
            service.merge_adjacent_ranges()
        
        # Validate
        if not service.validate_ranges():
            return Response(
                {
                    'success': False,
                    'errors': service.errors,
                    'warnings': service.warnings
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save to database
        profile = service.save_as_temperature_profile(
            data['profile_name'],
            fill_gaps=data['fill_gaps'],
            interpolation_method=data['interpolation_method']
        )
        
        if profile:
            # Return created profile
            profile_serializer = TemperatureProfileSerializer(profile)
            return Response(
                profile_serializer.data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {
                    'success': False,
                    'errors': service.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download CSV template for temperature data."""
        service = BulkDataImportService()
        template_content = service.generate_csv_template('temperature')
        
        response = HttpResponse(template_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="temperature_template.csv"'
        return response
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get temperature statistics for a profile."""
        profile = self.get_object()
        readings = profile.readings.all()
        
        if not readings.exists():
            return Response(
                {'message': 'No temperature data available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        temps = [r.temperature for r in readings]
        
        return Response({
            'profile_name': profile.name,
            'statistics': {
                'min': min(temps),
                'max': max(temps),
                'avg': sum(temps) / len(temps),
                'count': len(temps),
                'date_range': {
                    'start': readings.order_by('day_number').first().day_number,
                    'end': readings.order_by('day_number').last().day_number
                }
            }
        })


class TGCModelViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """Enhanced ViewSet for TGC models with audit trail support."""
    
    queryset = TGCModel.objects.select_related('profile').prefetch_related('stage_overrides')
    serializer_class = TGCModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['location', 'release_period']
    search_fields = ['name', 'location']
    ordering_fields = ['name', 'location', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get predefined TGC model templates."""
        templates = [
            {
                'name': 'Standard Scottish TGC',
                'location': 'Scotland',
                'release_period': 'Spring',
                'tgc_value': 0.025,
                'exponent_n': 0.33,
                'exponent_m': 0.66,
                'description': 'Standard TGC model for Scottish waters with spring release'
            },
            {
                'name': 'Norwegian Winter TGC',
                'location': 'Norway',
                'release_period': 'Winter',
                'tgc_value': 0.022,
                'exponent_n': 0.35,
                'exponent_m': 0.65,
                'description': 'Optimized for Norwegian fjords with winter release'
            },
            {
                'name': 'Faroe Islands TGC',
                'location': 'Faroe Islands',
                'release_period': 'Year-round',
                'tgc_value': 0.024,
                'exponent_n': 0.33,
                'exponent_m': 0.66,
                'description': 'Adapted for Faroe Islands conditions'
            }
        ]
        
        return Response(templates)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a TGC model with a new name."""
        original = self.get_object()
        new_name = request.data.get('new_name')
        
        if not new_name:
            return Response(
                {'error': 'new_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if TGCModel.objects.filter(name=new_name).exists():
            return Response(
                {'error': 'A TGC model with this name already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create duplicate
        duplicate = TGCModel.objects.create(
            name=new_name,
            location=original.location,
            release_period=original.release_period,
            tgc_value=original.tgc_value,
            exponent_n=original.exponent_n,
            exponent_m=original.exponent_m,
            profile=original.profile
        )
        
        # Copy stage overrides
        for stage_override in original.stage_overrides.all():
            stage_override.pk = None
            stage_override.tgc_model = duplicate
            stage_override.save()
        
        serializer = TGCModelSerializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FCRModelViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """Enhanced ViewSet for FCR models with audit trail support."""
    
    queryset = FCRModel.objects.prefetch_related('stages__stage', 'stages__overrides')
    serializer_class = FCRModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get predefined FCR model templates."""
        templates = [
            {
                'name': 'Standard FCR Model',
                'description': 'Standard FCR progression across lifecycle stages',
                'stages': [
                    {'stage': 'Fry', 'fcr': 0.8, 'duration': 60},
                    {'stage': 'Parr', 'fcr': 0.9, 'duration': 90},
                    {'stage': 'Smolt', 'fcr': 1.0, 'duration': 60},
                    {'stage': 'Post-Smolt', 'fcr': 1.1, 'duration': 120},
                    {'stage': 'Harvest', 'fcr': 1.2, 'duration': 365}
                ]
            },
            {
                'name': 'Optimized FCR Model',
                'description': 'Optimized FCR for high-performance feeds',
                'stages': [
                    {'stage': 'Fry', 'fcr': 0.7, 'duration': 60},
                    {'stage': 'Parr', 'fcr': 0.8, 'duration': 90},
                    {'stage': 'Smolt', 'fcr': 0.9, 'duration': 60},
                    {'stage': 'Post-Smolt', 'fcr': 1.0, 'duration': 120},
                    {'stage': 'Harvest', 'fcr': 1.1, 'duration': 365}
                ]
            }
        ]
        
        return Response(templates)
    
    @action(detail=True, methods=['get'])
    def stage_summary(self, request, pk=None):
        """Get summary of stages for an FCR model."""
        fcr_model = self.get_object()
        stages = fcr_model.stages.select_related('stage').order_by('stage__expected_weight_min_g')
        
        summary = {
            'model_name': fcr_model.name,
            'total_stages': stages.count(),
            'total_duration': sum(s.duration_days for s in stages),
            'average_fcr': stages.aggregate(avg_fcr=Avg('fcr_value'))['avg_fcr'],
            'stages': [
                {
                    'stage': s.stage.name,
                    'fcr': float(s.fcr_value),
                    'duration': s.duration_days,
                    'overrides': s.overrides.count()
                }
                for s in stages
            ]
        }
        
        return Response(summary)


class MortalityModelViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """Enhanced ViewSet for mortality models with audit trail support."""
    
    queryset = MortalityModel.objects.prefetch_related('stage_overrides')
    serializer_class = MortalityModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['frequency']
    search_fields = ['name']
    ordering_fields = ['name', 'rate', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get predefined mortality model templates."""
        templates = [
            {
                'name': 'Low Mortality',
                'frequency': 'daily',
                'rate': 0.02,
                'description': 'Low mortality rate for optimal conditions'
            },
            {
                'name': 'Standard Mortality',
                'frequency': 'daily',
                'rate': 0.05,
                'description': 'Industry standard mortality rate'
            },
            {
                'name': 'High Mortality',
                'frequency': 'daily',
                'rate': 0.1,
                'description': 'Higher mortality for challenging conditions'
            },
            {
                'name': 'Weekly Standard',
                'frequency': 'weekly',
                'rate': 0.35,
                'description': 'Standard weekly mortality rate'
            }
        ]
        
        return Response(templates)


class BiologicalConstraintsViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """ViewSet for biological constraints with audit trail support."""
    
    queryset = BiologicalConstraints.objects.prefetch_related('stage_constraints')
    serializer_class = BiologicalConstraintsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active constraint sets."""
        active_constraints = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_constraints, many=True)
        return Response(serializer.data)


class ScenarioViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """Enhanced ViewSet for scenarios with audit trail support."""
    
    queryset = Scenario.objects.select_related(
        'tgc_model', 'fcr_model', 'mortality_model', 'batch', 
        'created_by', 'biological_constraints'
    ).prefetch_related('model_changes', 'projections')
    serializer_class = ScenarioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['start_date', 'tgc_model__location', 'created_by']
    search_fields = ['name', 'genotype', 'supplier']
    ordering_fields = ['name', 'start_date', 'created_at', 'duration_days']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter scenarios to user's own by default."""
        queryset = super().get_queryset()
        
        # Option to view all scenarios or just user's own
        if self.request.query_params.get('all') != 'true':
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a scenario with a new name.
        
        Request body:
        {
            "new_name": "Scenario Copy",
            "include_projections": false,
            "include_model_changes": true
        }
        """
        scenario = self.get_object()
        
        serializer = ScenarioDuplicateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Create duplicate scenario
            duplicate = Scenario.objects.create(
                name=serializer.validated_data['new_name'],
                start_date=scenario.start_date,
                duration_days=scenario.duration_days,
                initial_count=scenario.initial_count,
                initial_weight=scenario.initial_weight,
                genotype=scenario.genotype,
                supplier=scenario.supplier,
                tgc_model=scenario.tgc_model,
                fcr_model=scenario.fcr_model,
                mortality_model=scenario.mortality_model,
                batch=scenario.batch,
                biological_constraints=scenario.biological_constraints,
                created_by=request.user
            )
            
            # Copy model changes if requested
            if serializer.validated_data['include_model_changes']:
                for change in scenario.model_changes.all():
                    ScenarioModelChange.objects.create(
                        scenario=duplicate,
                        change_day=change.change_day,
                        new_tgc_model=change.new_tgc_model,
                        new_fcr_model=change.new_fcr_model,
                        new_mortality_model=change.new_mortality_model
                    )
            
            # Note: Projections are not copied as they should be recalculated
        
        # Return duplicated scenario
        scenario_serializer = ScenarioSerializer(duplicate, context={'request': request})
        return Response(scenario_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def from_batch(self, request):
        """
        Create a scenario initialized from a batch.
        
        Request body:
        {
            "batch_id": 123,
            "scenario_name": "Batch 123 Projection",
            "duration_days": 600,
            "use_current_models": true
        }
        """
        serializer = BatchInitializationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get initial data from batch
        scenario_data = serializer.create_scenario_from_batch(
            serializer.validated_data
        )
        
        # Add user
        scenario_data['created_by'] = request.user
        
        # Create scenario
        scenario = Scenario.objects.create(**scenario_data)
        
        # Return created scenario
        scenario_serializer = ScenarioSerializer(scenario, context={'request': request})
        return Response(scenario_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def compare(self, request):
        """
        Compare multiple scenarios.
        
        Request body:
        {
            "scenario_ids": [1, 2, 3],
            "comparison_metrics": ["final_weight", "final_biomass", "fcr_overall"]
        }
        """
        serializer = ScenarioComparisonSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Get scenarios
        scenarios = Scenario.objects.filter(
            scenario_id__in=serializer.validated_data['scenario_ids'],
            created_by=request.user
        ).prefetch_related('projections')
        
        # Generate comparison
        comparison_data = serializer.to_representation(scenarios)
        
        return Response(comparison_data)
    
    @action(detail=True, methods=['post'])
    def run_projection(self, request, pk=None):
        """
        Run projection calculation for a scenario.
        
        Returns projection summary and saves results to database.
        """
        scenario = self.get_object()
        
        # Check if user owns the scenario
        if scenario.created_by != request.user:
            return Response(
                {'error': 'You do not have permission to run projections for this scenario'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create projection engine
        engine = ProjectionEngine(scenario)
        
        # Run projection
        result = engine.run_projection(save_results=True)
        
        if result['success']:
            return Response(
                {
                    'success': True,
                    'summary': result['summary'],
                    'warnings': result['warnings'],
                    'message': f"Projection completed successfully. {scenario.duration_days} days calculated."
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'success': False,
                    'errors': result['errors'],
                    'warnings': result['warnings'],
                    'message': 'Projection failed due to validation errors.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def sensitivity_analysis(self, request, pk=None):
        """
        Run sensitivity analysis on a scenario parameter.
        
        Request body:
        {
            "parameter": "tgc",  // or "fcr" or "mortality"
            "variations": [-10, -5, 0, 5, 10]  // percentage variations
        }
        """
        scenario = self.get_object()
        
        # Check permissions
        if scenario.created_by != request.user:
            return Response(
                {'error': 'You do not have permission to analyze this scenario'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get parameters
        parameter = request.data.get('parameter')
        variations = request.data.get('variations', [-10, -5, 0, 5, 10])
        
        if parameter not in ['tgc', 'fcr', 'mortality']:
            return Response(
                {
                    'error': 'Invalid parameter. Must be one of: tgc, fcr, mortality'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create projection engine
        engine = ProjectionEngine(scenario)
        
        # Run sensitivity analysis
        result = engine.run_sensitivity_analysis(
            parameter=parameter,
            variations=variations,
            save_results=False
        )
        
        return Response(result, status=status.HTTP_200_OK)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter projections at or after this date (YYYY-MM-DD).',
                required=False,
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter projections at or before this date (YYYY-MM-DD).',
                required=False,
            ),
            OpenApiParameter(
                name='aggregation',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Aggregation granularity for projections (daily, weekly, monthly).',
                required=False,
                default='daily',
                enum=['daily', 'weekly', 'monthly'],
            ),
        ],
        responses=ScenarioProjectionSerializer(many=True),
    )
    @action(detail=True, methods=['get'])
    def projections(self, request, pk=None):
        """Get projections for a scenario with optional filtering."""
        scenario = self.get_object()
        projections = scenario.projections.select_related('current_stage')
        
        # Support date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            projections = projections.filter(projection_date__gte=start_date)
        if end_date:
            projections = projections.filter(projection_date__lte=end_date)
        
        # Support aggregation
        aggregation = request.query_params.get('aggregation', 'daily')
        
        if aggregation == 'weekly':
            # Sample every 7th day (weekly aggregation)
            projections = projections.annotate(
                mod_result=Mod(F('day_number'), 7)
            ).filter(mod_result=0)
        elif aggregation == 'monthly':
            # Sample every 30th day (monthly aggregation)
            projections = projections.annotate(
                mod_result=Mod(F('day_number'), 30)
            ).filter(mod_result=0)
        
        serializer = ScenarioProjectionSerializer(projections, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='chart_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Chart visualization type (line, area, or bar).',
                required=False,
                default='line',
                enum=['line', 'area', 'bar'],
            ),
            OpenApiParameter(
                name='metrics',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Comma-separated metrics to include (weight, population, biomass, feed, temperature).',
                required=False,
            ),
            OpenApiParameter(
                name='aggregation',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Temporal aggregation for chart data (daily, weekly, monthly).',
                required=False,
                default='daily',
                enum=['daily', 'weekly', 'monthly'],
            ),
        ]
    )
    @action(detail=True, methods=['get'])
    def chart_data(self, request, pk=None):
        """Get projection data formatted for charts."""
        scenario = self.get_object()
        projections = scenario.projections.select_related('current_stage').order_by('day_number')
        
        # Use chart serializer
        chart_serializer = ProjectionChartSerializer(data=request.query_params)
        chart_serializer.is_valid(raise_exception=True)
        
        chart_data = chart_serializer.to_representation(projections)
        
        return Response(chart_data)
    
    @action(detail=True, methods=['get'])
    def export_projections(self, request, pk=None):
        """Export projections as CSV."""
        scenario = self.get_object()
        projections = scenario.projections.select_related('current_stage').order_by('day_number')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{scenario.name}_projections.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Day', 'Date', 'Weight (g)', 'Population', 'Biomass (kg)',
            'Daily Feed (kg)', 'Cumulative Feed (kg)', 'Temperature (°C)',
            'Stage', 'Growth Rate (%)', 'FCR Actual'
        ])
        
        prev_weight = scenario.initial_weight or 0
        for proj in projections:
            growth_rate = ((proj.average_weight - prev_weight) / prev_weight * 100) if prev_weight > 0 else 0
            fcr_actual = (proj.cumulative_feed / proj.biomass) if proj.biomass > 0 else 0
            
            writer.writerow([
                proj.day_number,
                proj.projection_date.strftime('%Y-%m-%d'),
                round(proj.average_weight, 2),
                round(proj.population, 0),
                round(proj.biomass, 2),
                round(proj.daily_feed, 2),
                round(proj.cumulative_feed, 2),
                round(proj.temperature, 1),
                proj.current_stage.name if proj.current_stage else 'Unknown',
                round(growth_rate, 2),
                round(fcr_actual, 2)
            ])
            
            prev_weight = proj.average_weight
        
        return response
    
    @action(detail=False, methods=['get'])
    def summary_stats(self, request):
        """Get summary statistics for user's scenarios."""
        user_scenarios = self.get_queryset()
        
        stats = {
            'total_scenarios': user_scenarios.count(),
            'scenarios_with_projections': user_scenarios.filter(
                projections__isnull=False
            ).distinct().count(),
            'average_duration': user_scenarios.aggregate(
                avg_duration=Avg('duration_days')
            )['avg_duration'],
            'location_distribution': list(
                user_scenarios.values('tgc_model__location').annotate(
                    count=Count('scenario_id')
                ).order_by('-count')
            ),
            'recent_scenarios': ScenarioSerializer(
                user_scenarios.order_by('-created_at')[:5],
                many=True,
                context={'request': request}
            ).data
        }
        
        return Response(stats)


class DataEntryViewSet(viewsets.ViewSet):
    """
    ViewSet for data entry operations.
    
    Provides endpoints for various data entry methods.
    """
    permission_classes = [IsAuthenticated]
    # Base serializer so drf-spectacular can infer request / response schema.
    # Individual @action methods still override validation logic as needed.
    serializer_class = CSVUploadSerializer
    
    @action(detail=False, methods=['post'])
    def validate_csv(self, request):
        """
        Validate CSV file without saving.
        
        Returns preview data and any validation errors/warnings.
        """
        serializer = CSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Force validation only
        serializer.validated_data['validate_only'] = True
        
        # Get file content
        csv_file = serializer.validated_data['file']
        file_content = csv_file.read().decode('utf-8')
        csv_io = io.StringIO(file_content)
        
        # Validate based on data type
        data_type = serializer.validated_data['data_type']
        service = BulkDataImportService()
        
        if data_type == 'temperature':
            success, result = service.import_temperature_data(
                csv_io,
                serializer.validated_data['profile_name'],
                validate_only=True
            )
        elif data_type == 'fcr':
            success, result = service.import_fcr_data(
                csv_io,
                serializer.validated_data.get('model_name', 'Imported FCR'),
                validate_only=True
            )
        elif data_type == 'mortality':
            success, result = service.import_mortality_data(
                csv_io,
                serializer.validated_data.get('model_name', 'Imported Mortality'),
                validate_only=True
            )
        else:
            return Response(
                {'error': f'Unknown data type: {data_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result_serializer = DataValidationResultSerializer(data=result)
        result_serializer.is_valid()
        
        return Response(
            result_serializer.data,
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='data_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Type of template to download (temperature, fcr, mortality).",
                required=True,
                enum=['temperature', 'fcr', 'mortality'],
            ),
            OpenApiParameter(
                name='include_sample_data',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include sample rows in the generated template.',
                required=False,
                default=False,
            ),
        ],
        responses=OpenApiResponse(description='CSV template file'),
    )
    @action(detail=False, methods=['get'])
    def csv_template(self, request):
        """
        Download CSV template for specified data type.
        
        Query params:
        - data_type: 'temperature', 'fcr', or 'mortality'
        - include_sample_data: true/false
        """
        serializer = CSVTemplateRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data_type = serializer.validated_data['data_type']
        include_sample = serializer.validated_data.get('include_sample_data', False)
        service = BulkDataImportService()
        
        try:
            template_content = service.generate_csv_template(data_type)
            
            response = HttpResponse(template_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{data_type}_template.csv"'
            return response
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def import_status(self, request):
        """Check status of recent imports."""
        # This would track import jobs if we implement async processing
        return Response({
            'message': 'Import status tracking not yet implemented',
            'recent_imports': []
        }) 