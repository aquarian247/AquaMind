"""
Growth Assimilation Service - Issue #112 Phase 3

This module implements the core computation engine for batch growth assimilation,
computing daily actual states by assimilating real measurements with TGC models.

Architecture:
- Reuses existing TGCCalculator and MortalityCalculator from scenario app
- Detects anchors (growth samples, measured transfers, vaccinations)
- Computes TGC-based growth between anchors
- Tracks provenance (sources) and confidence scores
- Handles stage transitions based on biological constraints

Production-grade considerations:
- Comprehensive error handling
- Logging for debugging
- Transaction safety
- Performance optimization (bulk operations)
- Edge case handling (missing data, gaps, etc.)
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.batch.models import (
    BatchContainerAssignment,
    ActualDailyAssignmentState,
    GrowthSample,
    TransferAction,
    MortalityEvent
)
from apps.environmental.models import EnvironmentalReading
from apps.inventory.models import FeedingEvent
from apps.health.models import Treatment
from apps.scenario.models import Scenario, TGCModel, MortalityModel, BiologicalConstraints
from apps.scenario.services.calculations.tgc_calculator import TGCCalculator
from apps.scenario.services.calculations.mortality_calculator import MortalityCalculator

logger = logging.getLogger(__name__)


class GrowthAssimilationEngine:
    """
    Core engine for computing daily actual states by assimilating measurements.
    
    This engine:
    1. Detects anchor points (growth samples, measured transfers, vaccinations)
    2. Segments date range by anchors
    3. For each segment: compute daily states using TGC with measured temperature
    4. Tracks data sources and confidence scores for transparency
    5. Handles stage transitions based on weight thresholds
    
    Usage:
        engine = GrowthAssimilationEngine(assignment)
        engine.recompute_range(start_date, end_date)
    """
    
    def __init__(self, assignment: BatchContainerAssignment):
        """
        Initialize engine for a specific batch-container assignment.
        
        Args:
            assignment: The BatchContainerAssignment to compute states for
        """
        self.assignment = assignment
        self.batch = assignment.batch
        self.container = assignment.container
        
        # Get pinned scenario or default
        self.scenario = self._get_scenario()
        
        # Initialize calculators
        self.tgc_calculator = TGCCalculator(self.scenario.tgc_model)
        self.mortality_calculator = MortalityCalculator(self.scenario.mortality_model)
        self.bio_constraints = self.scenario.biological_constraints
        
        logger.info(
            f"Initialized GrowthAssimilationEngine for assignment {assignment.id} "
            f"(Batch: {self.batch.batch_number}, Container: {self.container.name})"
        )
    
    def _get_scenario(self) -> Scenario:
        """
        Get the scenario to use for TGC/mortality models.
        
        Priority:
        1. Batch pinned_projection_run.scenario (NEW)
        2. Batch pinned_scenario (DEPRECATED, for backward compatibility)
        3. Batch's first scenario (if any)
        4. Raise error (scenario is required)
        
        Returns:
            Scenario to use for calculations
            
        Raises:
            ValueError: If no scenario is available
        """
        # NEW: Try pinned projection run first
        if self.batch.pinned_projection_run:
            return self.batch.pinned_projection_run.scenario
        
        # DEPRECATED: Try old pinned scenario (for backward compatibility)
        if self.batch.pinned_scenario:
            logger.warning(
                f"Batch {self.batch.batch_number} using deprecated pinned_scenario. "
                f"Consider pinning a ProjectionRun instead."
            )
            return self.batch.pinned_scenario
        
        # Try first scenario for this batch
        scenario = self.batch.scenarios.first()
        if scenario:
            logger.info(f"Using first scenario for batch {self.batch.batch_number}: {scenario.name}")
            return scenario
        
        raise ValueError(
            f"No scenario available for batch {self.batch.batch_number}. "
            f"Pin a projection run or assign a scenario to this batch."
        )
    
    def recompute_range(
        self, 
        start_date: date, 
        end_date: Optional[date] = None,
        force: bool = False
    ) -> Dict[str, any]:
        """
        Recompute daily states for a date range.
        
        This is the main entry point for the engine. It:
        1. Validates inputs
        2. Detects anchors in the range
        3. Segments by anchors
        4. Computes each segment
        5. Saves to database
        
        Args:
            start_date: Start of range to recompute
            end_date: End of range (None = today)
            force: If True, recompute even if data exists
            
        Returns:
            Dict with computation stats (rows_created, rows_updated, anchors_found)
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if end_date is None:
            end_date = timezone.now().date()
        
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")
        
        if start_date < self.batch.start_date:
            logger.warning(
                f"start_date ({start_date}) is before batch start ({self.batch.start_date}). "
                f"Adjusting to batch start date."
            )
            start_date = self.batch.start_date
        
        # CRITICAL: Don't compute states before assignment existed
        if start_date < self.assignment.assignment_date:
            logger.warning(
                f"start_date ({start_date}) is before assignment start ({self.assignment.assignment_date}). "
                f"Adjusting to assignment start date."
            )
            start_date = self.assignment.assignment_date
            
            # Check if adjusted range is still valid
            if start_date > end_date:
                logger.info(
                    f"Assignment {self.assignment.id} has no valid range after adjusting for assignment_date "
                    f"(adjusted start={start_date}, end={end_date}). Skipping."
                )
                return {
                    'rows_created': 0,
                    'rows_updated': 0,
                    'anchors_found': 0,
                    'errors': [],
                    'skipped': True
                }
        
        # Also validate end_date - STOP BEFORE DEPARTURE (not on departure day)
        if self.assignment.departure_date and end_date >= self.assignment.departure_date:
            # Stop computing the day BEFORE departure to avoid double-counting
            # On departure day, the NEW assignment takes over
            adjusted_end = self.assignment.departure_date - timedelta(days=1)
            
            # Edge case: If start_date >= adjusted_end, assignment has no valid range
            if start_date > adjusted_end:
                logger.info(
                    f"Assignment {self.assignment.id} has no valid date range "
                    f"(start={start_date}, departure={self.assignment.departure_date}). Skipping."
                )
                return {
                    'rows_created': 0,
                    'rows_updated': 0,
                    'anchors_found': 0,
                    'errors': [],
                    'skipped': True
                }
            
            logger.warning(
                f"end_date ({end_date}) includes/exceeds assignment departure ({self.assignment.departure_date}). "
                f"Adjusting to day before departure ({adjusted_end}) to avoid double-counting."
            )
            end_date = adjusted_end
        
        logger.info(f"Recomputing range [{start_date}, {end_date}] for assignment {self.assignment.id}")
        
        # Detect anchors in range
        anchors = self._detect_anchors(start_date, end_date)
        logger.info(f"Detected {len(anchors)} anchors in range")
        
        # Get initial state (day before start_date)
        initial_state = self._get_initial_state(start_date)
        
        # Compute segments
        stats = {
            'rows_created': 0,
            'rows_updated': 0,
            'anchors_found': len(anchors),
            'errors': []
        }
        
        current_date = start_date
        prev_weight = initial_state['weight']
        prev_population = initial_state['population']
        prev_biomass = initial_state['biomass']
        current_stage = initial_state['stage']
        
        with transaction.atomic():
            while current_date <= end_date:
                try:
                    # Compute state for this date
                    state_data = self._compute_daily_state(
                        current_date=current_date,
                        prev_weight=prev_weight,
                        prev_population=prev_population,
                        prev_biomass=prev_biomass,
                        current_stage=current_stage,
                        anchors=anchors
                    )
                    
                    # Save to database (upsert)
                    daily_state, created = ActualDailyAssignmentState.objects.update_or_create(
                        assignment=self.assignment,
                        date=current_date,
                        defaults=state_data
                    )
                    
                    if created:
                        stats['rows_created'] += 1
                    else:
                        stats['rows_updated'] += 1
                    
                    # Update for next iteration
                    prev_weight = state_data['avg_weight_g']
                    prev_population = state_data['population']
                    prev_biomass = state_data['biomass_kg']
                    current_stage = state_data['lifecycle_stage']
                    
                except Exception as e:
                    logger.error(f"Error computing state for {current_date}: {e}")
                    stats['errors'].append({
                        'date': current_date,
                        'error': str(e)
                    })
                
                current_date += timedelta(days=1)
        
        logger.info(
            f"Recompute complete: {stats['rows_created']} created, "
            f"{stats['rows_updated']} updated, {len(stats['errors'])} errors"
        )
        
        return stats
    
    def _detect_anchors(self, start_date: date, end_date: date) -> Dict[date, Dict]:
        """
        Detect all anchor points in the date range.
        
        Anchor precedence (highest to lowest):
        1. Growth samples (measured weights)
        2. Transfers with measured weights
        3. Vaccinations/treatments with weighing
        4. Manual admin anchors (future: separate model)
        
        Args:
            start_date: Start of range
            end_date: End of range
            
        Returns:
            Dict mapping date -> anchor data {type, weight, confidence, source_obj}
        """
        anchors = {}
        
        # 1. Growth samples (highest priority)
        samples = GrowthSample.objects.filter(
            assignment=self.assignment,
            sample_date__gte=start_date,
            sample_date__lte=end_date
        ).select_related('assignment')
        
        for sample in samples:
            if sample.avg_weight_g:
                anchors[sample.sample_date] = {
                    'type': 'growth_sample',
                    'weight': float(sample.avg_weight_g),
                    'confidence': 1.0,
                    'source_obj': sample,
                    'priority': 1
                }
        
        # 2. Transfers with measured weights
        # Note: Using actual_execution_date (actual field name) instead of execution_date (pseudocode)
        transfers = TransferAction.objects.filter(
            source_assignment=self.assignment,
            actual_execution_date__gte=start_date,
            actual_execution_date__lte=end_date,
            status='COMPLETED',
            measured_avg_weight_g__isnull=False
        ).select_related('workflow')
        
        for transfer in transfers:
            transfer_date = transfer.actual_execution_date
            # Only override if no growth sample on same date
            if transfer_date not in anchors or anchors[transfer_date]['priority'] > 2:
                # Adjust weight based on selection_method
                measured_weight = float(transfer.measured_avg_weight_g)
                adjusted_weight = self._adjust_for_selection_bias(
                    measured_weight, 
                    transfer.selection_method
                )
                
                anchors[transfer_date] = {
                    'type': 'transfer',
                    'weight': adjusted_weight,
                    'confidence': 0.95,  # Slightly lower than growth sample
                    'source_obj': transfer,
                    'priority': 2,
                    'selection_method': transfer.selection_method
                }
        
        # 3. Treatments with weighing
        treatments = Treatment.objects.filter(
            batch_assignment=self.assignment,
            treatment_date__date__gte=start_date,
            treatment_date__date__lte=end_date,
            includes_weighing=True
        ).select_related('sampling_event')
        
        for treatment in treatments:
            treatment_date = treatment.treatment_date.date()
            # Only use if no higher-priority anchor exists
            if treatment_date not in anchors or anchors[treatment_date]['priority'] > 3:
                # Try to get weight from sampling event
                if treatment.sampling_event:
                    # Get average weight from individual fish observations
                    from apps.health.models import IndividualFishObservation
                    observations = IndividualFishObservation.objects.filter(
                        sampling_event=treatment.sampling_event,
                        weight_g__isnull=False
                    )
                    if observations.exists():
                        from django.db.models import Avg
                        avg_weight = observations.aggregate(Avg('weight_g'))['weight_g__avg']
                        if avg_weight:
                            anchors[treatment_date] = {
                                'type': 'vaccination',
                                'weight': float(avg_weight),
                                'confidence': 0.90,
                                'source_obj': treatment,
                                'priority': 3
                            }
        
        logger.debug(f"Detected {len(anchors)} anchors in range [{start_date}, {end_date}]")
        return anchors
    
    def _adjust_for_selection_bias(
        self, 
        measured_weight: float, 
        selection_method: str
    ) -> float:
        """
        Adjust measured weight for selection bias.
        
        When transferring fish, operators may systematically select:
        - LARGEST: Top performers (positive bias)
        - SMALLEST: Runts/cullable fish (negative bias)  
        - AVERAGE: Representative sample (no bias)
        
        Args:
            measured_weight: Measured average weight
            selection_method: One of AVERAGE, LARGEST, SMALLEST
            
        Returns:
            Adjusted weight estimate for population average
        """
        if selection_method == 'LARGEST':
            # Measured weight likely 10-15% above population average
            return measured_weight * 0.88  # Adjust down 12%
        elif selection_method == 'SMALLEST':
            # Measured weight likely 10-15% below population average
            return measured_weight * 1.12  # Adjust up 12%
        else:  # AVERAGE or unknown
            return measured_weight
    
    def _get_initial_state(self, start_date: date) -> Dict:
        """
        Get initial state for the computation (day before start_date).
        
        Per pseudocode lines 150-161:
        Priority:
        1. Previous day's computed state (if exists)
        2. Bootstrap from assignment/scenario initial values
        
        Args:
            start_date: Date to get initial state for
            
        Returns:
            Dict with weight, population, biomass, stage, date
        """
        prev_date = start_date - timedelta(days=1)
        
        # Try to get previous computed state (already computed)
        prev_state = ActualDailyAssignmentState.objects.filter(
            assignment=self.assignment,
            date__lt=start_date
        ).order_by('-date').first()
        
        if prev_state:
            return {
                'weight': float(prev_state.avg_weight_g),
                'population': prev_state.population,
                'biomass': float(prev_state.biomass_kg),
                'stage': prev_state.lifecycle_stage,
                'date': prev_state.date
            }
        
        # Bootstrap initial state
        # Get weight with proper fallback hierarchy to prevent stage transition spikes
        # IMPORTANT: Check transfers FIRST - Event Engine sets wrong avg_weight_g during transfers!
        initial_weight = None
        
        # Priority 1: ALWAYS check transfers first!
        # The Event Engine incorrectly sets dest assignment avg_weight_g to stage min (~3000g for Adult)
        # but actual fish weight should come from source assignment (~500g from Post-Smolt)
        transfer_in = TransferAction.objects.filter(
            dest_assignment=self.assignment,
            status='COMPLETED'
        ).select_related('source_assignment').first()
        
        if transfer_in:
            # Try measured weight from transfer (most accurate)
            if transfer_in.measured_avg_weight_g:
                initial_weight = float(transfer_in.measured_avg_weight_g)
            # Try last computed state from source (second best)
            elif transfer_in.source_assignment:
                last_state = ActualDailyAssignmentState.objects.filter(
                    assignment=transfer_in.source_assignment
                ).order_by('-date').first()
                if last_state:
                    initial_weight = float(last_state.avg_weight_g)
            # Try source assignment's weight (fallback)
            if not initial_weight and transfer_in.source_assignment and transfer_in.source_assignment.avg_weight_g:
                initial_weight = float(transfer_in.source_assignment.avg_weight_g)
        
        # Priority 2: Assignment has explicit weight (only for non-transfers)
        if not initial_weight and self.assignment.avg_weight_g:
            initial_weight = float(self.assignment.avg_weight_g)
        
        # Priority 3: Stage constraint min weight
        if not initial_weight and self.bio_constraints:
            try:
                from apps.scenario.models import StageConstraint
                stage_constraint = StageConstraint.objects.get(
                    constraint_set=self.bio_constraints,
                    lifecycle_stage=self.assignment.lifecycle_stage.name
                )
                initial_weight = float(stage_constraint.min_weight_g)
            except (StageConstraint.DoesNotExist, Exception):
                pass
        
        # Priority 4: Scenario's initial_weight
        if not initial_weight and self.scenario.initial_weight:
            initial_weight = float(self.scenario.initial_weight)
        
        # Priority 5: Lifecycle stage expected weight
        if not initial_weight:
            if hasattr(self.assignment.lifecycle_stage, 'expected_weight_min_g'):
                if self.assignment.lifecycle_stage.expected_weight_min_g:
                    initial_weight = float(self.assignment.lifecycle_stage.expected_weight_min_g)
            else:
                initial_weight = 1.0  # Ultra-safe fallback (1g)
        
        # Get population
        initial_population = self.assignment.population_count
        
        # Fix for Issue #112: Check if this assignment is a transfer destination
        # If fish were transferred IN on the assignment date, the population_count
        # already includes them (from event engine pre-population), so we need to
        # start from 0 to avoid double-counting when _get_placements() adds them daily.
        first_day_transfers = TransferAction.objects.filter(
            dest_assignment=self.assignment,
            actual_execution_date=self.assignment.assignment_date,
            status='COMPLETED'
        ).exists()
        
        if first_day_transfers:
            # Transfer destination - start from 0, placements will add fish daily
            logger.info(
                f"Assignment {self.assignment.id} is transfer destination on {self.assignment.assignment_date}, "
                f"starting from 0 population (was {initial_population}) to avoid double-counting"
            )
            initial_population = 0
        
        # Calculate biomass
        initial_biomass = (initial_population * initial_weight) / 1000
        
        return {
            'weight': initial_weight,
            'population': initial_population,
            'biomass': initial_biomass,
            'stage': self.assignment.lifecycle_stage,
            'date': self.batch.start_date - timedelta(days=1)
        }
    
    def _compute_daily_state(
        self,
        current_date: date,
        prev_weight: float,
        prev_population: int,
        prev_biomass: float,
        current_stage,
        anchors: Dict[date, Dict]
    ) -> Dict:
        """
        Compute daily state for a single date.
        
        This is the core computation logic that:
        1. Checks for anchor (resets weight if found)
        2. Retrieves temperature (measured > interpolated > profile)
        3. Retrieves mortality (actual > model)
        4. Retrieves feed (actual > none)
        5. Calculates growth (TGC formula)
        6. Updates population (subtract mortality)
        7. Calculates biomass
        8. Tracks sources and confidence
        
        Args:
            current_date: Date to compute
            prev_weight: Previous day's weight
            prev_population: Previous day's population
            prev_biomass: Previous day's biomass
            current_stage: Current lifecycle stage
            anchors: Dict of detected anchors
            
        Returns:
            Dict with all fields for ActualDailyAssignmentState
        """
        sources = {}
        confidence = {}
        anchor_type = None
        
        # Step 1: Check for anchor
        if current_date in anchors:
            anchor = anchors[current_date]
            anchor_type = anchor['type']
            measured_weight = anchor['weight']
            sources['weight'] = 'measured'
            confidence['weight'] = anchor['confidence']
        else:
            measured_weight = None
        
        # Step 2: Get temperature
        temp_c, temp_source, temp_confidence = self._get_temperature(current_date)
        sources['temp'] = temp_source
        confidence['temp'] = temp_confidence
        
        # Step 3: Get mortality
        mortality_count, mort_source, mort_confidence = self._get_mortality(
            current_date, 
            prev_population,
            current_stage
        )
        sources['mortality'] = mort_source
        confidence['mortality'] = mort_confidence
        
        # Step 4: Get feed
        feed_kg, feed_source, feed_confidence = self._get_feed(current_date)
        sources['feed'] = feed_source
        confidence['feed'] = feed_confidence
        
        # Step 5: Get placements (transfers IN to this assignment)
        placements_in = self._get_placements(current_date)
        
        # Step 6: Calculate population (previous + placements - mortality)
        new_population = max(0, prev_population + placements_in - mortality_count)
        
        # Step 7: Calculate weight
        if measured_weight is not None:
            # Anchor point - use measured weight
            new_weight = measured_weight
        else:
            # TGC-based growth
            if temp_c is not None:
                growth_result = self.tgc_calculator.calculate_daily_growth(
                    current_weight=float(prev_weight),  # Ensure float for TGC calc
                    temperature=float(temp_c),  # Ensure float for TGC calc
                    lifecycle_stage=current_stage.name if current_stage else None
                )
                new_weight = growth_result['new_weight_g']
                sources['weight'] = 'tgc_computed'
                # Weight confidence degrades based on temp confidence
                confidence['weight'] = min(temp_confidence, 0.8)
            else:
                # No temperature - can't calculate growth, keep previous weight
                new_weight = prev_weight
                sources['weight'] = 'unchanged'
                confidence['weight'] = 0.3
        
        # Step 8: Calculate biomass
        new_biomass = (new_population * new_weight) / 1000  # Convert to kg
        
        # Step 9: Calculate observed FCR (if feed and growth occurred)
        observed_fcr = None
        biomass_gain = new_biomass - float(prev_biomass)  # Ensure float for calculation
        
        # Only calculate FCR if biomass gain is substantial (>1kg)
        # FCR is meaningless for tiny fish (egg/alevin stage with <0.01kg gain)
        MIN_BIOMASS_GAIN_FOR_FCR = 1.0  # kg
        
        if feed_kg > 0 and biomass_gain > MIN_BIOMASS_GAIN_FOR_FCR:
            observed_fcr = feed_kg / biomass_gain
            # Cap absurdly high FCR values (data quality issues)
            if observed_fcr > 10.0:
                logger.warning(
                    f"Unusually high FCR={observed_fcr:.2f} on {current_date} "
                    f"(feed={feed_kg}kg, gain={biomass_gain:.3f}kg) - capping at 10.0"
                )
                observed_fcr = 10.0
            sources['fcr'] = 'observed'
        elif biomass_gain > MIN_BIOMASS_GAIN_FOR_FCR:
            # Use model FCR
            # Note: Will need to access FCRModel - defer to refinement
            sources['fcr'] = 'model'
        
        # Step 10: Check for stage transition
        new_stage = self._determine_stage_transition(new_weight, current_stage)
        if new_stage != current_stage:
            logger.info(
                f"Stage transition on {current_date}: {current_stage.name} -> {new_stage.name} "
                f"at {new_weight}g"
            )
            current_stage = new_stage
        
        # Calculate day number
        day_number = (current_date - self.batch.start_date).days + 1
        
        # Build state data dict
        state_data = {
            'batch': self.batch,
            'container': self.container,
            'lifecycle_stage': current_stage,
            'date': current_date,
            'day_number': day_number,
            'avg_weight_g': Decimal(str(round(new_weight, 2))),
            'population': new_population,
            'biomass_kg': Decimal(str(round(new_biomass, 2))),
            'temp_c': Decimal(str(round(temp_c, 2))) if temp_c is not None else None,
            'mortality_count': mortality_count,
            'feed_kg': Decimal(str(round(feed_kg, 2))),
            'observed_fcr': Decimal(str(round(observed_fcr, 3))) if observed_fcr else None,
            'anchor_type': anchor_type,
            'sources': sources,
            'confidence_scores': confidence
        }
        
        # Integration hook: Evaluate Production Planner activity templates
        # This will be fully implemented in Phase 8
        # For now, log when conditions might trigger planned activities
        self._evaluate_planner_triggers(state_data)
        
        return state_data
    
    def _evaluate_planner_triggers(self, state_data: Dict) -> None:
        """
        Evaluate if this state should trigger Production Planner activities.
        
        This is an integration hook for Phase 8. Currently logs potential triggers.
        
        In Phase 8, this will:
        - Check ActivityTemplates with WEIGHT_THRESHOLD trigger type
        - Check ActivityTemplates with STAGE_TRANSITION trigger type  
        - Auto-generate PlannedActivities when conditions are met
        - Call planner API endpoint: POST /activity-templates/{id}/generate-for-batch/
        
        Args:
            state_data: Computed state data for the day
        """
        # Phase 3: Stub implementation with logging
        avg_weight = float(state_data['avg_weight_g'])
        lifecycle_stage = state_data['lifecycle_stage']
        
        # Log potential weight-based triggers
        # TODO Phase 8: Query ActivityTemplate.objects.filter(trigger_type='WEIGHT_THRESHOLD')
        logger.debug(
            f"Planner hook: weight={avg_weight}g, stage={lifecycle_stage.name} "
            f"(Phase 8: check for template triggers)"
        )
    
    def _get_temperature(self, date: date) -> Tuple[Optional[float], str, float]:
        """
        Get temperature for a date with fallback hierarchy.
        
        Priority:
        1. Measured: Daily average from EnvironmentalReading
        2. Interpolated: Linear interpolation between nearest measurements
        3. Profile: From scenario's temperature profile
        
        Args:
            date: Date to get temperature for
            
        Returns:
            Tuple of (temperature, source, confidence)
            source: 'measured', 'interpolated', 'profile', or 'none'
            confidence: 1.0 (measured) -> 0.7 (interpolated) -> 0.5 (profile) -> 0.0 (none)
        """
        # Try measured temperature
        from django.db.models import Avg
        temp_readings = EnvironmentalReading.objects.filter(
            container=self.container,
            reading_time__date=date,
            parameter__name='temperature'
        )
        
        if temp_readings.exists():
            avg_temp = temp_readings.aggregate(Avg('value'))['value__avg']
            if avg_temp:
                return float(avg_temp), 'measured', 1.0
        
        # Try interpolation (get nearest readings within 7 days)
        before_reading = EnvironmentalReading.objects.filter(
            container=self.container,
            reading_time__date__lt=date,
            reading_time__date__gte=date - timedelta(days=7),
            parameter__name='temperature'
        ).order_by('-reading_time__date').first()
        
        after_reading = EnvironmentalReading.objects.filter(
            container=self.container,
            reading_time__date__gt=date,
            reading_time__date__lte=date + timedelta(days=7),
            parameter__name='temperature'
        ).order_by('reading_time__date').first()
        
        if before_reading and after_reading:
            # Linear interpolation
            before_date = before_reading.reading_time.date()
            after_date = after_reading.reading_time.date()
            before_temp = float(before_reading.value)
            after_temp = float(after_reading.value)
            
            days_span = (after_date - before_date).days
            days_from_before = (date - before_date).days
            
            if days_span > 0:
                interpolated_temp = before_temp + (
                    (after_temp - before_temp) * days_from_before / days_span
                )
                # Confidence degrades with gap size
                gap_confidence = max(0.4, 0.9 - (days_span / 30))
                return interpolated_temp, 'interpolated', gap_confidence
        elif before_reading:
            # Use nearest before
            return float(before_reading.value), 'nearest_before', 0.6
        elif after_reading:
            # Use nearest after
            return float(after_reading.value), 'nearest_after', 0.6
        
        # Fall back to temperature profile
        day_number = (date - self.batch.start_date).days + 1
        try:
            profile_temp = self.tgc_calculator._get_temperature_for_day(day_number)
            return profile_temp, 'profile', 0.5
        except:
            # No profile data
            return None, 'none', 0.0
    
    def _get_mortality(
        self, 
        date: date, 
        current_population: int,
        current_stage
    ) -> Tuple[int, str, float]:
        """
        Get mortality count for a date.
        
        MortalityEvent now tracks at assignment level, enabling direct queries
        with full confidence (no proration needed).
        
        Priority:
        1. Actual: Recorded MortalityEvent (assignment-specific)
        2. Model: Stage-specific mortality rate from scenario
        
        Args:
            date: Date to get mortality for
            current_population: Current population for this assignment
            current_stage: Current lifecycle stage
            
        Returns:
            Tuple of (mortality_count, source, confidence)
        """
        # Try actual mortality events (assignment-specific)
        from django.db.models import Sum
        mortality_events = MortalityEvent.objects.filter(
            assignment=self.assignment,
            event_date=date
        )
        
        actual_count = mortality_events.aggregate(Sum('count'))['count__sum'] or 0
        if actual_count > 0:
            # Direct assignment query - full confidence!
            return actual_count, 'actual', 1.0
        
        # Use model
        stage_name = current_stage.name if current_stage else None
        daily_rate = self.mortality_calculator.get_mortality_rate_for_stage(
            stage=stage_name,
            frequency='daily'
        )
        
        # Calculate expected mortality
        model_mortality = int(round(current_population * daily_rate))
        return model_mortality, 'model', 0.4
    
    def _get_batch_population(self, date: date) -> int:
        """
        Get total batch population on a date (across all active assignments).
        
        Used for prorating batch-level mortality events to assignments.
        
        Args:
            date: Date to get population for
            
        Returns:
            Total batch population count
        """
        # Try to get from computed states
        states = ActualDailyAssignmentState.objects.filter(
            batch=self.batch,
            date=date
        )
        
        if states.exists():
            return sum(state.population for state in states)
        
        # Fall back to assignment population_count (not ideal but better than nothing)
        assignments = self.batch.batch_assignments.filter(is_active=True)
        return sum(a.population_count for a in assignments)
    
    def _get_feed(self, date: date) -> Tuple[float, str, float]:
        """
        Get feed amount for a date.
        
        Priority:
        1. Actual: Recorded FeedingEvent
        2. None: No feed recorded (confidence = 0)
        
        Args:
            date: Date to get feed for
            
        Returns:
            Tuple of (feed_kg, source, confidence)
        """
        from django.db.models import Sum
        
        # Query feeding events for this container on this date
        # Note: FeedingEvent uses 'feeding_date' not 'event_date'
        feeding_events = FeedingEvent.objects.filter(
            container=self.container,
            feeding_date=date
        )
        
        total_feed = feeding_events.aggregate(Sum('amount_kg'))['amount_kg__sum']
        
        if total_feed and total_feed > 0:
            return float(total_feed), 'actual', 1.0
        
        return 0.0, 'none', 0.0
    
    def _get_placements(self, date: date) -> int:
        """
        Get number of fish placed into this assignment on a date.
        
        This handles transfers IN to this assignment (where this assignment is the destination).
        Per the pseudocode: population = prev_population + placements_in - mortality
        
        Args:
            date: Date to check for placements
            
        Returns:
            Number of fish transferred INTO this assignment
        """
        # Find transfer actions where this assignment is the destination
        # and transfer was executed on this date
        transfers_in = TransferAction.objects.filter(
            dest_assignment=self.assignment,
            actual_execution_date=date,
            status='COMPLETED'
        )
        
        total_placements = sum(transfer.transferred_count for transfer in transfers_in)
        
        if total_placements > 0:
            logger.debug(f"Placements on {date}: {total_placements} fish transferred IN")
        
        return total_placements
    
    def _determine_stage_transition(self, current_weight: float, current_stage):
        """
        Determine if fish should transition to next lifecycle stage.
        
        Checks biological constraints to see if weight exceeds max for current stage.
        Uses scenario's StageConstraint if available, falls back to LifeCycleStage defaults.
        
        Args:
            current_weight: Current average weight in grams
            current_stage: Current LifeCycleStage
            
        Returns:
            New LifeCycleStage (may be same as current if no transition)
        """
        if not current_stage:
            return current_stage
        
        max_weight = None
        
        # Try to get max weight from biological constraints
        if self.bio_constraints:
            try:
                from apps.scenario.models import StageConstraint
                stage_constraint = StageConstraint.objects.get(
                    constraint_set=self.bio_constraints,
                    lifecycle_stage=current_stage.name
                )
                max_weight = float(stage_constraint.max_weight_g)
            except (StageConstraint.DoesNotExist, Exception) as e:
                logger.debug(f"No stage constraint found for {current_stage.name}: {e}")
        
        # Fall back to LifeCycleStage's expected_weight_max_g
        if max_weight is None and hasattr(current_stage, 'expected_weight_max_g'):
            if current_stage.expected_weight_max_g:
                max_weight = float(current_stage.expected_weight_max_g)
        
        # Check if transition needed
        if max_weight and current_weight >= max_weight:
            next_stage = self._get_next_stage(current_stage)
            if next_stage and next_stage != current_stage:
                logger.info(
                    f"Stage transition triggered: {current_stage.name} -> {next_stage.name} "
                    f"(weight {current_weight}g >= max {max_weight}g)"
                )
                return next_stage
        
        return current_stage
    
    def _get_next_stage(self, current_stage):
        """
        Get the next lifecycle stage in sequence.
        
        Args:
            current_stage: Current LifeCycleStage
            
        Returns:
            Next LifeCycleStage or None if no next stage
        """
        from apps.batch.models import LifeCycleStage
        
        try:
            # Find next stage by order
            next_stage = LifeCycleStage.objects.filter(
                species=current_stage.species,
                order__gt=current_stage.order
            ).order_by('order').first()
            
            return next_stage if next_stage else current_stage
        except Exception as e:
            logger.warning(f"Error getting next stage: {e}")
            return current_stage


def recompute_batch_assignments(
    batch_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    assignment_ids: Optional[List[int]] = None
) -> Dict[str, any]:
    """
    Convenience function to recompute all assignments for a batch.
    
    Args:
        batch_id: Batch to recompute
        start_date: Start of recompute range
        end_date: End of range (None = today)
        assignment_ids: Optional list of specific assignment IDs (None = all active)
        
    Returns:
        Dict with overall stats
    """
    from apps.batch.models import Batch
    from django.utils import timezone
    
    batch = Batch.objects.get(id=batch_id)
    
    # Set default end_date if not provided
    if end_date is None:
        end_date = timezone.now().date()
    
    if assignment_ids:
        assignments = BatchContainerAssignment.objects.filter(
            id__in=assignment_ids,
            batch=batch
        )
    else:
        # Get ALL assignments that overlap with the date range (active or historical)
        # An assignment is relevant if:
        # - It started before or during the range (assignment_date <= end_date)
        # - It didn't end before the range (departure_date is NULL or >= start_date)
        assignments = batch.batch_assignments.filter(
            assignment_date__lte=end_date
        ).filter(
            Q(departure_date__isnull=True) | Q(departure_date__gte=start_date)
        )
    
    overall_stats = {
        'batch_id': batch_id,
        'assignments_processed': 0,
        'total_rows_created': 0,
        'total_rows_updated': 0,
        'total_errors': 0,
        'assignment_results': []
    }
    
    for assignment in assignments:
        try:
            engine = GrowthAssimilationEngine(assignment)
            result = engine.recompute_range(start_date, end_date)
            
            # Only count as processed if not skipped
            if not result.get('skipped', False):
                overall_stats['assignments_processed'] += 1
                overall_stats['total_rows_created'] += result['rows_created']
                overall_stats['total_rows_updated'] += result['rows_updated']
                overall_stats['total_errors'] += len(result['errors'])
            
            overall_stats['assignment_results'].append({
                'assignment_id': assignment.id,
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Error processing assignment {assignment.id}: {e}")
            overall_stats['total_errors'] += 1
            overall_stats['assignment_results'].append({
                'assignment_id': assignment.id,
                'error': str(e)
            })
    
    logger.info(
        f"Batch recompute complete: {overall_stats['assignments_processed']} assignments, "
        f"{overall_stats['total_rows_created']} created, {overall_stats['total_rows_updated']} updated"
    )
    
    return overall_stats

