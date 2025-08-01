import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.broodstock.models import (
    BroodstockFish,
    BreedingPlan,
    BreedingPair,
    EggProduction,
    FishMovement,
    BreedingTraitPriority,
    EggSupplier,
    ExternalEggBatch,
    MaintenanceTask,
    BatchParentage
)
from apps.infrastructure.models import (
    Container, 
    ContainerType,
    Hall, 
    FreshwaterStation,
    Geography,
    Area
)
from apps.batch.models import Batch, Species, LifeCycleStage
from django.contrib.auth import get_user_model

User = get_user_model()


class BroodstockBaseTestCase(TestCase):
    """Base test case with common setup for broodstock tests."""
    
    def setUp(self):
        """Set up common test data for broodstock tests."""
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create geography, station, and hall
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography description'
        )
        
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            station_type='FRESHWATER',
            geography=self.geography,
            latitude=62.01,
            longitude=-6.77,
            description='Test station description'
        )
        
        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station,
            description='Test hall description',
            area_sqm=1000.0
        )
        
        # Create area for sea-based containers
        self.area = Area.objects.create(
            name='Test Sea Area',
            geography=self.geography,
            latitude=60.0,
            longitude=5.0,
            max_biomass=10000.0
        )
        
        # Create container types
        self.tank_type = ContainerType.objects.create(
            name='Test Tank Type',
            category='TANK',
            max_volume_m3=100.0,
            description='Test tank type description'
        )
        
        self.pen_type = ContainerType.objects.create(
            name='Test Pen Type',
            category='PEN',
            max_volume_m3=1000.0,
            description='Test pen type description'
        )
        
        # Create containers
        self.tank = Container.objects.create(
            name='Test Tank',
            container_type=self.tank_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=200.0
        )
        
        self.pen = Container.objects.create(
            name='Test Pen',
            container_type=self.pen_type,
            area=self.area,
            volume_m3=500.0,
            max_biomass_kg=2000.0
        )
        
        # Create species and lifecycle stage for batch creation
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar',
            description='Test species description'
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Broodstock',
            species=self.species,
            order=5,
            description='Adult fish used for breeding'
        )
        
        # Create a batch for parentage testing
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date() + datetime.timedelta(days=365),
            status='ACTIVE',
            batch_type='STANDARD'
        )


class BroodstockFishModelTests(BroodstockBaseTestCase):
    """Test cases for the BroodstockFish model."""
    
    def setUp(self):
        """Set up test data for BroodstockFish tests."""
        super().setUp()
        
        # Create broodstock fish
        self.fish_traits = {
            'growth_rate': 'high',
            'disease_resistance': 'medium',
            'egg_quality': 'high'
        }
        
        self.broodstock_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits=self.fish_traits,
            health_status='healthy'
        )
    
    def test_broodstock_fish_creation(self):
        """Test that a BroodstockFish instance can be created."""
        self.assertEqual(self.broodstock_fish.container, self.tank)
        self.assertEqual(self.broodstock_fish.traits, self.fish_traits)
        self.assertEqual(self.broodstock_fish.health_status, 'healthy')
    
    def test_broodstock_fish_str_representation(self):
        """Test the string representation of a BroodstockFish."""
        expected_str = f"Fish #{self.broodstock_fish.id} in {self.tank.name}"
        self.assertEqual(str(self.broodstock_fish), expected_str)


class FishMovementModelTests(BroodstockBaseTestCase):
    """Test cases for the FishMovement model."""
    
    def setUp(self):
        """Set up test data for FishMovement tests."""
        super().setUp()
        
        # Create broodstock fish
        self.broodstock_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'growth_rate': 'high'},
            health_status='healthy'
        )
        
        # Create fish movement
        self.fish_movement = FishMovement.objects.create(
            fish=self.broodstock_fish,
            from_container=self.tank,
            to_container=self.pen,
            movement_date=timezone.now(),
            moved_by=self.user,
            notes='Test movement'
        )
    
    def test_fish_movement_creation(self):
        """Test that a FishMovement instance can be created."""
        self.assertEqual(self.fish_movement.fish, self.broodstock_fish)
        self.assertEqual(self.fish_movement.from_container, self.tank)
        self.assertEqual(self.fish_movement.to_container, self.pen)
        self.assertEqual(self.fish_movement.moved_by, self.user)
        self.assertEqual(self.fish_movement.notes, 'Test movement')
    
    def test_fish_movement_str_representation(self):
        """Test the string representation of a FishMovement."""
        expected_str = f"Fish #{self.broodstock_fish.id}: {self.tank.name} → {self.pen.name}"
        self.assertEqual(str(self.fish_movement), expected_str)
    
    def test_container_update_after_movement(self):
        """Test that the fish's container is updated after movement."""
        # Refresh the fish from the database
        self.broodstock_fish.refresh_from_db()
        
        # Check if the container has been updated to the destination container
        self.assertEqual(self.broodstock_fish.container, self.pen)


class BreedingPlanModelTests(BroodstockBaseTestCase):
    """Test cases for the BreedingPlan model."""
    
    def setUp(self):
        """Set up test data for BreedingPlan tests."""
        super().setUp()
        
        # Create breeding plan
        self.start_date = timezone.now()
        self.end_date = self.start_date + datetime.timedelta(days=90)
        
        self.breeding_plan = BreedingPlan.objects.create(
            name='Test Breeding Plan',
            start_date=self.start_date,
            end_date=self.end_date,
            objectives='Test objectives',
            geneticist_notes='Test geneticist notes',
            breeder_instructions='Test breeder instructions',
            created_by=self.user
        )
    
    def test_breeding_plan_creation(self):
        """Test that a BreedingPlan instance can be created."""
        self.assertEqual(self.breeding_plan.name, 'Test Breeding Plan')
        self.assertEqual(self.breeding_plan.objectives, 'Test objectives')
        self.assertEqual(self.breeding_plan.created_by, self.user)
    
    def test_breeding_plan_str_representation(self):
        """Test the string representation of a BreedingPlan."""
        self.assertEqual(str(self.breeding_plan), 'Test Breeding Plan')
    
    def test_is_active_property(self):
        """Test the is_active property of BreedingPlan."""
        # Current plan should be active
        self.assertTrue(self.breeding_plan.is_active)
        
        # Past plan should not be active
        past_start = timezone.now() - datetime.timedelta(days=100)
        past_end = timezone.now() - datetime.timedelta(days=10)
        past_plan = BreedingPlan.objects.create(
            name='Past Plan',
            start_date=past_start,
            end_date=past_end,
            objectives='Past objectives',
            created_by=self.user
        )
        self.assertFalse(past_plan.is_active)
        
        # Future plan should not be active
        future_start = timezone.now() + datetime.timedelta(days=10)
        future_end = timezone.now() + datetime.timedelta(days=100)
        future_plan = BreedingPlan.objects.create(
            name='Future Plan',
            start_date=future_start,
            end_date=future_end,
            objectives='Future objectives',
            created_by=self.user
        )
        self.assertFalse(future_plan.is_active)


class BreedingTraitPriorityModelTests(BroodstockBaseTestCase):
    """Test cases for the BreedingTraitPriority model."""
    
    def setUp(self):
        """Set up test data for BreedingTraitPriority tests."""
        super().setUp()
        
        # Create breeding plan
        self.breeding_plan = BreedingPlan.objects.create(
            name='Test Breeding Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=90),
            objectives='Test objectives',
            created_by=self.user
        )
        
        # Create breeding trait priority
        self.trait_priority = BreedingTraitPriority.objects.create(
            plan=self.breeding_plan,
            trait_name='growth_rate',
            priority_weight=0.8
        )
    
    def test_trait_priority_creation(self):
        """Test that a BreedingTraitPriority instance can be created."""
        self.assertEqual(self.trait_priority.plan, self.breeding_plan)
        self.assertEqual(self.trait_priority.trait_name, 'growth_rate')
        self.assertEqual(self.trait_priority.priority_weight, 0.8)
    
    def test_trait_priority_str_representation(self):
        """Test the string representation of a BreedingTraitPriority."""
        expected_str = f"{self.breeding_plan.name} - Growth Rate: 0.8"
        self.assertEqual(str(self.trait_priority), expected_str)
    
    def test_unique_constraint(self):
        """Test that the unique_together constraint works."""
        # Attempt to create another trait priority with the same plan and trait_name
        with self.assertRaises(Exception):  # Could be IntegrityError or ValidationError
            BreedingTraitPriority.objects.create(
                plan=self.breeding_plan,
                trait_name='growth_rate',  # Same trait name
                priority_weight=0.5
            )


class BreedingPairModelTests(BroodstockBaseTestCase):
    """Test cases for the BreedingPair model."""
    
    def setUp(self):
        """Set up test data for BreedingPair tests."""
        super().setUp()
        
        # Create breeding plan
        self.breeding_plan = BreedingPlan.objects.create(
            name='Test Breeding Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=90),
            objectives='Test objectives',
            created_by=self.user
        )
        
        # Create male and female fish
        self.male_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'male'},
            health_status='healthy'
        )
        
        self.female_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'female'},
            health_status='healthy'
        )
        
        # Create breeding pair
        self.breeding_pair = BreedingPair.objects.create(
            plan=self.breeding_plan,
            male_fish=self.male_fish,
            female_fish=self.female_fish,
            pairing_date=timezone.now(),
            progeny_count=None  # Will be updated after egg production
        )
    
    def test_breeding_pair_creation(self):
        """Test that a BreedingPair instance can be created."""
        self.assertEqual(self.breeding_pair.plan, self.breeding_plan)
        self.assertEqual(self.breeding_pair.male_fish, self.male_fish)
        self.assertEqual(self.breeding_pair.female_fish, self.female_fish)
        self.assertIsNone(self.breeding_pair.progeny_count)
    
    def test_breeding_pair_str_representation(self):
        """Test the string representation of a BreedingPair."""
        expected_str = f"Pair: Male #{self.male_fish.id} × Female #{self.female_fish.id}"
        self.assertEqual(str(self.breeding_pair), expected_str)


class EggProductionModelTests(BroodstockBaseTestCase):
    """Test cases for the EggProduction model."""
    
    def setUp(self):
        """Set up test data for EggProduction tests."""
        super().setUp()
        
        # Create breeding plan
        self.breeding_plan = BreedingPlan.objects.create(
            name='Test Breeding Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=90),
            objectives='Test objectives',
            created_by=self.user
        )
        
        # Create male and female fish
        self.male_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'male'},
            health_status='healthy'
        )
        
        self.female_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'female'},
            health_status='healthy'
        )
        
        # Create breeding pair
        self.breeding_pair = BreedingPair.objects.create(
            plan=self.breeding_plan,
            male_fish=self.male_fish,
            female_fish=self.female_fish,
            pairing_date=timezone.now()
        )
        
        # Create egg production (internal)
        self.internal_egg_production = EggProduction.objects.create(
            pair=self.breeding_pair,
            egg_batch_id='INT-001',
            egg_count=5000,
            production_date=timezone.now(),
            destination_station=self.station,
            source_type='internal'
        )
        
        # Create egg production (external)
        self.external_egg_production = EggProduction.objects.create(
            pair=None,  # No pair for external eggs
            egg_batch_id='EXT-001',
            egg_count=10000,
            production_date=timezone.now(),
            destination_station=self.station,
            source_type='external'
        )
    
    def test_egg_production_creation(self):
        """Test that EggProduction instances can be created."""
        # Test internal egg production
        self.assertEqual(self.internal_egg_production.pair, self.breeding_pair)
        self.assertEqual(self.internal_egg_production.egg_count, 5000)
        self.assertEqual(self.internal_egg_production.source_type, 'internal')
        
        # Test external egg production
        self.assertIsNone(self.external_egg_production.pair)
        self.assertEqual(self.external_egg_production.egg_count, 10000)
        self.assertEqual(self.external_egg_production.source_type, 'external')
    
    def test_egg_production_str_representation(self):
        """Test the string representation of EggProduction."""
        expected_internal_str = f"{self.internal_egg_production.egg_batch_id} - 5000 eggs (internal)"
        self.assertEqual(str(self.internal_egg_production), expected_internal_str)
        
        expected_external_str = f"{self.external_egg_production.egg_batch_id} - 10000 eggs (external)"
        self.assertEqual(str(self.external_egg_production), expected_external_str)
    
    def test_validation(self):
        """Test the validation logic for EggProduction."""
        # Test that internal eggs must have a pair
        with self.assertRaises(ValidationError):
            invalid_internal = EggProduction(
                pair=None,  # Missing pair
                egg_batch_id='INVALID-001',
                egg_count=5000,
                production_date=timezone.now(),
                destination_station=self.station,
                source_type='internal'  # But source type is internal
            )
            invalid_internal.clean()
        
        # Test that external eggs cannot have a pair
        with self.assertRaises(ValidationError):
            invalid_external = EggProduction(
                pair=self.breeding_pair,  # Has a pair
                egg_batch_id='INVALID-002',
                egg_count=10000,
                production_date=timezone.now(),
                destination_station=self.station,
                source_type='external'  # But source type is external
            )
            invalid_external.clean()


class EggSupplierModelTests(BroodstockBaseTestCase):
    """Test cases for the EggSupplier model."""
    
    def setUp(self):
        """Set up test data for EggSupplier tests."""
        super().setUp()
        
        # Create egg supplier
        self.egg_supplier = EggSupplier.objects.create(
            name='Test Supplier',
            contact_details='Contact details for test supplier',
            certifications='ISO 9001, ASC'
        )
    
    def test_egg_supplier_creation(self):
        """Test that an EggSupplier instance can be created."""
        self.assertEqual(self.egg_supplier.name, 'Test Supplier')
        self.assertEqual(self.egg_supplier.contact_details, 'Contact details for test supplier')
        self.assertEqual(self.egg_supplier.certifications, 'ISO 9001, ASC')
    
    def test_egg_supplier_str_representation(self):
        """Test the string representation of an EggSupplier."""
        self.assertEqual(str(self.egg_supplier), 'Test Supplier')


class ExternalEggBatchModelTests(BroodstockBaseTestCase):
    """Test cases for the ExternalEggBatch model."""
    
    def setUp(self):
        """Set up test data for ExternalEggBatch tests."""
        super().setUp()
        
        # Create egg supplier
        self.egg_supplier = EggSupplier.objects.create(
            name='Test Supplier',
            contact_details='Contact details for test supplier',
            certifications='ISO 9001, ASC'
        )
        
        # Create external egg production
        self.external_egg_production = EggProduction.objects.create(
            pair=None,
            egg_batch_id='EXT-001',
            egg_count=10000,
            production_date=timezone.now(),
            destination_station=self.station,
            source_type='external'
        )
        
        # Create external egg batch
        self.external_egg_batch = ExternalEggBatch.objects.create(
            egg_production=self.external_egg_production,
            supplier=self.egg_supplier,
            batch_number='SUP-001',
            provenance_data='Provenance data for test batch'
        )
    
    def test_external_egg_batch_creation(self):
        """Test that an ExternalEggBatch instance can be created."""
        self.assertEqual(self.external_egg_batch.egg_production, self.external_egg_production)
        self.assertEqual(self.external_egg_batch.supplier, self.egg_supplier)
        self.assertEqual(self.external_egg_batch.batch_number, 'SUP-001')
        self.assertEqual(self.external_egg_batch.provenance_data, 'Provenance data for test batch')
    
    def test_external_egg_batch_str_representation(self):
        """Test the string representation of an ExternalEggBatch."""
        expected_str = f"{self.egg_supplier.name} - {self.external_egg_batch.batch_number}"
        self.assertEqual(str(self.external_egg_batch), expected_str)


class MaintenanceTaskModelTests(BroodstockBaseTestCase):
    """Test cases for the MaintenanceTask model."""
    
    def setUp(self):
        """Set up test data for MaintenanceTask tests."""
        super().setUp()
        
        # Create scheduled maintenance task
        self.scheduled_task = MaintenanceTask.objects.create(
            container=self.tank,
            task_type='cleaning',
            scheduled_date=timezone.now() + datetime.timedelta(days=7),
            notes='Scheduled cleaning',
            created_by=self.user
        )
        
        # Create completed maintenance task
        self.completed_task = MaintenanceTask.objects.create(
            container=self.tank,
            task_type='repair',
            scheduled_date=timezone.now() - datetime.timedelta(days=7),
            completed_date=timezone.now() - datetime.timedelta(days=5),
            notes='Completed repair',
            created_by=self.user
        )
    
    def test_maintenance_task_creation(self):
        """Test that MaintenanceTask instances can be created."""
        # Test scheduled task
        self.assertEqual(self.scheduled_task.container, self.tank)
        self.assertEqual(self.scheduled_task.task_type, 'cleaning')
        self.assertIsNone(self.scheduled_task.completed_date)
        
        # Test completed task
        self.assertEqual(self.completed_task.container, self.tank)
        self.assertEqual(self.completed_task.task_type, 'repair')
        self.assertIsNotNone(self.completed_task.completed_date)
    
    def test_maintenance_task_str_representation(self):
        """Test the string representation of MaintenanceTask."""
        expected_scheduled_str = f"Cleaning - {self.tank.name} ({self.scheduled_task.scheduled_date.date()})"
        self.assertEqual(str(self.scheduled_task), expected_scheduled_str)
        
        expected_completed_str = f"Repair - {self.tank.name} ({self.completed_task.scheduled_date.date()})"
        self.assertEqual(str(self.completed_task), expected_completed_str)
    
    def test_is_overdue_property(self):
        """Test the is_overdue property of MaintenanceTask."""
        # Future task should not be overdue
        self.assertFalse(self.scheduled_task.is_overdue)
        
        # Completed task should not be overdue
        self.assertFalse(self.completed_task.is_overdue)
        
        # Create an overdue task
        overdue_task = MaintenanceTask.objects.create(
            container=self.tank,
            task_type='inspection',
            scheduled_date=timezone.now() - datetime.timedelta(days=1),
            notes='Overdue inspection',
            created_by=self.user
        )
        self.assertTrue(overdue_task.is_overdue)


class BatchParentageModelTests(BroodstockBaseTestCase):
    """Test cases for the BatchParentage model."""
    
    def setUp(self):
        """Set up test data for BatchParentage tests."""
        super().setUp()
        
        # Create breeding pair
        self.male_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'male'},
            health_status='healthy'
        )
        
        self.female_fish = BroodstockFish.objects.create(
            container=self.tank,
            traits={'gender': 'female'},
            health_status='healthy'
        )
        
        self.breeding_plan = BreedingPlan.objects.create(
            name='Test Breeding Plan',
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=90),
            objectives='Test objectives',
            created_by=self.user
        )
        
        self.breeding_pair = BreedingPair.objects.create(
            plan=self.breeding_plan,
            male_fish=self.male_fish,
            female_fish=self.female_fish,
            pairing_date=timezone.now()
        )
        
        # Create egg production
        self.egg_production = EggProduction.objects.create(
            pair=self.breeding_pair,
            egg_batch_id='INT-001',
            egg_count=5000,
            production_date=timezone.now(),
            destination_station=self.station,
            source_type='internal'
        )
        
        # Create batch parentage
        self.batch_parentage = BatchParentage.objects.create(
            batch=self.batch,
            egg_production=self.egg_production,
            assignment_date=timezone.now()
        )
    
    def test_batch_parentage_creation(self):
        """Test that a BatchParentage instance can be created."""
        self.assertEqual(self.batch_parentage.batch, self.batch)
        self.assertEqual(self.batch_parentage.egg_production, self.egg_production)
    
    def test_batch_parentage_str_representation(self):
        """Test the string representation of a BatchParentage."""
        expected_str = f"Batch {self.batch.batch_number} ← {self.egg_production.egg_batch_id}"
        self.assertEqual(str(self.batch_parentage), expected_str)
