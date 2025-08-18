"""
Test that the batch API correctly returns calculated biomass values.
This test specifically addresses GitHub issue #17.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.batch.models import Batch, BatchContainerAssignment
from apps.batch.tests.models.test_utils import (
    create_test_species,
    create_test_lifecycle_stage,
    create_test_batch,
    create_test_container,
)

User = get_user_model()


class BatchBiomassAPITests(TestCase):
    """Test that the batch API correctly returns calculated biomass values."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.species = create_test_species()
        self.lifecycle_stage = create_test_lifecycle_stage(species=self.species)
        
    def test_batch_api_returns_correct_biomass(self):
        """
        Test that the batch API returns the correct calculated biomass.
        This addresses GitHub issue #17.
        """
        # Create a batch
        batch = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="B2023-010"
        )
        
        # Create assignments with known biomass values
        biomass_values = [
            Decimal('100.50'),
            Decimal('250.75'),
            Decimal('500.00'),
        ]
        
        for i, biomass in enumerate(biomass_values):
            container = create_test_container(name=f"Tank {i+1}")
            
            # Create assignment with specific biomass
            assignment = BatchContainerAssignment(
                batch=batch,
                container=container,
                lifecycle_stage=self.lifecycle_stage,
                population_count=1000,
                biomass_kg=biomass,
                assignment_date=date.today() - timedelta(days=i),
                is_active=True
            )
            assignment.save()
        
        # Make API request
        response = self.client.get(f'/api/v1/batch/batches/{batch.id}/')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify biomass in response
        expected_biomass = sum(biomass_values)
        response_biomass = Decimal(str(response.data['calculated_biomass_kg']))
        
        self.assertEqual(response_biomass, expected_biomass)
        self.assertAlmostEqual(
            float(response_biomass),
            851.25,  # Sum of test biomass values
            places=2
        )
        
    def test_batch_list_api_returns_correct_biomass(self):
        """Test that the batch list API also returns correct biomass for each batch."""
        # Create two batches with different biomass values
        batch1 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001"
        )
        batch2 = create_test_batch(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH002"
        )
        
        # Add assignments to batch1
        container1 = create_test_container(name="Tank 1")
        BatchContainerAssignment.objects.create(
            batch=batch1,
            container=container1,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            biomass_kg=Decimal('50.00'),
            assignment_date=date.today(),
            is_active=True
        )
        
        # Add assignments to batch2
        container2 = create_test_container(name="Tank 2")
        BatchContainerAssignment.objects.create(
            batch=batch2,
            container=container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=200,
            biomass_kg=Decimal('150.00'),
            assignment_date=date.today(),
            is_active=True
        )
        
        # Make API request
        response = self.client.get('/api/v1/batch/batches/')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Find batches in response
        batch1_data = next(b for b in response.data['results'] if b['id'] == batch1.id)
        batch2_data = next(b for b in response.data['results'] if b['id'] == batch2.id)
        
        # Verify biomass values
        self.assertEqual(Decimal(str(batch1_data['calculated_biomass_kg'])), Decimal('50.00'))
        self.assertEqual(Decimal(str(batch2_data['calculated_biomass_kg'])), Decimal('150.00'))
