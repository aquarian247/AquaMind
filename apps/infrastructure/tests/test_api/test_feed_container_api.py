"""
Tests for the FeedContainer API endpoints.

This module tests CRUD operations for the FeedContainer model through the API.
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

from apps.infrastructure.models import (
    Geography, Area, FreshwaterStation, Hall, FeedContainer
)


class FeedContainerAPITest(APITestCase):
    """Test suite for FeedContainer API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate a user for testing
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.admin_user)
        
        # Create a geography
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography description'
        )
        
        # Create an area
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=Decimal('10.123456'),
            longitude=Decimal('20.123456'),
            max_biomass=Decimal('1000.00'),
            active=True
        )
        
        # Create a freshwater station
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            station_type='FRESHWATER',
            geography=self.geography,
            latitude=Decimal('11.123456'),
            longitude=Decimal('21.123456'),
            description='Test station description',
            active=True
        )
        
        # Create a hall
        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station,
            description='Test hall description',
            area_sqm=Decimal('500.00'),
            active=True
        )
        
        # Create a feed container in a hall
        self.hall_feed_container_data = {
            'name': 'Hall Feed Container',
            'container_type': 'SILO',
            'hall': self.hall.id,
            'area': None,
            'capacity_kg': Decimal('5000.00'),
            'active': True
        }
        self.hall_feed_container = FeedContainer.objects.create(
            name=self.hall_feed_container_data['name'],
            container_type=self.hall_feed_container_data['container_type'],
            hall=self.hall,
            capacity_kg=self.hall_feed_container_data['capacity_kg'],
            active=self.hall_feed_container_data['active']
        )
        
        # Create a feed container in an area
        self.area_feed_container_data = {
            'name': 'Area Feed Container',
            'container_type': 'BARGE',
            'hall': None,
            'area': self.area.id,
            'capacity_kg': Decimal('10000.00'),
            'active': True
        }
        self.area_feed_container = FeedContainer.objects.create(
            name=self.area_feed_container_data['name'],
            container_type=self.area_feed_container_data['container_type'],
            area=self.area,
            capacity_kg=self.area_feed_container_data['capacity_kg'],
            active=self.area_feed_container_data['active']
        )
        
        # Set up URLs for API endpoints
        self.list_url = reverse('feed-container-list')
        self.hall_container_detail_url = reverse(
            'infrastructure:feed-container-detail',
            kwargs={'pk': self.hall_feed_container.pk}
        )
        self.area_container_detail_url = reverse(
            'infrastructure:feed-container-detail',
            kwargs={'pk': self.area_feed_container.pk}
        )

    def test_list_feed_containers(self):
        """Test retrieving a list of feed containers."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_create_hall_feed_container(self):
        """Test creating a new feed container in a hall."""
        new_container_data = {
            'name': 'New Hall Feed Container',
            'container_type': 'TANK',
            'hall': self.hall.id,
            'capacity_kg': '6000.00',
            'active': True
        }
        response = self.client.post(self.list_url, new_container_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_container_data['name'])
        self.assertEqual(response.data['container_type'], new_container_data['container_type'])
        self.assertEqual(response.data['hall'], new_container_data['hall'])
        self.assertIsNone(response.data['area'])
        self.assertEqual(FeedContainer.objects.count(), 3)
        
        # Verify the data was saved correctly
        container = FeedContainer.objects.get(id=response.data['id'])
        self.assertAlmostEqual(float(container.capacity_kg), float(new_container_data['capacity_kg']))

    def test_create_area_feed_container(self):
        """Test creating a new feed container in an area."""
        new_container_data = {
            'name': 'New Area Feed Container',
            'container_type': 'SILO',
            'area': self.area.id,
            'capacity_kg': '12000.00',
            'active': True
        }
        response = self.client.post(self.list_url, new_container_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_container_data['name'])
        self.assertEqual(response.data['container_type'], new_container_data['container_type'])
        self.assertEqual(response.data['area'], new_container_data['area'])
        self.assertIsNone(response.data['hall'])
        self.assertEqual(FeedContainer.objects.count(), 3)
        
        # Verify the data was saved correctly
        container = FeedContainer.objects.get(id=response.data['id'])
        self.assertAlmostEqual(float(container.capacity_kg), float(new_container_data['capacity_kg']))

    def test_retrieve_hall_feed_container(self):
        """Test retrieving a single feed container in a hall."""
        response = self.client.get(self.hall_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.hall_feed_container_data['name'])
        self.assertEqual(response.data['container_type'], self.hall_feed_container_data['container_type'])
        self.assertEqual(response.data['hall'], self.hall_feed_container_data['hall'])
        self.assertIsNone(response.data['area'])
        self.assertAlmostEqual(float(response.data['capacity_kg']), float(self.hall_feed_container_data['capacity_kg']))

    def test_retrieve_area_feed_container(self):
        """Test retrieving a single feed container in an area."""
        response = self.client.get(self.area_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.area_feed_container_data['name'])
        self.assertEqual(response.data['container_type'], self.area_feed_container_data['container_type'])
        self.assertEqual(response.data['area'], self.area_feed_container_data['area'])
        self.assertIsNone(response.data['hall'])
        self.assertAlmostEqual(float(response.data['capacity_kg']), float(self.area_feed_container_data['capacity_kg']))

    def test_update_feed_container(self):
        """Test updating a feed container."""
        updated_data = {
            'name': 'Updated Hall Feed Container',
            'container_type': 'TANK',
            'hall': self.hall.id,
            'capacity_kg': '5500.00',
            'active': True
        }
        response = self.client.put(self.hall_container_detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall_feed_container.refresh_from_db()
        self.assertEqual(self.hall_feed_container.name, updated_data['name'])
        self.assertEqual(self.hall_feed_container.container_type, updated_data['container_type'])
        self.assertAlmostEqual(float(self.hall_feed_container.capacity_kg), float(updated_data['capacity_kg']))

    def test_partial_update_feed_container(self):
        """Test partially updating a feed container."""
        # Include the required location fields in the patch data
        patch_data = {
            'name': 'Patched Feed Container Name',
            'hall': self.hall.id,  # Need to include hall to satisfy validation
            'container_type': self.hall_feed_container_data['container_type']  # Also include container_type
        }
        response = self.client.patch(self.hall_container_detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall_feed_container.refresh_from_db()
        self.assertEqual(self.hall_feed_container.name, patch_data['name'])
        # Other fields should remain unchanged
        self.assertEqual(self.hall_feed_container.container_type, self.hall_feed_container_data['container_type'])
        self.assertAlmostEqual(float(self.hall_feed_container.capacity_kg), float(self.hall_feed_container_data['capacity_kg']))

    def test_delete_feed_container(self):
        """Test deleting a feed container."""
        response = self.client.delete(self.hall_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FeedContainer.objects.filter(id=self.hall_feed_container.id).count(), 0)
        # Make sure the area container still exists
        self.assertEqual(FeedContainer.objects.filter(id=self.area_feed_container.id).count(), 1)

    def test_location_constraint_validation(self):
        """Test validation of feed container location constraint (either hall or area, not both)."""
        # Try to create a feed container with both hall and area
        invalid_data = {
            'name': 'Invalid Feed Container',
            'container_type': 'SILO',
            'hall': self.hall.id,
            'area': self.area.id,  # Can't have both hall and area
            'capacity_kg': '5000.00',
            'active': True
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should have error about the location constraint

    def test_filter_by_container_type(self):
        """Test filtering feed containers by container_type."""
        # Test filtering by SILO
        response = self.client.get(f"{self.list_url}?container_type=SILO")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only SILO feed containers are returned
        for item in get_response_items(response):
            self.assertEqual(item['container_type'], 'SILO')
        
        # Test filtering by BARGE
        response = self.client.get(f"{self.list_url}?container_type=BARGE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only BARGE feed containers are returned
        for item in get_response_items(response):
            self.assertEqual(item['container_type'], 'BARGE')

    def test_filter_by_hall(self):
        """Test filtering feed containers by hall."""
        response = self.client.get(f"{self.list_url}?hall={self.hall.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only feed containers in the hall are returned
        for item in get_response_items(response):
            self.assertEqual(item['hall'], self.hall.id)
            self.assertIsNone(item['area'])

    def test_filter_by_area(self):
        """Test filtering feed containers by area."""
        response = self.client.get(f"{self.list_url}?area={self.area.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only feed containers in the area are returned
        for item in get_response_items(response):
            self.assertEqual(item['area'], self.area.id)
            self.assertIsNone(item['hall'])
