"""
Live Forward Projection Engine.

This module implements the core computation engine for live forward projections.
It projects future growth trajectories from the latest ActualDailyAssignmentState,
using temperature bias computed from recent sensor-derived readings.

Architecture:
- Uses existing TGCCalculator for growth math (same formula family as scenario)
- Uses MortalityCalculator for population decay
- Temperature bias computed from recent days with sensor-derived temps
- Stores projections in LiveForwardProjection hypertable
- Updates ContainerForecastSummary for fast dashboard queries

Key design decisions:
- FCR does NOT drive growth (FCR can be derived later for feed forecasting)
- Future temps = profile_temp(day_number) + bias
- Bias computed from sensor days, clamped to configurable bounds
- Projections run until scenario end (not artificial 365-day cap)

Issue: Live Forward Projection Feature
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.batch.models import (
    BatchContainerAssignment,
    ActualDailyAssignmentState,
    LiveForwardProjection,
    ContainerForecastSummary,
)
from apps.planning.models import PlannedActivity
from apps.scenario.models import Scenario
from apps.scenario.services.calculations.tgc_calculator import TGCCalculator
from apps.scenario.services.calculations.mortality_calculator import (
    MortalityCalculator
)

logger = logging.getLogger(__name__)


class LiveProjectionEngine:
    """
    Engine for computing live forward projections from current actual state.

    This engine:
    1. Gets latest ActualDailyAssignmentState for an assignment
    2. Computes temperature bias from recent sensor-derived temps
    3. Projects forward using TGC growth + mortality decay
    4. Stores projections in LiveForwardProjection
    5. Updates ContainerForecastSummary with key crossing dates

    Usage:
        engine = LiveProjectionEngine(assignment)
        engine.compute_and_store()
    """

    def __init__(self, assignment: BatchContainerAssignment):
        """
        Initialize engine for a specific batch-container assignment.

        Args:
            assignment: The BatchContainerAssignment to project for
        """
        self.assignment = assignment
        self.batch = assignment.batch
        self.container = assignment.container

        # Load settings
        self.bias_window_days = getattr(
            settings, 'LIVE_FORWARD_TEMP_BIAS_WINDOW_DAYS', 14
        )
        self.bias_clamp = getattr(
            settings, 'LIVE_FORWARD_TEMP_BIAS_CLAMP_C', (-2.0, 2.0)
        )
        self.max_horizon = getattr(
            settings, 'LIVE_FORWARD_MAX_HORIZON_DAYS', 1000
        )
        self.attention_threshold_days = getattr(
            settings, 'LIVE_FORWARD_ATTENTION_THRESHOLD_DAYS', 30
        )

        # Get scenario (required)
        self.scenario = self._get_scenario()
        if not self.scenario:
            raise ValueError(
                f"No scenario available for batch {self.batch.batch_number}. "
                f"Pin a projection run or assign a scenario."
            )

        # Initialize calculators
        self.tgc_calculator = TGCCalculator(self.scenario.tgc_model)
        self.mortality_calculator = MortalityCalculator(
            self.scenario.mortality_model
        )

        # Temperature profile from TGC model
        self.temp_profile = self.scenario.tgc_model.profile

        # Load lifecycle stages and durations for stage transitions
        self._load_lifecycle_stages()

        logger.debug(
            f"Initialized LiveProjectionEngine for assignment {assignment.id} "
            f"(Batch: {self.batch.batch_number}, Container: {self.container.name})"
        )

    def _get_scenario(self) -> Optional[Scenario]:
        """Get scenario for TGC/mortality models."""
        if self.batch.pinned_projection_run:
            return self.batch.pinned_projection_run.scenario
        return self.batch.scenarios.first()

    def _load_lifecycle_stages(self) -> None:
        """
        Load lifecycle stages and their durations for time-based transitions.
        
        This mirrors the ProjectionEngine's stage loading to ensure consistent
        stage transitions. Stages are determined by elapsed time, not weight.
        """
        from apps.batch.models import LifeCycleStage
        
        self.lifecycle_stages = list(
            LifeCycleStage.objects.order_by('order')
        )
        
        # Get stage durations from FCR model
        self.stage_durations = {}
        self.cumulative_stage_days = {}
        
        # Try to load stage durations from FCR model
        if self.scenario.fcr_model and hasattr(self.scenario.fcr_model, 'stages'):
            fcr_stages = self.scenario.fcr_model.stages.select_related('stage').all()
            cumulative_days = 0
            
            for fcr_stage in fcr_stages:
                # stage is FK to LifeCycleStage
                stage_name = fcr_stage.stage.name if fcr_stage.stage else None
                if not stage_name:
                    continue
                duration = fcr_stage.duration_days or 90  # Default 90 days
                
                self.stage_durations[stage_name] = duration
                self.cumulative_stage_days[stage_name] = cumulative_days
                cumulative_days += duration
        
        # Fall back to defaults if no stages were loaded
        # (handles: no FCR model, FCR model without stages, or empty stages)
        if not self.stage_durations:
            default_stages = [
                ('Egg&Alevin', 90),
                ('Fry', 90),
                ('Parr', 90),
                ('Smolt', 90),
                ('Post-Smolt', 90),
                ('Adult', 450),
            ]
            cumulative_days = 0
            for stage_name, duration in default_stages:
                self.stage_durations[stage_name] = duration
                self.cumulative_stage_days[stage_name] = cumulative_days
                cumulative_days += duration

    def _determine_lifecycle_stage(self, day_number: int):
        """
        Determine lifecycle stage based on elapsed days (time-based transitions).
        
        This mirrors the ProjectionEngine's stage determination to ensure
        live projections use the same stage transitions as scenario projections.
        
        Args:
            day_number: Current day number in the scenario (1-based)
            
        Returns:
            LifeCycleStage for the given day, or None
        """
        # day_number is 1-based, so day 1 has elapsed 0 days
        elapsed_days = day_number - 1
        
        for stage in self.lifecycle_stages:
            stage_name = stage.name
            
            if stage_name not in self.cumulative_stage_days:
                continue
            
            stage_start = self.cumulative_stage_days[stage_name]
            stage_duration = self.stage_durations.get(stage_name, 90)
            stage_end = stage_start + stage_duration
            
            if stage_start <= elapsed_days < stage_end:
                return stage
        
        # If past all stages, return last stage (Adult)
        return self.lifecycle_stages[-1] if self.lifecycle_stages else None

    def compute_and_store(self, computed_date: Optional[date] = None) -> Dict:
        """
        Compute projections and store to database.

        This is the main entry point. It:
        1. Gets latest actual state as starting point
        2. Computes temperature bias
        3. Projects forward to scenario end (or max horizon)
        4. Bulk inserts LiveForwardProjection rows
        5. Updates ContainerForecastSummary

        Args:
            computed_date: Date to use as computed_date (default: today)

        Returns:
            Dict with stats (rows_created, bias_computed, horizon_days, etc.)
        """
        if computed_date is None:
            computed_date = timezone.now().date()

        # Step 1: Get latest actual state
        latest_state = ActualDailyAssignmentState.objects.filter(
            assignment=self.assignment
        ).order_by('-date').first()

        if not latest_state:
            logger.warning(
                f"No actual state for assignment {self.assignment.id} - "
                f"cannot compute projection"
            )
            return {
                'success': False,
                'error': 'No actual state available',
                'assignment_id': self.assignment.id,
            }

        # Step 2: Compute temperature bias
        bias_c, bias_metadata = self._compute_temperature_bias(latest_state)

        # Step 3: Determine projection horizon
        start_date = latest_state.date
        start_day = latest_state.day_number

        # Project until scenario end (or max horizon as safety cap)
        scenario_end_day = self.scenario.duration_days
        remaining_days = scenario_end_day - start_day
        horizon_days = min(remaining_days, self.max_horizon)

        if horizon_days <= 0:
            logger.info(
                f"Assignment {self.assignment.id} at or past scenario end - "
                f"no projection needed"
            )
            return {
                'success': True,
                'rows_created': 0,
                'reason': 'At or past scenario end',
                'assignment_id': self.assignment.id,
            }

        end_date = start_date + timedelta(days=horizon_days)

        logger.info(
            f"Computing projection for assignment {self.assignment.id}: "
            f"day {start_day} to {scenario_end_day} ({horizon_days} days), "
            f"bias={bias_c}°C"
        )

        # Step 4: Project forward
        projections = self._project_forward(
            start_state=latest_state,
            start_date=start_date,
            horizon_days=horizon_days,
            computed_date=computed_date,
            bias_c=bias_c,
            bias_metadata=bias_metadata,
        )

        # Step 5: Store projections (delete existing for idempotency)
        with transaction.atomic():
            # Delete existing projections for this assignment/computed_date
            deleted_count = LiveForwardProjection.objects.filter(
                assignment=self.assignment,
                computed_date=computed_date,
            ).delete()[0]

            if deleted_count > 0:
                logger.debug(
                    f"Deleted {deleted_count} existing projections for "
                    f"assignment {self.assignment.id} on {computed_date}"
                )

            # Bulk create new projections
            LiveForwardProjection.objects.bulk_create(
                projections, batch_size=500
            )

            # Step 6: Update summary
            self._update_forecast_summary(
                latest_state=latest_state,
                projections=projections,
                computed_date=computed_date,
                bias_c=bias_c,
                bias_metadata=bias_metadata,
            )

        return {
            'success': True,
            'rows_created': len(projections),
            'assignment_id': self.assignment.id,
            'start_day': start_day,
            'horizon_days': horizon_days,
            'bias_c': float(bias_c),
            'bias_window_days': bias_metadata.get('window_days_used', 0),
        }

    def _compute_temperature_bias(
        self,
        latest_state: ActualDailyAssignmentState
    ) -> Tuple[Decimal, Dict]:
        """
        Compute temperature bias from recent sensor-derived temps.

        Looks at recent N days where sources['temp'] indicates sensor data:
        - 'measured': Direct sensor reading
        - 'interpolated': Interpolated between readings
        - 'nearest_before' / 'nearest_after': Nearest sensor reading

        For each such day, computes delta = actual_temp - profile_temp.
        Bias = mean(deltas), clamped to configured bounds.

        Args:
            latest_state: Most recent ActualDailyAssignmentState

        Returns:
            Tuple of (bias_c, metadata_dict)
        """
        sensor_sources = {'measured', 'interpolated', 'nearest_before',
                          'nearest_after'}

        # Get recent states with sensor-derived temps
        window_start = latest_state.date - timedelta(days=self.bias_window_days)
        recent_states = ActualDailyAssignmentState.objects.filter(
            assignment=self.assignment,
            date__gte=window_start,
            date__lte=latest_state.date,
            temp_c__isnull=False,
        ).order_by('-date')

        deltas = []
        for state in recent_states:
            sources = state.sources or {}
            temp_source = sources.get('temp', '')

            if temp_source in sensor_sources:
                # Get profile temp for this day_number
                profile_temp = self.tgc_calculator._get_temperature_for_day(
                    state.day_number
                )

                if profile_temp and profile_temp > 0:
                    delta = float(state.temp_c) - profile_temp
                    deltas.append(delta)

        # Compute mean bias
        if deltas:
            raw_bias = sum(deltas) / len(deltas)
            # Clamp to bounds
            bias_c = max(self.bias_clamp[0], min(raw_bias, self.bias_clamp[1]))
        else:
            bias_c = 0.0
            raw_bias = 0.0

        metadata = {
            'window_days_used': len(deltas),
            'window_days_requested': self.bias_window_days,
            'raw_bias_c': round(raw_bias, 2),
            'clamped': abs(raw_bias - bias_c) > 0.01,
            'clamp_min_c': self.bias_clamp[0],
            'clamp_max_c': self.bias_clamp[1],
        }

        logger.debug(
            f"Bias computed: {bias_c}°C from {len(deltas)} sensor days "
            f"(raw={raw_bias:.2f}°C, clamped={metadata['clamped']})"
        )

        return Decimal(str(round(bias_c, 2))), metadata

    def _project_forward(
        self,
        start_state: ActualDailyAssignmentState,
        start_date: date,
        horizon_days: int,
        computed_date: date,
        bias_c: Decimal,
        bias_metadata: Dict,
    ) -> List[LiveForwardProjection]:
        """
        Project growth forward from start state.

        Uses TGC calculator for growth, mortality calculator for population
        decay. Temperature = profile_temp + bias for each future day.

        Args:
            start_state: Starting ActualDailyAssignmentState
            start_date: Date of start state
            horizon_days: Number of days to project
            computed_date: Date this projection was computed
            bias_c: Temperature bias to apply
            bias_metadata: Metadata about bias computation

        Returns:
            List of LiveForwardProjection instances (not yet saved)
        """
        projections = []

        # Starting values
        current_weight = float(start_state.avg_weight_g)
        current_population = start_state.population
        current_day = start_state.day_number
        current_stage = start_state.lifecycle_stage

        # Profile info for provenance
        profile_id = self.temp_profile.profile_id if self.temp_profile else None
        profile_name = self.temp_profile.name if self.temp_profile else ''

        # Get TGC value (may vary by stage later)
        tgc_value = float(self.scenario.tgc_model.tgc_value)

        today = timezone.now().date()

        for day_offset in range(1, horizon_days + 1):
            proj_date = start_date + timedelta(days=day_offset)
            day_number = current_day + day_offset

            # Skip past dates (shouldn't happen, but safety check)
            if proj_date <= today:
                continue

            # Determine lifecycle stage based on elapsed time (time-based transitions)
            # This ensures live projections advance through stages like scenario projections
            new_stage = self._determine_lifecycle_stage(day_number)
            if new_stage and new_stage != current_stage:
                logger.debug(
                    f"Stage transition at day {day_number}: "
                    f"{current_stage.name if current_stage else 'None'} -> {new_stage.name}"
                )
                current_stage = new_stage

            # Get temperature for this day (profile + bias)
            profile_temp = self.tgc_calculator._get_temperature_for_day(
                day_number
            )
            temp_used = profile_temp + float(bias_c)

            # Calculate growth using TGC
            growth_result = self.tgc_calculator.calculate_daily_growth(
                current_weight=current_weight,
                temperature=temp_used,
                lifecycle_stage=current_stage.name if current_stage else None,
            )
            new_weight = growth_result['new_weight_g']

            # Calculate mortality
            stage_name = current_stage.name if current_stage else None
            daily_mortality_rate = \
                self.mortality_calculator.get_mortality_rate_for_stage(
                    stage=stage_name,
                    frequency='daily'
                )
            mortality = int(round(current_population * daily_mortality_rate))
            new_population = max(0, current_population - mortality)

            # Calculate biomass
            new_biomass = (new_weight * new_population) / 1000

            # Create projection row
            projection = LiveForwardProjection(
                computed_date=computed_date,
                assignment=self.assignment,
                batch=self.batch,
                container=self.container,
                projection_date=proj_date,
                day_number=day_number,
                projected_weight_g=Decimal(str(round(new_weight, 2))),
                projected_population=new_population,
                projected_biomass_kg=Decimal(str(round(new_biomass, 2))),
                temperature_used_c=Decimal(str(round(temp_used, 2))),
                tgc_value_used=Decimal(str(round(tgc_value, 4))),
                temp_profile_id=profile_id,
                temp_profile_name=profile_name,
                temp_bias_c=bias_c,
                temp_bias_window_days=bias_metadata.get(
                    'window_days_used', self.bias_window_days
                ),
                temp_bias_clamp_min_c=Decimal(str(self.bias_clamp[0])),
                temp_bias_clamp_max_c=Decimal(str(self.bias_clamp[1])),
            )
            projections.append(projection)

            # Update for next iteration
            current_weight = new_weight
            current_population = new_population

        return projections

    def _update_forecast_summary(
        self,
        latest_state: ActualDailyAssignmentState,
        projections: List[LiveForwardProjection],
        computed_date: date,
        bias_c: Decimal,
        bias_metadata: Dict,
    ) -> None:
        """
        Update or create ContainerForecastSummary for this assignment.

        Finds crossing dates for harvest/transfer thresholds and updates
        planning flags based on PlannedActivity existence.

        Args:
            latest_state: Starting actual state
            projections: Computed projections
            computed_date: Date of projection run
            bias_c: Temperature bias used
            bias_metadata: Bias metadata
        """
        # Get thresholds from scenario (if defined)
        harvest_threshold = self._get_harvest_threshold()
        transfer_threshold = self._get_transfer_threshold()

        # Find crossing dates
        harvest_crossing = None
        transfer_crossing = None

        for proj in projections:
            # Check harvest threshold
            if harvest_threshold and not harvest_crossing:
                if float(proj.projected_weight_g) >= harvest_threshold:
                    harvest_crossing = proj

            # Check transfer threshold
            if transfer_threshold and not transfer_crossing:
                if float(proj.projected_weight_g) >= transfer_threshold:
                    transfer_crossing = proj

            # Stop if both found
            if harvest_crossing and transfer_crossing:
                break

        # Check for planned activities
        has_planned_harvest = PlannedActivity.objects.filter(
            batch=self.batch,
            activity_type='HARVEST',
            status__in=['PENDING', 'IN_PROGRESS'],
        ).exists()

        has_planned_transfer = PlannedActivity.objects.filter(
            batch=self.batch,
            activity_type='TRANSFER',
            status__in=['PENDING', 'IN_PROGRESS'],
        ).exists()

        # Determine if needs attention (approaching threshold without plan)
        needs_attention = False
        if harvest_crossing and not has_planned_harvest:
            days_to = (
                harvest_crossing.projection_date - computed_date
            ).days
            if days_to <= self.attention_threshold_days:
                needs_attention = True
        if transfer_crossing and not has_planned_transfer:
            days_to = (
                transfer_crossing.projection_date - computed_date
            ).days
            if days_to <= self.attention_threshold_days:
                needs_attention = True

        # Get original harvest date from scenario (if available)
        original_harvest_date = self._get_original_harvest_date()
        harvest_variance = None
        if harvest_crossing and original_harvest_date:
            harvest_variance = (
                harvest_crossing.projection_date - original_harvest_date
            ).days

        # Compute overall confidence from latest state
        confidence_scores = latest_state.confidence_scores or {}
        overall_confidence = min(confidence_scores.values()) \
            if confidence_scores else 0.0

        # Update or create summary
        ContainerForecastSummary.objects.update_or_create(
            assignment=self.assignment,
            defaults={
                # Current state snapshot
                'current_weight_g': latest_state.avg_weight_g,
                'current_population': latest_state.population,
                'current_biomass_kg': latest_state.biomass_kg,
                'state_date': latest_state.date,
                'state_day_number': latest_state.day_number,
                'state_confidence': Decimal(str(round(overall_confidence, 2))),

                # Harvest projection
                'projected_harvest_date': (
                    harvest_crossing.projection_date if harvest_crossing
                    else None
                ),
                'projected_harvest_weight_g': (
                    harvest_crossing.projected_weight_g if harvest_crossing
                    else None
                ),
                'days_to_harvest': (
                    (harvest_crossing.projection_date - computed_date).days
                    if harvest_crossing else None
                ),
                'harvest_threshold_g': (
                    Decimal(str(harvest_threshold)) if harvest_threshold
                    else None
                ),

                # Transfer projection
                'projected_transfer_date': (
                    transfer_crossing.projection_date if transfer_crossing
                    else None
                ),
                'projected_transfer_weight_g': (
                    transfer_crossing.projected_weight_g if transfer_crossing
                    else None
                ),
                'days_to_transfer': (
                    (transfer_crossing.projection_date - computed_date).days
                    if transfer_crossing else None
                ),
                'transfer_threshold_g': (
                    Decimal(str(transfer_threshold)) if transfer_threshold
                    else None
                ),

                # Variance
                'original_harvest_date': original_harvest_date,
                'harvest_variance_days': harvest_variance,

                # Planning flags
                'has_planned_harvest': has_planned_harvest,
                'has_planned_transfer': has_planned_transfer,
                'needs_planning_attention': needs_attention,

                # Provenance
                'temp_profile_name': (
                    self.temp_profile.name if self.temp_profile else ''
                ),
                'temp_bias_c': bias_c,
                'temp_bias_window_days': bias_metadata.get(
                    'window_days_used', self.bias_window_days
                ),
                'computed_date': computed_date,
            }
        )

    def _get_harvest_threshold(self) -> Optional[float]:
        """Get harvest weight threshold from scenario."""
        # Try biological constraints first
        if self.scenario.biological_constraints:
            try:
                from apps.scenario.models import StageConstraint
                adult_constraint = StageConstraint.objects.get(
                    constraint_set=self.scenario.biological_constraints,
                    lifecycle_stage__in=['Adult', 'Harvest', 'adult', 'harvest']
                )
                if adult_constraint.max_weight_g:
                    return float(adult_constraint.max_weight_g)
            except StageConstraint.DoesNotExist:
                pass

        # Default harvest threshold (5kg is common for Atlantic Salmon)
        return 5000.0

    def _get_transfer_threshold(self) -> Optional[float]:
        """Get sea-transfer weight threshold from scenario."""
        # Try biological constraints first
        if self.scenario.biological_constraints:
            try:
                from apps.scenario.models import StageConstraint
                smolt_constraint = StageConstraint.objects.get(
                    constraint_set=self.scenario.biological_constraints,
                    lifecycle_stage__in=['Smolt', 'smolt']
                )
                if smolt_constraint.max_weight_g:
                    return float(smolt_constraint.max_weight_g)
            except StageConstraint.DoesNotExist:
                pass

        # Default smolt transfer weight (80-120g typical)
        return 100.0

    def _get_original_harvest_date(self) -> Optional[date]:
        """Get original harvest date from scenario projection."""
        if not self.batch.pinned_projection_run:
            return None

        try:
            from apps.scenario.models import ScenarioProjection
            # Find the day when projected weight first crosses harvest threshold
            harvest_threshold = self._get_harvest_threshold()
            if harvest_threshold is None:
                return None
                
            harvest_projection = ScenarioProjection.objects.filter(
                projection_run=self.batch.pinned_projection_run,
                average_weight__gte=float(harvest_threshold)
            ).order_by('day_number').first()

            if harvest_projection:
                return harvest_projection.projection_date
        except Exception as e:
            logger.warning(f"Error getting original harvest date: {e}")

        return None

