"""
Tests for the BatchCompositionViewSet.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from datetime import date, timedelta

from apps.batch.models import BatchComposition
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


class BatchCompositionViewSetTest(APITestCase):
    """Test the BatchComposition viewset."""

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
        
        # Create source batches with container assignments to ensure non-zero calculated values
        self.source_batch1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SOURCE001"
        )
        
        self.source_batch2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SOURCE002"
        )
        
        # Create containers and assignments for source batches
        self.source_container1 = create_test_container(name="Source Tank 1")
        self.source_assignment1 = create_test_batch_container_assignment(
            batch=self.source_batch1,
            container=self.source_container1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=10000,
            avg_weight_g=Decimal("5.0")
        )
        
        self.source_container2 = create_test_container(name="Source Tank 2")
        self.source_assignment2 = create_test_batch_container_assignment(
            batch=self.source_batch2,
            container=self.source_container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=8000,
            avg_weight_g=Decimal("6.0")
        )
        
        # Create mixed batch
        self.mixed_batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIXED001"
        )
        
        # Create a container and assignment for mixed batch
        self.mixed_container = create_test_container(name="Mixed Tank")
        self.mixed_assignment = create_test_batch_container_assignment(
            batch=self.mixed_batch,
            container=self.mixed_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=5000,
            avg_weight_g=Decimal("6.0")
        )
        
        # Create compositions
        self.composition1 = BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.source_batch1,
            percentage=Decimal("28.57"),
            population_count=20,
            biomass_kg=Decimal("2.0")
        )
        
        self.composition2 = BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.source_batch2,
            percentage=Decimal("71.43"),
            population_count=50,
            biomass_kg=Decimal("5.0")
        )
        
        # Valid data for API tests
        self.valid_composition_data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch1.id,
            'percentage': 50.0,
            'population_count': 30,
            'biomass_kg': 3.0
        }

    def test_list_compositions(self):
        """Test listing batch compositions."""
        url = get_batch_url('batch-compositions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_composition(self):
        """Test creating a batch composition."""
        url = get_batch_url('batch-compositions')
        
        # Print request data for debugging
        print("Create Composition Request Data:", self.valid_composition_data)
        
        response = self.client.post(url, self.valid_composition_data, format='json')
        
        # Print response for debugging
        print("Create Composition Response Status:", response.status_code)
        if response.status_code != status.HTTP_201_CREATED:
            print("Response Data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BatchComposition.objects.count(), 3)
        
        # Verify the created composition
        new_composition = BatchComposition.objects.get(id=response.data['id'])
        self.assertEqual(new_composition.mixed_batch, self.mixed_batch)
        self.assertEqual(new_composition.source_batch, self.source_batch1)
        self.assertEqual(new_composition.percentage, Decimal("50.0"))
        self.assertEqual(new_composition.population_count, 30)
        self.assertEqual(new_composition.biomass_kg, Decimal("3.0"))

    def test_retrieve_composition(self):
        """Test retrieving a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mixed_batch']['id'], self.mixed_batch.id)
        self.assertEqual(response.data['source_batch']['id'], self.source_batch1.id)
        self.assertEqual(Decimal(response.data['percentage']), Decimal("28.57"))
        self.assertEqual(response.data['population_count'], 20)
        self.assertEqual(Decimal(response.data['biomass_kg']), Decimal("2.0"))

    def test_update_composition(self):
        """Test updating a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        update_data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch1.id,
            'percentage': 35.0,
            'population_count': 25,
            'biomass_kg': 2.5
        }
        
        response = self.client.put(url, update_data, format='json')
        
        # Print response for debugging
        if response.status_code != status.HTTP_200_OK:
            print("Update Composition Response:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the composition from the database
        self.composition1.refresh_from_db()
        self.assertEqual(self.composition1.percentage, Decimal("35.0"))
        self.assertEqual(self.composition1.population_count, 25)
        self.assertEqual(self.composition1.biomass_kg, Decimal("2.5"))

    def test_partial_update_composition(self):
        """Test partially updating a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        update_data = {
            'percentage': 40.0
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the composition from the database
        self.composition1.refresh_from_db()
        self.assertEqual(self.composition1.percentage, Decimal("40.0"))
        self.assertEqual(self.composition1.population_count, 20)  # Unchanged
        self.assertEqual(self.composition1.biomass_kg, Decimal("2.0"))  # Unchanged

    def test_delete_composition(self):
        """Test deleting a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BatchComposition.objects.filter(id=self.composition1.id).count(), 0)
        self.assertEqual(BatchComposition.objects.count(), 1)  # Only composition2 should remain

    def test_filter_compositions(self):
        """Test filtering batch compositions."""
        # Filter by mixed_batch
        url = f"{get_batch_url('batch-compositions')}?mixed_batch={self.mixed_batch.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Filter by source_batch
        url = f"{get_batch_url('batch-compositions')}?source_batch={self.source_batch1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['source_batch']['id'], self.source_batch1.id)
