"""
Egg management service for complex egg-related operations.

This module provides services for managing egg production, acquisition,
and batch assignment with full traceability.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from django.db import transaction, models
from django.db.models import Sum, Count, Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.broodstock.models import (
    EggProduction, BreedingPair, EggSupplier, 
    ExternalEggBatch, BatchParentage
)
from apps.batch.models import Batch, LifeCycleStage
from apps.infrastructure.models import FreshwaterStation


class EggManagementService:
    """Service class for egg management operations."""
    
    @staticmethod
    def generate_egg_batch_id(source_type: str) -> str:
        """
        Generate a unique egg batch ID.
        
        Args:
            source_type: Either 'internal' or 'external'
            
        Returns:
            str: Unique egg batch ID
        """
        prefix = "EB-INT" if source_type == "internal" else "EB-EXT"
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        
        # Add microseconds for extra uniqueness
        microseconds = timezone.now().strftime('%f')[:3]
        
        return f"{prefix}-{timestamp}-{microseconds}"
    
    @staticmethod
    @transaction.atomic
    def produce_internal_eggs(
        breeding_pair: BreedingPair,
        egg_count: int,
        destination_station: Optional[FreshwaterStation] = None,
        production_date: Optional[datetime] = None
    ) -> EggProduction:
        """
        Create internal egg production from a breeding pair.
        
        Args:
            breeding_pair: The breeding pair producing eggs
            egg_count: Number of eggs produced
            destination_station: Optional destination freshwater station
            production_date: Optional production date (defaults to now)
            
        Returns:
            EggProduction: The created egg production record
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate breeding pair
        if not breeding_pair.plan.is_active:
            raise ValidationError(
                f"Breeding plan '{breeding_pair.plan.name}' is not active."
            )
        
        # Validate egg count
        if egg_count <= 0:
            raise ValidationError("Egg count must be positive.")
        
        # Check if both fish are still healthy
        if breeding_pair.male_fish.health_status != 'healthy':
            raise ValidationError(
                f"Male fish {breeding_pair.male_fish.id} is no longer healthy."
            )
        
        if breeding_pair.female_fish.health_status != 'healthy':
            raise ValidationError(
                f"Female fish {breeding_pair.female_fish.id} is no longer healthy."
            )
        
        # Generate unique batch ID
        egg_batch_id = EggManagementService.generate_egg_batch_id('internal')
        
        # Create egg production record
        egg_production = EggProduction.objects.create(
            pair=breeding_pair,
            egg_batch_id=egg_batch_id,
            egg_count=egg_count,
            production_date=production_date or timezone.now(),
            destination_station=destination_station,
            source_type='internal'
        )
        
        # Update breeding pair progeny count
        current_progeny = breeding_pair.progeny_count or 0
        breeding_pair.progeny_count = current_progeny + egg_count
        breeding_pair.save()
        
        return egg_production
    
    @staticmethod
    @transaction.atomic
    def acquire_external_eggs(
        supplier: EggSupplier,
        batch_number: str,
        egg_count: int,
        provenance_data: str = "",
        destination_station: Optional[FreshwaterStation] = None,
        acquisition_date: Optional[datetime] = None
    ) -> Tuple[EggProduction, ExternalEggBatch]:
        """
        Create external egg acquisition records.
        
        Args:
            supplier: The egg supplier
            batch_number: Supplier's batch number
            egg_count: Number of eggs acquired
            provenance_data: Additional provenance information
            destination_station: Optional destination station
            acquisition_date: Optional acquisition date
            
        Returns:
            Tuple[EggProduction, ExternalEggBatch]: Created records
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate egg count
        if egg_count <= 0:
            raise ValidationError("Egg count must be positive.")
        
        # Check for duplicate batch number from same supplier
        existing_batch = ExternalEggBatch.objects.filter(
            supplier=supplier,
            batch_number=batch_number
        ).exists()
        
        if existing_batch:
            raise ValidationError(
                f"Batch number '{batch_number}' already exists for supplier '{supplier.name}'."
            )
        
        # Generate unique batch ID
        egg_batch_id = EggManagementService.generate_egg_batch_id('external')
        
        # Create egg production record
        egg_production = EggProduction.objects.create(
            egg_batch_id=egg_batch_id,
            egg_count=egg_count,
            production_date=acquisition_date or timezone.now(),
            destination_station=destination_station,
            source_type='external'
        )
        
        # Create external batch record
        external_batch = ExternalEggBatch.objects.create(
            egg_production=egg_production,
            supplier=supplier,
            batch_number=batch_number,
            provenance_data=provenance_data
        )
        
        return egg_production, external_batch
    
    @staticmethod
    @transaction.atomic
    def assign_eggs_to_batch(
        egg_production: EggProduction,
        batch: Batch,
        assignment_date: Optional[datetime] = None
    ) -> BatchParentage:
        """
        Assign eggs from production to a batch.
        
        Args:
            egg_production: The egg production to assign
            batch: The target batch
            assignment_date: Optional assignment date
            
        Returns:
            BatchParentage: The created parentage record
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate batch lifecycle stage
        valid_stages = ['egg', 'alevin', 'fry']
        if batch.lifecycle_stage.name.lower() not in valid_stages:
            raise ValidationError(
                f"Batch must be in {', '.join(valid_stages)} stage. "
                f"Current stage: {batch.lifecycle_stage.name}"
            )
        
        # Check if eggs are already assigned to a batch
        existing_assignment = BatchParentage.objects.filter(
            egg_production=egg_production
        ).exists()
        
        if existing_assignment:
            raise ValidationError(
                f"Egg batch {egg_production.egg_batch_id} is already assigned to a batch."
            )
        
        # Validate destination station compatibility
        if egg_production.destination_station:
            # Get the batch's containers and check their freshwater stations
            batch_containers = batch.containers
            
            if batch_containers.exists():
                # Check if any of the batch's containers are in the destination station
                valid_container = False
                for container in batch_containers:
                    if hasattr(container, 'hall') and container.hall:
                        if container.hall.freshwater_station == egg_production.destination_station:
                            valid_container = True
                            break
                
                if not valid_container:
                    raise ValidationError(
                        f"None of the batch's containers are in the designated destination station "
                        f"({egg_production.destination_station.name})."
                    )
        
        # Create parentage record
        parentage = BatchParentage.objects.create(
            batch=batch,
            egg_production=egg_production,
            assignment_date=assignment_date or timezone.now()
        )
        
        return parentage
    
    @staticmethod
    def get_egg_production_summary(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source_type: Optional[str] = None
    ) -> Dict:
        """
        Get summary statistics for egg production.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            source_type: Optional source type filter ('internal' or 'external')
            
        Returns:
            Dict: Summary statistics
        """
        # Build query
        query = Q()
        if start_date:
            query &= Q(production_date__gte=start_date)
        if end_date:
            query &= Q(production_date__lte=end_date)
        if source_type:
            query &= Q(source_type=source_type)
        
        # Get egg productions
        productions = EggProduction.objects.filter(query)
        
        # Calculate statistics
        total_productions = productions.count()
        total_eggs = productions.aggregate(
            total=Sum('egg_count')
        )['total'] or 0
        
        # Group by source type
        by_source = productions.values('source_type').annotate(
            count=Count('id'),
            eggs=Sum('egg_count')
        ).order_by('source_type')
        
        # Get assigned vs unassigned
        assigned = productions.filter(
            batch_assignments__isnull=False
        ).distinct().count()
        
        unassigned = total_productions - assigned
        
        # Get top breeding pairs (for internal)
        top_pairs = []
        if not source_type or source_type == 'internal':
            top_pairs = productions.filter(
                source_type='internal'
            ).values(
                'pair__id',
                'pair__male_fish__id',
                'pair__female_fish__id'
            ).annotate(
                total_eggs=Sum('egg_count'),
                production_count=Count('id')
            ).order_by('-total_eggs')[:5]
        
        # Get top suppliers (for external)
        top_suppliers = []
        if not source_type or source_type == 'external':
            top_suppliers = ExternalEggBatch.objects.filter(
                egg_production__in=productions.filter(source_type='external')
            ).values(
                'supplier__id',
                'supplier__name'
            ).annotate(
                total_eggs=Sum('egg_production__egg_count'),
                batch_count=Count('id')
            ).order_by('-total_eggs')[:5]
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_productions': total_productions,
            'total_eggs': total_eggs,
            'by_source_type': list(by_source),
            'assignment_status': {
                'assigned': assigned,
                'unassigned': unassigned,
                'assignment_rate_percent': round(
                    (assigned / total_productions * 100) if total_productions > 0 else 0, 
                    2
                )
            },
            'top_breeding_pairs': list(top_pairs),
            'top_suppliers': list(top_suppliers)
        }
    
    @staticmethod
    def get_batch_lineage(batch: Batch) -> Dict:
        """
        Get complete lineage information for a batch.
        
        Args:
            batch: The batch to trace
            
        Returns:
            Dict: Complete lineage information
        """
        # Get all parentage records
        parentages = BatchParentage.objects.filter(
            batch=batch
        ).select_related(
            'egg_production',
            'egg_production__pair',
            'egg_production__pair__male_fish',
            'egg_production__pair__female_fish'
        ).prefetch_related(
            'egg_production__external_batch',
            'egg_production__external_batch__supplier'
        )
        
        lineage_data = {
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'egg_sources': []
        }
        
        for parentage in parentages:
            egg_prod = parentage.egg_production
            source_info = {
                'egg_batch_id': egg_prod.egg_batch_id,
                'egg_count': egg_prod.egg_count,
                'production_date': egg_prod.production_date,
                'source_type': egg_prod.source_type,
                'assignment_date': parentage.assignment_date
            }
            
            if egg_prod.source_type == 'internal':
                source_info['breeding_pair'] = {
                    'pair_id': egg_prod.pair.id,
                    'male_fish_id': egg_prod.pair.male_fish.id,
                    'female_fish_id': egg_prod.pair.female_fish.id,
                    'breeding_plan': egg_prod.pair.plan.name
                }
            else:  # external
                external_batch = egg_prod.external_batch
                source_info['external_source'] = {
                    'supplier': external_batch.supplier.name,
                    'supplier_batch_number': external_batch.batch_number,
                    'provenance_data': external_batch.provenance_data
                }
            
            lineage_data['egg_sources'].append(source_info)
        
        # Calculate totals
        total_eggs = sum(source['egg_count'] for source in lineage_data['egg_sources'])
        lineage_data['total_eggs'] = total_eggs
        lineage_data['source_count'] = len(lineage_data['egg_sources'])
        
        return lineage_data
    
    @staticmethod
    def validate_egg_traceability(egg_batch_id: str) -> Dict:
        """
        Validate and trace an egg batch through the system.
        
        Args:
            egg_batch_id: The egg batch ID to trace
            
        Returns:
            Dict: Traceability information
        """
        try:
            egg_production = EggProduction.objects.get(egg_batch_id=egg_batch_id)
        except EggProduction.DoesNotExist:
            raise ValidationError(f"Egg batch '{egg_batch_id}' not found.")
        
        trace_info = {
            'egg_batch_id': egg_batch_id,
            'source_type': egg_production.source_type,
            'egg_count': egg_production.egg_count,
            'production_date': egg_production.production_date,
            'destination_station': egg_production.destination_station.name if egg_production.destination_station else None
        }
        
        # Add source details
        if egg_production.source_type == 'internal':
            pair = egg_production.pair
            trace_info['source_details'] = {
                'type': 'internal_breeding',
                'breeding_pair_id': pair.id,
                'male_fish_id': pair.male_fish.id,
                'female_fish_id': pair.female_fish.id,
                'breeding_plan': pair.plan.name
            }
        else:
            external = egg_production.external_batch
            trace_info['source_details'] = {
                'type': 'external_acquisition',
                'supplier': external.supplier.name,
                'supplier_batch': external.batch_number,
                'certifications': external.supplier.certifications
            }
        
        # Check assignment status
        try:
            parentage = BatchParentage.objects.get(egg_production=egg_production)
            trace_info['assignment_status'] = {
                'is_assigned': True,
                'batch_id': parentage.batch.id,
                'batch_number': parentage.batch.batch_number,
                'assignment_date': parentage.assignment_date
            }
        except BatchParentage.DoesNotExist:
            trace_info['assignment_status'] = {
                'is_assigned': False,
                'batch_id': None,
                'batch_number': None,
                'assignment_date': None
            }
        
        return trace_info 