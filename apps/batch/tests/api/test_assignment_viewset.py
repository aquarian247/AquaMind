"""
Tests for the BatchContainerAssignmentViewSet.
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from tests.base import BaseAPITestCase
from decimal import Decimal
from datetime import date, timedelta

from apps.batch.models import BatchContainerAssignment
from apps.batch.tests.api.test_utils import (
    create_test_user,
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
    create_test_batch_container_assignment
)


class BatchContainerAssignmentViewSetTest(BaseAPITestCase):
    """Test the BatchContainerAssignment viewset."""

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
        
        # Create a container
        self.container = create_test_container(name="Tank 1")
        
        # Create an assignment to test
        self.assignment = create_test_batch_container_assignment(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            avg_weight_g=Decimal("10.0")
        )
        
        # Valid data for API tests
        self.valid_assignment_data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 500,
            'avg_weight_g': "15.0",
            'assignment_date': date.today().isoformat(),
            'is_active': True,
            'notes': 'Test assignment from API test'
        }

    def test_list_assignments(self):
        """Test listing container assignments."""
        url = self.get_api_url('batch', 'container-assignments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch']['id'], self.batch.id)
        self.assertEqual(response.data['results'][0]['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(response.data['results'][0]['container']['id'], self.container.id)
        self.assertEqual(response.data['results'][0]['container']['name'], self.container.name)

    def test_create_assignment(self):
        """Test creating a container assignment."""
        # Create a new batch to avoid population count validation issues
        new_batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH002"
        )
        
        # Create a new container
        new_container = create_test_container(name="Tank 2")
        
        # Update valid_assignment_data to use the new batch and container
        assignment_data = {
            'batch_id': new_batch.id,
            'container_id': new_container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 500,
            'avg_weight_g': "15.0",
            'assignment_date': date.today().isoformat(),
            'is_active': True,
            'notes': 'New test assignment from create test'
        }
        
        url = self.get_api_url('batch', 'container-assignments')
        
        # Print request data for debugging
        print("Create Assignment Request Data:", assignment_data)
        
        response = self.client.post(url, assignment_data, format='json')
        
        # Print response for debugging
        print("Create Assignment Response Status:", response.status_code)
        if response.status_code != status.HTTP_201_CREATED:
            print("Response Data:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BatchContainerAssignment.objects.count(), 2)
        
        # Verify the created assignment
        new_assignment = BatchContainerAssignment.objects.get(id=response.data['id'])
        self.assertEqual(new_assignment.batch, new_batch)
        self.assertEqual(new_assignment.container, new_container)
        self.assertEqual(new_assignment.lifecycle_stage, self.lifecycle_stage)
        self.assertEqual(new_assignment.population_count, 500)
        self.assertEqual(new_assignment.avg_weight_g, Decimal("15.0"))
        self.assertEqual(new_assignment.biomass_kg, Decimal("7.5"))  # Calculated field

    def test_retrieve_assignment(self):
        """Test retrieving a container assignment."""
        url = self.get_api_url('batch', 'container-assignments', detail=True, pk=self.assignment.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['id'], self.batch.id)
        self.assertEqual(response.data['batch']['batch_number'], self.batch.batch_number)
        self.assertEqual(response.data['container']['id'], self.container.id)
        self.assertEqual(response.data['container']['name'], self.container.name)
        self.assertEqual(response.data['population_count'], 1000)
        self.assertEqual(Decimal(response.data['avg_weight_g']), Decimal("10.0"))
        self.assertEqual(Decimal(response.data['biomass_kg']), Decimal("10.0"))

    def test_update_assignment(self):
        """Test updating a container assignment."""
        url = self.get_api_url('batch', 'container-assignments', detail=True, pk=self.assignment.id)
        update_data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 800,
            'avg_weight_g': "12.0",
            'is_active': True,
            'notes': 'Updated test assignment'
        }
        
        response = self.client.put(url, update_data, format='json')
        
        # Print response for debugging
        if response.status_code != status.HTTP_200_OK:
            print("Update Assignment Response:", response.data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the assignment from the database
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, 800)
        self.assertEqual(self.assignment.avg_weight_g, Decimal("12.0"))
        self.assertEqual(self.assignment.biomass_kg, Decimal("9.6"))  # Calculated field

    def test_partial_update_assignment(self):
        """Test partially updating a container assignment."""
        url = self.get_api_url('batch', 'container-assignments', detail=True, pk=self.assignment.id)
        update_data = {
            'population_count': 600
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the assignment from the database
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, 600)
        self.assertEqual(self.assignment.avg_weight_g, Decimal("10.0"))  # Unchanged
        self.assertEqual(self.assignment.biomass_kg, Decimal("6.0"))  # Recalculated

    def test_delete_assignment(self):
        """Test deleting a container assignment."""
        url = self.get_api_url('batch', 'container-assignments', detail=True, pk=self.assignment.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BatchContainerAssignment.objects.count(), 0)

    def test_filter_assignments(self):
        """Test filtering container assignments."""
        # Create another batch and assignment
        batch2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH002"
        )
        container2 = create_test_container(name="Tank 2")
        assignment2 = create_test_batch_container_assignment(
            batch=batch2,
            container=container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=500,
            avg_weight_g=Decimal("20.0")
        )
        
        # Filter by batch
        url = self.get_api_url('batch', 'container-assignments') + f'?batch={self.batch.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch']['id'], self.batch.id)
        self.assertEqual(response.data['results'][0]['batch']['batch_number'], self.batch.batch_number)
        
        # Filter by container
        url = self.get_api_url('batch', 'container-assignments') + f'?container={self.container.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['container']['id'], self.container.id)
        self.assertEqual(response.data['results'][0]['container']['name'], self.container.name)
        
        # Filter by active status
        url = self.get_api_url('batch', 'container-assignments') + '?is_active=true'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['is_active'], True)
        self.assertEqual(response.data['results'][1]['is_active'], True)
