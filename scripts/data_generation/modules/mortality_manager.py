"""
Mortality Manager Module

This module handles mortality event generation for the AquaMind test data.
It creates realistic mortality patterns with daily recording.
"""
import random
import datetime
import logging
import traceback
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.batch.models import BatchContainerAssignment, MortalityEvent

# Set up logging
logger = logging.getLogger('mortality_manager')

class MortalityManager:
    """Manages mortality-related data generation."""
    
    def __init__(self):
        """Initialize the mortality manager."""
        logger.info("Initializing MortalityManager")
        
        # Base mortality rates by lifecycle stage (% per day)
        self.base_mortality_rates = {
            "Egg&Alevin": (0.2, 0.5),     # 0.2-0.5% daily mortality
            "Fry": (0.05, 0.15),          # 0.05-0.15% daily mortality
            "Parr": (0.03, 0.1),          # 0.03-0.1% daily mortality
            "Smolt": (0.02, 0.08),        # 0.02-0.08% daily mortality
            "Post-Smolt": (0.01, 0.05),   # 0.01-0.05% daily mortality
            "Adult": (0.005, 0.03)        # 0.005-0.03% daily mortality
        }
        
        # Mortality causes mapped to the model's MORTALITY_CAUSE_CHOICES
        self.mortality_causes = {
            "Egg&Alevin": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "UNKNOWN"
            ],
            "Fry": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "UNKNOWN"
            ],
            "Parr": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "PREDATION",
                "UNKNOWN"
            ],
            "Smolt": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "UNKNOWN"
            ],
            "Post-Smolt": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "PREDATION",
                "UNKNOWN"
            ],
            "Adult": [
                "DISEASE",
                "ENVIRONMENTAL",
                "HANDLING",
                "PREDATION",
                "UNKNOWN",
                "OTHER"
            ]
        }
        
        # Description templates for different causes
        self.cause_descriptions = {
            "DISEASE": ["Bacterial infection", "Viral infection", "Fungal infection", "Parasites", "Sea lice"],
            "ENVIRONMENTAL": ["Water quality issues", "Algal bloom", "Oxygen deficiency", "Temperature stress"],
            "HANDLING": ["Handling stress", "Transfer related", "Grading related"],
            "PREDATION": ["Predation by birds", "Predation by marine mammals"],
            "UNKNOWN": ["Undetermined cause", "Natural causes"],
            "OTHER": ["Equipment failure", "Feed quality issue"]
        }
        
        logger.info("MortalityManager initialized")
    
    def get_daily_mortality_rate(self, stage_name):
        """Get the daily mortality rate range for a specific lifecycle stage."""
        rate = self.base_mortality_rates.get(stage_name, (0.01, 0.05))
        logger.debug(f"Daily mortality rate for {stage_name}: {rate}")
        return rate
    
    def get_mortality_cause(self, stage_name):
        """Get a random mortality cause for a specific lifecycle stage."""
        causes = self.mortality_causes.get(stage_name, ["UNKNOWN"])
        weights = [3 if cause == "UNKNOWN" else 1 for cause in causes]  # Higher weight for "UNKNOWN"
        cause = random.choices(causes, weights=weights, k=1)[0]
        logger.debug(f"Selected mortality cause for {stage_name}: {cause}")
        return cause
    
    def get_cause_description(self, cause):
        """Get a random description for a mortality cause."""
        descriptions = self.cause_descriptions.get(cause, ["Undetermined"])
        description = random.choice(descriptions)
        logger.debug(f"Selected description for cause {cause}: {description}")
        return description
    
    @transaction.atomic
    def generate_mortality_events(self, start_date, end_date=None):
        """
        Generate daily mortality events for all active batch container assignments.
        
        Args:
            start_date: The date to start generating mortality from
            end_date: The end date (defaults to today)
            
        Returns:
            Total number of mortality events generated
        """
        logger.info(f"Generating mortality events from {start_date} to {end_date or 'today'}")
        try:
            if end_date is None:
                end_date = timezone.now().date()
            
            # Get all active assignments in this period
            logger.info("Querying for batch container assignments")
            try:
                assignments = BatchContainerAssignment.objects.filter(
                    assignment_date__lte=end_date,
                    is_active=True
                ).select_related('batch', 'batch__lifecycle_stage')
                
                logger.info(f"Found {assignments.count()} active batch container assignments")
                
                # Check if any assignments exist
                if assignments.count() == 0:
                    logger.warning("No active batch container assignments found for mortality events")
                    print("WARNING: No active batch container assignments found for mortality events")
                    return 0
            except Exception as e:
                logger.error(f"Error querying batch container assignments: {str(e)}")
                logger.error(traceback.format_exc())
                return 0
            
            # Process each day in the range
            current_date = start_date
            total_events = 0
            
            while current_date <= end_date:
                logger.debug(f"Processing mortality for date: {current_date}")
                
                # Process each assignment
                for assignment in assignments:
                    try:
                        # Skip if assignment isn't active on this date (belt and suspenders check)
                        if (assignment.assignment_date > current_date or 
                            (hasattr(assignment, 'removal_date') and 
                             assignment.removal_date is not None and 
                             assignment.removal_date < current_date)):
                            continue
                        
                        # Get stage information
                        stage_name = assignment.batch.lifecycle_stage.name
                        logger.debug(f"Processing assignment for batch {assignment.batch.batch_number}, stage {stage_name}")
                        
                        # Get mortality rate for this stage
                        min_rate, max_rate = self.get_daily_mortality_rate(stage_name)
                        daily_rate = random.uniform(min_rate, max_rate)
                        
                        # Add occasional spikes (5% chance of 2-5x mortality)
                        if random.random() < 0.05:
                            spike_factor = random.uniform(2, 5)
                            daily_rate *= spike_factor
                            logger.debug(f"Mortality spike: {spike_factor}x normal rate")
                            
                            # Cap maximum daily mortality at 3%
                            daily_rate = min(daily_rate, 3.0)
                        
                        logger.debug(f"Daily mortality rate: {daily_rate}%")
                        
                        # Calculate mortality count
                        population = assignment.batch.population_count
                        mortality_count = int(population * daily_rate / 100)
                        
                        # Ensure at least 1 mortality if population > 100
                        if population > 100 and mortality_count == 0:
                            mortality_count = 1
                        
                        # Skip if no mortality
                        if mortality_count <= 0:
                            logger.debug("No mortality calculated for this day, skipping")
                            continue
                        
                        # Calculate biomass lost - assuming average fish weight
                        avg_weight_g = assignment.batch.biomass_kg * 1000 / assignment.batch.population_count if assignment.batch.population_count > 0 else 0
                        biomass_kg = Decimal(str(mortality_count * avg_weight_g / 1000))
                        logger.debug(f"Calculated mortality: {mortality_count} fish, {biomass_kg}kg biomass")
                        
                        # Get a cause for this mortality
                        cause = self.get_mortality_cause(stage_name)
                        description = self.get_cause_description(cause)
                        
                        # Create the mortality event
                        try:
                            event = MortalityEvent.objects.create(
                                batch=assignment.batch,
                                event_date=current_date,
                                count=mortality_count,
                                biomass_kg=biomass_kg,
                                cause=cause,
                                description=f"{description} - Auto-generated event"
                            )
                            logger.debug(f"Created mortality event: {event}")
                            
                            # Update batch population and biomass
                            assignment.batch.population_count -= mortality_count
                            assignment.batch.biomass_kg -= biomass_kg
                            assignment.batch.save()
                            logger.debug(f"Updated batch: {assignment.batch.population_count} fish remaining")
                            
                            # Update assignment population
                            assignment.population_count -= mortality_count
                            assignment.biomass_kg -= biomass_kg
                            assignment.save()
                            logger.debug(f"Updated assignment: {assignment.population_count} fish remaining")
                            
                            total_events += 1
                        except Exception as e:
                            logger.error(f"Error creating mortality event: {str(e)}")
                            logger.error(traceback.format_exc())
                    except Exception as e:
                        logger.error(f"Error processing assignment {assignment.id}: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Continue with next assignment
                
                # Move to next day
                current_date += datetime.timedelta(days=1)
            
            logger.info(f"Generated {total_events} mortality events")
            print(f"Generated {total_events:,} mortality events from {start_date} to {end_date}")
            return total_events
            
        except Exception as e:
            logger.error(f"Error in generate_mortality_events: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
