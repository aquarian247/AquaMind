"""
Unit tests for FinanceReportingService.

Tests comprehensive aggregation logic for finance reporting including
summary calculations, multi-dimensional breakdowns, and time series generation.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.batch.models import Batch, LifeCycleStage, Species
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType
)
from apps.inventory.models import Feed, FeedingEvent
from apps.inventory.services import FinanceReportingService


class FinanceReportingServiceSummaryTest(TestCase):
    """Test summary calculation methods."""

    def setUp(self):
        """Create test data for summary calculations."""
        # Create basic infrastructure
        self.geography = Geography.objects.create(name="Scotland")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=Decimal("57.0"),
            longitude=Decimal("-3.0"),
            max_biomass=Decimal("10000.0")
        )
        
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        self.container = Container.objects.create(
            name="Test Tank",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        # Create batch and feed
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date()
        )
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        
        # Create feeding events with known totals
        today = timezone.now().date()
        self.event1 = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("50.00"),
            method="MANUAL"
        )
        self.event2 = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("15.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("75.00"),
            method="MANUAL"
        )

    def test_calculate_summary(self):
        """Test summary calculation returns correct totals."""
        queryset = FeedingEvent.objects.all()
        summary = FinanceReportingService.calculate_summary(queryset)
        
        # Verify totals
        self.assertEqual(summary['total_feed_kg'], 25.0)  # 10 + 15
        self.assertEqual(summary['total_feed_cost'], 125.0)  # 50 + 75
        self.assertEqual(summary['events_count'], 2)
        
        # Verify date range
        self.assertIsNotNone(summary['date_range']['start'])
        self.assertIsNotNone(summary['date_range']['end'])

    def test_calculate_summary_empty_queryset(self):
        """Test summary with empty queryset returns zeros."""
        queryset = FeedingEvent.objects.none()
        summary = FinanceReportingService.calculate_summary(queryset)
        
        self.assertEqual(summary['total_feed_kg'], 0.0)
        self.assertEqual(summary['total_feed_cost'], 0.0)
        self.assertEqual(summary['events_count'], 0)
        self.assertIsNone(summary['date_range']['start'])
        self.assertIsNone(summary['date_range']['end'])


class FinanceReportingServiceBreakdownTest(TestCase):
    """Test breakdown methods by various dimensions."""

    def setUp(self):
        """Create comprehensive test data for breakdowns."""
        # Create two geographies
        self.scotland = Geography.objects.create(name="Scotland")
        self.faroe = Geography.objects.create(name="Faroe Islands")
        
        self.scotland_area = Area.objects.create(
            name="Scottish Area 1",
            geography=self.scotland,
            latitude=Decimal("57.0"),
            longitude=Decimal("-3.0"),
            max_biomass=Decimal("10000.0")
        )
        self.faroe_area = Area.objects.create(
            name="Faroe Area 1",
            geography=self.faroe,
            latitude=Decimal("62.0"),
            longitude=Decimal("-7.0"),
            max_biomass=Decimal("10000.0")
        )
        
        # Create containers
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        self.scotland_container = Container.objects.create(
            name="Scotland Tank",
            container_type=self.container_type,
            area=self.scotland_area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        self.faroe_container = Container.objects.create(
            name="Faroe Tank",
            container_type=self.container_type,
            area=self.faroe_area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        # Create batch
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date()
        )
        
        # Create multiple feeds
        self.feed1 = Feed.objects.create(
            name="Premium Feed",
            brand="Brand A",
            size_category="MEDIUM",
            protein_percentage=Decimal("48.0"),
            fat_percentage=Decimal("18.0")
        )
        self.feed2 = Feed.objects.create(
            name="Standard Feed",
            brand="Brand B",
            size_category="SMALL",
            protein_percentage=Decimal("42.0"),
            fat_percentage=Decimal("15.0")
        )
        
        # Create feeding events across different dimensions
        today = timezone.now().date()
        
        # Scotland events with different feeds
        self.scotland_event1 = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.feed1,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("600.00"),
            method="MANUAL"
        )
        self.scotland_event2 = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.feed2,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("80.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("400.00"),
            method="MANUAL"
        )
        
        # Faroe events
        self.faroe_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.faroe_container,
            feed=self.feed1,
            feeding_date=today,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("90.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("540.00"),
            method="MANUAL"
        )

    def test_breakdown_by_feed_type(self):
        """Test aggregation by feed type includes nutritional data."""
        queryset = FeedingEvent.objects.all()
        breakdown = FinanceReportingService.breakdown_by_feed_type(queryset)
        
        # Should have 2 feed types
        self.assertEqual(len(breakdown), 2)
        
        # Find premium feed entry
        premium = next((b for b in breakdown if b['feed_id'] == self.feed1.id), None)
        self.assertIsNotNone(premium)
        self.assertEqual(premium['feed_name'], "Premium Feed")
        self.assertEqual(premium['brand'], "Brand A")
        self.assertEqual(premium['protein_percentage'], 48.0)
        self.assertEqual(premium['fat_percentage'], 18.0)
        self.assertEqual(premium['total_kg'], 190.0)  # 100 + 90
        self.assertEqual(premium['total_cost'], 1140.0)  # 600 + 540
        self.assertEqual(premium['events_count'], 2)
        
        # Find standard feed entry
        standard = next((b for b in breakdown if b['feed_id'] == self.feed2.id), None)
        self.assertIsNotNone(standard)
        self.assertEqual(standard['total_kg'], 80.0)
        self.assertEqual(standard['total_cost'], 400.0)
        self.assertEqual(standard['events_count'], 1)

    def test_breakdown_by_geography(self):
        """Test aggregation by geography with area counts."""
        queryset = FeedingEvent.objects.all()
        breakdown = FinanceReportingService.breakdown_by_geography(queryset)
        
        # Should have 2 geographies
        self.assertEqual(len(breakdown), 2)
        
        # Find Scotland entry
        scotland = next((b for b in breakdown if b['geography_id'] == self.scotland.id), None)
        self.assertIsNotNone(scotland)
        self.assertEqual(scotland['geography_name'], "Scotland")
        self.assertEqual(scotland['total_kg'], 180.0)  # 100 + 80
        self.assertEqual(scotland['total_cost'], 1000.0)  # 600 + 400
        self.assertEqual(scotland['events_count'], 2)
        self.assertEqual(scotland['area_count'], 1)
        self.assertEqual(scotland['container_count'], 1)

    def test_breakdown_by_area(self):
        """Test aggregation by area with container counts."""
        queryset = FeedingEvent.objects.all()
        breakdown = FinanceReportingService.breakdown_by_area(queryset)
        
        # Should have 2 areas
        self.assertEqual(len(breakdown), 2)
        
        # Find Scottish area entry
        area = next((b for b in breakdown if b['area_id'] == self.scotland_area.id), None)
        self.assertIsNotNone(area)
        self.assertEqual(area['area_name'], "Scottish Area 1")
        self.assertEqual(area['geography'], "Scotland")
        self.assertEqual(area['total_kg'], 180.0)
        self.assertEqual(area['total_cost'], 1000.0)
        self.assertEqual(area['container_count'], 1)

    def test_breakdown_by_container(self):
        """Test aggregation by container with feed diversity."""
        queryset = FeedingEvent.objects.all()
        breakdown = FinanceReportingService.breakdown_by_container(queryset)
        
        # Should have 2 containers
        self.assertEqual(len(breakdown), 2)
        
        # Find Scotland container entry
        container = next((b for b in breakdown if b['container_id'] == self.scotland_container.id), None)
        self.assertIsNotNone(container)
        self.assertEqual(container['container_name'], "Scotland Tank")
        self.assertEqual(container['area'], "Scottish Area 1")
        self.assertEqual(container['total_kg'], 180.0)
        self.assertEqual(container['total_cost'], 1000.0)
        self.assertEqual(container['feed_type_count'], 2)  # 2 different feeds used


class FinanceReportingServiceTimeSeriesTest(TestCase):
    """Test time series generation methods."""

    def setUp(self):
        """Create test data spanning multiple days."""
        # Create infrastructure
        self.geography = Geography.objects.create(name="Scotland")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=Decimal("57.0"),
            longitude=Decimal("-3.0"),
            max_biomass=Decimal("10000.0")
        )
        
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        self.container = Container.objects.create(
            name="Test Tank",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        # Create batch and feed
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date()
        )
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM"
        )
        
        # Create events across 5 days
        today = timezone.now().date()
        for i in range(5):
            FeedingEvent.objects.create(
                batch=self.batch,
                container=self.container,
                feed=self.feed,
                feeding_date=today - timedelta(days=i),
                feeding_time=timezone.now().time(),
                amount_kg=Decimal("10.0"),
                batch_biomass_kg=Decimal("100.0"),
                feed_cost=Decimal("50.00"),
                method="MANUAL"
            )

    def test_generate_time_series_daily(self):
        """Test daily time series generation."""
        queryset = FeedingEvent.objects.all()
        time_series = FinanceReportingService.generate_time_series(queryset, interval='day')
        
        # Should have 5 days
        self.assertEqual(len(time_series), 5)
        
        # Each day should have correct values
        for entry in time_series:
            self.assertEqual(entry['total_kg'], 10.0)
            self.assertEqual(entry['total_cost'], 50.0)
            self.assertEqual(entry['events_count'], 1)
            self.assertIn('date', entry)

    def test_generate_time_series_invalid_interval(self):
        """Test invalid interval raises ValueError."""
        queryset = FeedingEvent.objects.all()
        
        with self.assertRaises(ValueError) as context:
            FinanceReportingService.generate_time_series(queryset, interval='invalid')
        
        self.assertIn("Unsupported interval", str(context.exception))

    def test_determine_time_series_interval(self):
        """Test automatic interval determination based on date range."""
        queryset = FeedingEvent.objects.all()
        
        # For 5 days, should use 'day'
        interval = FinanceReportingService._determine_time_series_interval(queryset, None)
        self.assertEqual(interval, 'day')
        
        # User-specified group_by should override
        interval = FinanceReportingService._determine_time_series_interval(queryset, 'week')
        self.assertEqual(interval, 'week')


class FinanceReportingServiceIntegrationTest(TestCase):
    """Test full report generation with all options."""

    def setUp(self):
        """Create comprehensive test data."""
        # Create geography and areas
        self.scotland = Geography.objects.create(name="Scotland")
        self.area1 = Area.objects.create(
            name="Area 1",
            geography=self.scotland,
            latitude=Decimal("57.0"),
            longitude=Decimal("-3.0"),
            max_biomass=Decimal("10000.0")
        )
        self.area2 = Area.objects.create(
            name="Area 2",
            geography=self.scotland,
            latitude=Decimal("58.0"),
            longitude=Decimal("-4.0"),
            max_biomass=Decimal("10000.0")
        )
        
        # Create containers
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        self.container1 = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            area=self.area1,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        self.container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            area=self.area2,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        # Create batch and feeds
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=1
        )
        self.batch = Batch.objects.create(
            batch_number="TEST001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date()
        )
        
        self.feed1 = Feed.objects.create(
            name="Premium Feed",
            brand="Premium Brand",
            size_category="MEDIUM",
            protein_percentage=Decimal("48.0"),
            fat_percentage=Decimal("18.0")
        )
        self.feed2 = Feed.objects.create(
            name="Standard Feed",
            brand="Standard Brand",
            size_category="SMALL",
            protein_percentage=Decimal("42.0"),
            fat_percentage=Decimal("15.0")
        )
        
        # Create events
        today = timezone.now().date()
        FeedingEvent.objects.create(
            batch=self.batch, container=self.container1, feed=self.feed1,
            feeding_date=today, feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"), batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("600.00"), method="MANUAL"
        )
        FeedingEvent.objects.create(
            batch=self.batch, container=self.container2, feed=self.feed2,
            feeding_date=today, feeding_time=timezone.now().time(),
            amount_kg=Decimal("80.0"), batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("400.00"), method="MANUAL"
        )

    def test_generate_finance_report_with_breakdowns(self):
        """Test full report generation with breakdowns enabled."""
        queryset = FeedingEvent.objects.all()
        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=True,
            include_time_series=False
        )
        
        # Verify structure
        self.assertIn('summary', report)
        self.assertIn('by_feed_type', report)
        self.assertIn('by_geography', report)
        self.assertIn('by_area', report)
        self.assertIn('by_container', report)
        self.assertNotIn('time_series', report)
        
        # Verify summary
        self.assertEqual(report['summary']['total_feed_kg'], 180.0)
        self.assertEqual(report['summary']['total_feed_cost'], 1000.0)
        
        # Verify breakdowns populated
        self.assertEqual(len(report['by_feed_type']), 2)
        self.assertEqual(len(report['by_geography']), 1)  # All in Scotland
        self.assertEqual(len(report['by_area']), 2)
        self.assertEqual(len(report['by_container']), 2)

    def test_generate_finance_report_with_time_series(self):
        """Test full report generation with time series enabled."""
        queryset = FeedingEvent.objects.all()
        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=False,
            include_time_series=True
        )
        
        # Verify structure
        self.assertIn('summary', report)
        self.assertNotIn('by_feed_type', report)
        self.assertIn('time_series', report)
        
        # Time series should have at least 1 entry
        self.assertGreater(len(report['time_series']), 0)

    def test_generate_finance_report_minimal(self):
        """Test report generation with no optional features."""
        queryset = FeedingEvent.objects.all()
        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=False,
            include_time_series=False
        )
        
        # Should only have summary
        self.assertIn('summary', report)
        self.assertNotIn('by_feed_type', report)
        self.assertNotIn('time_series', report)


class FinanceReportingServiceEdgeCasesTest(TestCase):
    """Test edge cases and error handling."""

    def test_empty_queryset_all_methods(self):
        """Test all methods handle empty querysets gracefully."""
        queryset = FeedingEvent.objects.none()
        
        # Summary
        summary = FinanceReportingService.calculate_summary(queryset)
        self.assertEqual(summary['total_feed_kg'], 0.0)
        self.assertEqual(summary['events_count'], 0)
        
        # Breakdowns should return empty lists
        self.assertEqual(FinanceReportingService.breakdown_by_feed_type(queryset), [])
        self.assertEqual(FinanceReportingService.breakdown_by_geography(queryset), [])
        self.assertEqual(FinanceReportingService.breakdown_by_area(queryset), [])
        self.assertEqual(FinanceReportingService.breakdown_by_container(queryset), [])
        
        # Time series should return empty list
        self.assertEqual(FinanceReportingService.generate_time_series(queryset), [])
        
        # Full report should work
        report = FinanceReportingService.generate_finance_report(queryset)
        self.assertEqual(report['summary']['events_count'], 0)

    def test_null_nutritional_values_handled(self):
        """Test handling of feeds with null nutritional values."""
        # Create minimal infrastructure
        geography = Geography.objects.create(name="Test")
        area = Area.objects.create(
            name="Test Area", geography=geography,
            latitude=Decimal("0"), longitude=Decimal("0"),
            max_biomass=Decimal("1000.0")
        )
        container_type = ContainerType.objects.create(
            name="Tank", category="TANK", max_volume_m3=Decimal("100.0")
        )
        container = Container.objects.create(
            name="Tank", container_type=container_type, area=area,
            volume_m3=Decimal("50.0"), max_biomass_kg=Decimal("500.0")
        )
        
        # Create batch and feed with NULL nutritional values
        species = Species.objects.create(name="Salmon", scientific_name="Salmo")
        lifecycle_stage = LifeCycleStage.objects.create(name="Smolt", species=species, order=1)
        batch = Batch.objects.create(
            batch_number="TEST001", species=species, lifecycle_stage=lifecycle_stage,
            start_date=timezone.now().date()
        )
        feed = Feed.objects.create(
            name="Minimal Feed",
            brand="Brand",
            size_category="MEDIUM"
            # No nutritional values set (NULL)
        )
        
        FeedingEvent.objects.create(
            batch=batch, container=container, feed=feed,
            feeding_date=timezone.now().date(), feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"), batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("50.00"), method="MANUAL"
        )
        
        # Should not crash
        queryset = FeedingEvent.objects.all()
        breakdown = FinanceReportingService.breakdown_by_feed_type(queryset)
        
        self.assertEqual(len(breakdown), 1)
        self.assertIsNone(breakdown[0]['protein_percentage'])
        self.assertIsNone(breakdown[0]['fat_percentage'])

