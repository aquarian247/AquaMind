"""
Main projection engine for scenario planning.

Orchestrates TGC, FCR, and mortality calculations to generate
comprehensive daily projections for scenarios.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from ...models import (
    Scenario, ScenarioProjection, ScenarioModelChange,
    TGCModel, FCRModel, MortalityModel
)
# We'll use the batch LifeCycleStage for now, but could switch to scenario-specific later
from apps.batch.models import LifeCycleStage
from .tgc_calculator import TGCCalculator
from .fcr_calculator import FCRCalculator
from .mortality_calculator import MortalityCalculator


class ProjectionEngine:
    """
    Main engine for running scenario projections.
    
    Coordinates all biological calculations and handles model changes
    during the projection period.
    """
    
    def __init__(self, scenario: Scenario):
        """
        Initialize engine with a scenario.
        
        Args:
            scenario: Scenario to project
        """
        self.scenario = scenario
        self.errors = []
        self.warnings = []
        
        # Validate required fields first (before accessing related objects)
        self._validate_scenario()
        
        # Only proceed with initialization if validation passed
        if not self.errors:
            # Initialize calculators
            self._initialize_calculators()
            
            # Load model changes
            self._load_model_changes()
            
            # Load lifecycle stages
            self._load_lifecycle_stages()
    
    def _validate_scenario(self):
        """Validate scenario has all required fields for projection."""
        if self.scenario.initial_weight is None:
            self.errors.append(
                "Scenario requires initial_weight to run projections. "
                "Please provide the starting weight in grams (e.g., 50.0 for "
                "smolt stage, 0.1 for egg stage)."
            )
        elif self.scenario.initial_weight <= 0:
            self.errors.append(
                f"initial_weight must be greater than 0 "
                f"(got {self.scenario.initial_weight}g)"
            )
    
    def _initialize_calculators(self):
        """Initialize the biological calculators."""
        self.tgc_calculator = TGCCalculator(self.scenario.tgc_model)
        self.fcr_calculator = FCRCalculator(self.scenario.fcr_model)
        self.mortality_calculator = MortalityCalculator(self.scenario.mortality_model)
        
        # Validate all models
        for calculator, model_name in [
            (self.tgc_calculator, 'TGC'),
            (self.fcr_calculator, 'FCR'),
            (self.mortality_calculator, 'Mortality')
        ]:
            is_valid, errors = calculator.validate_parameters()
            if not is_valid:
                self.errors.extend([f"{model_name}: {e}" for e in errors])
    
    def _load_model_changes(self):
        """Load scheduled model changes."""
        self.model_changes = {}
        
        for change in self.scenario.model_changes.select_related(
            'new_tgc_model', 'new_fcr_model', 'new_mortality_model'
        ):
            change_date = self.scenario.start_date + timedelta(days=change.change_day - 1)
            self.model_changes[change_date] = change
    
    def _load_lifecycle_stages(self):
        """Load lifecycle stages for stage transitions."""
        self.lifecycle_stages = list(
            # Use the correct weight fields defined on LifeCycleStage
            LifeCycleStage.objects.order_by('expected_weight_min_g')
        )
    
    def _determine_lifecycle_stage(self, weight: float) -> Optional[LifeCycleStage]:
        """
        Determine lifecycle stage based on weight.
        
        Args:
            weight: Current average weight in grams
            
        Returns:
            Appropriate lifecycle stage or None
        """
        for stage in self.lifecycle_stages:
            if stage.expected_weight_min_g and stage.expected_weight_max_g:
                if float(stage.expected_weight_min_g) <= weight <= float(stage.expected_weight_max_g):
                    return stage
            elif stage.expected_weight_min_g and weight >= float(stage.expected_weight_min_g):
                # Last stage with no end weight
                return stage
        
        # Default to first stage if no match
        return self.lifecycle_stages[0] if self.lifecycle_stages else None
    
    def _stage_has_external_feeding(self, stage: Optional[LifeCycleStage]) -> bool:
        """
        Check if a lifecycle stage involves external feeding.
        
        Egg and Alevin stages don't have external feeding, so no weight gain
        or feed consumption should be calculated.
        
        Args:
            stage: Current lifecycle stage
            
        Returns:
            True if stage has external feeding, False otherwise
        """
        if not stage:
            return True  # Default to allowing calculations
        
        # Stage names that don't have external feeding
        non_feeding_stages = ['egg', 'alevin', 'eyed egg']
        
        return stage.name.lower() not in non_feeding_stages
    
    def _apply_model_changes(self, current_date: date):
        """Apply any model changes scheduled for the current date."""
        if current_date in self.model_changes:
            change = self.model_changes[current_date]
            
            if change.new_tgc_model:
                self.tgc_calculator = TGCCalculator(change.new_tgc_model)
                self.warnings.append(
                    f"Applied TGC model change on {current_date}: {change.new_tgc_model.name}"
                )
            
            if change.new_fcr_model:
                self.fcr_calculator = FCRCalculator(change.new_fcr_model)
                self.warnings.append(
                    f"Applied FCR model change on {current_date}: {change.new_fcr_model.name}"
                )
            
            if change.new_mortality_model:
                self.mortality_calculator = MortalityCalculator(change.new_mortality_model)
                self.warnings.append(
                    f"Applied mortality model change on {current_date}: {change.new_mortality_model.name}"
                )
    
    @transaction.atomic
    def run_projection(
        self,
        save_results: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Run the complete projection for the scenario.
        
        Args:
            save_results: Whether to save projections to database
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with projection results and summary
        """
        if self.errors:
            return {
                'success': False,
                'errors': self.errors,
                'warnings': self.warnings,
                'projections': []
            }
        
        # Clear existing projections if re-running
        if save_results:
            self.scenario.projections.all().delete()
        
        # Initialize projection state
        current_date = self.scenario.start_date
        end_date = self.scenario.start_date + timedelta(days=self.scenario.duration_days - 1)
        
        current_weight = float(self.scenario.initial_weight)
        current_population = self.scenario.initial_count
        current_stage = self._determine_lifecycle_stage(current_weight)
        
        projections = []
        cumulative_feed = 0.0
        day_number = 0
        
        # Run daily projections
        while current_date <= end_date:
            day_number += 1
            
            # Apply any model changes
            self._apply_model_changes(current_date)
            
            # Get temperature for the day
            temperature = self.tgc_calculator._get_temperature_for_date(current_date)
            
            # Calculate growth (only if stage has external feeding)
            if self._stage_has_external_feeding(current_stage):
                # Use stage-specific TGC if available
                growth_result = self.tgc_calculator.calculate_daily_growth(
                    current_weight=current_weight,
                    temperature=temperature,
                    lifecycle_stage=current_stage.name if current_stage else None
                )
                new_weight = growth_result['new_weight_g']
                weight_gain = growth_result['growth_g']
            else:
                # No growth during egg/alevin stages
                new_weight = current_weight
                weight_gain = 0.0
            
            # Calculate mortality with stage-specific rate
            stage_mortality_rate = self.mortality_calculator.get_mortality_rate_for_stage(
                stage=current_stage.name if current_stage else None,
                frequency='daily'
            )
            mortality_data = self.mortality_calculator.calculate_mortality(
                population=current_population,
                days=1,
                custom_rate=stage_mortality_rate
            )
            new_population = mortality_data['surviving_population']
            
            # Update lifecycle stage if needed
            new_stage = self._determine_lifecycle_stage(new_weight)
            if new_stage and new_stage != current_stage:
                self.warnings.append(
                    f"Stage transition on day {day_number}: "
                    f"{current_stage.name if current_stage else 'Unknown'} -> {new_stage.name}"
                )
                current_stage = new_stage
            
            # Calculate feed (only if stage has external feeding)
            if self._stage_has_external_feeding(current_stage):
                # Get stage-specific FCR with weight overrides
                fcr_value = self.fcr_calculator.get_fcr_for_stage(
                    stage=current_stage,
                    weight_g=current_weight
                )
                feed_data = self.fcr_calculator.calculate_daily_feed_with_fcr(
                    avg_weight_g=current_weight,
                    weight_gain_g=weight_gain,
                    population=new_population,
                    fcr_value=fcr_value
                )
                cumulative_feed += feed_data['daily_feed_kg']
            else:
                # No feed during egg/alevin stages
                feed_data = {
                    'daily_feed_kg': 0.0,
                    'feed_per_fish_g': 0.0,
                    'feeding_rate_percent': 0.0,
                    'fcr_used': 0.0
                }
            
            # Calculate biomass
            biomass = (new_weight * new_population) / 1000.0  # Convert to kg
            
            # Create projection record
            projection = ScenarioProjection(
                scenario=self.scenario,
                projection_date=current_date,
                day_number=day_number,
                average_weight=new_weight,
                population=new_population,
                biomass=round(biomass, 2),
                daily_feed=feed_data['daily_feed_kg'],
                cumulative_feed=round(cumulative_feed, 3),
                temperature=temperature,
                current_stage=current_stage
            )
            
            projections.append(projection)
            
            # Update state for next iteration
            current_weight = new_weight
            current_population = new_population
            current_date += timedelta(days=1)
            
            # Progress callback
            if progress_callback:
                progress = (day_number / self.scenario.duration_days) * 100
                progress_callback(progress, f"Processing day {day_number}")
        
        # Save projections if requested
        if save_results and projections:
            ScenarioProjection.objects.bulk_create(projections)
        
        # Generate summary
        summary = self._generate_summary(projections)
        
        return {
            'success': True,
            'errors': self.errors,
            'warnings': self.warnings,
            'projections': projections if not save_results else [],
            'summary': summary,
            'projections_saved': save_results
        }
    
    def _generate_summary(self, projections: List[ScenarioProjection]) -> Dict:
        """Generate summary statistics from projections."""
        if not projections:
            return {}
        
        first = projections[0]
        last = projections[-1]
        
        # Calculate growth metrics
        total_weight_gain = last.average_weight - float(self.scenario.initial_weight)
        weight_gain_percent = (total_weight_gain / float(self.scenario.initial_weight)) * 100
        
        # Calculate mortality metrics
        total_mortality = self.scenario.initial_count - last.population
        mortality_percent = (total_mortality / self.scenario.initial_count) * 100
        
        # Calculate average FCR
        if total_weight_gain > 0 and last.population > 0:
            total_biomass_gain = (last.biomass - 
                                 (float(self.scenario.initial_weight) * self.scenario.initial_count / 1000))
            average_fcr = last.cumulative_feed / total_biomass_gain if total_biomass_gain > 0 else 0
        else:
            average_fcr = 0
        
        # Find min/max temperatures
        temps = [p.temperature for p in projections]
        
        return {
            'duration_days': self.scenario.duration_days,
            'initial_conditions': {
                'weight': float(self.scenario.initial_weight),
                'population': self.scenario.initial_count,
                'biomass': round((float(self.scenario.initial_weight) * self.scenario.initial_count) / 1000, 2)
            },
            'final_conditions': {
                'weight': round(last.average_weight, 2),
                'population': last.population,
                'biomass': round(last.biomass, 2)
            },
            'growth_metrics': {
                'total_weight_gain': round(total_weight_gain, 2),
                'weight_gain_percent': round(weight_gain_percent, 1),
                'average_daily_gain': round(total_weight_gain / self.scenario.duration_days, 2)
            },
            'mortality_metrics': {
                'total_deaths': total_mortality,
                'mortality_percent': round(mortality_percent, 2),
                'survival_rate': round(100 - mortality_percent, 2)
            },
            'feed_metrics': {
                'total_feed_kg': round(last.cumulative_feed, 2),
                'average_fcr': round(average_fcr, 3),
                'daily_average_feed': round(last.cumulative_feed / self.scenario.duration_days, 2)
            },
            'temperature_metrics': {
                'min': round(min(temps), 1),
                'max': round(max(temps), 1),
                'average': round(sum(temps) / len(temps), 1)
            }
        }
    
    def _get_original_parameter_value(self, parameter: str) -> float:
        """
        Get the original value for a parameter before sensitivity analysis.

        Args:
            parameter: Parameter name ('tgc', 'fcr', 'mortality')

        Returns:
            Original parameter value

        Raises:
            ValueError: If parameter is unknown
        """
        if parameter == 'tgc':
            return self.tgc_calculator.tgc_value
        elif parameter == 'fcr':
            # Get average FCR across stages
            fcr_values = [v for v in self.fcr_calculator.stage_fcr_map.values()]
            return sum(fcr_values) / len(fcr_values) if fcr_values else 1.2
        elif parameter == 'mortality':
            return self.mortality_calculator.rate
        else:
            raise ValueError(f'Unknown parameter: {parameter}')

    def _apply_parameter_variation(self, parameter: str, original_value: float, variation: float):
        """
        Apply a percentage variation to a parameter.

        Args:
            parameter: Parameter name
            original_value: Original parameter value
            variation: Percentage variation (e.g., -10.0, 5.0)
        """
        varied_value = original_value * (1 + variation / 100)

        if parameter == 'tgc':
            self.tgc_calculator.tgc_value = varied_value
        elif parameter == 'fcr':
            # Apply variation to all stages
            for stage_id in self.fcr_calculator.stage_fcr_map:
                self.fcr_calculator.stage_fcr_map[stage_id] *= (1 + variation / 100)
        elif parameter == 'mortality':
            self.mortality_calculator.rate = varied_value
            self.mortality_calculator.daily_rate = varied_value if self.mortality_calculator.frequency == 'daily' else self.mortality_calculator.daily_rate

    def _reset_parameter_to_original(self, parameter: str, original_value: float):
        """
        Reset a parameter to its original value.

        Args:
            parameter: Parameter name
            original_value: Original parameter value
        """
        if parameter == 'tgc':
            self.tgc_calculator.tgc_value = original_value
        elif parameter == 'fcr':
            self._initialize_calculators()  # Easiest way to reset
        elif parameter == 'mortality':
            self.mortality_calculator.rate = original_value
            self.mortality_calculator.__init__(self.scenario.mortality_model)

    def _run_projection_for_variation(self, parameter: str, original_value: float, variation: float) -> Optional[Dict]:
        """
        Run a projection for a parameter variation and extract results.

        Args:
            parameter: Parameter name
            original_value: Original parameter value
            variation: Percentage variation

        Returns:
            Dict with variation results or None if projection failed
        """
        varied_value = original_value * (1 + variation / 100)
        result = self.run_projection(save_results=False)

        if result['success'] and result['projections']:
            return {
                'parameter_value': round(varied_value, 3),
                'summary': result['summary']
            }

        return None

    def run_sensitivity_analysis(
        self,
        parameter: str,
        variations: List[float],
        save_results: bool = False
    ) -> Dict[str, any]:
        """
        Run sensitivity analysis on a parameter.

        Args:
            parameter: Parameter to vary ('tgc', 'fcr', 'mortality')
            variations: List of percentage variations (e.g., [-10, 0, 10])
            save_results: Whether to save results

        Returns:
            Dict with sensitivity analysis results
        """
        try:
            original_value = self._get_original_parameter_value(parameter)
        except ValueError as e:
            return {'error': str(e)}

        results = {}

        # Run projections with variations
        for variation in variations:
            self._apply_parameter_variation(parameter, original_value, variation)

            variation_result = self._run_projection_for_variation(parameter, original_value, variation)
            if variation_result:
                results[f"{variation:+.0f}%"] = variation_result

            self._reset_parameter_to_original(parameter, original_value)

        return {
            'parameter': parameter,
            'original_value': round(original_value, 3),
            'variations': results
        } 