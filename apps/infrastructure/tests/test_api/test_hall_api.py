"""
Tests for the Hall API endpoints.

This module tests CRUD operations for the Hall model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
def get_response_items(response):
    """Simple replacement for core test utils function."""
    if hasattr(response.data, 'get') and 'results' in response.data:
        return response.data['results']
    return response.data

from apps.infrastructure.models import Geography, FreshwaterStation, Hall


class HallAPITest(APITestCase):
    """Test suite for Hall API endpoints."""

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
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            station_type='FRESHWATER',
            geography=self.geography,
            latitude=Decimal('10.123456'),
            longitude=Decimal('20.123456'),
            description='Test station description',
            active=True
        )
        
        # Create a hall
        self.hall_data = {
            'name': 'Test Hall',
            'freshwater_station': self.station.id,
            'description': 'Test hall description',
            'area_sqm': Decimal('500.00'),
            'active': True
        }
        self.hall = Hall.objects.create(
            name=self.hall_data['name'],
            freshwater_station=self.station,
            description=self.hall_data['description'],
            area_sqm=self.hall_data['area_sqm'],
            active=self.hall_data['active']
        )
        
        # Set up URLs for API endpoints
        self.list_url = reverse('infrastructure:hall-list')
        self.detail_url = reverse('infrastructure:hall-detail', kwargs={'pk': self.hall.pk})

    def test_list_halls(self):
        """Test retrieving a list of halls."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_hall(self):
        """Test creating a new hall."""
        new_hall_data = {
            'name': 'New Hall',
            'freshwater_station': self.station.id,
            'description': 'New hall description',
            'area_sqm': '750.50',
            'active': True
        }
        response = self.client.post(self.list_url, new_hall_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_hall_data['name'])
        self.assertEqual(Hall.objects.count(), 2)
        
        # Verify the data was saved correctly
        hall = Hall.objects.get(id=response.data['id'])
        self.assertEqual(hall.description, new_hall_data['description'])
        self.assertAlmostEqual(float(hall.area_sqm), float(new_hall_data['area_sqm']))

    def test_retrieve_hall(self):
        """Test retrieving a single hall."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.hall_data['name'])
        self.assertEqual(response.data['freshwater_station'], self.hall_data['freshwater_station'])
        self.assertEqual(response.data['description'], self.hall_data['description'])
        self.assertAlmostEqual(float(response.data['area_sqm']), float(self.hall_data['area_sqm']))

    def test_update_hall(self):
        """Test updating a hall."""
        updated_data = {
            'name': 'Updated Hall',
            'freshwater_station': self.station.id,
            'description': 'Updated hall description',
            'area_sqm': '600.75',
            'active': True
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall.refresh_from_db()
        self.assertEqual(self.hall.name, updated_data['name'])
        self.assertEqual(self.hall.description, updated_data['description'])
        self.assertAlmostEqual(float(self.hall.area_sqm), float(updated_data['area_sqm']))

    def test_partial_update_hall(self):
        """Test partially updating a hall."""
        patch_data = {'name': 'Patched Hall Name'}
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall.refresh_from_db()
        self.assertEqual(self.hall.name, patch_data['name'])
        # Other fields should remain unchanged
        self.assertEqual(self.hall.description, self.hall_data['description'])
        self.assertAlmostEqual(float(self.hall.area_sqm), float(self.hall_data['area_sqm']))

    def test_delete_hall(self):
        """Test deleting a hall."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Hall.objects.count(), 0)

    def test_filter_by_station(self):
        """Test filtering halls by freshwater_station."""
        # Create another station
        another_station = FreshwaterStation.objects.create(
            name='Another Station',
            station_type='FRESHWATER',
            geography=self.geography,
            latitude=Decimal('11.123456'),
            longitude=Decimal('21.123456'),
            description='Another station description',
            active=True
        )
        
        # Create a hall in the new station
        Hall.objects.create(
            name='Another Hall',
            freshwater_station=another_station,
            description='Another hall description',
            area_sqm=Decimal('300.00'),
            active=True
        )
        
        # Test filtering by original station
        response = self.client.get(f"{self.list_url}?freshwater_station={self.station.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the halls are filtered by station
        for item in get_response_items(response):
            self.assertEqual(item['freshwater_station'], self.station.id)
        
        # Test filtering by new station
        response = self.client.get(f"{self.list_url}?freshwater_station={another_station.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the halls are filtered by station
        for item in get_response_items(response):
            self.assertEqual(item['freshwater_station'], another_station.id)
