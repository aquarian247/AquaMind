"""
Tests for the BatchSerializer.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DRFValidationError
from decimal import Decimal
from datetime import date, timedelta

from apps.batch.api.serializers import BatchSerializer
from apps.batch.models import Batch
from apps.batch.tests.api.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchSerializerTest(TestCase):
    """Test the Batch serializer."""

    def setUp(self):
        """Set up test data."""
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )
        
        # Create a batch with all required fields
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001"
        )
        
        # Create container and assignment to test calculated fields
        self.container = create_test_container(name="Tank 1")
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        
        # Valid data for serializer tests
        self.valid_batch_data = {
            'batch_number': 'BATCH002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': date.today().isoformat(),
            'expected_end_date': (date.today() + timedelta(days=365)).isoformat(),
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'notes': 'Test batch'
        }

    def test_valid_batch_serialization(self):
        """Test batch serialization with valid data."""
        serializer = BatchSerializer(data=self.valid_batch_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        batch = serializer.save()
        self.assertEqual(batch.batch_number, 'BATCH002')
        self.assertEqual(batch.species, self.species)
        self.assertEqual(batch.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(batch.status, 'ACTIVE')

    def test_lifecycle_stage_species_validation(self):
        """Test validation that lifecycle stage belongs to correct species."""
        # Create a different species and lifecycle stage
        other_species = create_test_species(name="Rainbow Trout")
        other_stage = create_test_lifecycle_stage(
            species=other_species,
            name="Smolt",
            order=3
        )
        
        # Try to create a batch with mismatched species and lifecycle stage
        invalid_data = self.valid_batch_data.copy()
        invalid_data['lifecycle_stage'] = other_stage.id
        
        serializer = BatchSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('lifecycle_stage', serializer.errors)

    def test_batch_container_assignment(self):
        """Test creating a batch and assigning it to a container."""
        # First create a batch
        serializer = BatchSerializer(data=self.valid_batch_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        batch = serializer.save()
        
        # Create an assignment for the batch
        assignment = create_test_batch_container_assignment(
            batch=batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("15.0")
        )
        
        # Refresh the batch to get updated calculated values
        batch.refresh_from_db()
        
        # Test calculated fields
        self.assertEqual(batch.calculated_population_count, 500)
        self.assertEqual(batch.calculated_biomass_kg, Decimal("7.5"))
        self.assertEqual(batch.calculated_avg_weight_g, Decimal("15.0"))
        
        # Serialize the batch and check the calculated fields
        serializer = BatchSerializer(batch)
        data = serializer.data
        self.assertEqual(data['calculated_population_count'], 500)
        self.assertEqual(Decimal(data['calculated_biomass_kg']), Decimal("7.50"))
        self.assertEqual(Decimal(data['calculated_avg_weight_g']), Decimal("15.00"))

    def test_end_date_validation(self):
        """Test validation that end date is after start date."""
        invalid_data = self.valid_batch_data.copy()
        invalid_data['expected_end_date'] = (date.today() - timedelta(days=1)).isoformat()
        
        serializer = BatchSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('expected_end_date', serializer.errors)

    def test_contains_expected_fields(self):
        """Test that the serializer contains all expected fields."""
        serializer = BatchSerializer(self.batch)
        data = serializer.data
        
        expected_fields = [
            'id', 'batch_number', 'species', 'species_name', 'lifecycle_stage',
            'status', 'batch_type', 'start_date', 'expected_end_date', 'notes',
            'calculated_population_count', 'calculated_biomass_kg', 'calculated_avg_weight_g',
            'current_lifecycle_stage', 'days_in_production', 'active_containers'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_field_content(self):
        """Test that the serialized data contains correct content."""
        serializer = BatchSerializer(self.batch)
        data = serializer.data
        
        self.assertEqual(data['batch_number'], 'BATCH001')
        self.assertEqual(data['species_name'], 'Atlantic Salmon')
        self.assertEqual(data['calculated_population_count'], 1000)
        self.assertEqual(Decimal(data['calculated_biomass_kg']), Decimal('10.00'))
        self.assertEqual(Decimal(data['calculated_avg_weight_g']), Decimal('10.00'))

    def test_create(self):
        """Test creating a batch with the serializer."""
        serializer = BatchSerializer(data=self.valid_batch_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        batch = serializer.save()
        
        self.assertEqual(batch.batch_number, 'BATCH002')
        self.assertEqual(batch.species, self.species)
        self.assertEqual(batch.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(batch.status, 'ACTIVE')
        self.assertEqual(batch.batch_type, 'STANDARD')
        self.assertEqual(batch.notes, 'Test batch')

    def test_update(self):
        """Test updating a batch with the serializer."""
        # Create update data
        update_data = {
            'batch_number': 'BATCH001-UPDATED',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'status': 'COMPLETED',
            'notes': 'Updated test batch'
        }
        
        serializer = BatchSerializer(self.batch, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_batch = serializer.save()
        
        self.assertEqual(updated_batch.batch_number, 'BATCH001-UPDATED')
        self.assertEqual(updated_batch.status, 'COMPLETED')
        self.assertEqual(updated_batch.notes, 'Updated test batch')
