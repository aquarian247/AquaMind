"""
Unit tests for container-level FCR calculations.

Tests the core business logic for calculating FCR at container level,
including confidence levels, estimation methods, and edge cases.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta, datetime, time
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.inventory.services.fcr_service import FCRCalculationService, FCRCalculationError
from apps.inventory.models import FeedingEvent, ContainerFeedingSummary, Feed
from apps.batch.models import Batch, BatchContainerAssignment, Species, LifeCycleStage
from apps.infrastructure.models import Container, FreshwaterStation, Area, Geography


User = get_user_model()


class ContainerFCRCalculationsTest(TestCase):
    """Test container-level FCR calculation logic."""

    def setUp(self):
        """Set up test data."""
        # Create geography hierarchy
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=60.0,
            longitude=-7.0,
            max_biomass=10000.0
        )
        # Create container type
        from apps.infrastructure.models import ContainerType
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.0
        )

        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            geography=self.geography,
            station_type="FRESHWATER",
            latitude=60.0,
            longitude=-7.0
        )

        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,  # Container in area, not hall
            volume_m3=50.0,
            max_biomass_kg=1000.0
        )

        # Create species and lifecycle
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Post-Smolt",
            order=4,
            species=self.species
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number="TEST-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100)
        )

        # Create container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2500,
            avg_weight_g=Decimal('150.00'),
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )

        # Create feed type
        self.feed = Feed.objects.create(
            name="Test Salmon Feed",
            brand="TestFeed",
            size_category="MEDIUM",
            protein_percentage=Decimal('45.0'),
            fat_percentage=Decimal('25.0'),
            carbohydrate_percentage=Decimal('15.0')
        )

        # Create feeding events
        self.feeding_events = []
        for i in range(7):  # One week of feeding
            event_date = date.today() - timedelta(days=6-i)
            event = FeedingEvent.objects.create(
                container=self.container,
                batch=self.batch,
                feed=self.feed,
                feeding_date=event_date,
                feeding_time=time(9, 0),  # 9:00 AM
                amount_kg=Decimal('25.0'),
                batch_biomass_kg=Decimal('375.0'),  # 2500 fish * 150g = 375kg
                feed_cost=Decimal('125.00')
            )
            self.feeding_events.append(event)

    def test_calculate_container_fcr_success(self):
        """Test successful container FCR calculation."""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Mock growth data
        with patch.object(FCRCalculationService, '_get_container_growth_data') as mock_growth:
            mock_growth.return_value = {
                'starting_biomass': Decimal('375.0'),
                'ending_biomass': Decimal('390.0'),  # 15kg growth
                'growth_kg': Decimal('15.0'),
                'has_weighing_events': True,
                'data_points': 2
            }

            result = FCRCalculationService.calculate_container_fcr(
                self.assignment, start_date, end_date
            )

            self.assertIsNotNone(result)
            self.assertEqual(result['total_feed_kg'], Decimal('175.0'))  # 25kg * 7 days
            self.assertEqual(result['growth_kg'], Decimal('15.0'))
            self.assertAlmostEqual(result['fcr'], Decimal('11.67'), places=2)  # 175 / 15
            self.assertEqual(result['confidence_level'], 'LOW')  # Default for new data without weighing
            self.assertEqual(result['estimation_method'], 'MEASURED')

    def test_calculate_container_fcr_no_feed(self):
        """Test FCR calculation with no feeding events."""
        # Create new container for this test
        empty_container = Container.objects.create(
            name="Empty Container",
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=1000.0
        )

        # Create assignment without feeding events
        empty_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=empty_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2500,
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )

        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = FCRCalculationService.calculate_container_fcr(
            empty_assignment, start_date, end_date
        )

        self.assertIsNone(result)

    def test_calculate_container_fcr_zero_growth(self):
        """Test FCR calculation with zero growth (division by zero protection)."""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        with patch.object(FCRCalculationService, '_get_container_growth_data') as mock_growth:
            mock_growth.return_value = {
                'starting_biomass': Decimal('375.0'),
                'ending_biomass': Decimal('375.0'),  # No growth
                'growth_kg': Decimal('0.0'),
                'has_weighing_events': True,
                'data_points': 2
            }

            result = FCRCalculationService.calculate_container_fcr(
                self.assignment, start_date, end_date
            )

            self.assertIsNone(result)

    def test_confidence_level_calculation(self):
        """Test confidence level calculation based on weighing date."""
        period_end = date.today()

        # Very high confidence (< 10 days)
        confidence = FCRCalculationService.calculate_confidence_level(
            self.batch, period_end, date.today() - timedelta(days=5)
        )
        self.assertEqual(confidence, 'VERY_HIGH')

        # High confidence (10-20 days)
        confidence = FCRCalculationService.calculate_confidence_level(
            self.batch, period_end, date.today() - timedelta(days=15)
        )
        self.assertEqual(confidence, 'HIGH')

        # Medium confidence (20-40 days)
        confidence = FCRCalculationService.calculate_confidence_level(
            self.batch, period_end, date.today() - timedelta(days=30)
        )
        self.assertEqual(confidence, 'MEDIUM')

        # Low confidence (> 40 days)
        confidence = FCRCalculationService.calculate_confidence_level(
            self.batch, period_end, date.today() - timedelta(days=50)
        )
        self.assertEqual(confidence, 'LOW')

        # Low confidence (no weighing date)
        confidence = FCRCalculationService.calculate_confidence_level(
            self.batch, period_end, None
        )
        self.assertEqual(confidence, 'LOW')

    def test_estimation_method_determination(self):
        """Test estimation method determination."""
        # Measured (has weighing events)
        method = FCRCalculationService.determine_estimation_method(
            Decimal('15.0'), True
        )
        self.assertEqual(method, 'MEASURED')

        # Interpolated (no weighing events)
        method = FCRCalculationService.determine_estimation_method(
            Decimal('15.0'), False
        )
        self.assertEqual(method, 'INTERPOLATED')

        # None (no FCR value)
        method = FCRCalculationService.determine_estimation_method(
            None, True
        )
        self.assertIsNone(method)

    def test_mixed_batch_feed_proration(self):
        """Test feed consumption calculation for mixed batches."""
        # Create mixed batch
        mixed_batch = Batch.objects.create(
            batch_number="MIXED-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100),
            batch_type='MIXED'
        )

        # Create composition (this batch is 50% of the mixed batch)
        from apps.batch.models import BatchComposition
        composition = BatchComposition.objects.create(
            mixed_batch=mixed_batch,
            source_batch=self.batch,
            percentage=Decimal('50.0'),
            population_count=2500,
            biomass_kg=Decimal('375.0')
        )

        # Create assignment for mixed batch
        mixed_assignment = BatchContainerAssignment.objects.create(
            batch=mixed_batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2500,
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )

        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Mock the proration method
        with patch.object(FCRCalculationService, '_get_mixed_container_feed_consumption') as mock_prorate:
            mock_prorate.return_value = Decimal('87.5')  # Half of 175kg

            feed_consumed = FCRCalculationService._get_container_feed_consumption(
                mixed_assignment, start_date, end_date
            )

            mock_prorate.assert_called_once()
            self.assertEqual(feed_consumed, Decimal('87.5'))

    def test_container_feeding_summary_creation(self):
        """Test creation of container feeding summary."""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Mock the calculation methods
        with patch.object(FCRCalculationService, 'calculate_container_fcr') as mock_calc:
            mock_calc.return_value = {
                'total_feed_kg': Decimal('175.0'),
                'starting_biomass_kg': Decimal('375.0'),
                'ending_biomass_kg': Decimal('390.0'),
                'growth_kg': Decimal('15.0'),
                'fcr': Decimal('11.67'),
                'confidence_level': 'HIGH',
                'estimation_method': 'MEASURED',
                'data_points': 7
            }

            summary = FCRCalculationService.create_container_feeding_summary(
                self.assignment, start_date, end_date
            )

            self.assertIsNotNone(summary)
            self.assertEqual(summary.container_assignment, self.assignment)
            self.assertEqual(summary.total_feed_kg, Decimal('175.0'))
            self.assertEqual(summary.fcr, Decimal('11.67'))
            self.assertEqual(summary.confidence_level, 'HIGH')

            # Verify it was saved to database
            saved_summary = ContainerFeedingSummary.objects.get(
                container_assignment=self.assignment,
                period_start=start_date,
                period_end=end_date
            )
            self.assertEqual(saved_summary.fcr, Decimal('11.67'))

    def test_batch_aggregation_from_containers(self):
        """Test batch-level aggregation from container summaries."""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        # Create mock container summaries
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignment,
            period_start=start_date,
            period_end=end_date,
            total_feed_kg=Decimal('175.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('11.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Aggregate to batch level
        batch_summary = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, start_date, end_date
        )

        self.assertIsNotNone(batch_summary)
        self.assertEqual(batch_summary.batch, self.batch)
        self.assertEqual(batch_summary.total_feed_kg, Decimal('175.0'))
        self.assertEqual(batch_summary.total_growth_kg, Decimal('15.0'))
        self.assertEqual(batch_summary.weighted_avg_fcr, Decimal('11.67'))
        self.assertEqual(batch_summary.container_count, 1)
        self.assertEqual(batch_summary.overall_confidence_level, 'HIGH')
        self.assertEqual(batch_summary.estimation_method, 'MEASURED')
