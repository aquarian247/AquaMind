from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

import statistics

from apps.batch.models import GrowthSample
from decimal import Decimal
from datetime import timedelta, date

from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_growth_sample
)


class GrowthSampleModelTest(TestCase):
    """Test the GrowthSample model."""

    @classmethod
    def setUpTestData(cls):
        cls.species = create_test_species()
        cls.stage = create_test_lifecycle_stage(species=cls.species)
        cls.batch = create_test_batch(
            species=cls.species,
            lifecycle_stage=cls.stage,
            batch_number="BATCH001"
        )
        cls.container = create_test_container(name="Tank 1")
        cls.assignment = create_test_batch_container_assignment(
            batch=cls.batch,
            container=cls.container,
            lifecycle_stage=cls.stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )

    def test_growth_sample_creation(self):
        """Test creating a growth sample."""
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today(),
            sample_size=50,
            avg_weight_g=Decimal("10.5"),
            min_weight_g=Decimal("9.0"),
            max_weight_g=Decimal("12.0"),
            std_deviation_weight=Decimal("0.8"),
            notes="Test growth sample"
        )
        self.assertEqual(sample.assignment, self.assignment)
        self.assertEqual(sample.avg_weight_g, Decimal("10.5"))
        self.assertEqual(str(sample), f"Growth sample for Assignment {self.assignment.id} (Batch: {self.batch.batch_number}) on {date.today()}")

    def test_calculate_condition_factor_valid(self):
        """Test the calculate_condition_factor method with valid inputs."""
        sample = GrowthSample(
            assignment=self.assignment,
            sample_date=date.today(),
            sample_size=50,
            avg_weight_g=Decimal("10.0"),
            avg_length_cm=Decimal("10.0")
        )
        k_factor = sample.calculate_condition_factor()
        self.assertEqual(k_factor, Decimal("1.00"))  # K = 100 * 10 / (10^3) = 1.00

    def test_calculate_condition_factor_zero_length(self):
        """Test K-factor calculation with zero length."""
        sample = GrowthSample(assignment=self.assignment, sample_date=date.today(), sample_size=50, avg_weight_g=Decimal("10.0"), avg_length_cm=Decimal("0.0"))
        self.assertIsNone(sample.calculate_condition_factor())

    def test_calculate_condition_factor_none_length(self):
        """Test K-factor calculation with None length."""
        sample = GrowthSample(assignment=self.assignment, sample_date=date.today(), sample_size=50, avg_weight_g=Decimal("10.0"), avg_length_cm=None)
        self.assertIsNone(sample.calculate_condition_factor())

    def test_calculate_condition_factor_none_weight(self):
        """Test K-factor calculation with None weight."""
        sample = GrowthSample(assignment=self.assignment, sample_date=date.today(), sample_size=50, avg_weight_g=None, avg_length_cm=Decimal("10.0"))
        self.assertIsNone(sample.calculate_condition_factor())

    def test_save_calculates_k_factor(self):
        """Test that the save method automatically calculates K-factor."""
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today(),
            sample_size=50,
            avg_weight_g=Decimal("10.0"),
            avg_length_cm=Decimal("10.0")
        )
        self.assertEqual(sample.condition_factor, Decimal("1.00"))  # K = 100 * 10 / (10^3) = 1.00

        # Test that K-factor is updated when avg_weight_g or avg_length_cm changes
        # We need to fetch the sample again to ensure we're working with the latest data
        sample = GrowthSample.objects.get(pk=sample.pk)
        sample.avg_weight_g = Decimal("20.0")
        # Set condition_factor to None to force recalculation
        sample.condition_factor = None
        sample.save()
        
        # Refresh from database to get the updated condition_factor
        sample.refresh_from_db()
        self.assertEqual(sample.condition_factor, Decimal("2.00"))  # K = 100 * 20 / (10^3) = 2.00

    def test_save_calculates_length_stats(self):
        """Test saving with length statistics."""
        # Create a sample with length statistics directly
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=5,
            avg_weight_g=Decimal("10.0"),
            avg_length_cm=Decimal("10.0"),
            std_deviation_length=Decimal("1.5")
        )
        
        # Check that the values are stored correctly
        self.assertEqual(sample.avg_length_cm, Decimal("10.0"))
        self.assertEqual(sample.std_deviation_length, Decimal("1.5"))

    def test_save_single_length_stat(self):
        """Test saving with a single length value."""
        # Create a sample with a single length value
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=1,
            avg_weight_g=Decimal("10.0"),
            avg_length_cm=Decimal("10.0"),
            std_deviation_length=Decimal("0.0")  # Single value, no std dev
        )
        
        self.assertEqual(sample.avg_length_cm, Decimal("10.0"))
        self.assertEqual(sample.std_deviation_length, Decimal("0.0"))

    def test_save_empty_length_stat(self):
        """Test saving without length data."""
        # Create a sample without length data
        sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=timezone.now().date(),
            sample_size=10,  # Note: sample_size is set, but no length measurements
            avg_weight_g=Decimal("10.0")
            # No avg_length_cm or std_deviation_length provided
        )
        
        self.assertIsNone(sample.avg_length_cm)
        self.assertIsNone(sample.std_deviation_length)
