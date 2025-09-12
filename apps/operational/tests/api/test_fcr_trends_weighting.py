"""
Unit tests for FCR Trends weighted averaging functionality.

Tests the weighted averaging implementation in both FCR service and FCR trends service,
ensuring proper calculation of FCR values weighted by feed consumption or biomass gain.
"""
import json
from datetime import date, timedelta, time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from apps.inventory.models import ContainerFeedingSummary, BatchFeedingSummary
from apps.inventory.services.fcr_service import FCRCalculationService
from apps.batch.models import Batch, BatchContainerAssignment, Species, LifeCycleStage
from apps.infrastructure.models import Container, FreshwaterStation, Area, Geography
from apps.operational.services.fcr_trends_service import FCRTrendsService, AggregationLevel, TimeInterval


User = get_user_model()


class FCRWeightedAveragingTestCase(TestCase):
    """Test weighted averaging logic in FCR service and trends service."""

    def setUp(self):
        """Set up test data for weighted averaging tests."""
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

        # Create multiple containers with different characteristics
        self.containers = []
        self.assignments = []

        for i in range(3):
            container = Container.objects.create(
                name=f"Test Container {i+1}",
                container_type=self.container_type,
                area=self.area,
                volume_m3=50.0,
                max_biomass_kg=1000.0
            )
            self.containers.append(container)

            assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=container,
                lifecycle_stage=self.lifecycle_stage,
                population_count=2500 * (i + 1),  # Different populations
                avg_weight_g=Decimal('150.00'),
                assignment_date=date.today() - timedelta(days=30),
                is_active=True
            )
            self.assignments.append(assignment)

    def test_weighted_averaging_basic_functionality(self):
        """Test basic weighted averaging with different feed amounts."""
        # Create container summaries with different feed amounts and FCR values
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Container 1: High feed, low FCR
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('200.0'),  # High feed
            growth_kg=Decimal('20.0'),
            fcr=Decimal('10.0'),  # Low FCR
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Container 2: Medium feed, high FCR
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[1],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('100.0'),  # Medium feed
            growth_kg=Decimal('15.0'),
            fcr=Decimal('6.67'),  # High FCR
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Container 3: Low feed, medium FCR
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[2],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('50.0'),  # Low feed
            growth_kg=Decimal('10.0'),
            fcr=Decimal('5.0'),  # Medium FCR
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Test weighted averaging
        result = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, period_start, period_end
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.weighted_avg_fcr)

        # Expected weighted FCR calculation:
        # (200 * 10.0) + (100 * 6.67) + (50 * 5.0) = 2000 + 667 + 250 = 2917
        # Total weight = 200 + 100 + 50 = 350
        # Weighted average = 2917 / 350 = 8.334...
        expected_fcr = Decimal('2917') / Decimal('350')
        self.assertAlmostEqual(float(result.weighted_avg_fcr), float(expected_fcr), places=3)

        # Verify container count
        self.assertEqual(result.container_count, 3)

    def test_weighted_averaging_with_zero_feed_containers(self):
        """Test weighted averaging handles zero feed containers correctly."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Container 1: Normal feed
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('100.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('6.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Container 2: Zero feed (should be excluded)
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[1],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('0.0'),
            growth_kg=Decimal('0.0'),
            fcr=Decimal('0.0'),
            confidence_level='LOW',
            estimation_method='MEASURED',
            data_points=0
        )

        # Container 3: Normal feed
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[2],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('50.0'),
            growth_kg=Decimal('10.0'),
            fcr=Decimal('5.0'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Test weighted averaging
        result = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, period_start, period_end
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.weighted_avg_fcr)

        # Expected: Only containers 1 and 3 should contribute
        # (100 * 6.67) + (50 * 5.0) = 667 + 250 = 917
        # Total weight = 100 + 50 = 150
        # Weighted average = 917 / 150 = 6.113...
        expected_fcr = Decimal('917') / Decimal('150')
        self.assertAlmostEqual(float(result.weighted_avg_fcr), float(expected_fcr), places=3)

        # Should still count all containers
        self.assertEqual(result.container_count, 3)

    def test_weighted_averaging_fallback_to_biomass_gain(self):
        """Test fallback to biomass_gain_kg when feed data is unavailable."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Container 1: Has feed data
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('100.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('6.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Container 2: Very low feed data, use biomass gain as fallback
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[1],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('0.001'),  # Very small feed amount to trigger fallback
            growth_kg=Decimal('20.0'),  # Use biomass gain as weight
            fcr=Decimal('5.0'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Test weighted averaging
        result = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, period_start, period_end
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.weighted_avg_fcr)

        # Expected: Container 1 uses feed weight, Container 2 uses biomass gain
        # (100 * 6.67) + (20 * 5.0) = 667 + 100 = 767
        # Total weight = 100 + 20 = 120
        # Weighted average = 767 / 120 = 6.391...
        expected_fcr = Decimal('767') / Decimal('120')
        self.assertAlmostEqual(float(result.weighted_avg_fcr), float(expected_fcr), places=3)

    def test_weighted_averaging_single_container(self):
        """Test weighted averaging with single container."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('100.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('6.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        result = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, period_start, period_end
        )

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.weighted_avg_fcr)
        # Single container should return its own FCR
        self.assertAlmostEqual(float(result.weighted_avg_fcr), 6.67, places=3)
        self.assertEqual(result.container_count, 1)

    def test_weighted_averaging_no_valid_containers(self):
        """Test weighted averaging when no containers have valid data."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Container with zero feed and zero FCR
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('0.0'),
            growth_kg=Decimal('0.0'),
            fcr=Decimal('0.0'),
            confidence_level='LOW',
            estimation_method='MEASURED',
            data_points=0
        )

        result = FCRCalculationService.aggregate_container_fcr_to_batch(
            self.batch, period_start, period_end
        )

        # Should return summary with None FCR
        self.assertIsNotNone(result)
        self.assertIsNone(result.weighted_avg_fcr)
        self.assertEqual(result.container_count, 1)

    def test_geography_level_weighted_averaging(self):
        """Test weighted averaging at geography level in FCR trends service."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Create batch feeding summaries for different batches in the geography
        batch2 = Batch.objects.create(
            batch_number="TEST-002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100)
        )

        # Create container assignment for batch2 in the same geography
        assignment2 = BatchContainerAssignment.objects.create(
            batch=batch2,
            container=self.containers[0],  # Use existing container in the geography
            lifecycle_stage=self.lifecycle_stage,
            population_count=2000,
            avg_weight_g=Decimal('150.00'),
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )

        # Batch 1 summary
        BatchFeedingSummary.objects.create(
            batch=self.batch,
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('200.0'),
            total_biomass_gain_kg=Decimal('25.0'),
            weighted_avg_fcr=Decimal('8.0'),
            container_count=2,
            overall_confidence_level='HIGH',
            estimation_method='MEASURED'
        )

        # Batch 2 summary
        BatchFeedingSummary.objects.create(
            batch=batch2,
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('150.0'),
            total_biomass_gain_kg=Decimal('20.0'),
            weighted_avg_fcr=Decimal('7.5'),
            container_count=1,
            overall_confidence_level='HIGH',
            estimation_method='MEASURED'
        )

        # Test geography-level aggregation
        series = FCRTrendsService._get_geography_aggregated_series(
            period_start, period_end, TimeInterval.WEEKLY, self.geography.id
        )

        self.assertEqual(len(series), 1)
        item = series[0]

        # Expected weighted calculation:
        # (200 * 8.0) + (150 * 7.5) = 1600 + 1125 = 2725
        # Total weight = 200 + 150 = 350
        # Weighted average = 2725 / 350 = 7.785...
        expected_fcr = 2725 / 350
        self.assertAlmostEqual(item['actual_fcr'], expected_fcr, places=3)
        self.assertEqual(item['total_containers'], 3)  # 2 + 1 containers


class FCRWeightedAveragingAPITestCase(APITestCase):
    """API tests for weighted averaging functionality."""

    def setUp(self):
        """Set up test data and authentication."""
        # Create superuser for API access
        self.user = User.objects.create_superuser(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create geography hierarchy (same as above)
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

        # Create containers and assignments
        self.containers = []
        self.assignments = []

        for i in range(2):
            container = Container.objects.create(
                name=f"Test Container {i+1}",
                container_type=self.container_type,
                area=self.area,
                volume_m3=50.0,
                max_biomass_kg=1000.0
            )
            self.containers.append(container)

            assignment = BatchContainerAssignment.objects.create(
                batch=self.batch,
                container=container,
                lifecycle_stage=self.lifecycle_stage,
                population_count=2500,
                avg_weight_g=Decimal('150.00'),
                assignment_date=date.today() - timedelta(days=30),
                is_active=True
            )
            self.assignments.append(assignment)

    def test_api_weighted_averaging_batch_level(self):
        """Test that API returns weighted average FCR at batch level."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Create container summaries with different feed amounts
        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[0],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('150.0'),
            growth_kg=Decimal('20.0'),
            fcr=Decimal('7.5'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignments[1],
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('100.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('6.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Create batch feeding summary (this is what the API will look for)
        BatchFeedingSummary.objects.create(
            batch=self.batch,
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('250.0'),  # 150 + 100
            total_biomass_gain_kg=Decimal('35.0'),  # 20 + 15
            weighted_avg_fcr=Decimal('7.0'),  # (150*7.5 + 100*6.67) / (150+100) = 7.0
            container_count=2,
            overall_confidence_level='HIGH',
            estimation_method='MEASURED'
        )

        # Test API call
        url = reverse('fcr-trends-list')
        params = {
            'batch_id': self.batch.id,
            'start_date': period_start.isoformat(),
            'end_date': period_end.isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['aggregation_level'], 'batch')
        self.assertEqual(len(data['series']), 1)

        series_item = data['series'][0]

        # Expected weighted FCR: (150 * 7.5 + 100 * 6.67) / (150 + 100) = 6.99...
        expected_fcr = (150 * 7.5 + 100 * 6.67) / (150 + 100)
        self.assertAlmostEqual(series_item['actual_fcr'], expected_fcr, places=2)
        self.assertEqual(series_item['container_count'], 2)

    def test_api_weighted_averaging_geography_level(self):
        """Test that API returns weighted average FCR at geography level."""
        period_start = date.today() - timedelta(days=7)
        period_end = date.today()

        # Create batch feeding summaries
        BatchFeedingSummary.objects.create(
            batch=self.batch,
            period_start=period_start,
            period_end=period_end,
            total_feed_kg=Decimal('250.0'),
            total_biomass_gain_kg=Decimal('30.0'),
            weighted_avg_fcr=Decimal('8.33'),
            container_count=2,
            overall_confidence_level='HIGH',
            estimation_method='MEASURED'
        )

        # Test API call
        url = reverse('fcr-trends-list')
        params = {
            'geography_id': self.geography.id,
            'start_date': period_start.isoformat(),
            'end_date': period_end.isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['aggregation_level'], 'geography')
        self.assertEqual(len(data['series']), 1)

        series_item = data['series'][0]
        # Should return the batch's weighted average
        self.assertAlmostEqual(series_item['actual_fcr'], 8.33, places=2)
        self.assertEqual(series_item['total_containers'], 2)
