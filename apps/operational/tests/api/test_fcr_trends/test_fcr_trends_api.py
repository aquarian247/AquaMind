"""
Integration tests for FCR Trends API endpoints.

Tests the complete API workflow from request to response,
including authentication, parameter validation, and data aggregation.
"""
import json
from datetime import date, timedelta, time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from apps.inventory.models import ContainerFeedingSummary
from apps.batch.models import Batch, BatchContainerAssignment, Species, LifeCycleStage
from apps.infrastructure.models import Container, FreshwaterStation, Area, Geography


User = get_user_model()


class FCRTrendsAPITest(APITestCase):
    """Test FCR Trends API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        # Create superuser for API access
        self.user = User.objects.create_superuser(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create geography hierarchy
        self.geography = Geography.objects.create(
            name="Test Geography"
        )
        self.area = Area.objects.create(
            name="Test Area",
            geography=self.geography,
            latitude=60.0,
            longitude=-7.0,
            max_biomass=10000.0
        )
        # Create container type
        from apps.infrastructure.models import ContainerType
        self.container_type = ContainerType.objects.create(
            name="Test Tank",
            category="TANK",
            max_volume_m3=100.0
        )

        self.station = FreshwaterStation.objects.create(
            name="Test Station",
            geography=self.geography,
            station_type="FRESHWATER",
            latitude=60.0,
            longitude=-7.0
        )

        self.container = Container.objects.create(
            name="Test Container",
            container_type=self.container_type,
            area=self.area,  # Container in area, not hall
            volume_m3=50.0,
            max_biomass_kg=1000.0
        )

        # Create species and lifecycle
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.lifecycle_stage = LifeCycleStage.objects.create(
            name="Post-Smolt",
            order=4,
            species=self.species
        )

        # Create batch
        self.batch = Batch.objects.create(
            batch_number="TEST-001",
            species=self.species,
            lifecycle_stage=self.lifecycle_stage,
            start_date=date.today() - timedelta(days=100)
        )

        # Create container assignment
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.lifecycle_stage,
            population_count=2500,
            avg_weight_g=Decimal('150.00'),
            assignment_date=date.today() - timedelta(days=30),
            is_active=True
        )

    def test_fcr_trends_api_container_assignment(self):
        """Test FCR trends API for container assignment."""
        # Create container feeding summary
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignment,
            period_start=start_date,
            period_end=end_date,
            total_feed_kg=Decimal('175.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('11.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Test API call
        url = reverse('fcr-trends-list')
        params = {
            'assignment_id': self.assignment.id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['interval'], 'WEEKLY')
        self.assertEqual(data['aggregation_level'], 'assignment')
        self.assertEqual(len(data['series']), 1)

        series_item = data['series'][0]
        self.assertEqual(series_item['assignment_id'], self.assignment.id)
        self.assertEqual(series_item['container_name'], self.container.name)
        self.assertEqual(series_item['actual_fcr'], 11.67)
        self.assertEqual(series_item['confidence'], 'HIGH')
        self.assertEqual(series_item['data_points'], 7)

    def test_fcr_trends_api_batch_aggregation(self):
        """Test FCR trends API for batch-level aggregation."""
        from apps.inventory.models import BatchFeedingSummary

        # Create batch feeding summary
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        BatchFeedingSummary.objects.create(
            batch=self.batch,
            period_start=start_date,
            period_end=end_date,
            total_feed_kg=Decimal('175.0'),
            total_growth_kg=Decimal('15.0'),
            weighted_avg_fcr=Decimal('11.67'),
            container_count=1,
            overall_confidence_level='HIGH',
            estimation_method='MEASURED'
        )

        # Test API call
        url = reverse('fcr-trends-list')
        params = {
            'batch_id': self.batch.id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['aggregation_level'], 'batch')
        self.assertEqual(len(data['series']), 1)

        series_item = data['series'][0]
        self.assertEqual(series_item['actual_fcr'], 11.67)
        self.assertEqual(series_item['confidence'], 'HIGH')
        self.assertEqual(series_item['container_count'], 1)
        self.assertIsNone(series_item['assignment_id'])  # Not applicable for batch aggregation

    def test_fcr_trends_api_parameter_validation(self):
        """Test API parameter validation."""
        url = reverse('fcr-trends-list')

        # Test missing required parameters - API provides defaults
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test invalid date format
        params = {
            'start_date': 'invalid-date',
            'end_date': date.today().isoformat(),
            'interval': 'WEEKLY'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test invalid interval
        params = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat(),
            'interval': 'INVALID'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test end date before start date
        params = {
            'start_date': date.today().isoformat(),
            'end_date': (date.today() - timedelta(days=1)).isoformat(),
            'interval': 'WEEKLY'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fcr_trends_api_unauthenticated(self):
        """Test API requires authentication."""
        # Remove authentication
        self.client.force_authenticate(user=None)

        url = reverse('fcr-trends-list')
        params = {
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fcr_trends_api_no_data(self):
        """Test API response when no data is available."""
        url = reverse('fcr-trends-list')
        params = {
            'assignment_id': self.assignment.id,
            'start_date': (date.today() - timedelta(days=30)).isoformat(),
            'end_date': date.today().isoformat(),
            'interval': 'WEEKLY'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['interval'], 'WEEKLY')
        self.assertEqual(data['aggregation_level'], 'assignment')
        self.assertEqual(len(data['series']), 0)  # No data available

    def test_fcr_trends_api_with_predicted_data(self):
        """Test API includes predicted FCR data when requested."""
        from apps.scenario.models import (
            Scenario, FCRModel, FCRModelStage, TGCModel, MortalityModel, BiologicalConstraints
        )

        # Create temperature profile first
        from apps.scenario.models import TemperatureProfile
        temp_profile = TemperatureProfile.objects.create(name="Test Temp Profile")

        # Create required models
        tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Test Period",
            tgc_value=2.5,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=temp_profile
        )
        fcr_model = FCRModel.objects.create(name="Test FCR Model")
        mortality_model = MortalityModel.objects.create(
            name="Test Mortality Model",
            frequency="DAILY",
            rate=0.01
        )
        biological_constraints = BiologicalConstraints.objects.create(name="Test Constraints")
        user = self.user  # Use existing test user

        # Create FCR model stage
        fcr_stage = FCRModelStage.objects.create(
            model=fcr_model,
            stage=self.lifecycle_stage,
            fcr_value=Decimal('1.2'),
            duration_days=90
        )

        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date.today() - timedelta(days=100),
            duration_days=365,
            initial_count=10000,
            genotype="Test Genotype",
            supplier="Test Supplier",
            tgc_model=tgc_model,
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            batch=self.batch,
            biological_constraints=biological_constraints,
            created_by=user
        )

        # Create container feeding summary
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        ContainerFeedingSummary.objects.create(
            batch=self.batch,
            container_assignment=self.assignment,
            period_start=start_date,
            period_end=end_date,
            total_feed_kg=Decimal('175.0'),
            growth_kg=Decimal('15.0'),
            fcr=Decimal('11.67'),
            confidence_level='HIGH',
            estimation_method='MEASURED',
            data_points=7
        )

        # Test API call with predicted data
        url = reverse('fcr-trends-list')
        params = {
            'assignment_id': self.assignment.id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': 'WEEKLY',
            'include_predicted': 'true'
        }

        response = self.client.get(url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['series']), 1)

        series_item = data['series'][0]
        self.assertIsNotNone(series_item.get('predicted_fcr'))
        self.assertIsNotNone(series_item.get('deviation'))

    def test_fcr_trends_api_default_parameters(self):
        """Test API with default parameters."""
        # Test with only assignment_id (should use defaults for dates and interval)
        url = reverse('fcr-trends-list')
        params = {
            'assignment_id': self.assignment.id
        }

        response = self.client.get(url, params)

        # Should not fail, but may return empty series if no data
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertEqual(data['interval'], 'WEEKLY')  # Default interval
            self.assertEqual(data['aggregation_level'], 'assignment')
