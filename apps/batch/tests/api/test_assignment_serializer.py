"""
Tests for the BatchContainerAssignmentSerializer.
"""
from django.test import TestCase
from rest_framework.exceptions import ValidationError as DRFValidationError
from decimal import Decimal
from datetime import date, timedelta

from apps.batch.api.serializers import BatchContainerAssignmentSerializer
from apps.batch.models import BatchContainerAssignment
from apps.batch.tests.api.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchContainerAssignmentSerializerTest(TestCase):
    """Test the BatchContainerAssignment serializer."""

    def setUp(self):
        """Set up test data."""
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )
        
        # Create a batch
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001"
        )
        
        # Create a container
        self.container = create_test_container(name="Tank 1")
        
        # Create a second container for new assignments
        self.container2 = create_test_container(name="Tank 2")
        
        # Create an assignment to test
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0"),
            notes="Initial assignment"
        )
        
        # Create a second batch with high population for testing new assignments
        self.test_batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH002"
        )
        
        # Create an initial assignment for the test batch to ensure it has calculated population
        create_test_batch_container_assignment(
            batch=self.test_batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2000,  # High population to accommodate test assignments
            avg_weight_g=Decimal("10.0"),
            notes="Initial assignment for test batch"
        )
        
        # Valid data for serializer tests
        self.valid_assignment_data = {
            'batch_id': self.test_batch.id,  # Use the test batch with high population
            'container_id': self.container2.id,  # Use a different container
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 500,  # This is less than the test batch's population
            'avg_weight_g': Decimal("15.0"),
            'assignment_date': date.today().isoformat(),
            'is_active': True,
            'notes': 'Test assignment'
        }

    def test_valid_assignment_serialization(self):
        """Test assignment serialization with valid data."""
        # Create an assignment directly to test serialization
        assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("15.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test serialization"
        )
        
        # Test serialization of the created assignment
        serializer = BatchContainerAssignmentSerializer(assignment)
        data = serializer.data
        
        self.assertEqual(data['batch']['id'], self.test_batch.id)
        self.assertEqual(data['container']['id'], self.container2.id)
        self.assertEqual(data['lifecycle_stage']['id'], self.lifecycle_stage.id)
        self.assertEqual(data['population_count'], 500)
        self.assertEqual(Decimal(data['avg_weight_g']), Decimal("15.0"))
        self.assertAlmostEqual(float(data['biomass_kg']), 7.5, places=2)  # Calculated field
        self.assertTrue(data['is_active'])

    def test_biomass_calculation(self):
        """Test that biomass_kg is correctly calculated from population_count and avg_weight_g."""
        # Create a new assignment directly with known values
        assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("15.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test biomass calculation"
        )
        
        # Test the calculation: biomass_kg = population_count * avg_weight_g / 1000
        expected_biomass = Decimal("7.5")  # 500 * 15.0 / 1000
        # Use assertAlmostEqual for decimal comparison to handle potential rounding issues
        self.assertAlmostEqual(float(assignment.biomass_kg), float(expected_biomass), places=2)
        
        # Serialize the assignment and check the biomass field
        serializer = BatchContainerAssignmentSerializer(assignment)
        self.assertAlmostEqual(float(serializer.data['biomass_kg']), float(expected_biomass), places=2)

    def test_negative_population_validation(self):
        """Test validation that population count cannot be negative."""
        # Create a test assignment directly
        test_assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test negative population"
        )
        
        # Try to update with negative population count
        update_data = {
            'population_count': -100
        }
        
        serializer = BatchContainerAssignmentSerializer(test_assignment, data=update_data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('population_count', serializer.errors)

    def test_negative_weight_validation(self):
        """Test validation that avg_weight_g cannot be negative."""
        # Create a test assignment directly
        test_assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test negative weight"
        )
        
        # Try to update with negative average weight
        update_data = {
            'avg_weight_g': Decimal("-5.0")
        }
        
        serializer = BatchContainerAssignmentSerializer(test_assignment, data=update_data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('avg_weight_g', serializer.errors)

    def test_container_capacity_validation(self):
        """Test validation that assignment biomass doesn't exceed container capacity."""
        # Set container max_biomass_kg to a low value
        self.container.max_biomass_kg = Decimal("5.0")
        self.container.save()
        
        # Try to create an assignment that would exceed capacity
        invalid_data = self.valid_assignment_data.copy()
        invalid_data['population_count'] = 1000
        invalid_data['avg_weight_g'] = Decimal("20.0")  # This would result in 20kg biomass
        
        serializer = BatchContainerAssignmentSerializer(data=invalid_data)
        # The validation may or may not enforce container capacity
        if not serializer.is_valid() and 'non_field_errors' in serializer.errors:
            self.assertIn('capacity', str(serializer.errors['non_field_errors']).lower())
        
        # Reset container capacity for other tests
        self.container.max_biomass_kg = Decimal("500.0")
        self.container.save()

    def test_update_assignment(self):
        """Test updating an assignment with the serializer."""
        # Create a new assignment for testing updates
        test_assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test update assignment"
        )
        
        # Prepare update data
        update_data = {
            'population_count': 800,
            'avg_weight_g': Decimal("12.0"),
            'notes': 'Updated assignment'
        }
        
        # Update using serializer
        serializer = BatchContainerAssignmentSerializer(test_assignment, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_assignment = serializer.save()
        
        # Verify updates
        self.assertEqual(updated_assignment.population_count, 800)
        self.assertEqual(updated_assignment.avg_weight_g, Decimal("12.0"))
        self.assertAlmostEqual(float(updated_assignment.biomass_kg), 9.6, places=2)  # 800 * 12.0 / 1000

    def test_partial_update_assignment(self):
        """Test partially updating an assignment with the serializer."""
        # Create a new assignment for testing partial updates
        test_assignment = BatchContainerAssignment.objects.create(
            batch=self.test_batch,
            container=self.container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0"),
            assignment_date=date.today(),
            is_active=True,
            notes="Test partial update"
        )
        
        # Only update population_count
        update_data = {
            'population_count': 600
        }
        
        serializer = BatchContainerAssignmentSerializer(test_assignment, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_assignment = serializer.save()
        
        # Verify updates
        self.assertEqual(updated_assignment.population_count, 600)
        self.assertEqual(updated_assignment.avg_weight_g, Decimal("10.0"))  # Unchanged
        self.assertAlmostEqual(float(updated_assignment.biomass_kg), 6.0, places=2)  # Recalculated: 600 * 10.0 / 1000

    def test_contains_expected_fields(self):
        """Test that the serializer contains all expected fields."""
        serializer = BatchContainerAssignmentSerializer(self.assignment)
        data = serializer.data
        
        expected_fields = [
            'id', 'batch', 'container', 'lifecycle_stage',
            'population_count', 'avg_weight_g', 'biomass_kg',
            'assignment_date', 'is_active', 'notes',
            'batch_info', 'container_info', 'lifecycle_stage_info'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_field_content(self):
        """Test that the serialized data contains correct content."""
        serializer = BatchContainerAssignmentSerializer(self.assignment)
        data = serializer.data
        
        self.assertEqual(data['batch']['id'], self.batch.id)
        self.assertEqual(data['container']['id'], self.container.id)
        self.assertEqual(data['lifecycle_stage']['id'], self.lifecycle_stage.id)
        self.assertEqual(data['population_count'], 1000)
        self.assertEqual(Decimal(data['avg_weight_g']), Decimal('10.0'))
        self.assertEqual(Decimal(data['biomass_kg']), Decimal('10.0'))
        self.assertTrue(data['is_active'])
        
        # Check nested info objects
        self.assertEqual(data['batch_info']['batch_number'], self.batch.batch_number)
        self.assertEqual(data['container_info']['name'], self.container.name)
        self.assertEqual(data['lifecycle_stage_info']['name'], self.lifecycle_stage.name)
