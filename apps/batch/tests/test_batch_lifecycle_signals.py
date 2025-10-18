"""
Tests for batch lifecycle signal handlers.

These tests verify that batches are automatically marked as COMPLETED
when all their container assignments are deactivated (harvested).
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.batch.models import Batch, BatchContainerAssignment, Species, LifeCycleStage
from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType,
    Container,
)


class BatchLifecycleSignalsTest(TestCase):
    """Test automatic batch completion when all assignments are inactive."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create infrastructure
        self.geography = Geography.objects.create(name="Test Region")
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="LAND",
            geography=self.geography,
            latitude=Decimal("62.0"),
            longitude=Decimal("-6.7"),
        )
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station,
        )
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=Decimal("100.00"),
        )
        self.container1 = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("50.00"),
            max_biomass_kg=Decimal("1000.00"),
        )
        self.container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("50.00"),
            max_biomass_kg=Decimal("1000.00"),
        )
        
        # Create batch context
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Fry",
            species=self.species,
            description="Young fish",
            order=2,
        )
    
    def create_batch(self, status='ACTIVE', actual_end_date=None):
        """Helper to create a test batch."""
        return Batch.objects.create(
            batch_number=f"TEST-{timezone.now().timestamp()}",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status=status,
            start_date=date.today() - timedelta(days=30),
            expected_end_date=date.today() + timedelta(days=30),
            actual_end_date=actual_end_date,
        )
    
    def create_assignment(self, batch, container, is_active=True, departure_date=None):
        """Helper to create a test assignment."""
        return BatchContainerAssignment.objects.create(
            batch=batch,
            container=container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.00"),
            biomass_kg=Decimal("10.00"),
            assignment_date=date.today() - timedelta(days=10),
            is_active=is_active,
            departure_date=departure_date,
        )
    
    def test_batch_completed_when_single_assignment_deactivated(self):
        """Test batch is marked COMPLETED when its only assignment is deactivated."""
        batch = self.create_batch(status='ACTIVE')
        assignment = self.create_assignment(batch, self.container1, is_active=True)
        
        # Verify initial state
        self.assertEqual(batch.status, 'ACTIVE')
        self.assertIsNone(batch.actual_end_date)
        
        # Deactivate the only assignment (simulating harvest)
        departure = date.today()
        assignment.is_active = False
        assignment.departure_date = departure
        assignment.save()
        
        # Batch should now be COMPLETED
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        self.assertEqual(batch.actual_end_date, departure)
    
    def test_batch_completed_when_all_assignments_deactivated(self):
        """Test batch is marked COMPLETED only when ALL assignments are inactive."""
        batch = self.create_batch(status='ACTIVE')
        assignment1 = self.create_assignment(batch, self.container1, is_active=True)
        assignment2 = self.create_assignment(batch, self.container2, is_active=True)
        
        # Deactivate first assignment
        assignment1.is_active = False
        assignment1.departure_date = date(2025, 10, 1)
        assignment1.save()
        
        # Batch should still be ACTIVE (assignment2 is still active)
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'ACTIVE')
        self.assertIsNone(batch.actual_end_date)
        
        # Deactivate second (last) assignment
        assignment2.is_active = False
        assignment2.departure_date = date(2025, 10, 5)
        assignment2.save()
        
        # NOW batch should be COMPLETED
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        # Should use the latest departure date
        self.assertEqual(batch.actual_end_date, date(2025, 10, 5))
    
    def test_batch_completion_uses_latest_departure_date(self):
        """Test actual_end_date is set to the latest departure date among all assignments."""
        batch = self.create_batch(status='ACTIVE')
        
        # Create assignments - both start active
        a1 = self.create_assignment(batch, self.container1, is_active=True)
        a2 = self.create_assignment(batch, self.container2, is_active=True)
        
        # Deactivate first assignment with an earlier date
        a1.is_active = False
        a1.departure_date = date(2025, 10, 1)
        a1.save()
        
        batch.refresh_from_db()
        # Batch should still be ACTIVE (a2 is still active)
        self.assertEqual(batch.status, 'ACTIVE')
        
        # Deactivate second assignment with a later date
        a2.is_active = False
        a2.departure_date = date(2025, 10, 5)
        a2.save()
        
        batch.refresh_from_db()
        # Should use the latest departure date (2025-10-5, not 2025-10-1)
        self.assertEqual(batch.actual_end_date, date(2025, 10, 5))
        self.assertEqual(batch.status, 'COMPLETED')
    
    def test_batch_not_completed_if_already_terminated(self):
        """Test signal doesn't change status if batch is already TERMINATED."""
        batch = self.create_batch(status='TERMINATED', actual_end_date=date(2025, 9, 1))
        assignment = self.create_assignment(batch, self.container1, is_active=True)
        
        # Deactivate assignment
        assignment.is_active = False
        assignment.departure_date = date(2025, 10, 1)
        assignment.save()
        
        # Batch should remain TERMINATED (not changed to COMPLETED)
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'TERMINATED')
        self.assertEqual(batch.actual_end_date, date(2025, 9, 1))  # Unchanged
    
    def test_batch_not_completed_if_already_completed(self):
        """Test signal is idempotent - doesn't re-process already completed batches."""
        batch = self.create_batch(status='COMPLETED', actual_end_date=date(2025, 9, 1))
        assignment = self.create_assignment(
            batch, self.container1, is_active=False, departure_date=date(2025, 9, 1)
        )
        
        # Save the assignment again (shouldn't trigger re-completion)
        assignment.population_count = 900
        assignment.save()
        
        # Batch should remain unchanged
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        self.assertEqual(batch.actual_end_date, date(2025, 9, 1))
    
    def test_fallback_to_updated_at_when_no_departure_date(self):
        """Test signal uses updated_at date when departure_date is not set."""
        batch = self.create_batch(status='ACTIVE')
        assignment = self.create_assignment(
            batch, self.container1, is_active=True, departure_date=None
        )
        
        # Deactivate without setting departure_date
        assignment.is_active = False
        # Don't set departure_date - should fall back to updated_at
        assignment.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        # Should have SOME end date (from updated_at)
        self.assertIsNotNone(batch.actual_end_date)
    
    def test_reactivating_assignment_does_not_trigger_completion(self):
        """Test that activating an assignment doesn't trigger the completion logic."""
        batch = self.create_batch(status='ACTIVE')
        assignment = self.create_assignment(
            batch, self.container1, is_active=False, departure_date=date(2025, 10, 1)
        )
        
        # Batch was already completed by the above
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        
        # Now reactivate the assignment (e.g., data correction)
        assignment.is_active = True
        assignment.departure_date = None
        assignment.save()
        
        # Batch should remain COMPLETED (signal only triggers on deactivation)
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
    
    def test_multiple_sequential_harvests(self):
        """Test realistic scenario: assignments harvested over multiple days."""
        batch = self.create_batch(status='ACTIVE')
        
        # Day 1: Create 3 active assignments
        a1 = self.create_assignment(batch, self.container1, is_active=True)
        a2 = self.create_assignment(batch, self.container2, is_active=True)
        
        # Day 2: Harvest first container
        a1.is_active = False
        a1.departure_date = date(2025, 10, 1)
        a1.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'ACTIVE')  # Still has a2
        
        # Day 5: Harvest second (last) container
        a2.is_active = False
        a2.departure_date = date(2025, 10, 5)
        a2.save()
        
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'COMPLETED')
        self.assertEqual(batch.actual_end_date, date(2025, 10, 5))
    
    def test_batch_with_no_assignments_remains_active(self):
        """Test batch without any assignments stays ACTIVE (edge case)."""
        batch = self.create_batch(status='ACTIVE')
        
        # No assignments created
        self.assertEqual(batch.status, 'ACTIVE')
        self.assertIsNone(batch.actual_end_date)
        
        # This is an edge case - batch exists but was never assigned to containers
        # It should remain ACTIVE until manually changed or assigned

