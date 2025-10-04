"""
Tests for the PhotoperiodData API endpoints.

This module tests CRUD operations and serializer validation for
the PhotoperiodData model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.environmental.models import PhotoperiodData
from apps.infrastructure.models import Geography, Area


class PhotoperiodDataAPITest(APITestCase):
    """Test suite for PhotoperiodData API endpoints."""

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

        # Create test date
        self.test_date = timezone.now().date()

        # Create initial PhotoperiodData entries
        self.photoperiod_data = PhotoperiodData.objects.create(
            area=self.area,
            date=self.test_date,
            day_length_hours=Decimal('12.50'),
            light_intensity=Decimal('15000.00'),
            is_interpolated=False
        )

        self.photoperiod_data2 = PhotoperiodData.objects.create(
            area=self.area,
            date=self.test_date + timezone.timedelta(days=1),
            day_length_hours=Decimal('13.00'),
            light_intensity=Decimal('16000.00'),
            is_interpolated=True
        )

        # Set up URLs
        self.list_url = reverse('photoperiod-list')
        self.detail_url = reverse('photoperiod-detail', kwargs={'pk': self.photoperiod_data.pk})

    def test_list_photoperiod_data(self):
        """Test listing all photoperiod data entries."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have at least the 2 objects we created in setUp
        self.assertGreaterEqual(len(response.data), 2)

    def test_retrieve_photoperiod_data(self):
        """Test retrieving a single photoperiod data entry."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['day_length_hours']), 12.50)
        self.assertEqual(float(response.data['light_intensity']), 15000.00)
        self.assertEqual(response.data['is_interpolated'], False)

    def test_create_photoperiod_data(self):
        """Test creating a new photoperiod data entry."""
        new_data = {
            'area': self.area.id,
            'date': (self.test_date + timezone.timedelta(days=2)).isoformat(),
            'day_length_hours': '14.00',
            'light_intensity': '17000.00',
            'is_interpolated': True
        }
        response = self.client.post(self.list_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['day_length_hours']), 14.00)
        self.assertEqual(float(response.data['light_intensity']), 17000.00)
        self.assertEqual(response.data['is_interpolated'], True)
        self.assertEqual(PhotoperiodData.objects.count(), 3)

    def test_create_photoperiod_data_minimal(self):
        """Test creating a new photoperiod data entry with minimal required fields."""
        new_data = {
            'area': self.area.id,
            'date': (self.test_date + timezone.timedelta(days=2)).isoformat(),
            'day_length_hours': '14.00'
        }
        response = self.client.post(self.list_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['day_length_hours']), 14.00)
        self.assertIsNone(response.data['light_intensity'])  # Optional field
        self.assertEqual(response.data['is_interpolated'], False)  # Default value
        self.assertEqual(PhotoperiodData.objects.count(), 3)

    def test_update_photoperiod_data(self):
        """Test updating a photoperiod data entry."""
        updated_data = {
            'area': self.area.id,
            'date': self.test_date.isoformat(),
            'day_length_hours': '13.50',
            'light_intensity': '15500.00',
            'is_interpolated': True
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.photoperiod_data.refresh_from_db()
        self.assertAlmostEqual(float(self.photoperiod_data.day_length_hours), 13.50)
        self.assertAlmostEqual(float(self.photoperiod_data.light_intensity), 15500.00)
        self.assertEqual(self.photoperiod_data.is_interpolated, True)

    def test_partial_update_photoperiod_data(self):
        """Test partially updating a photoperiod data entry."""
        patch_data = {
            'day_length_hours': '15.00',
            'is_interpolated': True
        }
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.photoperiod_data.refresh_from_db()
        self.assertAlmostEqual(float(self.photoperiod_data.day_length_hours), 15.00)
        self.assertEqual(self.photoperiod_data.is_interpolated, True)
        # Other fields should remain unchanged
        self.assertAlmostEqual(float(self.photoperiod_data.light_intensity), 15000.00)

    def test_delete_photoperiod_data(self):
        """Test deleting a photoperiod data entry."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PhotoperiodData.objects.count(), 1)

    def test_serializer_field_alignment(self):
        """Test that serializer fields match model fields exactly."""
        # This test ensures no phantom fields exist in serializer
        # that would cause FieldError on save
        serializer_data = {
            'area': self.area.id,
            'date': (self.test_date + timezone.timedelta(days=5)).isoformat(),
            'day_length_hours': '12.00',
            'light_intensity': '14000.00',
            'is_interpolated': False
        }

        # This should succeed without raising FieldError
        response = self.client.post(self.list_url, serializer_data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the object was created with correct data
        created_obj = PhotoperiodData.objects.get(pk=response.data['id'])
        self.assertEqual(float(created_obj.day_length_hours), 12.00)
        self.assertEqual(float(created_obj.light_intensity), 14000.00)
        self.assertEqual(created_obj.is_interpolated, False)

    def test_validation_day_length_hours_range(self):
        """Test validation of day_length_hours field range."""
        # Test minimum value (should fail)
        invalid_data = {
            'area': self.area.id,
            'date': self.test_date.isoformat(),
            'day_length_hours': '-1.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test maximum value (should fail)
        invalid_data['day_length_hours'] = '25.00'
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test valid boundary values
        valid_data = {
            'area': self.area.id,
            'date': (self.test_date + timezone.timedelta(days=3)).isoformat(),
            'day_length_hours': '0.00'
        }
        response = self.client.post(self.list_url, valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        valid_data['date'] = (self.test_date + timezone.timedelta(days=4)).isoformat()
        valid_data['day_length_hours'] = '24.00'
        response = self.client.post(self.list_url, valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
