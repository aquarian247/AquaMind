"""
Operations Generator for AquaMind Data Generation

Handles creation of daily operational data including feeding, growth, and mortality.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Batch, BatchContainerAssignment, GrowthSample,
    MortalityEvent, BatchTransfer
)
from apps.inventory.models import (
    Feed, FeedStock, FeedingEvent
)
from apps.health.models import Treatment, VaccinationType
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class OperationsGenerator:
    """
    Generates operational data including:
    - Daily feeding events
    - Growth samples (weekly)
    - Mortality events (stage-appropriate)
    - Batch transfers with grace periods
    - Initial vaccinations
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the operations generator.
        
        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run
        self.created_objects = {
            'feed_events': 0,
            'growth_samples': 0,
            'mortality_events': 0,
            'transfers': 0,
            'vaccinations': 0
        }
        
        # Get or create system user
        if not self.dry_run:
            self.system_user, _ = User.objects.get_or_create(
                username='data_generator',
                defaults={
                    'email': 'generator@aquamind.com',
                    'first_name': 'Data',
                    'last_name': 'Generator',
                    'is_staff': False,
                    'is_active': True
                }
            )
            
            # Ensure feed types exist
            self._ensure_feed_types()
    
    def _ensure_feed_types(self):
        """Ensure all feed types are defined in the database."""
        
        # Create standard feed types matching what operations expects
        # Based on FCR 1.2 and 100,000 tons production = 120,000 tons feed/year
        feed_types = {
            'Starter 0.5MM': {'pellet': 0.5, 'protein': 55, 'fat': 18, 'stages': ['fry']},
            'Starter 1.0MM': {'pellet': 1.0, 'protein': 52, 'fat': 20, 'stages': ['parr']},
            'Grower 2.0MM': {'pellet': 2.0, 'protein': 48, 'fat': 22, 'stages': ['smolt']},
            'Grower 3.0MM': {'pellet': 3.0, 'protein': 45, 'fat': 24, 'stages': ['post_smolt']},
            'Finisher 4.5MM': {'pellet': 4.5, 'protein': 42, 'fat': 28, 'stages': ['grow_out']},
            'Finisher 7.0MM': {'pellet': 7.0, 'protein': 40, 'fat': 30, 'stages': ['harvest']},
        }
        
        for feed_name, specs in feed_types.items():
            Feed.objects.get_or_create(
                name=feed_name,
                defaults={
                    'pellet_size_mm': Decimal(str(specs['pellet'])),
                    'protein_percentage': Decimal(str(specs['protein'])),
                    'fat_percentage': Decimal(str(specs['fat'])),
                    'carbohydrate_percentage': Decimal(str(100 - specs['protein'] - specs['fat'] - 5)),  # Rest minus ash
                    'brand': 'BioMar',
                    'size_category': 'starter' if 'Starter' in feed_name else 'grower' if 'Grower' in feed_name else 'finisher',
                    'is_active': True,
                    'description': f"{feed_name} - {specs['stages'][0]} stage feed"
                }
            )
    
    def generate_daily_operations(self, current_date: date) -> Dict[str, int]:
        """
        Generate all daily operational data for active batches.
        
        Args:
            current_date: Date to generate operations for
            
        Returns:
            Dictionary with counts of created objects
        """
        if self.dry_run:
            logger.info(f"Would generate daily operations for {current_date}")
            return self.created_objects
        
        # Get active batches with current assignments
        active_assignments = BatchContainerAssignment.objects.filter(
            departure_date__isnull=True,
            is_active=True,
            batch__status='ACTIVE'
        ).select_related('batch', 'container')
        
        logger.debug(f"Processing {active_assignments.count()} active batch assignments for {current_date}")
        
        for assignment in active_assignments:
            # Generate daily feeding
            self._generate_feeding_event(assignment, current_date)
            
            # Generate weekly growth sample (Mondays)
            if current_date.weekday() == 0:  # Monday
                self._generate_growth_sample(assignment, current_date)
            
            # Generate mortality events (probabilistic)
            self._generate_mortality_event(assignment, current_date)
            
            # Check for vaccinations (smolt stage)
            if assignment.lifecycle_stage.name == 'smolt':
                self._check_vaccination(assignment, current_date)
        
        return self.created_objects
    
    def _generate_feeding_event(self, assignment: BatchContainerAssignment, feeding_date: date) -> bool:
        """Generate daily feeding event for a batch."""
        
        if assignment.population_count <= 0:
            return False
        
        # Determine feed type based on lifecycle stage
        feed_type_map = {
            'fry': 'Starter 0.5MM',
            'parr': 'Starter 1.0MM',
            'smolt': 'Grower 2.0MM',
            'post_smolt': 'Grower 3.0MM',
            'grow_out': 'Finisher 4.5MM'
        }
        
        feed_name = feed_type_map.get(assignment.lifecycle_stage.name)
        if not feed_name:
            return False  # No feeding for eggs/alevin
        
        try:
            feed = Feed.objects.get(name=feed_name)
        except Feed.DoesNotExist:
            logger.warning(f"Feed type {feed_name} not found")
            return False
        
        # Calculate feed amount based on biomass and feeding rate
        feeding_rate = self._get_feeding_rate(assignment.lifecycle_stage.name)
        daily_feed_kg = float(assignment.biomass_kg) * feeding_rate / 100
        
        # Add some variation
        daily_feed_kg *= random.uniform(0.9, 1.1)
        
        # Create feeding event record
        FeedingEvent.objects.create(
            batch=assignment.batch,
            batch_assignment=assignment,
            container=assignment.container,
            feed=feed,
            feeding_date=feeding_date,
            feeding_time=datetime.now().time(),
            amount_kg=Decimal(str(daily_feed_kg)),
            batch_biomass_kg=assignment.biomass_kg,
            method='AUTOMATIC',  # Using automatic feeders
            notes=f"Daily feeding for batch {assignment.batch.batch_number} - {feeding_rate}% of body weight",
            recorded_by=self.system_user
        )
        
        self.created_objects['feed_events'] += 1
        
        # Update batch biomass (simplified growth)
        growth_factor = 1.002  # 0.2% daily growth
        assignment.biomass_kg *= Decimal(str(growth_factor))
        assignment.avg_weight_g *= Decimal(str(growth_factor))
        assignment.save()
        
        return True
    
    def _get_feeding_rate(self, lifecycle_stage: str) -> float:
        """Get feeding rate as percentage of body weight."""
        
        base_rates = {
            'fry': 8.0,
            'parr': 6.0,
            'smolt': 4.0,
            'post_smolt': 2.5,
            'grow_out': 1.5
        }
        
        return base_rates.get(lifecycle_stage, 2.0)
    
    def _generate_growth_sample(self, assignment: BatchContainerAssignment, sample_date: date) -> bool:
        """Generate weekly growth sample."""
        
        if assignment.population_count <= 0:
            return False
        
        # Sample size (typically 100 fish or 0.1% of population)
        sample_size = min(100, max(10, int(assignment.population_count * 0.001)))
        
        # Calculate sample statistics with some variation
        avg_weight = float(assignment.avg_weight_g)
        weight_cv = random.uniform(8, 15)  # Coefficient of variation 8-15%
        
        # Length estimation (simplified allometric relationship)
        avg_length = (avg_weight ** 0.33) * 3.5  # Rough approximation
        length_cv = random.uniform(5, 10)
        
        # Create growth sample
        final_avg_weight = Decimal(str(avg_weight * random.uniform(0.98, 1.02)))
        std_dev_weight = final_avg_weight * Decimal(str(weight_cv / 100))
        std_dev_length = Decimal(str(avg_length)) * Decimal(str(length_cv / 100))
        
        GrowthSample.objects.create(
            assignment=assignment,
            sample_date=sample_date,
            sample_size=sample_size,
            avg_weight_g=final_avg_weight,
            avg_length_cm=Decimal(str(avg_length)),
            std_deviation_weight=std_dev_weight,
            std_deviation_length=std_dev_length,
            min_weight_g=final_avg_weight - std_dev_weight * 2,
            max_weight_g=final_avg_weight + std_dev_weight * 2,
            condition_factor=Decimal(str(random.uniform(0.9, 1.2))),
            notes=f"Weekly growth sample for {assignment.batch.batch_number}"
        )
        
        self.created_objects['growth_samples'] += 1
        return True
    
    def _generate_mortality_event(self, assignment: BatchContainerAssignment, event_date: date) -> bool:
        """Generate mortality events based on stage-appropriate rates."""
        
        if assignment.population_count <= 0:
            return False
        
        # Get base mortality rate for stage
        base_rate = GP.BASE_MORTALITY_RATES.get(assignment.lifecycle_stage.name, 1.0)
        
        # Convert to daily rate
        if assignment.lifecycle_stage.name in ['post_smolt', 'grow_out']:
            # These are monthly rates
            daily_rate = base_rate / 30
        else:
            # These are cumulative stage rates
            stage_duration = GP.STAGE_DURATIONS.get(assignment.lifecycle_stage.name, (90, 90))[0]
            daily_rate = base_rate / stage_duration
        
        # Apply stochastic variation
        if random.random() < daily_rate / 100:
            # Mortality event occurs
            mortality_percent = random.uniform(daily_rate * 0.5, daily_rate * 2)
            mortality_count = int(assignment.population_count * mortality_percent / 100)
            
            if mortality_count > 0:
                # Determine cause
                is_freshwater = assignment.lifecycle_stage.name in ['egg', 'alevin', 'fry', 'parr', 'smolt']
                causes = GP.MORTALITY_CAUSES['freshwater' if is_freshwater else 'seawater']
                cause = random.choices(list(causes.keys()), weights=list(causes.values()))[0]
                
                # Create mortality event
                avg_weight = float(assignment.avg_weight_g) if assignment.avg_weight_g else 100
                biomass_lost = Decimal(str(mortality_count * avg_weight / 1000))  # Convert to kg
                MortalityEvent.objects.create(
                    batch=assignment.batch,
                    event_date=event_date,
                    count=mortality_count,
                    biomass_kg=biomass_lost,
                    cause=cause,
                    description=f"Daily mortality event - {cause.lower()}"
                )
                
                # Update population
                assignment.population_count -= mortality_count
                assignment.biomass_kg *= Decimal(str(1 - mortality_percent / 100))
                assignment.save()
                
                # Batch model doesn't have current_count field anymore
                # Population is tracked through assignments
                
                self.created_objects['mortality_events'] += 1
                return True
        
        return False
    
    def _check_vaccination(self, assignment: BatchContainerAssignment, check_date: date) -> bool:
        """Check and apply vaccination for smolt stage."""
        
        # Check if already vaccinated
        existing_vaccination = Treatment.objects.filter(
            batch=assignment.batch,
            treatment_type='vaccination',
            treatment_date__date__lte=check_date
        ).exists()
        
        if existing_vaccination:
            return False
        
        # Vaccinate after 30-60 days in smolt stage
        days_in_stage = (check_date - assignment.assignment_date).days
        
        if days_in_stage >= random.randint(30, 60):
            # Get or create vaccination type
            vaccine_type, _ = VaccinationType.objects.get_or_create(
                name='Alpha Ject 6-2',
                defaults={
                    'manufacturer': 'Pharmaq',
                    'dosage': '0.1ml per fish',
                    'description': 'Multivalent vaccine for salmon'
                }
            )
            
            # Create vaccination treatment
            Treatment.objects.create(
                batch=assignment.batch,
                container=assignment.container,
                batch_assignment=assignment,
                user=self.system_user,
                treatment_date=datetime.combine(check_date, datetime.min.time()),
                treatment_type='vaccination',
                vaccination_type=vaccine_type,
                description=f'Pre-seawater transfer vaccination for {assignment.population_count} fish',
                dosage='0.1ml per fish',
                duration_days=1,
                withholding_period_days=0,
                outcome='successful'
            )
            
            self.created_objects['vaccinations'] += 1
            
            # Small mortality from vaccination stress (0.5%)
            stress_mortality = int(assignment.population_count * 0.005)
            if stress_mortality > 0:
                avg_weight = float(assignment.avg_weight_g) if assignment.avg_weight_g else 100
                biomass_lost = Decimal(str(stress_mortality * avg_weight / 1000))  # Convert to kg
                MortalityEvent.objects.create(
                    batch=assignment.batch,
                    event_date=check_date,
                    count=stress_mortality,
                    biomass_kg=biomass_lost,
                    cause='HANDLING',
                    description='Vaccination stress mortality'
                )
                
                assignment.population_count -= stress_mortality
                assignment.biomass_kg *= Decimal(str(1 - 0.005))  # Adjust biomass
                assignment.save()
            
            return True
        
        return False
    
    def process_batch_transfers(self, current_date: date) -> int:
        """
        Process batch transfers between lifecycle stages with grace periods.
        
        Args:
            current_date: Date to check for transfers
            
        Returns:
            Number of transfers processed
        """
        if self.dry_run:
            return 0
        
        transfers_processed = 0
        
        # This is handled by the batch generator's progress_lifecycle_stages method
        # But we can track the transfers here
        
        # Find recent transfers to log
        recent_transfers = BatchTransfer.objects.filter(
            transfer_date=current_date
        )
        
        for transfer in recent_transfers:
            self.created_objects['transfers'] += 1
            transfers_processed += 1
        
        return transfers_processed
    
    def get_summary(self) -> str:
        """
        Get a summary of generated operational data.
        
        Returns:
            String summary of created objects
        """
        summary = "\n=== Operations Generation Summary ===\n"
        summary += f"Feed Events: {self.created_objects['feed_events']:,}\n"
        summary += f"Growth Samples: {self.created_objects['growth_samples']:,}\n"
        summary += f"Mortality Events: {self.created_objects['mortality_events']:,}\n"
        summary += f"Batch Transfers: {self.created_objects['transfers']:,}\n"
        summary += f"Vaccinations: {self.created_objects['vaccinations']:,}\n"
        
        return summary
