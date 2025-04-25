import decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

import statistics  # Added for statistical calculations

from apps.infrastructure.models import (
    Container, Geography, FreshwaterStation, Hall, ContainerType, Area
)
from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    GrowthSample
)
from decimal import Decimal
from datetime import timedelta
from apps.batch.api.serializers import GrowthSampleSerializer

class GrowthSampleModelTest(TestCase):
    """Tests for the GrowthSample model."""

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.species = Species.objects.create(name='Test Species')
        
        # Create a LifeCycleStage instance
        cls.lifecycle_stage = LifeCycleStage.objects.create(species=cls.species, name='Test Stage', order=1)
        
        # Create necessary infrastructure instances
        cls.geography = Geography.objects.create(name="Test Geography")
        cls.station = FreshwaterStation.objects.create(
            name="Test Station", 
            geography=cls.geography, 
            station_type='FRESHWATER',
            latitude=10.0,
            longitude=10.0
        )
        cls.hall = Hall.objects.create(name="Test Hall", freshwater_station=cls.station)
        cls.container_type = ContainerType.objects.create(
            name="Test Tank Type", category='TANK', max_volume_m3=100.0
        )
        cls.container = Container.objects.create(
            name="Test Container", 
            hall=cls.hall,  # Link to Hall instead of Facility
            container_type=cls.container_type, # Use ContainerType
            volume_m3=decimal.Decimal('100.0'), # Use volume_m3
            max_biomass_kg=decimal.Decimal('500.0') # Add required max_biomass_kg
        )
        
        # Existing Batch creation - needs review based on CI errors
        cls.batch = Batch.objects.create(
            batch_number='B001',
            species=cls.species,
            lifecycle_stage=cls.lifecycle_stage, # Add required lifecycle_stage
            status='ACTIVE',
            start_date=timezone.now().date(),
            population_count=1000, # Add required population_count
            avg_weight_g=Decimal('50.0') # Add required avg_weight_g (biomass_kg will be calculated)
        )
        
        # Existing Assignment creation
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.container,
            lifecycle_stage=cls.lifecycle_stage, 
            population_count=500,  # Assuming this is still valid for assignment
            biomass_kg=decimal.Decimal('25.0'), # Assuming this is still valid for assignment
            assignment_date=timezone.now().date(),
            is_active=True
        )

    def test_growth_sample_creation(self):
        """Test creating a GrowthSample instance."""
        sample_date = timezone.now().date()
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=sample_date,
            sample_size=10,
            avg_weight_g=60.5,
            avg_length_cm=15.2
        )
        self.assertEqual(sample.assignment, self.assignment)
        self.assertEqual(sample.sample_date, sample_date)
        self.assertEqual(sample.sample_size, 10)
        self.assertEqual(sample.avg_weight_g, 60.5)
        self.assertEqual(sample.avg_length_cm, 15.2)
        self.assertIsNotNone(sample.condition_factor) 
        self.assertEqual(GrowthSample.objects.count(), 1)

    def test_calculate_condition_factor_valid(self):
        """Test the calculate_condition_factor method with valid inputs."""
        sample = GrowthSample(avg_weight_g=100.0, avg_length_cm=20.0)
        expected_k = decimal.Decimal('1.25') 
        calculated_k = sample.calculate_condition_factor()
        self.assertIsNotNone(calculated_k)
        self.assertAlmostEqual(calculated_k, expected_k, places=2)

    def test_calculate_condition_factor_zero_length(self):
        """Test K-factor calculation with zero length."""
        sample = GrowthSample(avg_weight_g=100.0, avg_length_cm=0.0)
        self.assertIsNone(sample.calculate_condition_factor())

    def test_calculate_condition_factor_none_length(self):
        """Test K-factor calculation with None length."""
        sample = GrowthSample(avg_weight_g=100.0, avg_length_cm=None)
        self.assertIsNone(sample.calculate_condition_factor())

    def test_calculate_condition_factor_none_weight(self):
        """Test K-factor calculation with None weight."""
        sample = GrowthSample(avg_weight_g=None, avg_length_cm=20.0)
        self.assertIsNone(sample.calculate_condition_factor())

    def test_save_calculates_k_factor(self):
        """Test that the save method automatically calculates K-factor."""
        sample = GrowthSample(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=5,
            avg_weight_g=120.0,
            avg_length_cm=22.0
        )
        sample.save()
        self.assertIsNotNone(sample.condition_factor)
        expected_k = (decimal.Decimal('120.0') / (decimal.Decimal('22.0')**3)) * 100
        self.assertAlmostEqual(sample.condition_factor, expected_k, places=2)

    def test_save_calculates_length_stats(self):
        """Test saving with individual_lengths calculates avg and std dev."""
        lengths = [Decimal('10.0'), Decimal('12.5'), Decimal('11.0'), Decimal('13.0'), Decimal('10.5')]
        expected_avg = statistics.mean(lengths).quantize(Decimal("0.01"))
        expected_std_dev = statistics.stdev(lengths).quantize(Decimal("0.01"))

        data = {
            'assignment': self.assignment.pk,
            'sample_date': timezone.now().date(),
            'sample_size': len(lengths),
            'avg_weight_g': Decimal('50.0'), # Add dummy weight to satisfy model constraint
            'individual_lengths': [str(l) for l in lengths] # Serializer expects strings usually
        }
        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        sample = serializer.save()

        self.assertIsNotNone(sample.avg_length_cm)
        self.assertIsNotNone(sample.std_deviation_length)
        self.assertEqual(sample.avg_length_cm, expected_avg)
        self.assertEqual(sample.std_deviation_length, expected_std_dev)

    def test_save_single_length_stat(self):
        """Test saving with a single individual length."""
        data = {
            'assignment': self.assignment.pk,
            'sample_date': timezone.now().date(),
            'sample_size': 1,
            'avg_weight_g': Decimal('50.0'), # Add dummy weight to satisfy model constraint
            'individual_lengths': ['15.0']
        }
        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        sample = serializer.save()

        self.assertIsNotNone(sample.avg_length_cm)
        self.assertEqual(sample.avg_length_cm, Decimal('15.00'))
        self.assertEqual(sample.std_deviation_length, Decimal('0.00')) 

    def test_save_empty_length_stat(self):
        """Test saving with an empty individual length list."""
        individual_lengths = []
        sample = GrowthSample(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=len(individual_lengths), 
            avg_weight_g=50.0,
            avg_length_cm=14.0 
        )
        sample.save()

        self.assertEqual(sample.avg_length_cm, decimal.Decimal('14.0')) 
        self.assertIsNone(sample.std_deviation_length) 
        self.assertIsNotNone(sample.condition_factor)
        expected_k = (decimal.Decimal('50.0') / (decimal.Decimal('14.0')**3)) * 100
        self.assertAlmostEqual(sample.condition_factor, expected_k, places=2)