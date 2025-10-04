"""
Integration tests for EggProduction ViewSet actions.

Tests that produce_internal and acquire_external actions properly delegate
to EggManagementService with full validation.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from apps.broodstock.models import (
    BroodstockFish, BreedingPlan, BreedingPair, 
    EggProduction, EggSupplier, ExternalEggBatch
)
from apps.infrastructure.models import (
    Geography, FreshwaterStation, Hall, 
    ContainerType, Container
)
from apps.batch.models import Species

User = get_user_model()


class EggProductionActionsTest(TestCase):
    """Test EggProduction ViewSet actions delegate to service properly."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create infrastructure
        self.geography = Geography.objects.create(name='Test Region')
        self.station = FreshwaterStation.objects.create(
            name='Test Station',
            geography=self.geography,
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060')
        )
        self.hall = Hall.objects.create(
            name='Test Hall',
            freshwater_station=self.station
        )
        container_type = ContainerType.objects.create(
            name='Broodstock Tank',
            category='TANK',
            max_volume_m3=Decimal('100.0')
        )
        self.container = Container.objects.create(
            name='Test Container',
            container_type=container_type,
            hall=self.hall,
            volume_m3=Decimal('50.0'),
            max_biomass_kg=Decimal('500.0')
        )
        
        # Create species
        self.species = Species.objects.create(
            name='Atlantic Salmon',
            scientific_name='Salmo salar'
        )
        
        # Create broodstock fish
        self.male_fish = BroodstockFish.objects.create(
            container=self.container,
            health_status='healthy'
        )
        self.female_fish = BroodstockFish.objects.create(
            container=self.container,
            health_status='healthy'
        )
        
        # Create breeding plan (active - based on date range)
        now = timezone.now()
        self.plan = BreedingPlan.objects.create(
            name='Test Plan 2025',
            start_date=now - timedelta(days=1),  # Started yesterday
            end_date=now + timedelta(days=90),  # Ends in 90 days
            created_by=self.user
        )
        
        # Create breeding pair
        self.pair = BreedingPair.objects.create(
            plan=self.plan,
            male_fish=self.male_fish,
            female_fish=self.female_fish,
            pairing_date=date.today()
        )
        
        # Create egg supplier
        self.supplier = EggSupplier.objects.create(
            name='External Supplier',
            contact_details='supplier@example.com'
        )
    
    def test_produce_internal_success(self):
        """Test successful internal egg production via action."""
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': self.pair.id,
            'egg_count': 10000,
            'destination_station_id': self.station.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('egg_batch_id', response.data)
        self.assertTrue(response.data['egg_batch_id'].startswith('EB-INT-'))
        self.assertEqual(response.data['egg_count'], 10000)
        self.assertEqual(response.data['source_type'], 'internal')
        
        # Verify progeny count updated
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.progeny_count, 10000)
        
        # Verify egg production created
        self.assertEqual(EggProduction.objects.count(), 1)
    
    def test_produce_internal_inactive_plan_rejected(self):
        """Test that inactive breeding plans are rejected."""
        # Make plan inactive by setting end_date in the past
        past_date = timezone.now() - timedelta(days=30)
        self.plan.start_date = past_date - timedelta(days=10)
        self.plan.end_date = past_date  # Ended in the past
        self.plan.save()
        
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': self.pair.id,
            'egg_count': 10000
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('not active', response.data['error'])
        
        # Verify no egg production created
        self.assertEqual(EggProduction.objects.count(), 0)
        
        # Verify progeny count not updated
        self.pair.refresh_from_db()
        self.assertIsNone(self.pair.progeny_count)
    
    def test_produce_internal_unhealthy_male_rejected(self):
        """Test that unhealthy male fish are rejected."""
        self.male_fish.health_status = 'sick'
        self.male_fish.save()
        
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': self.pair.id,
            'egg_count': 10000
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('no longer healthy', response.data['error'])
        
        # Verify no egg production created
        self.assertEqual(EggProduction.objects.count(), 0)
    
    def test_produce_internal_unhealthy_female_rejected(self):
        """Test that unhealthy female fish are rejected."""
        self.female_fish.health_status = 'sick'
        self.female_fish.save()
        
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': self.pair.id,
            'egg_count': 10000
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('no longer healthy', response.data['error'])
        
        # Verify no egg production created
        self.assertEqual(EggProduction.objects.count(), 0)
    
    def test_produce_internal_invalid_pair_id(self):
        """Test that invalid pair ID returns 404."""
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': 99999,
            'egg_count': 10000
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('not found', response.data['error'])
    
    def test_produce_internal_missing_required_fields(self):
        """Test that missing required fields return 400."""
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        
        # Missing egg_count
        response = self.client.post(url, {'pair_id': self.pair.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing pair_id
        response = self.client.post(url, {'egg_count': 10000}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_produce_internal_negative_egg_count_rejected(self):
        """Test that negative egg count is rejected."""
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        data = {
            'pair_id': self.pair.id,
            'egg_count': -100
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('positive', response.data['error'])
    
    def test_produce_internal_progeny_count_accumulates(self):
        """Test that progeny count accumulates across multiple productions."""
        url = '/api/v1/broodstock/egg-productions/produce_internal/'
        
        # First production
        data = {'pair_id': self.pair.id, 'egg_count': 10000}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.progeny_count, 10000)
        
        # Second production
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.progeny_count, 20000)
    
    def test_acquire_external_success(self):
        """Test successful external egg acquisition via action."""
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        data = {
            'supplier_id': self.supplier.id,
            'batch_number': 'SUPP-2025-001',
            'egg_count': 15000,
            'provenance_data': 'Farm X, Location Y',
            'destination_station_id': self.station.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('egg_batch_id', response.data)
        self.assertTrue(response.data['egg_batch_id'].startswith('EB-EXT-'))
        self.assertEqual(response.data['egg_count'], 15000)
        self.assertEqual(response.data['source_type'], 'external')
        
        # Verify egg production and external batch created
        self.assertEqual(EggProduction.objects.count(), 1)
        self.assertEqual(ExternalEggBatch.objects.count(), 1)
        
        # Verify external batch details
        external_batch = ExternalEggBatch.objects.first()
        self.assertEqual(external_batch.supplier, self.supplier)
        self.assertEqual(external_batch.batch_number, 'SUPP-2025-001')
        self.assertEqual(external_batch.provenance_data, 'Farm X, Location Y')
    
    def test_acquire_external_duplicate_batch_rejected(self):
        """Test that duplicate supplier batch numbers are rejected."""
        # Create first batch
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        data = {
            'supplier_id': self.supplier.id,
            'batch_number': 'SUPP-2025-001',
            'egg_count': 15000
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Try to create duplicate
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('already exists', response.data['error'])
        
        # Verify only one external batch exists
        self.assertEqual(ExternalEggBatch.objects.count(), 1)
    
    def test_acquire_external_different_supplier_same_batch_number_allowed(self):
        """Test that same batch number from different suppliers is allowed."""
        # Create another supplier
        supplier2 = EggSupplier.objects.create(
            name='Another Supplier',
            contact_details='another@example.com'
        )
        
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        
        # First supplier with batch number
        data1 = {
            'supplier_id': self.supplier.id,
            'batch_number': 'BATCH-001',
            'egg_count': 10000
        }
        response = self.client.post(url, data1, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Second supplier with same batch number (should work)
        data2 = {
            'supplier_id': supplier2.id,
            'batch_number': 'BATCH-001',
            'egg_count': 10000
        }
        response = self.client.post(url, data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify both batches exist
        self.assertEqual(ExternalEggBatch.objects.count(), 2)
    
    def test_acquire_external_invalid_supplier_id(self):
        """Test that invalid supplier ID returns 404."""
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        data = {
            'supplier_id': 99999,
            'batch_number': 'BATCH-001',
            'egg_count': 10000
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('not found', response.data['error'])
    
    def test_acquire_external_missing_required_fields(self):
        """Test that missing required fields return 400."""
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        
        # Missing egg_count
        response = self.client.post(
            url, 
            {'supplier_id': self.supplier.id, 'batch_number': 'BATCH-001'}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing batch_number
        response = self.client.post(
            url, 
            {'supplier_id': self.supplier.id, 'egg_count': 10000}, 
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_acquire_external_negative_egg_count_rejected(self):
        """Test that negative egg count is rejected."""
        url = '/api/v1/broodstock/egg-productions/acquire_external/'
        data = {
            'supplier_id': self.supplier.id,
            'batch_number': 'BATCH-001',
            'egg_count': -100
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('positive', response.data['error'])
    
    def test_egg_batch_id_uniqueness(self):
        """Test that generated egg batch IDs are unique."""
        url_internal = '/api/v1/broodstock/egg-productions/produce_internal/'
        url_external = '/api/v1/broodstock/egg-productions/acquire_external/'
        
        # Create internal production
        data_internal = {
            'pair_id': self.pair.id,
            'egg_count': 10000
        }
        response1 = self.client.post(url_internal, data_internal, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        batch_id_1 = response1.data['egg_batch_id']
        
        # Create external acquisition
        data_external = {
            'supplier_id': self.supplier.id,
            'batch_number': 'BATCH-001',
            'egg_count': 15000
        }
        response2 = self.client.post(url_external, data_external, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        batch_id_2 = response2.data['egg_batch_id']
        
        # Verify unique IDs
        self.assertNotEqual(batch_id_1, batch_id_2)
        self.assertTrue(batch_id_1.startswith('EB-INT-'))
        self.assertTrue(batch_id_2.startswith('EB-EXT-'))

