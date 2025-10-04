"""
Broodstock service for complex business operations.

This module provides services for managing broodstock fish, movements,
breeding operations, and container capacity management.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.db import transaction, models
from django.db.models import Count, Sum, Q, F
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

from apps.broodstock.models import (
    BroodstockFish, FishMovement, BreedingPair, 
    BreedingPlan, MaintenanceTask
)
from apps.infrastructure.models import Container

AVG_FISH_WEIGHT_KG = settings.BROODSTOCK_DEFAULTS.get('AVG_FISH_WEIGHT_KG', 10.0)

class BroodstockService:
    """Service class for broodstock-related business operations."""
    
    @staticmethod
    @transaction.atomic
    def move_fish(
        fish: BroodstockFish,
        to_container: Container,
        user,
        notes: str = ""
    ) -> FishMovement:
        """
        Move a fish from its current container to a new container.
        
        This method handles:
        - Validation of container types and capacity
        - Creation of movement record
        - Update of fish location
        - Population count updates
        
        Args:
            fish: The BroodstockFish instance to move
            to_container: The destination Container
            user: The user performing the movement
            notes: Optional notes about the movement
            
        Returns:
            FishMovement: The created movement record
            
        Raises:
            ValidationError: If the movement is invalid
        """
        # Validate destination container type
        if 'broodstock' not in to_container.container_type.name.lower():
            raise ValidationError(
                f"Destination container {to_container.name} is not a broodstock container."
            )
        
        # Check if fish is already in the destination container
        if fish.container == to_container:
            raise ValidationError(
                f"Fish {fish.id} is already in container {to_container.name}."
            )
        
        # Check destination container capacity
        current_population = BroodstockFish.objects.filter(
            container=to_container
        ).count()
        
        # Assuming average weight per broodstock fish (this could be made configurable)
        avg_fish_weight_kg = AVG_FISH_WEIGHT_KG
        estimated_biomass = (current_population + 1) * avg_fish_weight_kg
        
        if to_container.max_biomass_kg:
            if estimated_biomass > to_container.max_biomass_kg:
                raise ValidationError(
                    f"Moving fish would exceed container {to_container.name} "
                    f"biomass capacity ({estimated_biomass:.2f} kg > "
                    f"{to_container.max_biomass_kg:.2f} kg)."
                )
        
        # Store the current container before moving
        from_container = fish.container
        
        # Create movement record
        movement = FishMovement.objects.create(
            fish=fish,
            from_container=from_container,
            to_container=to_container,
            movement_date=timezone.now(),
            moved_by=user,
            notes=notes
        )
        
        # Update fish location
        fish.container = to_container
        fish.save()
        
        return movement
    
    @staticmethod
    @transaction.atomic
    def bulk_move_fish(
        fish_ids: List[int],
        from_container: Container,
        to_container: Container,
        user,
        notes: str = ""
    ) -> List[FishMovement]:
        """
        Move multiple fish between containers in a single operation.
        
        Args:
            fish_ids: List of fish IDs to move
            from_container: Source container
            to_container: Destination container
            user: User performing the movement
            notes: Optional notes
            
        Returns:
            List[FishMovement]: Created movement records
            
        Raises:
            ValidationError: If any validation fails
        """
        # Validate containers
        if from_container == to_container:
            raise ValidationError("Source and destination containers must be different.")
        
        for container in [from_container, to_container]:
            if 'broodstock' not in container.container_type.name.lower():
                raise ValidationError(
                    f"Container {container.name} is not a broodstock container."
                )
        
        # Get fish objects and validate they're in the source container
        fish_list = BroodstockFish.objects.filter(
            id__in=fish_ids,
            container=from_container
        )
        
        if fish_list.count() != len(fish_ids):
            raise ValidationError(
                "Some fish are not in the specified source container."
            )
        
        # Check destination capacity
        current_population = BroodstockFish.objects.filter(
            container=to_container
        ).count()
        
        avg_fish_weight_kg = AVG_FISH_WEIGHT_KG
        new_population = current_population + len(fish_ids)
        estimated_biomass = new_population * avg_fish_weight_kg
        
        if to_container.max_biomass_kg:
            if estimated_biomass > to_container.max_biomass_kg:
                raise ValidationError(
                    f"Moving {len(fish_ids)} fish would exceed container "
                    f"{to_container.name} biomass capacity "
                    f"({estimated_biomass:.2f} kg > "
                    f"{to_container.max_biomass_kg:.2f} kg)."
                )
        
        # Perform bulk movement
        movements = []
        movement_date = timezone.now()
        
        for fish in fish_list:
            movement = FishMovement.objects.create(
                fish=fish,
                from_container=from_container,
                to_container=to_container,
                movement_date=movement_date,
                moved_by=user,
                notes=notes
            )
            movements.append(movement)
        
        # Update all fish locations
        fish_list.update(container=to_container)
        
        return movements
    
    @staticmethod
    def validate_breeding_pair(
        male_fish: BroodstockFish,
        female_fish: BroodstockFish,
        plan: BreedingPlan
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a potential breeding pair.
        
        Checks:
        - Fish are different individuals
        - Both fish are healthy
        - Fish are not already paired in the same plan
        - Plan is active
        
        Args:
            male_fish: Male broodstock fish
            female_fish: Female broodstock fish
            plan: Breeding plan
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check if fish are different
        if male_fish == female_fish:
            return False, "Male and female fish must be different individuals."
        
        # Check health status
        if male_fish.health_status != 'healthy':
            return False, f"Male fish {male_fish.id} is not healthy."
        
        if female_fish.health_status != 'healthy':
            return False, f"Female fish {female_fish.id} is not healthy."
        
        # Check if plan is active
        if not plan.is_active:
            return False, f"Breeding plan '{plan.name}' is not active."
        
        # Check for existing pairing in the same plan
        existing_pair = BreedingPair.objects.filter(
            plan=plan,
            male_fish=male_fish,
            female_fish=female_fish
        ).exists()
        
        if existing_pair:
            return False, "This pair already exists in the breeding plan."
        
        # Check if either fish is already paired in this plan
        male_paired = BreedingPair.objects.filter(
            plan=plan,
            male_fish=male_fish
        ).exists()
        
        if male_paired:
            return False, f"Male fish {male_fish.id} is already paired in this plan."
        
        female_paired = BreedingPair.objects.filter(
            plan=plan,
            female_fish=female_fish
        ).exists()
        
        if female_paired:
            return False, f"Female fish {female_fish.id} is already paired in this plan."
        
        return True, None
    
    @staticmethod
    @transaction.atomic
    def create_breeding_pair(
        male_fish: BroodstockFish,
        female_fish: BroodstockFish,
        plan: BreedingPlan,
        pairing_date: Optional[datetime] = None
    ) -> BreedingPair:
        """
        Create a breeding pair with validation.
        
        Args:
            male_fish: Male broodstock fish
            female_fish: Female broodstock fish
            plan: Breeding plan
            pairing_date: Optional pairing date (defaults to now)
            
        Returns:
            BreedingPair: The created breeding pair
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate the pair
        is_valid, error_message = BroodstockService.validate_breeding_pair(
            male_fish, female_fish, plan
        )
        
        if not is_valid:
            raise ValidationError(error_message)
        
        # Create the breeding pair
        breeding_pair = BreedingPair.objects.create(
            plan=plan,
            male_fish=male_fish,
            female_fish=female_fish,
            pairing_date=pairing_date or timezone.now()
        )
        
        return breeding_pair
    
    @staticmethod
    def get_container_statistics(container: Container) -> Dict:
        """
        Get comprehensive statistics for a broodstock container.
        
        Args:
            container: The container to analyze
            
        Returns:
            Dict: Container statistics including population, health status, etc.
        """
        # Validate container type
        if 'broodstock' not in container.container_type.name.lower():
            raise ValidationError(f"{container.name} is not a broodstock container.")
        
        # Get fish in container
        fish_qs = BroodstockFish.objects.filter(container=container)
        
        # Calculate statistics
        total_population = fish_qs.count()
        
        health_distribution = fish_qs.values('health_status').annotate(
            count=Count('id')
        ).order_by('health_status')
        
        # Get recent movements
        recent_movements_in = FishMovement.objects.filter(
            to_container=container,
            movement_date__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        recent_movements_out = FishMovement.objects.filter(
            from_container=container,
            movement_date__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Get breeding pairs using fish from this container
        active_breeding_pairs = BreedingPair.objects.filter(
            Q(male_fish__container=container) | Q(female_fish__container=container),
            plan__start_date__lte=timezone.now(),
            plan__end_date__gte=timezone.now()
        ).count()
        
        # Calculate capacity utilization
        avg_fish_weight_kg = AVG_FISH_WEIGHT_KG
        estimated_biomass = total_population * avg_fish_weight_kg
        capacity_utilization = 0
        
        if container.max_biomass_kg:
            capacity_utilization = (estimated_biomass / container.max_biomass_kg) * 100
        
        # Get pending maintenance tasks
        pending_maintenance = MaintenanceTask.objects.filter(
            container=container,
            completed_date__isnull=True
        ).count()
        
        overdue_maintenance = MaintenanceTask.objects.filter(
            container=container,
            completed_date__isnull=True,
            scheduled_date__lt=timezone.now()
        ).count()
        
        return {
            'container_id': container.id,
            'container_name': container.name,
            'total_population': total_population,
            'health_distribution': list(health_distribution),
            'estimated_biomass_kg': estimated_biomass,
            'capacity_utilization_percent': round(capacity_utilization, 2),
            'recent_movements': {
                'in': recent_movements_in,
                'out': recent_movements_out,
                'net': recent_movements_in - recent_movements_out
            },
            'active_breeding_pairs': active_breeding_pairs,
            'maintenance': {
                'pending': pending_maintenance,
                'overdue': overdue_maintenance
            }
        }
    
    @staticmethod
    def get_breeding_plan_summary(plan: BreedingPlan) -> Dict:
        """
        Get comprehensive summary of a breeding plan.
        
        Args:
            plan: The breeding plan to summarize
            
        Returns:
            Dict: Summary statistics of the breeding plan
        """
        # Get all pairs in the plan
        pairs = BreedingPair.objects.filter(plan=plan)
        total_pairs = pairs.count()
        
        # Get egg production from these pairs
        egg_productions = models.Sum('egg_productions__egg_count')
        total_eggs = pairs.aggregate(
            total_eggs=egg_productions or 0
        )['total_eggs'] or 0
        
        # Get trait priorities
        trait_priorities = plan.trait_priorities.all().order_by('-priority_weight')
        
        # Calculate success metrics
        pairs_with_progeny = pairs.filter(progeny_count__gt=0).count()
        success_rate = (pairs_with_progeny / total_pairs * 100) if total_pairs > 0 else 0
        
        # Get unique fish involved
        unique_males = pairs.values('male_fish').distinct().count()
        unique_females = pairs.values('female_fish').distinct().count()
        
        return {
            'plan_id': plan.id,
            'plan_name': plan.name,
            'is_active': plan.is_active,
            'duration_days': (plan.end_date - plan.start_date).days,
            'total_pairs': total_pairs,
            'pairs_with_progeny': pairs_with_progeny,
            'success_rate_percent': round(success_rate, 2),
            'total_eggs_produced': total_eggs,
            'unique_males': unique_males,
            'unique_females': unique_females,
            'trait_priorities': [
                {
                    'trait': tp.get_trait_name_display(),
                    'weight': tp.priority_weight
                }
                for tp in trait_priorities
            ]
        }
    
    @staticmethod
    def check_container_maintenance_due(container: Container) -> List[MaintenanceTask]:
        """
        Check for due or overdue maintenance tasks for a container.
        
        Args:
            container: The container to check
            
        Returns:
            List[MaintenanceTask]: List of due/overdue maintenance tasks
        """
        return MaintenanceTask.objects.filter(
            container=container,
            completed_date__isnull=True,
            scheduled_date__lte=timezone.now() + timedelta(days=7)
        ).order_by('scheduled_date') 