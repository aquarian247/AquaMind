"""
Tests for individual growth observation functionality.

This module tests the creation and management of individual fish observations
within growth samples, including aggregate calculation and serialization.
"""
from django.test import TestCase
from decimal import Decimal
from datetime import date

from apps.batch.models import GrowthSample, IndividualGrowthObservation
from apps.batch.api.serializers import GrowthSampleSerializer
from apps.batch.tests.api.test_utils import create_test_batch_container_assignment


class IndividualGrowthObservationTest(TestCase):
    """Test the IndividualGrowthObservation model and integration with GrowthSample."""

    def setUp(self):
        """Set up test data."""
        self.assignment = create_test_batch_container_assignment(
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )

    def test_create_growth_sample_with_individual_observations(self):
        """Test creating a growth sample with individual fish observations."""
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'individual_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': Decimal('10.0'),
                    'length_cm': Decimal('10.0')
                },
                {
                    'fish_identifier': '2',
                    'weight_g': Decimal('12.0'),
                    'length_cm': Decimal('11.0')
                },
                {
                    'fish_identifier': '3',
                    'weight_g': Decimal('14.0'),
                    'length_cm': Decimal('12.0')
                },
            ]
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        growth_sample = serializer.save()
        
        # Verify individual observations were created
        self.assertEqual(growth_sample.individual_observations.count(), 3)
        
        # Verify aggregates were calculated correctly
        self.assertEqual(growth_sample.sample_size, 3)
        self.assertAlmostEqual(growth_sample.avg_weight_g, Decimal('12.0'), places=2)
        self.assertAlmostEqual(growth_sample.avg_length_cm, Decimal('11.0'), places=2)
        self.assertEqual(growth_sample.min_weight_g, Decimal('10.0'))
        self.assertEqual(growth_sample.max_weight_g, Decimal('14.0'))
        
        # Verify condition factor was calculated
        self.assertIsNotNone(growth_sample.condition_factor)

    def test_create_growth_sample_with_75_individual_observations(self):
        """Test creating a growth sample with 75 individual fish observations (success criteria)."""
        observations = [
            {
                'fish_identifier': str(i),
                'weight_g': Decimal('10.0') + Decimal(str(i % 50)) * Decimal('0.1'),
                'length_cm': Decimal('10.0') + Decimal(str(i % 50)) * Decimal('0.05')
            }
            for i in range(75)
        ]
        
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'individual_observations': observations
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        growth_sample = serializer.save()
        
        # Verify all 75 observations were created
        self.assertEqual(growth_sample.individual_observations.count(), 75)
        
        # Verify sample size matches
        self.assertEqual(growth_sample.sample_size, 75)
        
        # Verify aggregates were calculated
        self.assertIsNotNone(growth_sample.avg_weight_g)
        self.assertIsNotNone(growth_sample.avg_length_cm)
        self.assertIsNotNone(growth_sample.std_deviation_weight)
        self.assertIsNotNone(growth_sample.std_deviation_length)

    def test_growth_sample_serialization_includes_fish_observations(self):
        """Test that serialized growth sample includes nested fish observations."""
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'individual_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': Decimal('100.0'),
                    'length_cm': Decimal('10.0')
                },
                {
                    'fish_identifier': '2',
                    'weight_g': Decimal('121.0'),
                    'length_cm': Decimal('11.0')
                },
            ]
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        growth_sample = serializer.save()
        
        # Serialize the instance for GET
        output_serializer = GrowthSampleSerializer(growth_sample)
        output_data = output_serializer.data
        
        # Verify fish_observations is present in output
        self.assertIn('fish_observations', output_data)
        self.assertEqual(len(output_data['fish_observations']), 2)
        
        # Verify each observation has calculated K-factor
        for obs in output_data['fish_observations']:
            self.assertIn('calculated_k_factor', obs)
            self.assertIsNotNone(obs['calculated_k_factor'])

    def test_aggregate_recalculation_on_update(self):
        """Test that aggregates are recalculated when observations are updated."""
        # Create initial sample
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'individual_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': Decimal('10.0'),
                    'length_cm': Decimal('10.0')
                },
                {
                    'fish_identifier': '2',
                    'weight_g': Decimal('12.0'),
                    'length_cm': Decimal('11.0')
                },
            ]
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        growth_sample = serializer.save()
        
        initial_avg_weight = growth_sample.avg_weight_g
        
        # Update with new observations
        update_data = {
            'individual_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': Decimal('20.0'),
                    'length_cm': Decimal('15.0')
                },
                {
                    'fish_identifier': '2',
                    'weight_g': Decimal('22.0'),
                    'length_cm': Decimal('16.0')
                },
                {
                    'fish_identifier': '3',
                    'weight_g': Decimal('24.0'),
                    'length_cm': Decimal('17.0')
                },
            ]
        }
        
        update_serializer = GrowthSampleSerializer(
            growth_sample, data=update_data, partial=True
        )
        self.assertTrue(update_serializer.is_valid())
        updated_sample = update_serializer.save()
        
        # Verify observations were replaced
        self.assertEqual(updated_sample.individual_observations.count(), 3)
        
        # Verify aggregates were recalculated
        self.assertEqual(updated_sample.sample_size, 3)
        self.assertNotEqual(updated_sample.avg_weight_g, initial_avg_weight)
        self.assertAlmostEqual(updated_sample.avg_weight_g, Decimal('22.0'), places=2)

    def test_k_factor_accuracy(self):
        """Test that K-factor is accurate to 2 decimal places."""
        # K = 100 * (weight_g / length_cm^3)
        # For weight=100g, length=10cm: K = 100 * 100 / 1000 = 10.00
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'individual_observations': [
                {
                    'fish_identifier': '1',
                    'weight_g': Decimal('100.0'),
                    'length_cm': Decimal('10.0')
                },
            ]
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        growth_sample = serializer.save()
        
        # Verify K-factor is calculated correctly
        expected_k_factor = (Decimal('100.0') / (Decimal('10.0') ** 3)) * 100
        self.assertAlmostEqual(
            growth_sample.condition_factor,
            expected_k_factor,
            places=2,
            msg=f"Expected K-factor: {expected_k_factor}, Got: {growth_sample.condition_factor}"
        )

    def test_individual_observation_unique_constraint(self):
        """Test that fish_identifier is unique within a growth sample."""
        growth_sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today(),
            sample_size=0,
            avg_weight_g=Decimal('10.0'),
        )
        
        # Create first observation
        IndividualGrowthObservation.objects.create(
            growth_sample=growth_sample,
            fish_identifier='1',
            weight_g=Decimal('10.0'),
            length_cm=Decimal('10.0')
        )
        
        # Try to create duplicate
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            IndividualGrowthObservation.objects.create(
                growth_sample=growth_sample,
                fish_identifier='1',  # Duplicate identifier
                weight_g=Decimal('12.0'),
                length_cm=Decimal('11.0')
            )

    def test_empty_observations_sets_sample_size_to_zero(self):
        """Test that growth sample with no observations has sample_size = 0."""
        growth_sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today(),
            sample_size=5,  # Initial value
            avg_weight_g=Decimal('10.0'),
        )
        
        # Calculate aggregates with no observations
        growth_sample.calculate_aggregates()
        
        # Verify sample_size is set to 0
        self.assertEqual(growth_sample.sample_size, 0)

    def test_manual_entry_still_works(self):
        """Test that manual entry (without individual observations) still works."""
        data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'sample_size': 50,
            'avg_weight_g': Decimal('10.25'),
            'avg_length_cm': Decimal('9.2'),
            'std_deviation_weight': Decimal('0.5'),
            'std_deviation_length': Decimal('0.3'),
            'min_weight_g': Decimal('9.0'),
            'max_weight_g': Decimal('12.0')
        }

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        growth_sample = serializer.save()
        
        # Verify manual values were saved
        self.assertEqual(growth_sample.sample_size, 50)
        self.assertEqual(growth_sample.avg_weight_g, Decimal('10.25'))
        self.assertEqual(growth_sample.avg_length_cm, Decimal('9.2'))

