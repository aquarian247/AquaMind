"""
Tests for FCR Calculation Service.

This module tests the Feed Conversion Ratio calculation functionality,
including support for mixed batches.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from unittest.mock import Mock

from apps.inventory.models import (
    Feed, FeedingEvent, BatchFeedingSummary
)
from apps.infrastructure.models import Container, ContainerType, Hall, Geography, FreshwaterStation
from apps.batch.models import Batch, Species, LifeCycleStage, BatchComposition, BatchContainerAssignment
from apps.inventory.services import FCRCalculationService
from apps.inventory.services.fcr_service import FCRCalculationError


class FCRCalculationServiceTest(TestCase):
    """Test cases for FCR Calculation Service."""
    
    def setUp(self):
        """Set up test data."""
        # Create geography
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography for FCR testing"
        )
        
        # Create freshwater station
        self.freshwater_station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=Decimal("10.123456"),
            longitude=Decimal("20.123456"),
            description="Test station for FCR testing"
        )
        
        # Create hall
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.freshwater_station
        )
        
        # Create container type
        self.container_type = ContainerType.objects.create(
            name="Sea Cage",
            category="PEN",
            max_volume_m3=Decimal("1000.00")
        )
        
        # Create container
        self.container = Container.objects.create(
            name="Container 1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("500.00"),
            max_biomass_kg=Decimal("10000.00")
        )
        
        # Create feed
        self.feed = Feed.objects.create(
            name="Premium Salmon Feed",
            brand="AquaFeed",
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
        
        # Create batches
        self.batch1 = Batch.objects.create(
            batch_number="BATCH001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100)
        )
        
        self.batch2 = Batch.objects.create(
            batch_number="BATCH002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=95)
        )
        
        # Create mixed batch
        self.mixed_batch = Batch.objects.create(
            batch_number="MIXED001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=90),
            batch_type='MIXED'
        )
        
        # Create batch composition for mixed batch
        BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.batch1,
            percentage=Decimal("60.0"),
            population_count=600,
            biomass_kg=Decimal("30.0")
        )
        BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.batch2,
            percentage=Decimal("40.0"),
            population_count=400,
            biomass_kg=Decimal("20.0")
        )
        
        # Create container assignments for mixed batch
        BatchContainerAssignment.objects.create(
            batch=self.mixed_batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("50.0"),
            biomass_kg=Decimal("50.0"),
            assignment_date=date.today() - timedelta(days=10),
            is_active=True
        )
    
    def test_get_batch_feed_consumption_single_batch(self):
        """Test getting feed consumption for a single batch."""
        # Create feeding events
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("250.0")
        )
        
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=3),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("120.0"),
            batch_biomass_kg=Decimal("1100.0"),
            feed_cost=Decimal("300.0")
        )
        
        # Calculate feed consumption
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        total_feed = FCRCalculationService.get_batch_feed_consumption(
            self.batch1, period_start, period_end
        )
        
        self.assertEqual(total_feed, Decimal("220.0"))
    
    def test_get_batch_feed_consumption_mixed_batch(self):
        """Test getting feed consumption for a mixed batch."""
        # Create feeding events for the container with mixed batch
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("600.0"),  # 60% of container
            feed_cost=Decimal("250.0")
        )
        
        FeedingEvent.objects.create(
            batch=self.batch2,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("80.0"),
            batch_biomass_kg=Decimal("400.0"),  # 40% of container
            feed_cost=Decimal("200.0")
        )
        
        # Calculate feed consumption for mixed batch
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        total_feed = FCRCalculationService.get_batch_feed_consumption(
            self.mixed_batch, period_start, period_end
        )
        
        # Should be proportional: (100 * 0.6) + (80 * 0.4) = 60 + 32 = 92
        expected_feed = Decimal("100.0") * Decimal("0.6") + Decimal("80.0") * Decimal("0.4")
        self.assertEqual(total_feed, expected_feed)
    
    def test_get_batch_feed_cost_single_batch(self):
        """Test getting feed cost for a single batch."""
        # Create feeding events
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("250.0")
        )
        
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=3),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("120.0"),
            batch_biomass_kg=Decimal("1100.0"),
            feed_cost=Decimal("300.0")
        )
        
        # Calculate feed cost
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        total_cost = FCRCalculationService.get_batch_feed_cost(
            self.batch1, period_start, period_end
        )
        
        self.assertEqual(total_cost, Decimal("550.0"))
    
    def test_get_batch_feed_cost_mixed_batch(self):
        """Test getting feed cost for a mixed batch."""
        # Create feeding events for the container with mixed batch
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("600.0"),
            feed_cost=Decimal("250.0")
        )
        
        FeedingEvent.objects.create(
            batch=self.batch2,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("80.0"),
            batch_biomass_kg=Decimal("400.0"),
            feed_cost=Decimal("200.0")
        )
        
        # Calculate feed cost for mixed batch
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        total_cost = FCRCalculationService.get_batch_feed_cost(
            self.mixed_batch, period_start, period_end
        )
        
        # Should be proportional: (250 * 0.6) + (200 * 0.4) = 150 + 80 = 230
        expected_cost = Decimal("250.0") * Decimal("0.6") + Decimal("200.0") * Decimal("0.4")
        self.assertEqual(total_cost, expected_cost)
    
    def test_calculate_batch_fcr_with_biomass_gain(self):
        """Test calculating FCR with provided biomass gain."""
        # Create feeding events
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("250.0")
        )
        
        # Calculate FCR
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        biomass_gain = Decimal("80.0")  # 80kg gain
        
        fcr = FCRCalculationService.calculate_batch_fcr(
            self.batch1, period_start, period_end, biomass_gain
        )
        
        # FCR = feed consumed / biomass gain = 100 / 80 = 1.25
        expected_fcr = Decimal("100.0") / Decimal("80.0")
        self.assertEqual(fcr, expected_fcr)
    
    def test_calculate_batch_fcr_zero_biomass_gain(self):
        """Test calculating FCR with zero biomass gain."""
        # Create feeding events
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("250.0")
        )
        
        # Calculate FCR with zero biomass gain
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        with self.assertRaises(FCRCalculationError):
            FCRCalculationService.calculate_batch_fcr(
                self.batch1, period_start, period_end, Decimal("0.0")
            )
    
    def test_update_batch_feeding_summary(self):
        """Test updating batch feeding summary."""
        # Create feeding events
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=5),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("250.0")
        )
        
        FeedingEvent.objects.create(
            batch=self.batch1,
            container=self.container,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=3),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("120.0"),
            batch_biomass_kg=Decimal("1100.0"),
            feed_cost=Decimal("300.0")
        )
        
        # Update batch feeding summary
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        biomass_gain = Decimal("150.0")
        starting_biomass = Decimal("950.0")
        ending_biomass = Decimal("1100.0")
        
        summary = FCRCalculationService.update_batch_feeding_summary(
            batch=self.batch1,
            period_start=period_start,
            period_end=period_end,
            biomass_gain_kg=biomass_gain,
            starting_biomass_kg=starting_biomass,
            ending_biomass_kg=ending_biomass
        )
        
        # Check summary values
        self.assertEqual(summary.batch, self.batch1)
        self.assertEqual(summary.period_start, period_start)
        self.assertEqual(summary.period_end, period_end)
        self.assertEqual(summary.total_feed_kg, Decimal("220.0"))
        self.assertEqual(summary.total_feed_cost, Decimal("550.0"))
        self.assertEqual(summary.biomass_gain_kg, biomass_gain)
        self.assertEqual(summary.starting_biomass_kg, starting_biomass)
        self.assertEqual(summary.ending_biomass_kg, ending_biomass)
        
        # FCR = 220 / 150 = 1.4667 (rounded to 4 decimal places)
        expected_fcr = Decimal("220.0") / Decimal("150.0")
        self.assertAlmostEqual(summary.fcr, expected_fcr, places=4)
    
    def test_update_batch_feeding_summary_existing(self):
        """Test updating an existing batch feeding summary."""
        # Create initial summary
        period_start = date.today() - timedelta(days=7)
        period_end = date.today() - timedelta(days=1)
        
        existing_summary = BatchFeedingSummary.objects.create(
            batch=self.batch1,
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal("100.0"),
            total_biomass_gain_kg=Decimal("80.0"),
            fcr=Decimal("1.25")
        )
        
        # Update with new values
        updated_summary = FCRCalculationService.update_batch_feeding_summary(
            batch=self.batch1,
            period_start=period_start,
            period_end=period_end,
            biomass_gain_kg=Decimal("120.0"),
            starting_biomass_kg=Decimal("950.0"),
            ending_biomass_kg=Decimal("1070.0")
        )
        
        # Should be the same object, updated
        self.assertEqual(updated_summary.id, existing_summary.id)
        self.assertEqual(updated_summary.biomass_gain_kg, Decimal("120.0"))
        self.assertEqual(updated_summary.starting_biomass_kg, Decimal("950.0"))
        self.assertEqual(updated_summary.ending_biomass_kg, Decimal("1070.0"))
    
    def test_get_mixed_batch_composition_percentages(self):
        """Test getting composition percentages for mixed batch."""
        percentages = FCRCalculationService.get_mixed_batch_composition_percentages(
            self.mixed_batch
        )
        
        expected_percentages = {
            self.batch1.id: Decimal("60.0"),
            self.batch2.id: Decimal("40.0")
        }
        
        self.assertEqual(percentages, expected_percentages)
    
    def test_get_mixed_batch_composition_percentages_single_batch(self):
        """Test getting composition percentages for single (non-mixed) batch."""
        percentages = FCRCalculationService.get_mixed_batch_composition_percentages(
            self.batch1
        )

        # Single batch should return 100% for itself
        expected_percentages = {self.batch1.id: Decimal("100.0")}
        self.assertEqual(percentages, expected_percentages)

    # ============================================================================
    # Tests for Pure Helper Functions
    # ============================================================================

    def test_calculate_fcr_value_valid_inputs(self):
        """Test FCR calculation with valid inputs."""
        total_feed = Decimal('100.0')
        biomass_gain = Decimal('80.0')

        fcr = FCRCalculationService._calculate_fcr_value(total_feed, biomass_gain)
        expected_fcr = Decimal('1.25')  # 100 / 80

        self.assertEqual(fcr, expected_fcr)

    def test_calculate_fcr_value_zero_biomass_gain(self):
        """Test FCR calculation with zero biomass gain raises error."""
        total_feed = Decimal('100.0')
        biomass_gain = Decimal('0')

        with self.assertRaises(FCRCalculationError):
            FCRCalculationService._calculate_fcr_value(total_feed, biomass_gain)

    def test_calculate_fcr_value_negative_biomass_gain(self):
        """Test FCR calculation with negative biomass gain raises error."""
        total_feed = Decimal('100.0')
        biomass_gain = Decimal('-10.0')

        with self.assertRaises(FCRCalculationError):
            FCRCalculationService._calculate_fcr_value(total_feed, biomass_gain)

    def test_calculate_fcr_value_zero_feed_consumed(self):
        """Test FCR calculation with zero feed consumed returns zero."""
        total_feed = Decimal('0')
        biomass_gain = Decimal('80.0')

        fcr = FCRCalculationService._calculate_fcr_value(total_feed, biomass_gain)
        self.assertEqual(fcr, Decimal('0'))

    def test_calculate_confidence_level_from_days_very_high(self):
        """Test confidence level calculation for very recent weighing."""
        days = 5
        confidence = FCRCalculationService._calculate_confidence_level_from_days(days)
        self.assertEqual(confidence, 'VERY_HIGH')

    def test_calculate_confidence_level_from_days_high(self):
        """Test confidence level calculation for recent weighing."""
        days = 15
        confidence = FCRCalculationService._calculate_confidence_level_from_days(days)
        self.assertEqual(confidence, 'HIGH')

    def test_calculate_confidence_level_from_days_medium(self):
        """Test confidence level calculation for medium-term weighing."""
        days = 25
        confidence = FCRCalculationService._calculate_confidence_level_from_days(days)
        self.assertEqual(confidence, 'MEDIUM')

    def test_calculate_confidence_level_from_days_low(self):
        """Test confidence level calculation for old weighing."""
        days = 50
        confidence = FCRCalculationService._calculate_confidence_level_from_days(days)
        self.assertEqual(confidence, 'LOW')

    def test_calculate_confidence_level_from_days_negative(self):
        """Test confidence level calculation for future weighing date."""
        days = -5
        confidence = FCRCalculationService._calculate_confidence_level_from_days(days)
        self.assertEqual(confidence, 'LOW')

    def test_determine_estimation_method_from_data_with_biomass_and_weighing(self):
        """Test estimation method determination with biomass gain and weighing events."""
        biomass_gain = Decimal('100.0')
        has_weighing_events = True

        method = FCRCalculationService._determine_estimation_method_from_data(
            biomass_gain, has_weighing_events
        )
        self.assertEqual(method, 'MEASURED')

    def test_determine_estimation_method_from_data_with_biomass_no_weighing(self):
        """Test estimation method determination with biomass gain but no weighing events."""
        biomass_gain = Decimal('100.0')
        has_weighing_events = False

        method = FCRCalculationService._determine_estimation_method_from_data(
            biomass_gain, has_weighing_events
        )
        self.assertEqual(method, 'INTERPOLATED')

    def test_determine_estimation_method_from_data_no_biomass(self):
        """Test estimation method determination with no biomass gain."""
        biomass_gain = None
        has_weighing_events = True

        method = FCRCalculationService._determine_estimation_method_from_data(
            biomass_gain, has_weighing_events
        )
        self.assertIsNone(method)

    def test_prorate_feed_by_composition(self):
        """Test feed prorating by composition percentage."""
        feed_amount = Decimal('100.0')
        percentage = Decimal('60.0')

        prorated = FCRCalculationService._prorate_feed_by_composition(
            feed_amount, percentage
        )
        expected = Decimal('60.0')  # 100 * (60/100)

        self.assertEqual(prorated, expected)

    def test_calculate_weighted_average_fcr_with_contributions(self):
        """Test weighted average FCR calculation with valid contributions."""
        contributions = [
            (Decimal('100.0'), Decimal('1.2')),
            (Decimal('200.0'), Decimal('1.5')),
        ]

        weighted_avg = FCRCalculationService._calculate_weighted_average_fcr(contributions)
        # (100*1.2 + 200*1.5) / (100+200) = (120 + 300) / 300 = 420/300 = 1.4
        expected = Decimal('1.400')  # Rounded to 3 decimal places

        self.assertEqual(weighted_avg, expected)

    def test_calculate_weighted_average_fcr_empty_contributions(self):
        """Test weighted average FCR calculation with no contributions."""
        contributions = []

        weighted_avg = FCRCalculationService._calculate_weighted_average_fcr(contributions)
        self.assertIsNone(weighted_avg)

    def test_calculate_weighted_average_fcr_zero_weights(self):
        """Test weighted average FCR calculation with zero weights."""
        contributions = [
            (Decimal('0'), Decimal('1.2')),
            (Decimal('0'), Decimal('1.5')),
        ]

        weighted_avg = FCRCalculationService._calculate_weighted_average_fcr(contributions)
        self.assertIsNone(weighted_avg)

    def test_aggregate_feeding_event_data_with_events(self):
        """Test aggregation of feeding event data."""
        event_data = [
            {'batch_biomass_kg': Decimal('1000.0'), 'feeding_percentage': Decimal('5.0')},
            {'batch_biomass_kg': Decimal('1100.0'), 'feeding_percentage': Decimal('4.5')},
            {'batch_biomass_kg': None, 'feeding_percentage': Decimal('6.0')},
        ]

        avg_biomass, avg_feeding_pct = FCRCalculationService._aggregate_feeding_event_data(event_data)

        # Biomass: (1000 + 1100) / 2 = 1050
        self.assertEqual(avg_biomass, Decimal('1050.0'))
        # Feeding %: (5.0 + 4.5 + 6.0) / 3 = 5.1667
        self.assertAlmostEqual(avg_feeding_pct, Decimal('5.1667'), places=4)

    def test_aggregate_feeding_event_data_empty(self):
        """Test aggregation of empty feeding event data."""
        event_data = []

        avg_biomass, avg_feeding_pct = FCRCalculationService._aggregate_feeding_event_data(event_data)

        self.assertIsNone(avg_biomass)
        self.assertIsNone(avg_feeding_pct)

    def test_calculate_worst_confidence_level(self):
        """Test calculation of worst confidence level from list."""
        confidence_levels = ['HIGH', 'VERY_HIGH', 'MEDIUM', 'LOW']
        worst = FCRCalculationService._calculate_worst_confidence_level(confidence_levels)
        self.assertEqual(worst, 'LOW')

    def test_calculate_worst_confidence_level_empty(self):
        """Test calculation of worst confidence level from empty list."""
        confidence_levels = []
        worst = FCRCalculationService._calculate_worst_confidence_level(confidence_levels)
        self.assertEqual(worst, 'LOW')

    def test_determine_overall_estimation_method_single_method(self):
        """Test overall estimation method with single method."""
        methods = ['MEASURED', 'MEASURED', 'MEASURED']
        overall = FCRCalculationService._determine_overall_estimation_method(methods)
        self.assertEqual(overall, 'MEASURED')

    def test_determine_overall_estimation_method_mixed(self):
        """Test overall estimation method with mixed methods."""
        methods = ['MEASURED', 'INTERPOLATED']
        overall = FCRCalculationService._determine_overall_estimation_method(methods)
        self.assertEqual(overall, 'MIXED')

    def test_determine_overall_estimation_method_only_interpolated(self):
        """Test overall estimation method with only interpolated."""
        methods = ['INTERPOLATED', 'INTERPOLATED']
        overall = FCRCalculationService._determine_overall_estimation_method(methods)
        self.assertEqual(overall, 'INTERPOLATED')

    def test_determine_overall_estimation_method_only_measured(self):
        """Test overall estimation method with only measured."""
        methods = ['MEASURED', 'MEASURED']
        overall = FCRCalculationService._determine_overall_estimation_method(methods)
        self.assertEqual(overall, 'MEASURED') 