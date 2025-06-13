"""
Tests for broodstock services.

This module contains comprehensive tests for BroodstockService and
EggManagementService to ensure robust business logic implementation.
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.broodstock.models import (
    BroodstockFish, FishMovement, BreedingPlan, BreedingPair,
    EggProduction, EggSupplier, ExternalEggBatch, BatchParentage
)
from apps.broodstock.services import BroodstockService, EggManagementService
from apps.infrastructure.models import (
    Container, ContainerType, Area, FreshwaterStation, Hall, Geography
)
from apps.batch.models import Batch, LifeCycleStage, Species

User = get_user_model()


class BroodstockServiceTestCase(TestCase):
    """Test case for BroodstockService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create container types
        self.broodstock_type = ContainerType.objects.create(
            name='Broodstock Tank',
            category='TANK',
            max_volume_m3=100.0
        )
        
        self.regular_type = ContainerType.objects.create(
            name='Regular Tank',
            category='TANK',
            max_volume_m3=100.0
        )
        
        # Create geography and area
        self.geography = Geography.objects.create(
            name='Test Region'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=Decimal('60.0'),
            longitude=Decimal('5.0'),
            max_biomass=Decimal('100000.0')
        )
        
        self.container1 = Container.objects.create(
            name='Broodstock Tank 1',
            container_type=self.broodstock_type,
            area=self.area,
            volume_m3=80.0,
            max_biomass_kg=500.0
        )
        
        self.container2 = Container.objects.create(
            name='Broodstock Tank 2',
            container_type=self.broodstock_type,
            area=self.area,
            volume_m3=80.0,
            max_biomass_kg=500.0
        )
        
        self.regular_container = Container.objects.create(
            name='Regular Tank',
            container_type=self.regular_type,
            area=self.area,
            volume_m3=80.0,
            max_biomass_kg=500.0
        )
        
        # Create fish
        self.fish1 = BroodstockFish.objects.create(
            container=self.container1,
            health_status='healthy'
        )
        
        self.fish2 = BroodstockFish.objects.create(
            container=self.container1,
            health_status='healthy'
        )
        
        self.sick_fish = BroodstockFish.objects.create(
            container=self.container1,
            health_status='sick'
        )
    
    def test_move_fish_success(self):
        """Test successful fish movement."""
        movement = BroodstockService.move_fish(
            fish=self.fish1,
            to_container=self.container2,
            user=self.user,
            notes="Test movement"
        )
        
        self.assertEqual(movement.fish, self.fish1)
        self.assertEqual(movement.from_container, self.container1)
        self.assertEqual(movement.to_container, self.container2)
        self.assertEqual(movement.moved_by, self.user)
        
        # Refresh fish from database
        self.fish1.refresh_from_db()
        self.assertEqual(self.fish1.container, self.container2)
    
    def test_move_fish_to_non_broodstock_container(self):
        """Test that moving to non-broodstock container fails."""
        with self.assertRaises(ValidationError) as context:
            BroodstockService.move_fish(
                fish=self.fish1,
                to_container=self.regular_container,
                user=self.user
            )
        
        self.assertIn("not a broodstock container", str(context.exception))
    
    def test_move_fish_to_same_container(self):
        """Test that moving to same container fails."""
        with self.assertRaises(ValidationError) as context:
            BroodstockService.move_fish(
                fish=self.fish1,
                to_container=self.container1,
                user=self.user
            )
        
        self.assertIn("already in container", str(context.exception))
    
    def test_move_fish_capacity_check(self):
        """Test that capacity limits are enforced."""
        # Create many fish to fill container2 near capacity
        # Assuming 10kg per fish, 500kg capacity = 50 fish max
        for i in range(49):
            BroodstockFish.objects.create(
                container=self.container2,
                health_status='healthy'
            )
        
        # This should succeed (50th fish)
        BroodstockService.move_fish(
            fish=self.fish1,
            to_container=self.container2,
            user=self.user
        )
        
        # This should fail (51st fish)
        with self.assertRaises(ValidationError) as context:
            BroodstockService.move_fish(
                fish=self.fish2,
                to_container=self.container2,
                user=self.user
            )
        
        self.assertIn("exceed container", str(context.exception))
        self.assertIn("biomass capacity", str(context.exception))
    
    def test_bulk_move_fish(self):
        """Test bulk fish movement."""
        fish_ids = [self.fish1.id, self.fish2.id]
        
        movements = BroodstockService.bulk_move_fish(
            fish_ids=fish_ids,
            from_container=self.container1,
            to_container=self.container2,
            user=self.user,
            notes="Bulk transfer"
        )
        
        self.assertEqual(len(movements), 2)
        
        # Check all fish moved
        self.fish1.refresh_from_db()
        self.fish2.refresh_from_db()
        self.assertEqual(self.fish1.container, self.container2)
        self.assertEqual(self.fish2.container, self.container2)
    
    def test_validate_breeding_pair(self):
        """Test breeding pair validation."""
        # Create breeding plan
        plan = BreedingPlan.objects.create(
            name='Test Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Test valid pair
        is_valid, error = BroodstockService.validate_breeding_pair(
            self.fish1, self.fish2, plan
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test same fish
        is_valid, error = BroodstockService.validate_breeding_pair(
            self.fish1, self.fish1, plan
        )
        self.assertFalse(is_valid)
        self.assertIn("different individuals", error)
        
        # Test unhealthy fish
        is_valid, error = BroodstockService.validate_breeding_pair(
            self.fish1, self.sick_fish, plan
        )
        self.assertFalse(is_valid)
        self.assertIn("not healthy", error)
    
    def test_create_breeding_pair(self):
        """Test breeding pair creation."""
        plan = BreedingPlan.objects.create(
            name='Test Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        pair = BroodstockService.create_breeding_pair(
            male_fish=self.fish1,
            female_fish=self.fish2,
            plan=plan
        )
        
        self.assertEqual(pair.male_fish, self.fish1)
        self.assertEqual(pair.female_fish, self.fish2)
        self.assertEqual(pair.plan, plan)
        
        # Test duplicate pair fails
        with self.assertRaises(ValidationError):
            BroodstockService.create_breeding_pair(
                male_fish=self.fish1,
                female_fish=self.fish2,
                plan=plan
            )
    
    def test_get_container_statistics(self):
        """Test container statistics calculation."""
        stats = BroodstockService.get_container_statistics(self.container1)
        
        self.assertEqual(stats['total_population'], 3)  # 3 fish created in setUp
        self.assertEqual(stats['container_name'], 'Broodstock Tank 1')
        self.assertIn('health_distribution', stats)
        self.assertIn('capacity_utilization_percent', stats)
        self.assertIn('recent_movements', stats)
        self.assertIn('maintenance', stats)


class EggManagementServiceTestCase(TestCase):
    """Test case for EggManagementService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create infrastructure
        self.geography = Geography.objects.create(
            name='Test Region'
        )
        
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            geography=self.geography,
            latitude=Decimal('60.0'),
            longitude=Decimal('5.0')
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=Decimal('60.0'),
            longitude=Decimal('5.0'),
            max_biomass=Decimal('100000.0')
        )
        
        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station
        )
        
        # Create container types and containers
        self.broodstock_type = ContainerType.objects.create(
            name='Broodstock Tank',
            category='TANK',
            max_volume_m3=100.0
        )
        
        self.container = Container.objects.create(
            name='Broodstock Tank 1',
            container_type=self.broodstock_type,
            hall=self.hall,
            volume_m3=80.0,
            max_biomass_kg=500.0
        )
        
        # Create breeding setup
        self.male_fish = BroodstockFish.objects.create(
            container=self.container,
            health_status='healthy'
        )
        
        self.female_fish = BroodstockFish.objects.create(
            container=self.container,
            health_status='healthy'
        )
        
        self.plan = BreedingPlan.objects.create(
            name='Test Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        self.pair = BreedingPair.objects.create(
            plan=self.plan,
            male_fish=self.male_fish,
            female_fish=self.female_fish
        )
        
        # Create egg supplier
        self.supplier = EggSupplier.objects.create(
            name='Test Supplier',
            contact_details='test@example.com',
            certifications='ISO 9001'
        )
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.egg_stage = LifeCycleStage.objects.create(
            name='Egg',
            species=self.species,
            order=1
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number='TEST-001',
            species=self.species,
            lifecycle_stage=self.egg_stage,
            start_date=timezone.now().date()
        )
    
    def test_generate_egg_batch_id(self):
        """Test egg batch ID generation."""
        internal_id = EggManagementService.generate_egg_batch_id('internal')
        external_id = EggManagementService.generate_egg_batch_id('external')
        
        self.assertTrue(internal_id.startswith('EB-INT-'))
        self.assertTrue(external_id.startswith('EB-EXT-'))
        
        # Test uniqueness - add a small delay to ensure different timestamps
        id1 = EggManagementService.generate_egg_batch_id('internal')
        time.sleep(0.001)  # 1 millisecond delay
        id2 = EggManagementService.generate_egg_batch_id('internal')
        self.assertNotEqual(id1, id2)
    
    def test_produce_internal_eggs(self):
        """Test internal egg production."""
        egg_production = EggManagementService.produce_internal_eggs(
            breeding_pair=self.pair,
            egg_count=10000,
            destination_station=self.station
        )
        
        self.assertEqual(egg_production.source_type, 'internal')
        self.assertEqual(egg_production.egg_count, 10000)
        self.assertEqual(egg_production.pair, self.pair)
        self.assertEqual(egg_production.destination_station, self.station)
        
        # Check progeny count updated
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.progeny_count, 10000)
    
    def test_produce_internal_eggs_validation(self):
        """Test internal egg production validation."""
        # Test with inactive plan
        self.plan.end_date = timezone.now() - timedelta(days=1)
        self.plan.save()
        
        with self.assertRaises(ValidationError) as context:
            EggManagementService.produce_internal_eggs(
                breeding_pair=self.pair,
                egg_count=10000
            )
        
        self.assertIn("not active", str(context.exception))
        
        # Test with negative egg count
        self.plan.end_date = timezone.now() + timedelta(days=30)
        self.plan.save()
        
        with self.assertRaises(ValidationError) as context:
            EggManagementService.produce_internal_eggs(
                breeding_pair=self.pair,
                egg_count=-100
            )
        
        self.assertIn("must be positive", str(context.exception))
    
    def test_acquire_external_eggs(self):
        """Test external egg acquisition."""
        egg_prod, external_batch = EggManagementService.acquire_external_eggs(
            supplier=self.supplier,
            batch_number='SUP-001',
            egg_count=50000,
            provenance_data='Norway stock',
            destination_station=self.station
        )
        
        self.assertEqual(egg_prod.source_type, 'external')
        self.assertEqual(egg_prod.egg_count, 50000)
        self.assertEqual(external_batch.supplier, self.supplier)
        self.assertEqual(external_batch.batch_number, 'SUP-001')
        self.assertEqual(external_batch.provenance_data, 'Norway stock')
    
    def test_acquire_external_eggs_duplicate_batch(self):
        """Test that duplicate batch numbers are rejected."""
        # First acquisition
        EggManagementService.acquire_external_eggs(
            supplier=self.supplier,
            batch_number='SUP-001',
            egg_count=50000
        )
        
        # Duplicate should fail
        with self.assertRaises(ValidationError) as context:
            EggManagementService.acquire_external_eggs(
                supplier=self.supplier,
                batch_number='SUP-001',
                egg_count=30000
            )
        
        self.assertIn("already exists", str(context.exception))
    
    def test_assign_eggs_to_batch(self):
        """Test egg to batch assignment."""
        # Create egg production without destination station
        egg_prod = EggManagementService.produce_internal_eggs(
            breeding_pair=self.pair,
            egg_count=10000
        )
        
        # Assign to batch
        parentage = EggManagementService.assign_eggs_to_batch(
            egg_production=egg_prod,
            batch=self.batch
        )
        
        self.assertEqual(parentage.egg_production, egg_prod)
        self.assertEqual(parentage.batch, self.batch)
    
    def test_assign_eggs_validation(self):
        """Test egg assignment validation."""
        # Create egg production
        egg_prod = EggManagementService.produce_internal_eggs(
            breeding_pair=self.pair,
            egg_count=10000
        )
        
        # Create batch with wrong lifecycle stage
        adult_stage = LifeCycleStage.objects.create(
            name='Adult',
            species=self.species,
            order=10
        )
        
        adult_batch = Batch.objects.create(
            batch_number='ADULT-001',
            species=self.species,
            lifecycle_stage=adult_stage,
            start_date=timezone.now().date()
        )
        
        with self.assertRaises(ValidationError) as context:
            EggManagementService.assign_eggs_to_batch(
                egg_production=egg_prod,
                batch=adult_batch
            )
        
        self.assertIn("must be in egg", str(context.exception))
    
    def test_get_batch_lineage(self):
        """Test batch lineage tracking."""
        # Create multiple egg sources
        egg_prod1 = EggManagementService.produce_internal_eggs(
            breeding_pair=self.pair,
            egg_count=5000
        )
        
        egg_prod2, _ = EggManagementService.acquire_external_eggs(
            supplier=self.supplier,
            batch_number='EXT-001',
            egg_count=3000
        )
        
        # Assign both to batch
        EggManagementService.assign_eggs_to_batch(egg_prod1, self.batch)
        EggManagementService.assign_eggs_to_batch(egg_prod2, self.batch)
        
        # Get lineage
        lineage = EggManagementService.get_batch_lineage(self.batch)
        
        self.assertEqual(lineage['batch_number'], 'TEST-001')
        self.assertEqual(lineage['source_count'], 2)
        self.assertEqual(lineage['total_eggs'], 8000)
        self.assertEqual(len(lineage['egg_sources']), 2)
        
        # Check source details
        internal_source = next(s for s in lineage['egg_sources'] if s['source_type'] == 'internal')
        external_source = next(s for s in lineage['egg_sources'] if s['source_type'] == 'external')
        
        self.assertIn('breeding_pair', internal_source)
        self.assertIn('external_source', external_source) 