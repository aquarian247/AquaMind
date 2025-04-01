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

from apps.batch.tests.api.test_helpers import get_api_url

# Helper function to construct URLs for the batch app endpoints
def get_batch_url(endpoint, detail=False, **kwargs):
    """Helper function to construct URLs for batch API endpoints"""
    return get_api_url('batch', endpoint, detail, **kwargs)

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    BatchComposition,
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
            status='ACTIVE',
            batch_type='STANDARD',
            population_count=10000,
            avg_weight_g=Decimal('2.50'),
            biomass_kg=Decimal('25.00'),
            start_date=datetime.date.today()
        )
        
        # Create BatchContainerAssignment
        from apps.batch.models import BatchContainerAssignment
        self.batch_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=10000,
            biomass_kg=Decimal('25.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # Batch data for API tests
        self.batch_data = {
            'batch_number': 'BATCH002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'population_count': 5000,
            'avg_weight_g': '3.00',
            'start_date': datetime.date.today().isoformat(),
            'expected_end_date': (datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            'notes': 'Test batch'
        }
        
        # Container assignment data
        self.assignment_data = {
            'batch_id': None,  # Will be set after batch creation
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 5000,
            'biomass_kg': '15.00',
            'assignment_date': datetime.date.today().isoformat(),
            'is_active': True
        }

    def test_list_batches(self):
        """Test listing batches."""
        url = get_batch_url('batches')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)

    def test_create_batch(self):
        """Test creating a batch and assigning it to a container."""
        # Create batch
        url = get_batch_url('batches')
        response = self.client.post(url, self.batch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Batch.objects.count(), 2)
        new_batch = Batch.objects.get(batch_number='BATCH002')
        self.assertEqual(new_batch.population_count, 5000)
        self.assertEqual(new_batch.avg_weight_g, Decimal('3.00'))
        # Check biomass calculation: 5000 * 3g / 1000 = 15kg
        self.assertEqual(new_batch.biomass_kg, Decimal('15.00'))
        
        # Now create container assignment
        url = get_batch_url('container-assignments')
        self.assignment_data['batch_id'] = new_batch.id
        response = self.client.post(url, self.assignment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the assignment was created
        from apps.batch.models import BatchContainerAssignment
        assignments = BatchContainerAssignment.objects.filter(batch=new_batch)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments[0].population_count, 5000)
        self.assertEqual(assignments[0].biomass_kg, Decimal('15.00'))

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
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
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
        
        # The container assignment should be updated separately
        url = get_batch_url('container-assignments', detail=True, pk=self.batch_assignment.id)
        assignment_update = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'population_count': 8000,
            'biomass_kg': '24.00',
            'is_active': True
        }
        response = self.client.patch(url, assignment_update, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
        batch = Batch.objects.create(
            batch_number='BATCH003',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            status='COMPLETED',
            batch_type='STANDARD',
            population_count=2000,
            avg_weight_g=Decimal('5.00'),
            biomass_kg=Decimal('10.00'),
            start_date=datetime.date.today(),
            actual_end_date=datetime.date.today()
        )
        
        # Create BatchContainerAssignment for the new batch
        from apps.batch.models import BatchContainerAssignment
        BatchContainerAssignment.objects.create(
            batch=batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2000,
            biomass_kg=Decimal('10.00'),
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        url = get_batch_url('batches') + '?status=ACTIVE'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch_number'], 'BATCH001')


class BatchContainerAssignmentViewSetTest(APITestCase):
    """Test the BatchContainerAssignment viewset."""

    def setUp(self):
        # Create user
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create geography/area
        self.geography = Geography.objects.create(
            name='Test Geography',
        )
        self.area = Area.objects.create(
            name='Test Area',
            geography=self.geography,
            latitude=10.0,
            longitude=10.0,
            max_biomass=1000.0
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name='Test Container Type',
            category='TANK',
            max_volume_m3=10.0
        )
        self.container = Container.objects.create(
            name='Test Container',
            container_type=self.container_type,
            area=self.area,
            volume_m3=8.0,
            max_biomass_kg=100.0,
            active=True
        )
        
        # Create species
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus testus'
        )
        
        # Create lifecycle stage
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Test Stage',
            species=self.species,
            order=1
        )
        
        # Create batch
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=150,  # Increased to allow for multiple assignments
            biomass_kg=15.0,       # Increased proportionally 
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        # Create container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            biomass_kg=10.0,
            assignment_date=datetime.date.today(),
            is_active=True
        )

    def test_list_assignments(self):
        """Test listing container assignments."""
        url = get_batch_url('container-assignments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch']['batch_number'], 'BATCH001')
        self.assertEqual(items[0]['container']['name'], 'Test Container')
        self.assertEqual(items[0]['population_count'], 100)
        self.assertEqual(Decimal(items[0]['biomass_kg']), Decimal('10.0'))
        
    def test_create_assignment(self):
        """Test creating a container assignment."""
        url = get_batch_url('container-assignments')
        
        # Create another container for testing
        container2 = Container.objects.create(
            name='Test Container 2',
            container_type=self.container_type,
            area=self.area,
            volume_m3=8.0,
            max_biomass_kg=100.0,
            active=True
        )
        
        data = {
            'batch_id': self.batch.id,
            'container_id': container2.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 50,
            'biomass_kg': 5.0,
            'assignment_date': datetime.date.today().isoformat(),
            'is_active': True
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the assignment was created in the database
        self.assertEqual(BatchContainerAssignment.objects.count(), 2)
        new_assignment = BatchContainerAssignment.objects.get(container=container2)
        self.assertEqual(new_assignment.population_count, 50)
        self.assertEqual(new_assignment.biomass_kg, Decimal('5.0'))
        
    def test_retrieve_assignment(self):
        """Test retrieving a container assignment."""
        url = get_batch_url('container-assignments', detail=True, pk=self.assignment.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['batch_number'], 'BATCH001')
        self.assertEqual(response.data['container']['name'], 'Test Container')
        self.assertEqual(response.data['population_count'], 100)
        self.assertEqual(Decimal(response.data['biomass_kg']), Decimal('10.0'))
        
    def test_update_assignment(self):
        """Test updating a container assignment."""
        url = get_batch_url('container-assignments', detail=True, pk=self.assignment.id)
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 75,  # Updated count
            'biomass_kg': 7.5,       # Updated biomass
            'assignment_date': datetime.date.today().isoformat(),
            'is_active': True
        }
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, 75)
        self.assertEqual(self.assignment.biomass_kg, Decimal('7.5'))
        
    def test_delete_assignment(self):
        """Test deleting a container assignment."""
        url = get_batch_url('container-assignments', detail=True, pk=self.assignment.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BatchContainerAssignment.objects.count(), 0)

    def test_filter_assignments(self):
        """Test filtering container assignments."""
        # Create a second batch and assignment for filtering
        batch2 = Batch.objects.create(
            batch_number='BATCH002',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=200,
            biomass_kg=20.0,
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        container2 = Container.objects.create(
            name='Test Container 2',
            container_type=self.container_type,
            area=self.area,
            volume_m3=8.0,
            max_biomass_kg=100.0,
            active=True
        )
        
        BatchContainerAssignment.objects.create(
            batch=batch2,
            container=container2,
            lifecycle_stage=self.lifecycle_stage,
            population_count=200,
            biomass_kg=20.0,
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # Filter by batch
        url = f"{get_batch_url('container-assignments')}?batch={self.batch.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch']['batch_number'], 'BATCH001')
        
        # Filter by container
        url = f"{get_batch_url('container-assignments')}?container={container2.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch']['batch_number'], 'BATCH002')
        
        # Filter by is_active
        url = f"{get_batch_url('container-assignments')}?is_active=true"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 2)


class BatchCompositionViewSetTest(APITestCase):
    """Test the BatchComposition viewset."""

    def setUp(self):
        # Create user
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create species
        self.species = Species.objects.create(
            name='Test Species',
            scientific_name='Testus testus'
        )
        
        # Create lifecycle stage
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name='Test Stage',
            species=self.species,
            order=1
        )
        
        # Create source batches
        self.source_batch1 = Batch.objects.create(
            batch_number='SOURCE001',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=80,  # Was 100, now 80 after 20 moved to mixed batch
            biomass_kg=8.0,       # Was 10, now 8 after 2 moved to mixed batch
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        self.source_batch2 = Batch.objects.create(
            batch_number='SOURCE002',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=150,  # Was 200, now 150 after 50 moved to mixed batch
            biomass_kg=15.0,       # Was 20, now 15 after 5 moved to mixed batch
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        # Create mixed batch
        self.mixed_batch = Batch.objects.create(
            batch_number='MIXED001',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=70,   # 20 from batch1 + 50 from batch2
            biomass_kg=7.0,        # 2 from batch1 + 5 from batch2
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='MIXED'
        )
        
        # Create batch compositions
        self.composition1 = BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.source_batch1,
            percentage=Decimal('28.57'),  # 20 fish out of 70 total
            population_count=20,
            biomass_kg=2.0
        )
        
        self.composition2 = BatchComposition.objects.create(
            mixed_batch=self.mixed_batch,
            source_batch=self.source_batch2,
            percentage=Decimal('71.43'),  # 50 fish out of 70 total
            population_count=50,
            biomass_kg=5.0
        )

    def test_list_compositions(self):
        """Test listing batch compositions."""
        url = get_batch_url('batch-compositions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 2)
        
        # Sort by percentage descending
        items = sorted(items, key=lambda x: Decimal(x['percentage']), reverse=True)
        
        self.assertEqual(items[0]['source_batch']['batch_number'], 'SOURCE002')
        self.assertEqual(Decimal(items[0]['percentage']), Decimal('71.43'))
        self.assertEqual(items[0]['population_count'], 50)
        self.assertEqual(Decimal(items[0]['biomass_kg']), Decimal('5.0'))
        
        self.assertEqual(items[1]['source_batch']['batch_number'], 'SOURCE001')
        self.assertEqual(Decimal(items[1]['percentage']), Decimal('28.57'))
        self.assertEqual(items[1]['population_count'], 20)
        self.assertEqual(Decimal(items[1]['biomass_kg']), Decimal('2.0'))
        
    def test_create_composition(self):
        """Test creating a batch composition."""
        # Create another source batch
        source_batch3 = Batch.objects.create(
            batch_number='SOURCE003',
            status='ACTIVE',
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=100,
            biomass_kg=10.0,
            avg_weight_g=100.0,
            start_date=datetime.date.today(),
            batch_type='STANDARD'
        )
        
        url = get_batch_url('batch-compositions')
        data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': source_batch3.id,
            'percentage': 10.0,  # Adding a small percentage to existing mixed batch
            'population_count': 10,
            'biomass_kg': 1.0
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that the composition was created in the database
        self.assertEqual(BatchComposition.objects.count(), 3)
        new_composition = BatchComposition.objects.get(source_batch=source_batch3)
        self.assertEqual(new_composition.population_count, 10)
        self.assertEqual(new_composition.biomass_kg, Decimal('1.0'))
        
    def test_retrieve_composition(self):
        """Test retrieving a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mixed_batch']['batch_number'], 'MIXED001')
        self.assertEqual(response.data['source_batch']['batch_number'], 'SOURCE001')
        self.assertEqual(Decimal(response.data['percentage']), Decimal('28.57'))
        self.assertEqual(response.data['population_count'], 20)
        self.assertEqual(Decimal(response.data['biomass_kg']), Decimal('2.0'))
        
    def test_update_composition(self):
        """Test updating a batch composition."""
        url = get_batch_url('batch-compositions', detail=True, pk=self.composition1.id)
        data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch1.id,
            'percentage': 35.0,      # Updated percentage
            'population_count': 25,   # Updated count
            'biomass_kg': 2.5        # Updated biomass
        }
        
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.composition1.refresh_from_db()
        self.assertEqual(self.composition1.population_count, 25)
        self.assertEqual(self.composition1.biomass_kg, Decimal('2.5'))
        self.assertEqual(self.composition1.percentage, Decimal('35.0'))
        
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
        items = get_response_items(response)
        self.assertEqual(len(items), 2)
        
        # Filter by source_batch
        url = f"{get_batch_url('batch-compositions')}?source_batch={self.source_batch1.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source_batch']['batch_number'], 'SOURCE001')
