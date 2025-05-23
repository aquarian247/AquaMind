"""
Tests for the BatchViewSet.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from apps.batch.models import Batch
from apps.batch.tests.api.test_helpers import get_api_url
from apps.batch.tests.api.test_utils import (
    create_test_user,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


def get_batch_url(endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for batch API endpoints"""
    return get_api_url('batch', endpoint, detail, **kwargs)


class BatchViewSetTest(APITestCase):
    """Test the Batch viewset."""

    def setUp(self):
        """Set up test data."""
        # Create a test user and authenticate
        self.user = create_test_user()
        self.client.force_authenticate(user=self.user)
        
        # Create species and lifecycle stage
        self.species = create_test_species(name="Atlantic Salmon")
        self.lifecycle_stage = create_test_lifecycle_stage(
            species=self.species,
            name="Fry",
            order=2
        )
        
        # Create a batch
        self.batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001"
        )
        
        # Create a container and assignment for the batch
        self.container = create_test_container(name="Tank 1")
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        
        # Valid data for API tests
        self.valid_batch_data = {
            'batch_number': 'BATCH002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': date.today().isoformat(),
            'expected_end_date': (date.today() + timedelta(days=365)).isoformat(),
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'notes': 'Test batch'
        }

    def test_list_batches(self):
        """Test listing batches."""
        url = get_batch_url('batches')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
        
        # Check calculated fields
        self.assertEqual(response.data['results'][0]['calculated_population_count'], 1000)
        self.assertEqual(Decimal(response.data['results'][0]['calculated_biomass_kg']), Decimal('10.00'))
        self.assertEqual(Decimal(response.data['results'][0]['calculated_avg_weight_g']), Decimal('10.00'))

    def test_create_batch(self):
        """
        Test creating a new batch via the API.
        """
        url = get_batch_url('batches')
        
        # Print request data for debugging
        print("Create Batch Request Data:", self.valid_batch_data)
        
        response = self.client.post(url, self.valid_batch_data, format='json')
        
        # Print response for debugging
        print("Create Batch Response Status:", response.status_code)
        if response.status_code != status.HTTP_201_CREATED:
            print("Response Data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Batch.objects.count(), 2)
        
        # Verify the created batch
        new_batch = Batch.objects.get(batch_number='BATCH002')
        self.assertEqual(new_batch.species, self.species)
        self.assertEqual(new_batch.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(new_batch.status, 'ACTIVE')
        self.assertEqual(new_batch.batch_type, 'STANDARD')
        self.assertEqual(new_batch.notes, 'Test batch')

    def test_retrieve_batch(self):
        """Test retrieving a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch_number'], 'BATCH001')
        self.assertEqual(response.data['species'], self.species.id)
        self.assertEqual(response.data['lifecycle_stage'], self.lifecycle_stage.id)
        self.assertEqual(response.data['calculated_population_count'], 1000)
        self.assertEqual(Decimal(response.data['calculated_biomass_kg']), Decimal('10.00'))
        self.assertEqual(Decimal(response.data['calculated_avg_weight_g']), Decimal('10.00'))

    def test_update_batch(self):
        """Test updating a batch (direct fields like status, notes)."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        update_data = {
            'batch_number': 'BATCH001-UPDATED',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': self.batch.start_date.isoformat(),
            'expected_end_date': self.batch.expected_end_date.isoformat(),
            'status': 'COMPLETED',
            'batch_type': 'STANDARD',
            'notes': 'Updated test batch'
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the batch from the database
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.batch_number, 'BATCH001-UPDATED')
        self.assertEqual(self.batch.status, 'COMPLETED')
        self.assertEqual(self.batch.notes, 'Updated test batch')

    def test_partial_update_batch(self):
        """Test partially updating a batch (direct fields like status, notes)."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        update_data = {
            'status': 'COMPLETED',
            'notes': 'Partially updated batch'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the batch from the database
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'COMPLETED')
        self.assertEqual(self.batch.notes, 'Partially updated batch')

    def test_delete_batch(self):
        """Test deleting a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Batch.objects.count(), 0)

    def test_filter_batches(self):
        """Test filtering batches."""
        # Create another batch with different species
        other_species = create_test_species(name="Rainbow Trout")
        other_stage = create_test_lifecycle_stage(
            species=other_species,
            name="Smolt",
            order=3
        )
        other_batch = create_test_batch(
            species=other_species,
            lifecycle_stage=other_stage,
            batch_number="BATCH002"
        )
        
        # Define a fixed "today" for mocking to make date-based filters deterministic
        simulated_today = date(2025, 1, 1) # Uses 'date' from 'from datetime import date'

        with patch('apps.batch.tests.api.test_batch_viewset.date.today') as mock_today: # Patch 'date.today' as imported in this module
            mock_today.return_value = simulated_today
            
            # Filter by species
            url = f"{get_batch_url('batches')}?species={self.species.id}"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
            
            # Filter by status
            url = f"{get_batch_url('batches')}?status=ACTIVE"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)  # Both batches are active
            
            # Filter by date range
            # Uses the mocked date.today() (which returns simulated_today)
            start_date_query_val = (date.today() - timedelta(days=60)).isoformat()
            end_date_query_val = (date.today() - timedelta(days=1)).isoformat()
            url = f"{get_batch_url('batches')}?start_date_after={start_date_query_val}&start_date_before={end_date_query_val}"
            response = self.client.get(url)
            
            # Print response for debugging
            print("Filter by Date Range Response:", response.data)
            
            # The test batch should be included as it was created 30 days ago
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)
            
            # Filter by batch number
            url = f"{get_batch_url('batches')}?batch_number=BATCH001"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
