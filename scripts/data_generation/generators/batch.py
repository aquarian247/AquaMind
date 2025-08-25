"""
Batch Generator for AquaMind Data Generation

Handles creation of batches with staggered starts and lifecycle management.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime, timedelta

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Species, LifeCycleStage, Batch, BatchContainerAssignment,
    BatchComposition
)
from apps.infrastructure.models import Container, ContainerType
from scripts.data_generation.config.generation_params import GenerationParameters as GP

logger = logging.getLogger(__name__)
User = get_user_model()


class BatchGenerator:
    """
    Generates batch data including:
    - Initial batch creation with staggered starts
    - Egg source assignments (60% external, 40% internal)
    - Container assignments
    - Lifecycle stage progressions
    - Population initialization
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the batch generator.
        
        Args:
            dry_run: If True, only log actions without database changes
        """
        self.dry_run = dry_run
        self.created_batches = []
        self.created_assignments = []
        
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
            
            # Get or create Atlantic Salmon species
            self.species, _ = Species.objects.get_or_create(
                name='Atlantic Salmon',
                defaults={
                    'scientific_name': 'Salmo salar',
                    'description': 'Primary farmed species'
                }
            )
    
    def generate_initial_batches(self, start_date: date, num_batches: int = 8) -> Dict[str, int]:
        """
        Generate initial batches with staggered starts for Year 1.
        
        Based on Bakkafrost production model:
        - 100,000 tons/year = ~10 batches harvested/year
        - 900-day cycle = 25 active batches in pipeline
        - New batch every ~36 days for steady state
        
        Args:
            start_date: Starting date for batch creation
            num_batches: Number of initial batches to create (8 for realistic start)
            
        Returns:
            Dictionary with counts of created objects
        """
        logger.info(f"Generating {num_batches} initial batches...")
        
        if self.dry_run:
            logger.info(f"Would create {num_batches} batches")
            return {'batches': 0, 'assignments': 0}
        
        with transaction.atomic():
            # Create batches with realistic spacing - every 30-40 days
            for i in range(num_batches):
                # Space batches ~36 days apart (matching production needs)
                days_offset = i * 36 + random.randint(-3, 3)
                batch_start_date = start_date + timedelta(days=days_offset)
                
                # Create the batch
                batch = self._create_batch(batch_start_date, i + 1)
                
                if batch:
                    self.created_batches.append(batch)
                    
                    # Create initial container assignment
                    assignment = self._create_initial_assignment(batch, batch_start_date)
                    if assignment:
                        self.created_assignments.append(assignment)
        
        logger.info(f"Created {len(self.created_batches)} batches with {len(self.created_assignments)} assignments")
        
        return {
            'batches': len(self.created_batches),
            'assignments': len(self.created_assignments)
        }
    
    def _create_batch(self, start_date: date, batch_number: int) -> Optional[Batch]:
        """Create a single batch with appropriate parameters."""
        
        # Generate batch name following company convention
        year = start_date.year
        week = start_date.isocalendar()[1]
        batch_code = f"{GP.BATCH_NAME_PREFIX}{year}{week:02d}{batch_number:02d}"
        
        # Check if batch already exists
        if Batch.objects.filter(batch_number=batch_code).exists():
            logger.debug(f"Batch {batch_code} already exists, skipping")
            return None
        
        # Generate egg count with normal distribution
        egg_count = int(random.gauss(GP.EGG_COUNT_MEAN, GP.EGG_COUNT_STDDEV))
        egg_count = max(GP.EGG_COUNT_MIN, min(GP.EGG_COUNT_MAX, egg_count))
        
        # Determine egg source (60% external, 40% internal)
        is_external = random.random() < GP.EXTERNAL_EGG_PROBABILITY
        
        # Select genetic strain
        genetic_strains = ['AquaGen Supreme', 'SalmoBreed Plus', 'Benchmark Genetics', 'Internal Line A']
        genetic_strain = random.choice(genetic_strains)
        
        # Get or create initial lifecycle stage (egg)
        egg_stage, _ = LifeCycleStage.objects.get_or_create(
            name='egg',
            species=self.species,
            defaults={
                'order': 1,
                'description': 'Egg stage'
            }
        )
        
        # Create the batch
        batch = Batch.objects.create(
            batch_number=batch_code,
            species=self.species,
            lifecycle_stage=egg_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            start_date=start_date,
            expected_end_date=start_date + timedelta(days=540),  # ~18 months
            notes=f"Source: {'External' if is_external else 'Internal'}, Strain: {genetic_strain}, Initial count: {egg_count:,}"
        )
        
        logger.debug(f"Created batch {batch.batch_number} with {egg_count:,} eggs")
        
        return batch
    
    def _create_initial_assignment(self, batch: Batch, assignment_date: date) -> Optional[BatchContainerAssignment]:
        """Create initial container assignment for a batch."""
        
        # Find available incubation trays for eggs
        incubation_type = ContainerType.objects.get(name='Incubation Tray')
        
        # Get containers that are incubation trays
        available_containers = Container.objects.filter(
            container_type=incubation_type,
            active=True
        )
        
        if not available_containers.exists():
            logger.warning(f"No available incubation trays for batch {batch.batch_number}")
            return None
        
        # Check which containers are currently occupied
        occupied_containers = BatchContainerAssignment.objects.filter(
            departure_date__isnull=True,
            container__in=available_containers
        ).values_list('container_id', flat=True)
        
        # Find truly available containers
        free_containers = available_containers.exclude(id__in=occupied_containers)
        
        if not free_containers.exists():
            logger.warning(f"All incubation trays are occupied for batch {batch.batch_number}")
            # In production, we might want to handle this differently
            # For now, just use any container
            free_containers = available_containers
        
        # Extract egg count from batch notes (temporary solution)
        import re
        match = re.search(r'Initial count: ([\d,]+)', batch.notes)
        if match:
            egg_count = int(match.group(1).replace(',', ''))
        else:
            egg_count = 3_250_000  # Default if not found
        
        # Select containers needed based on capacity
        # Incubation trays typically hold 50,000-100,000 eggs
        eggs_per_tray = 75000
        num_trays_needed = (egg_count + eggs_per_tray - 1) // eggs_per_tray
        
        selected_containers = list(free_containers[:num_trays_needed])
        
        if not selected_containers:
            logger.error(f"Could not find containers for batch {batch.batch_number}")
            return None
        
        # Create assignments for each container
        assignments = []
        eggs_remaining = egg_count
        
        for container in selected_containers:
            eggs_in_container = min(eggs_per_tray, eggs_remaining)
            
            # Get egg lifecycle stage
            egg_stage = batch.lifecycle_stage
            
            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=egg_stage,
                assignment_date=assignment_date,
                population_count=eggs_in_container,
                biomass_kg=Decimal(str(eggs_in_container * GP.INITIAL_WEIGHTS['egg'] / 1000)),
                avg_weight_g=Decimal(str(GP.INITIAL_WEIGHTS['egg'])),
                is_active=True
            )
            
            assignments.append(assignment)
            eggs_remaining -= eggs_in_container
            
            if eggs_remaining <= 0:
                break
        
        logger.debug(f"Created {len(assignments)} container assignments for batch {batch.batch_number}")
        
        return assignments[0] if assignments else None
    
    def create_batch_for_date(self, current_date: date) -> Optional[Batch]:
        """
        Determine if a new batch should be created for the given date.
        
        Args:
            current_date: The date to check for batch creation
            
        Returns:
            Created batch or None
        """
        # Get current active batch count
        active_batches = Batch.objects.filter(
            status='ACTIVE',
            start_date__lte=current_date
        ).count()
        
        # Check if we need more batches
        # Based on Bakkafrost model: 25 active batches (10/year × 2.5 year cycle)
        target_active_batches = 25
        
        if active_batches >= target_active_batches:
            return None  # At capacity
        
        # Calculate days since last batch creation
        last_batch = Batch.objects.order_by('-start_date').first()
        days_since_last = 0
        if last_batch:
            days_since_last = (current_date - last_batch.start_date).days
            
        # Create batch roughly every 36 days
        if days_since_last < 30:
            create_probability = 0  # Too soon
        elif days_since_last >= 36:
            create_probability = 0.5  # 50% chance after 36 days
        else:
            create_probability = 0.1  # 10% chance between 30-36 days
        
        # Apply seasonal factors (higher in Q1/Q2)
        month = current_date.month
        seasonal_multipliers = {
            1: 1.3, 2: 1.2, 3: 1.1, 4: 0.9,
            5: 0.8, 6: 0.7, 7: 0.7, 8: 0.8,
            9: 0.9, 10: 1.0, 11: 1.1, 12: 1.2
        }
        
        create_probability *= seasonal_multipliers.get(month, 1.0)
        
        # Tweak create_probability based on active_batches vs target
        if active_batches > target_active_batches:
            create_probability = 0 # Ensure no new batches if already at capacity
        elif active_batches < target_active_batches:
            create_probability = 0.8 # Increase probability if below target
        
        # Random decision
        if random.random() < create_probability:
            # Generate batch number for the day
            existing_today = Batch.objects.filter(
                start_date=current_date
            ).count()
            
            batch = self._create_batch(current_date, existing_today + 1)
            if batch:
                assignment = self._create_initial_assignment(batch, current_date)
                logger.info(f"Created new batch {batch.batch_number} for {current_date}")
                return batch
        
        return None
    
    def progress_lifecycle_stages(self, current_date: date) -> int:
        """
        Progress batches through lifecycle stages based on time and conditions.
        
        Args:
            current_date: Current date for processing
            
        Returns:
            Number of batches progressed
        """
        progressed_count = 0
        
        # Define stage progression rules using correct durations from config
        # Calculate average duration from GP.STAGE_DURATIONS
        stage_progression = {
            'egg': ('alevin', (GP.STAGE_DURATIONS['egg'][0] + GP.STAGE_DURATIONS['egg'][1]) // 2),
            'alevin': ('fry', (GP.STAGE_DURATIONS['alevin'][0] + GP.STAGE_DURATIONS['alevin'][1]) // 2),
            'fry': ('parr', (GP.STAGE_DURATIONS['fry'][0] + GP.STAGE_DURATIONS['fry'][1]) // 2),
            'parr': ('smolt', (GP.STAGE_DURATIONS['smolt'][0] + GP.STAGE_DURATIONS['smolt'][1]) // 2),
            'smolt': ('post_smolt', (GP.STAGE_DURATIONS['post_smolt'][0] + GP.STAGE_DURATIONS['post_smolt'][1]) // 2),
            'post_smolt': ('grow_out', (GP.STAGE_DURATIONS['grow_out'][0] + GP.STAGE_DURATIONS['grow_out'][1]) // 2),
            # grow_out ends with harvest, not progression
        }
        
        # Get active assignments that might need progression
        active_assignments = BatchContainerAssignment.objects.filter(
            departure_date__isnull=True,
            is_active=True,
            batch__status='ACTIVE'
        ).select_related('batch', 'container')
        
        for assignment in active_assignments:
            if assignment.lifecycle_stage.name not in stage_progression:
                continue
            
            next_stage, min_days = stage_progression[assignment.lifecycle_stage.name]
            days_in_stage = (current_date - assignment.assignment_date).days
            
            # Check if ready for progression (with some variability)
            min_days_adjusted = min_days + random.randint(-5, 10)
            
            if days_in_stage >= min_days_adjusted:
                # Progress to next stage
                if self._progress_batch_stage(assignment, next_stage, current_date):
                    progressed_count += 1
        
        if progressed_count > 0:
            logger.info(f"Progressed {progressed_count} batches to next lifecycle stage")
        
        return progressed_count
    
    def _progress_batch_stage(self, current_assignment: BatchContainerAssignment, 
                            next_stage: str, transition_date: date) -> bool:
        """
        Progress a batch to the next lifecycle stage with new container assignment.
        
        Args:
            current_assignment: Current container assignment
            next_stage: Next lifecycle stage
            transition_date: Date of transition
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            return True
        
        batch = current_assignment.batch
        
        # Determine new container type based on next stage
        container_type_map = {
            'alevin': 'start tank',
            'fry': 'circular tank small',
            'parr': 'circular tank large',
            'smolt': 'pre-transfer tank',
            'post_smolt': 'pre-transfer tank',  # Fixed - post-smolt stays in freshwater
            'grow_out': 'sea cage standard'
        }
        
        new_container_type_name = container_type_map.get(next_stage)
        if not new_container_type_name:
            logger.error(f"No container type mapping for stage {next_stage}")
            return False
        
        try:
            new_container_type = ContainerType.objects.get(name=new_container_type_name)
        except ContainerType.DoesNotExist:
            logger.error(f"Container type {new_container_type_name} not found")
            return False
        
        # Find available containers of the new type
        available_containers = Container.objects.filter(
            container_type=new_container_type,
            active=True
        )
        
        # Check occupancy
        occupied = BatchContainerAssignment.objects.filter(
            departure_date__isnull=True,
            is_active=True,
            container__in=available_containers
        ).values_list('container_id', flat=True)
        
        free_containers = available_containers.exclude(id__in=occupied)
        
        if not free_containers.exists():
            logger.warning(f"No free containers of type {new_container_type_name} for batch {batch.batch_number}")
            if new_container_type_name == 'Start Tank':
                logger.info("Falling back to Circular Tank Small")
                alternative_type_name = 'Circular Tank Small'
                try:
                    alternative_type = ContainerType.objects.get(name=alternative_type_name)
                    available_containers = Container.objects.filter(
                        container_type=alternative_type,
                        active=True
                    )
                    occupied = BatchContainerAssignment.objects.filter(
                        departure_date__isnull=True,
                        is_active=True,
                        container__in=available_containers
                    ).values_list('container_id', flat=True)
                    free_containers = available_containers.exclude(id__in=occupied)
                except ContainerType.DoesNotExist:
                    logger.error(f"Alternative container type {alternative_type_name} not found")
                    return False
            if not free_containers.exists():
                logger.warning(f"No free containers (including fallback) for batch {batch.batch_number}")
                return False
        
        selected_container = free_containers.first()
        if not selected_container:
            return False
        
        # Add grace period check before selecting container
        last_assignment = BatchContainerAssignment.objects.filter(
            container=selected_container
        ).order_by('-departure_date').first()

        if last_assignment and last_assignment.departure_date:
            days_since = (transition_date - last_assignment.departure_date).days
            # Convert display name to grace period key format
            grace_key = new_container_type_name.lower().replace(' ', '_')
            grace = GP.GRACE_PERIODS.get(grace_key, 0)
            if days_since < grace:
                logger.warning(f"Grace period violation for {selected_container}")
                return False

        with transaction.atomic():
            # End current assignment
            current_assignment.departure_date = transition_date
            current_assignment.is_active = False
            current_assignment.save()
            
            # Calculate new metrics (some mortality during transfer)
            transfer_mortality_rate = random.uniform(0.01, 0.02) # 1-2% transfer mortality
            new_count = int(current_assignment.population_count * (1 - transfer_mortality_rate))
            
            # Update average weight based on stage
            new_avg_weight = GP.INITIAL_WEIGHTS.get(next_stage, current_assignment.avg_weight_g * Decimal('1.5'))
            new_biomass = Decimal(str(new_count * float(new_avg_weight) / 1000))
            
            # Get or create the next lifecycle stage
            next_stage_obj, _ = LifeCycleStage.objects.get_or_create(
                name=next_stage,
                species=batch.species,
                defaults={
                    'order': current_assignment.lifecycle_stage.order + 1,
                    'description': f'{next_stage} stage'
                }
            )
            
            # Create new assignment
            new_assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=selected_container,
                lifecycle_stage=next_stage_obj,
                assignment_date=transition_date,
                population_count=new_count,
                biomass_kg=new_biomass,
                avg_weight_g=new_avg_weight,
                is_active=True
            )
            
            # Update batch lifecycle stage
            batch.lifecycle_stage = next_stage_obj
            batch.save()
            
            logger.debug(f"Progressed batch {batch.batch_number} from {current_assignment.lifecycle_stage.name} to {next_stage}")
            
        if next_stage == 'grow_out':
            if (transition_date - batch.start_date) > timedelta(days=18*30):  # ~18 months
                batch.harvest_date = transition_date
                batch.save()
                current_assignment.departure_date = transition_date
                current_assignment.is_active = False
                current_assignment.save()
                logger.info(f"Auto-harvested batch {batch.batch_number} after prolonged grower stage")
                return True
        
        return True
    
    def get_summary(self) -> str:
        """
        Get a summary of all created batches.
        
        Returns:
            String summary of created objects
        """
        summary = "\n=== Batch Generation Summary ===\n"
        summary += f"Total Batches Created: {len(self.created_batches)}\n"
        summary += f"Total Container Assignments: {len(self.created_assignments)}\n"
        
        if self.created_batches:
            # Source breakdown (from notes)
            import re
            external = 0
            internal = 0
            total_eggs = 0
            
            for batch in self.created_batches:
                if 'External' in batch.notes:
                    external += 1
                else:
                    internal += 1
                
                # Extract egg count from notes
                match = re.search(r'Initial count: ([\d,]+)', batch.notes)
                if match:
                    total_eggs += int(match.group(1).replace(',', ''))
            
            summary += f"Egg Sources: External={external}, Internal={internal}\n"
            summary += f"Total Initial Eggs: {total_eggs:,}\n"
        
        return summary

    def process_container_transfers(self, current_date: date) -> int:
        """
        Process container transfers for batches that need to move to different facilities.

        Args:
            current_date: Current date for processing

        Returns:
            Number of transfers processed
        """
        if self.dry_run:
            return 0

        transfers_count = 0

        try:
            # Get batches that might need transfers
            active_assignments = BatchContainerAssignment.objects.filter(
                departure_date__isnull=True,
                is_active=True,
                batch__status='ACTIVE'
            ).select_related('batch', 'container', 'lifecycle_stage')

            for assignment in active_assignments:
                batch = assignment.batch
                current_stage = assignment.lifecycle_stage.name if assignment.lifecycle_stage else None

                if not current_stage:
                    continue

                # Check if batch needs to transfer to different facility type
                target_facility_type = self._get_target_facility_for_stage(current_stage)

                if target_facility_type and target_facility_type != assignment.container.container_type.name:
                    # Check if enough time has passed since last transfer
                    days_since_assignment = (current_date - assignment.assignment_date).days
                    min_days_in_facility = self._get_minimum_days_in_facility(current_stage)

                    if days_since_assignment >= min_days_in_facility:
                        # Attempt transfer
                        if self._transfer_batch_to_facility(batch, assignment, target_facility_type, current_date):
                            transfers_count += 1

        except Exception as e:
            logger.error(f"Error processing container transfers: {e}")

        if transfers_count > 0:
            logger.info(f"Processed {transfers_count} container transfers")

        return transfers_count

    def _get_target_facility_for_stage(self, stage: str) -> str:
        """Get the target facility type for a given lifecycle stage."""
        facility_mapping = {
            'egg': 'incubation_tray',
            'alevin': 'start_tank',
            'fry': 'circular_tank_small',
            'parr': 'circular_tank_large',
            'smolt': 'pre_transfer_tank',
            'post_smolt': 'pre_transfer_tank',  # Post-smolt stays in freshwater
            'grow_out': 'sea_cage_standard'
        }
        return facility_mapping.get(stage)

    def _get_minimum_days_in_facility(self, stage: str) -> int:
        """Get minimum days a batch should stay in current facility type."""
        # Use stage durations as minimum time in facility
        return GP.STAGE_DURATIONS.get(stage, (90, 90))[0]  # Use minimum duration

    def _transfer_batch_to_facility(self, batch: Batch, current_assignment: BatchContainerAssignment,
                                  target_facility_type: str, transfer_date: date) -> bool:
        """Transfer a batch to a new facility type."""
        try:
            # End current assignment
            current_assignment.departure_date = transfer_date
            current_assignment.is_active = False
            current_assignment.save()

            # Find available container of target type
            target_containers = Container.objects.filter(
                container_type__name=target_facility_type,
                active=True
            )

            # Exclude occupied containers
            occupied_container_ids = BatchContainerAssignment.objects.filter(
                departure_date__isnull=True,
                container__in=target_containers
            ).values_list('container_id', flat=True)

            available_containers = target_containers.exclude(id__in=occupied_container_ids)

            if not available_containers.exists():
                logger.warning(f"No available {target_facility_type} containers for batch {batch.batch_number}")
                return False

            # Get the lifecycle stage for the target
            try:
                lifecycle_stage = LifeCycleStage.objects.get(name=batch.lifecycle_stage.name)
            except LifeCycleStage.DoesNotExist:
                logger.error(f"Lifecycle stage {batch.lifecycle_stage.name} not found")
                return False

            # Create new assignment
            new_container = available_containers.first()  # Use first available

            new_assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=new_container,
                lifecycle_stage=lifecycle_stage,
                assignment_date=transfer_date,
                population_count=batch.current_count or 0,
                is_active=True,
                notes=f"Transfer from {current_assignment.container.container_type.name} to {target_facility_type}"
            )

            logger.info(f"Transferred batch {batch.batch_number} to {target_facility_type}")
            return True

        except Exception as e:
            logger.error(f"Error transferring batch {batch.batch_number}: {e}")
            return False
