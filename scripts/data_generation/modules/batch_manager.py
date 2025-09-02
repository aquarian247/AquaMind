"""
Batch Manager Module

This module handles batch creation, lifecycle stage transitions, and container assignments
for the AquaMind test data generation system.
"""
import random
import datetime
import logging
import traceback
from decimal import Decimal
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db import transaction
from datetime import timedelta
from datetime import date

from apps.batch.models import (
    Species, LifeCycleStage, Batch, BatchContainerAssignment, BatchTransfer,
    MortalityEvent
)
from apps.infrastructure.models import Container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('batch_manager')

class BatchManager:
    """Manages batches and their lifecycle transitions."""
    
    def __init__(self):
        """Initialize the batch manager."""
        logger.info("Initializing BatchManager")
        try:
            self.species = Species.objects.get(name="Atlantic Salmon")
            self.lifecycle_stages = list(LifeCycleStage.objects.filter(species=self.species).order_by('order'))
            
            # Map container types to lifecycle stages
            self.containers_by_stage = self._get_containers_by_stage()
            logger.info(f"BatchManager initialized with {len(self.lifecycle_stages)} lifecycle stages")
            for stage in self.lifecycle_stages:
                logger.debug(f"Lifecycle stage: {stage.name} (order: {stage.order})")
        except Exception as e:
            logger.error(f"Error initializing BatchManager: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _get_containers_by_stage(self):
        """Get containers organized by lifecycle stage."""
        logger.info("Getting containers by lifecycle stage")
        try:
            containers_by_stage = {
                "egg": list(Container.objects.filter(container_type__name='Incubation Tray')),
                "alevin": list(Container.objects.filter(container_type__name='Incubation Tray')),
                "fry": list(Container.objects.filter(container_type__name='Circular Tank Small')),
                "parr": list(Container.objects.filter(container_type__name='Circular Tank Large')),
                "smolt": list(Container.objects.filter(container_type__name='Pre-Transfer Tank')),
                "post_smolt": list(Container.objects.filter(container_type__name='Post-Smolt Tank')),  # Freshwater post-smolt containers
                "adult": list(Container.objects.filter(container_type__name='Sea Cage Large'))
            }
            
            # Log container counts
            for stage, containers in containers_by_stage.items():
                logger.info(f"Found {len(containers)} containers for stage '{stage}'")
            
            return containers_by_stage
        except Exception as e:
            logger.error(f"Error getting containers by stage: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def get_stage_by_name(self, stage_name):
        """Get a lifecycle stage object by name."""
        logger.debug(f"Getting lifecycle stage by name: {stage_name}")
        for stage in self.lifecycle_stages:
            if stage.name == stage_name:
                return stage
        logger.warning(f"Lifecycle stage '{stage_name}' not found")
        return None
    
    def get_stage_duration_days(self, stage_name):
        """Get the expected duration in days for a lifecycle stage."""
        durations = {
            "Egg&Alevin": random.randint(90, 100),
            "Fry": random.randint(90, 100),
            "Parr": random.randint(90, 100),
            "Smolt": random.randint(90, 100),
            "Post-Smolt": random.randint(90, 100),
            "Adult": random.randint(380, 420),
        }
        duration = durations.get(stage_name, 90)
        logger.debug(f"Duration for stage '{stage_name}': {duration} days")
        return duration
    
    @transaction.atomic
    def create_batch(self, start_date=None, initial_population=3600000):
        """
        Create a new batch starting at the egg stage.
        
        Args:
            start_date: Date when the batch starts (defaults to ~900 days ago)
            initial_population: Initial population count (default: 3.6 million eggs)
            
        Returns:
            The created Batch object
        """
        logger.info(f"Creating new batch with {initial_population:,} initial population")
        try:
            if start_date is None:
                # Start approximately 900 days ago to go through the full lifecycle
                start_date = timezone.now().date() - datetime.timedelta(days=900)
            
            # Calculate target harvest date (approximately 850-900 days after start)
            target_harvest_date = start_date + datetime.timedelta(days=random.randint(850, 900))
            logger.info(f"Batch period: {start_date} to {target_harvest_date}")
            
            # Create unique batch number
            year = start_date.year
            # Find the next available batch number
            next_num = 1
            while True:
                candidate = f"B{year}-{next_num:03d}"
                if not Batch.objects.filter(batch_number=candidate).exists():
                    break
                next_num += 1
                if next_num > 9999:  # Safety limit
                    raise ValueError(f"Too many batches for year {year}")

            batch_number = candidate
            logger.info(f"Creating batch with number: {batch_number}")
            
            batch = Batch.objects.create(
                batch_number=batch_number,
                species=self.species,
                lifecycle_stage=self.lifecycle_stages[0],  # Start at Egg stage
                start_date=start_date,
                expected_end_date=target_harvest_date,
                notes=f"Test batch created for data generation on {timezone.now().date()}"
            )
            logger.info(f"Created batch: {batch}")
            
            # Assign to an egg container
            container = random.choice(self.containers_by_stage["egg"])
            logger.info(f"Assigning batch to container: {container.name}")
            self._create_container_assignment(batch, container, initial_population, start_date)
            
            print(f"Created batch {batch.batch_number} with {initial_population:,} eggs starting on {start_date}")
            return batch
        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @transaction.atomic
    def _create_container_assignment(self, batch, container, population_count, assignment_date):
        """Create a container assignment for a batch."""
        logger.info(f"Creating container assignment for batch {batch.batch_number} to container {container.name}")
        try:
            # Calculate realistic weight using TGC-based growth
            avg_weight_g = self._calculate_realistic_weight(batch, assignment_date)
            biomass_kg = Decimal(str(population_count * avg_weight_g / 1000))
            logger.debug(f"Container assignment details: population={population_count:,}, avg_weight={avg_weight_g}g, biomass={biomass_kg}kg")
            
            # Create the assignment
            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=batch.lifecycle_stage,
                population_count=population_count,
                avg_weight_g=avg_weight_g,
                assignment_date=assignment_date
            )
            logger.info(f"Created container assignment: {assignment}")
            
            print(f"  Assigned {population_count:,} fish to {container.name}")
            return assignment
        except Exception as e:
            logger.error(f"Error creating container assignment: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _get_avg_weight_for_stage(self, stage_name):
        """Get the average weight (in grams) for a given lifecycle stage."""
        avg_weights = {
            "egg": 0.001,         # 1g per 1000 eggs (eggs are ~1g total per 1000)
            "alevin": 0.005,      # 5g (alevin are larger than eggs)
            "fry": 10,            # 10g (corrected: 0.5-30g range, target ~10g)
            "parr": 120,          # 120g (corrected: 30-120g range, target ~120g)
            "smolt": 250,         # 250g (corrected: 120-250g range, target ~250g)
            "post_smolt": 400,    # 400g (corrected: 250-400g range, freshwater phase)
            "adult": 6000,        # 6kg (corrected: 400g-6kg range, harvest weight)
        }
        weight = avg_weights.get(stage_name, 1)
        logger.debug(f"Average weight for stage '{stage_name}': {weight}g")
        return weight

    def _calculate_realistic_weight(self, batch, assignment_date, current_date=None):
        """
        Calculate realistic fish weight using TGC-based growth from egg stage.

        Args:
            batch: Batch object
            assignment_date: When this assignment was created
            current_date: Current date for calculation (defaults to today)

        Returns:
            Realistic weight in grams based on growth from egg stage
        """
        if current_date is None:
            from datetime import date
            current_date = date.today()

        try:
            from scripts.data_generation.modules.growth_manager import GrowthManager
            growth_mgr = GrowthManager()

            # Start with egg weight
            current_weight = 0.001  # 1g per 1000 eggs = 0.001g per egg

            start_date = batch.start_date
            total_days = (current_date - start_date).days
            if total_days <= 0:
                return current_weight

            # Find which stage the batch should be in based on age
            days_accumulated = 0
            target_stage = None
            days_in_target_stage = 0

            for stage in self.lifecycle_stages:
                # Adult stage is much longer (450 days vs 90 days for others)
                if stage.name == 'adult':
                    stage_days = 450  # 15 months for adult growth phase
                else:
                    stage_days = 90   # 3 months for other stages

                if days_accumulated + stage_days >= total_days:
                    # This is the current stage
                    target_stage = stage
                    days_in_target_stage = total_days - days_accumulated
                    break
                else:
                    # This stage is complete
                    current_weight = growth_mgr.calculate_tgc_growth(
                        current_weight, stage_days, 10.0, stage.name
                    )
                    days_accumulated += stage_days

            # If we found the target stage, calculate growth in that stage
            if target_stage:
                if days_in_target_stage > 0:
                    current_weight = growth_mgr.calculate_tgc_growth(
                        current_weight, days_in_target_stage, 10.0, target_stage.name
                    )

                # Safety check
                if current_weight > 10000:
                    current_weight = 10000

            return current_weight

        except Exception as e:
            logger.error(f"Error calculating realistic weight: {str(e)}")
            # Fallback to stage-based weight
            return self._get_avg_weight_for_stage(batch.lifecycle_stage.name)
    
    @transaction.atomic
    def process_lifecycle(self, batch, end_date=None):
        """
        Process a batch through its complete lifecycle up to the end_date.
        
        Args:
            batch: The Batch object to process
            end_date: The end date for processing (defaults to today)
        """
        logger.info(f"Processing lifecycle for batch {batch.batch_number}")
        try:
            if end_date is None:
                end_date = timezone.now().date()
            logger.info(f"Processing from {batch.start_date} to {end_date}")
            
            current_date = batch.start_date
            current_stage_index = 0
            
            # Process each lifecycle stage
            while current_date <= end_date and current_stage_index < len(self.lifecycle_stages):
                current_stage = self.lifecycle_stages[current_stage_index]
                logger.info(f"Processing stage: {current_stage.name} (index: {current_stage_index})")
                
                # Calculate stage duration and end date
                stage_duration = self.get_stage_duration_days(current_stage.name)
                stage_end_date = current_date + datetime.timedelta(days=stage_duration)
                logger.info(f"Stage duration: {stage_duration} days, ends on {stage_end_date}")
                
                # Check if we need to transition to the next stage within our processing period
                if stage_end_date <= end_date and current_stage_index < len(self.lifecycle_stages) - 1:
                    next_stage = self.lifecycle_stages[current_stage_index + 1]
                    logger.info(f"Transitioning from {current_stage.name} to {next_stage.name} on {stage_end_date}")
                    
                    try:
                        self._transition_to_next_stage(batch, current_stage, next_stage, stage_end_date)
                        current_stage_index += 1
                        current_date = stage_end_date
                        logger.info(f"Transition successful, now at stage {current_stage_index}: {next_stage.name}")
                    except Exception as e:
                        logger.error(f"Error during stage transition: {str(e)}")
                        logger.error(traceback.format_exc())
                        break
                else:
                    # We've either reached the end date or the final stage
                    logger.info(f"Reached end date or final stage. Current date: {current_date}, End date: {end_date}")
                    break
            
            logger.info(f"Lifecycle processing completed for batch {batch.batch_number}")
            return batch
        except Exception as e:
            logger.error(f"Error processing lifecycle for batch {batch.batch_number}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @transaction.atomic
    def _transition_to_next_stage(self, batch, current_stage, next_stage, transition_date):
        """Transition a batch from one lifecycle stage to the next."""
        logger.info(f"Transitioning batch {batch.batch_number} from {current_stage.name} to {next_stage.name}")
        try:
            # Get active container assignments for this batch
            current_assignments = BatchContainerAssignment.objects.filter(
                batch=batch, 
                is_active=True
            )
            logger.info(f"Found {current_assignments.count()} active container assignments")
            
            current_total_population = 0
            current_total_biomass = 0
            
            # Mark current assignments as inactive
            for assignment in current_assignments:
                current_total_population += assignment.population_count
                current_total_biomass += assignment.biomass_kg
                assignment.is_active = False
                assignment.save()
                logger.debug(f"Marked assignment in {assignment.container.name} as inactive")
            
            # Apply mortality for this transition (1-5%)
            mortality_rate = random.uniform(0.01, 0.05)
            mortality_count = int(current_total_population * mortality_rate)
            # Ensure we multiply Decimals together to avoid TypeError
            mortality_biomass = current_total_biomass * Decimal(str(mortality_rate))
            
            # Create a mortality event
            if mortality_count > 0:
                MortalityEvent.objects.create(
                    batch=batch,
                    event_date=transition_date,
                    count=mortality_count,
                    biomass_kg=mortality_biomass,
                    cause="HANDLING",
                    description=f"Mortality during transition from {current_stage.name} to {next_stage.name}"
                )
                logger.info(f"Created mortality event: {mortality_count:,} fish lost ({mortality_biomass}kg)")
            
            # Calculate new population and biomass after mortality
            new_total_population = current_total_population - mortality_count
            new_total_biomass = current_total_biomass - mortality_biomass
            
            # Calculate new average weight (growth during transition)
            current_avg_weight = (current_total_biomass * 1000) / current_total_population if current_total_population > 0 else 0
            new_avg_weight = self._get_avg_weight_for_stage(next_stage.name)
            logger.info(f"Weight transition: {current_avg_weight}g -> {new_avg_weight}g")
            
            # Recalculate biomass based on new weight
            new_total_biomass = Decimal(str(new_total_population * new_avg_weight / 1000))
            
            # Update the batch with new stage, population and biomass
            batch.lifecycle_stage = next_stage
            batch.save()
            logger.info(f"Updated batch: stage={next_stage.name}, population={new_total_population:,}, biomass={new_total_biomass}kg")
            
            # If this is the transition to the sea (Adult stage), distribute across multiple sea pens
            if next_stage.name == "Adult":
                sea_pens = self.containers_by_stage["Adult"]
                logger.info(f"Transitioning to sea pens - distributing across {len(sea_pens)} potential pens")
                self._distribute_to_sea_pens(batch, sea_pens, new_total_population, transition_date)
            else:
                # For other stages, get appropriate containers and move fish there
                appropriate_containers = self.containers_by_stage[next_stage.name]
                
                if not appropriate_containers:
                    logger.error(f"No appropriate containers found for stage: {next_stage.name}")
                    raise ValueError(f"No appropriate containers found for stage: {next_stage.name}")
                
                # Select a random container of appropriate type
                container = random.choice(appropriate_containers)
                logger.info(f"Selected container for next stage: {container.name}")
                
                # Create new assignment in new container
                self._create_container_assignment(
                    batch=batch,
                    container=container,
                    population_count=new_total_population,
                    assignment_date=transition_date
                )
            
            logger.info(f"Successfully transitioned batch {batch.batch_number} to {next_stage.name}")
            return batch
        except Exception as e:
            logger.error(f"Error transitioning to next stage: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    @transaction.atomic
    def _distribute_to_sea_pens(self, batch, sea_pens, total_population, assignment_date):
        """Distribute a batch across multiple sea pens."""
        logger.info(f"Distributing batch {batch.batch_number} across sea pens. Total population: {total_population:,}")
        try:
            # Use 3-8 sea pens for distribution
            num_pens = min(random.randint(3, 8), len(sea_pens))
            selected_pens = random.sample(sea_pens, num_pens)
            logger.info(f"Selected {num_pens} sea pens for distribution")
            
            # Distribute population across pens
            populations = self._distribute_population(total_population, num_pens)
            
            # Create assignments for each pen
            for i, pen in enumerate(selected_pens):
                pop_count = populations[i]
                logger.info(f"Assigning {pop_count:,} fish to pen {pen.name}")
                self._create_container_assignment(
                    batch=batch,
                    container=pen,
                    population_count=pop_count,
                    assignment_date=assignment_date
                )
            
            logger.info(f"Successfully distributed batch across {num_pens} sea pens")
        except Exception as e:
            logger.error(f"Error distributing to sea pens: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _distribute_population(self, total, num_groups):
        """Distribute a total population across a number of groups."""
        try:
            base_size = total // num_groups
            remainder = total % num_groups
            
            # Create an array of group sizes
            populations = [base_size] * num_groups
            
            # Distribute the remainder
            for i in range(remainder):
                populations[i] += 1
            
            # Add some randomness to make it more realistic
            for i in range(num_groups):
                variance = int(populations[i] * random.uniform(-0.05, 0.05))
                populations[i] += variance
            
            # Adjust to ensure the total is still correct
            current_total = sum(populations)
            adjustment = total - current_total
            
            if adjustment != 0:
                idx = 0
                step = 1 if adjustment > 0 else -1
                
                while adjustment != 0:
                    populations[idx] += step
                    adjustment -= step
                    idx = (idx + 1) % num_groups
            
            logger.debug(f"Distributed population: {populations}, total: {sum(populations)}")
            return populations
        except Exception as e:
            logger.error(f"Error distributing population: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @transaction.atomic
    def generate_current_batches(self, start_date: date, end_date: date, num_batches: int = 10):
        """Generate new batches for the current year."""
        batches = []
        interval = (end_date - start_date).days // num_batches
        current_date = start_date
        
        for i in range(num_batches):
            batch_date = current_date + timedelta(days=i * interval)
            new_batch = self.create_batch(batch_date)
            if new_batch:
                batches.append(new_batch)
        
        logger.info(f"Generated {len(batches)} new batches for current year")
        return batches

    @transaction.atomic
    def process_recent_harvests(self, start_date: date, end_date: date):
        """Process recent harvests for mature batches."""
        harvests = []
        mature_batches = Batch.objects.filter(
            lifecycle_stage__name='Adult',
            expected_end_date__range=(start_date, end_date),
            actual_end_date__isnull=True
        )
        
        for batch in mature_batches:
            # Simulate harvest
            batch.actual_end_date = batch.expected_end_date
            batch.status = 'HARVESTED'
            batch.save()
            harvests.append(batch)
            logger.info(f"Processed harvest for batch {batch.batch_number}")
        
        return harvests
