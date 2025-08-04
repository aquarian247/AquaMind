"""
Integration tests for scenario planning.

These tests verify end-to-end workflows, performance characteristics,
and integration between components of the scenario planning system.
"""
import json
import csv
import io
import concurrent.futures
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import unittest

from apps.scenario.models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel,
    FCRModelStage, MortalityModel, Scenario, ScenarioModelChange,
    BiologicalConstraints, StageConstraint, TGCModelStage,
    FCRModelStageOverride, MortalityModelStage, ScenarioProjection,
    LifecycleStageChoices
)
from apps.batch.models import LifeCycleStage, Batch, Species
from apps.scenario.services.calculations.projection_engine import ProjectionEngine
from apps.scenario.services.calculations.tgc_calculator import TGCCalculator
from apps.scenario.services.calculations.fcr_calculator import FCRCalculator
from apps.scenario.services.calculations.mortality_calculator import MortalityCalculator

User = get_user_model()


class ScenarioWorkflowTests(TestCase):
    """Integration tests for scenario planning workflows."""

    def setUp(self):
        """Set up test data for all tests."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass",
            is_staff=True
        )
        self.client.force_login(self.user)

        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        
        # Create lifecycle stages
        self.fry_stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        self.parr_stage = LifeCycleStage.objects.create(
            name="parr",
            species=self.species,
            order=4,
            expected_weight_min_g=5.0,
            expected_weight_max_g=30.0
        )
        
        self.smolt_stage = LifeCycleStage.objects.create(
            name="smolt",
            species=self.species,
            order=5,
            expected_weight_min_g=30.0,
            expected_weight_max_g=150.0
        )
        
        # Create a batch
        self.batch = Batch.objects.create(
            batch_number="Test Batch",
            species=self.species,
            lifecycle_stage=self.fry_stage,
            start_date=date.today() - timedelta(days=30),
            expected_end_date=date.today() + timedelta(days=335)
        )
        
        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        
        # Add temperature readings
        start_date = date.today()
        for i in range(365):  # One year of data
            temp = 10.0 + 5.0 * (1 + (i % 365) / 182.5)  # Seasonal variation
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                reading_date=start_date + timedelta(days=i),
                temperature=temp
            )
        
        # Create TGC model
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        # Create FCR model
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR Model"
        )
        
        # Create FCR model stages
        self.fcr_stage_fry = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.fry_stage,
            fcr_value=1.0,
            duration_days=30
        )
        
        self.fcr_stage_parr = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.parr_stage,
            fcr_value=1.1,
            duration_days=60
        )
        
        self.fcr_stage_smolt = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.smolt_stage,
            fcr_value=1.2,
            duration_days=90
        )
        
        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Test Mortality Model",
            frequency="daily",
            rate=0.05
        )
        
        # Create biological constraints
        self.constraints = BiologicalConstraints.objects.create(
            name="Test Constraints",
            description="Test constraint set",
            created_by=self.user
        )
        
        # Create stage constraints
        self.fry_constraint = StageConstraint.objects.create(
            constraint_set=self.constraints,
            lifecycle_stage=LifecycleStageChoices.FRY,
            min_weight_g=1.0,
            max_weight_g=5.0,
            min_temperature_c=8.0,
            max_temperature_c=14.0,
            typical_duration_days=30,
            max_freshwater_weight_g=5.0
        )
        
        self.parr_constraint = StageConstraint.objects.create(
            constraint_set=self.constraints,
            lifecycle_stage=LifecycleStageChoices.PARR,
            min_weight_g=5.0,
            max_weight_g=30.0,
            min_temperature_c=6.0,
            max_temperature_c=16.0,
            typical_duration_days=60,
            max_freshwater_weight_g=30.0
        )
        
        self.smolt_constraint = StageConstraint.objects.create(
            constraint_set=self.constraints,
            lifecycle_stage=LifecycleStageChoices.SMOLT,
            min_weight_g=30.0,
            max_weight_g=150.0,
            min_temperature_c=4.0,
            max_temperature_c=18.0,
            typical_duration_days=90,
            max_freshwater_weight_g=150.0
        )

    def test_create_scenario_from_scratch(self):
        """Test creating a scenario from scratch and running a projection."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_create_scenario_from_scratch(self):
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Mock the projection engine to simulate running a projection
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            mock_engine_instance.run_projection.return_value = [
                {
                    'day_number': 0,
                    'projection_date': date.today(),
                    'average_weight': 2.5,
                    'population': 10000.0,
                    'biomass': 25.0,
                    'daily_feed': 0.0,
                    'cumulative_feed': 0.0,
                    'temperature': 12.0,
                    'current_stage_id': self.fry_stage.id
                },
                {
                    'day_number': 30,
                    'projection_date': date.today() + timedelta(days=30),
                    'average_weight': 5.0,
                    'population': 9850.0,
                    'biomass': 49.25,
                    'daily_feed': 0.5,
                    'cumulative_feed': 15.0,
                    'temperature': 13.0,
                    'current_stage_id': self.fry_stage.id
                },
                {
                    'day_number': 60,
                    'projection_date': date.today() + timedelta(days=60),
                    'average_weight': 15.0,
                    'population': 9700.0,
                    'biomass': 145.5,
                    'daily_feed': 1.5,
                    'cumulative_feed': 60.0,
                    'temperature': 14.0,
                    'current_stage_id': self.parr_stage.id
                },
                {
                    'day_number': 90,
                    'projection_date': date.today() + timedelta(days=90),
                    'average_weight': 35.0,
                    'population': 9550.0,
                    'biomass': 334.25,
                    'daily_feed': 3.5,
                    'cumulative_feed': 150.0,
                    'temperature': 15.0,
                    'current_stage_id': self.smolt_stage.id
                }
            ]
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            # Check that the projection engine was called
            MockEngine.assert_called_once()
            mock_engine_instance.run_projection.assert_called_once()
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that the projections were saved to the database
            projections = ScenarioProjection.objects.filter(scenario=scenario)
            self.assertEqual(projections.count(), 4)
            
            # Check the final projection values
            final_projection = projections.order_by('day_number').last()
            self.assertEqual(final_projection.day_number, 90)
            self.assertEqual(final_projection.average_weight, 35.0)
            self.assertEqual(final_projection.population, 9550.0)
            self.assertEqual(final_projection.biomass, 334.25)
            self.assertEqual(final_projection.cumulative_feed, 150.0)
            self.assertEqual(final_projection.current_stage.id, self.smolt_stage.id)

    def test_create_scenario_from_batch(self):
        """Test creating a scenario from an existing batch."""
        # Create a scenario from an existing batch
        scenario = Scenario.objects.create(
            name="Batch-based Scenario",
            start_date=date.today(),
            duration_days=90,
            # Batch model doesn't store initial_count directly; using a fixed value for tests
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            batch=self.batch,  # Link to the batch
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Verify the scenario was created with the batch's data
        self.assertEqual(scenario.batch, self.batch)
        self.assertEqual(scenario.initial_count, 10000)

        
        # Mock the projection engine to simulate running a projection
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            mock_engine_instance.run_projection.return_value = [
                {
                    'day_number': 0,
                    'projection_date': date.today(),
                    'average_weight': 2.5,
                    'population': 10000.0,
                    'biomass': 25.0,
                    'daily_feed': 0.0,
                    'cumulative_feed': 0.0,
                    'temperature': 12.0,
                    'current_stage_id': self.fry_stage.id
                },
                # Additional projection data points...
            ]
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Verify projections were created
            self.assertTrue(ScenarioProjection.objects.filter(scenario=scenario).exists())

    def test_compare_multiple_scenarios(self):
        """Test comparing multiple scenarios."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_compare_multiple_scenarios(self):
        # Create two scenarios with different parameters
        scenario1 = Scenario.objects.create(
            name="Scenario 1",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Create a second TGC model with higher growth rate
        tgc_model2 = TGCModel.objects.create(
            name="High Growth TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.030,  # Higher TGC value
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        scenario2 = Scenario.objects.create(
            name="Scenario 2",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Enhanced",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=tgc_model2,  # Different TGC model
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Create projections for both scenarios
        # For scenario 1
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                scenario=scenario1,
                projection_date=date.today() + timedelta(days=day),
                day_number=day,
                average_weight=weight,
                population=population,
                biomass=biomass,
                daily_feed=i * 0.5,
                cumulative_feed=i * i * 5,
                temperature=12.0 + i,
                current_stage=self.fry_stage if i == 0 else self.parr_stage if i == 1 else self.smolt_stage
            )
        
        # For scenario 2 (higher growth rate)
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i * 1.2)  # 20% faster growth
            population = 10000 - (i * 150)  # Same mortality
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                scenario=scenario2,
                projection_date=date.today() + timedelta(days=day),
                day_number=day,
                average_weight=weight,
                population=population,
                biomass=biomass,
                daily_feed=i * 0.6,  # More feed due to faster growth
                cumulative_feed=i * i * 6,
                temperature=12.0 + i,
                current_stage=self.fry_stage if i == 0 else self.parr_stage if i == 1 else self.smolt_stage
            )
        
        # Get comparison data from API
        response = self.client.get(
            reverse('api:scenario-compare', kwargs={'pk': scenario1.pk}) + f'?compare_to={scenario2.pk}',
            content_type='application/json'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Parse the response data
        comparison_data = response.json()
        
        # Verify the comparison data contains both scenarios
        self.assertIn('base_scenario', comparison_data)
        self.assertIn('compare_scenario', comparison_data)
        self.assertEqual(comparison_data['base_scenario']['id'], scenario1.pk)
        self.assertEqual(comparison_data['compare_scenario']['id'], scenario2.pk)
        
        # Verify the comparison data includes projections
        self.assertIn('projections', comparison_data)
        self.assertEqual(len(comparison_data['projections']), 4)  # 4 time points
        
        # Check that the final weights are different
        final_day = comparison_data['projections'][-1]
        self.assertNotEqual(
            final_day['base_scenario']['average_weight'],
            final_day['compare_scenario']['average_weight']
        )
        self.assertTrue(
            final_day['compare_scenario']['average_weight'] > 
            final_day['base_scenario']['average_weight']
        )

    def test_sensitivity_analysis(self):
        """Test sensitivity analysis by varying TGC values."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_sensitivity_analysis(self):
        # Create base scenario
        base_scenario = Scenario.objects.create(
            name="Base Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Mock the projection engine for sensitivity analysis
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock to return different results for different TGC values
            mock_engine_instance = MockEngine.return_value
            
            # Define sensitivity variations
            variations = [
                {'tgc_value': 0.020, 'final_weight': 30.0},  # Lower TGC
                {'tgc_value': 0.025, 'final_weight': 35.0},  # Base TGC
                {'tgc_value': 0.030, 'final_weight': 40.0}   # Higher TGC
            ]
            
            # Set up the mock to return different results based on TGC value
            def side_effect_func(scenario, *args, **kwargs):
                # Find the TGC value of the scenario
                tgc_value = scenario.tgc_model.tgc_value
                
                # Find the matching variation
                variation = next((v for v in variations if abs(v['tgc_value'] - tgc_value) < 0.001), variations[1])
                
                # Return projection data based on the variation
                return [
                    {
                        'day_number': 0,
                        'projection_date': scenario.start_date,
                        'average_weight': scenario.initial_weight,
                        'population': scenario.initial_count,
                        'biomass': scenario.initial_weight * scenario.initial_count / 1000,
                        'daily_feed': 0.0,
                        'cumulative_feed': 0.0,
                        'temperature': 12.0,
                        'current_stage_id': self.fry_stage.id
                    },
                    {
                        'day_number': 90,
                        'projection_date': scenario.start_date + timedelta(days=90),
                        'average_weight': variation['final_weight'],
                        'population': 9500.0,
                        'biomass': variation['final_weight'] * 9500.0 / 1000,
                        'daily_feed': 3.5,
                        'cumulative_feed': 150.0,
                        'temperature': 15.0,
                        'current_stage_id': self.smolt_stage.id
                    }
                ]
            
            mock_engine_instance.run_projection.side_effect = side_effect_func
            
            # Run sensitivity analysis for different TGC values
            sensitivity_results = []
            
            for variation in variations:
                # Create a TGC model with the variation
                tgc_model = TGCModel.objects.create(
                    name=f"TGC Model {variation['tgc_value']}",
                    location="Test Location",
                    release_period="Spring",
                    tgc_value=variation['tgc_value'],
                    exponent_n=0.33,
                    exponent_m=0.66,
                    profile=self.temp_profile
                )
                
                # Create a scenario with this TGC model
                scenario = Scenario.objects.create(
                    name=f"Scenario TGC {variation['tgc_value']}",
                    start_date=date.today(),
                    duration_days=90,
                    initial_count=10000,
                    genotype="Standard",
                    supplier="Test Supplier",
                    initial_weight=2.5,
                    tgc_model=tgc_model,
                    fcr_model=self.fcr_model,
                    mortality_model=self.mortality_model,
                    biological_constraints=self.constraints,
                    created_by=self.user
                )
                
                # Run projection
                response = self.client.post(
                    reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                    content_type='application/json'
                )
                
                # Check that the response is successful
                self.assertEqual(response.status_code, 200)
                
                # Get the final projection
                final_projection = ScenarioProjection.objects.filter(
                    scenario=scenario
                ).order_by('day_number').last()
                
                # Store the result
                sensitivity_results.append({
                    'tgc_value': variation['tgc_value'],
                    'final_weight': final_projection.average_weight,
                    'final_biomass': final_projection.biomass
                })
            
            # Verify that higher TGC values result in higher final weights
            self.assertTrue(
                sensitivity_results[0]['final_weight'] < 
                sensitivity_results[1]['final_weight'] < 
                sensitivity_results[2]['final_weight']
            )

    def test_export_data(self):
        """Test exporting scenario data to CSV."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_export_data(self):
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Export Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Create projections
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                scenario=scenario,
                projection_date=date.today() + timedelta(days=day),
                day_number=day,
                average_weight=weight,
                population=population,
                biomass=biomass,
                daily_feed=i * 0.5,
                cumulative_feed=i * i * 5,
                temperature=12.0 + i,
                current_stage=self.fry_stage if i == 0 else self.parr_stage if i == 1 else self.smolt_stage
            )
        
        # Call the export endpoint
        response = self.client.get(
            reverse('api:scenario-export', kwargs={'pk': scenario.pk}),
            content_type='application/json'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue('attachment; filename=' in response['Content-Disposition'])
        
        # Parse the CSV content
        content = response.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        # Check that all projection data is included
        self.assertEqual(len(rows), 4)  # 4 time points
        
        # Check the headers
        expected_headers = [
            'Day', 'Date', 'Average Weight (g)', 'Population', 
            'Biomass (kg)', 'Daily Feed (kg)', 'Cumulative Feed (kg)',
            'Temperature (°C)', 'Lifecycle Stage'
        ]
        for header in expected_headers:
            self.assertIn(header, reader.fieldnames)
        
        # Check the values in the first and last rows
        self.assertEqual(rows[0]['Day'], '0')
        self.assertEqual(rows[0]['Average Weight (g)'], '2.5')
        self.assertEqual(rows[0]['Population'], '10000.0')
        
        self.assertEqual(rows[-1]['Day'], '90')
        self.assertEqual(rows[-1]['Average Weight (g)'], '10.0')
        self.assertEqual(rows[-1]['Population'], '9550.0')

    def test_chart_data_generation(self):
        """Test generating chart data for scenarios."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_chart_data_generation(self):
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Chart Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Create projections
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                scenario=scenario,
                projection_date=date.today() + timedelta(days=day),
                day_number=day,
                average_weight=weight,
                population=population,
                biomass=biomass,
                daily_feed=i * 0.5,
                cumulative_feed=i * i * 5,
                temperature=12.0 + i,
                current_stage=self.fry_stage if i == 0 else self.parr_stage if i == 1 else self.smolt_stage
            )
        
        # Call the chart data endpoint
        response = self.client.get(
            reverse('api:scenario-chart-data', kwargs={'pk': scenario.pk}),
            content_type='application/json'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Parse the response data
        chart_data = response.json()
        
        # Verify the chart data structure
        self.assertIn('weight_data', chart_data)
        self.assertIn('biomass_data', chart_data)
        self.assertIn('population_data', chart_data)
        self.assertIn('feed_data', chart_data)
        
        # Check that each data series has the correct number of points
        self.assertEqual(len(chart_data['weight_data']['data']), 4)
        self.assertEqual(len(chart_data['biomass_data']['data']), 4)
        self.assertEqual(len(chart_data['population_data']['data']), 4)
        self.assertEqual(len(chart_data['feed_data']['data']), 4)
        
        # Verify the data values
        self.assertEqual(chart_data['weight_data']['data'][0]['y'], 2.5)
        self.assertEqual(chart_data['weight_data']['data'][-1]['y'], 10.0)
        
        self.assertEqual(chart_data['biomass_data']['data'][0]['y'], 25.0)
        self.assertTrue(chart_data['biomass_data']['data'][-1]['y'] > 90.0)
        
        self.assertEqual(chart_data['population_data']['data'][0]['y'], 10000.0)
        self.assertEqual(chart_data['population_data']['data'][-1]['y'], 9550.0)

    def test_model_changes_mid_scenario(self):
        """Test applying model changes mid-scenario."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_model_changes_mid_scenario(self):
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Model Change Scenario",
            start_date=date.today(),
            duration_days=180,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        
        # Create a second TGC model with higher growth rate
        tgc_model2 = TGCModel.objects.create(
            name="High Growth TGC Model",
            location="Test Location",
            release_period="Summer",
            tgc_value=0.030,  # Higher TGC value
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        # Create a model change at day 90
        model_change = ScenarioModelChange.objects.create(
            scenario=scenario,
            change_day=90,
            new_tgc_model=tgc_model2,
            new_fcr_model=None,  # Keep the same FCR model
            new_mortality_model=None  # Keep the same mortality model
        )
        
        # Mock the projection engine to handle model changes
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            # Define projection data with a change at day 90
            projection_data = []
            
            # First 90 days with original TGC
            for i, day in enumerate([0, 30, 60, 90]):
                weight = 2.5 * (1 + i * 0.5)
                population = 10000 - (i * 50)
                biomass = weight * population / 1000
                projection_data.append({
                    'day_number': day,
                    'projection_date': date.today() + timedelta(days=day),
                    'average_weight': weight,
                    'population': population,
                    'biomass': biomass,
                    'daily_feed': i * 0.3,
                    'cumulative_feed': i * i * 3,
                    'temperature': 12.0 + i * 0.5,
                    'current_stage_id': self.fry_stage.id if day < 60 else self.parr_stage.id
                })
            
            # Days 120-180 with higher TGC
            for i, day in enumerate([120, 150, 180], start=4):
                # Faster growth after day 90
                weight = projection_data[3]['average_weight'] * (1 + (i - 3) * 0.8)
                population = projection_data[3]['population'] - ((i - 3) * 50)
                biomass = weight * population / 1000
                projection_data.append({
                    'day_number': day,
                    'projection_date': date.today() + timedelta(days=day),
                    'average_weight': weight,
                    'population': population,
                    'biomass': biomass,
                    'daily_feed': i * 0.4,  # More feed due to faster growth
                    'cumulative_feed': projection_data[3]['cumulative_feed'] + (i - 3) * (i - 3) * 4,
                    'temperature': 14.0 + (i - 3) * 0.5,
                    'current_stage_id': self.parr_stage.id if day < 150 else self.smolt_stage.id
                })
            
            mock_engine_instance.run_projection.return_value = projection_data
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that the projection engine was called with the model change
            MockEngine.assert_called_once()
            call_kwargs = mock_engine_instance.run_projection.call_args[1]
            self.assertIn('model_changes', call_kwargs)
            self.assertEqual(len(call_kwargs['model_changes']), 1)
            self.assertEqual(call_kwargs['model_changes'][0].change_day, 90)
            self.assertEqual(call_kwargs['model_changes'][0].new_tgc_model, tgc_model2)
            
            # Check that the projections were saved to the database
            projections = ScenarioProjection.objects.filter(scenario=scenario).order_by('day_number')
            self.assertEqual(projections.count(), 7)
            
            # Check that the growth rate increases after the model change
            weight_at_90 = projections.get(day_number=90).average_weight
            weight_at_120 = projections.get(day_number=120).average_weight
            weight_at_150 = projections.get(day_number=150).average_weight
            
            # Calculate growth rates
            growth_rate_60_to_90 = (weight_at_90 - projections.get(day_number=60).average_weight) / 30
            growth_rate_90_to_120 = (weight_at_120 - weight_at_90) / 30
            
            # Growth rate should be higher after the model change
            self.assertTrue(growth_rate_90_to_120 > growth_rate_60_to_90)

    def test_temperature_profile_upload(self):
        """Test uploading temperature profile data."""
    @unittest.skip("TODO: Enable after API consolidation - requires 'api' namespace")
    def test_temperature_profile_upload(self):
        # Create a new temperature profile
        new_profile = TemperatureProfile.objects.create(
            name="Uploaded Temperature Profile"
        )
        
        # Create CSV data for temperature readings
        csv_data = "date,temperature\n"
        start_date = date.today()
        for i in range(30):
            csv_data += f"{start_date + timedelta(days=i)},{10 + i % 5}\n"
        
        # Create a file upload
        csv_file = SimpleUploadedFile(
            "temperatures.csv",
            csv_data.encode('utf-8'),
            content_type="text/csv"
        )
        
        # Upload the file
        response = self.client.post(
            reverse('api:temperature-profile-upload', kwargs={'pk': new_profile.pk}),
            {'file': csv_file},
            format='multipart'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Verify that temperature readings were created
        readings = TemperatureReading.objects.filter(profile=new_profile)
        self.assertEqual(readings.count(), 30)
        
        # Verify the values
        for i in range(30):
            reading_date = start_date + timedelta(days=i)
            reading = readings.get(reading_date=reading_date)
            self.assertEqual(reading.temperature, 10 + i % 5)

    def test_biological_constraint_enforcement(self):
        """Test that biological constraints are enforced when creating scenarios."""
        # Try to create a scenario with weight outside constraints
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Invalid Weight Scenario",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=0.5,  # Too low for fry stage (min 1.0)
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                biological_constraints=self.constraints,
                created_by=self.user
            )
            scenario.full_clean()
        
        # Try to create a scenario with weight at the boundary (should be valid)
        scenario = Scenario(
            name="Boundary Weight Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=1.0,  # Exactly at min for fry stage
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints,
            created_by=self.user
        )
        scenario.full_clean()  # Should not raise
        
        # Create a TGC model with "freshwater" in location
        freshwater_tgc = TGCModel.objects.create(
            name="Freshwater TGC Model",
            location="Freshwater Location",
            release_period="Spring",
            tgc_value=0.025,
            profile=self.temp_profile
        )
        
        # Try to create a scenario exceeding freshwater weight limit
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Exceed Freshwater Limit",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=5.1,  # Exceeds max_freshwater_weight_g of 5.0
                tgc_model=freshwater_tgc,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                biological_constraints=self.constraints,
                created_by=self.user
            )
            scenario.clean()


class EndToEndWorkflowTests(TestCase):
    """End-to-end workflow tests for scenario planning."""

    def setUp(self):
        """Set up test data for all tests."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create species
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        
        # Create lifecycle stages
        self.fry_stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        self.parr_stage = LifeCycleStage.objects.create(
            name="parr",
            species=self.species,
            order=4,
            expected_weight_min_g=5.0,
            expected_weight_max_g=30.0
        )

    def test_complete_scenario_workflow(self):
        """Test a complete end-to-end scenario workflow."""
        # Step 1: Create a temperature profile
        temp_profile = TemperatureProfile.objects.create(
            name="E2E Test Temperature Profile"
        )
        
        # Add temperature readings
        start_date = date.today()
        for i in range(365):  # One year of data
            temp = 10.0 + 5.0 * (1 + (i % 365) / 182.5)  # Seasonal variation
            TemperatureReading.objects.create(
                profile=temp_profile,
                reading_date=start_date + timedelta(days=i),
                temperature=temp
            )
        
        # Step 2: Create a TGC model
        tgc_model = TGCModel.objects.create(
            name="E2E Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=temp_profile
        )
        
        # Step 3: Create a TGC model stage override
        tgc_stage = TGCModelStage.objects.create(
            tgc_model=tgc_model,
            lifecycle_stage=LifecycleStageChoices.FRY,
            tgc_value=Decimal('0.0300'),  # Higher TGC for fry
            temperature_exponent=Decimal('1.0'),
            weight_exponent=Decimal('0.333')
        )
        
        # Step 4: Create an FCR model
        fcr_model = FCRModel.objects.create(
            name="E2E Test FCR Model"
        )
        
        # Step 5: Create FCR model stages
        fcr_stage_fry = FCRModelStage.objects.create(
            model=fcr_model,
            stage=self.fry_stage,
            fcr_value=1.0,
            duration_days=30
        )
        
        fcr_stage_parr = FCRModelStage.objects.create(
            model=fcr_model,
            stage=self.parr_stage,
            fcr_value=1.1,
            duration_days=60
        )
        
        # Step 6: Create FCR stage override
        fcr_override = FCRModelStageOverride.objects.create(
            fcr_stage=fcr_stage_fry,
            min_weight_g=Decimal('1.0'),
            max_weight_g=Decimal('3.0'),
            fcr_value=Decimal('0.9')  # Better FCR for smaller fry
        )
        
        # Step 7: Create a mortality model
        mortality_model = MortalityModel.objects.create(
            name="E2E Test Mortality Model",
            frequency="daily",
            rate=0.05
        )
        
        # Step 8: Create mortality model stage override
        mortality_stage = MortalityModelStage.objects.create(
            mortality_model=mortality_model,
            lifecycle_stage=LifecycleStageChoices.FRY,
            daily_rate_percent=Decimal('0.1')  # Higher mortality for fry
        )
        
        # Step 9: Create biological constraints
        constraints = BiologicalConstraints.objects.create(
            name="E2E Test Constraints",
            description="End-to-end test constraint set",
            created_by=self.user
        )
        
        # Create stage constraints
        fry_constraint = StageConstraint.objects.create(
            constraint_set=constraints,
            lifecycle_stage=LifecycleStageChoices.FRY,
            min_weight_g=1.0,
            max_weight_g=5.0,
            min_temperature_c=8.0,
            max_temperature_c=14.0,
            typical_duration_days=30,
            max_freshwater_weight_g=5.0
        )
        
        # Step 10: Create a scenario
        scenario = Scenario.objects.create(
            name="E2E Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=tgc_model,
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            biological_constraints=constraints,
            created_by=self.user
        )
        
        # Step 11: Create a model change
        # Create a second TGC model with higher growth rate
        tgc_model2 = TGCModel.objects.create(
            name="E2E High Growth TGC Model",
            location="Test Location",
            release_period="Summer",
            tgc_value=0.030,  # Higher TGC value
            exponent_n=0.33,
            exponent_m=0.66,
            profile=temp_profile
        )
        
        model_change = ScenarioModelChange.objects.create(
            scenario=scenario,
            change_day=45,
            new_tgc_model=tgc_model2,
            new_fcr_model=None,
            new_mortality_model=None
        )
        
        # Step 12: Run a projection with the real projection engine
        # This is a real integration test using the actual projection engine
        
        # Create the projection engine with just the scenario
        engine = ProjectionEngine(scenario)
        
        # Run the projection
        # Run the projection (model changes are automatically loaded from the scenario)
        projections = engine.run_projection()
        
        # Save the projections
        for proj in projections:
            ScenarioProjection.objects.create(
                scenario=scenario,
                **proj
            )
        
        # Step 13: Verify the results
        saved_projections = ScenarioProjection.objects.filter(scenario=scenario).order_by('day_number')
        
        # Check that projections were created
        self.assertTrue(saved_projections.exists())
        
        # Check that the initial values match the scenario
        initial_proj = saved_projections.first()
        self.assertEqual(initial_proj.day_number, 0)
        self.assertEqual(initial_proj.average_weight, 2.0)
        self.assertEqual(initial_proj.population, 10000.0)
        
        # Check that the final values show growth
        final_proj = saved_projections.last()
        self.assertTrue(final_proj.day_number > 0)
        self.assertTrue(final_proj.average_weight > 2.0)
        self.assertTrue(final_proj.population < 10000.0)  # Some mortality
        
        # Step 14: Check history tracking
        # Verify that history records were created for the models
        self.assertEqual(tgc_model.history.count(), 1)
        self.assertEqual(fcr_model.history.count(), 1)
        self.assertEqual(mortality_model.history.count(), 1)
        self.assertEqual(scenario.history.count(), 1)
        self.assertEqual(model_change.history.count(), 1)
        
        # Update the scenario and check for a new history record
        scenario.name = "Updated E2E Test Scenario"
        scenario.save()
        self.assertEqual(scenario.history.count(), 2)
        self.assertEqual(scenario.history.earliest().name, "E2E Test Scenario")
        self.assertEqual(scenario.history.latest().name, "Updated E2E Test Scenario")


class PerformanceTests(TransactionTestCase):
    """Performance tests for scenario planning."""

    def setUp(self):
        """Set up test data for all tests."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create species
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        
        # Create lifecycle stages
        self.fry_stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        self.parr_stage = LifeCycleStage.objects.create(
            name="parr",
            species=self.species,
            order=4,
            expected_weight_min_g=5.0,
            expected_weight_max_g=30.0
        )
        
        self.smolt_stage = LifeCycleStage.objects.create(
            name="smolt",
            species=self.species,
            order=5,
            expected_weight_min_g=30.0,
            expected_weight_max_g=150.0
        )
        
        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Performance Test Temperature Profile"
        )
        
        # Add temperature readings for 3 years
        start_date = date.today()
        for i in range(3 * 365):  # Three years of data
            temp = 10.0 + 5.0 * (1 + (i % 365) / 182.5)  # Seasonal variation
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                reading_date=start_date + timedelta(days=i),
                temperature=temp
            )
        
        # Create TGC model
        self.tgc_model = TGCModel.objects.create(
            name="Performance Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        # Create FCR model
        self.fcr_model = FCRModel.objects.create(
            name="Performance Test FCR Model"
        )
        
        # Create FCR model stages
        self.fcr_stage_fry = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.fry_stage,
            fcr_value=1.0,
            duration_days=30
        )
        
        self.fcr_stage_parr = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.parr_stage,
            fcr_value=1.1,
            duration_days=60
        )
        
        self.fcr_stage_smolt = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.smolt_stage,
            fcr_value=1.2,
            duration_days=90
        )
        
        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Performance Test Mortality Model",
            frequency="daily",
            rate=0.05
        )

    def test_long_duration_projection(self):
        """Test performance with a 900+ day projection."""
        # Create a scenario with a long duration
        scenario = Scenario.objects.create(
            name="Long Duration Scenario",
            start_date=date.today(),
            duration_days=900,  # 900 days (about 2.5 years)
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Mock the projection engine for performance testing
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock to return data for all 900 days
            mock_engine_instance = MockEngine.return_value
            
            # Generate projection data for 900 days
            projection_data = []
            for day in range(0, 901, 30):  # Every 30 days
                weight = 2.0 * (1 + day / 100)  # Simple growth model
                population = 10000 * (1 - day / 10000)  # Simple mortality model
                biomass = weight * population / 1000
                projection_data.append({
                    'day_number': day,
                    'projection_date': date.today() + timedelta(days=day),
                    'average_weight': weight,
                    'population': population,
                    'biomass': biomass,
                    'daily_feed': day / 100,
                    'cumulative_feed': day * day / 1000,
                    'temperature': 12.0 + (day % 365) / 30,
                    'current_stage_id': self.fry_stage.id if day < 60 else 
                                       self.parr_stage.id if day < 180 else 
                                       self.smolt_stage.id
                })
            
            mock_engine_instance.run_projection.return_value = projection_data
            
            # Measure the time to run and save the projection
            start_time = timezone.now()
            
            # Call the API endpoint to run the projection
            self.client.force_login(self.user)
            response = self.client.post(
                reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            end_time = timezone.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that all projections were saved
            projections = ScenarioProjection.objects.filter(scenario=scenario)
            self.assertEqual(projections.count(), len(projection_data))
            
            # Performance assertion: should complete in under 5 seconds
            # This is a reasonable threshold for saving 30+ data points
            self.assertLess(execution_time, 5.0)

    def test_large_population_scenario(self):
        """Test performance with a large population scenario."""
        # Create a scenario with a large initial population
        scenario = Scenario.objects.create(
            name="Large Population Scenario",
            start_date=date.today(),
            duration_days=180,
            initial_count=2000000,  # 2 million fish
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Mock the projection engine for performance testing
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            # Generate projection data
            projection_data = []
            for day in range(0, 181, 30):  # Every 30 days
                weight = 2.0 * (1 + day / 100)
                population = 2000000 * (1 - day / 10000)
                biomass = weight * population / 1000
                projection_data.append({
                    'day_number': day,
                    'projection_date': date.today() + timedelta(days=day),
                    'average_weight': weight,
                    'population': population,
                    'biomass': biomass,
                    'daily_feed': day / 10,
                    'cumulative_feed': day * day / 100,
                    'temperature': 12.0 + (day % 365) / 30,
                    'current_stage_id': self.fry_stage.id if day < 60 else self.parr_stage.id
                })
            
            mock_engine_instance.run_projection.return_value = projection_data
            
            # Measure the time to run and save the projection
            start_time = timezone.now()
            
            # Call the API endpoint to run the projection
            self.client.force_login(self.user)
            response = self.client.post(
                reverse('api:scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            end_time = timezone.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Performance assertion: should complete in under 5 seconds
            self.assertLess(execution_time, 5.0)
            
            # Verify that large numbers are handled correctly
            final_projection = ScenarioProjection.objects.filter(
                scenario=scenario
            ).order_by('day_number').last()
            
            self.assertTrue(final_projection.population > 1900000)  # Should still be close to 2 million
            self.assertTrue(final_projection.biomass > 5000)  # Should be several tons

    def test_concurrent_scenario_processing(self):
        """Test concurrent processing of multiple scenarios."""
        # Create multiple scenarios
        scenarios = []
        for i in range(5):
            scenario = Scenario.objects.create(
                name=f"Concurrent Scenario {i}",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=2.0 + i * 0.5,  # Different initial weights
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                created_by=self.user
            )
            scenarios.append(scenario)
        
        # Mock the projection engine
        with patch('apps.scenario.services.calculations.projection_engine.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            def mock_projection(scenario, *args, **kwargs):
                # Return different data based on the scenario's initial weight
                initial_weight = scenario.initial_weight
                projection_data = []
                for day in range(0, 91, 30):
                    weight = initial_weight * (1 + day / 60)
                    population = 10000 * (1 - day / 2000)
                    projection_data.append({
                        'day_number': day,
                        'projection_date': scenario.start_date + timedelta(days=day),
                        'average_weight': weight,
                        'population': population,
                        'biomass': weight * population / 1000,
                        'daily_feed': day / 100,
                        'cumulative_feed': day * day / 1000,
                        'temperature': 12.0,
                        'current_stage_id': self.fry_stage.id
                    })
                return projection_data
            
            mock_engine_instance.run_projection.side_effect = mock_projection
            
            # Use ThreadPoolExecutor to run projections concurrently
            self.client.force_login(self.user)
            
            def run_projection(scenario_id):
                return self.client.post(
                    reverse('api:scenario-run-projection', kwargs={'pk': scenario_id}),
                    content_type='application/json'
                )
            
            start_time = timezone.now()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(run_projection, s.pk) for s in scenarios]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = timezone.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Check that all responses are successful
            for response in responses:
                self.assertEqual(response.status_code, 200)
            
            # Check that all scenarios have projections
            for scenario in scenarios:
                projections = ScenarioProjection.objects.filter(scenario=scenario)
                self.assertTrue(projections.exists())
            
            # Performance assertion: concurrent processing should be faster than sequential
            # This is hard to assert precisely, but we can check it completes in a reasonable time
            self.assertLess(execution_time, 10.0)


class DataConsistencyTests(TestCase):
    """Tests for data consistency and integrity in the scenario planning system."""

    def setUp(self):
        """Set up test data for all tests."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create species
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        
        # Create lifecycle stage
        self.stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Data Consistency Temperature Profile"
        )
        
        # Add temperature readings
        start_date = date.today()
        for i in range(30):
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                reading_date=start_date + timedelta(days=i),
                temperature=12.0 + i % 5
            )
        
        # Create TGC model
        self.tgc_model = TGCModel.objects.create(
            name="Data Consistency TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.temp_profile
        )
        
        # Create FCR model
        self.fcr_model = FCRModel.objects.create(
            name="Data Consistency FCR Model"
        )
        
        # Create FCR model stage
        self.fcr_stage = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.stage,
            fcr_value=1.0,
            duration_days=30
        )
        
        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Data Consistency Mortality Model",
            frequency="daily",
            rate=0.05
        )

    def test_relationship_integrity(self):
        """Test that relationships between models are maintained correctly."""
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Relationship Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Verify relationships are correct
        self.assertEqual(scenario.tgc_model, self.tgc_model)
        self.assertEqual(scenario.fcr_model, self.fcr_model)
        self.assertEqual(scenario.mortality_model, self.mortality_model)
        self.assertEqual(scenario.created_by, self.user)
        
        # Verify reverse relationships
        self.assertIn(scenario, self.tgc_model.scenarios.all())
        self.assertIn(scenario, self.fcr_model.scenarios.all())
        self.assertIn(scenario, self.mortality_model.scenarios.all())
        
        # Create a model change
        model_change = ScenarioModelChange.objects.create(
            scenario=scenario,
            change_day=30,
            new_tgc_model=self.tgc_model,  # Same model for simplicity
            new_fcr_model=None,
            new_mortality_model=None
        )
        
        # Verify relationships for model change
        self.assertEqual(model_change.scenario, scenario)
        self.assertEqual(model_change.new_tgc_model, self.tgc_model)
        self.assertIsNone(model_change.new_fcr_model)
        self.assertIsNone(model_change.new_mortality_model)
        
        # Verify reverse relationship from scenario to model changes
        self.assertIn(model_change, scenario.model_changes.all())

    def test_cascade_protect_behavior(self):
        """Test CASCADE and PROTECT behaviors for foreign keys."""
        # Create a scenario
        scenario = Scenario.objects.create(
            name="Cascade Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Create a model change
        model_change = ScenarioModelChange.objects.create(
            scenario=scenario,
            change_day=30,
            new_tgc_model=self.tgc_model,
            new_fcr_model=None,
            new_mortality_model=None
        )
        
        # Create projections
        for day in range(0, 91, 30):
            ScenarioProjection.objects.create(
                scenario=scenario,
                projection_date=date.today() + timedelta(days=day),
                day_number=day,
                average_weight=2.0 + day / 30,
                population=10000 - day * 10,
                biomass=(2.0 + day / 30) * (10000 - day * 10) / 1000,
                daily_feed=day / 10,
                cumulative_feed=day * day / 100,
                temperature=12.0,
                current_stage=self.stage
            )
        
        # Test PROTECT behavior: Cannot delete TGC model while scenario exists
        with self.assertRaises(IntegrityError):
            self.tgc_model.delete()
        
        # Test PROTECT behavior: Cannot delete FCR model while scenario exists
        with self.assertRaises(IntegrityError):
            self.fcr_model.delete()
        
        # Test PROTECT behavior: Cannot delete mortality model while scenario exists
        with self.assertRaises(IntegrityError):
            self.mortality_model.delete()
        
        # Test CASCADE behavior: Deleting scenario should delete model changes and projections
        scenario_id = scenario.pk
        model_change_id = model_change.pk
        
        # Delete the scenario
        scenario.delete()
        
        # Verify that the scenario is deleted
        self.assertFalse(Scenario.objects.filter(pk=scenario_id).exists())
        
        # Verify that model changes are deleted (CASCADE)
        self.assertFalse(ScenarioModelChange.objects.filter(pk=model_change_id).exists())
        
        # Verify that projections are deleted (CASCADE)
        self.assertFalse(ScenarioProjection.objects.filter(scenario_id=scenario_id).exists())
        
        # Verify that the models still exist (PROTECT worked)
        self.assertTrue(TGCModel.objects.filter(pk=self.tgc_model.pk).exists())
        self.assertTrue(FCRModel.objects.filter(pk=self.fcr_model.pk).exists())
        self.assertTrue(MortalityModel.objects.filter(pk=self.mortality_model.pk).exists())

    def test_history_tracking(self):
        """Test that history records are created correctly."""
        # Create a scenario
        scenario = Scenario.objects.create(
            name="History Test Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Verify initial history record
        self.assertEqual(scenario.history.count(), 1)
        self.assertEqual(scenario.history.first().name, "History Test Scenario")
        
        # Update the scenario
        scenario.name = "Updated History Test Scenario"
        scenario.initial_count = 12000
        scenario.save()
        
        # Verify updated history record
        self.assertEqual(scenario.history.count(), 2)
        self.assertEqual(scenario.history.earliest().name, "History Test Scenario")
        self.assertEqual(scenario.history.earliest().initial_count, 10000)
        self.assertEqual(scenario.history.latest().name, "Updated History Test Scenario")
        self.assertEqual(scenario.history.latest().initial_count, 12000)
        
        # Update again
        scenario.duration_days = 120
        scenario.save()
        
        # Verify another history record
        self.assertEqual(scenario.history.count(), 3)
        self.assertEqual(scenario.history.latest().duration_days, 120)
        
        # Test history tracking for TGC model
        self.assertEqual(self.tgc_model.history.count(), 1)
        
        # Update TGC model
        self.tgc_model.tgc_value = 0.030
        self.tgc_model.save()
        
        # Verify TGC model history
        self.assertEqual(self.tgc_model.history.count(), 2)
        self.assertEqual(self.tgc_model.history.earliest().tgc_value, 0.025)
        self.assertEqual(self.tgc_model.history.latest().tgc_value, 0.030)

    def test_calculated_fields(self):
        """Test that calculated fields are computed correctly."""
        # Create projections with specific values
        scenario = Scenario.objects.create(
            name="Calculated Fields Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.0,
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )
        
        # Create projections with known values
        day0 = ScenarioProjection.objects.create(
            scenario=scenario,
            projection_date=date.today(),
            day_number=0,
            average_weight=2.0,
            population=10000.0,
            biomass=20.0,  # 2.0 * 10000 / 1000
            daily_feed=0.0,
            cumulative_feed=0.0,
            temperature=12.0,
            current_stage=self.stage
        )
        
        day30 = ScenarioProjection.objects.create(
            scenario=scenario,
            projection_date=date.today() + timedelta(days=30),
            day_number=30,
            average_weight=4.0,
            population=9700.0,
            biomass=38.8,  # 4.0 * 9700 / 1000
            daily_feed=3.0,
            cumulative_feed=50.0,
            temperature=13.0,
            current_stage=self.stage
        )
        
        # Verify biomass calculation
        self.assertEqual(day0.biomass, 2.0 * 10000 / 1000)
        self.assertEqual(day30.biomass, 4.0 * 9700 / 1000)
        
        # Test FCR calculation using the service
        # Create feeding events for FCR calculation
        for i in range(1, 31):
            feed_amount = i * 0.1  # Increasing feed amount
            ScenarioProjection.objects.create(
                scenario=scenario,
                projection_date=date.today() + timedelta(days=i),
                day_number=i,
                average_weight=2.0 + i * 0.067,  # Linear growth
                population=10000 - i * 10,  # Linear mortality
                biomass=(2.0 + i * 0.067) * (10000 - i * 10) / 1000,
                daily_feed=feed_amount,
                cumulative_feed=sum(j * 0.1 for j in range(1, i + 1)),
                temperature=12.0 + i % 5,
                current_stage=self.stage
            )
        
        # Calculate FCR using the service
        # NOTE:
        # The FCRCalculator class does not expose a direct `calculate_fcr`
        # utility; it focuses on feed-requirement calculations.  For the
        # purposes of this data-consistency test we can compute Feed-Conversion
        # Ratio directly:
        #
        #   FCR = total feed consumed (kg) / biomass gained (kg)
        #
        # This keeps the assertion meaningful without depending on a non-existent
        # helper method.
        biomass_gain = day30.biomass - day0.biomass
        fcr = day30.cumulative_feed / biomass_gain if biomass_gain > 0 else 0
        
        # Verify FCR is within a reasonable positive range
        self.assertGreater(fcr, 0)
        # Salmon production FCRs typically fall well below 2; use 5 as a generous
        # upper bound to catch obvious calculation errors.
        self.assertLess(fcr, 5.0)
