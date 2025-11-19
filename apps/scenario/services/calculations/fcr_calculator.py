"""
FCR (Feed Conversion Ratio) calculator for feed projections.

Implements feed requirement calculations based on growth and lifecycle stages.
FCR = Feed consumed (kg) / Weight gain (kg)
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from ...models import FCRModel, FCRModelStage
from ...models import LifecycleStageChoices
from apps.batch.models import LifeCycleStage


class FCRCalculator:
    """
    Calculator for feed requirements using FCR models.
    
    Supports lifecycle-specific FCR values and feed optimization.
    """
    
    def __init__(self, fcr_model: FCRModel):
        """
        Initialize calculator with an FCR model.
        
        Args:
            fcr_model: FCR model with stage-specific values
        """
        self.model = fcr_model
        self._load_stage_fcr_map()
    
    def _load_stage_fcr_map(self):
        """Load FCR values by lifecycle stage into a map."""
        self.stage_fcr_map = {}
        self.stage_duration_map = {}
        
        for stage_fcr in self.model.stages.select_related('stage'):
            self.stage_fcr_map[stage_fcr.stage.id] = float(stage_fcr.fcr_value)
            self.stage_duration_map[stage_fcr.stage.id] = stage_fcr.duration_days
    
    def get_fcr_for_stage(
        self,
        stage: LifeCycleStage,
        weight_g: Optional[float] = None
    ) -> float:
        """
        Get FCR value for a specific lifecycle stage.
        
        Args:
            stage: Lifecycle stage
            weight_g: Optional weight for weight-based FCR overrides
            
        Returns:
            FCR value for the stage
        """
        # First try to find stage-specific FCR from map
        fcr_value = self.stage_fcr_map.get(stage.id)
        if fcr_value is not None:
            # Check for weight-based overrides within the stage
            try:
                fcr_stage = self.model.stages.get(stage=stage)
                if weight_g and hasattr(fcr_stage, 'overrides'):
                    for override in fcr_stage.overrides.all().order_by('min_weight_g'):
                        if override.min_weight_g <= weight_g <= override.max_weight_g:
                            return float(override.fcr_value)
            except:
                pass
            
            return fcr_value
        
        # No stage-specific FCR found, use default
        return 1.2  # Default FCR if not specified
    
    def calculate_daily_feed_with_fcr(
        self,
        avg_weight_g: float,
        weight_gain_g: float,
        population: int,
        fcr_value: float
    ) -> Dict[str, float]:
        """
        Calculate daily feed requirements using a specific FCR value.
        
        Args:
            avg_weight_g: Average weight per fish in grams
            weight_gain_g: Daily weight gain per fish in grams
            population: Number of fish
            fcr_value: FCR value to use
            
        Returns:
            Dict containing feed calculations
        """
        # Total biomass gain in kg
        total_biomass_gain_kg = (weight_gain_g * population) / 1000
        
        # Feed required based on FCR
        daily_feed_kg = total_biomass_gain_kg * fcr_value
        
        # Feed per fish
        feed_per_fish_g = (daily_feed_kg * 1000) / population if population > 0 else 0
        
        # Feeding rate as percentage of body weight
        feeding_rate_percent = (feed_per_fish_g / avg_weight_g * 100) if avg_weight_g > 0 else 0
        
        return {
            'daily_feed_kg': round(daily_feed_kg, 3),
            'feed_per_fish_g': round(feed_per_fish_g, 2),
            'feeding_rate_percent': round(feeding_rate_percent, 2),
            'fcr_used': fcr_value,
            'biomass_gain_kg': round(total_biomass_gain_kg, 3)
        }
    
    def calculate_daily_feed(
        self,
        current_weight: float,
        weight_gain: float,
        stage: LifeCycleStage,
        population: int = 1
    ) -> Dict[str, float]:
        """
        Calculate daily feed requirement.
        
        Args:
            current_weight: Current average weight in grams
            weight_gain: Daily weight gain in grams
            stage: Current lifecycle stage
            population: Number of fish (default 1)
            
        Returns:
            Dict with feed metrics
        """
        if weight_gain <= 0:
            return {
                'daily_feed_g': 0.0,
                'daily_feed_kg': 0.0,
                'feed_per_fish_g': 0.0,
                'feeding_rate_percent': 0.0,
                'fcr_used': self.get_fcr_for_stage(stage)
            }
        
        fcr = self.get_fcr_for_stage(stage)
        
        # Calculate feed needed for weight gain
        # FCR = Feed / Gain, so Feed = FCR × Gain
        feed_per_fish_g = fcr * weight_gain
        total_feed_g = feed_per_fish_g * population
        total_feed_kg = total_feed_g / 1000.0
        
        # Calculate feeding rate as percentage of body weight
        feeding_rate = (feed_per_fish_g / current_weight) * 100 if current_weight > 0 else 0
        
        return {
            'daily_feed_g': round(total_feed_g, 2),
            'daily_feed_kg': round(total_feed_kg, 3),
            'feed_per_fish_g': round(feed_per_fish_g, 2),
            'feeding_rate_percent': round(feeding_rate, 2),
            'fcr_used': fcr
        }
    
    def calculate_feed_for_period(
        self,
        weight_changes: List[Dict],
        stage_transitions: Optional[Dict[date, LifeCycleStage]] = None
    ) -> List[Dict]:
        """
        Calculate feed requirements over a period with weight changes.
        
        Args:
            weight_changes: List of dicts with 'date', 'weight', 'population', 'stage'
            stage_transitions: Optional dict of date->stage for transitions
            
        Returns:
            List of daily feed calculations
        """
        feed_projections = []
        cumulative_feed = 0.0
        
        for i, day_data in enumerate(weight_changes):
            # Determine current stage
            if stage_transitions and day_data['date'] in stage_transitions:
                current_stage = stage_transitions[day_data['date']]
            else:
                current_stage = day_data.get('stage')
            
            # Calculate weight gain
            if i == 0:
                # First day - assume small gain
                weight_gain = day_data['weight'] * 0.01  # 1% gain assumption
            else:
                weight_gain = day_data['weight'] - weight_changes[i-1]['weight']
            
            # Calculate feed
            feed_data = self.calculate_daily_feed(
                day_data['weight'],
                weight_gain,
                current_stage,
                day_data.get('population', 1)
            )
            
            # Add cumulative data
            cumulative_feed += feed_data['daily_feed_kg']
            feed_data['cumulative_feed_kg'] = round(cumulative_feed, 3)
            feed_data['date'] = day_data['date']
            feed_data['stage'] = current_stage
            
            feed_projections.append(feed_data)
        
        return feed_projections
    
    def optimize_fcr(
        self,
        current_fcr: float,
        target_improvement: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculate potential feed savings from FCR improvement.
        
        Args:
            current_fcr: Current FCR value
            target_improvement: Target FCR reduction (default 0.05)
            
        Returns:
            Dict with optimization metrics
        """
        improved_fcr = max(0.8, current_fcr - target_improvement)  # Min FCR of 0.8
        
        # Calculate percentage improvements
        fcr_improvement_percent = ((current_fcr - improved_fcr) / current_fcr) * 100
        feed_savings_percent = fcr_improvement_percent  # Direct relationship
        
        return {
            'current_fcr': current_fcr,
            'improved_fcr': round(improved_fcr, 3),
            'fcr_reduction': round(current_fcr - improved_fcr, 3),
            'improvement_percent': round(fcr_improvement_percent, 1),
            'feed_savings_percent': round(feed_savings_percent, 1)
        }
    
    def calculate_feed_cost(
        self,
        feed_amount_kg: float,
        feed_price_per_kg: float = 1.5
    ) -> Dict[str, float]:
        """
        Calculate feed cost.
        
        Args:
            feed_amount_kg: Amount of feed in kg
            feed_price_per_kg: Price per kg (default 1.5)
            
        Returns:
            Dict with cost metrics
        """
        total_cost = feed_amount_kg * feed_price_per_kg
        
        return {
            'feed_amount_kg': round(feed_amount_kg, 3),
            'price_per_kg': feed_price_per_kg,
            'total_cost': round(total_cost, 2),
            'cost_per_tonne': round(total_cost / (feed_amount_kg / 1000), 2) if feed_amount_kg > 0 else 0
        }
    
    def estimate_stage_duration(
        self,
        stage: LifeCycleStage,
        current_weight: float,
        target_weight: float,
        daily_growth_rate: float
    ) -> int:
        """
        Estimate days remaining in lifecycle stage.
        
        Args:
            stage: Current lifecycle stage
            current_weight: Current weight in grams
            target_weight: Target weight for stage completion
            daily_growth_rate: Daily growth rate as decimal (e.g., 0.02 for 2%)
            
        Returns:
            Estimated days to complete stage
        """
        if current_weight >= target_weight or daily_growth_rate <= 0:
            return 0
        
        # Calculate days using compound growth formula
        # target = current × (1 + rate)^days
        # days = log(target/current) / log(1 + rate)
        import math
        
        weight_ratio = target_weight / current_weight
        days = math.log(weight_ratio) / math.log(1 + daily_growth_rate)
        
        # Check against stage duration if defined
        stage_duration = self.stage_duration_map.get(stage.id)
        if stage_duration:
            # Return minimum of calculated and defined duration
            return min(int(math.ceil(days)), stage_duration)
        
        return int(math.ceil(days))
    
    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Validate FCR model parameters.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not self.model.stages.exists():
            errors.append("No lifecycle stages defined for FCR model")
        
        for stage_fcr in self.model.stages.all():
            # Allow FCR=0 for Egg&Alevin stage (no external feeding, yolk sac)
            stage_name = stage_fcr.stage.name if hasattr(stage_fcr.stage, 'name') else str(stage_fcr.stage)
            
            if stage_fcr.fcr_value < 0:
                errors.append(f"FCR value must be non-negative for stage {stage_fcr.stage}")
            elif stage_fcr.fcr_value == 0 and 'Egg' not in stage_name and 'Alevin' not in stage_name:
                errors.append(f"FCR value must be positive for stage {stage_fcr.stage}")
            elif stage_fcr.fcr_value > 0 and stage_fcr.fcr_value < 0.5:
                errors.append(f"FCR value unusually low (<0.5) for stage {stage_fcr.stage}")
            
            if stage_fcr.fcr_value > 3.0:
                errors.append(f"FCR value unusually high (>3.0) for stage {stage_fcr.stage}")
            
            if stage_fcr.duration_days and stage_fcr.duration_days <= 0:
                errors.append(f"Duration must be positive for stage {stage_fcr.stage}")
        
        return len(errors) == 0, errors
    
    def get_stage_summary(self) -> List[Dict]:
        """
        Get summary of all stages in the FCR model.
        
        Returns:
            List of stage summaries
        """
        summaries = []
        
        # Order by the correct minimum expected weight field
        for stage_fcr in self.model.stages.select_related('stage').order_by('stage__expected_weight_min_g'):
            summaries.append({
                'stage_name': stage_fcr.stage.name,
                'fcr_value': float(stage_fcr.fcr_value),
                'duration_days': stage_fcr.duration_days,
                'weight_range': {
                    # Use the correct field name for the start weight of the stage
                    'start': float(stage_fcr.stage.expected_weight_min_g) if stage_fcr.stage.expected_weight_min_g else None,
                    # And the correct field for the end weight of the stage
                    'end': float(stage_fcr.stage.expected_weight_max_g) if stage_fcr.stage.expected_weight_max_g else None
                }
            })
        
        return summaries 