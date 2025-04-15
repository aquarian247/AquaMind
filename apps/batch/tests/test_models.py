import decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.infrastructure.models import Container, Site, Facility
from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    GrowthSample
)

class GrowthSampleModelTest(TestCase):
    """Tests for the GrowthSample model."""

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.species = Species.objects.create(name='Test Species')
        cls.lifecycle_stage = LifeCycleStage.objects.create(
            species=cls.species, name='Test Stage', order=1
        )
        cls.site = Site.objects.create(name="Test Site")
        cls.facility = Facility.objects.create(name="Test Facility", site=cls.site)
        cls.container = Container.objects.create(
            name="Test Container", facility=cls.facility, type='TANK', capacity_m3=100
        )
        cls.batch = Batch.objects.create(
            batch_number='B001',
            species=cls.species,
            status='ACTIVE',
            start_date=timezone.now().date(),
            population_count=1000,
            avg_weight_g=50.0
        )
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=cls.container,
            lifecycle_stage=cls.lifecycle_stage, 
            population_count=500,
            biomass_kg=25.0, 
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
        individual_lengths = [14.5, 15.0, 15.5, 16.0, 14.0]
        sample = GrowthSample(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=len(individual_lengths),
            avg_weight_g=55.0,
        )
        sample.individual_lengths = individual_lengths 
        sample.save()

        expected_avg = decimal.Decimal('15.00') 
        expected_std_dev = decimal.Decimal('0.74') 

        self.assertAlmostEqual(sample.avg_length_cm, expected_avg, places=2)
        self.assertAlmostEqual(sample.std_deviation_length, expected_std_dev, places=2)
        self.assertIsNotNone(sample.condition_factor)
        expected_k = (decimal.Decimal('55.0') / (expected_avg**3)) * 100
        self.assertAlmostEqual(sample.condition_factor, expected_k, places=2)

    def test_save_single_length_stat(self):
        """Test saving with a single individual length."""
        individual_lengths = [15.0]
        sample = GrowthSample(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=len(individual_lengths),
            avg_weight_g=50.0
        )
        sample.individual_lengths = individual_lengths
        sample.save()

        self.assertEqual(sample.avg_length_cm, decimal.Decimal('15.00'))
        self.assertEqual(sample.std_deviation_length, decimal.Decimal('0.00')) 
        self.assertIsNotNone(sample.condition_factor)

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
        sample.individual_lengths = individual_lengths
        sample.save()

        self.assertEqual(sample.avg_length_cm, decimal.Decimal('14.0')) 
        self.assertIsNone(sample.std_deviation_length) 
        self.assertIsNotNone(sample.condition_factor)
        expected_k = (decimal.Decimal('50.0') / (decimal.Decimal('14.0')**3)) * 100
        self.assertAlmostEqual(sample.condition_factor, expected_k, places=2)