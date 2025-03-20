"""
Tests for the batch analytics API endpoints.

This module tests the analytics functionality of the batch API, including:
- Growth analysis endpoint
- Performance metrics endpoint
- Batch comparison endpoint
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    GrowthSample,
    MortalityEvent,
    BatchContainerAssignment
)
from apps.infrastructure.models import Container, Hall, Geography, FreshwaterStation

from apps.batch.tests.api.test_helpers import get_api_url


class BatchAnalyticsTestCase(APITestCase):
    """Test case for batch analytics endpoints."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user and authentication token
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create required related objects
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
            description="A common farmed fish species",
            optimal_temperature_min=7.0,
            optimal_temperature_max=14.0
        )
        
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Juvenile",
            species=self.species,
            order=2,  # After fry, before smolt
            description="Young fish",
            expected_weight_min_g=10.0,
            expected_weight_max_g=80.0
        )
        
        # Create infrastructure hierarchy
        self.geography = Geography.objects.create(
            name="Test Region",
            description="Test region description"
        )
        
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            station_type="FRESHWATER",
            geography=self.geography,
            latitude=60.0,
            longitude=5.0
        )
        
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station,
            description="Test hall description"
        )
        
        # Create container types and containers
        from apps.infrastructure.models import ContainerType
        self.container_type = ContainerType.objects.create(
            name="Standard Tank",
            category="TANK",
            max_volume_m3=20.0
        )
        
        self.container = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=10.0,
            max_biomass_kg=500.0,
            active=True
        )
        
        self.container2 = Container.objects.create(
            name="Tank 2",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=15.0,
            max_biomass_kg=800.0,
            active=True
        )
        
        # Create batch with initial data
        self.batch = Batch.objects.create(
            batch_number="B001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1000,
            biomass_kg=Decimal('100.00'),
            start_date=date.today() - timedelta(days=30),
            status="active"
        )
        
        # Create a second batch for comparison
        self.batch2 = Batch.objects.create(
            batch_number="B002",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=1500,
            biomass_kg=Decimal('120.00'),
            start_date=date.today() - timedelta(days=20),
            status="active"
        )
        
        # Assign batches to containers
        self.assignment1 = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            assignment_date=date.today() - timedelta(days=30),
            population_count=1000,
            biomass_kg=Decimal('100.00'),
            is_active=True
        )
        
        self.assignment2 = BatchContainerAssignment.objects.create(
            batch=self.batch2,
            container=self.container2,
            assignment_date=date.today() - timedelta(days=20),
            population_count=1500,
            biomass_kg=Decimal('120.00'),
            is_active=True
        )
        
        # Create growth samples for the first batch
        self.growth_sample1 = GrowthSample.objects.create(
            batch=self.batch,
            sample_date=date.today() - timedelta(days=30),
            sample_size=50,
            avg_weight_g=Decimal('100.00'),
            avg_length_cm=Decimal('12.50'),
            condition_factor=Decimal('1.05')
        )
        
        self.growth_sample2 = GrowthSample.objects.create(
            batch=self.batch,
            sample_date=date.today() - timedelta(days=20),
            sample_size=50,
            avg_weight_g=Decimal('120.00'),
            avg_length_cm=Decimal('13.80'),
            condition_factor=Decimal('1.08')
        )
        
        self.growth_sample3 = GrowthSample.objects.create(
            batch=self.batch,
            sample_date=date.today() - timedelta(days=10),
            sample_size=50,
            avg_weight_g=Decimal('140.00'),
            avg_length_cm=Decimal('15.00'),
            condition_factor=Decimal('1.10')
        )
        
        # Create growth samples for the second batch
        self.growth_sample4 = GrowthSample.objects.create(
            batch=self.batch2,
            sample_date=date.today() - timedelta(days=20),
            sample_size=50,
            avg_weight_g=Decimal('80.00'),
            avg_length_cm=Decimal('10.50'),
            condition_factor=Decimal('1.04')
        )
        
        self.growth_sample5 = GrowthSample.objects.create(
            batch=self.batch2,
            sample_date=date.today() - timedelta(days=10),
            sample_size=50,
            avg_weight_g=Decimal('105.00'),
            avg_length_cm=Decimal('12.20'),
            condition_factor=Decimal('1.07')
        )
        
        # Create mortality events
        self.mortality1 = MortalityEvent.objects.create(
            batch=self.batch,
            event_date=date.today() - timedelta(days=25),
            count=50,
            cause="DISEASE",
            biomass_kg=Decimal('5.00'),
            description="Test mortality event"
        )
        
        self.mortality2 = MortalityEvent.objects.create(
            batch=self.batch,
            event_date=date.today() - timedelta(days=15),
            count=30,
            cause="HANDLING",
            biomass_kg=Decimal('3.60'),
            description="Test mortality event 2"
        )
        
        self.mortality3 = MortalityEvent.objects.create(
            batch=self.batch2,
            event_date=date.today() - timedelta(days=15),
            count=75,
            cause="DISEASE",
            biomass_kg=Decimal('6.00'),
            description="Test mortality event 3"
        )

    def test_growth_analysis_endpoint(self):
        """Test the growth analysis endpoint."""
        url = get_api_url('batch', 'batches', detail=True, pk=self.batch.id) + 'growth_analysis/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        # Check that the response has the expected structure
        self.assertEqual(data['batch_number'], self.batch.batch_number)
        self.assertEqual(data['species'], self.species.name)
        self.assertIn('growth_metrics', data)
        self.assertIn('summary', data)
        
        # Check that all growth samples are included
        self.assertEqual(len(data['growth_metrics']), 3)
        
        # Check that metrics are calculated correctly
        first_sample = data['growth_metrics'][0]
        self.assertEqual(Decimal(str(first_sample['avg_weight_g'])), self.growth_sample1.avg_weight_g)
        
        # The second growth metric should have weight gain data
        second_sample = data['growth_metrics'][1]
        self.assertIn('weight_gain_g', second_sample)
        self.assertIn('daily_growth_g', second_sample)
        self.assertIn('sgr', second_sample)
        
        # Check summary data
        self.assertIn('total_weight_gain_g', data['summary'])
        self.assertIn('avg_daily_growth_g', data['summary'])
        self.assertIn('avg_sgr', data['summary'])
        
        # Expected weight gain: 140 - 100 = 40g
        self.assertAlmostEqual(float(data['summary']['total_weight_gain_g']), 40.0, places=1)
        
        # Expected daily growth: 40g / 20 days = 2g/day
        self.assertAlmostEqual(float(data['summary']['avg_daily_growth_g']), 2.0, places=1)

    def test_growth_analysis_no_samples(self):
        """Test the growth analysis endpoint when no samples are available."""
        # Create a new batch with no growth samples
        new_batch = Batch.objects.create(
            batch_number="B003",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            population_count=800,
            biomass_kg=Decimal('80.00'),
            start_date=date.today() - timedelta(days=10),
            status="active"
        )
        
        url = get_api_url('batch', 'batches', detail=True, pk=new_batch.id) + 'growth_analysis/'
        response = self.client.get(url)
        
        # Should return 404 when no growth samples are found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.json())

    def test_performance_metrics_endpoint(self):
        """Test the performance metrics endpoint."""
        url = get_api_url('batch', 'batches', detail=True, pk=self.batch.id) + 'performance_metrics/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        # Check that the response has the expected structure
        self.assertEqual(data['batch_number'], self.batch.batch_number)
        self.assertIn('current_metrics', data)
        self.assertIn('mortality_metrics', data)
        
        # Check mortality calculations
        mortality = data['mortality_metrics']
        self.assertEqual(mortality['total_count'], 80)  # 50 + 30
        self.assertAlmostEqual(float(mortality['total_biomass_kg']), 8.6, places=1)  # 5.0 + 3.6
        
        # Expected mortality rate: 80 / (1000 + 80) ≈ 7.41%
        self.assertAlmostEqual(mortality['mortality_rate'], 7.41, places=1)
        
        # Check by_cause breakdown
        causes = mortality['by_cause']
        self.assertEqual(len(causes), 2)  # Disease and Handling
        
        # Check container metrics
        self.assertIn('container_metrics', data)
        container_data = data['container_metrics'][0]
        self.assertEqual(container_data['container_name'], self.container.name)
        self.assertEqual(container_data['population'], 1000)
        self.assertAlmostEqual(float(container_data['biomass_kg']), 100.0, places=1)
        
        # Check density calculation: 100 kg / 10 m³ = 10 kg/m³
        self.assertAlmostEqual(float(container_data['density_kg_m3']), 10.0, places=1)
        
        # Check recent growth samples
        self.assertIn('recent_growth_samples', data)
        self.assertEqual(len(data['recent_growth_samples']), 3)

    def test_batch_comparison_endpoint(self):
        """Test the batch comparison endpoint."""
        url = get_api_url('batch', 'batches') + 'compare/'
        
        # Test with no batch_ids parameter
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test with invalid batch_ids format
        response = self.client.get(url + '?batch_ids=invalid')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test with non-existent batch IDs
        response = self.client.get(url + '?batch_ids=9999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test with valid batch IDs and all metrics
        response = self.client.get(url + f'?batch_ids={self.batch.id},{self.batch2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        # Check that the response has the expected structure
        self.assertIn('batches', data)
        self.assertEqual(len(data['batches']), 2)
        self.assertIn('growth_comparison', data)
        self.assertIn('mortality_comparison', data)
        self.assertIn('biomass_comparison', data)
        
        # Check growth comparison data
        growth_data = data['growth_comparison']
        self.assertEqual(len(growth_data), 2)
        
        # First batch growth: From 100g to 140g
        batch1_growth = next(item for item in growth_data if item['batch_id'] == self.batch.id)
        self.assertAlmostEqual(float(batch1_growth['initial_weight_g']), 100.0, places=1)
        self.assertAlmostEqual(float(batch1_growth['final_weight_g']), 140.0, places=1)
        self.assertAlmostEqual(float(batch1_growth['weight_gain_g']), 40.0, places=1)
        
        # Second batch growth: From 80g to 105g
        batch2_growth = next(item for item in growth_data if item['batch_id'] == self.batch2.id)
        self.assertAlmostEqual(float(batch2_growth['initial_weight_g']), 80.0, places=1)
        self.assertAlmostEqual(float(batch2_growth['final_weight_g']), 105.0, places=1)
        self.assertAlmostEqual(float(batch2_growth['weight_gain_g']), 25.0, places=1)
        
        # Check mortality comparison
        mortality_data = data['mortality_comparison']
        self.assertEqual(len(mortality_data), 2)
        
        # First batch mortality: 80 fish (7.41%)
        batch1_mortality = next(item for item in mortality_data if item['batch_id'] == self.batch.id)
        self.assertEqual(batch1_mortality['total_mortality'], 80)
        self.assertAlmostEqual(batch1_mortality['mortality_rate'], 7.41, places=1)
        
        # Second batch mortality: 75 fish
        batch2_mortality = next(item for item in mortality_data if item['batch_id'] == self.batch2.id)
        self.assertEqual(batch2_mortality['total_mortality'], 75)
        
        # Test with filtered metrics
        response = self.client.get(url + f'?batch_ids={self.batch.id},{self.batch2.id}&metrics=growth')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('growth_comparison', data)
        self.assertNotIn('mortality_comparison', data)
        self.assertNotIn('biomass_comparison', data)
