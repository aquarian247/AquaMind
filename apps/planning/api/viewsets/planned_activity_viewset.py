from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Count, Avg, Min, Max, Q, F
from django.db.models.functions import TruncMonth, TruncWeek
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.planning.models import PlannedActivity
from apps.planning.api.serializers import (
    PlannedActivitySerializer,
    VarianceReportSerializer,
)


class PlannedActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for PlannedActivity model."""
    
    queryset = PlannedActivity.objects.select_related(
        'scenario',
        'batch',
        'container',
        'created_by',
        'completed_by',
        'transfer_workflow'
    ).all()
    serializer_class = PlannedActivitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scenario', 'batch', 'activity_type', 'status', 'container']
    search_fields = ['notes', 'batch__batch_number']
    ordering_fields = ['due_date', 'created_at', 'status']
    ordering = ['due_date', 'created_at']
    
    def get_queryset(self):
        """Apply custom filters."""
        queryset = super().get_queryset()
        
        # Filter by overdue status
        if self.request.query_params.get('overdue') == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                status='PENDING',
                due_date__lt=timezone.now().date()
            )
        
        # Filter by date range
        due_date_after = self.request.query_params.get('due_date_after')
        due_date_before = self.request.query_params.get('due_date_before')
        
        if due_date_after:
            queryset = queryset.filter(due_date__gte=due_date_after)
        if due_date_before:
            queryset = queryset.filter(due_date__lte=due_date_before)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        """Mark activity as completed."""
        activity = self.get_object()
        
        if activity.status == 'COMPLETED':
            return Response(
                {"error": "Activity is already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if activity.status == 'CANCELLED':
            return Response(
                {"error": "Cannot complete a cancelled activity"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activity.mark_completed(user=request.user)
        
        serializer = self.get_serializer(activity)
        return Response({
            "message": "Activity marked as completed",
            "activity": serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='spawn-workflow')
    def spawn_workflow(self, request, pk=None):
        """Spawn a Transfer Workflow from this planned activity."""
        activity = self.get_object()
        
        if activity.activity_type != 'TRANSFER':
            return Response(
                {"error": "Can only spawn workflows from TRANSFER activities"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if activity.transfer_workflow:
            return Response(
                {"error": "Workflow already spawned for this activity"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract parameters from request
        workflow_type = request.data.get('workflow_type', 'LIFECYCLE_TRANSITION')
        source_stage_id = request.data.get('source_lifecycle_stage')
        dest_stage_id = request.data.get('dest_lifecycle_stage')
        
        if not source_stage_id or not dest_stage_id:
            return Response(
                {"error": "source_lifecycle_stage and dest_lifecycle_stage are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.batch.models import LifeCycleStage
            
            # Validate lifecycle stages exist
            source_stage = LifeCycleStage.objects.get(id=source_stage_id)
            dest_stage = LifeCycleStage.objects.get(id=dest_stage_id)
            
            workflow = activity.spawn_transfer_workflow(
                workflow_type=workflow_type,
                source_lifecycle_stage=source_stage,
                dest_lifecycle_stage=dest_stage,
                user=request.user
            )
        except LifeCycleStage.DoesNotExist as e:
            return Response(
                {"error": "Lifecycle stage not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.batch.api.serializers import BatchTransferWorkflowDetailSerializer
        serializer = BatchTransferWorkflowDetailSerializer(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='scenario',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by scenario ID',
                required=False,
            ),
            OpenApiParameter(
                name='due_date_after',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter activities due on or after this date (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='due_date_before',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter activities due on or before this date (YYYY-MM-DD)',
                required=False,
            ),
            OpenApiParameter(
                name='activity_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by activity type',
                required=False,
                enum=['VACCINATION', 'TREATMENT', 'CULL', 'HARVEST', 'SALE',
                      'FEED_CHANGE', 'TRANSFER', 'MAINTENANCE', 'SAMPLING', 'OTHER'],
            ),
            OpenApiParameter(
                name='group_by',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Time series grouping: "month" or "week"',
                required=False,
                default='month',
                enum=['month', 'week'],
            ),
            OpenApiParameter(
                name='include_details',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include individual activity details in response',
                required=False,
                default=False,
            ),
        ],
        responses={200: VarianceReportSerializer},
        description='Generate variance report comparing planned vs actual activity execution.'
    )
    @action(detail=False, methods=['get'], url_path='variance-report')
    def variance_report(self, request):
        """
        Generate variance report comparing planned vs actual activity execution.
        
        Returns summary statistics, per-activity-type breakdown, and time series data.
        Variance is calculated as: completed_at.date() - due_date (in days).
        - Negative = completed early
        - Zero = completed on time
        - Positive = completed late
        """
        queryset = self.get_queryset()
        
        # Apply filters from query params
        scenario_id = request.query_params.get('scenario')
        due_date_after = request.query_params.get('due_date_after')
        due_date_before = request.query_params.get('due_date_before')
        activity_type = request.query_params.get('activity_type')
        group_by = request.query_params.get('group_by', 'month')
        include_details = request.query_params.get('include_details', 'false').lower() == 'true'
        
        if scenario_id:
            queryset = queryset.filter(scenario_id=scenario_id)
        if due_date_after:
            queryset = queryset.filter(due_date__gte=due_date_after)
        if due_date_before:
            queryset = queryset.filter(due_date__lte=due_date_before)
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # Get scenario info if filtering by scenario
        scenario_name = None
        if scenario_id:
            from apps.scenario.models import Scenario
            try:
                scenario = Scenario.objects.get(pk=scenario_id)
                scenario_name = scenario.name
            except Scenario.DoesNotExist:
                pass
        
        # Calculate variance for completed activities
        activities_list = list(queryset)
        today = timezone.now().date()
        
        # Process activities and calculate variance
        activity_data = []
        for activity in activities_list:
            variance_days = None
            is_on_time = None
            
            if activity.status == 'COMPLETED' and activity.completed_at:
                completed_date = activity.completed_at.date()
                variance_days = (completed_date - activity.due_date).days
                is_on_time = variance_days <= 0
            
            activity_data.append({
                'id': activity.id,
                'batch_number': activity.batch.batch_number,
                'batch_id': activity.batch_id,
                'activity_type': activity.activity_type,
                'activity_type_display': activity.get_activity_type_display(),
                'due_date': activity.due_date,
                'completed_at': activity.completed_at,
                'status': activity.status,
                'variance_days': variance_days,
                'is_on_time': is_on_time,
            })
        
        # Calculate summary statistics
        total = len(activity_data)
        completed = [a for a in activity_data if a['status'] == 'COMPLETED']
        pending = [a for a in activity_data if a['status'] in ['PENDING', 'IN_PROGRESS']]
        cancelled = [a for a in activity_data if a['status'] == 'CANCELLED']
        overdue = [a for a in activity_data 
                   if a['status'] in ['PENDING', 'IN_PROGRESS'] 
                   and a['due_date'] < today]
        
        completed_with_variance = [a for a in completed if a['variance_days'] is not None]
        on_time = [a for a in completed_with_variance if a['variance_days'] <= 0]
        late = [a for a in completed_with_variance if a['variance_days'] > 0]
        early = [a for a in completed_with_variance if a['variance_days'] < 0]
        
        # Calculate rates
        non_cancelled = total - len(cancelled)
        completion_rate = (len(completed) / non_cancelled * 100) if non_cancelled > 0 else 0
        on_time_rate = (len(on_time) / len(completed_with_variance) * 100) if completed_with_variance else 0
        
        avg_variance = None
        if completed_with_variance:
            avg_variance = sum(a['variance_days'] for a in completed_with_variance) / len(completed_with_variance)
        
        summary = {
            'total_activities': total,
            'completed_activities': len(completed),
            'pending_activities': len(pending),
            'cancelled_activities': len(cancelled),
            'overdue_activities': len(overdue),
            'overall_completion_rate': round(completion_rate, 1),
            'on_time_activities': len(on_time),
            'late_activities': len(late),
            'early_activities': len(early),
            'overall_on_time_rate': round(on_time_rate, 1),
            'avg_variance_days': round(avg_variance, 1) if avg_variance is not None else None,
        }
        
        # Group by activity type
        by_activity_type = self._calculate_type_stats(activity_data, today)
        
        # Generate time series
        time_series = self._calculate_time_series(activity_data, group_by)
        
        # Build response
        response_data = {
            'report_generated_at': timezone.now(),
            'scenario_id': int(scenario_id) if scenario_id else None,
            'scenario_name': scenario_name,
            'date_range_start': due_date_after,
            'date_range_end': due_date_before,
            'summary': summary,
            'by_activity_type': by_activity_type,
            'time_series': time_series,
        }
        
        if include_details:
            response_data['activities'] = activity_data
        
        serializer = VarianceReportSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)
    
    def _calculate_type_stats(self, activity_data, today):
        """Calculate variance statistics grouped by activity type."""
        from collections import defaultdict
        
        type_groups = defaultdict(list)
        for activity in activity_data:
            type_groups[activity['activity_type']].append(activity)
        
        type_stats = []
        type_display_map = dict(PlannedActivity.ACTIVITY_TYPE_CHOICES)
        
        for activity_type, activities in type_groups.items():
            completed = [a for a in activities if a['status'] == 'COMPLETED']
            pending = [a for a in activities if a['status'] in ['PENDING', 'IN_PROGRESS']]
            cancelled = [a for a in activities if a['status'] == 'CANCELLED']
            
            completed_with_variance = [a for a in completed if a['variance_days'] is not None]
            on_time = [a for a in completed_with_variance if a['variance_days'] <= 0]
            late = [a for a in completed_with_variance if a['variance_days'] > 0]
            early = [a for a in completed_with_variance if a['variance_days'] < 0]
            
            non_cancelled = len(activities) - len(cancelled)
            completion_rate = (len(completed) / non_cancelled * 100) if non_cancelled > 0 else 0
            on_time_rate = (len(on_time) / len(completed_with_variance) * 100) if completed_with_variance else 0
            
            variances = [a['variance_days'] for a in completed_with_variance]
            avg_variance = sum(variances) / len(variances) if variances else None
            min_variance = min(variances) if variances else None
            max_variance = max(variances) if variances else None
            
            type_stats.append({
                'activity_type': activity_type,
                'activity_type_display': type_display_map.get(activity_type, activity_type),
                'total_count': len(activities),
                'completed_count': len(completed),
                'pending_count': len(pending),
                'cancelled_count': len(cancelled),
                'completion_rate': round(completion_rate, 1),
                'on_time_count': len(on_time),
                'late_count': len(late),
                'early_count': len(early),
                'on_time_rate': round(on_time_rate, 1),
                'avg_variance_days': round(avg_variance, 1) if avg_variance is not None else None,
                'min_variance_days': min_variance,
                'max_variance_days': max_variance,
            })
        
        # Sort by activity type
        type_stats.sort(key=lambda x: x['activity_type'])
        return type_stats
    
    def _calculate_time_series(self, activity_data, group_by):
        """Calculate time series variance data."""
        from collections import defaultdict
        
        period_groups = defaultdict(list)
        
        for activity in activity_data:
            due_date = activity['due_date']
            if group_by == 'week':
                # ISO week format: YYYY-Www
                period = f"{due_date.isocalendar()[0]}-W{due_date.isocalendar()[1]:02d}"
            else:
                # Month format: YYYY-MM
                period = due_date.strftime('%Y-%m')
            period_groups[period].append(activity)
        
        time_series = []
        for period in sorted(period_groups.keys()):
            activities = period_groups[period]
            completed = [a for a in activities if a['status'] == 'COMPLETED']
            completed_with_variance = [a for a in completed if a['variance_days'] is not None]
            on_time = [a for a in completed_with_variance if a['variance_days'] <= 0]
            late = [a for a in completed_with_variance if a['variance_days'] > 0]
            early = [a for a in completed_with_variance if a['variance_days'] < 0]
            
            completion_rate = (len(completed) / len(activities) * 100) if activities else 0
            on_time_rate = (len(on_time) / len(completed_with_variance) * 100) if completed_with_variance else 0
            
            time_series.append({
                'period': period,
                'total_due': len(activities),
                'completed': len(completed),
                'on_time': len(on_time),
                'late': len(late),
                'early': len(early),
                'completion_rate': round(completion_rate, 1),
                'on_time_rate': round(on_time_rate, 1),
            })
        
        return time_series
    
    @extend_schema(
        responses={200: dict},
        description='Get projection preview showing scenario-based rationale for activity due date.'
    )
    @action(detail=True, methods=['get'], url_path='projection-preview')
    def projection_preview(self, request, pk=None):
        """
        Return projection rationale for this activity's due date.
        
        Joins with scenario projections to show:
        - Projected weight at the due date
        - Projected population
        - Rationale (from scenario and day number)
        
        This enables the "Projection Preview" tooltip in the Production Planner UI.
        """
        activity = self.get_object()
        
        # Get scenario projection for the due date
        projected_weight_g = None
        projected_population = None
        projected_biomass_kg = None
        day_number = None
        
        try:
            from apps.scenario.models import ProjectionDay
            projection = ProjectionDay.objects.filter(
                projection_run__scenario=activity.scenario,
                batch=activity.batch,
                day_date=activity.due_date
            ).first()
            
            if projection:
                # Use 'is not None' checks - truthy checks would incorrectly treat 0 as missing
                projected_weight_g = float(projection.avg_weight_g) if projection.avg_weight_g is not None else None
                projected_population = projection.population if hasattr(projection, 'population') and projection.population is not None else None
                projected_biomass_kg = float(projection.biomass_kg) if hasattr(projection, 'biomass_kg') and projection.biomass_kg is not None else None
                day_number = projection.day_number if hasattr(projection, 'day_number') and projection.day_number is not None else None
        except Exception as e:
            # Log but continue - projection data is optional
            pass
        
        # Build rationale string (use 'is not None' - 0 is a valid weight)
        if projected_weight_g is not None:
            if day_number is not None:
                rationale = (
                    f"From {activity.scenario.name}: "
                    f"Day {day_number}, projected {projected_weight_g:.1f}g"
                )
            else:
                rationale = (
                    f"From {activity.scenario.name}: "
                    f"Projected weight {projected_weight_g:.1f}g"
                )
        else:
            rationale = f"Scheduled per {activity.scenario.name}"
        
        response_data = {
            'activity_id': activity.id,
            'due_date': activity.due_date,
            'scenario_id': activity.scenario_id,
            'scenario_name': activity.scenario.name,
            'projected_weight_g': projected_weight_g,
            'projected_population': projected_population,
            'projected_biomass_kg': projected_biomass_kg,
            'day_number': day_number,
            'rationale': rationale,
        }
        
        return Response(response_data)
    
    @extend_schema(
        responses={200: dict},
        description='Get variance-from-actual data for a specific activity by joining with ActualDailyAssignmentState.'
    )
    @action(detail=True, methods=['get'], url_path='variance-from-actual')
    def variance_from_actual(self, request, pk=None):
        """
        Get variance data comparing planned activity with actual daily state.
        
        Returns:
        - Planned date and actual completion date (if completed)
        - Weight at planned date (from scenario projection or actual state)
        - Weight at completion (from actual daily state)
        - FCR at completion (from actual daily state)
        - Variance metrics: days_variance, weight_variance_g, weight_variance_pct, fcr_variance
        """
        activity = self.get_object()
        
        # Get actual daily state data
        from apps.batch.models import ActualDailyAssignmentState
        
        # Get state on due date
        state_on_due_date = ActualDailyAssignmentState.objects.filter(
            batch=activity.batch,
            date=activity.due_date
        ).first()
        
        # Get state on completion date (if completed)
        state_at_completion = None
        completion_date = None
        if activity.status == 'COMPLETED' and activity.completed_at:
            completion_date = activity.completed_at.date()
            state_at_completion = ActualDailyAssignmentState.objects.filter(
                batch=activity.batch,
                date=completion_date
            ).first()
        
        # Get projected weight from scenario (if available)
        projected_weight_g = None
        try:
            from apps.scenario.models import ProjectionDay
            projection = ProjectionDay.objects.filter(
                projection_run__scenario=activity.scenario,
                batch=activity.batch,
                day_date=activity.due_date
            ).first()
            if projection and projection.avg_weight_g is not None:
                projected_weight_g = float(projection.avg_weight_g)
        except Exception:
            pass
        
        # Build response data
        response_data = {
            'activity_id': activity.id,
            'batch_number': activity.batch.batch_number,
            'activity_type': activity.activity_type,
            'activity_type_display': activity.get_activity_type_display(),
            'scenario_name': activity.scenario.name,
            'status': activity.status,
            
            # Dates
            'planned_date': activity.due_date,
            'actual_completion_date': completion_date,
            'days_variance': None,
            
            # Weight at planned date
            'projected_weight_g': projected_weight_g,
            'actual_weight_at_planned_date_g': None,
            
            # Weight at completion
            'weight_at_completion_g': None,
            'weight_variance_g': None,
            'weight_variance_pct': None,
            
            # FCR at completion
            'fcr_at_completion': None,
            'fcr_projected': None,
            'fcr_variance_pct': None,
            
            # Biomass data
            'biomass_at_planned_date_kg': None,
            'biomass_at_completion_kg': None,
            'population_at_completion': None,
        }
        
        # Fill in actual data from daily states
        if state_on_due_date:
            response_data['actual_weight_at_planned_date_g'] = float(state_on_due_date.avg_weight_g)
            response_data['biomass_at_planned_date_kg'] = float(state_on_due_date.biomass_kg)
        
        if state_at_completion:
            response_data['weight_at_completion_g'] = float(state_at_completion.avg_weight_g)
            response_data['biomass_at_completion_kg'] = float(state_at_completion.biomass_kg)
            response_data['population_at_completion'] = state_at_completion.population
            
            if state_at_completion.observed_fcr is not None:
                response_data['fcr_at_completion'] = float(state_at_completion.observed_fcr)
        
        # Calculate variances
        if completion_date:
            response_data['days_variance'] = (completion_date - activity.due_date).days
        
        # Weight variance (comparing projected vs actual at completion)
        if projected_weight_g and response_data['weight_at_completion_g']:
            weight_variance = response_data['weight_at_completion_g'] - projected_weight_g
            response_data['weight_variance_g'] = round(weight_variance, 2)
            if projected_weight_g > 0:
                response_data['weight_variance_pct'] = round(
                    (weight_variance / projected_weight_g) * 100, 1
                )
        
        return Response(response_data)

