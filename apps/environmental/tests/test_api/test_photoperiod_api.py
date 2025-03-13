"""
Tests for the PhotoperiodData API endpoints.

This module tests CRUD operations for the PhotoperiodData model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import date, timedelta

from apps.environmental.models import PhotoperiodData
from apps.infrastructure.models import Geography, Area


class PhotoperiodDataAPITest(APITestCase):
    """Test suite for PhotoperiodData API endpoints."""

    def setUp(self):
        """Set up test data."""
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
        
        # Create photoperiod data
        self.today = date.today()
        self.photoperiod_data = {
            'area': self.area,
            'date': self.today,
            'day_length_hours': Decimal('12.50'),
            'is_interpolated': False
        }
        
        self.photoperiod = PhotoperiodData.objects.create(**self.photoperiod_data)
        self.list_url = reverse('photoperioddata-list')
        self.detail_url = reverse('photoperioddata-detail', kwargs={'pk': self.photoperiod.pk})
        
        # Create additional photoperiod data for date range tests
        for i in range(1, 6):
            PhotoperiodData.objects.create(
                area=self.area,
                date=self.today - timedelta(days=i),
                day_length_hours=Decimal(f'{12.0 - (i*0.2)}'),
                is_interpolated=True
            )

    def test_list_photoperiod_data(self):
        """Test retrieving a list of photoperiod data entries."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)  # Initial + 5 additional entries

    def test_create_photoperiod_data(self):
        """Test creating a new photoperiod data entry."""
        new_data = {
            'area': self.area.id,
            'date': (self.today + timedelta(days=1)).isoformat(),
            'day_length_hours': '12.75',
            'is_interpolated': False
        }
        response = self.client.post(self.list_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['day_length_hours']), float(new_data['day_length_hours']))
        self.assertEqual(PhotoperiodData.objects.count(), 7)

    def test_retrieve_photoperiod_data(self):
        """Test retrieving a single photoperiod data entry."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['day_length_hours']), float(self.photoperiod_data['day_length_hours']))
        self.assertEqual(response.data['is_interpolated'], self.photoperiod_data['is_interpolated'])

    def test_update_photoperiod_data(self):
        """Test updating a photoperiod data entry."""
        updated_data = {
            'area': self.area.id,
            'date': self.today.isoformat(),
            'day_length_hours': '13.25',
            'is_interpolated': True
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.photoperiod.refresh_from_db()
        self.assertAlmostEqual(float(self.photoperiod.day_length_hours), float(updated_data['day_length_hours']))
        self.assertEqual(self.photoperiod.is_interpolated, updated_data['is_interpolated'])

    def test_partial_update_photoperiod_data(self):
        """Test partially updating a photoperiod data entry."""
        patch_data = {'day_length_hours': '13.00'}
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.photoperiod.refresh_from_db()
        self.assertAlmostEqual(float(self.photoperiod.day_length_hours), float(patch_data['day_length_hours']))
        self.assertEqual(self.photoperiod.is_interpolated, self.photoperiod_data['is_interpolated'])  # Unchanged

    def test_delete_photoperiod_data(self):
        """Test deleting a photoperiod data entry."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PhotoperiodData.objects.count(), 5)  # Only the 5 additional entries remain

    def test_day_length_validation(self):
        """Test validation of day length hours."""
        # Test day length < 0
        invalid_data = {
            'area': self.area.id,
            'date': (self.today + timedelta(days=1)).isoformat(),
            'day_length_hours': '-1.0',  # Invalid: less than 0
            'is_interpolated': False
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('day_length_hours', str(response.data))

        # Test day length > 24
        invalid_data = {
            'area': self.area.id,
            'date': (self.today + timedelta(days=1)).isoformat(),
            'day_length_hours': '25.0',  # Invalid: greater than 24
            'is_interpolated': False
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('day_length_hours', str(response.data))

    def test_date_filtering(self):
        """Test filtering photoperiod data by date range."""
        from_date = (self.today - timedelta(days=3)).isoformat()
        to_date = self.today.isoformat()
        
        # Should return the initial entry and 3 of the additional entries
        url = f"{self.list_url}?from_date={from_date}&to_date={to_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_filter_by_area(self):
        """Test filtering photoperiod data by area."""
        # Create a second area
        second_area = Area.objects.create(
            name="Second Area",
            geography=self.geography,
            latitude=Decimal('30.123456'),
            longitude=Decimal('40.123456'),
            max_biomass=Decimal('2000.00')
        )
        
        # Create photoperiod data for the second area
        PhotoperiodData.objects.create(
            area=second_area,
            date=self.today,
            day_length_hours=Decimal('11.50'),
            is_interpolated=False
        )
        
        # Test filtering by the original area
        url = f"{self.list_url}?area={self.area.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)  # Original 6 entries
        
        # Test filtering by the second area
        url = f"{self.list_url}?area={second_area.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # One entry for the second area
