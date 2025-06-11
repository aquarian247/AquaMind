"""
Tests for the Sensor API endpoints.

This module tests CRUD operations for the Sensor model through the API.
"""
from decimal import Decimal
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
def get_response_items(response):
    """Simple replacement for core test utils function."""
    if hasattr(response.data, 'get') and 'results' in response.data:
        return response.data['results']
    return response.data

from apps.infrastructure.models import Geography, Area, ContainerType, Container, Sensor


class SensorAPITest(APITestCase):
    """Test suite for Sensor API endpoints."""

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
        
        # Create a container type
        self.container_type = ContainerType.objects.create(
            name='Test Container Type',
            category='PEN',
            max_volume_m3=Decimal('1000.00'),
            description='Test container type description'
        )
        
        # Create a container
        self.container = Container.objects.create(
            name='Test Container',
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('500.00'),
            max_biomass_kg=Decimal('5000.00'),
            active=True
        )
        
        # Create a sensor
        self.installation_date = date(2023, 1, 1)
        self.calibration_date = date(2023, 6, 1)
        
        self.sensor_data = {
            'name': 'Test Sensor',
            'sensor_type': 'TEMPERATURE',
            'container': self.container.id,
            'serial_number': 'SN123456',
            'manufacturer': 'Test Manufacturer',
            'installation_date': self.installation_date.isoformat(),
            'last_calibration_date': self.calibration_date.isoformat(),
            'active': True
        }
        self.sensor = Sensor.objects.create(
            name=self.sensor_data['name'],
            sensor_type=self.sensor_data['sensor_type'],
            container=self.container,
            serial_number=self.sensor_data['serial_number'],
            manufacturer=self.sensor_data['manufacturer'],
            installation_date=self.installation_date,
            last_calibration_date=self.calibration_date,
            active=self.sensor_data['active']
        )
        
        # Set up URLs for API endpoints
        self.list_url = reverse('infrastructure:sensor-list')
        self.detail_url = reverse('infrastructure:sensor-detail', kwargs={'pk': self.sensor.pk})

    def test_list_sensors(self):
        """Test retrieving a list of sensors."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_sensor(self):
        """Test creating a new sensor."""
        new_sensor_data = {
            'name': 'New Sensor',
            'sensor_type': 'OXYGEN',
            'container': self.container.id,
            'serial_number': 'SN789012',
            'manufacturer': 'New Manufacturer',
            'installation_date': '2023-02-01',
            'last_calibration_date': '2023-07-01',
            'active': True
        }
        response = self.client.post(self.list_url, new_sensor_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], new_sensor_data['name'])
        self.assertEqual(response.data['sensor_type'], new_sensor_data['sensor_type'])
        self.assertEqual(response.data['container'], new_sensor_data['container'])
        self.assertEqual(Sensor.objects.count(), 2)
        
        # Verify the data was saved correctly
        sensor = Sensor.objects.get(id=response.data['id'])
        self.assertEqual(sensor.serial_number, new_sensor_data['serial_number'])
        self.assertEqual(sensor.manufacturer, new_sensor_data['manufacturer'])
        self.assertEqual(sensor.installation_date.isoformat(), new_sensor_data['installation_date'])
        self.assertEqual(sensor.last_calibration_date.isoformat(), new_sensor_data['last_calibration_date'])

    def test_retrieve_sensor(self):
        """Test retrieving a single sensor."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.sensor_data['name'])
        self.assertEqual(response.data['sensor_type'], self.sensor_data['sensor_type'])
        self.assertEqual(response.data['container'], self.sensor_data['container'])
        self.assertEqual(response.data['serial_number'], self.sensor_data['serial_number'])
        self.assertEqual(response.data['manufacturer'], self.sensor_data['manufacturer'])
        self.assertEqual(response.data['installation_date'], self.sensor_data['installation_date'])
        self.assertEqual(response.data['last_calibration_date'], self.sensor_data['last_calibration_date'])

    def test_update_sensor(self):
        """Test updating a sensor."""
        updated_data = {
            'name': 'Updated Sensor',
            'sensor_type': 'PH',
            'container': self.container.id,
            'serial_number': 'SN-UPDATED',
            'manufacturer': 'Updated Manufacturer',
            'installation_date': '2023-03-01',
            'last_calibration_date': '2023-08-01',
            'active': True
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.name, updated_data['name'])
        self.assertEqual(self.sensor.sensor_type, updated_data['sensor_type'])
        self.assertEqual(self.sensor.serial_number, updated_data['serial_number'])
        self.assertEqual(self.sensor.manufacturer, updated_data['manufacturer'])
        self.assertEqual(self.sensor.installation_date.isoformat(), updated_data['installation_date'])
        self.assertEqual(self.sensor.last_calibration_date.isoformat(), updated_data['last_calibration_date'])

    def test_partial_update_sensor(self):
        """Test partially updating a sensor."""
        patch_data = {
            'name': 'Patched Sensor Name',
            'last_calibration_date': '2023-09-01'
        }
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.name, patch_data['name'])
        self.assertEqual(self.sensor.last_calibration_date.isoformat(), patch_data['last_calibration_date'])
        # Other fields should remain unchanged
        self.assertEqual(self.sensor.sensor_type, self.sensor_data['sensor_type'])
        self.assertEqual(self.sensor.serial_number, self.sensor_data['serial_number'])

    def test_delete_sensor(self):
        """Test deleting a sensor."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Sensor.objects.count(), 0)

    def test_filter_by_sensor_type(self):
        """Test filtering sensors by sensor_type."""
        # Create sensors with different types
        Sensor.objects.create(
            name='Oxygen Sensor',
            sensor_type='OXYGEN',
            container=self.container,
            serial_number='SN-OXYGEN',
            manufacturer='Test Manufacturer',
            active=True
        )
        
        # Test filtering by TEMPERATURE
        response = self.client.get(f"{self.list_url}?sensor_type=TEMPERATURE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only TEMPERATURE sensors are returned
        for item in get_response_items(response):
            self.assertEqual(item['sensor_type'], 'TEMPERATURE')
        
        # Test filtering by OXYGEN
        response = self.client.get(f"{self.list_url}?sensor_type=OXYGEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only OXYGEN sensors are returned
        for item in get_response_items(response):
            self.assertEqual(item['sensor_type'], 'OXYGEN')

    def test_filter_by_container(self):
        """Test filtering sensors by container."""
        # Create another container and sensor
        another_container = Container.objects.create(
            name='Another Container',
            container_type=self.container_type,
            area=self.area,
            volume_m3=Decimal('300.00'),
            max_biomass_kg=Decimal('3000.00'),
            active=True
        )
        
        Sensor.objects.create(
            name='Another Sensor',
            sensor_type='SALINITY',
            container=another_container,
            serial_number='SN-ANOTHER',
            manufacturer='Test Manufacturer',
            active=True
        )
        
        # Test filtering by original container
        response = self.client.get(f"{self.list_url}?container={self.container.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only sensors in the original container are returned
        for item in get_response_items(response):
            self.assertEqual(item['container'], self.container.id)
        
        # Test filtering by new container
        response = self.client.get(f"{self.list_url}?container={another_container.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that only sensors in the new container are returned
        for item in get_response_items(response):
            self.assertEqual(item['container'], another_container.id)
