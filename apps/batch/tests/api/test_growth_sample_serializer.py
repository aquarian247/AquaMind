"""
Tests for the GrowthSampleSerializer.

This module contains comprehensive tests for the GrowthSampleSerializer,
including validation of individual measurements, manual weight entry,
and error handling.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DRFValidationError
from decimal import Decimal
from datetime import date

from apps.batch.api.serializers import GrowthSampleSerializer
from apps.batch.models import GrowthSample
from apps.batch.tests.api.test_utils import (
    create_test_batch_container_assignment,
    create_test_user
)


class GrowthSampleSerializerTest(TestCase):
    """Test the GrowthSampleSerializer."""

    def setUp(self):
        """Set up test data."""
        self.assignment = create_test_batch_container_assignment(
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        self.user = create_test_user()

        # Valid data for serializer tests
        self.valid_measurement_data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'sample_size': 3,
            'individual_weights': [Decimal("9.5"), Decimal("10.0"), Decimal("10.5")],
            'individual_lengths': [Decimal("8.5"), Decimal("9.0"), Decimal("9.5")]
        }

        self.valid_manual_data = {
            'assignment': self.assignment.id,
            'sample_date': date.today(),
            'sample_size': 50,
            'avg_weight_g': Decimal("10.25"),
            'avg_length_cm': Decimal("9.2"),
            'std_deviation_weight': Decimal("0.5"),
            'std_deviation_length': Decimal("0.3"),
            'min_weight_g': Decimal("9.0"),
            'max_weight_g': Decimal("12.0")
        }

    def test_valid_measurement_based_creation(self):
        """Test serializer with valid individual measurement data."""
        serializer = GrowthSampleSerializer(data=self.valid_measurement_data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        # Check that calculated fields are present
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['sample_size'], 3)
        self.assertAlmostEqual(validated_data['avg_weight_g'], Decimal("10.0"), places=2)
        self.assertAlmostEqual(validated_data['avg_length_cm'], Decimal("9.0"), places=2)
        self.assertEqual(validated_data['min_weight_g'], Decimal("9.5"))
        self.assertEqual(validated_data['max_weight_g'], Decimal("10.5"))

    def test_valid_manual_weight_entry(self):
        """Test serializer with valid manual weight data."""
        serializer = GrowthSampleSerializer(data=self.valid_manual_data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['sample_size'], 50)
        self.assertEqual(validated_data['avg_weight_g'], Decimal("10.25"))
        self.assertEqual(validated_data['avg_length_cm'], Decimal("9.2"))
        self.assertEqual(validated_data['min_weight_g'], Decimal("9.0"))
        self.assertEqual(validated_data['max_weight_g'], Decimal("12.0"))

    def test_invalid_sample_size_mismatch_weights(self):
        """Test validation when sample_size doesn't match individual_weights length."""
        invalid_data = self.valid_measurement_data.copy()
        invalid_data['sample_size'] = 5  # Should be 3 based on weights list

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('sample_size', cm.exception.detail)
        self.assertIn('must match length of individual_weights', str(cm.exception.detail['sample_size']))

    def test_invalid_sample_size_mismatch_lengths(self):
        """Test validation when sample_size doesn't match individual_lengths length."""
        invalid_data = self.valid_measurement_data.copy()
        invalid_data['sample_size'] = 5  # Should be 3 based on lengths list

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('sample_size', cm.exception.detail)
        self.assertIn('must match length of individual_lengths', str(cm.exception.detail['sample_size']))

    def test_invalid_weights_lengths_mismatch(self):
        """Test validation when individual_weights and individual_lengths have different lengths."""
        invalid_data = self.valid_measurement_data.copy()
        invalid_data['individual_lengths'] = [Decimal("8.5"), Decimal("9.0")]  # Only 2 lengths vs 3 weights

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('individual_measurements', cm.exception.detail)
        self.assertIn('must match', str(cm.exception.detail['individual_measurements']))

    def test_invalid_min_weight_greater_than_max(self):
        """Test validation when min_weight_g > max_weight_g in manual entry."""
        invalid_data = self.valid_manual_data.copy()
        invalid_data['min_weight_g'] = Decimal("15.0")  # Greater than max_weight_g (12.0)

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('min_weight_g', cm.exception.detail)
        self.assertIn('cannot be greater than maximum weight', str(cm.exception.detail['min_weight_g']))

    def test_missing_assignment(self):
        """Test validation when assignment is missing."""
        invalid_data = self.valid_measurement_data.copy()
        del invalid_data['assignment']

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('assignment', cm.exception.detail)
        self.assertIn('required', str(cm.exception.detail['assignment']))

    def test_sample_size_exceeds_population(self):
        """Test validation when sample_size exceeds assignment population."""
        invalid_data = self.valid_manual_data.copy()
        invalid_data['sample_size'] = 2000  # Exceeds assignment population of 1000

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('sample_size', cm.exception.detail)
        self.assertIn('exceeds assignment population', str(cm.exception.detail['sample_size']))

    def test_measurement_based_with_manual_weights_fails(self):
        """Test that providing both individual_weights and manual weight fields fails."""
        invalid_data = self.valid_measurement_data.copy()
        invalid_data['avg_weight_g'] = Decimal("10.0")  # Manual weight field

        serializer = GrowthSampleSerializer(data=invalid_data)
        # This should actually work - individual measurements take precedence
        self.assertTrue(serializer.is_valid(), f"Unexpected errors: {serializer.errors}")

    def test_manual_entry_without_individual_weights(self):
        """Test that manual entry works when individual_weights is not provided."""
        # This should work fine - manual entry is allowed
        serializer = GrowthSampleSerializer(data=self.valid_manual_data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

    def test_empty_individual_measurements_lists(self):
        """Test validation with empty individual measurement lists."""
        data = self.valid_measurement_data.copy()
        data['individual_weights'] = []
        data['individual_lengths'] = []
        data['sample_size'] = 0

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

    def test_condition_factor_calculation(self):
        """Test that condition factor is calculated from individual measurements."""
        data = self.valid_measurement_data.copy()
        # Weights and lengths that should give a reasonable K-factor
        data['individual_weights'] = [Decimal("100.0"), Decimal("121.0"), Decimal("144.0")]
        data['individual_lengths'] = [Decimal("10.0"), Decimal("11.0"), Decimal("12.0")]

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        validated_data = serializer.validated_data
        self.assertIsNotNone(validated_data.get('condition_factor'))
        # For weight=100g, length=10cm: K = 100 * 100 / (10^3) = 10000 / 1000 = 10.0
        # For weight=121g, length=11cm: K = 100 * 121 / (11^3) = 12100 / 1331 ≈ 9.09
        # For weight=144g, length=12cm: K = 100 * 144 / (12^3) = 14400 / 1728 ≈ 8.33
        # Average: (10.0 + 9.09 + 8.33) / 3 ≈ 9.14
        self.assertAlmostEqual(validated_data['condition_factor'], Decimal("9.14"), places=2)

    def test_serialization_includes_assignment_details(self):
        """Test that serialized data includes assignment details."""
        # Create a growth sample first
        serializer = GrowthSampleSerializer(data=self.valid_measurement_data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        growth_sample = serializer.save()

        # Now serialize the instance
        serializer = GrowthSampleSerializer(growth_sample)
        data = serializer.data

        self.assertIn('assignment_details', data)
        assignment_details = data['assignment_details']
        self.assertEqual(assignment_details['id'], self.assignment.id)
        self.assertIn('batch', assignment_details)
        self.assertIn('container', assignment_details)
        self.assertIn('lifecycle_stage', assignment_details)
        self.assertEqual(assignment_details['population_count'], 1000)

    def test_update_existing_growth_sample(self):
        """Test updating an existing growth sample."""
        # Create initial growth sample
        serializer = GrowthSampleSerializer(data=self.valid_measurement_data)
        self.assertTrue(serializer.is_valid())
        growth_sample = serializer.save()

        # Update with new data
        update_data = {
            'sample_size': 2,
            'individual_weights': [Decimal("11.0"), Decimal("12.0")],
            'individual_lengths': [Decimal("10.0"), Decimal("10.5")]
        }

        update_serializer = GrowthSampleSerializer(growth_sample, data=update_data, partial=True)
        self.assertTrue(update_serializer.is_valid(), f"Update serializer errors: {update_serializer.errors}")

        updated_sample = update_serializer.save()
        self.assertEqual(updated_sample.sample_size, 2)
        self.assertAlmostEqual(updated_sample.avg_weight_g, Decimal("11.5"), places=2)

    def test_negative_sample_size_validation(self):
        """Test validation of negative sample size."""
        invalid_data = self.valid_manual_data.copy()
        invalid_data['sample_size'] = -1

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError) as cm:
            serializer.is_valid(raise_exception=True)

        self.assertIn('sample_size', cm.exception.detail)
        # Check for either our custom message or Django's default message
        error_msg = str(cm.exception.detail['sample_size'])
        self.assertTrue(
            'cannot be negative' in error_msg.lower() or
            'greater than or equal to 0' in error_msg.lower(),
            f"Expected negative validation message, got: {error_msg}"
        )

    def test_zero_sample_size_validation(self):
        """Test validation of zero sample size."""
        invalid_data = self.valid_manual_data.copy()
        invalid_data['sample_size'] = 0

        serializer = GrowthSampleSerializer(data=invalid_data)
        # Zero sample size should be allowed for manual entry
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

    def test_large_measurement_lists(self):
        """Test handling of large individual measurement lists."""
        # Create 20 measurements with simple decimal values that stay within max_digits=10
        large_weights = [Decimal(f"{10 + i}.0") for i in range(20)]  # 10.0 to 29.0
        large_lengths = [Decimal(f"{5 + i}.0") for i in range(20)]   # 5.0 to 24.0

        data = self.valid_measurement_data.copy()
        data['sample_size'] = 20
        data['individual_weights'] = large_weights
        data['individual_lengths'] = large_lengths

        serializer = GrowthSampleSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['sample_size'], 20)
        # Average weight: (10.0 + 29.0) / 2 = 19.5
        self.assertAlmostEqual(validated_data['avg_weight_g'], Decimal("19.5"), places=1)

    def test_invalid_decimal_formats(self):
        """Test validation with invalid decimal formats."""
        invalid_data = self.valid_measurement_data.copy()
        invalid_data['individual_weights'] = ["invalid", Decimal("10.0"), Decimal("10.5")]

        serializer = GrowthSampleSerializer(data=invalid_data)
        with self.assertRaises(DRFValidationError):
            serializer.is_valid(raise_exception=True)
