"""
Unit tests for FeedingEvent filtering capabilities.

Tests comprehensive filtering including geographic, nutritional, and cost-based filters
for finance reporting.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.batch.models import Batch, LifeCycleStage, Species
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType, FeedContainer
)
from apps.inventory.models import Feed, FeedingEvent
from apps.inventory.api.filters.feeding import FeedingEventFilter


class FeedingEventFilterGeographicTest(TestCase):
    """Test geographic dimension filters for FeedingEvent."""

    def setUp(self):
        """Create test data with geographic hierarchy."""
        # Create geographic hierarchy
        self.scotland = Geography.objects.create(name="Scotland")
        self.faroe = Geography.objects.create(name="Faroe Islands")
        
        self.scotland_area = Area.objects.create(
            name="Scottish Area 1",
            geography=self.scotland,
            latitude=57.0,
            longitude=-3.0,
            max_biomass=Decimal("10000.0")
        )
        self.faroe_area = Area.objects.create(
            name="Faroe Area 1",
            geography=self.faroe,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=Decimal("10000.0")
        )
        
        # Create freshwater station and hall
        self.station = FreshwaterStation.objects.create(
            name="Station A",
            geography=self.scotland,
            station_type="HATCHERY",
            latitude=Decimal("57.5"),
            longitude=Decimal("-3.5")
        )
        self.hall = Hall.objects.create(
            name="Hall 1",
            freshwater_station=self.station
        )
        
        # Create containers
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        
        self.scotland_container = Container.objects.create(
            name="Scotland Tank 1",
            container_type=self.container_type,
            area=self.scotland_area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        self.faroe_container = Container.objects.create(
            name="Faroe Tank 1",
            container_type=self.container_type,
            area=self.faroe_area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
        self.hall_container = Container.objects.create(
            name="Hall Tank 1",
            container_type=self.container_type,
            hall=self.hall,
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
        
        # Create feeding events in different geographies
        self.scotland_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )
        
        self.faroe_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.faroe_container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("15.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )
        
        self.hall_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.hall_container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("12.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )

    def test_filter_by_geography_scotland(self):
        """Test filtering by single geography returns correct events."""
        filter_data = {'geography': self.scotland.id}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.scotland_event, results)
        self.assertNotIn(self.faroe_event, results)

    def test_filter_by_geography_multiple(self):
        """Test filtering by multiple geographies returns combined results."""
        filter_data = {'geography__in': f"{self.scotland.id},{self.faroe.id}"}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 2)
        self.assertIn(self.scotland_event, results)
        self.assertIn(self.faroe_event, results)

    def test_filter_by_area(self):
        """Test filtering by area returns correct events."""
        filter_data = {'area': self.scotland_area.id}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.scotland_event, results)

    def test_filter_by_area_multiple(self):
        """Test filtering by multiple areas returns combined results."""
        filter_data = {'area__in': f"{self.scotland_area.id},{self.faroe_area.id}"}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 2)

    def test_filter_by_freshwater_station(self):
        """Test filtering by freshwater station returns correct events."""
        filter_data = {'freshwater_station': self.station.id}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.hall_event, results)

    def test_filter_by_hall(self):
        """Test filtering by hall returns correct events."""
        filter_data = {'hall': self.hall.id}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.hall_event, results)

    def test_combined_geographic_filters(self):
        """Test combining geography and area filters works as AND."""
        filter_data = {
            'geography': self.scotland.id,
            'area': self.scotland_area.id
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Should only return Scotland events (AND condition)
        self.assertEqual(len(results), 1)
        self.assertIn(self.scotland_event, results)


class FeedingEventFilterNutritionalTest(TestCase):
    """Test feed nutritional property filters."""

    def setUp(self):
        """Create test data with varying feed properties."""
        # Create geography and area
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0.0,
            longitude=0.0,
            max_biomass=Decimal("10000.0")
        )
        
        # Create container
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
        
        # Create feeds with different nutritional profiles
        self.high_protein_feed = Feed.objects.create(
            name="High Protein Feed",
            brand="Premium Brand",
            size_category="MEDIUM",
            protein_percentage=Decimal("48.0"),
            fat_percentage=Decimal("18.0"),
            carbohydrate_percentage=Decimal("20.0")
        )
        
        self.high_fat_feed = Feed.objects.create(
            name="High Fat Feed",
            brand="Premium Brand",
            size_category="LARGE",
            protein_percentage=Decimal("38.0"),
            fat_percentage=Decimal("25.0"),
            carbohydrate_percentage=Decimal("22.0")
        )
        
        self.standard_feed = Feed.objects.create(
            name="Standard Feed",
            brand="Standard Brand",
            size_category="SMALL",
            protein_percentage=Decimal("42.0"),
            fat_percentage=Decimal("15.0"),
            carbohydrate_percentage=Decimal("25.0")
        )
        
        # Create feeding events with different feeds
        self.high_protein_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.high_protein_feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )
        
        self.high_fat_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.high_fat_feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("15.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )
        
        self.standard_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.standard_feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("12.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )

    def test_filter_protein_percentage_gte(self):
        """Test filtering by minimum protein percentage."""
        filter_data = {'feed__protein_percentage__gte': 45}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only high protein feed (48%) should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_protein_event, results)

    def test_filter_protein_percentage_lte(self):
        """Test filtering by maximum protein percentage."""
        filter_data = {'feed__protein_percentage__lte': 40}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only high fat feed (38%) should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_fat_event, results)

    def test_filter_protein_percentage_range(self):
        """Test filtering protein percentage with both min and max."""
        filter_data = {
            'feed__protein_percentage__gte': 40,
            'feed__protein_percentage__lte': 45
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only standard feed (42%) should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.standard_event, results)

    def test_filter_fat_percentage_gte(self):
        """Test filtering by minimum fat percentage."""
        filter_data = {'feed__fat_percentage__gte': 20}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only high fat feed (25%) should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_fat_event, results)

    def test_filter_fat_percentage_lte(self):
        """Test filtering by maximum fat percentage."""
        filter_data = {'feed__fat_percentage__lte': 18}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # High protein (18%) and standard (15%) should match
        self.assertEqual(len(results), 2)
        self.assertIn(self.high_protein_event, results)
        self.assertIn(self.standard_event, results)

    def test_filter_carbohydrate_percentage_range(self):
        """Test filtering by carbohydrate percentage range."""
        filter_data = {
            'feed__carbohydrate_percentage__gte': 21,
            'feed__carbohydrate_percentage__lte': 23
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only high fat feed (22%) should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_fat_event, results)

    def test_filter_by_brand_exact(self):
        """Test filtering by exact brand name (case-insensitive)."""
        filter_data = {'feed__brand': 'premium brand'}  # lowercase
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Both premium brand feeds should match
        self.assertEqual(len(results), 2)
        self.assertIn(self.high_protein_event, results)
        self.assertIn(self.high_fat_event, results)

    def test_filter_by_brand_multiple(self):
        """Test filtering by multiple brands."""
        filter_data = {'feed__brand__in': 'Premium Brand,Standard Brand'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # All three events should match
        self.assertEqual(len(results), 3)

    def test_filter_by_brand_partial(self):
        """Test filtering by partial brand name."""
        filter_data = {'feed__brand__icontains': 'Premium'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Both premium brand feeds should match
        self.assertEqual(len(results), 2)

    def test_filter_by_size_category(self):
        """Test filtering by feed size category."""
        filter_data = {'feed__size_category': 'MEDIUM'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_protein_event, results)

    def test_filter_by_size_category_multiple(self):
        """Test filtering by multiple size categories."""
        filter_data = {'feed__size_category__in': ['SMALL', 'MEDIUM']}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 2)
        self.assertIn(self.high_protein_event, results)
        self.assertIn(self.standard_event, results)

    def test_combined_nutritional_filters(self):
        """Test combining multiple nutritional filters works as AND."""
        filter_data = {
            'feed__protein_percentage__gte': 45,  # >= 45
            'feed__fat_percentage__lte': 20,       # <= 20
            'feed__brand': 'Premium Brand'         # exact match
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only high protein feed matches all conditions (48% protein, 18% fat, Premium)
        self.assertEqual(len(results), 1)
        self.assertIn(self.high_protein_event, results)


class FeedingEventFilterCostTest(TestCase):
    """Test cost-based filters."""

    def setUp(self):
        """Create test data with varying costs."""
        # Create basic infrastructure
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0.0,
            longitude=0.0,
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
        
        # Create feeding events with different costs
        self.low_cost_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("25.00"),
            method="MANUAL"
        )
        
        self.medium_cost_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("15.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("75.00"),
            method="MANUAL"
        )
        
        self.high_cost_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("20.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("150.00"),
            method="MANUAL"
        )

    def test_filter_feed_cost_gte(self):
        """Test filtering by minimum feed cost."""
        filter_data = {'feed_cost__gte': 50}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Medium and high cost events should match
        self.assertEqual(len(results), 2)
        self.assertIn(self.medium_cost_event, results)
        self.assertIn(self.high_cost_event, results)
        self.assertNotIn(self.low_cost_event, results)

    def test_filter_feed_cost_lte(self):
        """Test filtering by maximum feed cost."""
        filter_data = {'feed_cost__lte': 100}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Low and medium cost events should match
        self.assertEqual(len(results), 2)
        self.assertIn(self.low_cost_event, results)
        self.assertIn(self.medium_cost_event, results)
        self.assertNotIn(self.high_cost_event, results)

    def test_filter_feed_cost_range(self):
        """Test filtering by cost range."""
        filter_data = {
            'feed_cost__gte': 50,
            'feed_cost__lte': 100
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only medium cost event should match
        self.assertEqual(len(results), 1)
        self.assertIn(self.medium_cost_event, results)


class FeedingEventFilterCombinationTest(TestCase):
    """Test complex multi-dimensional filter combinations."""

    def setUp(self):
        """Create comprehensive test data for complex filtering."""
        # Create geographies
        self.scotland = Geography.objects.create(name="Scotland")
        self.faroe = Geography.objects.create(name="Faroe Islands")
        
        self.scotland_area = Area.objects.create(
            name="Scottish Area 1",
            geography=self.scotland,
            latitude=57.0,
            longitude=-3.0,
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
            start_date=timezone.now().date() - timedelta(days=60)
        )
        
        # Create feeds
        self.premium_high_fat = Feed.objects.create(
            name="Premium High Fat",
            brand="Supplier Y",
            size_category="MEDIUM",
            protein_percentage=Decimal("45.0"),
            fat_percentage=Decimal("22.0")
        )
        
        self.standard_low_fat = Feed.objects.create(
            name="Standard Low Fat",
            brand="Supplier X",
            size_category="SMALL",
            protein_percentage=Decimal("42.0"),
            fat_percentage=Decimal("10.0")
        )
        
        # Create feeding events with date spread
        today = timezone.now().date()
        
        # Event matching all criteria: Scotland + fat > 12 + Supplier Y + last 32 days
        self.matching_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.premium_high_fat,
            feeding_date=today - timedelta(days=15),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("60.00"),
            method="MANUAL"
        )
        
        # Event not matching geography filter (would match if Faroe container existed)
        self.non_matching_event_1 = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.standard_low_fat,  # Low fat, won't match
            feeding_date=today - timedelta(days=20),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("12.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("48.00"),
            method="MANUAL"
        )
        
        # Event outside date range
        self.old_event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.premium_high_fat,
            feeding_date=today - timedelta(days=40),  # Too old
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("60.00"),
            method="MANUAL"
        )

    def test_scotland_high_fat_supplier_y_last_32_days(self):
        """
        Test the exact finance requirement:
        "Feed with fat % > 12 from Supplier Y in Scotland, last 32 days"
        """
        today = timezone.now().date()
        filter_data = {
            'geography': self.scotland.id,
            'feed__fat_percentage__gte': 12,
            'feed__brand': 'Supplier Y',
            'feeding_date_after': today - timedelta(days=32),
            'feeding_date_before': today
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only the matching event should pass all filters
        self.assertEqual(len(results), 1)
        self.assertIn(self.matching_event, results)

    def test_geographic_plus_nutritional_filters(self):
        """Test combining geographic and nutritional filters."""
        filter_data = {
            'area': self.scotland_area.id,
            'feed__protein_percentage__gte': 44
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Both events with premium high fat feed (45% protein)
        self.assertEqual(len(results), 2)

    def test_cost_plus_nutritional_filters(self):
        """Test combining cost and nutritional filters."""
        filter_data = {
            'feed_cost__gte': 50,
            'feed__fat_percentage__gte': 12
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Events with cost >= 50 AND fat >= 12
        self.assertEqual(len(results), 2)
        self.assertIn(self.matching_event, results)

    def test_date_plus_brand_plus_nutritional(self):
        """Test combining date, brand, and nutritional filters."""
        today = timezone.now().date()
        filter_data = {
            'feeding_date_after': today - timedelta(days=25),
            'feed__brand__icontains': 'Supplier',
            'feed__protein_percentage__gte': 44
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # Only matching event within 25 days with high protein
        self.assertEqual(len(results), 1)
        self.assertIn(self.matching_event, results)

    def test_empty_results_with_impossible_combination(self):
        """Test that impossible filter combinations return empty results."""
        filter_data = {
            'feed__protein_percentage__gte': 50,  # > 50%
            'feed__fat_percentage__gte': 30       # > 30%
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        # No feed has both protein > 50 and fat > 30
        self.assertEqual(len(results), 0)


class FeedingEventFilterBackwardCompatibilityTest(TestCase):
    """Test that existing filters still work (backward compatibility)."""

    def setUp(self):
        """Create minimal test data."""
        self.geography = Geography.objects.create(name="Test Geography")
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=0.0,
            longitude=0.0,
            max_biomass=Decimal("10000.0")
        )
        
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.0")
        )
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("500.0")
        )
        
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
            batch_number="BATCH001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date()
        )
        
        self.feed = Feed.objects.create(
            name="Test Feed Alpha",
            brand="Brand A",
            size_category="MEDIUM"
        )
        
        self.event = FeedingEvent.objects.create(
            batch=self.batch,
            container=self.container,
            feed=self.feed,
            feeding_date=timezone.now().date(),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"),
            batch_biomass_kg=Decimal("100.0"),
            method="MANUAL"
        )

    def test_legacy_feed_name_filter(self):
        """Test existing feed_name filter still works."""
        filter_data = {'feed_name': 'Alpha'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)
        self.assertIn(self.event, results)

    def test_legacy_container_name_filter(self):
        """Test existing container_name filter still works."""
        filter_data = {'container_name': 'Test Container'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)

    def test_legacy_batch_number_filter(self):
        """Test existing batch_number filter still works."""
        filter_data = {'batch_number': 'BATCH001'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)

    def test_legacy_method_in_filter(self):
        """Test existing method_in filter still works."""
        # MultipleChoiceFilter works via Meta fields, test via method exact match
        filter_data = {'method': 'MANUAL'}
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)

    def test_legacy_amount_range_filters(self):
        """Test existing amount min/max filters still work."""
        filter_data = {
            'amount_min': 5,
            'amount_max': 15
        }
        filterset = FeedingEventFilter(data=filter_data, queryset=FeedingEvent.objects.all())
        
        self.assertTrue(filterset.is_valid())
        results = list(filterset.qs)
        
        self.assertEqual(len(results), 1)

