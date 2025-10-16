"""
TGC (Thermal Growth Coefficient) calculator for growth projections.

Implements the standard TGC formula used in salmonid aquaculture:
TGC = (W2^(1/3) - W1^(1/3)) / (T × D) × 1000

Where:
- W1 = Initial weight (g)
- W2 = Final weight (g)
- T = Average temperature (°C)
- D = Number of days
"""
import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from ...models import TGCModel, TemperatureProfile, LifecycleStageChoices


class TGCCalculator:
    """
    Calculator for fish growth using Thermal Growth Coefficient models.
    
    Supports both forward calculation (weight from TGC) and reverse
    calculation (TGC from weight change).
    """
    
    def __init__(self, tgc_model: TGCModel):
        """
        Initialize calculator with a TGC model.
        
        Args:
            tgc_model: TGC model containing coefficient and temperature profile
        """
        self.model = tgc_model
        self.tgc_value = float(tgc_model.tgc_value)
        self.exponent_n = float(tgc_model.exponent_n)
        self.exponent_m = float(tgc_model.exponent_m)
        self.temperature_profile = tgc_model.profile
    
    def calculate_weight_gain(
        self,
        initial_weight: float,
        temperature: float,
        days: int = 1
    ) -> float:
        """
        Calculate weight gain over a period using TGC formula.
        
        Args:
            initial_weight: Starting weight in grams
            temperature: Average temperature in Celsius
            days: Number of days (default 1)
            
        Returns:
            Final weight in grams
        """
        if initial_weight <= 0 or temperature <= 0 or days <= 0:
            return initial_weight
        
        # Standard TGC formula rearranged to solve for W2
        # W2^(1/3) = W1^(1/3) + (TGC × T × D / 1000)
        # W2 = (W1^(1/3) + (TGC × T × D / 1000))^3
        
        # Apply temperature exponent if not 1.0
        temp_factor = temperature if self.exponent_n == 1.0 else math.pow(temperature, self.exponent_n)
        
        # Apply weight exponent (typically 1/3 for salmonids)
        weight_exp = 1.0 / 3.0 if self.exponent_m == 0 else self.exponent_m
        
        initial_weight_root = math.pow(initial_weight, weight_exp)
        growth_factor = (self.tgc_value * temp_factor * days) / 1000.0
        
        final_weight_root = initial_weight_root + growth_factor
        final_weight = math.pow(final_weight_root, 1.0 / weight_exp)
        
        return round(final_weight, 2)
    
    def calculate_daily_growth(
        self,
        current_weight: float,
        temperature: float,
        lifecycle_stage: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate daily growth using TGC formula.
        
        Args:
            current_weight: Current average weight in grams
            temperature: Water temperature in Celsius
            lifecycle_stage: Current lifecycle stage (for stage-specific TGC)
            
        Returns:
            Dict with growth_g and new_weight_g
        """
        # Check for stage-specific TGC override
        tgc_value = self.model.tgc_value
        temp_exponent = self.model.exponent_n
        weight_exponent = self.model.exponent_m
        
        if lifecycle_stage:
            # Look for stage-specific override
            try:
                stage_override = self.model.stage_overrides.get(
                    lifecycle_stage=lifecycle_stage
                )
                tgc_value = float(stage_override.tgc_value)
                temp_exponent = float(stage_override.temperature_exponent)
                weight_exponent = float(stage_override.weight_exponent)
            except:
                # No override found, use base model values
                pass
        
        # Standard TGC formula: ΔW = TGC × T^n × W^m
        growth_g = (
            tgc_value * 
            (temperature ** temp_exponent) * 
            (current_weight ** weight_exponent)
        )
        
        new_weight = current_weight + growth_g
        
        return {
            'growth_g': growth_g,
            'new_weight_g': new_weight,
            'tgc_value': tgc_value,
            'temperature': temperature
        }
    
    def calculate_tgc_from_growth(
        self,
        initial_weight: float,
        final_weight: float,
        average_temperature: float,
        days: int
    ) -> float:
        """
        Calculate TGC value from observed growth (reverse calculation).
        
        Args:
            initial_weight: Starting weight in grams
            final_weight: Ending weight in grams
            average_temperature: Average temperature over period
            days: Number of days
            
        Returns:
            Calculated TGC value
        """
        if initial_weight <= 0 or final_weight <= 0 or average_temperature <= 0 or days <= 0:
            return 0.0
        
        # TGC = (W2^(1/3) - W1^(1/3)) / (T × D) × 1000
        weight_exp = 1.0 / 3.0 if self.exponent_m == 0 else self.exponent_m
        
        w1_root = math.pow(initial_weight, weight_exp)
        w2_root = math.pow(final_weight, weight_exp)
        
        temp_factor = average_temperature if self.exponent_n == 1.0 else math.pow(average_temperature, self.exponent_n)
        
        tgc = ((w2_root - w1_root) / (temp_factor * days)) * 1000
        
        return round(tgc, 3)
    
    def project_growth(
        self,
        initial_weight: float,
        start_date: date,
        end_date: date,
        temperature_override: Optional[Dict[date, float]] = None
    ) -> List[Dict]:
        """
        Project daily growth over a date range.
        
        Args:
            initial_weight: Starting weight in grams
            start_date: Start date for projection
            end_date: End date for projection
            temperature_override: Optional dict of date->temperature overrides
            
        Returns:
            List of daily projections with date, temperature, and weight
        """
        projections = []
        current_weight = initial_weight
        current_date = start_date
        
        while current_date <= end_date:
            # Get temperature for this date
            if temperature_override and current_date in temperature_override:
                temperature = temperature_override[current_date]
            else:
                temperature = self._get_temperature_for_date(current_date)
            
            # Calculate new weight
            new_weight = self.calculate_weight_gain(current_weight, temperature, days=1)
            daily_gain = new_weight - current_weight
            growth_rate = (daily_gain / current_weight * 100) if current_weight > 0 else 0
            
            projections.append({
                'date': current_date,
                'day_number': (current_date - start_date).days + 1,
                'temperature': temperature,
                'weight': round(new_weight, 2),
                'daily_gain': round(daily_gain, 2),
                'growth_rate': round(growth_rate, 3),
                'cumulative_gain': round(new_weight - initial_weight, 2)
            })
            
            # Update for next iteration
            current_weight = new_weight
            current_date += timedelta(days=1)
        
        return projections
    
    def calculate_days_to_target_weight(
        self,
        initial_weight: float,
        target_weight: float,
        average_temperature: float
    ) -> int:
        """
        Calculate days needed to reach target weight.
        
        Args:
            initial_weight: Starting weight in grams
            target_weight: Target weight in grams
            average_temperature: Average temperature assumption
            
        Returns:
            Estimated number of days
        """
        if initial_weight >= target_weight or average_temperature <= 0:
            return 0
        
        # Rearrange TGC formula to solve for days
        # D = (W2^(1/3) - W1^(1/3)) / (TGC × T) × 1000
        weight_exp = 1.0 / 3.0 if self.exponent_m == 0 else self.exponent_m
        
        w1_root = math.pow(initial_weight, weight_exp)
        w2_root = math.pow(target_weight, weight_exp)
        
        temp_factor = average_temperature if self.exponent_n == 1.0 else math.pow(average_temperature, self.exponent_n)
        
        days = ((w2_root - w1_root) * 1000) / (self.tgc_value * temp_factor)
        
        return max(1, int(math.ceil(days)))
    
    def _get_temperature_for_day(self, day_number: int) -> float:
        """
        Get temperature from profile for a specific day number.

        Args:
            day_number: Relative day number (1-based) from scenario start

        Returns:
            Temperature in Celsius, or 10.0 as default
        """
        if not self.temperature_profile:
            return 10.0  # Default temperature

        try:
            # Direct lookup by day number
            reading = self.temperature_profile.readings.filter(
                day_number=day_number
            ).first()

            if reading:
                return float(reading.temperature)

            # If no exact match, try to interpolate between adjacent days
            before = self.temperature_profile.readings.filter(
                day_number__lt=day_number
            ).order_by('-day_number').first()

            after = self.temperature_profile.readings.filter(
                day_number__gt=day_number
            ).order_by('day_number').first()

            if before and after:
                # Linear interpolation between days
                days_total = after.day_number - before.day_number
                days_from_before = day_number - before.day_number

                temp_diff = float(after.temperature - before.temperature)
                interpolated = float(before.temperature) + (temp_diff * days_from_before / days_total)

                return round(interpolated, 2)
            elif before:
                # Use last known temperature
                return float(before.temperature)
            elif after:
                # Use next known temperature
                return float(after.temperature)
            else:
                return 10.0  # Default if no data

        except Exception:
            return 10.0  # Default on any error
    
    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Validate TGC model parameters.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if self.tgc_value <= 0:
            errors.append("TGC value must be positive")
        
        if self.tgc_value > 5:
            errors.append("TGC value unusually high (>5)")
        
        if self.exponent_n < 0 or self.exponent_n > 2:
            errors.append("Temperature exponent should be between 0 and 2")
        
        if self.exponent_m <= 0 or self.exponent_m > 1:
            errors.append("Weight exponent should be between 0 and 1")
        
        if not self.temperature_profile:
            errors.append("No temperature profile associated with TGC model")
        
        return len(errors) == 0, errors
    
    def calculate_degree_days(
        self,
        start_date: date,
        end_date: date,
        base_temperature: float = 0.0
    ) -> float:
        """
        Calculate cumulative degree-days for a period.
        
        Useful for egg/alevin development timing where development is
        temperature-dependent but not growth-based. Salmon eggs typically
        need 400-500 degree-days to hatch.
        
        Args:
            start_date: Start date
            end_date: End date  
            base_temperature: Base temperature for calculation (default 0°C)
            
        Returns:
            Cumulative degree-days
        """
        degree_days = 0.0
        current_date = start_date
        
        while current_date <= end_date:
            temperature = self._get_temperature_for_date(current_date)
            if temperature > base_temperature:
                degree_days += (temperature - base_temperature)
            current_date += timedelta(days=1)
        
        return round(degree_days, 1) 