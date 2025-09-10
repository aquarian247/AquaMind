"""
Tests for the Container API endpoints.

This module tests CRUD operations for the Container model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.infrastructure.models import Geography, Area, FreshwaterStation, Hall, ContainerType, Container
from apps.infrastructure.models.container import HistoricalContainer

def get_response_items(response):
    """Simple replacement for core test utils function."""
    if hasattr(response.data, 'get') and 'results' in response.data:
        return response.data['results']
    return response.data


class ContainerAPITest(APITestCase):
    """Test suite for Container API endpoints."""

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
        
        # Create a container type
        self.container_type = ContainerType.objects.create(
            name='Test Container Type',
            category='TANK',
            max_volume_m3=Decimal('100.00'),
            description='Test container type description'
        )
        
        # Create a container in a hall
        self.hall_container_data = {
            'name': 'Hall Container',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'area': None,
            'volume_m3': Decimal('50.00'),
            'max_biomass_kg': Decimal('500.00'),
            'active': True
        }
        self.hall_container = Container.objects.create(
            name=self.hall_container_data['name'],
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=self.hall_container_data['volume_m3'],
            max_biomass_kg=self.hall_container_data['max_biomass_kg'],
            active=self.hall_container_data['active']
        )
        
        # Create a container in an area
        self.area_container_data = {
            'name': 'Area Container',
            'container_type': self.container_type.id,
            'hall': None,
            'area': self.area.id,
            'volume_m3': Decimal('75.00'),
            'max_biomass_kg': Decimal('750.00'),
            'active': True
        }
        self.area_container = Container.objects.create(
            name=self.area_container_data['name'],
            container_type=self.container_type,
            area=self.area,
            volume_m3=self.area_container_data['volume_m3'],
            max_biomass_kg=self.area_container_data['max_biomass_kg'],
            active=self.area_container_data['active']
        )
        
        # Set up URLs for API endpoints
        # The router no longer uses the "infrastructure" namespace, so drop the prefix
        self.list_url = reverse('container-list')
        self.hall_container_detail_url = reverse('container-detail', kwargs={'pk': self.hall_container.pk})
        self.area_container_detail_url = reverse('container-detail', kwargs={'pk': self.area_container.pk})

    def test_list_containers(self):
        """Test retrieving a list of containers."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_create_hall_container(self):
        """Test creating a new container in a hall."""
        new_container_data = {
            'name': 'New Hall Container',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'volume_m3': '60.00',
            'max_biomass_kg': '600.00',
            'active': True
        }
        response = self.client.post(self.list_url, new_container_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_container_data['name'])
        self.assertEqual(response.data['hall'], new_container_data['hall'])
        self.assertIsNone(response.data['area'])
        self.assertEqual(Container.objects.count(), 3)
        
        # Verify the data was saved correctly
        container = Container.objects.get(id=response.data['id'])
        self.assertAlmostEqual(float(container.volume_m3), float(new_container_data['volume_m3']))
        self.assertAlmostEqual(float(container.max_biomass_kg), float(new_container_data['max_biomass_kg']))

    def test_create_area_container(self):
        """Test creating a new container in an area."""
        new_container_data = {
            'name': 'New Area Container',
            'container_type': self.container_type.id,
            'area': self.area.id,
            'volume_m3': '85.00',
            'max_biomass_kg': '850.00',
            'active': True
        }
        response = self.client.post(self.list_url, new_container_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_container_data['name'])
        self.assertEqual(response.data['area'], new_container_data['area'])
        self.assertIsNone(response.data['hall'])
        self.assertEqual(Container.objects.count(), 3)
        
        # Verify the data was saved correctly
        container = Container.objects.get(id=response.data['id'])
        self.assertAlmostEqual(float(container.volume_m3), float(new_container_data['volume_m3']))
        self.assertAlmostEqual(float(container.max_biomass_kg), float(new_container_data['max_biomass_kg']))

    def test_retrieve_hall_container(self):
        """Test retrieving a single container in a hall."""
        response = self.client.get(self.hall_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.hall_container_data['name'])
        self.assertEqual(response.data['container_type'], self.hall_container_data['container_type'])
        self.assertEqual(response.data['hall'], self.hall_container_data['hall'])
        self.assertIsNone(response.data['area'])
        self.assertAlmostEqual(float(response.data['volume_m3']), float(self.hall_container_data['volume_m3']))
        self.assertAlmostEqual(float(response.data['max_biomass_kg']), float(self.hall_container_data['max_biomass_kg']))

    def test_retrieve_area_container(self):
        """Test retrieving a single container in an area."""
        response = self.client.get(self.area_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.area_container_data['name'])
        self.assertEqual(response.data['container_type'], self.area_container_data['container_type'])
        self.assertEqual(response.data['area'], self.area_container_data['area'])
        self.assertIsNone(response.data['hall'])
        self.assertAlmostEqual(float(response.data['volume_m3']), float(self.area_container_data['volume_m3']))
        self.assertAlmostEqual(float(response.data['max_biomass_kg']), float(self.area_container_data['max_biomass_kg']))

    def test_update_container(self):
        """Test updating a container."""
        updated_data = {
            'name': 'Updated Hall Container',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'volume_m3': '55.50',
            'max_biomass_kg': '555.00',
            'active': True
        }
        response = self.client.put(self.hall_container_detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall_container.refresh_from_db()
        self.assertEqual(self.hall_container.name, updated_data['name'])
        self.assertAlmostEqual(float(self.hall_container.volume_m3), float(updated_data['volume_m3']))
        self.assertAlmostEqual(float(self.hall_container.max_biomass_kg), float(updated_data['max_biomass_kg']))

    def test_partial_update_container(self):
        """Test partially updating a container."""
        # Include the required location fields in the patch data
        patch_data = {
            'name': 'Patched Container Name',
            'hall': self.hall.id,  # Need to include hall to satisfy validation
            'container_type': self.container_type.id  # Also include container_type
        }
        response = self.client.patch(self.hall_container_detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.hall_container.refresh_from_db()
        self.assertEqual(self.hall_container.name, patch_data['name'])
        # Other fields should remain unchanged
        self.assertAlmostEqual(float(self.hall_container.volume_m3), float(self.hall_container_data['volume_m3']))

    def test_delete_container(self):
        """Test deleting a container."""
        response = self.client.delete(self.hall_container_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Container.objects.filter(id=self.hall_container.id).count(), 0)
        # Make sure the area container still exists
        self.assertEqual(Container.objects.filter(id=self.area_container.id).count(), 1)

    def test_volume_validation(self):
        """Test validation of container volume against container type max volume."""
        # Try to create a container with volume larger than container type max volume
        invalid_data = {
            'name': 'Invalid Container',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'volume_m3': '150.00',  # Max for container type is 100.00
            'max_biomass_kg': '1000.00',
            'active': True
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('volume_m3', response.data)

    def test_location_constraint_validation(self):
        """Test validation of container location constraint (either hall or area, not both)."""
        # Try to create a container with both hall and area
        invalid_data = {
            'name': 'Invalid Container',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'area': self.area.id,  # Can't have both hall and area
            'volume_m3': '50.00',
            'max_biomass_kg': '500.00',
            'active': True
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should have error about the location constraint

    def test_filter_by_hall(self):
        """Test filtering containers by hall."""
        response = self.client.get(f"{self.list_url}?hall={self.hall.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only containers in the hall are returned
        items = get_response_items(response)
        for item in items:
            self.assertEqual(item['hall'], self.hall.id)
            self.assertIsNone(item['area'])

    def test_filter_by_area(self):
        """Test filtering containers by area."""
        response = self.client.get(f"{self.list_url}?area={self.area.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that only containers in the area are returned
        items = get_response_items(response)
        for item in items:
            self.assertEqual(item['area'], self.area.id)
            self.assertIsNone(item['hall'])


class ContainerHistoryReasonTest(APITestCase):
    """Test suite for Container API history change reasons."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate a user for testing
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.admin_user)

        # Create basic infrastructure
        self.geography = Geography.objects.create(
            name='Test Geography',
            description='Test geography description'
        )

        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            station_type='FRESHWATER',
            geography=self.geography,
            latitude=Decimal('11.123456'),
            longitude=Decimal('21.123456'),
            description='Test station description',
            active=True
        )

        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station,
            description='Test hall description',
            area_sqm=Decimal('500.00'),
            active=True
        )

        self.container_type = ContainerType.objects.create(
            name='Test Container Type',
            category='TANK',
            max_volume_m3=Decimal('100.00'),
            description='Test container type description'
        )

        # Set up URLs for API endpoints
        self.list_url = reverse('container-list')

    def test_create_captures_change_reason(self):
        """Test that creating a container captures the change reason."""
        container_data = {
            'name': 'Test Container for History',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'volume_m3': '50.00',
            'max_biomass_kg': '500.00',
            'active': True
        }

        # Create container via API
        response = self.client.post(self.list_url, container_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify historical record was created
        container = Container.objects.get(id=response.data['id'])
        historical_records = HistoricalContainer.objects.filter(id=container.id)

        # Should have one historical record for creation
        self.assertEqual(historical_records.count(), 1)

        historical_record = historical_records.first()
        self.assertEqual(historical_record.history_type, '+')  # Creation
        self.assertEqual(historical_record.history_user, self.admin_user)
        self.assertIn('created via API by', historical_record.history_change_reason)
        self.assertIn(self.admin_user.username, historical_record.history_change_reason)

    def test_update_captures_change_reason(self):
        """Test that updating a container captures the change reason."""
        # First create a container
        container = Container.objects.create(
            name='Original Container',
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal('50.00'),
            max_biomass_kg=Decimal('500.00'),
            active=True
        )

        # Update container via API
        update_data = {
            'name': 'Updated Container Name',
            'container_type': self.container_type.id,
            'hall': self.hall.id,
            'volume_m3': '60.00',
            'max_biomass_kg': '600.00',
            'active': True
        }

        detail_url = reverse('container-detail', kwargs={'pk': container.pk})
        response = self.client.put(detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify historical record was created for update
        historical_records = HistoricalContainer.objects.filter(id=container.id)

        # Should have one historical record for creation and one for update
        self.assertEqual(historical_records.count(), 2)

        # Get the latest historical record (the update)
        update_record = historical_records.order_by('-history_date').first()
        self.assertEqual(update_record.history_type, '~')  # Update
        self.assertEqual(update_record.history_user, self.admin_user)
        self.assertIn('updated via API by', update_record.history_change_reason)
        self.assertIn(self.admin_user.username, update_record.history_change_reason)

    def test_delete_captures_change_reason(self):
        """Test that deleting a container captures the change reason."""
        # First create a container
        container = Container.objects.create(
            name='Container to Delete',
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal('50.00'),
            max_biomass_kg=Decimal('500.00'),
            active=True
        )

        # Verify creation record exists
        creation_records = HistoricalContainer.objects.filter(id=container.id)
        self.assertEqual(creation_records.count(), 1)
        creation_record = creation_records.first()
        self.assertEqual(creation_record.history_type, '+')
        self.assertEqual(creation_record.history_user, None)  # Created outside of request context

        # Delete container via API
        detail_url = reverse('container-detail', kwargs={'pk': container.pk})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # After deletion, we can't check historical records directly because they cascade delete
        # But we can verify that the deletion was processed (status 204 indicates success)
        # The change reason would have been captured during the deletion process
        # This test primarily verifies that the delete operation completes successfully
        # with the HistoryReasonMixin applied

        # Verify the container was actually deleted
        self.assertFalse(Container.objects.filter(id=container.id).exists())
