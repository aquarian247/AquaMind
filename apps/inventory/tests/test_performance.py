"""
Performance tests for inventory finance reporting.

These tests validate that the finance reporting system can handle
large datasets efficiently with acceptable response times and query
counts.

Run with: python manage.py test apps.inventory.tests.test_performance
"""
import time
from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from django.db import connection
from datetime import timedelta

from apps.batch.models import (
    Batch, LifeCycleStage, Species, BatchContainerAssignment
)
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType
)
from apps.inventory.models import Feed, FeedingEvent, FeedPurchase
from apps.inventory.services import FinanceReportingService


@override_settings(DEBUG=True)  # Enable query tracking
class FinanceReportingPerformanceTest(TestCase):
    """
    Performance validation for finance reporting with large datasets.

    Tests use realistic data with proper relationships for:
    - Geography → Area → Container
    - Batch → BatchContainerAssignment → Container
    - Feed → FeedPurchase
    - FeedingEvent with proper relationships and calculated costs
    """

    @classmethod
    def _create_geographies_and_areas(cls):
        """Create geographies and areas."""
        cls.scotland = Geography.objects.create(name="Scotland")
        cls.faroe = Geography.objects.create(name="Faroe Islands")

        cls.areas = []
        for geo in [cls.scotland, cls.faroe]:
            for i in range(3):
                area = Area.objects.create(
                    name=f"{geo.name} Area {i+1}",
                    geography=geo,
                    latitude=Decimal('57.0') + i,
                    longitude=Decimal('-3.0') - i,
                    max_biomass=Decimal('50000.0')
                )
                cls.areas.append(area)

    @classmethod
    def _create_stations_and_halls(cls):
        """Create freshwater stations and halls."""
        cls.station = FreshwaterStation.objects.create(
            name="Test Station",
            geography=cls.scotland,
            station_type="HATCHERY",
            latitude=Decimal('57.5'),
            longitude=Decimal('-3.5')
        )
        cls.halls = [
            Hall.objects.create(
                name=f"Hall {i+1}",
                freshwater_station=cls.station
            )
            for i in range(2)
        ]

    @classmethod
    def _create_containers(cls):
        """Create containers for areas and halls."""
        cls.container_type = ContainerType.objects.create(
            name="Standard Tank",
            category="TANK",
            max_volume_m3=Decimal('200.0')
        )

        cls.containers = []
        # Area-based containers
        for area in cls.areas:
            for i in range(5):
                container = Container.objects.create(
                    name=f"{area.name} Tank {i+1}",
                    container_type=cls.container_type,
                    area=area,
                    volume_m3=Decimal('100.0'),
                    max_biomass_kg=Decimal('5000.0')
                )
                cls.containers.append(container)

        # Hall-based containers
        for hall in cls.halls:
            for i in range(2):
                container = Container.objects.create(
                    name=f"{hall.name} Tank {i+1}",
                    container_type=cls.container_type,
                    hall=hall,
                    volume_m3=Decimal('100.0'),
                    max_biomass_kg=Decimal('5000.0')
                )
                cls.containers.append(container)

    @classmethod
    def _create_feeds(cls):
        """Create feeds with varying nutritional profiles."""
        cls.feeds_with_purchases = []
        nutritional_profiles = [
            ("Premium Starter", "Supplier A", 50, 22, Decimal('7.50')),
            ("Growth Feed", "Supplier B", 46, 20, Decimal('6.50')),
            ("Standard Feed", "Supplier A", 42, 16, Decimal('5.50')),
            ("Economy Feed", "Supplier C", 38, 12, Decimal('4.50')),
            ("Finishing Feed", "Supplier B", 36, 10, Decimal('4.00')),
        ]

        for name, supplier, protein, fat, cost in nutritional_profiles:
            feed = Feed.objects.create(
                name=name,
                brand=supplier,
                size_category="MEDIUM",
                protein_percentage=Decimal(str(protein)),
                fat_percentage=Decimal(str(fat))
            )

            purchase = FeedPurchase.objects.create(
                feed=feed,
                quantity_kg=Decimal('100000.0'),
                cost_per_kg=cost,
                supplier=supplier,
                purchase_date=timezone.now().date() - timedelta(days=60),
                batch_number=f"BATCH-{name[:3].upper()}-001"
            )

            cls.feeds_with_purchases.append((feed, purchase, cost))

    @classmethod
    def _create_batches(cls):
        """Create batches with proper container assignments."""
        cls.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        cls.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=cls.species,
            order=3
        )

        cls.batches = []
        for i in range(10):
            batch = Batch.objects.create(
                batch_number=f"PERF-TEST-{i+1:04d}",
                species=cls.species,
                lifecycle_stage=cls.lifecycle_stage,
                start_date=timezone.now().date() - timedelta(days=90)
            )
            cls.batches.append(batch)

            # Assign batch to a container
            container = cls.containers[i % len(cls.containers)]
            BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=cls.lifecycle_stage,
                population_count=10000,
                assignment_date=timezone.now().date() - timedelta(days=90),
                biomass_kg=Decimal('500.0'),
                is_active=True
            )

    @classmethod
    def setUpClass(cls):
        """Create realistic test infrastructure ONCE for all tests."""
        super().setUpClass()
        cls._create_geographies_and_areas()
        cls._create_stations_and_halls()
        cls._create_containers()
        cls._create_feeds()
        cls._create_batches()

    def create_feeding_events(self, count: int):
        """
        Create specified number of feeding events distributed across
        multiple dates, containers, feeds, and batches.

        Args:
            count: Number of feeding events to create
        """
        events = []
        start_date = timezone.now().date() - timedelta(days=90)

        for i in range(count):
            # Distribute events
            days_offset = i % 90
            container_idx = i % len(self.containers)
            feed_idx = i % len(self.feeds_with_purchases)
            batch_idx = i % len(self.batches)

            feed, purchase, cost_per_kg = self.feeds_with_purchases[feed_idx]
            container = self.containers[container_idx]
            batch = self.batches[batch_idx]

            # Realistic feed amounts (10-100 kg per event)
            amount_kg = Decimal(str(10 + (i % 90)))
            feed_cost = amount_kg * cost_per_kg

            events.append(FeedingEvent(
                batch=batch,
                container=container,
                feed=feed,
                feeding_date=start_date + timedelta(days=days_offset),
                feeding_time=timezone.now().time(),
                amount_kg=amount_kg,
                batch_biomass_kg=Decimal('500.0'),  # Match assignment biomass
                feed_cost=feed_cost,
                method='AUTOMATIC'
            ))

        # Bulk create for efficiency
        FeedingEvent.objects.bulk_create(events, batch_size=1000)

    def test_performance_10k_events_full_report(self):
        """
        Performance test: Generate full finance report with 10k events.

        Requirements:
        - Response time < 2 seconds
        - Query count < 10
        - Correct data returned
        """
        # Create 10,000 feeding events
        self.create_feeding_events(10000)

        # Get all events
        queryset = FeedingEvent.objects.all()

        # Measure query count
        connection.queries_log.clear()

        # Measure response time
        start_time = time.time()

        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=True,
            include_time_series=False,  # Skip time series for this test
            group_by=None
        )

        elapsed_time = time.time() - start_time
        query_count = len(connection.queries)

        # Performance assertions
        msg = f"Report took {elapsed_time:.2f}s (should be < 2s)"
        self.assertLess(elapsed_time, 2.0, msg)

        msg = f"Report used {query_count} queries (should be < 10)"
        self.assertLess(query_count, 10, msg)

        # Correctness assertions
        self.assertIn('summary', report)
        self.assertIn('by_feed_type', report)
        self.assertIn('by_geography', report)
        self.assertIn('by_area', report)

        # Verify summary has realistic totals
        summary = report['summary']
        self.assertEqual(summary['events_count'], 10000)
        self.assertGreater(summary['total_feed_kg'], 0)
        self.assertGreater(summary['total_feed_cost'], 0)

        # Verify breakdowns exist
        self.assertGreater(len(report['by_feed_type']), 0)
        self.assertGreater(len(report['by_geography']), 0)
        self.assertGreater(len(report['by_area']), 0)

        print("\n✅ Performance Test Results:")
        print("   - Events processed: 10,000")
        print(f"   - Response time: {elapsed_time:.3f}s")
        print(f"   - Query count: {query_count}")
        print(f"   - Total feed kg: {summary['total_feed_kg']:.2f}")
        print(f"   - Total cost: ${summary['total_feed_cost']:.2f}")

    def test_performance_10k_events_filtered(self):
        """
        Performance test: Filtered report with 10k events.

        Tests realistic filtering scenario:
        - Geography filter (Scotland only)
        - Feed protein filter (>40%)
        """
        self.create_feeding_events(10000)

        # Apply realistic filters
        queryset = FeedingEvent.objects.filter(
            container__area__geography=self.scotland,
            feed__protein_percentage__gte=40
        )

        connection.queries_log.clear()
        start_time = time.time()

        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=True,
            include_time_series=False,
            group_by=None
        )

        elapsed_time = time.time() - start_time
        query_count = len(connection.queries)

        # Performance assertions
        self.assertLess(elapsed_time, 2.0)
        self.assertLess(query_count, 10)

        # Verify filtering worked
        self.assertGreater(report['summary']['events_count'], 0)
        self.assertLess(report['summary']['events_count'], 10000)

        print("\n✅ Filtered Performance Test Results:")
        print(f"   - Response time: {elapsed_time:.3f}s")
        print(f"   - Query count: {query_count}")
        print(f"   - Filtered events: {report['summary']['events_count']}")

    def test_performance_10k_events_time_series(self):
        """
        Performance test: Time series generation with 10k events.

        Time series is computationally expensive tested separately.
        """
        self.create_feeding_events(10000)

        queryset = FeedingEvent.objects.all()

        connection.queries_log.clear()
        start_time = time.time()

        report = FinanceReportingService.generate_finance_report(
            queryset=queryset,
            include_breakdowns=False,  # Skip breakdowns for this test
            include_time_series=True,
            group_by='week'
        )

        elapsed_time = time.time() - start_time
        query_count = len(connection.queries)

        # Slightly more lenient for time series (can be 2.5s)
        msg = (
            f"Time series took {elapsed_time:.2f}s (should be < 2.5s)"
        )
        self.assertLess(elapsed_time, 2.5, msg)
        self.assertLess(query_count, 10)

        # Verify time series generated
        self.assertIn('time_series', report)
        self.assertGreater(len(report['time_series']), 0)

        print("\n✅ Time Series Performance Test Results:")
        print(f"   - Response time: {elapsed_time:.3f}s")
        print(f"   - Query count: {query_count}")
        print(f"   - Time buckets: {len(report['time_series'])}")

    def test_query_optimization_select_related(self):
        """
        Verify that service uses proper query optimization.

        Tests that select_related is used for foreign keys to avoid
        N+1 queries.
        """
        # Create modest dataset
        self.create_feeding_events(100)

        queryset = FeedingEvent.objects.all()

        connection.queries_log.clear()

        # Generate breakdown by feed type
        breakdown = FinanceReportingService.breakdown_by_feed_type(
            queryset
        )

        query_count = len(connection.queries)

        # Should be 1-2 queries max (one for aggregation)
        msg = (
            f"Feed type breakdown used {query_count} queries "
            "(should be ≤2)"
        )
        self.assertLessEqual(query_count, 2, msg)

        # Verify data correctness
        self.assertGreater(len(breakdown), 0)
        for item in breakdown:
            self.assertIn('feed_id', item)
            self.assertIn('feed_name', item)
            self.assertIn('total_kg', item)

        print("\n✅ Query Optimization Test:")
        print(f"   - Queries for breakdown: {query_count}")
        print(f"   - Feed types found: {len(breakdown)}")
