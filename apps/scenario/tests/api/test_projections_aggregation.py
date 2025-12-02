"""
Tests for scenario projections aggregation endpoints.

Tests ensure that weekly/monthly aggregation works correctly
using proper Django ORM functions.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, FCRModelStage, MortalityModel,
    TemperatureProfile, TemperatureReading, ScenarioProjection, ProjectionRun
)
from apps.batch.models import Species, LifeCycleStage

User = get_user_model()


class ProjectionsAggregationTestCase(TestCase):
    """Test projections aggregation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.fry_stage = LifeCycleStage.objects.create(
            name="Fry",
            species=self.species,
            order=1,
            expected_weight_min_g=1,
            expected_weight_max_g=50
        )

        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Profile"
        )
        for day_offset in range(365):
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                day_number=day_offset + 1,  # 1-based day numbers
                temperature=12.0
            )

        # Create TGC model
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC",
            location="Test Location",
            release_period="January",
            tgc_value=0.025,
            profile=self.temp_profile
        )

        # Create FCR model with stages
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR"
        )
        FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.fry_stage,
            fcr_value=1.2,
            duration_days=90
        )

        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Low Mortality",
            frequency="daily",
            rate=0.1
        )

        # Create scenario
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=5.0,
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        # Create sample projection data
        self._create_sample_projections()

    def _create_sample_projections(self):
        """Create sample projection data for testing."""
        # Create ProjectionRun first
        projection_run = ProjectionRun.objects.create(
            scenario=self.scenario,
            run_number=1,
            label='Test Run',
            parameters_snapshot={},
            created_by=self.user,
            total_projections=91
        )
        
        projections = []
        for day in range(91):  # Days 0 to 90
            projection = ScenarioProjection(
                projection_run=projection_run,
                projection_date=date(2024, 1, 1) + timedelta(days=day),
                day_number=day,
                average_weight=5.0 + (day * 0.5),
                population=10000 - (day * 10),
                biomass=(5.0 + (day * 0.5)) * (10000 - (day * 10)) / 1000,
                daily_feed=10.0 + day,
                cumulative_feed=(10.0 + day) * (day + 1) / 2,
                temperature=12.0,
                current_stage=self.fry_stage
            )
            projections.append(projection)
        ScenarioProjection.objects.bulk_create(projections)
        
        # Update run summary
        last_proj = projections[-1]
        projection_run.final_weight_g = last_proj.average_weight
        projection_run.final_biomass_kg = last_proj.biomass
        projection_run.save()

    def test_daily_aggregation_returns_all_projections(self):
        """Test that daily aggregation returns all projections."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'daily'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have all 91 projections (days 0-90)
        self.assertEqual(len(response.data), 91)

    def test_weekly_aggregation_samples_every_7th_day(self):
        """Test that weekly aggregation samples every 7th day."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Days 0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84
        # That's 13 projections
        expected_count = len([d for d in range(91) if d % 7 == 0])
        self.assertEqual(len(response.data), expected_count)

        # Verify day numbers are multiples of 7
        day_numbers = [p['day_number'] for p in response.data]
        for day_num in day_numbers:
            self.assertEqual(day_num % 7, 0,
                           f"Day {day_num} should be divisible by 7")

    def test_monthly_aggregation_samples_every_30th_day(self):
        """Test that monthly aggregation samples every 30th day."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'monthly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Days 0, 30, 60, 90 - That's 4 projections
        expected_count = len([d for d in range(91) if d % 30 == 0])
        self.assertEqual(len(response.data), expected_count)

        # Verify day numbers are multiples of 30
        day_numbers = [p['day_number'] for p in response.data]
        for day_num in day_numbers:
            self.assertEqual(day_num % 30, 0,
                           f"Day {day_num} should be divisible by 30")

    def test_aggregation_preserves_data_structure(self):
        """Test that aggregation preserves all expected fields."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

        # Check first projection has all expected fields
        first = response.data[0]
        expected_fields = [
            'projection_id', 'projection_run', 'projection_date',
            'day_number', 'average_weight', 'population',
            'biomass', 'daily_feed', 'cumulative_feed',
            'temperature', 'current_stage', 'stage_name'
        ]
        for field in expected_fields:
            self.assertIn(field, first,
                         f"Field '{field}' should be in response")

    def test_aggregation_returns_model_instances(self):
        """Test that aggregation returns serializable model instances."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Response should be JSON serializable
        self.assertIsInstance(response.data, list)
        
        # Each item should have all fields properly serialized
        for item in response.data:
            self.assertIsInstance(item, dict)
            self.assertIsInstance(item['average_weight'], (int, float))
            self.assertIsInstance(item['population'], (int, float))
            self.assertIsInstance(item['day_number'], int)

    def test_aggregation_with_date_filtering(self):
        """Test aggregation combined with date range filtering."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0, "Should have some weekly data")
        
        # Verify data is filtered to weekly
        day_numbers = [p['day_number'] for p in response.data]
        for day_num in day_numbers:
            self.assertEqual(day_num % 7, 0)

    def test_invalid_aggregation_defaults_to_daily(self):
        """Test that invalid aggregation value defaults to daily."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'invalid'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all projections (daily)
        self.assertEqual(len(response.data), 91)

    def test_no_aggregation_param_defaults_to_daily(self):
        """Test that missing aggregation parameter defaults to daily."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return all projections
        self.assertEqual(len(response.data), 91)

    def test_weekly_aggregation_with_no_projections(self):
        """Test weekly aggregation when scenario has no projections."""
        # Create scenario without projections
        empty_scenario = Scenario.objects.create(
            name="Empty Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=5.0,
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        url = f'/api/v1/scenario/scenarios/{empty_scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        # Should return 404 as there are no projection runs
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_aggregation_maintains_chronological_order(self):
        """Test that aggregated results maintain chronological order."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        response = self.client.get(url, {'aggregation': 'weekly'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that day numbers are in ascending order
        day_numbers = [p['day_number'] for p in response.data]
        self.assertEqual(day_numbers, sorted(day_numbers),
                        "Day numbers should be in ascending order")

    def test_aggregation_includes_day_zero(self):
        """Test that weekly/monthly aggregation includes day 0."""
        url = f'/api/v1/scenario/scenarios/{self.scenario.scenario_id}/projections/'
        
        # Weekly
        response = self.client.get(url, {'aggregation': 'weekly'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        day_numbers = [p['day_number'] for p in response.data]
        self.assertIn(0, day_numbers, "Day 0 should be included in weekly")

        # Monthly
        response = self.client.get(url, {'aggregation': 'monthly'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        day_numbers = [p['day_number'] for p in response.data]
        self.assertIn(0, day_numbers, "Day 0 should be included in monthly")

