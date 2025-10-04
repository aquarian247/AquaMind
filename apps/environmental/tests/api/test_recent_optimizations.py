"""
Tests for optimized 'recent' action endpoints.

Verifies that the optimized queries return correct data and maintain
proper ordering without N+1 query issues.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from apps.environmental.models import (
    EnvironmentalParameter, EnvironmentalReading, WeatherData
)
from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, Container, ContainerType
)

User = get_user_model()


class EnvironmentalReadingRecentOptimizationTestCase(TestCase):
    """Test optimized recent endpoint for environmental readings."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create infrastructure
        from decimal import Decimal
        
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=Decimal('10.123456'),
            longitude=Decimal('20.123456')
        )
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station
        )
        self.container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal('100.00'),
            description="Tank type"
        )
        self.container1 = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=100.0,
            max_biomass_kg=500.0
        )
        self.container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=100.0,
            max_biomass_kg=500.0
        )

        # Create parameters
        self.temp_param = EnvironmentalParameter.objects.create(
            name="Temperature",
            unit="°C",
            description="Water temperature"
        )
        self.oxygen_param = EnvironmentalParameter.objects.create(
            name="Dissolved Oxygen",
            unit="mg/L",
            description="Oxygen level"
        )

        # Create readings with different timestamps
        now = timezone.now()
        
        # Container 1, Temperature - multiple readings
        EnvironmentalReading.objects.create(
            parameter=self.temp_param,
            container=self.container1,
            reading_time=now - timedelta(hours=3),
            value=10.0
        )
        EnvironmentalReading.objects.create(
            parameter=self.temp_param,
            container=self.container1,
            reading_time=now - timedelta(hours=1),
            value=12.0
        )

        # Container 1, Oxygen
        EnvironmentalReading.objects.create(
            parameter=self.oxygen_param,
            container=self.container1,
            reading_time=now - timedelta(hours=2),
            value=8.5
        )
        EnvironmentalReading.objects.create(
            parameter=self.oxygen_param,
            container=self.container1,
            reading_time=now,
            value=9.0
        )

        # Container 2, Temperature
        EnvironmentalReading.objects.create(
            parameter=self.temp_param,
            container=self.container2,
            reading_time=now - timedelta(hours=2),
            value=11.0
        )
        EnvironmentalReading.objects.create(
            parameter=self.temp_param,
            container=self.container2,
            reading_time=now - timedelta(minutes=30),
            value=11.5
        )

    def test_recent_returns_one_per_combination(self):
        """Test that recent returns one reading per param-container combo."""
        url = '/api/v1/environmental/readings/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 3 readings: (temp, container1),
        # (oxygen, container1), (temp, container2)
        self.assertEqual(len(response.data), 3)

    def test_recent_returns_most_recent_values(self):
        """Test that recent returns the actual most recent values."""
        url = '/api/v1/environmental/readings/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find the temperature reading for container1
        temp_c1 = [
            r for r in response.data
            if r['parameter'] == self.temp_param.id
            and r['container'] == self.container1.id
        ][0]

        # Should be 12.0 (most recent), not 10.0
        self.assertEqual(float(temp_c1['value']), 12.0)

        # Find oxygen reading for container1
        oxy_c1 = [
            r for r in response.data
            if r['parameter'] == self.oxygen_param.id
            and r['container'] == self.container1.id
        ][0]

        # Should be 9.0 (most recent), not 8.5
        self.assertEqual(float(oxy_c1['value']), 9.0)

    def test_recent_includes_all_fields(self):
        """Test that recent includes all serialized fields."""
        url = '/api/v1/environmental/readings/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

        # Check first reading has expected fields
        first = response.data[0]
        expected_fields = [
            'id', 'parameter', 'container',
            'reading_time', 'value', 'notes'
        ]
        for field in expected_fields:
            self.assertIn(field, first)

    def test_recent_with_no_readings(self):
        """Test recent endpoint when no readings exist."""
        # Delete all readings
        EnvironmentalReading.objects.all().delete()

        url = '/api/v1/environmental/readings/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_recent_performance_single_query(self):
        """Test that recent uses minimal queries (no N+1)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = '/api/v1/environmental/readings/recent/'

        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should use minimal queries:
        # PostgreSQL: 1-3 queries (DISTINCT ON optimization)
        # SQLite: 8-12 queries (fallback with select_related per combo)
        # N+1 without optimization would be 20+ queries
        num_queries = len(context.captured_queries)

        # Allow reasonable threshold based on database
        # SQLite fallback uses more queries but still avoids N+1
        max_queries = 15 if connection.vendor == 'sqlite' else 10
        self.assertLess(
            num_queries, max_queries,
            f"Too many queries ({num_queries}). Possible N+1 issue."
        )


class WeatherDataRecentOptimizationTestCase(TestCase):
    """Test optimized recent endpoint for weather data."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create areas
        from decimal import Decimal
        
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        self.area1 = Area.objects.create(
            name="Area 1",
            geography=self.geography,
            latitude=Decimal('10.123456'),
            longitude=Decimal('20.123456'),
            max_biomass=Decimal('10000.00')
        )
        self.area2 = Area.objects.create(
            name="Area 2",
            geography=self.geography,
            latitude=Decimal('11.123456'),
            longitude=Decimal('21.123456'),
            max_biomass=Decimal('10000.00')
        )

        # Create weather data with different timestamps
        now = timezone.now()

        # Area 1 - multiple entries
        WeatherData.objects.create(
            area=self.area1,
            timestamp=now - timedelta(hours=2),
            temperature=Decimal('15.0')
        )
        WeatherData.objects.create(
            area=self.area1,
            timestamp=now,  # Most recent for area 1
            temperature=Decimal('16.0')
        )

        # Area 2
        WeatherData.objects.create(
            area=self.area2,
            timestamp=now - timedelta(hours=1),
            temperature=Decimal('14.0')
        )
        WeatherData.objects.create(
            area=self.area2,
            timestamp=now - timedelta(minutes=30),  # Most recent
            temperature=Decimal('14.5')
        )

    def test_recent_returns_one_per_area(self):
        """Test that recent returns one weather record per area."""
        url = '/api/v1/environmental/weather/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have 2 weather records (one per area)
        self.assertEqual(len(response.data), 2)

    def test_recent_returns_most_recent_values(self):
        """Test that recent returns the actual most recent values."""
        url = '/api/v1/environmental/weather/recent/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find area1's weather
        area1_weather = [
            w for w in response.data
            if w['area'] == self.area1.id
        ][0]

        # Should be 16.0 (most recent), not 15.0
        self.assertEqual(float(area1_weather['temperature']), 16.0)

        # Find area2's weather
        area2_weather = [
            w for w in response.data
            if w['area'] == self.area2.id
        ][0]

        # Should be 14.5 (most recent), not 14.0
        self.assertEqual(float(area2_weather['temperature']), 14.5)

    def test_recent_performance_single_query(self):
        """Test that recent uses minimal queries (no N+1)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = '/api/v1/environmental/weather/recent/'

        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should use minimal queries
        # PostgreSQL: 1-3 queries (DISTINCT ON optimization)
        # SQLite: 5-8 queries (fallback with select_related per area)
        num_queries = len(context.captured_queries)

        # Allow reasonable threshold based on database
        max_queries = 12 if connection.vendor == 'sqlite' else 10
        self.assertLess(
            num_queries, max_queries,
            f"Too many queries ({num_queries}). Possible N+1 issue."
        )
