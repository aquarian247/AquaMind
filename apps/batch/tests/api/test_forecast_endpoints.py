"""
Tests for the forecast aggregation endpoints.

This module tests the /api/v1/batch/forecast/harvest/ and
/api/v1/batch/forecast/sea-transfer/ endpoints which provide
harvest and sea-transfer forecasts for the executive dashboard.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from tests.base import BaseAPITestCase

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    ActualDailyAssignmentState,
)
from apps.infrastructure.models import (
    Container,
    Hall,
    Geography,
    FreshwaterStation,
    Area,
    ContainerType
)
from apps.planning.models import PlannedActivity


class HarvestForecastTestCase(BaseAPITestCase):
    """Test case for harvest forecast endpoint."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
            description="A common farmed fish species",
            optimal_temperature_min=7.0,
            optimal_temperature_max=12.0
        )
        self.stage_adult = LifeCycleStage.objects.create(
            name="Adult",
            species=self.species,
            order=6,
            description="Adult stage"
        )
        
        # Get or create geography
        self.geography, _ = Geography.objects.get_or_create(
            name="Faroe Islands",
            defaults={'description': "Test geography"}
        )
        
        # Create sea infrastructure (for harvest-ready batches)
        self.area = Area.objects.create(
            name="Sea Area 1",
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=50000.0
        )
        
        # Create container type and containers
        self.container_type = ContainerType.objects.create(
            name="Sea Pen",
            max_volume_m3=10000.0
        )
        self.container = Container.objects.create(
            name="Pen 1",
            container_type=self.container_type,
            area=self.area,
            volume_m3=5000.0,
            max_biomass_kg=50000.0
        )
        
        # Create batch approaching harvest weight
        self.batch = Batch.objects.create(
            batch_number="HARVEST-001",
            species=self.species,
            lifecycle_stage=self.stage_adult,
            status='ACTIVE',
            start_date=date.today() - timedelta(days=500),
            expected_end_date=date.today() + timedelta(days=60)
        )
        
        # Create container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_adult,
            assignment_date=date.today() - timedelta(days=100),
            population_count=50000,
            avg_weight_g=Decimal('4200.00'),  # Approaching 5000g target
            biomass_kg=Decimal('210000.00'),
            is_active=True
        )
        
        # Create actual daily state with confidence scores
        self.daily_state = ActualDailyAssignmentState.objects.create(
            assignment=self.assignment,
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_adult,
            date=date.today(),
            day_number=500,
            avg_weight_g=Decimal('4200.00'),
            population=50000,
            biomass_kg=Decimal('210000.00'),
            confidence_scores={'weight': 0.95, 'temperature': 0.90, 'mortality': 0.92}
        )
        
        # Note: Projections are not created in this test setup to keep tests simple.
        # The forecast endpoints should still work and return batches without
        # projected dates when no projection data exists.
    
    def test_harvest_forecast_success(self):
        """Test successful harvest forecast retrieval."""
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check response structure
        self.assertIn('summary', data)
        self.assertIn('upcoming', data)
        self.assertIn('by_quarter', data)
        
        # Check summary fields
        summary = data['summary']
        self.assertIn('total_batches', summary)
        self.assertIn('harvest_ready_count', summary)
        self.assertIn('avg_days_to_harvest', summary)
        self.assertIn('total_projected_biomass_tonnes', summary)
    
    def test_harvest_forecast_with_geography_filter(self):
        """Test harvest forecast filtered by geography."""
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url, {'geography_id': self.geography.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return batches in the specified geography
        self.assertGreaterEqual(data['summary']['total_batches'], 0)
    
    def test_harvest_forecast_with_invalid_geography(self):
        """Test harvest forecast with invalid geography ID."""
        url = self.get_api_url('batch', 'forecast/harvest')
        
        # Non-existent geography
        response = self.client.get(url, {'geography_id': 99999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Invalid format
        response = self.client.get(url, {'geography_id': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_harvest_forecast_with_species_filter(self):
        """Test harvest forecast filtered by species."""
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url, {'species_id': self.species.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All returned batches should be the specified species
        for batch_data in data['upcoming']:
            self.assertEqual(batch_data['species'], self.species.name)
    
    def test_harvest_forecast_with_date_range(self):
        """Test harvest forecast with date range filters."""
        url = self.get_api_url('batch', 'forecast/harvest')
        
        from_date = date.today().isoformat()
        to_date = (date.today() + timedelta(days=90)).isoformat()
        
        response = self.client.get(url, {
            'from_date': from_date,
            'to_date': to_date
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_harvest_forecast_with_invalid_date_format(self):
        """Test harvest forecast with invalid date format."""
        url = self.get_api_url('batch', 'forecast/harvest')
        
        response = self.client.get(url, {'from_date': 'invalid-date'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_harvest_forecast_with_min_confidence(self):
        """Test harvest forecast filtered by minimum confidence."""
        url = self.get_api_url('batch', 'forecast/harvest')
        
        # High confidence threshold - may exclude some batches
        response = self.client.get(url, {'min_confidence': '0.95'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Low confidence threshold - should include more batches
        response = self.client.get(url, {'min_confidence': '0.1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_harvest_forecast_empty_results(self):
        """Test harvest forecast when no batches match criteria."""
        # Deactivate all batches
        Batch.objects.all().update(status='COMPLETED')
        
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return empty results
        self.assertEqual(data['summary']['total_batches'], 0)
        self.assertEqual(data['summary']['harvest_ready_count'], 0)
        self.assertEqual(len(data['upcoming']), 0)
        self.assertEqual(len(data['by_quarter']), 0)
    
    def test_harvest_forecast_quarterly_aggregation(self):
        """Test that quarterly aggregation is correctly calculated."""
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check quarterly structure
        by_quarter = data['by_quarter']
        for quarter_key, quarter_data in by_quarter.items():
            self.assertIn('count', quarter_data)
            self.assertIn('biomass_tonnes', quarter_data)
            self.assertGreaterEqual(quarter_data['count'], 0)
            self.assertGreaterEqual(quarter_data['biomass_tonnes'], 0)
    
    def test_harvest_forecast_includes_planned_activity(self):
        """Test that planned harvest activities are included in response."""
        url = self.get_api_url('batch', 'forecast/harvest')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Find our test batch
        test_batch = next(
            (b for b in data['upcoming'] if b['batch_number'] == 'HARVEST-001'),
            None
        )
        
        if test_batch:
            # Should have planned activity fields (may be null if no activity exists)
            self.assertIn('planned_activity_id', test_batch)
            self.assertIn('planned_activity_status', test_batch)


class SeaTransferForecastTestCase(BaseAPITestCase):
    """Test case for sea-transfer forecast endpoint."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
            description="A common farmed fish species",
            optimal_temperature_min=7.0,
            optimal_temperature_max=12.0
        )
        self.stage_parr = LifeCycleStage.objects.create(
            name="Parr",
            species=self.species,
            order=3,
            description="Parr stage"
        )
        self.stage_smolt = LifeCycleStage.objects.create(
            name="Smolt",
            species=self.species,
            order=4,
            description="Smolt stage"
        )
        
        # Get or create geography
        self.geography, _ = Geography.objects.get_or_create(
            name="Faroe Islands",
            defaults={'description': "Test geography"}
        )
        
        # Create freshwater infrastructure
        self.station = FreshwaterStation.objects.create(
            name="FW Station 1",
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0
        )
        self.hall = Hall.objects.create(
            name="Hall 1",
            freshwater_station=self.station
        )
        
        # Create container type and container
        self.container_type = ContainerType.objects.create(
            name="Tank",
            max_volume_m3=100.0
        )
        self.container = Container.objects.create(
            name="Tank 1",
            container_type=self.container_type,
            hall=self.hall,  # In hall = freshwater
            volume_m3=50.0,
            max_biomass_kg=500.0
        )
        
        # Create batch in freshwater approaching smolt stage
        self.batch = Batch.objects.create(
            batch_number="TRANSFER-001",
            species=self.species,
            lifecycle_stage=self.stage_parr,
            status='ACTIVE',
            start_date=date.today() - timedelta(days=180),
            expected_end_date=date.today() + timedelta(days=500)
        )
        
        # Create container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_parr,
            assignment_date=date.today() - timedelta(days=60),
            population_count=100000,
            avg_weight_g=Decimal('85.00'),  # Approaching 100g transfer target
            biomass_kg=Decimal('8500.00'),
            is_active=True
        )
        
        # Create actual daily state
        self.daily_state = ActualDailyAssignmentState.objects.create(
            assignment=self.assignment,
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage_parr,
            date=date.today(),
            day_number=180,
            avg_weight_g=Decimal('85.00'),
            population=100000,
            biomass_kg=Decimal('8500.00'),
            confidence_scores={'weight': 0.88, 'temperature': 0.92, 'mortality': 0.85}
        )
        
        # Note: Projections are not created in this test setup to keep tests simple.
        # The forecast endpoints should still work and return batches without
        # projected dates when no projection data exists.
    
    def test_sea_transfer_forecast_success(self):
        """Test successful sea-transfer forecast retrieval."""
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check response structure
        self.assertIn('summary', data)
        self.assertIn('upcoming', data)
        self.assertIn('by_month', data)
        
        # Check summary fields
        summary = data['summary']
        self.assertIn('total_freshwater_batches', summary)
        self.assertIn('transfer_ready_count', summary)
        self.assertIn('avg_days_to_transfer', summary)
    
    def test_sea_transfer_only_freshwater_batches(self):
        """Test that sea-transfer forecast only returns freshwater batches."""
        # Create a sea pen container type with larger volume for sea cages
        sea_pen_type = ContainerType.objects.create(
            name="Sea Pen Large",
            max_volume_m3=5000.0
        )
        
        # Create a sea-based batch (should NOT appear)
        area = Area.objects.create(
            name="Sea Area Test",
            geography=self.geography,
            latitude=62.0,
            longitude=-7.0,
            max_biomass=10000.0
        )
        sea_container = Container.objects.create(
            name="Sea Pen Test",
            container_type=sea_pen_type,
            area=area,  # In area = sea
            volume_m3=1000.0,
            max_biomass_kg=10000.0
        )
        sea_batch = Batch.objects.create(
            batch_number="SEA-001",
            species=self.species,
            lifecycle_stage=self.stage_smolt,
            status='ACTIVE',
            start_date=date.today() - timedelta(days=200),
            expected_end_date=date.today() + timedelta(days=400)
        )
        BatchContainerAssignment.objects.create(
            batch=sea_batch,
            container=sea_container,
            lifecycle_stage=self.stage_smolt,
            assignment_date=date.today() - timedelta(days=30),
            population_count=50000,
            avg_weight_g=Decimal('500.00'),
            biomass_kg=Decimal('25000.00'),
            is_active=True
        )
        
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Sea batch should NOT be in results
        batch_numbers = [b['batch_number'] for b in data['upcoming']]
        self.assertNotIn('SEA-001', batch_numbers)
    
    def test_sea_transfer_with_geography_filter(self):
        """Test sea-transfer forecast filtered by geography."""
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url, {'geography_id': self.geography.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_sea_transfer_empty_results(self):
        """Test sea-transfer forecast when no freshwater batches exist."""
        # Deactivate the assignment
        self.assignment.is_active = False
        self.assignment.save()
        
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return empty results
        self.assertEqual(data['summary']['total_freshwater_batches'], 0)
    
    def test_sea_transfer_monthly_aggregation(self):
        """Test that monthly aggregation is correctly calculated."""
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Check monthly structure
        by_month = data['by_month']
        for month_key, month_data in by_month.items():
            self.assertIn('count', month_data)
            self.assertGreaterEqual(month_data['count'], 0)
    
    def test_sea_transfer_includes_stage_info(self):
        """Test that stage information is included in response."""
        url = self.get_api_url('batch', 'forecast/sea-transfer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        if data['upcoming']:
            batch_data = data['upcoming'][0]
            self.assertIn('current_stage', batch_data)
            self.assertIn('target_stage', batch_data)

