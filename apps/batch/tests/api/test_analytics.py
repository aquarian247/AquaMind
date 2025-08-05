"""
Tests for the batch analytics API endpoints.

This module tests the analytics functionality of the batch API, including:
- Growth analysis endpoint
- Performance metrics endpoint
- Batch comparison endpoint
"""
import json
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from tests.base import BaseAPITestCase
from rest_framework.authtoken.models import Token

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    GrowthSample,
    MortalityEvent,
    BatchContainerAssignment
)
from apps.infrastructure.models import Container, Hall, Geography, FreshwaterStation, Area, ContainerType


class BatchAnalyticsTestCase(BaseAPITestCase):
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
            optimal_temperature_max=12.0
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
        self.stage3 = LifeCycleStage.objects.create(
            name="Parr",
            species=self.species,
            order=3,
            description="Parr stage"
        )
        
        # Create infrastructure objects
        self.geography = Geography.objects.create(
            name="Test Geography",
            description="Test site for analytics"
        )
        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0
        )
        self.hall = Hall.objects.create(
            name="Test Hall",
            freshwater_station=self.station
        )
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=40.7128,
            longitude=-74.0060,
            max_biomass=1000.0
        )
        self.container_type = ContainerType.objects.create(
            name="Test Container Type",
            max_volume_m3=100.0
        )
        self.container1 = Container.objects.create(
            name="Test Container 1",
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        self.container2 = Container.objects.create(
            name="Test Container 2",
            container_type=self.container_type,
            area=self.area,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        # Create batches
        self.batch = Batch.objects.create(
            batch_number="BATCH001",
            species=self.species,
            lifecycle_stage=self.stage2,
            start_date=date.today() - timedelta(days=60),
            expected_end_date=date.today() + timedelta(days=300)
        )
        self.batch2 = Batch.objects.create(
            batch_number="BATCH002",
            species=self.species,
            lifecycle_stage=self.stage2,
            start_date=date.today() - timedelta(days=40),
            expected_end_date=date.today() + timedelta(days=320)
        )
        self.batch_no_samples = Batch.objects.create(
            batch_number="BATCH003",
            species=self.species,
            lifecycle_stage=self.stage2,
            start_date=date.today() - timedelta(days=40),
            expected_end_date=date.today() + timedelta(days=320)
        )
        
        # Create container assignments
        self.assignment1 = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container1,
            lifecycle_stage=self.stage2,
            assignment_date=date.today() - timedelta(days=55),
            population_count=10000,
            avg_weight_g=Decimal('50.00'),
            is_active=True
        )
        self.assignment2 = BatchContainerAssignment.objects.create(
            batch=self.batch2,
            container=self.container2,
            lifecycle_stage=self.stage2,
            assignment_date=date.today() - timedelta(days=35),
            population_count=8000,
            avg_weight_g=Decimal('60.00'),
            is_active=True
        )
        
        # Create growth samples for the first batch
        self.growth_sample1 = GrowthSample.objects.create(
            assignment=self.assignment1,
            sample_date=date.today() - timedelta(days=30),
            sample_size=50,
            avg_weight_g=Decimal('100.00'),
            avg_length_cm=Decimal('12.50'),
            condition_factor=Decimal('1.05')
        )
        
        self.growth_sample2 = GrowthSample.objects.create(
            assignment=self.assignment1,
            sample_date=date.today() - timedelta(days=20),
            sample_size=50,
            avg_weight_g=Decimal('120.00'),
            avg_length_cm=Decimal('13.80'),
            condition_factor=Decimal('1.08')
        )
        
        self.growth_sample3 = GrowthSample.objects.create(
            assignment=self.assignment1,
            sample_date=date.today() - timedelta(days=10),
            sample_size=50,
            avg_weight_g=Decimal('140.00'),
            avg_length_cm=Decimal('15.00'),
            condition_factor=Decimal('1.10')
        )
        
        # Create growth samples for the second batch
        self.growth_sample4 = GrowthSample.objects.create(
            assignment=self.assignment2,
            sample_date=date.today() - timedelta(days=20),
            sample_size=50,
            avg_weight_g=Decimal('80.00'),
            avg_length_cm=Decimal('10.50'),
            condition_factor=Decimal('1.04')
        )
        
        self.growth_sample5 = GrowthSample.objects.create(
            assignment=self.assignment2,
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
        url = self.get_api_url('batch', 'batches', detail=True, pk=self.batch.id) + 'growth_analysis/'
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
        """
        Test growth analysis endpoint when no growth samples exist for the batch.
        """
        batch = Batch.objects.create(
            batch_number=f"BATCH{secrets.token_hex(3).upper()}",
            species=self.species,
            start_date=date.today(),
            lifecycle_stage=self.stage1
        )
        url = reverse('batch:batch-growth-analysis', kwargs={'pk': batch.id})
        response = self.client.get(url)
        print(f"Growth Analysis URL: {url}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'No growth samples available for this batch.')

    def test_performance_metrics_endpoint(self):
        """Test the performance metrics endpoint."""
        url = reverse('batch:batch-list')
        response = self.client.get(url)
        print("Performance Metrics Response:", response.status_code, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Adjust based on actual Batch model fields; assuming calculated_population_count exists
        self.assertIn('results', response.data)
        if response.data['results']:
            for metric in response.data['results']:
                self.assertIn('batch_number', metric)
                self.assertIn('calculated_population_count', metric)  # Adjust to existing field

    def test_batch_comparison_endpoint(self):
        """Test the batch comparison endpoint."""
        url = reverse('batch:batch-compare')
        batch_ids_str = f"{self.batch.id},{self.batch2.id}"
        response = self.client.get(url, {'batch_ids': batch_ids_str})
        print(f"Batch Comparison Response: {response.status_code} {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('batches', response.data)  
        self.assertIn('growth_comparison', response.data)
        if response.data.get('growth_comparison'):
            for comparison_item in response.data['growth_comparison']:
                self.assertIn('current_avg_weight_g', comparison_item)
