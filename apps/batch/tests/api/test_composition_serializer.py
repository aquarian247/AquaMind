"""
Tests for the BatchCompositionSerializer.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DRFValidationError
from decimal import Decimal
from datetime import date, timedelta

from apps.batch.api.serializers import BatchCompositionSerializer
from apps.batch.models import BatchComposition
from apps.batch.tests.api.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchCompositionSerializerTest(TestCase):
    """Test the BatchComposition serializer."""

    def setUp(self):
        """Set up test data."""
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )
        
        # Create source batch with container assignment to ensure non-zero calculated values
        self.source_batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SOURCE001"
        )
        
        # Create a container and assignment for source batch
        self.source_container = create_test_container(name="Source Tank")
        self.source_assignment = create_test_batch_container_assignment(
            batch=self.source_batch,
            container=self.source_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=10000,
            avg_weight_g=Decimal("5.0")
        )
        
        # Create mixed batch
        self.mixed_batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIXED001"
        )
        
        # Create a container and assignment for mixed batch
        self.mixed_container = create_test_container(name="Mixed Tank")
        self.mixed_assignment = create_test_batch_container_assignment(
            batch=self.mixed_batch,
            container=self.mixed_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=5000,
            avg_weight_g=Decimal("6.0")
        )
        
        # Create a composition
        self.composition = BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.source_batch,
            percentage=Decimal("20.00"),
            population_count=1000,
            biomass_kg=Decimal("5.0")
        )
        
        # Valid data for serializer tests
        self.valid_composition_data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch.id,
            'percentage': Decimal("20.00"),
            'population_count': 1000,
            'biomass_kg': Decimal("5.0")
        }

    def test_valid_composition_serialization(self):
        """Test composition serialization with valid data."""
        serializer = BatchCompositionSerializer(data=self.valid_composition_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        composition = serializer.save()
        self.assertEqual(composition.mixed_batch, self.mixed_batch)
        self.assertEqual(composition.source_batch, self.source_batch)
        self.assertEqual(composition.percentage, Decimal("20.00"))
        self.assertEqual(composition.population_count, 1000)
        self.assertEqual(composition.biomass_kg, Decimal("5.0"))
        # No notes field in BatchComposition model

    def test_population_count_validation(self):
        """Test validation that population count doesn't exceed source batch population."""
        # Try to create a composition with population exceeding source batch
        invalid_data = self.valid_composition_data.copy()
        invalid_data['population_count'] = 11000  # Source batch only has 10000
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('population_count', serializer.errors)

    def test_biomass_validation(self):
        """Test validation that biomass doesn't exceed source batch biomass."""
        # Source batch biomass is 50kg (10000 * 5g / 1000)
        invalid_data = self.valid_composition_data.copy()
        invalid_data['biomass_kg'] = Decimal("60.0")  # Exceeds source batch biomass
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('biomass_kg', serializer.errors)

    def test_percentage_validation(self):
        """Test validation that percentage is between 0 and 100."""
        # Test percentage > 100
        invalid_data = self.valid_composition_data.copy()
        invalid_data['percentage'] = Decimal("120.00")
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('percentage', serializer.errors)
        
        # Test percentage < 0
        invalid_data['percentage'] = Decimal("-10.00")
        
        serializer = BatchCompositionSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('percentage', serializer.errors)

    def test_update_composition(self):
        """Test updating a composition with the serializer."""
        update_data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch.id,
            'percentage': Decimal("25.00"),
            'population_count': 1200,
            'biomass_kg': Decimal("6.0")
        }
        
        serializer = BatchCompositionSerializer(self.composition, data=update_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_composition = serializer.save()
        
        self.assertEqual(updated_composition.percentage, Decimal("25.00"))
        self.assertEqual(updated_composition.population_count, 1200)
        self.assertEqual(updated_composition.biomass_kg, Decimal("6.0"))
        # No notes field in BatchComposition model

    def test_partial_update_composition(self):
        """Test partially updating a composition with the serializer."""
        update_data = {
            'percentage': Decimal("30.00")
        }
        
        serializer = BatchCompositionSerializer(self.composition, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_composition = serializer.save()
        
        self.assertEqual(updated_composition.percentage, Decimal("30.00"))
        self.assertEqual(updated_composition.population_count, 1000)  # Unchanged
        self.assertEqual(updated_composition.biomass_kg, Decimal("5.0"))  # Unchanged
        # No notes field in BatchComposition model

    def test_contains_expected_fields(self):
        """Test that the serializer contains all expected fields."""
        serializer = BatchCompositionSerializer(self.composition)
        data = serializer.data
        
        expected_fields = [
            'id', 'mixed_batch', 'source_batch', 'percentage',
            'population_count', 'biomass_kg'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_field_content(self):
        """Test that the serialized data contains correct content."""
        serializer = BatchCompositionSerializer(self.composition)
        data = serializer.data
        
        self.assertEqual(data['mixed_batch']['id'], self.mixed_batch.id)
        self.assertEqual(data['mixed_batch']['batch_number'], self.mixed_batch.batch_number)
        self.assertEqual(data['source_batch']['id'], self.source_batch.id)
        self.assertEqual(data['source_batch']['batch_number'], self.source_batch.batch_number)
        self.assertEqual(Decimal(data['percentage']), Decimal("20.00"))
        self.assertEqual(data['population_count'], 1000)
        self.assertEqual(Decimal(data['biomass_kg']), Decimal("5.0"))
        # No notes field in BatchComposition model
