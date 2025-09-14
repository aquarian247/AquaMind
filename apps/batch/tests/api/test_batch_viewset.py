"""
Tests for the BatchViewSet.
"""
from rest_framework import status
from tests.base import BaseAPITestCase
from decimal import Decimal
from datetime import date, timedelta
import datetime # Import the full module for aliasing
from unittest.mock import patch

OriginalDate = datetime.date  # Alias for the original datetime.date

from apps.batch.models import Batch
from apps.batch.tests.api.test_utils import (
    create_test_user,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchViewSetTest(BaseAPITestCase):
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
        url = self.get_api_url('batch', 'batches')
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
        url = self.get_api_url('batch', 'batches')
        
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
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
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
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
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
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
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
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id)
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
        simulated_today = OriginalDate(2025, 1, 1) # Use OriginalDate to create the instance for clarity

        # Patch the 'date' name in the current module's namespace.
        # autospec=OriginalDate ensures the mock behaves like datetime.date for isinstance checks etc.
        with patch('apps.batch.tests.api.test_batch_viewset.date', autospec=OriginalDate) as MockDateType:
            MockDateType.today.return_value = simulated_today
            # When date(Y, M, D) is called (which is now MockDateType(Y,M,D)), 
            # it should return a real datetime.date instance.
            MockDateType.side_effect = lambda *args, **kwargs: OriginalDate(*args, **kwargs)
            
            # Filter by species
            url = f"{self.get_api_url('batch', 'batches')}?species={self.species.id}"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
            
            # Filter by status
            url = f"{self.get_api_url('batch', 'batches')}?status=ACTIVE"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)  # Both batches are active
            
            # Filter by date range
            # The batches were created with start_date = real_today - 30 days
            # So we need to filter for dates that include that range
            thirty_days_ago = OriginalDate.today() - timedelta(days=30)
            sixty_days_ago = OriginalDate.today() - timedelta(days=60)
            ten_days_ago = OriginalDate.today() - timedelta(days=10)

            # Filter for batches created between 60 days ago and 10 days ago
            start_date_query_val = sixty_days_ago.isoformat()
            end_date_query_val = ten_days_ago.isoformat()
            url = f"{self.get_api_url('batch', 'batches')}?start_date_after={start_date_query_val}&start_date_before={end_date_query_val}"
            response = self.client.get(url)

            # Print response for debugging
            print("Filter by Date Range Response:", response.data)

            # Both test batches should be included as they were created ~30 days ago
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 2)
            
            # Filter by batch number
            url = f"{self.get_api_url('batch', 'batches')}?batch_number=BATCH001"
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
