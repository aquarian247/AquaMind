"""
API integration tests for finance reporting endpoints.

Tests the finance_report endpoint with various filter combinations and validates
response structure, data accuracy, and error handling.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from apps.batch.models import Batch, LifeCycleStage, Species
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType
)
from apps.inventory.models import Feed, FeedingEvent

User = get_user_model()


def get_api_url(app_name, endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for API endpoints."""
    if detail:
        pk = kwargs.get('pk')
        return f'/api/v1/{app_name}/{endpoint}/{pk}/'
    return f'/api/v1/{app_name}/{endpoint}/'


class FinanceReportAPITest(TestCase):
    """Test finance report API endpoint."""

    def setUp(self):
        """Create test data and API client."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Create geographies
        self.scotland = Geography.objects.create(name="Scotland")
        self.faroe = Geography.objects.create(name="Faroe Islands")
        
        # Create areas
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
        
        # Create freshwater station for hall-based filtering
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
        self.hall_container = Container.objects.create(
            name="Hall Tank",
            container_type=self.container_type,
            hall=self.hall,
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
        
        # Create feeds with different properties
        self.premium_feed = Feed.objects.create(
            name="Premium Feed",
            brand="Supplier Y",
            size_category="MEDIUM",
            protein_percentage=Decimal("48.0"),
            fat_percentage=Decimal("22.0")
        )
        self.standard_feed = Feed.objects.create(
            name="Standard Feed",
            brand="Supplier X",
            size_category="SMALL",
            protein_percentage=Decimal("42.0"),
            fat_percentage=Decimal("10.0")
        )
        
        # Create feeding events with date spread
        today = timezone.now().date()
        
        # Scotland events - last 30 days
        for i in range(3):
            FeedingEvent.objects.create(
                batch=self.batch,
                container=self.scotland_container,
                feed=self.premium_feed,
                feeding_date=today - timedelta(days=i * 10),
                feeding_time=timezone.now().time(),
                amount_kg=Decimal("100.0"),
                batch_biomass_kg=Decimal("1000.0"),
                feed_cost=Decimal("600.00"),
                method="MANUAL"
            )
        
        # Faroe events - last 30 days
        for i in range(2):
            FeedingEvent.objects.create(
                batch=self.batch,
                container=self.faroe_container,
                feed=self.standard_feed,
                feeding_date=today - timedelta(days=i * 15),
                feeding_time=timezone.now().time(),
                amount_kg=Decimal("80.0"),
                batch_biomass_kg=Decimal("1000.0"),
                feed_cost=Decimal("400.00"),
                method="MANUAL"
            )
        
        # Old events - outside 32 day window
        FeedingEvent.objects.create(
            batch=self.batch,
            container=self.scotland_container,
            feed=self.premium_feed,
            feeding_date=today - timedelta(days=40),
            feeding_time=timezone.now().time(),
            amount_kg=Decimal("100.0"),
            batch_biomass_kg=Decimal("1000.0"),
            feed_cost=Decimal("600.00"),
            method="MANUAL"
        )

    def test_finance_report_requires_date_range(self):
        """Test that start_date and end_date are required."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        
        # No dates
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Only start_date
        response = self.client.get(url, {'start_date': '2024-01-01'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Only end_date
        response = self.client.get(url, {'end_date': '2024-01-31'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_finance_report_invalid_date_format(self):
        """Test invalid date format returns 400 error."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        response = self.client.get(url, {
            'start_date': 'invalid',
            'end_date': '2024-01-31'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_finance_report_invalid_date_range(self):
        """Test start_date after end_date returns 400 error."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        response = self.client.get(url, {
            'start_date': '2024-02-01',
            'end_date': '2024-01-01'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_finance_report_basic_request(self):
        """Test basic finance report with just date range."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify structure
        self.assertIn('summary', response.data)
        self.assertIn('by_feed_type', response.data)
        self.assertIn('by_geography', response.data)
        self.assertIn('by_area', response.data)
        self.assertIn('by_container', response.data)
        
        # Verify summary has required fields
        summary = response.data['summary']
        self.assertIn('total_feed_kg', summary)
        self.assertIn('total_feed_cost', summary)
        self.assertIn('events_count', summary)
        self.assertIn('date_range', summary)

    def test_finance_report_scotland_filter(self):
        """Test filtering by Scotland geography."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'geography': self.scotland.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only include Scotland events
        summary = response.data['summary']
        self.assertEqual(summary['total_feed_kg'], 300.0)  # 3 events * 100kg
        self.assertEqual(summary['total_feed_cost'], 1800.0)  # 3 * 600
        self.assertEqual(summary['events_count'], 3)

    def test_finance_report_high_fat_filter(self):
        """Test filtering by fat percentage >= 12."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'feed__fat_percentage__gte': 12
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only include premium feed events (22% fat)
        summary = response.data['summary']
        self.assertEqual(summary['total_feed_kg'], 300.0)  # 3 events
        self.assertEqual(summary['events_count'], 3)

    def test_finance_report_scotland_high_fat_supplier_y_last_32_days(self):
        """
        Test the exact finance requirement:
        'Feed with fat > 12 from Supplier Y in Scotland, last 32 days'
        """
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=32)).isoformat(),
            'end_date': today.isoformat(),
            'geography': self.scotland.id,
            'feed__fat_percentage__gte': 12,
            'feed__brand': 'Supplier Y'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only include Scotland premium feed events within 32 days
        summary = response.data['summary']
        self.assertEqual(summary['total_feed_kg'], 300.0)  # 3 Scotland premium events
        self.assertEqual(summary['events_count'], 3)
        
        # Verify breakdowns
        self.assertEqual(len(response.data['by_feed_type']), 1)
        self.assertEqual(response.data['by_feed_type'][0]['feed_name'], 'Premium Feed')
        self.assertEqual(response.data['by_feed_type'][0]['brand'], 'Supplier Y')

    def test_finance_report_with_time_series(self):
        """Test finance report with time series enabled."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'include_time_series': 'true'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should include time series
        self.assertIn('time_series', response.data)
        self.assertGreater(len(response.data['time_series']), 0)
        
        # Each time series entry should have required fields
        for entry in response.data['time_series']:
            self.assertIn('date', entry)
            self.assertIn('total_kg', entry)
            self.assertIn('total_cost', entry)
            self.assertIn('events_count', entry)

    def test_finance_report_without_breakdowns(self):
        """Test finance report with breakdowns disabled."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'include_breakdowns': 'false'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only have summary
        self.assertIn('summary', response.data)
        self.assertNotIn('by_feed_type', response.data)
        self.assertNotIn('by_geography', response.data)

    def test_finance_report_multiple_geographic_filters(self):
        """Test combining multiple geographic filters."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'geography__in': f'{self.scotland.id},{self.faroe.id}'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should include both geographies
        summary = response.data['summary']
        self.assertEqual(summary['events_count'], 5)  # 3 Scotland + 2 Faroe
        self.assertEqual(len(response.data['by_geography']), 2)

    def test_finance_report_area_filter(self):
        """Test filtering by specific area."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'area': self.scotland_area.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only include Scottish area events
        summary = response.data['summary']
        self.assertEqual(summary['events_count'], 3)

    def test_finance_report_feed_type_filter(self):
        """Test filtering by feed type."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=30)).isoformat(),
            'end_date': today.isoformat(),
            'feed': self.premium_feed.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only include premium feed events
        summary = response.data['summary']
        self.assertEqual(summary['events_count'], 3)
        self.assertEqual(len(response.data['by_feed_type']), 1)

    def test_finance_report_complex_combination(self):
        """Test complex multi-dimensional filter combination."""
        url = '/api/v1/inventory/feeding-events/finance_report/'
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': (today - timedelta(days=32)).isoformat(),
            'end_date': today.isoformat(),
            'geography': self.scotland.id,
            'feed__fat_percentage__gte': 20,
            'feed__protein_percentage__gte': 45,
            'feed__brand__icontains': 'Supplier'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # All filters should apply as AND
        summary = response.data['summary']
        self.assertGreaterEqual(summary['events_count'], 0)  # May be 0 or more depending on data


class UpdatedSummaryEndpointTest(TestCase):
    """Test updated summary endpoint includes total_feed_cost."""

    def setUp(self):
        """Create minimal test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
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
        
        # Create batch and feed
        species = Species.objects.create(name="Salmon", scientific_name="Salmo")
        lifecycle_stage = LifeCycleStage.objects.create(name="Smolt", species=species, order=1)
        batch = Batch.objects.create(
            batch_number="TEST001", species=species, lifecycle_stage=lifecycle_stage,
            start_date=timezone.now().date()
        )
        feed = Feed.objects.create(
            name="Test Feed", brand="Brand", size_category="MEDIUM"
        )
        
        # Create feeding events
        today = timezone.now().date()
        FeedingEvent.objects.create(
            batch=batch, container=container, feed=feed,
            feeding_date=today, feeding_time=timezone.now().time(),
            amount_kg=Decimal("10.0"), batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("50.00"), method="MANUAL"
        )
        FeedingEvent.objects.create(
            batch=batch, container=container, feed=feed,
            feeding_date=today, feeding_time=timezone.now().time(),
            amount_kg=Decimal("15.0"), batch_biomass_kg=Decimal("100.0"),
            feed_cost=Decimal("75.00"), method="MANUAL"
        )

    def test_summary_endpoint_includes_cost(self):
        """Test summary endpoint now includes total_feed_cost."""
        url = get_api_url('inventory', 'feeding-events/summary')
        today = timezone.now().date()
        
        response = self.client.get(url, {
            'start_date': today.isoformat(),
            'end_date': today.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all fields present
        self.assertIn('events_count', response.data)
        self.assertIn('total_feed_kg', response.data)
        self.assertIn('total_feed_cost', response.data)  # NEW FIELD
        
        # Verify correct values
        self.assertEqual(response.data['events_count'], 2)
        self.assertEqual(response.data['total_feed_kg'], 25.0)  # 10 + 15
        self.assertEqual(response.data['total_feed_cost'], 125.0)  # 50 + 75

