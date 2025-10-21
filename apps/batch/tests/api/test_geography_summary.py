"""
Tests for the geography-level batch aggregation endpoint.

This module tests the /api/v1/batch/batches/geography-summary/ endpoint
which provides aggregated growth, mortality, and feed metrics across all
batches within a geography.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from tests.base import BaseAPITestCase

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    GrowthSample,
    MortalityEvent,
    BatchContainerAssignment
)
from apps.infrastructure.models import (
    Container,
    Hall,
    Geography,
    FreshwaterStation,
    Area,
    ContainerType
)
from apps.inventory.models import Feed, FeedingEvent, BatchFeedingSummary


class GeographySummaryTestCase(BaseAPITestCase):
    """Test case for geography-level batch aggregation endpoint."""
    
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
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
            description="A common farmed fish species",
            optimal_temperature_min=7.0,
            optimal_temperature_max=12.0
        )
        self.stage_fry = LifeCycleStage.objects.create(
            name="Fry",
            species=self.species,
            order=1,
            description="Fry stage"
        )
        self.stage_parr = LifeCycleStage.objects.create(
            name="Parr",
            species=self.species,
            order=2,
            description="Parr stage"
        )
        
        # Create geographies
        self.geography1 = Geography.objects.create(
            name="Faroe Islands",
            description="Test geography 1"
        )
        self.geography2 = Geography.objects.create(
            name="Scotland",
            description="Test geography 2"
        )
        
        # Create infrastructure for geography 1
        self.station1 = FreshwaterStation.objects.create(
            name="Station 1",
            geography=self.geography1,
            latitude=62.0,
            longitude=-7.0
        )
        self.hall1 = Hall.objects.create(
            name="Hall 1",
            freshwater_station=self.station1
        )
        self.area1 = Area.objects.create(
            name="Area 1",
            geography=self.geography1,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=1000.0
        )
        
        # Create infrastructure for geography 2
        self.station2 = FreshwaterStation.objects.create(
            name="Station 2",
            geography=self.geography2,
            latitude=57.0,
            longitude=-5.0
        )
        self.hall2 = Hall.objects.create(
            name="Hall 2",
            freshwater_station=self.station2
        )
        
        # Create container types and containers
        self.container_type = ContainerType.objects.create(
            name="Tank",
            max_volume_m3=100.0
        )
        self.container1 = Container.objects.create(
            name="Container 1",
            container_type=self.container_type,
            hall=self.hall1,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        self.container2 = Container.objects.create(
            name="Container 2",
            container_type=self.container_type,
            area=self.area1,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        self.container3 = Container.objects.create(
            name="Container 3",
            container_type=self.container_type,
            hall=self.hall2,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        # Create batches in geography 1
        self.batch1 = Batch.objects.create(
            batch_number="BATCH001",
            species=self.species,
            lifecycle_stage=self.stage_fry,
            start_date=date.today() - timedelta(days=60),
            expected_end_date=date.today() + timedelta(days=300)
        )
        self.batch2 = Batch.objects.create(
            batch_number="BATCH002",
            species=self.species,
            lifecycle_stage=self.stage_fry,
            start_date=date.today() - timedelta(days=50),
            expected_end_date=date.today() + timedelta(days=310)
        )
        
        # Create batch in geography 2
        self.batch3 = Batch.objects.create(
            batch_number="BATCH003",
            species=self.species,
            lifecycle_stage=self.stage_parr,
            start_date=date.today() - timedelta(days=40),
            expected_end_date=date.today() + timedelta(days=320)
        )
        
        # Create container assignments
        self.assignment1 = BatchContainerAssignment.objects.create(
            batch=self.batch1,
            container=self.container1,
            lifecycle_stage=self.stage_fry,
            assignment_date=date.today() - timedelta(days=55),
            population_count=10000,
            avg_weight_g=Decimal('50.00'),
            is_active=True
        )
        self.assignment2 = BatchContainerAssignment.objects.create(
            batch=self.batch2,
            container=self.container2,
            lifecycle_stage=self.stage_fry,
            assignment_date=date.today() - timedelta(days=45),
            population_count=8000,
            avg_weight_g=Decimal('60.00'),
            is_active=True
        )
        self.assignment3 = BatchContainerAssignment.objects.create(
            batch=self.batch3,
            container=self.container3,
            lifecycle_stage=self.stage_parr,
            assignment_date=date.today() - timedelta(days=35),
            population_count=5000,
            avg_weight_g=Decimal('100.00'),
            is_active=True
        )
        
        # Create growth samples for geography 1 batches
        self._create_growth_samples_for_batch(self.assignment1, [
            (30, Decimal('100.00'), Decimal('12.50')),
            (20, Decimal('120.00'), Decimal('13.80')),
            (10, Decimal('140.00'), Decimal('15.00')),
        ])
        self._create_growth_samples_for_batch(self.assignment2, [
            (25, Decimal('80.00'), Decimal('11.00')),
            (15, Decimal('100.00'), Decimal('12.00')),
        ])
        
        # Create growth samples for geography 2 batch
        self._create_growth_samples_for_batch(self.assignment3, [
            (30, Decimal('150.00'), Decimal('16.00')),
            (20, Decimal('180.00'), Decimal('17.50')),
        ])
        
        # Create mortality events
        MortalityEvent.objects.create(
            batch=self.batch1,
            event_date=date.today() - timedelta(days=25),
            count=200,
            cause="DISEASE",
            biomass_kg=Decimal('20.00'),
            description="Disease outbreak"
        )
        MortalityEvent.objects.create(
            batch=self.batch1,
            event_date=date.today() - timedelta(days=15),
            count=100,
            cause="HANDLING",
            biomass_kg=Decimal('12.00'),
            description="Handling mortality"
        )
        MortalityEvent.objects.create(
            batch=self.batch2,
            event_date=date.today() - timedelta(days=20),
            count=150,
            cause="DISEASE",
            biomass_kg=Decimal('12.00'),
            description="Disease"
        )
        MortalityEvent.objects.create(
            batch=self.batch3,
            event_date=date.today() - timedelta(days=20),
            count=100,
            cause="PREDATION",
            biomass_kg=Decimal('15.00'),
            description="Predation"
        )
        
        # Create feed and feeding events
        self.feed = Feed.objects.create(
            name="Test Feed",
            brand="Test Brand",
            size_category="MEDIUM",
            description="Test feed type",
            protein_percentage=Decimal('45.00'),
            fat_percentage=Decimal('20.00')
        )
        
        # Create feeding events for geography 1
        FeedingEvent.objects.create(
            batch=self.batch1,
            batch_assignment=self.assignment1,
            container=self.container1,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=20),
            feeding_time="09:00:00",
            amount_kg=Decimal('10.50'),
            batch_biomass_kg=Decimal('500.00')
        )
        FeedingEvent.objects.create(
            batch=self.batch2,
            batch_assignment=self.assignment2,
            container=self.container2,
            feed=self.feed,
            feeding_date=date.today() - timedelta(days=15),
            feeding_time="09:00:00",
            amount_kg=Decimal('8.00'),
            batch_biomass_kg=Decimal('480.00')
        )
        
        # Create batch feeding summaries for testing FCR
        BatchFeedingSummary.objects.create(
            batch=self.batch1,
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() - timedelta(days=1),
            total_feed_kg=Decimal('150.00'),
            fcr=Decimal('1.15')
        )
        BatchFeedingSummary.objects.create(
            batch=self.batch2,
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() - timedelta(days=1),
            total_feed_kg=Decimal('120.00'),
            fcr=Decimal('1.20')
        )
    
    def _create_growth_samples_for_batch(self, assignment, samples_data):
        """
        Helper to create growth samples.
        
        Args:
            assignment: BatchContainerAssignment instance
            samples_data: List of tuples (days_ago, avg_weight_g, avg_length_cm)
        """
        for days_ago, weight, length in samples_data:
            GrowthSample.objects.create(
                assignment=assignment,
                sample_date=date.today() - timedelta(days=days_ago),
                sample_size=50,
                avg_weight_g=weight,
                avg_length_cm=length
            )
    
    def test_geography_summary_success(self):
        """Test successful geography summary with all metrics."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url, {'geography': self.geography1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check basic structure
        self.assertEqual(data['geography_id'], self.geography1.id)
        self.assertEqual(data['geography_name'], self.geography1.name)
        self.assertEqual(data['total_batches'], 2)  # batch1 and batch2
        
        # Check growth metrics structure
        self.assertIn('growth_metrics', data)
        growth = data['growth_metrics']
        self.assertIn('avg_sgr', growth)
        self.assertIn('avg_growth_rate_g_per_day', growth)
        self.assertIn('avg_weight_g', growth)
        self.assertIn('total_biomass_kg', growth)
        
        # SGR should be calculated from growth samples
        self.assertIsNotNone(growth['avg_sgr'])
        self.assertGreater(growth['avg_sgr'], 0)
        
        # Check mortality metrics
        self.assertIn('mortality_metrics', data)
        mortality = data['mortality_metrics']
        self.assertEqual(mortality['total_count'], 450)  # 200+100+150 from geo1
        self.assertGreater(mortality['total_biomass_kg'], 0)
        self.assertGreater(mortality['avg_mortality_rate_percent'], 0)
        self.assertEqual(len(mortality['by_cause']), 2)  # DISEASE and HANDLING
        
        # Check feed metrics
        self.assertIn('feed_metrics', data)
        feed = data['feed_metrics']
        self.assertGreater(feed['total_feed_kg'], 0)
        self.assertIsNotNone(feed['avg_fcr'])
    
    def test_geography_summary_with_date_filters(self):
        """Test geography summary with start_date and end_date filters."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        
        # Filter to recent assignments only
        start_date = (date.today() - timedelta(days=50)).isoformat()
        end_date = date.today().isoformat()
        
        response = self.client.get(url, {
            'geography': self.geography1.id,
            'start_date': start_date,
            'end_date': end_date
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should still have batches within date range
        self.assertGreaterEqual(data['total_batches'], 1)
        self.assertEqual(data['period_start'], start_date)
        self.assertEqual(data['period_end'], end_date)
    
    def test_geography_summary_empty_geography(self):
        """Test geography summary for geography with no batches."""
        # Create empty geography
        empty_geo = Geography.objects.create(
            name="Empty Geography",
            description="No batches here"
        )
        
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url, {'geography': empty_geo.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return zeros/nulls
        self.assertEqual(data['total_batches'], 0)
        self.assertEqual(data['growth_metrics']['total_biomass_kg'], 0.0)
        self.assertEqual(data['mortality_metrics']['total_count'], 0)
    
    def test_geography_summary_missing_geography_param(self):
        """Test error when geography parameter is missing."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('geography', response.json())
    
    def test_geography_summary_invalid_geography_id(self):
        """Test error when geography ID is invalid."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        
        # Test with non-existent ID
        response = self.client.get(url, {'geography': 99999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('geography', response.json())
        
        # Test with invalid format
        response = self.client.get(url, {'geography': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('geography', response.json())
    
    def test_geography_summary_invalid_date_format(self):
        """Test error when date format is invalid."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        
        # Test invalid start_date
        response = self.client.get(url, {
            'geography': self.geography1.id,
            'start_date': 'invalid-date'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.json())
        
        # Test invalid end_date
        response = self.client.get(url, {
            'geography': self.geography1.id,
            'end_date': '2024/10/20'  # Wrong format
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.json())
    
    def test_geography_summary_multiple_geographies(self):
        """Test that geography filtering is exclusive."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        
        # Get summary for geography 1
        response1 = self.client.get(url, {'geography': self.geography1.id})
        data1 = response1.json()
        
        # Get summary for geography 2
        response2 = self.client.get(url, {'geography': self.geography2.id})
        data2 = response2.json()
        
        # Should have different batch counts
        self.assertNotEqual(data1['total_batches'], data2['total_batches'])
        self.assertEqual(data1['total_batches'], 2)  # geo1 has 2 batches
        self.assertEqual(data2['total_batches'], 1)  # geo2 has 1 batch
    
    def test_geography_summary_no_growth_samples(self):
        """Test geography summary when batches have no growth samples."""
        # Create new geography with batch but no growth samples
        new_geo = Geography.objects.create(
            name="New Geography",
            description="Test"
        )
        new_station = FreshwaterStation.objects.create(
            name="New Station",
            geography=new_geo,
            latitude=60.0,
            longitude=-6.0
        )
        new_hall = Hall.objects.create(
            name="New Hall",
            freshwater_station=new_station
        )
        new_container = Container.objects.create(
            name="New Container",
            container_type=self.container_type,
            hall=new_hall,
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        new_batch = Batch.objects.create(
            batch_number="BATCH_NO_SAMPLES",
            species=self.species,
            lifecycle_stage=self.stage_fry,
            start_date=date.today() - timedelta(days=30),
            expected_end_date=date.today() + timedelta(days=330)
        )
        BatchContainerAssignment.objects.create(
            batch=new_batch,
            container=new_container,
            lifecycle_stage=self.stage_fry,
            assignment_date=date.today() - timedelta(days=25),
            population_count=5000,
            avg_weight_g=Decimal('40.00'),
            is_active=True
        )
        
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url, {'geography': new_geo.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return None for SGR/growth rate
        self.assertEqual(data['total_batches'], 1)
        self.assertIsNone(data['growth_metrics']['avg_sgr'])
        self.assertIsNone(data['growth_metrics']['avg_growth_rate_g_per_day'])
        # But should still have biomass from assignments
        self.assertGreater(data['growth_metrics']['total_biomass_kg'], 0)
    
    def test_geography_summary_mortality_by_cause_distribution(self):
        """Test that mortality by cause is correctly distributed."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url, {'geography': self.geography1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        by_cause = data['mortality_metrics']['by_cause']
        
        # Should have DISEASE as top cause (200+150=350)
        disease_item = next((item for item in by_cause if item['cause'] == 'DISEASE'), None)
        self.assertIsNotNone(disease_item)
        self.assertEqual(disease_item['count'], 350)
        
        # Should have HANDLING as second (100)
        handling_item = next((item for item in by_cause if item['cause'] == 'HANDLING'), None)
        self.assertIsNotNone(handling_item)
        self.assertEqual(handling_item['count'], 100)
        
        # Percentages should sum to 100
        total_percentage = sum(item['percentage'] for item in by_cause)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
    
    def test_geography_summary_fcr_calculation(self):
        """Test that FCR is correctly calculated from summaries."""
        url = self.get_api_url('batch', 'batches/geography-summary')
        response = self.client.get(url, {'geography': self.geography1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        feed_metrics = data['feed_metrics']
        
        # Should have FCR from batch summaries
        self.assertIsNotNone(feed_metrics['avg_fcr'])
        self.assertGreater(feed_metrics['avg_fcr'], 0)
        
        # Average of 1.15 and 1.20 should be around 1.17-1.18
        self.assertAlmostEqual(feed_metrics['avg_fcr'], 1.17, places=1)

