"""
Tests for the batch app API viewsets.
"""
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from apps.core.test_utils import get_response_items
from decimal import Decimal
import datetime
import json

# Helper function to construct URLs for the batch app endpoints
def get_batch_url(endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for batch API endpoints"""
    base_url = '/api/v1/batch/'
    if detail:
        pk = kwargs.get('pk')
        return f'{base_url}{endpoint}/{pk}/'
    return f'{base_url}{endpoint}/'

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.infrastructure.models import (
    Geography,
    Area,
    ContainerType,
    Container
)


class SpeciesViewSetTest(APITestCase):
    """Test the Species viewset."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate user for API access
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        self.species_data = {
            'name': 'Atlantic Salmon',
            'scientific_name': 'Salmo salar',
            'description': 'Common farmed salmon species',
            'optimal_temperature_min': '4.00',
            'optimal_temperature_max': '14.00',
            'optimal_oxygen_min': '7.00',
            'optimal_ph_min': '6.50',
            'optimal_ph_max': '8.50'
        }
        self.species = Species.objects.create(**self.species_data)
        
        # Update fields with decimal values for API data
        self.species_data['optimal_temperature_min'] = '4.00'
        self.species_data['optimal_temperature_max'] = '14.00'
        self.species_data['optimal_oxygen_min'] = '7.00'
        self.species_data['optimal_ph_min'] = '6.50'
        self.species_data['optimal_ph_max'] = '8.50'

    def test_list_species(self):
        """Test listing species."""
        url = get_batch_url('species')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)

    def test_create_species(self):
        """Test creating a species."""
        url = get_batch_url('species')
        new_species_data = {
            'name': 'Rainbow Trout',
            'scientific_name': 'Oncorhynchus mykiss',
            'description': 'Freshwater species',
            'optimal_temperature_min': '10.00',
            'optimal_temperature_max': '18.00',
            'optimal_oxygen_min': '6.00',
            'optimal_ph_min': '6.00',
            'optimal_ph_max': '8.00'
        }
        response = self.client.post(url, new_species_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Species.objects.count(), 2)
        self.assertEqual(Species.objects.get(name='Rainbow Trout').scientific_name, 'Oncorhynchus mykiss')

    def test_retrieve_species(self):
        """Test retrieving a species."""
        url = get_batch_url('species', detail=True, pk=self.species.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Atlantic Salmon')

    def test_update_species(self):
        """Test updating a species."""
        url = get_batch_url('species', detail=True, pk=self.species.id)
        updated_data = {
            'name': 'Atlantic Salmon',
            'scientific_name': 'Salmo salar',
            'description': 'Updated description',
            'optimal_temperature_min': '5.00',
            'optimal_temperature_max': '15.00',
            'optimal_oxygen_min': '7.00',
            'optimal_ph_min': '6.50',
            'optimal_ph_max': '8.50'
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.species.refresh_from_db()
        self.assertEqual(self.species.description, 'Updated description')
        self.assertEqual(self.species.optimal_temperature_min, Decimal('5.00'))

    def test_delete_species(self):
        """Test deleting a species."""
        url = get_batch_url('species', detail=True, pk=self.species.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Species.objects.count(), 0)

    def test_filter_species(self):
        """Test filtering species."""
        # Create another species
        Species.objects.create(
            name='Rainbow Trout',
            scientific_name='Oncorhynchus mykiss',
            description='Freshwater species'
        )
        
        url = get_batch_url('species') + '?name=Atlantic Salmon'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Atlantic Salmon')

    def test_search_species(self):
        """Test searching species."""
        # Create another species
        Species.objects.create(
            name='Rainbow Trout',
            scientific_name='Oncorhynchus mykiss',
            description='Freshwater species'
        )
        
        url = get_batch_url('species') + '?search=salar'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Atlantic Salmon')


class BatchViewSetTest(APITestCase):
    """Test the Batch viewset."""

    def setUp(self):
        """Set up test data."""
        # Create and authenticate user for API access
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        # Create Species and Lifecycle Stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Fry',
            species=self.species,
            order=2
        )
        
        # Create Geography and Area
        self.geography = Geography.objects.create(
            name='Faroe Islands',
            description='Faroe Islands operations'
        )
        
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=62.0,
            longitude=7.0,
            max_biomass=10000
        )
        
        # Create Container Type and Container
        self.container_type = ContainerType.objects.create(
            name='Standard Tank',
            category='TANK',
            max_volume_m3=100
        )
        
        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            area=self.area,
            volume_m3=80,
            max_biomass_kg=500
        )
        
        # Create Batch
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            container=self.container,
            status='ACTIVE',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today()
        )
        
        # Batch data for API tests
        self.batch_data = {
            'batch_number': 'BATCH002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'container': self.container.id,
            'status': 'ACTIVE',
            'population_count': 5000,
            'avg_weight_g': '3.00',
            'start_date': datetime.date.today().isoformat(),
            'expected_end_date': (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            'notes': 'Test batch'
        }

    def test_list_batches(self):
        """Test listing batches."""
        url = get_batch_url('batches')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)

    def test_create_batch(self):
        """Test creating a batch."""
        url = get_batch_url('batches')
        response = self.client.post(url, self.batch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Batch.objects.count(), 2)
        new_batch = Batch.objects.get(batch_number='BATCH002')
        self.assertEqual(new_batch.population_count, 5000)
        self.assertEqual(new_batch.avg_weight_g, Decimal('3.00'))
        # Check biomass calculation: 5000 * 3g / 1000 = 15kg
        self.assertEqual(new_batch.biomass_kg, Decimal('15.00'))

    def test_retrieve_batch(self):
        """Test retrieving a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch_number'], 'BATCH001')
        self.assertEqual(response.data['species_name'], 'Atlantic Salmon')

    def test_update_batch(self):
        """Test updating a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        updated_data = {
            'batch_number': 'BATCH001',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'container': self.container.id,
            'status': 'ACTIVE',
            'population_count': 8000,
            'avg_weight_g': '3.00',
            'start_date': self.batch.start_date.isoformat(),
            'notes': 'Updated notes'
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.population_count, 8000)
        self.assertEqual(self.batch.notes, 'Updated notes')
        # Check biomass recalculation: 8000 * 3g / 1000 = 24kg
        self.assertEqual(self.batch.biomass_kg, Decimal('24.00'))

    def test_partial_update_batch(self):
        """Test partially updating a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        updated_data = {
            'population_count': 7500,
            'notes': 'Partial update'
        }
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.population_count, 7500)
        self.assertEqual(self.batch.notes, 'Partial update')
        # Check biomass recalculation: 7500 * 2.5g / 1000 = 18.75kg
        self.assertEqual(self.batch.biomass_kg, Decimal('18.75'))

    def test_delete_batch(self):
        """Test deleting a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Batch.objects.count(), 0)

    def test_filter_batches(self):
        """Test filtering batches."""
        # Create another batch
        Batch.objects.create(
            batch_number='BATCH003',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            container=self.container,
            status='COMPLETED',
            population_count=2000,
            avg_weight_g=Decimal('5.00'),
            biomass_kg=Decimal('10.00'),
            start_date=datetime.date.today(),
            actual_end_date=datetime.date.today()
        )
        
        url = get_batch_url('batches') + '?status=ACTIVE'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch_number'], 'BATCH001')
