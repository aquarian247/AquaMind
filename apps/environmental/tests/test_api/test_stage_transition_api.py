"""
Tests for the StageTransitionEnvironmental API endpoints.

This module tests CRUD operations for the StageTransitionEnvironmental model through the API.
"""
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.environmental.models import StageTransitionEnvironmental
from apps.batch.models import BatchTransfer, Batch


class StageTransitionEnvironmentalAPITest(APITestCase):
    """Test suite for StageTransitionEnvironmental API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create required related objects
        self.batch = Batch.objects.create(
            name="Test Batch",
            start_date=timezone.now().date(),
            expected_end_date=timezone.now().date()
        )
        
        self.batch_transfer = BatchTransfer.objects.create(
            batch=self.batch,
            transfer_date=timezone.now().date(),
            from_stage="EGG",
            to_stage="FRY",
            quantity=1000
        )
        
        # Create stage transition environmental data
        self.transition_data = {
            'batch_transfer': self.batch_transfer,
            'temperature': Decimal('12.50'),
            'oxygen': Decimal('90.00'),
            'ph': Decimal('7.20'),
            'salinity': Decimal('35.00'),
            'notes': 'Initial test transition'
        }
        
        self.transition = StageTransitionEnvironmental.objects.create(**self.transition_data)
        self.list_url = reverse('stagetransitionenvironmental-list')
        self.detail_url = reverse('stagetransitionenvironmental-detail', kwargs={'pk': self.transition.pk})

    def test_list_transitions(self):
        """Test retrieving a list of stage transition environmental data."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['temperature']), float(self.transition_data['temperature']))

    def test_create_transition(self):
        """Test creating a new stage transition environmental record."""
        new_batch_transfer = BatchTransfer.objects.create(
            batch=self.batch,
            transfer_date=timezone.now().date(),
            from_stage="FRY",
            to_stage="FINGERLING",
            quantity=950
        )
        
        new_data = {
            'batch_transfer': new_batch_transfer.id,
            'temperature': '13.50',
            'oxygen': '92.00',
            'ph': '7.30',
            'salinity': '36.00',
            'notes': 'New test transition'
        }
        response = self.client.post(self.list_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['temperature']), float(new_data['temperature']))
        self.assertEqual(StageTransitionEnvironmental.objects.count(), 2)

    def test_retrieve_transition(self):
        """Test retrieving a single stage transition environmental record."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data['temperature']), float(self.transition_data['temperature']))
        self.assertEqual(float(response.data['oxygen']), float(self.transition_data['oxygen']))
        self.assertEqual(float(response.data['ph']), float(self.transition_data['ph']))
        self.assertEqual(float(response.data['salinity']), float(self.transition_data['salinity']))
        self.assertEqual(response.data['notes'], self.transition_data['notes'])

    def test_update_transition(self):
        """Test updating a stage transition environmental record."""
        updated_data = {
            'batch_transfer': self.batch_transfer.id,
            'temperature': '14.00',
            'oxygen': '93.50',
            'ph': '7.40',
            'salinity': '34.50',
            'notes': 'Updated test transition'
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transition.refresh_from_db()
        self.assertAlmostEqual(float(self.transition.temperature), float(updated_data['temperature']))
        self.assertAlmostEqual(float(self.transition.oxygen), float(updated_data['oxygen']))
        self.assertAlmostEqual(float(self.transition.ph), float(updated_data['ph']))
        self.assertAlmostEqual(float(self.transition.salinity), float(updated_data['salinity']))
        self.assertEqual(self.transition.notes, updated_data['notes'])

    def test_partial_update_transition(self):
        """Test partially updating a stage transition environmental record."""
        patch_data = {
            'temperature': '13.00',
            'notes': 'Patched notes'
        }
        response = self.client.patch(self.detail_url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transition.refresh_from_db()
        self.assertAlmostEqual(float(self.transition.temperature), float(patch_data['temperature']))
        self.assertEqual(self.transition.notes, patch_data['notes'])
        # Other fields should remain unchanged
        self.assertAlmostEqual(float(self.transition.oxygen), float(self.transition_data['oxygen']))

    def test_delete_transition(self):
        """Test deleting a stage transition environmental record."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StageTransitionEnvironmental.objects.count(), 0)

    def test_value_validation(self):
        """Test validation of environmental values."""
        # Test negative temperature
        invalid_data = {
            'batch_transfer': self.batch_transfer.id,
            'temperature': '-5.0',  # Invalid: negative temperature
            'oxygen': '90.00',
            'ph': '7.20',
            'salinity': '35.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('temperature', str(response.data))

        # Test negative oxygen
        invalid_data = {
            'batch_transfer': self.batch_transfer.id,
            'temperature': '12.50',
            'oxygen': '-10.00',  # Invalid: negative oxygen
            'ph': '7.20',
            'salinity': '35.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('oxygen', str(response.data))

        # Test pH out of range (0-14)
        invalid_data = {
            'batch_transfer': self.batch_transfer.id,
            'temperature': '12.50',
            'oxygen': '90.00',
            'ph': '15.00',  # Invalid: pH > 14
            'salinity': '35.00'
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ph', str(response.data))

        # Test negative salinity
        invalid_data = {
            'batch_transfer': self.batch_transfer.id,
            'temperature': '12.50',
            'oxygen': '90.00',
            'ph': '7.20',
            'salinity': '-5.00'  # Invalid: negative salinity
        }
        response = self.client.post(self.list_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('salinity', str(response.data))

    def test_filter_by_batch_transfer(self):
        """Test filtering by batch transfer."""
        # Create a second batch transfer and associated environmental data
        second_batch_transfer = BatchTransfer.objects.create(
            batch=self.batch,
            transfer_date=timezone.now().date(),
            from_stage="FRY",
            to_stage="FINGERLING",
            quantity=950
        )
        
        StageTransitionEnvironmental.objects.create(
            batch_transfer=second_batch_transfer,
            temperature=Decimal('14.50'),
            oxygen=Decimal('91.00'),
            ph=Decimal('7.25'),
            salinity=Decimal('36.50'),
            notes='Second transition'
        )
        
        # Test filtering by the original batch transfer
        url = f"{self.list_url}?batch_transfer={self.batch_transfer.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # Test filtering by the second batch transfer
        url = f"{self.list_url}?batch_transfer={second_batch_transfer.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['temperature']), 14.50)
