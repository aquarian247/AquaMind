"""
Tests for mortality population reduction logic.
"""
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from datetime import date
import logging

from apps.health.models import MortalityReason, MortalityRecord
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment,
    create_test_batch_with_assignment
)


class MortalityPopulationTests(TestCase):
    """Test mortality record population reduction logic."""

    def setUp(self):
        self.species = create_test_species()
        self.lifecycle_stage = create_test_lifecycle_stage(species=self.species)
        self.batch, self.assignment = create_test_batch_with_assignment(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MORT_BATCH",
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        self.reason = MortalityReason.objects.create(name="Test Mortality", description="Test reason")

    def test_mortality_reduces_population(self):
        """Test that mortality records reduce batch population."""
        original_population = self.assignment.population_count

        # Record mortality
        mortality = MortalityRecord.objects.create(
            batch=self.batch,
            container=self.assignment.container,
            count=100,
            reason=self.reason,
            notes="Test mortality"
        )

        # Check population was reduced
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, original_population - 100)

    def test_mortality_prevents_negative_population(self):
        """Test that mortality clamps population at zero."""
        # Create fresh batch and assignment with small population
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SMALL_POP_BATCH"
        )
        small_assignment = create_test_batch_container_assignment(
            batch=batch,
            container=create_test_container(),
            lifecycle_stage=self.lifecycle_stage,
            population_count=50,
            avg_weight_g=Decimal("10.0")
        )

        # Record mortality exceeding population
        mortality = MortalityRecord.objects.create(
            batch=batch,
            container=small_assignment.container,
            count=100,  # More than available
            reason=self.reason,
            notes="Excessive mortality test"
        )

        # Check population was clamped to zero
        small_assignment.refresh_from_db()
        self.assertEqual(small_assignment.population_count, 0)

    def test_mortality_marks_assignment_inactive_when_zero(self):
        """Test that assignments are marked inactive when population reaches zero."""
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="ZERO_MORT_BATCH"
        )
        assignment = create_test_batch_container_assignment(
            batch=batch,
            container=create_test_container(),
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            avg_weight_g=Decimal("10.0")
        )

        # Record mortality that depletes population
        mortality = MortalityRecord.objects.create(
            batch=batch,
            container=assignment.container,
            count=100,
            reason=self.reason,
            notes="Depleting mortality"
        )

        # Check assignment was marked inactive
        assignment.refresh_from_db()
        self.assertEqual(assignment.population_count, 0)
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.departure_date, mortality.event_date.date())

    def test_mortality_distributes_across_assignments(self):
        """Test that mortality is distributed proportionally across assignments."""
        # Create fresh batch with multiple assignments
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="DIST_MORT_BATCH"
        )
        # Create multiple assignments for the same batch in different containers
        # Use unique container names to avoid constraint violations
        container1 = create_test_container(name="DIST_Container_1")
        assignment1 = create_test_batch_container_assignment(
            batch=batch,
            container=container1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        container2 = create_test_container(name="DIST_Container_2")
        assignment2 = create_test_batch_container_assignment(
            batch=batch,
            container=container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0")
        )

        # Total population: 1000 + 500 = 1500
        # Record mortality of 300
        mortality = MortalityRecord.objects.create(
            batch=batch,
            count=300,  # No specific container - should distribute across all
            reason=self.reason,
            notes="Distributed mortality"
        )

        # Check proportional distribution
        assignment1.refresh_from_db()
        assignment2.refresh_from_db()

        # assignment1 should lose ~200 (1000/1500 * 300)
        # assignment2 should lose ~100 (500/1500 * 300)
        expected_assignment1 = 1000 - 200
        expected_assignment2 = 500 - 100

        self.assertEqual(assignment1.population_count, expected_assignment1)
        self.assertEqual(assignment2.population_count, expected_assignment2)

    def test_mortality_container_specific(self):
        """Test that container-specific mortality only affects assignments in that container."""
        # Create fresh batch and assignments
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="CONT_SPEC_BATCH"
        )
        # Create two assignments for this batch in different containers
        # Use unique container names to avoid constraint violations
        container1 = create_test_container(name="CONT_SPEC_Container_1")
        test_assignment1 = create_test_batch_container_assignment(
            batch=batch,
            container=container1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        container2 = create_test_container(name="CONT_SPEC_Container_2")
        test_assignment2 = create_test_batch_container_assignment(
            batch=batch,
            container=container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("10.0")
        )

        # Record mortality for specific container (assignment1's container)
        mortality = MortalityRecord.objects.create(
            batch=batch,
            container=test_assignment1.container,  # Only affects assignment1
            count=200,
            reason=self.reason,
            notes="Container-specific mortality"
        )

        # Check only the specific assignment was affected
        test_assignment1.refresh_from_db()
        test_assignment2.refresh_from_db()

        self.assertEqual(test_assignment1.population_count, 1000 - 200)
        self.assertEqual(test_assignment2.population_count, 500)  # Unchanged


class MortalityTransactionTests(TransactionTestCase):
    """Test mortality operations with transaction rollback."""

    def setUp(self):
        self.species = create_test_species()
        self.lifecycle_stage = create_test_lifecycle_stage(species=self.species)
        self.batch, self.assignment = create_test_batch_with_assignment(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MORT_TX_BATCH",
            population_count=100,
            avg_weight_g=Decimal("10.0")
        )
        self.reason = MortalityReason.objects.create(name="Test Mortality", description="Test reason")

    def test_mortality_transaction_rollback(self):
        """Test that mortality operations are transactional."""
        original_population = self.assignment.population_count

        # Simulate a transaction failure scenario
        try:
            with transaction.atomic():
                # Create mortality record
                mortality = MortalityRecord(
                    batch=self.batch,
                    container=self.assignment.container,
                    count=50,
                    reason=self.reason,
                    notes="Test mortality"
                )
                mortality.save()

                # Force a transaction rollback by raising an exception
                raise ValidationError("Simulated failure")
        except ValidationError:
            pass  # Expected

        # Verify population wasn't changed due to rollback
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, original_population)
