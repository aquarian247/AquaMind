"""
Tests for the batch app API serializers.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from decimal import Decimal, ROUND_HALF_UP
import datetime
import statistics  # Added for std dev calculation

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    BatchComposition,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.batch.api.serializers import (
    SpeciesSerializer,
    LifeCycleStageSerializer,
    BatchSerializer,
    BatchContainerAssignmentSerializer,
    BatchCompositionSerializer,
    BatchTransferSerializer,
    MortalityEventSerializer,
    GrowthSampleSerializer
)
from apps.infrastructure.models import (
    Geography,
    Area,
    ContainerType,
    Container
)


class SpeciesSerializerTest(TestCase):
    """Test the Species serializer."""

    def setUp(self):
        """Set up test data."""
        self.valid_species_data = {
            'name': 'Atlantic Salmon',
            'scientific_name': 'Salmo salar',
            'description': 'Common farmed salmon species',
            'optimal_temperature_min': Decimal('4.00'),
            'optimal_temperature_max': Decimal('14.00'),
            'optimal_oxygen_min': Decimal('7.00'),
            'optimal_ph_min': Decimal('6.50'),
            'optimal_ph_max': Decimal('8.50')
        }

    def test_valid_species_serialization(self):
        """Test species serialization with valid data."""
        serializer = SpeciesSerializer(data=self.valid_species_data)
        self.assertTrue(serializer.is_valid())
        species = serializer.save()
        self.assertEqual(species.name, 'Atlantic Salmon')
        self.assertEqual(species.scientific_name, 'Salmo salar')

    def test_temperature_range_validation(self):
        """Test validation of temperature range."""
        invalid_data = self.valid_species_data.copy()
        invalid_data['optimal_temperature_min'] = Decimal('15.00')
        invalid_data['optimal_temperature_max'] = Decimal('10.00')
        
        serializer = SpeciesSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('optimal_temperature_min', serializer.errors)

    def test_ph_range_validation(self):
        """Test validation of pH range."""
        invalid_data = self.valid_species_data.copy()
        invalid_data['optimal_ph_min'] = Decimal('9.00')
        invalid_data['optimal_ph_max'] = Decimal('7.00')
        
        serializer = SpeciesSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('optimal_ph_min', serializer.errors)


class LifeCycleStageSerializerTest(TestCase):
    """Test the LifeCycleStage serializer."""

    def setUp(self):
        """Set up test data."""
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar',
            description='Common farmed salmon species'
        )
        
        self.valid_lifecycle_stage_data = {
            'name': 'Fry',
            'species': self.species.id,
            'order': 2,
            'description': 'Early stage after hatching',
            'expected_weight_min_g': Decimal('0.10'),
            'expected_weight_max_g': Decimal('5.00'),
            'expected_length_min_cm': Decimal('2.00'),
            'expected_length_max_cm': Decimal('8.00')
        }

    def test_valid_lifecycle_stage_serialization(self):
        """Test lifecycle stage serialization with valid data."""
        serializer = LifeCycleStageSerializer(data=self.valid_lifecycle_stage_data)
        self.assertTrue(serializer.is_valid())
        lifecycle_stage = serializer.save()
        self.assertEqual(lifecycle_stage.name, 'Fry')
        self.assertEqual(lifecycle_stage.order, 2)
        self.assertEqual(lifecycle_stage.species, self.species)

    def test_weight_range_validation(self):
        """Test validation of weight range."""
        invalid_data = self.valid_lifecycle_stage_data.copy()
        invalid_data['expected_weight_min_g'] = Decimal('6.00')
        invalid_data['expected_weight_max_g'] = Decimal('4.00')
        
        serializer = LifeCycleStageSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expected_weight_min_g', serializer.errors)

    def test_length_range_validation(self):
        """Test validation of length range."""
        invalid_data = self.valid_lifecycle_stage_data.copy()
        invalid_data['expected_length_min_cm'] = Decimal('10.00')
        invalid_data['expected_length_max_cm'] = Decimal('5.00')
        
        serializer = LifeCycleStageSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expected_length_min_cm', serializer.errors)


class BatchSerializerTest(TestCase):
    """Test the Batch serializer."""

    def setUp(self):
        """Set up test data."""
        # Create Species
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        # Create Lifecycle Stages
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        self.different_species = Species.objects.create(
            name='Rainbow Trout',
            scientific_name='Oncorhynchus mykiss'
        )
        
        self.different_lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry Stage',  # Changed name to avoid unique constraint
            species=self.different_species,
            order=2
        )
        
        # Create Geography and Area
        self.geography = Geography.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=7.0,
            max_biomass=10000
        )
        
        # Create Container Type and Container
        self.container_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=100,
            description='Standard tank for fry'
        )
        
        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=80,
            max_biomass_kg=500,
            active=True
        )
        
        # Valid batch data
        self.valid_batch_data = {
            'batch_number': 'BATCH001',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'population_count': 10000,
            'avg_weight_g': Decimal('2.50'),
            'start_date': datetime.date.today(),
            'expected_end_date': datetime.date.today() + datetime.timedelta(days=30),
            'notes': 'Test batch'
        }

    def test_valid_batch_serialization(self):
        """Test batch serialization with valid data."""
        serializer = BatchSerializer(data=self.valid_batch_data)
        self.assertTrue(serializer.is_valid())
        batch = serializer.save()
        self.assertEqual(batch.batch_number, 'BATCH001')
        self.assertEqual(batch.species, self.species)
        self.assertEqual(batch.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(batch.batch_type, 'STANDARD')
        self.assertEqual(batch.population_count, 10000)
        self.assertEqual(batch.avg_weight_g, Decimal('2.50'))
        self.assertEqual(batch.biomass_kg, Decimal('25.00'))  # 10000 * 2.5g / 1000

    def test_lifecycle_stage_species_validation(self):
        """Test validation that lifecycle stage belongs to correct species."""
        invalid_data = self.valid_batch_data.copy()
        invalid_data['lifecycle_stage'] = self.different_lifecycle_stage.id
        
        serializer = BatchSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('lifecycle_stage', serializer.errors)

    def test_batch_container_assignment(self):
        """Test creating a batch and assigning it to a container."""
        # Create a batch that is within capacity limits
        batch = Batch.objects.create(
            batch_number='BATCH002',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            population_count=10000,
            avg_weight_g=Decimal('40.00'),  # 400 kg total
            biomass_kg=Decimal('400.00'),
            start_date=datetime.date.today()
        )
        
        # Now test creating a container assignment for this batch
        from apps.batch.models import BatchContainerAssignment
        
        # This should work - creating an assignment within container capacity
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=10000,
            biomass_kg=Decimal('400.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        self.assertEqual(assignment.batch, batch)
        self.assertEqual(assignment.container, self.container)
        self.assertEqual(assignment.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(assignment.population_count, 10000)

    def test_end_date_validation(self):
        """Test validation that end date is after start date."""
        invalid_data = self.valid_batch_data.copy()
        invalid_data['expected_end_date'] = datetime.date.today() - datetime.timedelta(days=5)
        
        serializer = BatchSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expected_end_date', serializer.errors)


class BatchTransferSerializerTest(TestCase):
    """Test the BatchTransfer serializer."""

    def setUp(self):
        """Set up test data."""
        # Create Species and Lifecycle Stages
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.lifecycle_stage1 = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        self.lifecycle_stage2 = LifeCycleStage.objects.create(
            name='Parr',
            species=self.species,
            order=3
        )
        
        # Create Geography and Area
        self.geography = Geography.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=7.0,
            max_biomass=10000
        )
        
        # Create Container Types and Containers
        self.container_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=100
        )
        
        self.container1 = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=80,
            max_biomass_kg=500
        )
        
        self.container2 = Container.objects.create(
            name='Tank 2',
            container_type=self.container_type,
            area=self.area,
            volume_m3=100,
            max_biomass_kg=600
        )
        
        # Create Batches
        self.source_batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage1,
            status='ACTIVE',
            batch_type='STANDARD',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today()
        )
        
        # Create a container assignment for the source batch
        from apps.batch.models import BatchContainerAssignment
        self.source_assignment = BatchContainerAssignment.objects.create(
            batch=self.source_batch,
            container=self.container1,
            lifecycle_stage=self.lifecycle_stage1,
            population_count=10000,
            biomass_kg=Decimal('25.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        self.destination_batch = Batch.objects.create(
            batch_number='BATCH002',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage2,
            status='ACTIVE',
            batch_type='STANDARD',
            population_count=5000,
            avg_weight_g=Decimal('10.00'),
            biomass_kg=Decimal('50.00'),
            start_date=datetime.date.today()
        )
        
        # Create a container assignment for the destination batch
        self.destination_assignment = BatchContainerAssignment.objects.create(
            batch=self.destination_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage2,
            population_count=5000,
            biomass_kg=Decimal('50.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # Valid transfer data
        self.valid_transfer_data = {
            'source_batch': self.source_batch.id,
            'destination_batch': self.destination_batch.id,
            'transfer_type': 'CONTAINER',
            'transfer_date': datetime.date.today(),
            'source_count': 10000,
            'transferred_count': 5000,
            'mortality_count': 50,
            'source_biomass_kg': Decimal('25.00'),
            'transferred_biomass_kg': Decimal('12.00'),
            'source_lifecycle_stage': self.lifecycle_stage1.id,
            'destination_lifecycle_stage': self.lifecycle_stage1.id,
            'source_assignment': self.source_assignment.id,
            'destination_assignment': self.destination_assignment.id,
            'notes': 'Test transfer'
        }

    def test_valid_transfer_serialization(self):
        """Test batch transfer serialization with valid data."""
        serializer = BatchTransferSerializer(data=self.valid_transfer_data)
        self.assertTrue(serializer.is_valid())
        transfer = serializer.save()
        self.assertEqual(transfer.source_batch, self.source_batch)
        self.assertEqual(transfer.destination_batch, self.destination_batch)
        self.assertEqual(transfer.transfer_type, 'CONTAINER')
        self.assertEqual(transfer.transferred_count, 5000)
        self.assertEqual(transfer.transferred_biomass_kg, Decimal('12.00'))

    def test_transfer_count_validation(self):
        """Test validation that transfer count doesn't exceed source population."""
        invalid_data = self.valid_transfer_data.copy()
        invalid_data['transferred_count'] = 12000  # More than source batch population
        
        serializer = BatchTransferSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('transferred_count', serializer.errors)

    def test_transfer_biomass_validation(self):
        """Test validation that transfer biomass doesn't exceed source biomass."""
        invalid_data = self.valid_transfer_data.copy()
        invalid_data['transferred_biomass_kg'] = Decimal('30.00')  # More than source batch biomass
        
        serializer = BatchTransferSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('transferred_biomass_kg', serializer.errors)

    def test_transfer_type_validation(self):
        """Test validation of required fields based on transfer type."""
        # Test container transfer without destination assignment
        invalid_data = self.valid_transfer_data.copy()
        invalid_data['destination_assignment'] = None
        
        serializer = BatchTransferSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('destination_assignment', serializer.errors)
        
        # Test lifecycle transfer without destination lifecycle stage
        invalid_data = self.valid_transfer_data.copy()
        invalid_data['transfer_type'] = 'LIFECYCLE'
        invalid_data['destination_lifecycle_stage'] = None
        
        serializer = BatchTransferSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('destination_lifecycle_stage', serializer.errors)


class MortalityEventSerializerTest(TestCase):
    """Test the MortalityEvent serializer."""

    def setUp(self):
        """Set up test data."""
        # Create Species and Lifecycle Stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        # Create Geography and Area
        self.geography = Geography.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=7.0,
            max_biomass=10000
        )
        
        # Create Container Type and Container
        self.container_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=100
        )
        
        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=80,
            max_biomass_kg=500
        )
        
        # Create Batch
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            batch_type='STANDARD',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today()
        )
        
        # Create BatchContainerAssignment
        from apps.batch.models import BatchContainerAssignment
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=10000,
            biomass_kg=Decimal('25.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # Valid mortality event data
        self.valid_mortality_data = {
            'batch': self.batch.id,
            'event_date': datetime.date.today(),
            'count': 100,
            'biomass_kg': Decimal('0.25'),
            'cause': 'DISEASE',
            'description': 'Test mortality event'
        }

    def test_valid_mortality_serialization(self):
        """Test mortality event serialization with valid data."""
        serializer = MortalityEventSerializer(data=self.valid_mortality_data)
        self.assertTrue(serializer.is_valid(), msg=f"Errors: {serializer.errors}")
        mortality = serializer.save()
        self.assertEqual(mortality.batch, self.batch)
        self.assertEqual(mortality.count, 100)
        self.assertEqual(mortality.biomass_kg, Decimal('0.25'))
        self.assertEqual(mortality.cause, 'DISEASE')

    def test_mortality_count_validation(self):
        """Test validation that mortality count doesn't exceed batch population."""
        # The MortalityEventSerializer needs a saved batch to validate against
        # First save a valid mortality event
        serializer = MortalityEventSerializer(data=self.valid_mortality_data)
        self.assertTrue(serializer.is_valid(), msg=f"Errors: {serializer.errors}")
        serializer.save()
        
        # Now test with invalid count
        invalid_data = self.valid_mortality_data.copy()
        invalid_data['count'] = 15000  # More than batch population
        
        serializer = MortalityEventSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('count', serializer.errors)

    def test_mortality_biomass_validation(self):
        """Test validation that mortality biomass doesn't exceed batch biomass."""
        invalid_data = self.valid_mortality_data.copy()
        invalid_data['biomass_kg'] = Decimal('30.00')  # More than batch biomass
        
        serializer = MortalityEventSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('biomass_kg', serializer.errors)


class BatchContainerAssignmentSerializerTest(TestCase):
    """Test the BatchContainerAssignment serializer."""

    def setUp(self):
        """Set up test data."""
        # Create Species and Lifecycle Stages
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        # Create Geography and Area
        self.geography = Geography.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=7.0,
            max_biomass=10000
        )
        
        # Create Container Type and Container
        self.container_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=100,
            description='Standard tank for fry'
        )
        
        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=80,
            max_biomass_kg=500,
            active=True
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        # Valid assignment data
        self.valid_assignment_data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 5000,
            'biomass_kg': Decimal('12.50'),
            'assignment_date': datetime.date.today(),
            'is_active': True,
            'notes': 'Test assignment'
        }
    
    def test_valid_assignment_serialization(self):
        """Test assignment serialization with valid data."""
        serializer = BatchContainerAssignmentSerializer(data=self.valid_assignment_data)
        self.assertTrue(serializer.is_valid())
        assignment = serializer.save()
        self.assertEqual(assignment.batch, self.batch)
        self.assertEqual(assignment.container, self.container)
        self.assertEqual(assignment.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(assignment.population_count, 5000)
        self.assertEqual(assignment.biomass_kg, Decimal('12.50'))
        self.assertTrue(assignment.is_active)
    
    def test_container_capacity_validation(self):
        """Test validation that container capacity is not exceeded."""
        # Create an existing assignment that uses most of the container capacity
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=5000,
            biomass_kg=Decimal('450.00'),  # 450 kg of 500 kg capacity
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # This new assignment would exceed the container capacity (450 + 60 > 500)
        invalid_data = self.valid_assignment_data.copy()
        invalid_data['biomass_kg'] = Decimal('60.00')  
        
        serializer = BatchContainerAssignmentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('biomass_kg', serializer.errors)
    
    def test_batch_population_validation(self):
        """Test validation that batch population is not exceeded."""
        # Create an existing assignment that uses part of the batch population
        BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=8000,  # 8000 of 10000 total
            biomass_kg=Decimal('20.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # This new assignment would exceed the batch population (8000 + 3000 > 10000)
        invalid_data = self.valid_assignment_data.copy()
        invalid_data['population_count'] = 3000
        
        serializer = BatchContainerAssignmentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('population_count', serializer.errors)


class BatchCompositionSerializerTest(TestCase):
    """Test the BatchComposition serializer."""

    def setUp(self):
        """Set up test data."""
        # Create Species and Lifecycle Stages
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        # Create batches
        self.source_batch = Batch.objects.create(
            batch_number='SOURCE001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        self.mixed_batch = Batch.objects.create(
            batch_number='MIXED001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='ACTIVE',
            population_count=1000,  # Initial population count
            avg_weight_g=Decimal('3.00'),
            biomass_kg=Decimal('3.00'),
            start_date=datetime.date.today(),
            batch_type='MIXED'
        )
        
        # Valid composition data
        self.valid_composition_data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch.id,
            'percentage': Decimal('20.00'),
            'population_count': 1000,
            'biomass_kg': Decimal('2.50')
        }
    
    def test_valid_composition_serialization(self):
        """Test composition serialization with valid data."""
        serializer = BatchCompositionSerializer(data=self.valid_composition_data)
        self.assertTrue(serializer.is_valid())
        composition = serializer.save()
        self.assertEqual(composition.mixed_batch, self.mixed_batch)
        self.assertEqual(composition.source_batch, self.source_batch)
        self.assertEqual(composition.percentage, Decimal('20.00'))
        self.assertEqual(composition.population_count, 1000)
        self.assertEqual(composition.biomass_kg, Decimal('2.50'))
    
    def test_population_count_validation(self):
        """Test validation that population count doesn't exceed source batch population."""
        invalid_data = self.valid_composition_data.copy()
        invalid_data['population_count'] = 11000  # Source batch only has 10000
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('population_count', serializer.errors)
    
    def test_percentage_validation(self):
        """Test validation that percentage is between 0 and 100."""
        invalid_data = self.valid_composition_data.copy()
        invalid_data['percentage'] = Decimal('120.00')  # Percentage > 100
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('percentage', serializer.errors)
        
        invalid_data['percentage'] = Decimal('-10.00')  # Percentage < 0
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('percentage', serializer.errors)


class GrowthSampleSerializerTest(TestCase):
    """Test the GrowthSample serializer."""

    def setUp(self):
        """Set up test data."""
        self.species = Species.objects.create(name="Trout")
        self.stage = LifeCycleStage.objects.create(species=self.species, name="Fingerling", order=1)
        self.batch = Batch.objects.create(
            batch_number='B001',
            species=self.species,
            start_date=datetime.date.today() - datetime.timedelta(days=30),
            initial_count=1000,
            initial_biomass_kg=Decimal('10.0')
        )
        self.container = Container.objects.create(name='Tank 1', volume_m3=Decimal('50.0'))
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            assignment_date=datetime.date.today() - datetime.timedelta(days=30),
            population_count=1000, # Population for validation
            biomass_kg=Decimal('10.0'),
            lifecycle_stage=self.stage
        )

        self.valid_sample_data = {
            'assignment': self.assignment.id,
            'sample_date': datetime.date.today(),
            'sample_size': 10,
            'avg_weight_g': Decimal('3.00'),
            'avg_length_cm': Decimal('5.50'), # Required if no individual lengths
            'std_deviation_weight': Decimal('0.50'),
            'std_deviation_length': Decimal('0.25'), # Required if no individual lengths
            'min_weight_g': Decimal('2.00'),
            'max_weight_g': Decimal('4.00'),
            # condition_factor will be calculated by model save if possible
            'notes': 'Routine sample'
        }

        self.lengths_data = [Decimal('5.0'), Decimal('5.5'), Decimal('6.0')]
        self.weights_data = [Decimal('2.8'), Decimal('3.0'), Decimal('3.2')]

        self.sample_data_with_lengths = {
            'assignment': self.assignment.id,
            'sample_date': datetime.date.today(),
            'sample_size': len(self.lengths_data),
            'individual_lengths': [str(l) for l in self.lengths_data],
            # avg_length_cm, std_deviation_length, condition_factor should be calculated
            # Provide avg_weight_g as it's not calculable from lengths alone
            'avg_weight_g': Decimal('3.0'),
            'notes': 'Sample with individual lengths'
        }

        self.sample_data_with_weights = {
            'assignment': self.assignment.id,
            'sample_date': datetime.date.today(),
            'sample_size': len(self.weights_data),
            'individual_weights': [str(w) for w in self.weights_data],
            # avg_weight_g, std_deviation_weight should be calculated
            # Provide avg_length_cm as it's not calculable from weights alone
            'avg_length_cm': Decimal('5.5'),
            'notes': 'Sample with individual weights'
        }

        self.sample_data_with_both = {
            'assignment': self.assignment.id,
            'sample_date': datetime.date.today(),
            'sample_size': len(self.weights_data),
            'individual_weights': [str(w) for w in self.weights_data],
            'individual_lengths': [str(l) for l in self.lengths_data],
            # All stats should be calculated
            'notes': 'Sample with individual weights and lengths'
        }

    def test_valid_sample_serialization(self):
        """Test basic sample serialization with manually entered stats."""
        serializer = GrowthSampleSerializer(data=self.valid_sample_data)
        self.assertTrue(serializer.is_valid(), msg=f"Serializer errors: {serializer.errors}")
        sample = serializer.save()
        self.assertEqual(sample.sample_size, 10)
        self.assertEqual(sample.avg_weight_g, Decimal('3.00'))
        self.assertEqual(sample.avg_length_cm, Decimal('5.50'))
        self.assertIsNotNone(sample.condition_factor) # Should be calculated by model save

    def test_validation(self):
        """Test various validation rules."""
        # 1. Sample size exceeds population
        invalid_data = self.valid_sample_data.copy()
        invalid_data['sample_size'] = 2000 # Exceeds assignment.population_count (1000)
        serializer = GrowthSampleSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sample_size', serializer.errors)

        # 2. Min weight > Max weight
        invalid_data = self.valid_sample_data.copy()
        invalid_data['min_weight_g'] = Decimal('5.00')
        invalid_data['max_weight_g'] = Decimal('4.00')
        serializer = GrowthSampleSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('min_weight_g', serializer.errors)

        # 3. Sample size mismatch with individual_lengths
        invalid_data = self.sample_data_with_lengths.copy()
        invalid_data['sample_size'] = 5 # Doesn't match len(individual_lengths) which is 3
        serializer = GrowthSampleSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sample_size', serializer.errors)

        # 4. Sample size mismatch with individual_weights
        invalid_data = self.sample_data_with_weights.copy()
        invalid_data['sample_size'] = 1 # Doesn't match len(individual_weights) which is 3
        serializer = GrowthSampleSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sample_size', serializer.errors)

        # 5. Mismatched lengths of individual_weights and individual_lengths
        invalid_data = self.sample_data_with_both.copy()
        invalid_data['individual_lengths'] = ['5.0', '5.5'] # Length 2
        # individual_weights has length 3
        serializer = GrowthSampleSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('individual_measurements', serializer.errors)


    def test_valid_sample_serialization_with_lengths(self):
        """Test calculating length stats from individual_lengths."""
        serializer = GrowthSampleSerializer(data=self.sample_data_with_lengths)
        self.assertTrue(serializer.is_valid(), msg=f"Serializer errors: {serializer.errors}")
        sample = serializer.save()

        expected_avg_length = statistics.mean(self.lengths_data)
        expected_std_dev_length = statistics.stdev(self.lengths_data)
        # K factor should be calculated by model's save as avg_weight provided
        expected_k = (100 * self.sample_data_with_lengths['avg_weight_g']) / (expected_avg_length ** 3)

        quantizer = Decimal('0.01')
        self.assertEqual(sample.avg_length_cm.quantize(quantizer), expected_avg_length.quantize(quantizer))
        self.assertEqual(sample.std_deviation_length.quantize(quantizer), expected_std_dev_length.quantize(quantizer))
        self.assertEqual(sample.avg_weight_g, self.sample_data_with_lengths['avg_weight_g']) # Should remain as provided
        self.assertIsNone(sample.std_deviation_weight) # Not calculated
        self.assertIsNotNone(sample.condition_factor)
        self.assertEqual(sample.condition_factor.quantize(quantizer), expected_k.quantize(quantizer))

    def test_valid_sample_serialization_with_weights(self):
        """Test calculating weight stats from individual_weights."""
        serializer = GrowthSampleSerializer(data=self.sample_data_with_weights)
        self.assertTrue(serializer.is_valid(), msg=f"Serializer errors: {serializer.errors}")
        sample = serializer.save()

        expected_avg_weight = statistics.mean(self.weights_data)
        expected_std_dev_weight = statistics.stdev(self.weights_data)
        # K factor should be calculated by model's save as avg_length provided
        expected_k = (100 * expected_avg_weight) / (self.sample_data_with_weights['avg_length_cm'] ** 3)

        quantizer = Decimal('0.01')
        self.assertEqual(sample.avg_weight_g.quantize(quantizer), expected_avg_weight.quantize(quantizer))
        self.assertEqual(sample.std_deviation_weight.quantize(quantizer), expected_std_dev_weight.quantize(quantizer))
        self.assertEqual(sample.avg_length_cm, self.sample_data_with_weights['avg_length_cm']) # Should remain as provided
        self.assertIsNone(sample.std_deviation_length) # Not calculated
        self.assertIsNotNone(sample.condition_factor)
        self.assertEqual(sample.condition_factor.quantize(quantizer), expected_k.quantize(quantizer))

    def test_valid_sample_serialization_with_both(self):
        """Test calculating all stats when both individual lists are provided."""
        serializer = GrowthSampleSerializer(data=self.sample_data_with_both)
        self.assertTrue(serializer.is_valid(), msg=f"Serializer errors: {serializer.errors}")
        sample = serializer.save()

        expected_avg_length = statistics.mean(self.lengths_data)
        expected_std_dev_length = statistics.stdev(self.lengths_data)
        expected_avg_weight = statistics.mean(self.weights_data)
        expected_std_dev_weight = statistics.stdev(self.weights_data)

        # Calculate expected average K from individuals
        k_factors = [(100 * w) / (l ** 3) for w, l in zip(self.weights_data, self.lengths_data) if l > 0]
        expected_avg_k = statistics.mean(k_factors) if k_factors else None

        quantizer = Decimal('0.01')
        self.assertEqual(sample.avg_length_cm.quantize(quantizer), expected_avg_length.quantize(quantizer))
        self.assertEqual(sample.std_deviation_length.quantize(quantizer), expected_std_dev_length.quantize(quantizer))
        self.assertEqual(sample.avg_weight_g.quantize(quantizer), expected_avg_weight.quantize(quantizer))
        self.assertEqual(sample.std_deviation_weight.quantize(quantizer), expected_std_dev_weight.quantize(quantizer))
        self.assertIsNotNone(sample.condition_factor)
        if expected_avg_k:
            self.assertEqual(sample.condition_factor.quantize(quantizer), expected_avg_k.quantize(quantizer))
        else:
            self.assertIsNone(sample.condition_factor)


    def test_update_sample_with_lengths(self):
        """Test updating a sample with new individual_lengths."""
        # First, create a sample using manual stats
        serializer = GrowthSampleSerializer(data=self.valid_sample_data)
        self.assertTrue(serializer.is_valid())
        sample = serializer.save()
        original_avg_length = sample.avg_length_cm
        original_k_factor = sample.condition_factor

        # Now, prepare update data with individual_lengths
        update_lengths = [Decimal('6.0'), Decimal('6.5')] # New lengths
        # Provide an avg_weight_g for K factor calculation update
        # If avg_weight is not updated, K will use the original weight
        update_avg_weight = sample.avg_weight_g # Use original weight for this test

        update_data = {
            'individual_lengths': [str(l) for l in update_lengths],
            'sample_size': len(update_lengths) # Match new lengths
            # 'avg_weight_g': update_avg_weight, # Not updating weight here
        }

        update_serializer = GrowthSampleSerializer(instance=sample, data=update_data, partial=True)
        self.assertTrue(update_serializer.is_valid(), msg=f"Update serializer errors: {update_serializer.errors}")
        updated_sample = update_serializer.save()

        # Verify calculated fields after update
        expected_avg_length = statistics.mean(update_lengths)
        expected_std_dev = statistics.stdev(update_lengths) if len(update_lengths) > 1 else Decimal('0.00')
        # K factor recalculation depends on the model's save method using the *new* avg_length
        # and the *existing* avg_weight (since we didn't provide a new one or individual_weights)
        expected_condition_factor = (Decimal('100') * updated_sample.avg_weight_g) / (expected_avg_length ** 3)

        quantizer = Decimal('0.01')
        self.assertEqual(updated_sample.avg_length_cm.quantize(quantizer), expected_avg_length.quantize(quantizer))
        self.assertEqual(updated_sample.std_deviation_length.quantize(quantizer), expected_std_dev.quantize(quantizer))
        self.assertNotEqual(updated_sample.avg_length_cm, original_avg_length) # Ensure length changed
        # Check if K factor was recalculated (it should if avg_length changed)
        self.assertIsNotNone(updated_sample.condition_factor)
        # self.assertNotEqual(updated_sample.condition_factor.quantize(quantizer), original_k_factor.quantize(quantizer)) # Might fail if rounding is identical
        self.assertEqual(updated_sample.condition_factor.quantize(quantizer), expected_condition_factor.quantize(quantizer))

    def test_update_sample_with_weights(self):
        """Test updating a sample with new individual_weights."""
        serializer = GrowthSampleSerializer(data=self.valid_sample_data)
        self.assertTrue(serializer.is_valid())
        sample = serializer.save()
        original_avg_weight = sample.avg_weight_g

        update_weights = [Decimal('3.5'), Decimal('4.0')] # New weights
        update_data = {
            'individual_weights': [str(w) for w in update_weights],
            'sample_size': len(update_weights)
        }

        update_serializer = GrowthSampleSerializer(instance=sample, data=update_data, partial=True)
        self.assertTrue(update_serializer.is_valid(), msg=f"Update serializer errors: {update_serializer.errors}")
        updated_sample = update_serializer.save()

        expected_avg_weight = statistics.mean(update_weights)
        expected_std_dev = statistics.stdev(update_weights) if len(update_weights) > 1 else Decimal('0.00')
        expected_condition_factor = (Decimal('100') * expected_avg_weight) / (updated_sample.avg_length_cm ** 3)

        quantizer = Decimal('0.01')
        self.assertEqual(updated_sample.avg_weight_g.quantize(quantizer), expected_avg_weight.quantize(quantizer))
        self.assertEqual(updated_sample.std_deviation_weight.quantize(quantizer), expected_std_dev.quantize(quantizer))
        self.assertNotEqual(updated_sample.avg_weight_g, original_avg_weight)
        self.assertIsNotNone(updated_sample.condition_factor)
        self.assertEqual(updated_sample.condition_factor.quantize(quantizer), expected_condition_factor.quantize(quantizer))

    def test_update_sample_with_both(self):
        """Test updating a sample with new individual_weights and individual_lengths."""
        serializer = GrowthSampleSerializer(data=self.valid_sample_data)
        self.assertTrue(serializer.is_valid())
        sample = serializer.save()

        update_weights = [Decimal('3.8'), Decimal('4.2')] # New weights
        update_lengths = [Decimal('6.1'), Decimal('6.3')] # New lengths
        update_data = {
            'individual_weights': [str(w) for w in update_weights],
            'individual_lengths': [str(l) for l in update_lengths],
            'sample_size': len(update_weights)
        }

        update_serializer = GrowthSampleSerializer(instance=sample, data=update_data, partial=True)
        self.assertTrue(update_serializer.is_valid(), msg=f"Update serializer errors: {update_serializer.errors}")
        updated_sample = update_serializer.save()

        expected_avg_weight = statistics.mean(update_weights)
        expected_std_dev_weight = statistics.stdev(update_weights)
        expected_avg_length = statistics.mean(update_lengths)
        expected_std_dev_length = statistics.stdev(update_lengths)
        k_factors = [(100 * w) / (l ** 3) for w, l in zip(update_weights, update_lengths) if l > 0]
        expected_avg_k = statistics.mean(k_factors) if k_factors else None

        quantizer = Decimal('0.01')
        self.assertEqual(updated_sample.avg_weight_g.quantize(quantizer), expected_avg_weight.quantize(quantizer))
        self.assertEqual(updated_sample.std_deviation_weight.quantize(quantizer), expected_std_dev_weight.quantize(quantizer))
        self.assertEqual(updated_sample.avg_length_cm.quantize(quantizer), expected_avg_length.quantize(quantizer))
        self.assertEqual(updated_sample.std_deviation_length.quantize(quantizer), expected_std_dev_length.quantize(quantizer))
        if expected_avg_k:
            self.assertIsNotNone(updated_sample.condition_factor)
            self.assertEqual(updated_sample.condition_factor.quantize(quantizer), expected_avg_k.quantize(quantizer))
        else:
            self.assertIsNone(updated_sample.condition_factor)


    def test_calculation_if_no_individual_measurements(self):
        """ Test behavior when no individual measurement lists are provided. """
        # Create sample without individual lists
        serializer = GrowthSampleSerializer(data=self.valid_sample_data)
        self.assertTrue(serializer.is_valid())
        sample = serializer.save()

        # Check that calculated fields match provided values (or are calculated by model)
        self.assertEqual(sample.avg_weight_g, self.valid_sample_data['avg_weight_g'])
        self.assertEqual(sample.std_deviation_weight, self.valid_sample_data['std_deviation_weight'])
        self.assertEqual(sample.avg_length_cm, self.valid_sample_data['avg_length_cm'])
        self.assertEqual(sample.std_deviation_length, self.valid_sample_data['std_deviation_length'])
        # Condition factor should be calculated by model's save based on provided averages
        expected_k = (100 * sample.avg_weight_g) / (sample.avg_length_cm ** 3)
        self.assertIsNotNone(sample.condition_factor)
        self.assertEqual(sample.condition_factor.quantize(Decimal('0.01')), expected_k.quantize(Decimal('0.01')))

        # Update sample without providing lists
        update_data = {'notes': 'Updated notes'}
        update_serializer = GrowthSampleSerializer(instance=sample, data=update_data, partial=True)
        self.assertTrue(update_serializer.is_valid())
        updated_sample = update_serializer.save()

        # Ensure calculated fields remain unchanged
        self.assertEqual(updated_sample.avg_weight_g, sample.avg_weight_g)
        self.assertEqual(updated_sample.std_deviation_weight, sample.std_deviation_weight)
        self.assertEqual(updated_sample.avg_length_cm, sample.avg_length_cm)
        self.assertEqual(updated_sample.std_deviation_length, sample.std_deviation_length)
        self.assertEqual(updated_sample.condition_factor, sample.condition_factor)

    # Removed test_length_validation_if_no_individual_lengths as the
    # serializer now correctly handles absent lists by not calculating stats,
    # relying on model defaults or provided averages.
    # The test_calculation_if_no_individual_measurements covers this scenario.
