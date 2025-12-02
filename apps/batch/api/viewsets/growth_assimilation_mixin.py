"""
Growth Assimilation API Mixin for BatchViewSet.

Provides endpoints for the Growth Analysis page (Issue #112 Phase 6):
- Combined endpoint: samples + scenario + actual states
- Pin scenario to batch
- Manual recompute (admin)

Extracted into mixin to keep BatchViewSet maintainable.
"""
from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import ActualDailyAssignmentState, GrowthSample
from apps.scenario.models import Scenario, ScenarioProjection
from apps.batch.api.serializers import (
    GrowthAnalysisCombinedSerializer,
    PinScenarioSerializer,
    ManualRecomputeSerializer,
    ActualDailyAssignmentStateListSerializer,
)


class GrowthAssimilationMixin:
    """
    Mixin containing Growth Assimilation endpoints for BatchViewSet.
    
    Endpoints:
    - combined-growth-data: Combined data for Growth Analysis chart
    - pin-scenario: Pin a scenario to batch
    - recompute-daily-states: Manual recompute (admin)
    
    Issue: #112 - Phase 6
    """
    
    @extend_schema(
        operation_id="batch-combined-growth-data",
        summary="Get combined growth data (samples, scenario, actual states)",
        description=(
            "Returns all data needed for the Growth Analysis page:\n"
            "- Growth samples (measured anchors)\n"
            "- Scenario projection (planned/modeled)\n"
            "- Actual daily states (assimilated reality)\n"
            "- Container assignments (for drilldown)\n\n"
            "This is the primary endpoint for the frontend Growth Analysis chart."
        ),
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Start date for data range (ISO 8601: YYYY-MM-DD). Default: batch start date",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="End date for data range (ISO 8601: YYYY-MM-DD). Default: today",
                required=False,
            ),
            OpenApiParameter(
                name="assignment_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter to specific container assignment (optional)",
                required=False,
            ),
            OpenApiParameter(
                name="granularity",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Data granularity: 'daily' or 'weekly'. Default: daily",
                required=False,
                enum=['daily', 'weekly'],
            ),
        ],
        responses={
            200: GrowthAnalysisCombinedSerializer,
            404: {"description": "Batch not found or no scenario available"},
        }
    )
    @action(detail=True, methods=['get'], url_path='combined-growth-data')
    def combined_growth_data(self, request, pk=None):
        """
        Get combined growth data for Growth Analysis page.
        
        URL: /api/v1/batch/batches/{pk}/combined-growth-data/
        
        Returns:
            Combined response with samples, scenario projection, and actual daily states
        """
        batch = self.get_object()
        
        # Parse query parameters
        start_date = self._parse_date_param(request, 'start_date', batch.start_date)
        end_date = self._parse_date_param(request, 'end_date', datetime.now().date())
        assignment_id = request.query_params.get('assignment_id')
        granularity = request.query_params.get('granularity', 'daily')
        
        # Validate granularity
        if granularity not in ['daily', 'weekly']:
            raise ValidationError({'granularity': 'Must be "daily" or "weekly"'})
        
        # Get projection run from pinned projection run or find latest
        from apps.scenario.models import ProjectionRun
        
        projection_run = batch.pinned_projection_run
        scenario = None
        
        if projection_run:
            scenario = projection_run.scenario
        else:
            # Find latest projection run for any scenario linked to this batch
            scenario = batch.scenarios.first()
            if scenario:
                projection_run = ProjectionRun.objects.filter(
                    scenario=scenario
                ).order_by('-run_number').first()
        
        if not scenario or not projection_run:
            return Response(
                {
                    'detail': 'No scenario/projection run available for this batch. Create and pin a scenario first.',
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build response
        response_data = {
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'species': batch.species.name,
            'lifecycle_stage': batch.lifecycle_stage.name,
            'start_date': batch.start_date,
            'status': batch.status,
            'scenario': self._serialize_scenario(scenario),
            'projection_run': self._serialize_projection_run(projection_run),
            'growth_samples': self._get_growth_samples(batch, start_date, end_date, assignment_id),
            'scenario_projection': self._get_scenario_projection(projection_run, start_date, end_date, granularity),
            'actual_daily_states': self._get_actual_daily_states(batch, start_date, end_date, assignment_id, granularity),
            'container_assignments': self._get_container_assignments(batch, start_date, end_date),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'granularity': granularity,
            }
        }
        
        return Response(response_data)
    
    @extend_schema(
        operation_id="batch-pin-scenario",
        summary="Pin a scenario to a batch",
        description=(
            "Associate a specific scenario with this batch as the reference for\n"
            "growth assimilation calculations. Only one scenario can be pinned at a time."
        ),
        request=PinScenarioSerializer,
        responses={
            200: {"description": "Scenario pinned successfully"},
            400: {"description": "Invalid scenario ID or validation error"},
            404: {"description": "Batch or scenario not found"},
        }
    )
    @extend_schema(
        operation_id="batch_pin_projection_run",
        summary="Pin a projection run to this batch",
        description=(
            "Pin a specific projection run to this batch for growth analysis.\n"
            "Provides version control for scenario projections."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'projection_run_id': {
                        'type': 'integer',
                        'description': 'ID of the projection run to pin'
                    }
                },
                'required': ['projection_run_id']
            }
        },
        responses={
            200: {"description": "Projection run pinned successfully"},
            400: {"description": "Invalid projection run ID or validation error"},
            404: {"description": "Batch or projection run not found"},
        }
    )
    @action(detail=True, methods=['post'], url_path='pin-projection-run')
    def pin_projection_run(self, request, pk=None):
        """
        Pin a specific projection run to this batch.
        
        Request body:
        {
            "projection_run_id": 123
        }
        """
        from apps.scenario.models import ProjectionRun
        from django.shortcuts import get_object_or_404
        
        batch = self.get_object()
        projection_run_id = request.data.get('projection_run_id')
        
        if not projection_run_id:
            return Response(
                {'error': 'projection_run_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        projection_run = get_object_or_404(ProjectionRun, pk=projection_run_id)
        
        batch.pinned_projection_run = projection_run
        batch.save(update_fields=['pinned_projection_run'])
        
        return Response({
            'success': True,
            'pinned_projection_run_id': projection_run.run_id,
            'scenario_name': projection_run.scenario.name,
            'run_number': projection_run.run_number,
            'run_label': projection_run.label,
        })
    
    @action(detail=True, methods=['post'], url_path='pin-scenario')
    def pin_scenario(self, request, pk=None):
        """
        DEPRECATED: Use pin_projection_run instead.
        
        This endpoint pins the LATEST projection run for the given scenario.
        
        URL: POST /api/v1/batch/batches/{pk}/pin-scenario/
        Body: {"scenario_id": 123}
        """
        from apps.scenario.models import ProjectionRun
        from django.shortcuts import get_object_or_404
        
        batch = self.get_object()
        serializer = PinScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        scenario_id = serializer.validated_data['scenario_id']
        
        try:
            scenario = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return Response(
                {'detail': f'Scenario {scenario_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get latest projection run for this scenario
        latest_run = ProjectionRun.objects.filter(scenario=scenario).order_by('-run_number').first()
        
        if not latest_run:
            return Response(
                {'error': 'Scenario has no projection runs. Run projections first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Pin to latest run
        batch.pinned_projection_run = latest_run
        batch.save(update_fields=['pinned_projection_run'])
        
        return Response({
            'success': True,
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'pinned_projection_run_id': latest_run.run_id,
            'scenario_id': scenario.scenario_id,
            'scenario_name': scenario.name,
            'message': 'DEPRECATED: Use pin_projection_run endpoint. Pinned to latest run.',
        })
    
    @extend_schema(
        operation_id="batch-recompute-daily-states",
        summary="Manually trigger recomputation of daily states (Admin)",
        description=(
            "Trigger manual recomputation of ActualDailyAssignmentState for a date range.\n"
            "Enqueues Celery task(s) to recompute daily states.\n\n"
            "**Requires**: Admin or Manager role with can_recompute_daily_state permission."
        ),
        request=ManualRecomputeSerializer,
        responses={
            200: {"description": "Recompute task(s) enqueued successfully (synchronous in tests)"},
            202: {"description": "Recompute task(s) enqueued successfully (async in production)"},
            400: {"description": "Invalid date range or parameters"},
            403: {"description": "Permission denied"},
        }
    )
    @action(detail=True, methods=['post'], url_path='recompute-daily-states')
    def recompute_daily_states(self, request, pk=None):
        """
        Manual recompute trigger (admin endpoint).
        
        URL: POST /api/v1/batch/batches/{pk}/recompute-daily-states/
        Body: {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "assignment_ids": [1, 2, 3]  // Optional
        }
        """
        batch = self.get_object()
        
        # Permission check (admin/manager only)
        if not request.user.is_staff and not request.user.profile.role in ['MANAGER', 'ADMIN']:
            raise PermissionDenied(
                "Only administrators and managers can trigger manual recomputation"
            )
        
        serializer = ManualRecomputeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data.get('end_date')
        assignment_ids = serializer.validated_data.get('assignment_ids')
        
        # Import here to avoid circular imports
        from apps.batch.tasks import recompute_batch_window, recompute_assignment_window
        
        tasks_enqueued = []
        
        if assignment_ids:
            # Recompute specific assignments
            for assignment_id in assignment_ids:
                try:
                    task = recompute_assignment_window.delay(
                        assignment_id,
                        start_date.isoformat(),
                        end_date.isoformat() if end_date else None
                    )
                    tasks_enqueued.append({
                        'assignment_id': assignment_id,
                        'task_id': task.id,
                    })
                except Exception as e:
                    return Response(
                        {'detail': f'Failed to enqueue task for assignment {assignment_id}: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        else:
            # Recompute all assignments (batch-level)
            try:
                task = recompute_batch_window.delay(
                    batch.id,
                    start_date.isoformat(),
                    end_date.isoformat() if end_date else None
                )
                tasks_enqueued.append({
                    'batch_id': batch.id,
                    'task_id': task.id,
                })
            except Exception as e:
                return Response(
                    {'detail': f'Failed to enqueue batch recompute task: {e}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response({
            'success': True,
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat() if end_date else 'today',
            },
            'tasks_enqueued': len(tasks_enqueued),
            'task_ids': [t['task_id'] for t in tasks_enqueued],
        }, status=status.HTTP_202_ACCEPTED)
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _parse_date_param(self, request, param_name, default):
        """Parse date parameter from query string."""
        date_str = request.query_params.get(param_name)
        if not date_str:
            return default
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError({
                param_name: f'Invalid date format. Use YYYY-MM-DD'
            })
    
    def _serialize_scenario(self, scenario):
        """Serialize scenario basic info."""
        return {
            'id': scenario.scenario_id,
            'name': scenario.name,
            'start_date': scenario.start_date,
            'duration_days': scenario.duration_days,
            'initial_count': scenario.initial_count,
            'initial_weight': float(scenario.initial_weight),
        }
    
    def _serialize_projection_run(self, projection_run):
        """Serialize projection run info."""
        return {
            'id': projection_run.run_id,
            'run_number': projection_run.run_number,
            'label': projection_run.label,
            'run_date': projection_run.run_date,
            'total_projections': projection_run.total_projections,
            'final_weight_g': projection_run.final_weight_g,
            'final_biomass_kg': projection_run.final_biomass_kg,
        }
    
    def _get_growth_samples(self, batch, start_date, end_date, assignment_id=None):
        """Get growth samples for the batch in date range."""
        qs = GrowthSample.objects.filter(
            assignment__batch=batch,
            sample_date__gte=start_date,
            sample_date__lte=end_date
        ).select_related('assignment', 'assignment__container')
        
        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        
        qs = qs.order_by('sample_date')
        
        return [
            {
                'date': sample.sample_date,
                'avg_weight_g': float(sample.avg_weight_g),
                'sample_size': sample.sample_size,
                'assignment_id': sample.assignment.id,
                'container_name': sample.assignment.container.name,
                'condition_factor': float(sample.condition_factor) if sample.condition_factor else None,
            }
            for sample in qs
        ]
    
    def _get_scenario_projection(self, projection_run, start_date, end_date, granularity):
        """Get scenario projection for date range from a projection run."""
        scenario = projection_run.scenario
        
        # Calculate day numbers from scenario start
        start_day = (start_date - scenario.start_date).days + 1
        end_day = (end_date - scenario.start_date).days + 1
        
        # Clamp to valid range
        start_day = max(1, start_day)
        end_day = min(scenario.duration_days, end_day)
        
        if start_day > end_day:
            return []
        
        # Query projection days from the specific projection run
        qs = ScenarioProjection.objects.filter(
            projection_run=projection_run,
            day_number__gte=start_day,
            day_number__lte=end_day
        ).order_by('day_number')
        
        # Apply granularity (sample every Nth day if weekly)
        if granularity == 'weekly':
            # Python-side filtering for weekly sampling (every 7th day)
            projections = list(qs)
            projections = [projections[i] for i in range(0, len(projections), 7)]
        else:
            projections = qs
        
        return [
            {
                'date': scenario.start_date + timedelta(days=proj.day_number - 1),
                'day_number': proj.day_number,
                'avg_weight_g': float(proj.average_weight),  # ScenarioProjection uses 'average_weight'
                'population': int(proj.population),
                'biomass_kg': float(proj.biomass),
            }
            for proj in projections
        ]
    
    def _get_actual_daily_states(self, batch, start_date, end_date, assignment_id, granularity):
        """Get actual daily states for batch in date range."""
        qs = ActualDailyAssignmentState.objects.filter(
            assignment__batch=batch,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('assignment', 'assignment__container')
        
        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        
        qs = qs.order_by('date')
        
        # Apply granularity (sample every Nth row if weekly)
        if granularity == 'weekly':
            # Get every 7th state (weekly sampling)
            states = list(qs)
            states = [states[i] for i in range(0, len(states), 7)]
        else:
            states = qs
        
        return [
            {
                'date': state.date,
                'day_number': state.day_number,
                'avg_weight_g': float(state.avg_weight_g) if state.avg_weight_g else None,
                'population': state.population,
                'biomass_kg': float(state.biomass_kg) if state.biomass_kg else None,
                'anchor_type': state.anchor_type,
                'assignment_id': state.assignment.id,
                'container_name': state.assignment.container.name,
                'confidence_scores': state.confidence_scores,
                'sources': state.sources,
            }
            for state in states
        ]
    
    def _get_container_assignments(self, batch, start_date, end_date):
        """
        Get container assignments for batch (for drilldown UI).
        
        Returns ALL assignments that overlap with the date range, not just active ones.
        This is critical for frontend aggregation to avoid double-counting on transfer days.
        """
        from django.db.models import Q
        
        # Get all assignments that overlap with the date range
        assignments = batch.batch_assignments.filter(
            assignment_date__lte=end_date
        ).filter(
            Q(departure_date__isnull=True) | Q(departure_date__gte=start_date)
        ).select_related('container', 'lifecycle_stage').order_by('assignment_date')
        
        return [
            {
                'id': assignment.id,
                'container_name': assignment.container.name,
                'container_type': assignment.container.container_type.name,
                'arrival_date': assignment.assignment_date,
                'departure_date': assignment.departure_date,
                'population_count': assignment.population_count,
                'avg_weight_g': float(assignment.avg_weight_g) if assignment.avg_weight_g else None,
                'biomass_kg': float(assignment.biomass_kg) if assignment.biomass_kg else None,
                'lifecycle_stage': assignment.lifecycle_stage.name if assignment.lifecycle_stage else None,
            }
            for assignment in assignments
        ]
