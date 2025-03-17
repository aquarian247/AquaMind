"""
Tests for the FreshwaterStation API endpoints.

This module tests CRUD operations for the FreshwaterStation model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.infrastructure.models import Geography, FreshwaterStation


class FreshwaterStationAPITest(APITestCase):
    """Test suite for FreshwaterStation API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate a user for testing
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.admin_user)
        
        # Create a geography first
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography description'
        )
        
        # Create a freshwater station
        self.station_data = {
            'name': 'Test Station',
            'station_type': 'FRESHWATER',
            'geography': self.geography.id,
            'latitude': Decimal('10.123456'),
            'longitude': Decimal('20.123456'),
            'description': 'Test station description',
            'active': True
        }
        self.station = FreshwaterStation.objects.create(
            name=self.station_data['name'],
            station_type=self.station_data['station_type'],
            geography=self.geography,
            latitude=self.station_data['latitude'],
            longitude=self.station_data['longitude'],
            description=self.station_data['description'],
            active=self.station_data['active']
        )
        
        # Set up URLs for API endpoints
        self.list_url = reverse('infrastructure:freshwaterstation-list')
        self.detail_url = reverse('infrastructure:freshwaterstation-detail', kwargs={'pk': self.station.pk})

    def test_list_stations(self):
        """Test retrieving a list of freshwater stations."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_station(self):
        """Test creating a new freshwater station."""
        new_station_data = {
            'name': 'New Station',
            'station_type': 'BROODSTOCK',
            'geography': self.geography.id,
            'latitude': '15.654321',
            'longitude': '25.654321',
            'description': 'New station description',
            'active': True
        }
        response = self.client.post(self.list_url, new_station_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_station_data['name'])
        self.assertEqual(response.data['station_type'], new_station_data['station_type'])
        self.assertEqual(FreshwaterStation.objects.count(), 2)
        
        # Verify the data was saved correctly
        station = FreshwaterStation.objects.get(id=response.data['id'])
        self.assertAlmostEqual(float(station.latitude), float(new_station_data['latitude']))
        self.assertAlmostEqual(float(station.longitude), float(new_station_data['longitude']))
        self.assertEqual(station.description, new_station_data['description'])

    def test_retrieve_station(self):
        """Test retrieving a single freshwater station."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.station_data['name'])
        self.assertEqual(response.data['station_type'], self.station_data['station_type'])
        self.assertEqual(response.data['geography'], self.station_data['geography'])
        self.assertAlmostEqual(float(response.data['latitude']), float(self.station_data['latitude']))
        self.assertAlmostEqual(float(response.data['longitude']), float(self.station_data['longitude']))

    def test_update_station(self):
        """Test updating a freshwater station."""
        updated_data = {
            'name': 'Updated Station',
            'station_type': 'BROODSTOCK',
            'geography': self.geography.id,
            'latitude': '12.345678',
            'longitude': '23.456789',
            'description': 'Updated description',
            'active': True
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, updated_data['name'])
        self.assertEqual(self.station.station_type, updated_data['station_type'])
        self.assertAlmostEqual(float(self.station.latitude), float(updated_data['latitude']))
        self.assertAlmostEqual(float(self.station.longitude), float(updated_data['longitude']))
        self.assertEqual(self.station.description, updated_data['description'])

    def test_partial_update_station(self):
        """Test partially updating a freshwater station."""
        patch_data = {'name': 'Patched Station Name'}
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, patch_data['name'])
        # Other fields should remain unchanged
        self.assertEqual(self.station.station_type, self.station_data['station_type'])
        self.assertAlmostEqual(float(self.station.latitude), float(self.station_data['latitude']))

    def test_delete_station(self):
        """Test deleting a freshwater station."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FreshwaterStation.objects.count(), 0)

    def test_latitude_longitude_validation(self):
        """Test validation of latitude and longitude."""
        # Test invalid latitude (out of range)
        invalid_data = {
            'name': 'Invalid Station',
            'station_type': 'FRESHWATER',
            'geography': self.geography.id,
            'latitude': '100.0',  # Invalid: > 90
            'longitude': '20.0',
            'description': 'Test station description'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)

        # Test invalid longitude (out of range)
        invalid_data = {
            'name': 'Invalid Station',
            'station_type': 'FRESHWATER',
            'geography': self.geography.id,
            'latitude': '10.0',
            'longitude': '200.0',  # Invalid: > 180
            'description': 'Test station description'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('longitude', response.data)

    def test_filter_by_station_type(self):
        """Test filtering stations by station_type."""
        # Create a broodstock station
        FreshwaterStation.objects.create(
            name='Broodstock Station',
            station_type='BROODSTOCK',
            geography=self.geography,
            latitude=Decimal('30.123456'),
            longitude=Decimal('40.123456'),
            description='Broodstock station description',
            active=True
        )
        
        # Test filtering by freshwater
        response = self.client.get(f"{self.list_url}?station_type=FRESHWATER")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that only freshwater stations are returned
        for item in response.data['results']:
            self.assertEqual(item['station_type'], 'FRESHWATER')
        
        # Test filtering by broodstock
        response = self.client.get(f"{self.list_url}?station_type=BROODSTOCK")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that only broodstock stations are returned
        for item in response.data['results']:
            self.assertEqual(item['station_type'], 'BROODSTOCK')
