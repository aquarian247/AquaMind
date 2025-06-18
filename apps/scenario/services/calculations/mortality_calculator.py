"""
Mortality calculator for population projections.

Implements mortality calculations based on daily or weekly rates.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import math

from ...models import MortalityModel


class MortalityCalculator:
    """
    Calculator for mortality and population changes.
    
    Supports daily and weekly mortality rates with various
    calculation methods.
    """
    
    def __init__(self, mortality_model: MortalityModel):
        """
        Initialize calculator with a mortality model.
        
        Args:
            mortality_model: Mortality model with rate and frequency
        """
        self.model = mortality_model
        self.rate = float(mortality_model.rate)
        self.frequency = mortality_model.frequency
        
        # Convert to daily rate if weekly
        if self.frequency == 'weekly':
            # Convert weekly rate to daily using compound formula
            # daily_rate = 1 - (1 - weekly_rate)^(1/7)
            self.daily_rate = 1 - math.pow(1 - (self.rate / 100), 1/7)
            self.daily_rate *= 100  # Convert to percentage
        else:
            self.daily_rate = self.rate
    
    def calculate_daily_mortality(
        self,
        current_population: int,
        custom_rate: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate daily mortality.
        
        Args:
            current_population: Current number of fish
            custom_rate: Optional custom mortality rate (percentage)
            
        Returns:
            Dict with mortality metrics
        """
        if current_population <= 0:
            return {
                'deaths': 0,
                'surviving_population': 0,
                'mortality_rate': 0.0,
                'survival_rate': 0.0
            }
        
        rate_to_use = custom_rate if custom_rate is not None else self.daily_rate
        
        # Calculate deaths
        deaths = current_population * (rate_to_use / 100)
        
        # Round deaths appropriately
        if deaths < 1 and deaths > 0:
            # For very low mortality, use probabilistic rounding
            import random
            deaths = 1 if random.random() < deaths else 0
        else:
            deaths = round(deaths)
        
        surviving = current_population - deaths
        survival_rate = 100 - rate_to_use
        
        return {
            'deaths': deaths,
            'surviving_population': surviving,
            'mortality_rate': round(rate_to_use, 4),
            'survival_rate': round(survival_rate, 4)
        }
    
    def project_population(
        self,
        initial_population: int,
        days: int,
        mortality_events: Optional[Dict[int, float]] = None
    ) -> List[Dict]:
        """
        Project population over time with mortality.
        
        Args:
            initial_population: Starting population
            days: Number of days to project
            mortality_events: Optional dict of day->mortality_rate for events
            
        Returns:
            List of daily population data
        """
        projections = []
        current_population = initial_population
        cumulative_deaths = 0
        
        for day in range(1, days + 1):
            # Check for mortality event
            if mortality_events and day in mortality_events:
                mortality_rate = mortality_events[day]
            else:
                mortality_rate = self.daily_rate
            
            # Calculate mortality
            mortality_data = self.calculate_daily_mortality(
                current_population,
                mortality_rate
            )
            
            # Update cumulative data
            cumulative_deaths += mortality_data['deaths']
            cumulative_mortality_rate = (cumulative_deaths / initial_population * 100) if initial_population > 0 else 0
            
            projections.append({
                'day': day,
                'population': mortality_data['surviving_population'],
                'daily_deaths': mortality_data['deaths'],
                'cumulative_deaths': cumulative_deaths,
                'daily_mortality_rate': mortality_data['mortality_rate'],
                'cumulative_mortality_rate': round(cumulative_mortality_rate, 2),
                'survival_rate': round((mortality_data['surviving_population'] / initial_population * 100) if initial_population > 0 else 0, 2)
            })
            
            # Update for next iteration
            current_population = mortality_data['surviving_population']
        
        return projections
    
    def calculate_period_mortality(
        self,
        initial_population: int,
        final_population: int,
        days: int
    ) -> Dict[str, float]:
        """
        Calculate mortality rate from population change.
        
        Args:
            initial_population: Starting population
            final_population: Ending population
            days: Number of days
            
        Returns:
            Dict with calculated mortality metrics
        """
        if initial_population <= 0 or days <= 0:
            return {
                'total_mortality': 0,
                'daily_rate': 0.0,
                'weekly_rate': 0.0,
                'survival_rate': 0.0
            }
        
        total_deaths = initial_population - final_population
        survival_ratio = final_population / initial_population
        
        # Calculate daily mortality rate using compound formula
        # survival_ratio = (1 - daily_rate)^days
        # daily_rate = 1 - survival_ratio^(1/days)
        daily_rate = (1 - math.pow(survival_ratio, 1/days)) * 100
        
        # Convert to weekly rate
        weekly_rate = (1 - math.pow(1 - daily_rate/100, 7)) * 100
        
        return {
            'total_mortality': total_deaths,
            'daily_rate': round(daily_rate, 4),
            'weekly_rate': round(weekly_rate, 3),
            'survival_rate': round(survival_ratio * 100, 2)
        }
    
    def simulate_mortality_scenarios(
        self,
        initial_population: int,
        days: int,
        scenarios: Dict[str, float]
    ) -> Dict[str, List[Dict]]:
        """
        Simulate multiple mortality scenarios for comparison.
        
        Args:
            initial_population: Starting population
            days: Number of days to simulate
            scenarios: Dict of scenario_name->mortality_rate
            
        Returns:
            Dict of scenario results
        """
        results = {}
        
        for scenario_name, mortality_rate in scenarios.items():
            # Create temporary calculator with scenario rate
            temp_model = MortalityModel(
                name=f"Scenario: {scenario_name}",
                frequency='daily',
                rate=mortality_rate
            )
            temp_calculator = MortalityCalculator(temp_model)
            
            # Run projection
            projections = temp_calculator.project_population(
                initial_population,
                days
            )
            
            results[scenario_name] = {
                'projections': projections,
                'final_population': projections[-1]['population'] if projections else 0,
                'total_mortality': projections[-1]['cumulative_deaths'] if projections else 0,
                'survival_rate': projections[-1]['survival_rate'] if projections else 0
            }
        
        return results
    
    def estimate_catastrophic_event(
        self,
        population: int,
        event_mortality_rate: float,
        recovery_days: int = 7
    ) -> List[Dict]:
        """
        Model a catastrophic mortality event with recovery period.
        
        Args:
            population: Current population
            event_mortality_rate: Mortality rate for the event (percentage)
            recovery_days: Days of elevated mortality after event
            
        Returns:
            List of population projections during event and recovery
        """
        projections = []
        current_population = population
        
        # Day 0: Catastrophic event
        event_deaths = round(current_population * (event_mortality_rate / 100))
        current_population -= event_deaths
        
        projections.append({
            'day': 0,
            'event': 'catastrophic',
            'population': current_population,
            'deaths': event_deaths,
            'mortality_rate': event_mortality_rate
        })
        
        # Recovery period with declining mortality
        for day in range(1, recovery_days + 1):
            # Mortality rate declines exponentially during recovery
            recovery_rate = self.daily_rate * math.exp(-0.3 * day) * 3  # 3x normal, declining
            
            mortality_data = self.calculate_daily_mortality(
                current_population,
                recovery_rate
            )
            
            projections.append({
                'day': day,
                'event': 'recovery',
                'population': mortality_data['surviving_population'],
                'deaths': mortality_data['deaths'],
                'mortality_rate': mortality_data['mortality_rate']
            })
            
            current_population = mortality_data['surviving_population']
        
        # Return to normal mortality
        for day in range(recovery_days + 1, recovery_days + 8):
            mortality_data = self.calculate_daily_mortality(current_population)
            
            projections.append({
                'day': day,
                'event': 'normal',
                'population': mortality_data['surviving_population'],
                'deaths': mortality_data['deaths'],
                'mortality_rate': mortality_data['mortality_rate']
            })
            
            current_population = mortality_data['surviving_population']
        
        return projections
    
    def validate_parameters(self) -> Tuple[bool, List[str]]:
        """
        Validate mortality model parameters.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if self.rate < 0:
            errors.append("Mortality rate cannot be negative")
        
        if self.rate > 10:
            errors.append("Mortality rate unusually high (>10%)")
        
        if self.frequency not in ['daily', 'weekly']:
            errors.append("Frequency must be 'daily' or 'weekly'")
        
        if self.frequency == 'weekly' and self.rate > 50:
            errors.append("Weekly mortality rate extremely high (>50%)")
        
        return len(errors) == 0, errors

    def get_mortality_rate_for_stage(
        self,
        stage: Optional[str] = None,
        frequency: str = 'daily'
    ) -> float:
        """
        Get mortality rate for a specific lifecycle stage.
        
        Args:
            stage: Lifecycle stage (None uses base rate)
            frequency: 'daily' or 'weekly'
            
        Returns:
            Mortality rate as decimal (not percentage)
        """
        # Check for stage-specific override
        if stage:
            try:
                stage_override = self.model.stage_overrides.get(
                    lifecycle_stage=stage
                )
                if frequency == 'daily':
                    return float(stage_override.daily_rate_percent) / 100
                else:
                    return float(stage_override.weekly_rate_percent) / 100
            except:
                # No override found, use base rate
                pass
        
        # Use base rate
        if self.frequency == frequency:
            return self.rate / 100
        elif frequency == 'daily' and self.frequency == 'weekly':
            # Convert weekly to daily
            return self._weekly_to_daily_rate(self.rate / 100)
        elif frequency == 'weekly' and self.frequency == 'daily':
            # Convert daily to weekly
            return self._daily_to_weekly_rate(self.rate / 100)
        else:
            return self.rate / 100 