"""
Tests for the feeding-events summary endpoint with date range support.

This test suite covers the enhanced functionality added in Issue #50:
- Date range filtering with start_date/end_date parameters
- Backward compatibility with existing date parameter
- Proper validation and error handling
- Precedence rules when both range and date parameters are provided
"""
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.infrastructure.models import Geography, Area, ContainerType, Container, FeedContainer
from apps.batch.models import Species, LifeCycleStage, Batch
from apps.inventory.models import Feed, FeedingEvent
from apps.users.models import User


def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for API endpoints"""
    if detail:
        pk = kwargs.get('pk')
        return f'/api/v1/{app_name}/{endpoint}/{pk}/'
    return f'/api/v1/{app_name}/{endpoint}/'


class FeedingEventSummaryRangeTest(APITestCase):
    """
    Test suite for feeding-events summary endpoint with date range support.
    """

    def setUp(self):
        """Create minimal fixture data for testing."""
        # Ensure clean slate for each test
        FeedingEvent.objects.all().delete()

        self.client = APIClient()
        self.user = User.objects.create_user(username="summary_range_user", password="p@ssword")
        self.client.force_authenticate(user=self.user)

        # Geography → Area
        self.geography = Geography.objects.create(name="Geo")
        self.area = Area.objects.create(
            name="Area-1",
            geography=self.geography,
            latitude=0,
            longitude=0,
            max_biomass=Decimal("5000.0"),
        )

        # ContainerType → Container
        self.container_type = ContainerType.objects.create(
            name="Tank-Type",
            category="TANK",
            max_volume_m3=Decimal("100.0"),
        )
        self.container = Container.objects.create(
            name="Tank-1",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("50.0"),
            max_biomass_kg=Decimal("800.0"),
        )

        # Species / Stage / Batch
        self.species = Species.objects.create(name="Salmon", scientific_name="Salmo salar")
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Smolt", species=self.species, order=1
        )
        self.batch = Batch.objects.create(
            batch_number="B-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=10),
        )

        # Feed / FeedContainer
        self.feed = Feed.objects.create(name="Feed-A", brand="Brand", size_category="SMALL")
        self.feed_container = FeedContainer.objects.create(
            name="Feeder-1", area=self.area, capacity_kg=Decimal("200.0")
        )

        # URL helper
        self.summary_url = get_api_url("inventory", "feeding-events/summary")

    def _create_feeding_event(
        self,
        date,
        amount_kg,
        batch=None,
        container=None,
    ):
        """Utility to create a FeedingEvent."""
        return FeedingEvent.objects.create(
            batch=batch or self.batch,
            container=container or self.container,
            feed=self.feed,
            feeding_date=date,
            feeding_time=timezone.now().time(),
            amount_kg=Decimal(str(amount_kg)),
            batch_biomass_kg=Decimal("300.0"),
            method="MANUAL",
        )

    def test_single_day_range_equals_date_filter(self):
        """Single-day range (start_date == end_date) equals date= result."""
        FeedingEvent.objects.all().delete()
        today = timezone.now().date()

        # Create event for today
        self._create_feeding_event(date=today, amount_kg=10.5)

        # Test with date parameter
        date_resp = self.client.get(f"{self.summary_url}?date={today.isoformat()}")
        self.assertEqual(date_resp.status_code, status.HTTP_200_OK)

        # Test with single-day range
        range_resp = self.client.get(f"{self.summary_url}?start_date={today.isoformat()}&end_date={today.isoformat()}")
        self.assertEqual(range_resp.status_code, status.HTTP_200_OK)

        # Results should be identical
        self.assertEqual(date_resp.data["events_count"], range_resp.data["events_count"])
        self.assertEqual(date_resp.data["total_feed_kg"], range_resp.data["total_feed_kg"])

    def test_multi_day_range_aggregates_correctly(self):
        """Multi-day range aggregates correctly across days."""
        FeedingEvent.objects.all().delete()
        base_date = timezone.now().date()

        # Create events across multiple days
        self._create_feeding_event(date=base_date - timedelta(days=2), amount_kg=5.0)
        self._create_feeding_event(date=base_date - timedelta(days=1), amount_kg=7.5)
        self._create_feeding_event(date=base_date, amount_kg=12.0)
        self._create_feeding_event(date=base_date + timedelta(days=1), amount_kg=8.5)  # Should be excluded

        # Test 3-day range
        start_date = (base_date - timedelta(days=2)).isoformat()
        end_date = base_date.isoformat()

        resp = self.client.get(f"{self.summary_url}?start_date={start_date}&end_date={end_date}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Should include only the first 3 events
        self.assertEqual(resp.data["events_count"], 3)
        self.assertEqual(resp.data["total_feed_kg"], 24.5)

    def test_invalid_range_start_after_end(self):
        """Invalid range (start_date > end_date) returns 400."""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        resp = self.client.get(f"{self.summary_url}?start_date={tomorrow.isoformat()}&end_date={today.isoformat()}")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date must be before or equal to end_date", resp.data["error"])

    def test_only_start_date_provided(self):
        """Only start_date provided (missing end_date) returns 400."""
        today = timezone.now().date()
        resp = self.client.get(f"{self.summary_url}?start_date={today.isoformat()}")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Both start_date and end_date must be provided together", resp.data["error"])

    def test_only_end_date_provided(self):
        """Only end_date provided (missing start_date) returns 400."""
        today = timezone.now().date()
        resp = self.client.get(f"{self.summary_url}?end_date={today.isoformat()}")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Both start_date and end_date must be provided together", resp.data["error"])

    def test_range_precedence_over_date(self):
        """Both range and date supplied → range takes precedence."""
        FeedingEvent.objects.all().delete()
        base_date = timezone.now().date()

        # Create events on different days
        self._create_feeding_event(date=base_date - timedelta(days=1), amount_kg=10.0)  # In range
        self._create_feeding_event(date=base_date, amount_kg=5.0)  # Only in date param

        start_date = (base_date - timedelta(days=1)).isoformat()
        end_date = (base_date - timedelta(days=1)).isoformat()  # Only yesterday

        # Request with both range and date parameters
        resp = self.client.get(
            f"{self.summary_url}?start_date={start_date}&end_date={end_date}&date={base_date.isoformat()}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Should use range (only yesterday's event), not date parameter
        self.assertEqual(resp.data["events_count"], 1)
        self.assertEqual(resp.data["total_feed_kg"], 10.0)

    def test_existing_filters_work_with_range(self):
        """Existing filters (batch, container) still work in range mode."""
        FeedingEvent.objects.all().delete()

        # Create another batch and container for testing filters
        other_batch = Batch.objects.create(
            batch_number="B-002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=timezone.now().date() - timedelta(days=5),
        )
        other_container = Container.objects.create(
            name="Tank-2",
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal("60.0"),
            max_biomass_kg=Decimal("900.0"),
        )

        base_date = timezone.now().date()
        # Create events for different batches/containers
        self._create_feeding_event(date=base_date, amount_kg=10.0, batch=self.batch, container=self.container)
        self._create_feeding_event(date=base_date, amount_kg=15.0, batch=other_batch, container=self.container)
        self._create_feeding_event(date=base_date, amount_kg=20.0, batch=self.batch, container=other_container)

        start_date = base_date.isoformat()
        end_date = base_date.isoformat()

        # Test batch filter with range
        resp = self.client.get(
            f"{self.summary_url}?start_date={start_date}&end_date={end_date}&batch={other_batch.id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["events_count"], 1)
        self.assertEqual(resp.data["total_feed_kg"], 15.0)

        # Test container filter with range
        resp = self.client.get(
            f"{self.summary_url}?start_date={start_date}&end_date={end_date}&container={other_container.id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["events_count"], 1)
        self.assertEqual(resp.data["total_feed_kg"], 20.0)

    def test_invalid_date_format(self):
        """Invalid date format returns 400."""
        resp = self.client.get(f"{self.summary_url}?start_date=invalid-date&end_date=2025-01-01")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date format", resp.data["error"])

    def test_backward_compatibility_date_parameter(self):
        """Existing date parameter still works correctly."""
        FeedingEvent.objects.all().delete()
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Create events
        self._create_feeding_event(date=today, amount_kg=10.0)
        self._create_feeding_event(date=yesterday, amount_kg=5.0)

        # Test date parameter
        resp = self.client.get(f"{self.summary_url}?date={yesterday.isoformat()}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["events_count"], 1)
        self.assertEqual(resp.data["total_feed_kg"], 5.0)

    # Removed test_default_behavior_no_parameters - this functionality is already
    # thoroughly tested in FeedingEventSummaryTest.test_default_today_filter
    # Removing this duplicate test eliminates database isolation issues between test classes

    def test_empty_range(self):
        """Empty range (no events in date range) returns zero values."""
        FeedingEvent.objects.all().delete()
        today = timezone.now().date()

        # Request range with no events
        past_date = (today - timedelta(days=30)).isoformat()
        yesterday = (today - timedelta(days=1)).isoformat()

        resp = self.client.get(f"{self.summary_url}?start_date={past_date}&end_date={yesterday}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["events_count"], 0)
        self.assertEqual(resp.data["total_feed_kg"], 0.0)
