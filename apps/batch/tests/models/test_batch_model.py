from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.batch.models import Batch
from decimal import Decimal
from datetime import timedelta, date

from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_batch_with_assignment
)


class BatchModelTests(TestCase):
    """Test the Batch model."""

    @classmethod
    def setUpTestData(cls):
        cls.species = create_test_species()
        cls.stage = create_test_lifecycle_stage(species=cls.species)
        cls.batch = create_test_batch(
            species=cls.species,
            lifecycle_stage=cls.stage,
            batch_number="BATCH001"
        )

    def test_batch_str(self):
        """Test the string representation of a Batch."""
        # Update test to match the current string representation
        self.assertEqual(str(self.batch), f"Batch BATCH001 - Test Species (Test Stage)")

    def test_batch_calculated_fields(self):
        """Test calculated fields on the Batch model."""
        # Create a container for the assignment
        container = create_test_container(name="Tank 1")
        
        # Create a batch container assignment
        assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        
        # Refresh the batch from the database
        self.batch.refresh_from_db()
        
        # Test calculated fields
        self.assertEqual(self.batch.calculated_population_count, 1000)
        self.assertEqual(self.batch.calculated_biomass_kg, Decimal("10.0"))
        self.assertEqual(self.batch.calculated_avg_weight_g, Decimal("10.0"))
