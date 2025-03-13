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
        # Create required related objects first
        from apps.infrastructure.models import Container, ContainerType, Area, Geography
        from apps.batch.models import Species, LifeCycleStage
        
        # Create a species
        self.species = Species.objects.create(
            name="Test Species",
            scientific_name="Testus fishus"
        )
        
        # Create lifecycle stages
        self.source_stage = LifeCycleStage.objects.create(
            name="EGG",
            species=self.species,
            order=1
        )
        
        self.dest_stage = LifeCycleStage.objects.create(
            name="FRY",
            species=self.species,
            order=2
        )
        
        # Create Geography and Area for our Container
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=Decimal('60.000000'),
            longitude=Decimal('-5.000000'),
            max_biomass=Decimal('10000.00')
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=Decimal('10.00')
        )
        
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,  # Associate with an area
            active=True,
            volume_m3=Decimal('5.00'),
            max_biomass_kg=Decimal('500.00')  # Add required max biomass field
        )
        
        # Create a batch
        self.batch = Batch.objects.create(
            batch_number="TEST-BATCH-001",
            species=self.species,
            lifecycle_stage=self.source_stage,
            container=self.container,
            population_count=1000,
            biomass_kg=Decimal('100.00'),
            avg_weight_g=Decimal('100.00'),
            start_date=timezone.now().date()
        )
        
        # Create a batch transfer
        self.batch_transfer = BatchTransfer.objects.create(
            source_batch=self.batch,
            transfer_type="LIFECYCLE",
            transfer_date=timezone.now().date(),
            source_count=1000,
            transferred_count=1000,
            source_biomass_kg=Decimal('100.00'),
            transferred_biomass_kg=Decimal('100.00'),
            source_lifecycle_stage=self.source_stage,
            destination_lifecycle_stage=self.dest_stage,
            source_container=self.container,
            destination_container=self.container
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
        # Create a second batch transfer with proper field names
        new_batch_transfer = BatchTransfer.objects.create(
            source_batch=self.batch,
            transfer_type="LIFECYCLE",
            transfer_date=timezone.now().date(),
            source_count=950,
            transferred_count=950,
            source_biomass_kg=Decimal('100.00'),
            transferred_biomass_kg=Decimal('100.00'),
            source_lifecycle_stage=self.source_stage,
            destination_lifecycle_stage=self.dest_stage,
            source_container=self.container,
            destination_container=self.container
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
        # Create a new batch transfer for this test to avoid unique constraint violation
        validation_batch = Batch.objects.create(
            batch_number="TEST-BATCH-003",
            species=self.species,
            lifecycle_stage=self.source_stage,
            container=self.container,
            population_count=500,
            biomass_kg=Decimal('50.00'),
            avg_weight_g=Decimal('100.00'),
            start_date=timezone.now().date()
        )
        
        validation_transfer = BatchTransfer.objects.create(
            source_batch=validation_batch,
            transfer_type="LIFECYCLE",
            transfer_date=timezone.now().date(),
            source_count=500,
            transferred_count=500,
            source_biomass_kg=Decimal('50.00'),
            transferred_biomass_kg=Decimal('50.00'),
            source_lifecycle_stage=self.source_stage,
            destination_lifecycle_stage=self.dest_stage,
            source_container=self.container,
            destination_container=self.container
        )
        
        # Test negative temperature
        invalid_data = {
            'batch_transfer': validation_transfer.id,
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
            'batch_transfer': validation_transfer.id,
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
            'batch_transfer': validation_transfer.id,
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
            'batch_transfer': validation_transfer.id,
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
        # Create another batch and transfer
        second_batch = Batch.objects.create(
            batch_number="TEST-BATCH-002",
            species=self.species,
            lifecycle_stage=self.source_stage,
            container=self.container,
            population_count=800,
            biomass_kg=Decimal('80.00'),
            avg_weight_g=Decimal('100.00'),
            start_date=timezone.now().date()
        )
        
        # Create a second batch transfer with the correct field names
        second_batch_transfer = BatchTransfer.objects.create(
            source_batch=second_batch,
            transfer_type="LIFECYCLE",
            transfer_date=timezone.now().date(),
            source_count=800,
            transferred_count=800,
            source_biomass_kg=Decimal('80.00'),
            transferred_biomass_kg=Decimal('80.00'),
            source_lifecycle_stage=self.source_stage,
            destination_lifecycle_stage=self.dest_stage,
            source_container=self.container,
            destination_container=self.container
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
