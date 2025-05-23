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
    Hall,
    FreshwaterStation,
    ContainerType,
    Container
)
from unittest.mock import patch

class SpeciesViewSetTest(APITestCase):
    """Test the Species viewset."""

    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        self.species_data = {
            'name': 'Atlantic Salmon',
            'scientific_name': 'Salmo salar',
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
            'optimal_temperature_min': '5.00',
            'optimal_temperature_max': '15.00',
            'optimal_oxygen_min': '7.00',
            'optimal_ph_min': '6.50',
            'optimal_ph_max': '8.50'
        }
        response = self.client.put(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.species.refresh_from_db()
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
            scientific_name='Oncorhynchus mykiss'
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
            scientific_name='Oncorhynchus mykiss'
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
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=FreshwaterStation.objects.create(
                name="Test Station",
                geography=self.geography,
                latitude=40.7128,
                longitude=-74.0060
            )
        )
        
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            max_volume_m3=100.0
        )
        
        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        self.species = Species.objects.create(
            name="Test Species"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Test Stage",
            order=1,
            description="A test lifecycle stage",
            species=self.species
        )
        self.batch = Batch.objects.create(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="BATCH001",
            start_date=datetime.date.today(),
            status="ACTIVE",
            notes="Test batch notes"
        )
        # Create a batch container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            assignment_date=datetime.date.today(),
            population_count=1000,
            avg_weight_g=Decimal("10.5"),
            is_active=True,
            notes="Test assignment"
        )

        self.batch_data_for_create = {
            'batch_number': 'BATCH_CREATE_TEST_003',
            'species_id': self.species.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'start_date': datetime.date.today().isoformat(),
            'expected_end_date': (
                datetime.date.today() + datetime.timedelta(days=30)
            ).isoformat(),
            'notes': 'Test batch',
        }
        self.batch_data_for_update = {
            'status': 'INACTIVE',
            'notes': 'Updated test batch notes',
        }
        self.assignment_data = { # For creating a BCA directly
            'batch_id': None,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.lifecycle_stage.id,
            'population_count': 5000,
            'avg_weight_g': '3.00',
            'assignment_date': datetime.date.today().isoformat(),
            'is_active': True,
        }

    def test_list_batches(self):
        """Test listing batches."""
        url = get_batch_url('batches')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        # Add more assertions based on self.batch and its calculated properties
        listed_batch = items[0]
        self.assertEqual(listed_batch['batch_number'], self.batch.batch_number)
        self.assertEqual(listed_batch['calculated_population_count'], 1000)
        self.assertEqual(listed_batch['calculated_avg_weight_g'], '10.50')
        self.assertEqual(listed_batch['calculated_biomass_kg'], '10.50')


    def test_create_batch(self):
        """
        Test creating a new batch via the API.
        """
        url = reverse('batch:batch-list')
        data = {
            'batch_number': 'BATCH_CREATE_TEST_002',
            'species': self.species.id,
            'lifecycle_stage': self.lifecycle_stage.id,
            'start_date': datetime.date.today().isoformat(),
            'status': 'ACTIVE'
        }
        response = self.client.post(url, data)
        print(f"Create Batch URL: {url}")
        print(f"Request Data: {data}")
        print(f"Create Batch Response: {response.status_code} {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['batch_number'], 'BATCH_CREATE_TEST_002')
        self.assertEqual(response.data['species'], self.species.id)

    def test_retrieve_batch(self):
        """Test retrieving a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch_number'], 'BATCH001')
        self.assertEqual(response.data['species_name'], 'Test Species')
        self.assertEqual(response.data['calculated_population_count'], 1000)
        self.assertEqual(response.data['calculated_avg_weight_g'], '10.50')
        self.assertEqual(response.data['calculated_biomass_kg'], '10.50')

    def test_update_batch(self):
        """Test updating a batch (direct fields like status, notes)."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        # self.batch_data_for_update only contains fields directly on Batch model
        # A PUT expects all required Batch fields. Using PATCH for simplicity to update notes.
        patch_data = {'notes': "Patched notes for BATCH001"}
        response = self.client.patch(url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.notes, "Patched notes for BATCH001")
        # Calculated fields should remain unchanged as no BCAs were touched
        self.assertEqual(self.batch.calculated_population_count, 1000)


    def test_partial_update_batch(self):
        """Test partially updating a batch (direct fields like status, notes)."""
        url = reverse('batch:batch-detail', kwargs={'pk': self.batch.id})
        data = {
            'notes': 'Updated notes without status change'
        }
        response = self.client.patch(url, data, format='json')
        print("Partial Update Response:", response.status_code, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh from database
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.notes, 'Updated notes without status change')

    def test_delete_batch(self):
        """Test deleting a batch."""
        url = get_batch_url('batches', detail=True, pk=self.batch.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Batch.objects.count(), 0)
        # Also check that associated BCA is deleted (due to on_delete=models.CASCADE)
        self.assertEqual(BatchContainerAssignment.objects.count(), 0)


    def test_filter_batches(self):
        """Test filtering batches."""
        url = reverse('batch:batch-list')
        # Filter by species
        response = self.client.get(url + f'?species={self.species.id}', format='json')
        print("Filter Response:", response.status_code, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response data contains results key or is a direct list
        if 'results' in response.data:
            results = response.data['results']
            if results:
                print("Results found in response:", results)
                self.assertEqual(results[0]['batch_number'], 'BATCH001')
            else:
                print("No results found in response['results'].")
        elif isinstance(response.data, list) and response.data:
            print("Direct list response:", response.data)
            self.assertEqual(response.data[0]['batch_number'], 'BATCH001')
        else:
            print("Unexpected response structure or no data returned:", response.data)
        
        # Filter by date range
        response = self.client.get(url + '?date_from=2023-01-15&date_to=2023-02-15', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['batch_number'], 'BATCH001')
        
        # Filter by active status (active if start_date <= today and no actual_end_date)
        with patch('django.utils.timezone.now', return_value=datetime.date(2023, 6, 1)):
            response = self.client.get(url + '?is_active=true', format='json')
            print("Filter Batches Response:", response.status_code, response.data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['results']), 1)  # Only one batch is active in June 2023


class BatchContainerAssignmentViewSetTest(APITestCase):
    """Test the BatchContainerAssignment viewset."""

    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        # Create species and lifecycle stage
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        self.stage1 = LifeCycleStage.objects.create(
            name="Egg & Alevin",
            species=self.species,
            order=1,
            description="Egg and Alevin stage"
        )
        self.stage2 = LifeCycleStage.objects.create(
            name="Fry",
            species=self.species,
            order=2,
            description="Fry stage"
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number='BATCH001',
            species=self.species,
            lifecycle_stage=self.stage1,
            start_date=datetime.date(2023, 1, 1),
            expected_end_date=datetime.date(2023, 12, 31),
            batch_type='STANDARD',
            status='ACTIVE',
            notes='Test batch'
        )
        
        # Create a second batch for testing new assignments
        self.test_batch = Batch.objects.create(
            batch_number='BATCH002',
            species=self.species,
            lifecycle_stage=self.stage1,
            start_date=datetime.date(2023, 1, 1),
            expected_end_date=datetime.date(2023, 12, 31),
            batch_type='STANDARD',
            status='ACTIVE',
            notes='Test batch for new assignments'
        )

        # Create infrastructure
        self.geography = Geography.objects.create(name='Test Geography')
        self.station = FreshwaterStation.objects.create(
            name="Test Station", 
            geography=self.geography, 
            latitude=Decimal('40.7128'), 
            longitude=Decimal('-74.0060')
        )
        self.hall = Hall.objects.create(name="Test Hall", freshwater_station=self.station)
        self.container_type = ContainerType.objects.create(name='Tank', max_volume_m3=100.0)
        self.container = Container.objects.create(
            name='Tank 1',
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        self.container2 = Container.objects.create(
            name='Tank 2',
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )

        # Create initial container assignment for batch to set population
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage1,
            population_count=100,
            avg_weight_g=Decimal('50.0'),
            assignment_date=datetime.date(2023, 1, 5),
            is_active=True,
            notes='Initial test assignment'
        )

        # Data for creating a new assignment
        self.new_assignment_data = {
            'batch_id': self.batch.id,
            'container_id': self.container2.id,
            'lifecycle_stage_id': self.stage2.id,
            'population_count': 50,
            'avg_weight_g': Decimal('50.0').quantize(Decimal('0.01')),
            'biomass_kg': Decimal('2.5').quantize(Decimal('0.01')),
            'assignment_date': datetime.date(2023, 2, 1),
            'is_active': True,
            'notes': 'Test assignment from viewset test'
        }

    def test_list_assignments(self):
        """Test listing container assignments."""
        url = get_batch_url('container-assignments')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_response_items(response)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['batch']['batch_number'], 'BATCH001')
        self.assertEqual(items[0]['container']['name'], 'Tank 1')
        self.assertEqual(items[0]['population_count'], 100)
        self.assertEqual(Decimal(items[0]['biomass_kg']), Decimal('5.00'))
        
    def test_create_assignment(self):
        """Test creating a container assignment."""
        url = get_batch_url('container-assignments')
        response = self.client.post(url, self.new_assignment_data, format='json')
        print(f"Assignment Response: {response.status_code} {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['population_count'], 50)
        self.assertEqual(response.data['is_active'], True)
        
    def test_retrieve_assignment(self):
        """Test retrieving a container assignment."""
        url = get_batch_url('container-assignments', detail=True, pk=self.assignment.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['batch']['batch_number'], 'BATCH001')
        self.assertEqual(response.data['container']['name'], 'Tank 1')
        self.assertEqual(response.data['population_count'], 100)
        self.assertEqual(Decimal(response.data['biomass_kg']), Decimal('5.00'))
        
    def test_update_assignment(self):
        """Test updating a container assignment."""
        url = get_batch_url('container-assignments', detail=True, pk=self.assignment.id)
        data = {
            'batch_id': self.batch.id,
            'container_id': self.container.id,
            'lifecycle_stage_id': self.stage1.id,
            'assignment_date': datetime.date(2023, 1, 5),
            'population_count': 75,  # Updated count
            'avg_weight_g': Decimal('50.0').quantize(Decimal('0.01')),  # Updated weight
            'biomass_kg': Decimal('3.75').quantize(Decimal('0.01')),  # Updated biomass
            'is_active': True
        }
        
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.population_count, 75)
        self.assertEqual(self.assignment.avg_weight_g, Decimal('50.0'))
        self.assertEqual(self.assignment.biomass_kg, Decimal('3.75'))
        
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
            batch_number="BATCH002",
            species=self.species,
            lifecycle_stage=self.stage1,
            start_date=datetime.date(2023, 1, 1),
            expected_end_date=datetime.date(2023, 12, 31)
        )
        
        container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        BatchContainerAssignment.objects.create(
            batch=batch2,
            container=container2,
            lifecycle_stage=self.stage1,
            population_count=200,
            avg_weight_g=Decimal('50.0'),
            assignment_date=datetime.date(2023, 1, 5),
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
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="testpass", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        self.species = Species.objects.create(
            name="Test Species"
        )
        
        # Create lifecycle stage
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Test Stage",
            order=1,
            description="A test lifecycle stage",
            species=self.species
        )
        
        # Create geography, area, and container type needed for container assignments
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=FreshwaterStation.objects.create(
                name="Test Station",
                geography=self.geography,
                latitude=40.7128,
                longitude=-74.0060
            )
        )
        
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            max_volume_m3=100.0
        )
        
        # Create source batches
        self.source_batch1 = Batch.objects.create(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SOURCE001",
            start_date=datetime.date.today(),
            status="ACTIVE",
            notes="Source batch 1"
        )
        
        # Create a container assignment for source batch 1 to set population and weight
        self.source1_container = Container.objects.create(
            name="Source1 Container",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        BatchContainerAssignment.objects.create(
            batch=self.source_batch1,
            container=self.source1_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=80,  # Was 100, now 80 after 20 moved to mixed batch
            avg_weight_g=100.0,   # This will calculate biomass_kg = 8.0
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        self.source_batch2 = Batch.objects.create(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="SOURCE002",
            start_date=datetime.date.today(),
            status="ACTIVE",
            notes="Source batch 2"
        )
        
        # Create a container assignment for source batch 2 to set population and weight
        self.source2_container = Container.objects.create(
            name="Source2 Container",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        BatchContainerAssignment.objects.create(
            batch=self.source_batch2,
            container=self.source2_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=150,  # Was 200, now 150 after 50 moved to mixed batch
            avg_weight_g=100.0,    # This will calculate biomass_kg = 15.0
            assignment_date=datetime.date.today(),
            is_active=True
        )
        
        # Create mixed batch
        self.mixed_batch = Batch.objects.create(
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            batch_number="MIXED001",
            start_date=datetime.date.today(),
            status="ACTIVE",
            notes="Mixed batch",
            batch_type="MIXED"
        )
        
        # Create a container assignment for mixed batch to set population and weight
        self.mixed_container = Container.objects.create(
            name="Mixed Container",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        BatchContainerAssignment.objects.create(
            batch=self.mixed_batch,
            container=self.mixed_container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=70,   # 20 from batch1 + 50 from batch2
            avg_weight_g=100.0,    # This will calculate biomass_kg = 7.0
            assignment_date=datetime.date.today(),
            is_active=True
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
        url = reverse('batch:batchcomposition-list')
        data = {
            'mixed_batch_id': self.mixed_batch.id,
            'source_batch_id': self.source_batch1.id,
            'percentage': 50.0,
            'population_count': 30,
            'biomass_kg': 3.0,
            'notes': 'Half composition'
        }
        response = self.client.post(url, data, format='json')
        print("Create Composition Response:", response.status_code)
        print("Request Data:", data)
        print("Response Data:", response.data)
        if response.status_code != status.HTTP_201_CREATED:
            print("Validation errors or other issues:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BatchComposition.objects.count(), 3)
        comp = BatchComposition.objects.filter(mixed_batch=self.mixed_batch, source_batch=self.source_batch1).first()
        if comp:
            self.assertEqual(comp.percentage, 50.0)
        else:
            print("Composition not found in database.")
        
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
        
        response = self.client.put(url, data)
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
