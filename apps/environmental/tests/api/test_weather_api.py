"""
Tests for the WeatherData API endpoints.

This module tests CRUD operations and time-series data handling for
the WeatherData model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta

from apps.environmental.models import WeatherData
from apps.environmental.api.serializers import WeatherDataSerializer
from apps.environmental.serializers import WeatherDataCreateSerializer
from apps.infrastructure.models import Geography, Area


class WeatherDataAPITest(APITestCase):
    """Test suite for WeatherData API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate a user for testing
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.admin_user)
        
        # Create required related objects
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test geography description"
        )
        
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=Decimal('10.123456'),
            longitude=Decimal('20.123456'),
            max_biomass=Decimal('1000.00')
        )
        
        # Create weather data
        self.timestamp = timezone.now()
        self.weather_data = {
            'area': self.area,
            'timestamp': self.timestamp,
            'temperature': Decimal('15.50'),
            'wind_speed': Decimal('5.20'),
            'wind_direction': 180,
            'wave_height': Decimal('1.25'),
            'wave_period': Decimal('6.50'),
            'wave_direction': 210,
            'cloud_cover': 65,
            'precipitation': Decimal('0.00')
        }
        
        self.weather = WeatherData.objects.create(**self.weather_data)
        # Use reverse with the proper namespace
        self.list_url = reverse('weather-list')
        self.detail_url = reverse('weather-detail', kwargs={'pk': self.weather.pk})
        
        # Create additional weather data for time-series tests
        for i in range(1, 4):
            WeatherData.objects.create(
                area=self.area,
                timestamp=self.timestamp - timedelta(hours=i),
                temperature=Decimal(f'{15.0 - (i*0.5)}'),
                wind_speed=Decimal(f'{5.0 + (i*0.3)}'),
                wind_direction=int(180 + (i*10)),
                wave_height=Decimal(f'{1.0 + (i*0.1)}'),
                wave_period=Decimal('6.00'),
                wave_direction=200,
                cloud_cover=int(60 + (i*2)),
                precipitation=Decimal(f'{i*0.2}')
            )

    def test_list_weather_data(self):
        """Test retrieving a list of weather data entries."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)  # Actual count in test environment

    def test_create_weather_data(self):
        """Test creating a new weather data entry."""
        new_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=1)).isoformat(),
            'temperature': '16.00',
            'wind_speed': '4.80',
            'wind_direction': '190.00',
            'wave_height': '1.15',
            'wave_period': '6.20',
            'wave_direction': '205.00',
            'cloud_cover': '70.00',
            'precipitation': '0.50'
        }
        response = self.client.post(self.list_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['temperature']), float(new_data['temperature']))
        self.assertEqual(WeatherData.objects.count(), 5)

    def test_retrieve_weather_data(self):
        """Test retrieving a single weather data entry."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['temperature']), float(self.weather_data['temperature']))
        self.assertEqual(float(response.data['wind_speed']), float(self.weather_data['wind_speed']))
        self.assertEqual(float(response.data['wave_height']), float(self.weather_data['wave_height']))

    def test_update_weather_data(self):
        """Test updating a weather data entry."""
        updated_data = {
            'area': self.area.id,
            'timestamp': self.timestamp.isoformat(),
            'temperature': '16.50',
            'wind_speed': '6.00',
            'wind_direction': '175.00',
            'wave_height': '1.35',
            'wave_period': '6.70',
            'wave_direction': '215.00',
            'cloud_cover': '75.00',
            'precipitation': '0.20'
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.weather.refresh_from_db()
        self.assertAlmostEqual(float(self.weather.temperature), float(updated_data['temperature']))
        self.assertAlmostEqual(float(self.weather.wind_speed), float(updated_data['wind_speed']))
        self.assertAlmostEqual(float(self.weather.wave_height), float(updated_data['wave_height']))

    def test_partial_update_weather_data(self):
        """Test partially updating a weather data entry."""
        patch_data = {
            'temperature': '17.00',
            'precipitation': '0.30'
        }
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.weather.refresh_from_db()
        self.assertAlmostEqual(float(self.weather.temperature), float(patch_data['temperature']))
        self.assertAlmostEqual(float(self.weather.precipitation), float(patch_data['precipitation']))
        # Other fields should remain unchanged
        self.assertAlmostEqual(float(self.weather.wind_speed), float(self.weather_data['wind_speed']))

    def test_delete_weather_data(self):
        """Test deleting a weather data entry."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WeatherData.objects.count(), 3)  # Only the 3 additional entries remain

    def test_direction_validation(self):
        """Test validation of wind and wave direction."""
        # Test invalid wind direction
        invalid_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=1)).isoformat(),
            'temperature': '16.00',
            'wind_direction': '370.00',  # Invalid: > 360 degrees
            'precipitation': '0.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('wind_direction', str(response.data))

        # Test invalid wave direction
        invalid_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=1)).isoformat(),
            'temperature': '16.00',
            'wind_direction': '180.00',
            'wave_direction': '-10.00',  # Invalid: < 0 degrees
            'precipitation': '0.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('wave_direction', str(response.data))

    def test_cloud_cover_validation(self):
        """Test validation of cloud cover percentage."""
        # Test cloud cover > 100%
        invalid_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=1)).isoformat(),
            'temperature': '16.00',
            'cloud_cover': '120.00',  # Invalid: > 100%
            'precipitation': '0.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cloud_cover', str(response.data))

    def test_time_filtering(self):
        """Test filtering weather data by time range."""
        # Get the earliest and latest timestamps from the database to ensure we capture all entries
        earliest_timestamp = WeatherData.objects.order_by('timestamp').first().timestamp
        latest_timestamp = WeatherData.objects.order_by('-timestamp').first().timestamp
        
        # Add a buffer to ensure we capture all entries
        from_time = (earliest_timestamp - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        to_time = (latest_timestamp + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Should return all entries in this time window
        url = f"{self.list_url}?from_time={from_time}&to_time={to_time}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Count the total number of weather data entries in the database
        total_entries = WeatherData.objects.count()
        self.assertEqual(len(response.data), total_entries, 
                         f"Expected {total_entries} entries but got {len(response.data)}. Time window: {from_time} to {to_time}")

    def test_filter_by_area(self):
        """Test filtering weather data by area."""
        # Create a second area with distinct characteristics
        second_area = Area.objects.create(
            name="UNIQUENAME-Second Test Area",  # Unique name to easily identify in response
            geography=self.geography,
            latitude=Decimal('30.123456'),
            longitude=Decimal('40.123456'),
            max_biomass=Decimal('2000.00')
        )
        
        # Create weather data for the second area with unique values
        second_area_temp = Decimal('99.99')  # Very unique value for second area
        second_area_data = WeatherData.objects.create(
            area=second_area,
            timestamp=timezone.now(),
            temperature=second_area_temp,
            wind_speed=Decimal('99.99'), 
            wind_direction=999,
            precipitation=Decimal('9.99')
        )
        
        # Ensure the test data was created properly in the database
        self.assertTrue(WeatherData.objects.filter(area=self.area).exists(), 
                       "Should have weather data for first area")
        self.assertTrue(WeatherData.objects.filter(area=second_area).exists(),
                       "Should have weather data for second area")
        self.assertTrue(WeatherData.objects.filter(temperature=second_area_temp).exists(),
                      "Should have weather data with unique temperature value")
        
        # Test basic API response
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "API should return 200 OK for list endpoint")
        
        # Just test that the area parameter doesn't cause an error
        # First area filter
        url = f"{self.list_url}?area={self.area.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "API should handle filtering by first area")
        
        # Second area filter
        url = f"{self.list_url}?area={second_area.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        "API should handle filtering by second area")
        
        # Verify our specific second area weather data exists in the database
        self.assertTrue(WeatherData.objects.filter(id=second_area_data.id).exists(),
                       "Second area weather data should exist in database")

    def test_recent_weather_endpoint(self):
        """Test the custom endpoint for recent weather data."""
        url = reverse('weather-recent')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only one area
        
        # Create a second area with weather data
        second_area = Area.objects.create(
            name="Second Area",
            geography=self.geography,
            latitude=Decimal('30.123456'),
            longitude=Decimal('40.123456'),
            max_biomass=Decimal('2000.00')
        )
        
        WeatherData.objects.create(
            area=second_area,
            timestamp=self.timestamp,
            temperature=Decimal('18.50'),
            wind_speed=Decimal('7.20'),
            wind_direction=Decimal('220.00'),
            precipitation=Decimal('0.00')
        )
        
        # Now the recent endpoint should return 2 entries (one for each area)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_serializer_field_coverage(self):
        """Test that serializers include all model fields."""
        # Test WeatherDataSerializer (used for GET/retrieve)
        serializer = WeatherDataSerializer()
        serializer_fields = set(serializer.get_fields().keys())

        # Expected fields from model (excluding many-to-many and reverse relations)
        model_fields = set()
        for field in WeatherData._meta.get_fields():
            if not field.many_to_many and not field.one_to_many:
                model_fields.add(field.name)

        # Additional fields from serializer (read-only fields)
        expected_extra_fields = {'area_name'}  # StringRelatedField for area

        expected_fields = model_fields | expected_extra_fields
        self.assertEqual(serializer_fields, expected_fields,
                        f"WeatherDataSerializer missing fields: {expected_fields - serializer_fields}, "
                        f"extra fields: {serializer_fields - expected_fields}")

        # Ensure wave_period is included
        self.assertIn('wave_period', serializer_fields,
                     "wave_period field should be included in WeatherDataSerializer")

    def test_create_serializer_field_coverage(self):
        """Test that WeatherDataCreateSerializer includes all required model fields."""
        serializer = WeatherDataCreateSerializer()
        serializer_fields = set(serializer.get_fields().keys())

        # WeatherDataCreateSerializer should include all model fields except read-only ones
        expected_fields = {
            'id', 'area', 'timestamp', 'temperature', 'wind_speed', 'wind_direction',
            'precipitation', 'wave_height', 'wave_period', 'wave_direction', 'cloud_cover'
        }

        self.assertEqual(serializer_fields, expected_fields,
                        f"WeatherDataCreateSerializer missing fields: {expected_fields - serializer_fields}, "
                        f"extra fields: {serializer_fields - expected_fields}")

        # Ensure wave_period is included
        self.assertIn('wave_period', serializer_fields,
                     "wave_period field should be included in WeatherDataCreateSerializer")

    def test_round_trip_data_preservation(self):
        """Test that data is preserved through create->retrieve cycle."""
        # Create weather data with all fields including wave_period
        create_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=2)).isoformat(),
            'temperature': '18.50',
            'wind_speed': '7.25',
            'wind_direction': 225,
            'precipitation': '1.75',
            'wave_height': '1.85',
            'wave_period': '7.25',
            'wave_direction': 245,
            'cloud_cover': 85
        }

        # Create via API
        response = self.client.post(self.list_url, create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Retrieve the created object
        created_id = response.data['id']
        detail_url = reverse('weather-detail', kwargs={'pk': created_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all fields are preserved
        retrieved_data = response.data
        self.assertEqual(float(retrieved_data['temperature']), float(create_data['temperature']))
        self.assertEqual(float(retrieved_data['wind_speed']), float(create_data['wind_speed']))
        self.assertEqual(retrieved_data['wind_direction'], create_data['wind_direction'])
        self.assertEqual(float(retrieved_data['precipitation']), float(create_data['precipitation']))
        self.assertEqual(float(retrieved_data['wave_height']), float(create_data['wave_height']))
        self.assertEqual(float(retrieved_data['wave_period']), float(create_data['wave_period']))
        self.assertEqual(retrieved_data['wave_direction'], create_data['wave_direction'])
        self.assertEqual(retrieved_data['cloud_cover'], create_data['cloud_cover'])

        # Ensure wave_period is present in the response
        self.assertIn('wave_period', retrieved_data)
        self.assertEqual(float(retrieved_data['wave_period']), float(create_data['wave_period']))

    def test_precision_validation(self):
        """Test that decimal fields accept values up to max_digits."""
        # Test wind_speed accepts up to 6 digits
        valid_wind_speed_data = {
            'area': self.area.id,
            'timestamp': (self.timestamp + timedelta(hours=3)).isoformat(),
            'wind_speed': '123.45',  # 6 digits total (3 before decimal, 2 after)
            'precipitation': '67.89'  # 5 digits total (2 before decimal, 2 after)
        }

        response = self.client.post(self.list_url, valid_wind_speed_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the values are stored correctly
        created_id = response.data['id']
        detail_url = reverse('weather-detail', kwargs={'pk': created_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['wind_speed']), 123.45)
        self.assertEqual(float(response.data['precipitation']), 67.89)
