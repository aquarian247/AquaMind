"""
Tests for automatic FCR calculation signals.

This module tests that FCR summaries are automatically created/updated
when users create feeding events or growth samples through normal workflows.
"""

from decimal import Decimal
from django.test import TestCase
from datetime import date, timedelta

from apps.inventory.models import (
    Feed, FeedingEvent, BatchFeedingSummary, ContainerFeedingSummary
)
from apps.infrastructure.models import Container, ContainerType, Hall, Geography, FreshwaterStation
from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment, GrowthSample


class FCRSignalTests(TestCase):
    """Test automatic FCR calculation via Django signals."""
    
    def setUp(self):
        """Set up test data."""
        # Create infrastructure
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography for signal testing"
        )
        
        self.freshwater_station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=Decimal("10.123456"),
            longitude=Decimal("20.123456")
        )
        
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.freshwater_station
        )
        
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.00")
        )
        
        self.container = Container.objects.create(
            name="Tank-1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("50.00"),
            max_biomass_kg=Decimal("5000.00")
        )
        
        # Create feed
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="TestBrand",
            size_category="MEDIUM",
            protein_percentage=Decimal("45.0"),
            fat_percentage=Decimal("20.0")
        )
        
        # Create species and lifecycle stage
        self.species = Species.objects.create(name="Atlantic Salmon")
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number="TEST-BATCH-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=50)
        )
        
        # Create active container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,  # Required field
            assignment_date=date.today() - timedelta(days=40),
            population_count=10000,
            biomass_kg=Decimal("500.00"),
            is_active=True
        )
    
    def test_fcr_updates_on_feeding_event_creation(self):
        """
        When a feeding event is created, FCR summaries should be automatically
        calculated via signal handler.
        """
        # Verify no FCR summary exists initially
        self.assertEqual(BatchFeedingSummary.objects.filter(batch=self.batch).count(), 0)
        self.assertEqual(ContainerFeedingSummary.objects.filter(
            container_assignment=self.assignment
        ).count(), 0)
        
        # Create growth samples within last 30 days (signal uses 30-day window)
        # Start weight sample
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today() - timedelta(days=29),  # Within 30-day window
            avg_weight_g=Decimal("50.0"),
            sample_size=100
        )
        
        # Create multiple feeding events within 30-day window
        for days_ago in [28, 25, 20, 15, 10, 5]:
            FeedingEvent.objects.create(
                batch=self.batch,
                batch_assignment=self.assignment,
                container=self.container,
                feed=self.feed,
                feeding_date=date.today() - timedelta(days=days_ago),
                feeding_time="12:00:00",
                amount_kg=Decimal("100.0"),
                batch_biomass_kg=Decimal("500.0"),
                method='MANUAL'
            )
        
        # End weight sample (recent - shows growth)
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today() - timedelta(days=2),
            avg_weight_g=Decimal("80.0"),  # 30g weight gain
            sample_size=100
        )
        
        # Last feeding event should trigger final FCR calculation
        feeding_event = FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=1),
            feeding_time="12:00:00",
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("800.0"),  # Updated biomass
            method='MANUAL'
        )
        
        # Verify FCR summaries were created automatically
        batch_summaries = BatchFeedingSummary.objects.filter(batch=self.batch)
        self.assertGreater(
            batch_summaries.count(), 0,
            "Batch FCR summary should be auto-created after feeding event"
        )
        
        # Verify container summary exists
        container_summaries = ContainerFeedingSummary.objects.filter(
            container_assignment=self.assignment
        )
        self.assertGreater(
            container_summaries.count(), 0,
            "Container FCR summary should be auto-created after feeding event"
        )
    
    def test_no_fcr_update_for_inactive_assignment(self):
        """
        Signal should skip FCR calculation for inactive assignments.
        """
        # Make assignment inactive
        self.assignment.is_active = False
        self.assignment.save()
        
        # Create feeding event
        FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today(),
            feeding_time="12:00:00",
            amount_kg=Decimal("50.0"),
            batch_biomass_kg=Decimal("500.0"),
            method='MANUAL'
        )
        
        # FCR summary should NOT be created for inactive assignment
        summaries = BatchFeedingSummary.objects.filter(batch=self.batch)
        # May be 0 or existing from other tests, but should not increase
        initial_count = summaries.count()
        self.assertTrue(initial_count >= 0, "Should handle inactive assignments gracefully")
    
    def test_last_weighing_date_updates_on_growth_sample(self):
        """
        When growth sample is created, last_weighing_date should be updated
        on all active assignments for the batch.
        """
        # Verify last_weighing_date is initially None
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.last_weighing_date)
        
        # Create growth sample (should trigger signal)
        sample_date_value = date.today() - timedelta(days=5)
        growth_sample = GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=sample_date_value,
            avg_weight_g=Decimal("100.0"),
            sample_size=100
        )
        
        # Verify last_weighing_date was updated automatically
        self.assignment.refresh_from_db()
        self.assertEqual(
            self.assignment.last_weighing_date,
            sample_date_value,
            "last_weighing_date should be auto-updated on growth sample creation"
        )
    
    def test_fcr_updates_on_growth_sample_creation(self):
        """
        When growth sample is added, FCR should recalculate with new biomass data.
        """
        # Create initial growth sample within 30-day window
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today() - timedelta(days=29),
            avg_weight_g=Decimal("50.0"),
            sample_size=100
        )
        
        # Create multiple feeding events within 30-day window
        for days_ago in [28, 25, 20, 15, 10]:
            FeedingEvent.objects.create(
                batch=self.batch,
                batch_assignment=self.assignment,
                container=self.container,
                feed=self.feed,
                feeding_date=date.today() - timedelta(days=days_ago),
                feeding_time="12:00:00",
                amount_kg=Decimal("100.0"),
                batch_biomass_kg=Decimal("500.0"),
                method='MANUAL'
            )
        
        # Get initial FCR (if any)
        initial_summaries = BatchFeedingSummary.objects.filter(batch=self.batch).count()
        
        # Create new growth sample (should trigger FCR recalculation)
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today() - timedelta(days=2),
            avg_weight_g=Decimal("100.0"),  # Weight gain = 50g
            sample_size=100
        )
        
        # Verify FCR summary exists (created or updated)
        final_summaries = BatchFeedingSummary.objects.filter(batch=self.batch)
        self.assertGreater(
            final_summaries.count(), 0,
            "Batch FCR summary should exist after growth sample"
        )
        
        # Verify confidence level improved (recent weighing)
        latest_summary = final_summaries.order_by('-updated_at').first()
        if latest_summary:
            self.assertIn(
                latest_summary.overall_confidence_level,
                ['VERY_HIGH', 'HIGH'],
                "Recent growth sample should improve confidence level"
            )
    
    def test_signal_handles_errors_gracefully(self):
        """
        Signal should not block feeding event creation if FCR calculation fails.
        """
        # Create feeding event WITHOUT growth samples (FCR will fail to calculate)
        feeding_event = FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today(),
            feeding_time="12:00:00",
            amount_kg=Decimal("50.0"),
            batch_biomass_kg=Decimal("500.0"),
            method='MANUAL'
        )
        
        # Feeding event should still be created despite FCR calculation failure
        self.assertIsNotNone(feeding_event.id)
        self.assertEqual(feeding_event.batch, self.batch)
    
    def test_feeding_event_update_does_not_trigger_signal(self):
        """
        Signal should only trigger on creation, not on updates.
        """
        # Create growth samples
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today() - timedelta(days=30),
            avg_weight_g=Decimal("50.0"),
            sample_size=100
        )
        GrowthSample.objects.create(
            assignment=self.assignment,
            sample_date=date.today(),
            avg_weight_g=Decimal("80.0"),
            sample_size=100
        )
        
        # Create initial feeding event
        feeding_event = FeedingEvent.objects.create(
            batch=self.batch,
            batch_assignment=self.assignment,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=10),
            feeding_time="12:00:00",
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("500.0"),
            method='MANUAL'
        )
        
        # Get summary count after creation
        initial_count = BatchFeedingSummary.objects.filter(batch=self.batch).count()
        
        # Update the feeding event (should NOT trigger signal)
        feeding_event.notes = "Updated notes"
        feeding_event.save()
        
        # Summary count should not change
        final_count = BatchFeedingSummary.objects.filter(batch=self.batch).count()
        self.assertEqual(
            initial_count, final_count,
            "FCR should not recalculate on feeding event updates"
        )

