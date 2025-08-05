"""
Tests for the ContainerType API endpoints.

This module tests CRUD operations for the ContainerType model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.infrastructure.models import ContainerType

def get_response_items(response):
    """Simple replacement for core test utils function."""
    if hasattr(response.data, 'get') and 'results' in response.data:
        return response.data['results']
    return response.data


class ContainerTypeAPITest(APITestCase):
    """Test suite for ContainerType API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate a user for testing
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.admin_user)
        
        # Create a container type
        self.container_type_data = {
            'name': 'Test Container Type',
            'category': 'TANK',
            'max_volume_m3': Decimal('100.00'),
            'description': 'Test container type description'
        }
        self.container_type = ContainerType.objects.create(
            name=self.container_type_data['name'],
            category=self.container_type_data['category'],
            max_volume_m3=self.container_type_data['max_volume_m3'],
            description=self.container_type_data['description']
        )
        
        # Set up URLs for API endpoints
        self.list_url = reverse('infrastructure:container-type-list')
        self.detail_url = reverse(
            'infrastructure:container-type-detail',
            kwargs={'pk': self.container_type.pk}
        )

    def test_list_container_types(self):
        """Test retrieving a list of container types."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_container_type(self):
        """Test creating a new container type."""
        new_container_type_data = {
            'name': 'New Container Type',
            'category': 'PEN',
            'max_volume_m3': '200.50',
            'description': 'New container type description'
        }
        response = self.client.post(self.list_url, new_container_type_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_container_type_data['name'])
        self.assertEqual(response.data['category'], new_container_type_data['category'])
        self.assertEqual(ContainerType.objects.count(), 2)
        
        # Verify the data was saved correctly
        container_type = ContainerType.objects.get(id=response.data['id'])
        self.assertEqual(container_type.description, new_container_type_data['description'])
        self.assertAlmostEqual(float(container_type.max_volume_m3), float(new_container_type_data['max_volume_m3']))

    def test_retrieve_container_type(self):
        """Test retrieving a single container type."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.container_type_data['name'])
        self.assertEqual(response.data['category'], self.container_type_data['category'])
        self.assertAlmostEqual(float(response.data['max_volume_m3']), float(self.container_type_data['max_volume_m3']))
        self.assertEqual(response.data['description'], self.container_type_data['description'])

    def test_update_container_type(self):
        """Test updating a container type."""
        updated_data = {
            'name': 'Updated Container Type',
            'category': 'TRAY',
            'max_volume_m3': '150.75',
            'description': 'Updated container type description'
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.container_type.refresh_from_db()
        self.assertEqual(self.container_type.name, updated_data['name'])
        self.assertEqual(self.container_type.category, updated_data['category'])
        self.assertAlmostEqual(float(self.container_type.max_volume_m3), float(updated_data['max_volume_m3']))
        self.assertEqual(self.container_type.description, updated_data['description'])

    def test_partial_update_container_type(self):
        """Test partially updating a container type."""
        patch_data = {'name': 'Patched Container Type Name'}
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.container_type.refresh_from_db()
        self.assertEqual(self.container_type.name, patch_data['name'])
        # Other fields should remain unchanged
        self.assertEqual(self.container_type.category, self.container_type_data['category'])
        self.assertAlmostEqual(float(self.container_type.max_volume_m3), float(self.container_type_data['max_volume_m3']))

    def test_delete_container_type(self):
        """Test deleting a container type."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ContainerType.objects.count(), 0)

    def test_filter_by_category(self):
        """Test filtering container types by category."""
        # Create container types with different categories
        ContainerType.objects.create(
            name='Pen Container Type',
            category='PEN',
            max_volume_m3=Decimal('300.00'),
            description='Pen container type description'
        )
        
        ContainerType.objects.create(
            name='Tray Container Type',
            category='TRAY',
            max_volume_m3=Decimal('50.00'),
            description='Tray container type description'
        )
        
        # Test filtering by TANK category
        response = self.client.get(f"{self.list_url}?category=TANK")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only TANK container types are returned
        for item in get_response_items(response):
            self.assertEqual(item['category'], 'TANK')
        
        # Test filtering by PEN category
        response = self.client.get(f"{self.list_url}?category=PEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only PEN container types are returned
        for item in get_response_items(response):
            self.assertEqual(item['category'], 'PEN')
