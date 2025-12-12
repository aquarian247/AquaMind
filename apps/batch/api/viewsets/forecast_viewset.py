"""
Forecast viewset for executive dashboard forecasting.

Provides aggregation endpoints for harvest and sea-transfer forecasts,
following the patterns established in GeographyAggregationMixin.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Min, Max, Avg, Sum, Q, F, Subquery, OuterRef
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import Batch, BatchContainerAssignment, ActualDailyAssignmentState
from apps.scenario.models import ScenarioProjection, ProjectionRun
from apps.planning.models import PlannedActivity
from apps.infrastructure.models import Geography
from aquamind.api.permissions import IsOperator


def get_harvest_thresholds():
    """Get harvest thresholds from settings or use defaults."""
    return getattr(settings, 'HARVEST_THRESHOLDS', {
        'atlantic_salmon': {'min_weight_g': 4500, 'target_weight_g': 5000},
        'rainbow_trout': {'min_weight_g': 2500, 'target_weight_g': 3000},
        'default': {'min_weight_g': 4000, 'target_weight_g': 5000}
    })


def get_sea_transfer_criteria():
    """Get sea transfer criteria from settings or use defaults."""
    return getattr(settings, 'SEA_TRANSFER_CRITERIA', {
        'atlantic_salmon': {'min_weight_g': 80, 'target_weight_g': 100},
        'default': {'min_weight_g': 100, 'target_weight_g': 100}
    })


def get_threshold_for_species(thresholds, species_name):
    """Get threshold config for a specific species, falling back to default."""
    species_key = species_name.lower().replace(' ', '_')
    return thresholds.get(species_key, thresholds.get('default', {}))


class ForecastViewSet(viewsets.ViewSet):
    """
    ViewSet for executive forecast endpoints.
    
    Provides harvest and sea-transfer forecasts aggregated across batches.
    
    Note: This ViewSet uses @extend_schema decorators for inline response
    schemas instead of traditional DRF serializers. The serializer_class
    is set to None to satisfy contract tests while indicating this
    intentional design choice.
    """
    permission_classes = [IsAuthenticated, IsOperator]
    
    # ViewSet returns direct Response objects with inline schemas defined
    # via @extend_schema decorators. Empty serializer_classes dict satisfies
    # contract tests while indicating serializers are intentionally not used.
    serializer_classes = {}

    def _get_geography_filter(self, geography_id):
        """Build Q filter for geography-based batch filtering."""
        return (
            Q(batch_assignments__container__hall__freshwater_station__geography_id=geography_id) |
            Q(batch_assignments__container__area__geography_id=geography_id)
        )

    def _get_latest_actual_state(self, batch):
        """Get the latest ActualDailyAssignmentState for a batch."""
        return ActualDailyAssignmentState.objects.filter(
            batch=batch
        ).order_by('-date').first()

    def _get_earliest_harvest_date(self, batch, threshold_weight):
        """
        Find the earliest projection date where weight >= threshold.
        
        Uses the batch's pinned projection run if available.
        """
        # Try to get projections from pinned run or latest run
        projection_run = batch.pinned_projection_run
        
        if not projection_run:
            # Get the latest projection run for any scenario related to this batch
            projection_run = ProjectionRun.objects.filter(
                scenario__planned_activities__batch=batch
            ).order_by('-run_date').first()
        
        if not projection_run:
            return None
        
        # Find earliest date where weight >= threshold
        projection = ScenarioProjection.objects.filter(
            projection_run=projection_run,
            average_weight__gte=threshold_weight,
            projection_date__gte=date.today()
        ).order_by('projection_date').first()
        
        if projection:
            return projection.projection_date
        
        return None

    def _get_facility_name(self, batch):
        """Get the facility name for a batch from its active assignments."""
        assignment = batch.batch_assignments.filter(is_active=True).first()
        if not assignment:
            return "Unknown"
        
        container = assignment.container
        if container.hall:
            return container.hall.freshwater_station.name
        elif container.area:
            return container.area.name
        return "Unknown"

    def _get_planned_harvest_activity(self, batch):
        """Get any planned HARVEST activity for this batch."""
        return PlannedActivity.objects.filter(
            batch=batch,
            activity_type='HARVEST',
            status__in=['PENDING', 'IN_PROGRESS']
        ).order_by('due_date').first()

    def _get_planned_transfer_activity(self, batch):
        """Get any planned TRANSFER activity for this batch."""
        return PlannedActivity.objects.filter(
            batch=batch,
            activity_type='TRANSFER',
            status__in=['PENDING', 'IN_PROGRESS']
        ).order_by('due_date').first()

    def _calculate_quarterly_aggregation(self, upcoming_batches):
        """Aggregate upcoming harvests by quarter."""
        by_quarter = {}
        
        for batch_data in upcoming_batches:
            harvest_date = batch_data.get('projected_harvest_date')
            if not harvest_date:
                continue
            
            # Parse date if string
            if isinstance(harvest_date, str):
                harvest_date = date.fromisoformat(harvest_date)
            
            quarter = (harvest_date.month - 1) // 3 + 1
            quarter_key = f"Q{quarter}_{harvest_date.year}"
            
            if quarter_key not in by_quarter:
                by_quarter[quarter_key] = {'count': 0, 'biomass_tonnes': 0}
            
            by_quarter[quarter_key]['count'] += 1
            biomass_kg = batch_data.get('projected_biomass_kg', 0) or 0
            by_quarter[quarter_key]['biomass_tonnes'] += biomass_kg / 1000
        
        # Round biomass values
        for key in by_quarter:
            by_quarter[key]['biomass_tonnes'] = round(by_quarter[key]['biomass_tonnes'], 2)
        
        return by_quarter

    def _calculate_monthly_aggregation(self, upcoming_batches, date_field='projected_transfer_date'):
        """Aggregate upcoming transfers by month."""
        by_month = {}
        
        for batch_data in upcoming_batches:
            transfer_date = batch_data.get(date_field)
            if not transfer_date:
                continue
            
            # Parse date if string
            if isinstance(transfer_date, str):
                transfer_date = date.fromisoformat(transfer_date)
            
            month_key = f"{transfer_date.year}-{transfer_date.month:02d}"
            
            if month_key not in by_month:
                by_month[month_key] = {'count': 0}
            
            by_month[month_key]['count'] += 1
        
        return by_month

    @method_decorator(cache_page(60))  # Cache for 60 seconds
    @extend_schema(
        operation_id="forecastviewset_harvest",
        summary="Get harvest forecast for batches approaching harvest weight",
        description=(
            "Returns aggregated harvest forecast showing batches approaching harvest weight threshold.\n\n"
            "Uses projection data to find the earliest date when batches will reach species-specific "
            "harvest weight thresholds, enriched with confidence scores from actual daily states "
            "and existing planned HARVEST activities.\n\n"
            "Useful for executive dashboards and harvest planning."
        ),
        parameters=[
            OpenApiParameter(
                name="geography_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by geography ID (optional)",
                required=False,
            ),
            OpenApiParameter(
                name="species_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by species ID (optional)",
                required=False,
            ),
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter projections from this date (ISO 8601: YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter projections until this date (ISO 8601: YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="min_confidence",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Minimum confidence score (0-1, default 0.5)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total_batches": {"type": "integer"},
                                "harvest_ready_count": {"type": "integer"},
                                "avg_days_to_harvest": {"type": "number", "nullable": True},
                                "total_projected_biomass_tonnes": {"type": "number"},
                            },
                        },
                        "upcoming": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "batch_id": {"type": "integer"},
                                    "batch_number": {"type": "string"},
                                    "species": {"type": "string"},
                                    "facility": {"type": "string"},
                                    "current_weight_g": {"type": "number", "nullable": True},
                                    "target_weight_g": {"type": "number"},
                                    "projected_harvest_date": {"type": "string", "format": "date", "nullable": True},
                                    "days_until_harvest": {"type": "integer", "nullable": True},
                                    "projected_biomass_kg": {"type": "number", "nullable": True},
                                    "confidence": {"type": "number", "nullable": True},
                                    "planned_activity_id": {"type": "integer", "nullable": True},
                                    "planned_activity_status": {"type": "string", "nullable": True},
                                },
                            },
                        },
                        "by_quarter": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "count": {"type": "integer"},
                                    "biomass_tonnes": {"type": "number"},
                                },
                            },
                        },
                    },
                },
                description="Harvest forecast data",
            ),
        },
    )
    @action(detail=False, methods=['get'], url_path='harvest')
    def harvest(self, request):
        """
        Get harvest forecast for batches approaching harvest weight.
        """
        # Parse query parameters
        geography_id = request.query_params.get('geography_id')
        species_id = request.query_params.get('species_id')
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')
        min_confidence = float(request.query_params.get('min_confidence', 0.5))

        # Parse dates
        from_date = None
        to_date = None
        if from_date_str:
            try:
                from_date = date.fromisoformat(from_date_str)
            except ValueError:
                raise ValidationError({'from_date': 'Invalid date format. Use YYYY-MM-DD'})
        if to_date_str:
            try:
                to_date = date.fromisoformat(to_date_str)
            except ValueError:
                raise ValidationError({'to_date': 'Invalid date format. Use YYYY-MM-DD'})

        # Build batch queryset
        batches = Batch.objects.filter(status='ACTIVE')
        
        if geography_id:
            try:
                geography_id = int(geography_id)
                Geography.objects.get(id=geography_id)  # Validate exists
            except (ValueError, TypeError):
                raise ValidationError({'geography_id': 'Invalid geography ID'})
            except Geography.DoesNotExist:
                raise ValidationError({'geography_id': 'Geography not found'})
            
            batches = batches.filter(self._get_geography_filter(geography_id)).distinct()

        if species_id:
            try:
                species_id = int(species_id)
            except (ValueError, TypeError):
                raise ValidationError({'species_id': 'Invalid species ID'})
            batches = batches.filter(species_id=species_id)

        # Get harvest thresholds
        thresholds = get_harvest_thresholds()
        
        # Process each batch
        upcoming = []
        harvest_ready_count = 0
        total_biomass_tonnes = 0
        days_to_harvest_list = []
        
        for batch in batches.select_related('species', 'lifecycle_stage'):
            species_thresholds = get_threshold_for_species(thresholds, batch.species.name)
            target_weight = species_thresholds.get('target_weight_g', 5000)
            
            # Get current state
            latest_state = self._get_latest_actual_state(batch)
            current_weight = float(latest_state.avg_weight_g) if latest_state else None
            confidence = latest_state.confidence_overall if latest_state else None
            
            # Skip if below minimum confidence
            if confidence is not None and confidence < min_confidence:
                continue
            
            # Get projected harvest date
            projected_date = self._get_earliest_harvest_date(batch, target_weight)
            
            # Apply date filters
            if from_date and projected_date and projected_date < from_date:
                continue
            if to_date and projected_date and projected_date > to_date:
                continue
            
            # Calculate days until harvest
            days_until = None
            if projected_date:
                days_until = (projected_date - date.today()).days
                if days_until >= 0:
                    days_to_harvest_list.append(days_until)
            
            # Check if harvest ready (current weight >= target)
            if current_weight and current_weight >= target_weight:
                harvest_ready_count += 1
            
            # Get facility name
            facility = self._get_facility_name(batch)
            
            # Get current biomass
            current_biomass = float(batch.calculated_biomass_kg) if batch.calculated_biomass_kg else 0
            total_biomass_tonnes += current_biomass / 1000
            
            # Get planned activity
            planned_activity = self._get_planned_harvest_activity(batch)
            
            batch_data = {
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'species': batch.species.name,
                'facility': facility,
                'current_weight_g': current_weight,
                'target_weight_g': target_weight,
                'projected_harvest_date': projected_date.isoformat() if projected_date else None,
                'days_until_harvest': days_until,
                'projected_biomass_kg': current_biomass,
                'confidence': round(confidence, 2) if confidence is not None else None,
                'planned_activity_id': planned_activity.id if planned_activity else None,
                'planned_activity_status': planned_activity.status if planned_activity else None,
            }
            upcoming.append(batch_data)
        
        # Sort by projected date (None values at end)
        upcoming.sort(key=lambda x: (x['projected_harvest_date'] is None, x['projected_harvest_date'] or ''))
        
        # Calculate summary
        avg_days = None
        if days_to_harvest_list:
            avg_days = round(sum(days_to_harvest_list) / len(days_to_harvest_list), 1)
        
        # Calculate quarterly aggregation
        by_quarter = self._calculate_quarterly_aggregation(upcoming)
        
        return Response({
            'summary': {
                'total_batches': len(upcoming),
                'harvest_ready_count': harvest_ready_count,
                'avg_days_to_harvest': avg_days,
                'total_projected_biomass_tonnes': round(total_biomass_tonnes, 2),
            },
            'upcoming': upcoming,
            'by_quarter': by_quarter,
        })

    @method_decorator(cache_page(60))  # Cache for 60 seconds
    @extend_schema(
        operation_id="forecastviewset_sea_transfer",
        summary="Get sea-transfer forecast for freshwater batches approaching smolt stage",
        description=(
            "Returns aggregated sea-transfer forecast showing freshwater batches approaching "
            "smolt weight threshold for transfer to sea cages.\n\n"
            "Only includes batches currently in freshwater facilities (containers in halls). "
            "Uses projection data to find the earliest date when batches will reach "
            "species-specific transfer weight thresholds.\n\n"
            "Useful for executive dashboards and transfer planning."
        ),
        parameters=[
            OpenApiParameter(
                name="geography_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by geography ID (optional)",
                required=False,
            ),
            OpenApiParameter(
                name="species_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by species ID (optional)",
                required=False,
            ),
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter projections from this date (ISO 8601: YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter projections until this date (ISO 8601: YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="min_confidence",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Minimum confidence score (0-1, default 0.5)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "object",
                            "properties": {
                                "total_freshwater_batches": {"type": "integer"},
                                "transfer_ready_count": {"type": "integer"},
                                "avg_days_to_transfer": {"type": "number", "nullable": True},
                            },
                        },
                        "upcoming": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "batch_id": {"type": "integer"},
                                    "batch_number": {"type": "string"},
                                    "current_stage": {"type": "string"},
                                    "target_stage": {"type": "string"},
                                    "current_facility": {"type": "string"},
                                    "target_facility": {"type": "string", "nullable": True},
                                    "projected_transfer_date": {"type": "string", "format": "date", "nullable": True},
                                    "days_until_transfer": {"type": "integer", "nullable": True},
                                    "current_weight_g": {"type": "number", "nullable": True},
                                    "target_weight_g": {"type": "number"},
                                    "confidence": {"type": "number", "nullable": True},
                                    "planned_activity_id": {"type": "integer", "nullable": True},
                                },
                            },
                        },
                        "by_month": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "count": {"type": "integer"},
                                },
                            },
                        },
                    },
                },
                description="Sea-transfer forecast data",
            ),
        },
    )
    @action(detail=False, methods=['get'], url_path='sea-transfer')
    def sea_transfer(self, request):
        """
        Get sea-transfer forecast for freshwater batches approaching smolt stage.
        """
        # Parse query parameters
        geography_id = request.query_params.get('geography_id')
        species_id = request.query_params.get('species_id')
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')
        min_confidence = float(request.query_params.get('min_confidence', 0.5))

        # Parse dates
        from_date = None
        to_date = None
        if from_date_str:
            try:
                from_date = date.fromisoformat(from_date_str)
            except ValueError:
                raise ValidationError({'from_date': 'Invalid date format. Use YYYY-MM-DD'})
        if to_date_str:
            try:
                to_date = date.fromisoformat(to_date_str)
            except ValueError:
                raise ValidationError({'to_date': 'Invalid date format. Use YYYY-MM-DD'})

        # Build batch queryset - only freshwater batches (containers in halls)
        # A batch is in freshwater if it has an active assignment to a container in a hall
        freshwater_batches = Batch.objects.filter(
            status='ACTIVE',
            batch_assignments__is_active=True,
            batch_assignments__container__hall__isnull=False  # Container in hall = freshwater
        ).distinct()
        
        if geography_id:
            try:
                geography_id = int(geography_id)
                Geography.objects.get(id=geography_id)  # Validate exists
            except (ValueError, TypeError):
                raise ValidationError({'geography_id': 'Invalid geography ID'})
            except Geography.DoesNotExist:
                raise ValidationError({'geography_id': 'Geography not found'})
            
            freshwater_batches = freshwater_batches.filter(
                batch_assignments__container__hall__freshwater_station__geography_id=geography_id
            ).distinct()

        if species_id:
            try:
                species_id = int(species_id)
            except (ValueError, TypeError):
                raise ValidationError({'species_id': 'Invalid species ID'})
            freshwater_batches = freshwater_batches.filter(species_id=species_id)

        # Get sea transfer criteria
        criteria = get_sea_transfer_criteria()
        
        # Process each batch
        upcoming = []
        transfer_ready_count = 0
        days_to_transfer_list = []
        
        for batch in freshwater_batches.select_related('species', 'lifecycle_stage'):
            species_criteria = get_threshold_for_species(criteria, batch.species.name)
            target_weight = species_criteria.get('target_weight_g', 100)
            
            # Get current state
            latest_state = self._get_latest_actual_state(batch)
            current_weight = float(latest_state.avg_weight_g) if latest_state else None
            confidence = latest_state.confidence_overall if latest_state else None
            
            # Skip if below minimum confidence
            if confidence is not None and confidence < min_confidence:
                continue
            
            # Get projected transfer date
            projected_date = self._get_earliest_harvest_date(batch, target_weight)
            
            # Apply date filters
            if from_date and projected_date and projected_date < from_date:
                continue
            if to_date and projected_date and projected_date > to_date:
                continue
            
            # Calculate days until transfer
            days_until = None
            if projected_date:
                days_until = (projected_date - date.today()).days
                if days_until >= 0:
                    days_to_transfer_list.append(days_until)
            
            # Check if transfer ready (current weight >= target)
            if current_weight and current_weight >= target_weight:
                transfer_ready_count += 1
            
            # Get facility names
            current_facility = self._get_facility_name(batch)
            
            # Get planned activity to determine target facility if specified
            planned_activity = self._get_planned_transfer_activity(batch)
            target_facility = None
            if planned_activity and planned_activity.container:
                if planned_activity.container.area:
                    target_facility = planned_activity.container.area.name
            
            # Determine target stage (typically 'Smolt' for sea transfer)
            target_stage = 'Smolt'
            
            batch_data = {
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'current_stage': batch.lifecycle_stage.name,
                'target_stage': target_stage,
                'current_facility': current_facility,
                'target_facility': target_facility,
                'projected_transfer_date': projected_date.isoformat() if projected_date else None,
                'days_until_transfer': days_until,
                'current_weight_g': current_weight,
                'target_weight_g': target_weight,
                'confidence': round(confidence, 2) if confidence is not None else None,
                'planned_activity_id': planned_activity.id if planned_activity else None,
            }
            upcoming.append(batch_data)
        
        # Sort by projected date (None values at end)
        upcoming.sort(key=lambda x: (x['projected_transfer_date'] is None, x['projected_transfer_date'] or ''))
        
        # Calculate summary
        avg_days = None
        if days_to_transfer_list:
            avg_days = round(sum(days_to_transfer_list) / len(days_to_transfer_list), 1)
        
        # Calculate monthly aggregation
        by_month = self._calculate_monthly_aggregation(upcoming, 'projected_transfer_date')
        
        return Response({
            'summary': {
                'total_freshwater_batches': len(upcoming),
                'transfer_ready_count': transfer_ready_count,
                'avg_days_to_transfer': avg_days,
            },
            'upcoming': upcoming,
            'by_month': by_month,
        })

