"""
Batch viewsets.

These viewsets provide CRUD operations for batch management and analytics.
"""
import re
from datetime import datetime, timedelta
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, Case, When, Q, Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal

from aquamind.api.mixins import RBACFilterMixin
from aquamind.api.permissions import IsOperator
from aquamind.utils.history_mixins import HistoryReasonMixin

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from apps.batch.models import Batch, MortalityEvent
from apps.batch.models.assignment import BatchContainerAssignment
from apps.batch.models.workflow_action import TransferAction
from apps.batch.api.serializers import BatchSerializer
from apps.batch.api.filters.batch import BatchFilter
from apps.environmental.models import EnvironmentalReading
from apps.health.models import FishParameterScore
from apps.inventory.models import FeedingEvent
from .mixins import BatchAnalyticsMixin, GeographyAggregationMixin
from .growth_assimilation_mixin import GrowthAssimilationMixin


class BatchViewSet(RBACFilterMixin, HistoryReasonMixin, BatchAnalyticsMixin, GeographyAggregationMixin, GrowthAssimilationMixin, viewsets.ModelViewSet):
    """
    API endpoint for comprehensive management of aquaculture Batches.

    Provides full CRUD operations for batches, including detailed filtering,
    searching, and ordering capabilities. Batches represent groups of aquatic
    organisms managed together through their lifecycle. Access is restricted to
    operational staff (Operators, Managers, and Admins).
    
    RBAC Enforcement:
    - Permission: IsOperator (OPERATOR/MANAGER/Admin)
    - Geographic Filtering: Users only see batches in their geography
    - Object-level Validation: Prevents creating/updating batches outside user's scope

    Uses HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `batch_number`: Exact match.
    - `species`: Exact match by Species ID.
    - `species__in`: Filter by multiple Species IDs (comma-separated).
    - `lifecycle_stage`: Exact match by LifeCycleStage ID.
    - `lifecycle_stage__in`: Filter by multiple LifeCycleStage IDs (comma-separated).
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
    permission_classes = [IsAuthenticated, IsOperator]
    
    # RBAC configuration - filter by geography through batch assignments -> container
    # Support both area-based and hall-based containers
    geography_filter_fields = [
        'batch_assignments__container__area__geography',  # Sea area containers
        'batch_assignments__container__hall__freshwater_station__geography'  # Hall/station containers
    ]
    enable_operator_location_filtering = True  # Phase 2: Fine-grained operator filtering

    queryset = Batch.objects.annotate(
        _calculated_population_count=Sum(
            'batch_assignments__population_count',
            filter=Q(batch_assignments__is_active=True)
        ),
        _calculated_biomass_kg=Sum(
            'batch_assignments__biomass_kg',
            filter=Q(batch_assignments__is_active=True)
        ),
        # Use a simple annotation for avg_weight_g filtering - exact calculation is in model property
        _calculated_avg_weight_g=Sum(
            'batch_assignments__avg_weight_g',
            filter=Q(batch_assignments__is_active=True)
        )
    ).distinct()
    serializer_class = BatchSerializer
    filterset_class = BatchFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
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

    ENVIRONMENTAL_METRIC_DEFS = {
        'temperature': {
            'label': 'Temperature',
            'aliases': ('temp', 'temperature'),
            'default_unit': 'C',
        },
        'o2': {
            'label': 'O2',
            'aliases': ('o2', 'oxygen', 'dissolved oxygen'),
            'default_unit': 'mg/L',
        },
        'co2': {
            'label': 'CO2',
            'aliases': ('co2', 'carbon dioxide'),
            'default_unit': 'mg/L',
        },
        'no2': {
            'label': 'NO2',
            'aliases': ('no2', 'nitrite'),
            'default_unit': 'mg/L',
        },
        'no3': {
            'label': 'NO3',
            'aliases': ('no3', 'nitrate'),
            'default_unit': 'mg/L',
        },
        'ph': {
            'label': 'pH',
            'aliases': ('ph',),
            'default_unit': '',
        },
        'salinity': {
            'label': 'Salinity',
            'aliases': ('salinity', 'salt'),
            'default_unit': 'ppt',
        },
    }

    INSIGHTS_SCOPE_VALUES = {'batch', 'container', 'lineage'}

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
    
    @action(detail=True, methods=['get'], url_path='planned-activities')
    def planned_activities(self, request, pk=None):
        """Retrieve all planned activities for this batch across all scenarios."""
        from apps.planning.api.serializers import PlannedActivitySerializer
        
        batch = self.get_object()
        activities = batch.planned_activities.select_related(
            'scenario',
            'container',
            'created_by',
            'completed_by',
            'transfer_workflow'
        ).all()
        
        # Apply optional filters
        scenario_id = request.query_params.get('scenario')
        status_filter = request.query_params.get('status')
        
        if scenario_id:
            activities = activities.filter(scenario_id=scenario_id)
        if status_filter:
            activities = activities.filter(status=status_filter)
        
        serializer = PlannedActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='insights-timeseries')
    def insights_timeseries(self, request, pk=None):
        """
        Return daily aggregated insights for a batch, container, or container lineage.

        Query params:
        - start_date (YYYY-MM-DD, optional; default: last 90 days)
        - end_date (YYYY-MM-DD, optional; default: today)
        - scope: batch | container | lineage (optional)
        - container_id (int, optional)
        - assignment_id (int, optional; required for lineage unless inferred)
        """
        batch = self.get_object()
        today = timezone.now().date()

        start_date = self._parse_insights_date_param(
            request.query_params.get('start_date'),
            'start_date'
        ) or (today - timedelta(days=89))
        end_date = self._parse_insights_date_param(
            request.query_params.get('end_date'),
            'end_date'
        ) or today

        if start_date > end_date:
            return Response(
                {'detail': 'start_date must be on or before end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        container_id = self._parse_container_id_param(request.query_params.get('container_id'))
        assignment_id = self._parse_assignment_id_param(request.query_params.get('assignment_id'))
        scope = self._parse_insights_scope_param(
            request.query_params.get('scope'),
            default='container' if container_id else 'batch',
        )

        assignment = None
        if assignment_id:
            assignment = batch.batch_assignments.filter(id=assignment_id).select_related('container').first()
            if not assignment:
                return Response(
                    {'detail': f'assignment_id={assignment_id} does not belong to this batch.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if container_id and assignment.container_id != container_id:
                return Response(
                    {'detail': 'assignment_id does not belong to container_id.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not container_id:
                container_id = assignment.container_id

        if container_id and not batch.batch_assignments.filter(container_id=container_id).exists():
            return Response(
                {'detail': f'container_id={container_id} is not assigned to this batch.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if scope == 'container' and not container_id:
            return Response(
                {'detail': 'container scope requires container_id or assignment_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lineage_assignment_ids = None
        lineage_summary = None
        lineage_container_ids = None
        anchor_assignment_id = assignment_id

        if scope == 'lineage':
            if not anchor_assignment_id:
                if not container_id:
                    return Response(
                        {'detail': 'lineage scope requires assignment_id or container_id.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                active_assignment = batch.batch_assignments.filter(
                    container_id=container_id,
                    is_active=True,
                ).order_by('-assignment_date', '-id').first()
                fallback_assignment = batch.batch_assignments.filter(
                    container_id=container_id,
                ).order_by('-assignment_date', '-id').first()
                anchor = active_assignment or fallback_assignment
                if not anchor:
                    return Response(
                        {'detail': f'No assignment found for container_id={container_id} in this batch.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                anchor_assignment_id = anchor.id
                assignment = anchor
                container_id = anchor.container_id

            lineage_assignment_ids, lineage_summary = self._resolve_lineage_assignments(
                batch.id,
                anchor_assignment_id,
            )
            lineage_container_ids = sorted({
                int(item['container_id'])
                for item in (lineage_summary.get('assignments') if lineage_summary else [])
                if item.get('container_id') is not None
            })

        rows_by_date = {}
        cursor = start_date
        while cursor <= end_date:
            date_key = cursor.isoformat()
            rows_by_date[date_key] = {
                'date': date_key,
                'mortality': 0,
                'feed_kg': 0.0,
                'environmental': {},
                'health_factors': {},
            }
            cursor += timedelta(days=1)

        assignment_filter_ids = set(lineage_assignment_ids) if scope == 'lineage' else None
        self._aggregate_mortality(
            rows_by_date,
            batch.id,
            start_date,
            end_date,
            container_id=container_id if scope == 'container' else None,
            assignment_ids=assignment_filter_ids,
        )
        self._aggregate_feeding(
            rows_by_date,
            batch.id,
            start_date,
            end_date,
            container_id=container_id if scope == 'container' else None,
            assignment_ids=assignment_filter_ids,
            assignment_container_ids=lineage_container_ids,
        )
        environmental_metrics = self._aggregate_environmental(
            rows_by_date,
            batch.id,
            start_date,
            end_date,
            container_id=container_id if scope == 'container' else None,
            assignment_ids=assignment_filter_ids,
            assignment_container_ids=lineage_container_ids,
        )
        health_factors = self._aggregate_health_scores(
            rows_by_date,
            batch.id,
            start_date,
            end_date,
            container_id=container_id if scope == 'container' else None,
            assignment_ids=assignment_filter_ids,
        )

        return Response({
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'scope': scope,
            'container_id': container_id,
            'assignment_id': anchor_assignment_id if scope == 'lineage' else assignment_id,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            'lineage_summary': lineage_summary,
            'environmental_metrics': environmental_metrics,
            'health_factors': health_factors,
            'rows': list(rows_by_date.values()),
        })

    def _parse_insights_date_param(self, raw_value, field_name):
        """Parse YYYY-MM-DD date query params for insights endpoint."""
        if not raw_value:
            return None
        parsed = parse_date(raw_value)
        if parsed is None:
            raise ValidationError({field_name: 'Invalid date format. Use YYYY-MM-DD.'})
        return parsed

    def _parse_container_id_param(self, raw_value):
        """Parse optional container_id query param."""
        if raw_value is None or raw_value == '':
            return None
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValidationError({'container_id': 'container_id must be an integer.'})
        if value <= 0:
            raise ValidationError({'container_id': 'container_id must be a positive integer.'})
        return value

    def _parse_assignment_id_param(self, raw_value):
        """Parse optional assignment_id query param."""
        if raw_value is None or raw_value == '':
            return None
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValidationError({'assignment_id': 'assignment_id must be an integer.'})
        if value <= 0:
            raise ValidationError({'assignment_id': 'assignment_id must be a positive integer.'})
        return value

    def _parse_insights_scope_param(self, raw_value, default='batch'):
        """Parse optional insights scope param."""
        value = (raw_value or default or 'batch').strip().lower()
        if value not in self.INSIGHTS_SCOPE_VALUES:
            valid = ', '.join(sorted(self.INSIGHTS_SCOPE_VALUES))
            raise ValidationError({'scope': f'Invalid scope. Expected one of: {valid}.'})
        return value

    def _resolve_lineage_assignments(self, batch_id, anchor_assignment_id):
        """
        Resolve upstream assignment lineage for an anchor assignment within a batch.

        Traverses completed transfer actions from destination assignment backwards
        to source assignments to build the full ancestry set.
        """
        parent_edges = {}
        actions = TransferAction.objects.filter(
            workflow__batch_id=batch_id,
            status='COMPLETED',
            source_assignment_id__isnull=False,
            dest_assignment_id__isnull=False,
        ).values_list('dest_assignment_id', 'source_assignment_id')

        for dest_assignment_id, source_assignment_id in actions:
            parent_edges.setdefault(dest_assignment_id, set()).add(source_assignment_id)

        visited = set()
        depth = {}
        stack = [(anchor_assignment_id, 0)]
        while stack:
            assignment_id, current_depth = stack.pop()
            if assignment_id in visited:
                continue
            visited.add(assignment_id)
            depth[assignment_id] = current_depth
            for parent_assignment_id in parent_edges.get(assignment_id, set()):
                if parent_assignment_id not in visited:
                    stack.append((parent_assignment_id, current_depth + 1))

        assignment_rows = list(
            BatchContainerAssignment.objects.filter(
                batch_id=batch_id,
                id__in=visited,
            ).values(
                'id',
                'container_id',
                'assignment_date',
                'departure_date',
            )
        )
        valid_assignment_ids = {item['id'] for item in assignment_rows}

        lineage_roots = []
        for assignment_id in valid_assignment_ids:
            parents_in_lineage = {
                parent_id
                for parent_id in parent_edges.get(assignment_id, set())
                if parent_id in valid_assignment_ids
            }
            if not parents_in_lineage:
                lineage_roots.append(assignment_id)

        earliest_assignment_date = min(
            (item['assignment_date'] for item in assignment_rows if item.get('assignment_date')),
            default=None,
        )
        latest_activity_date = max(
            (
                item['departure_date'] or item['assignment_date']
                for item in assignment_rows
                if item.get('assignment_date')
            ),
            default=None,
        )

        summary = {
            'anchor_assignment_id': anchor_assignment_id,
            'assignment_count': len(valid_assignment_ids),
            'container_count': len({item['container_id'] for item in assignment_rows if item.get('container_id')}),
            'max_depth': max((depth.get(assignment_id, 0) for assignment_id in valid_assignment_ids), default=0),
            'root_assignment_ids': sorted(lineage_roots),
            'earliest_assignment_date': earliest_assignment_date.isoformat() if earliest_assignment_date else None,
            'latest_activity_date': latest_activity_date.isoformat() if latest_activity_date else None,
            'assignments': [
                {
                    'assignment_id': item['id'],
                    'container_id': item['container_id'],
                    'assignment_date': item['assignment_date'].isoformat() if item['assignment_date'] else None,
                    'departure_date': item['departure_date'].isoformat() if item['departure_date'] else None,
                }
                for item in assignment_rows
            ],
        }

        return valid_assignment_ids, summary

    def _aggregate_mortality(self, rows_by_date, batch_id, start_date, end_date, container_id=None, assignment_ids=None):
        """Fill daily mortality totals into rows_by_date."""
        queryset = MortalityEvent.objects.filter(
            batch_id=batch_id,
            event_date__gte=start_date,
            event_date__lte=end_date,
        )
        if assignment_ids:
            queryset = queryset.filter(assignment_id__in=assignment_ids)
        elif container_id:
            queryset = queryset.filter(assignment__container_id=container_id)

        daily = queryset.values('event_date').annotate(total_count=Sum('count')).order_by('event_date')
        for item in daily:
            event_date = item['event_date']
            if event_date is None:
                continue
            row = rows_by_date.get(event_date.isoformat())
            if row:
                row['mortality'] = int(item['total_count'] or 0)

    def _aggregate_feeding(
        self,
        rows_by_date,
        batch_id,
        start_date,
        end_date,
        container_id=None,
        assignment_ids=None,
        assignment_container_ids=None,
    ):
        """Fill daily feeding totals into rows_by_date."""
        queryset = FeedingEvent.objects.filter(
            batch_id=batch_id,
            feeding_date__gte=start_date,
            feeding_date__lte=end_date,
        )
        if assignment_ids:
            container_ids = assignment_container_ids or []
            lineage_filter = Q(batch_assignment_id__in=assignment_ids)
            if container_ids:
                lineage_filter |= Q(batch_assignment__isnull=True, container_id__in=container_ids)
            queryset = queryset.filter(lineage_filter)
        elif container_id:
            queryset = queryset.filter(container_id=container_id)

        daily = queryset.values('feeding_date').annotate(total_feed_kg=Sum('amount_kg')).order_by('feeding_date')
        for item in daily:
            feeding_date = item['feeding_date']
            if feeding_date is None:
                continue
            row = rows_by_date.get(feeding_date.isoformat())
            if row:
                row['feed_kg'] = float(item['total_feed_kg'] or 0.0)

    def _aggregate_environmental(
        self,
        rows_by_date,
        batch_id,
        start_date,
        end_date,
        container_id=None,
        assignment_ids=None,
        assignment_container_ids=None,
    ):
        """Fill daily environmental averages into rows_by_date and return metric metadata."""
        current_tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()), current_tz)
        end_exclusive = end_date + timedelta(days=1)
        end_dt = timezone.make_aware(datetime.combine(end_exclusive, datetime.min.time()), current_tz)

        queryset = EnvironmentalReading.objects.filter(
            batch_id=batch_id,
            reading_time__gte=start_dt,
            reading_time__lt=end_dt,
        )
        if assignment_ids:
            container_ids = assignment_container_ids or []
            lineage_filter = Q(batch_container_assignment_id__in=assignment_ids)
            if container_ids:
                lineage_filter |= Q(batch_container_assignment__isnull=True, container_id__in=container_ids)
            queryset = queryset.filter(lineage_filter)
        elif container_id:
            queryset = queryset.filter(
                Q(container_id=container_id) | Q(batch_container_assignment__container_id=container_id)
            )

        daily = queryset.annotate(day=TruncDate('reading_time')).values(
            'day',
            'parameter__name',
            'parameter__unit',
        ).annotate(
            avg_value=Avg('value'),
            sample_count=Count('id'),
        ).order_by('day')

        weighted_acc = {}
        seen_metric_keys = set()
        metric_units = {}

        for item in daily:
            day = item['day']
            if day is None:
                continue

            metric_key = self._map_environmental_metric(item.get('parameter__name'))
            if not metric_key:
                continue

            avg_value = item.get('avg_value')
            sample_count = int(item.get('sample_count') or 0)
            if avg_value is None or sample_count <= 0:
                continue

            row_metric_key = (day.isoformat(), metric_key)
            current = weighted_acc.get(row_metric_key, {'weighted_sum': 0.0, 'count': 0})
            current['weighted_sum'] += float(avg_value) * sample_count
            current['count'] += sample_count
            weighted_acc[row_metric_key] = current
            seen_metric_keys.add(metric_key)

            unit = item.get('parameter__unit')
            if unit and metric_key not in metric_units:
                metric_units[metric_key] = unit

        for (date_key, metric_key), acc in weighted_acc.items():
            row = rows_by_date.get(date_key)
            if not row or acc['count'] <= 0:
                continue
            row['environmental'][metric_key] = acc['weighted_sum'] / acc['count']

        metrics = []
        for metric_key in sorted(seen_metric_keys):
            definition = self.ENVIRONMENTAL_METRIC_DEFS[metric_key]
            metrics.append({
                'key': metric_key,
                'label': definition['label'],
                'unit': metric_units.get(metric_key, definition['default_unit']),
            })
        return metrics

    def _aggregate_health_scores(self, rows_by_date, batch_id, start_date, end_date, container_id=None, assignment_ids=None):
        """Fill daily average health factor scores into rows_by_date and return factor metadata."""
        queryset = FishParameterScore.objects.filter(
            individual_fish_observation__sampling_event__assignment__batch_id=batch_id,
            individual_fish_observation__sampling_event__sampling_date__gte=start_date,
            individual_fish_observation__sampling_event__sampling_date__lte=end_date,
        )
        if assignment_ids:
            queryset = queryset.filter(
                individual_fish_observation__sampling_event__assignment_id__in=assignment_ids
            )
        elif container_id:
            queryset = queryset.filter(
                individual_fish_observation__sampling_event__assignment__container_id=container_id
            )

        daily = queryset.values(
            'individual_fish_observation__sampling_event__sampling_date',
            'parameter_id',
            'parameter__name',
            'parameter__min_score',
            'parameter__max_score',
        ).annotate(avg_score=Avg('score')).order_by(
            'individual_fish_observation__sampling_event__sampling_date',
            'parameter_id',
        )

        factors_by_key = {}
        for item in daily:
            score_date = item.get('individual_fish_observation__sampling_event__sampling_date')
            if score_date is None:
                continue

            parameter_id = item.get('parameter_id')
            parameter_name = item.get('parameter__name') or f'Parameter {parameter_id}'
            factor_key = self._health_factor_key(parameter_name, parameter_id)

            row = rows_by_date.get(score_date.isoformat())
            if row:
                row['health_factors'][factor_key] = float(item.get('avg_score') or 0.0)

            factors_by_key[factor_key] = {
                'key': factor_key,
                'label': parameter_name,
                'parameter_id': parameter_id,
                'min_score': int(item.get('parameter__min_score') if item.get('parameter__min_score') is not None else 0),
                'max_score': int(item.get('parameter__max_score') if item.get('parameter__max_score') is not None else 4),
            }

        return list(factors_by_key.values())

    def _map_environmental_metric(self, parameter_name):
        """Map an environmental parameter name to a canonical insight metric key."""
        if not parameter_name:
            return None
        normalized = str(parameter_name).strip().lower()
        tokens = {
            token for token in re.split(r'[^a-z0-9]+', normalized) if token
        }
        for metric_key, definition in self.ENVIRONMENTAL_METRIC_DEFS.items():
            aliases = definition.get('aliases') or ()
            for alias in aliases:
                if alias in {'o2', 'co2', 'no2', 'no3', 'ph'}:
                    if alias == normalized or alias in tokens:
                        return metric_key
                elif alias in normalized:
                    return metric_key
        return None

    def _health_factor_key(self, parameter_name, parameter_id):
        """Create a stable, frontend-safe key for a health factor."""
        normalized = re.sub(r'[^a-z0-9]+', '_', str(parameter_name).lower()).strip('_')
        if normalized:
            return normalized
        return f'factor_{parameter_id}'
