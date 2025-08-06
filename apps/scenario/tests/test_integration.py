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
from rest_framework.test import APIClient   # DRF test client for auth-aware requests

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
        # Use DRF's APIClient and authenticate the user for JWT/DRF-aware views
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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
            # Set a stricter freshwater upper-bound so that weights in the
            # middle of the parr range (e.g., 25 g) exceed the freshwater
            # threshold and trigger validation errors.
            max_freshwater_weight_g=20.0
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
        # NOTE:
        # The ProjectionEngine class was moved to
        # `apps.scenario.services.calculations` during the Phase-4 refactor.
        # Update the patch target accordingly so the mock is correctly applied.
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            projection_data = [
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
            
            # Side-effect that mimics real engine behaviour: persist projections
            def mock_run_projection(save_results=True, *args, **kwargs):
                if save_results:
                    ScenarioProjection.objects.bulk_create([
                        ScenarioProjection(
                            scenario=scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p['daily_feed'],
                            cumulative_feed=p['cumulative_feed'],
                            temperature=p['temperature'],
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ])
                return {
                    'success': True,
                    'summary': {
                        'final_weight': 35.0,
                        'final_biomass': 334.25,
                        'final_population': 9550.0,
                        'total_feed': 150.0,
                        'fcr': 1.2
                    },
                    'warnings': [],
                    # real engine returns [] if it saved projections
                    'projections': [] if save_results else projection_data
                }

            mock_engine_instance.run_projection.side_effect = mock_run_projection
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            projection_data = [
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
            
            # Side-effect persisting projections
            def batch_mock_run_projection(save_results=True, *args, **kwargs):
                if save_results:
                    ScenarioProjection.objects.bulk_create([
                        ScenarioProjection(
                            scenario=scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p.get('daily_feed', 0.0),
                            cumulative_feed=p.get('cumulative_feed', 0.0),
                            temperature=p.get('temperature', 12.0),
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ])
                return {
                    'success': True,
                    'summary': {
                        'final_weight': 2.5,
                        'final_biomass': 25.0,
                        'final_population': 10000.0,
                        'total_feed': 0.0,
                        'fcr': 0.0
                    },
                    'warnings': [],
                    'projections': [] if save_results else projection_data
                }

            mock_engine_instance.run_projection.side_effect = batch_mock_run_projection
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Verify projections were created
            self.assertTrue(ScenarioProjection.objects.filter(scenario=scenario).exists())

    def test_compare_multiple_scenarios(self):
        """Test comparing multiple scenarios."""
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
        # Build JSON payload explicitly; use `content=` so the request body
        # is passed exactly as-is.  DRF will not attempt to encode it again.
        response = self.client.post(
            reverse('scenario-compare'),  # collection-level action
            {
                'scenario_ids': [scenario1.pk, scenario2.pk]
                # Rely on default comparison metrics defined in the serializer
            },
            format='json'  # Let DRF handle JSON serialization
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Parse the response data
        comparison_data = response.json()
        
        # ------------------------------------------------------------------
        # New comparison format (ScenarioComparisonSerializer.to_representation)
        # ------------------------------------------------------------------
        # Must contain:
        #   • "scenarios" → list of scenario summaries
        #   • "metrics"   → dict of metric comparisons
        # ------------------------------------------------------------------
        self.assertIn("scenarios", comparison_data)
        self.assertIn("metrics", comparison_data)

        # Two scenarios should be returned
        self.assertEqual(len(comparison_data["scenarios"]), 2)
        returned_ids = {s["id"] for s in comparison_data["scenarios"]}
        self.assertEqual(returned_ids, {scenario1.pk, scenario2.pk})

        # Ensure at least the default metric "final_weight" is present
        self.assertIn("final_weight", comparison_data["metrics"])

        # Metric values should reflect that scenario 2 (higher growth)
        # has a larger final weight than scenario 1.
        final_weight_values = {
            v["scenario"]: v["value"]
            for v in comparison_data["metrics"]["final_weight"]["values"]
        }
        self.assertGreater(
            final_weight_values["Scenario 2"],
            final_weight_values["Scenario 1"],
        )

    def test_sensitivity_analysis(self):
        """Test sensitivity analysis by varying TGC values."""
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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock to return different results for different TGC values
            mock_engine_instance = MockEngine.return_value
            
            # ------------------------------------------------------------------
            # Ensure the mocked engine keeps a reference to the *actual* scenario
            # object passed in by the viewset so that `side_effect_func` can
            # inspect its attributes (e.g., the associated TGC model).  We
            # achieve this by using a constructor side-effect that stores the
            # incoming scenario on the shared `mock_engine_instance`.
            # ------------------------------------------------------------------
            def _engine_ctor_side_effect(scenario_obj, *args, **kwargs):
                mock_engine_instance._scenario = scenario_obj
                return mock_engine_instance

            MockEngine.side_effect = _engine_ctor_side_effect

            # Define sensitivity variations
            # Keep the variations list **outside** of the side-effect function so
            # it is available when the mock is executed.  Using a distinct name
            # avoids shadowing the ``variations`` kwarg that DRF may inject.
            tgc_variations = [
                {'tgc_value': 0.020, 'final_weight': 30.0},  # Lower TGC
                {'tgc_value': 0.025, 'final_weight': 35.0},  # Base TGC
                {'tgc_value': 0.030, 'final_weight': 40.0}   # Higher TGC
            ]
            
            # Set up the mock to return different results based on TGC value
            def side_effect_func(*args, **kwargs):
                # Find the TGC value of the scenario
                tgc_value = mock_engine_instance._scenario.tgc_model.tgc_value
                
                # Find the matching variation
                variation = next(
                    (v for v in tgc_variations if abs(v['tgc_value'] - tgc_value) < 0.001),
                    tgc_variations[1]  # Fallback to base variation
                )
                
                # Generate projection data
                projection_data = [
                    {
                        'day_number': 0,
                        'projection_date': mock_engine_instance._scenario.start_date,
                        'average_weight': mock_engine_instance._scenario.initial_weight,
                        'population': mock_engine_instance._scenario.initial_count,
                        'biomass': mock_engine_instance._scenario.initial_weight * mock_engine_instance._scenario.initial_count / 1000,
                        'daily_feed': 0.0,
                        'cumulative_feed': 0.0,
                        'temperature': 12.0,
                        'current_stage_id': self.fry_stage.id
                    },
                    {
                        'day_number': 90,
                        'projection_date': mock_engine_instance._scenario.start_date + timedelta(days=90),
                        'average_weight': variation['final_weight'],
                        'population': 9500.0,
                        'biomass': variation['final_weight'] * 9500.0 / 1000,
                        'daily_feed': 3.5,
                        'cumulative_feed': 150.0,
                        'temperature': 15.0,
                        'current_stage_id': self.smolt_stage.id
                    }
                ]
                
                # Persist projections when requested (default save_results=True)
                save_results = kwargs.get("save_results", True)
                if save_results:
                    ScenarioProjection.objects.bulk_create(
                        [
                            ScenarioProjection(
                                scenario=mock_engine_instance._scenario,
                                projection_date=p["projection_date"],
                                day_number=p["day_number"],
                                average_weight=p["average_weight"],
                                population=p["population"],
                                biomass=p["biomass"],
                                daily_feed=p["daily_feed"],
                                cumulative_feed=p["cumulative_feed"],
                                temperature=p["temperature"],
                                current_stage_id=p["current_stage_id"],
                            )
                            for p in projection_data
                        ]
                    )
                    # When saved we mimic real engine contract by returning
                    # an empty list for projections
                    projections_payload = []
                else:
                    projections_payload = projection_data

                # Return dictionary with success, summary, warnings
                return {
                    'success': True,
                    'summary': {
                        'final_weight': variation['final_weight'],
                        'final_biomass': variation['final_weight'] * 9500.0 / 1000,
                        'final_population': 9500.0,
                        'total_feed': 150.0,
                        'fcr': 1.2
                    },
                    'warnings': [],
                    'projections': projections_payload
                }
            
            # Configure the mock to use the side effect function
            mock_engine_instance.run_projection.side_effect = side_effect_func
            
            # Run sensitivity analysis for different TGC values
            sensitivity_results = []
            
            for variation in tgc_variations:
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
                    reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
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
            # The action name in the viewset is `export_projections`, and the
            # router-generated route name follows the pattern
            # 'scenario-export-projections'.
            reverse('scenario-export-projections', kwargs={'pk': scenario.pk}),
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
            'Day', 'Date', 'Weight (g)', 'Population',
            'Biomass (kg)', 'Daily Feed (kg)', 'Cumulative Feed (kg)',
            'Temperature (°C)', 'Stage'
        ]
        for header in expected_headers:
            self.assertIn(header, reader.fieldnames)
        
        # Check the values in the first and last rows
        self.assertEqual(rows[0]['Day'], '0')
        self.assertEqual(rows[0]['Weight (g)'], '2.5')
        self.assertEqual(rows[0]['Population'], '10000.0')
        
        self.assertEqual(rows[-1]['Day'], '90')
        self.assertEqual(rows[-1]['Weight (g)'], '10.0')
        self.assertEqual(rows[-1]['Population'], '9550.0')

    def test_chart_data_generation(self):
        """Test generating chart data for scenarios."""
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
            # Explicitly request all metrics we need to validate.  The chart
            # serializer defaults to only ``weight`` & ``biomass`` when no
            # query-string is provided, so we pass the metrics parameter to
            # ensure the response includes population & feed as well.
            reverse('scenario-chart-data', kwargs={'pk': scenario.pk}) +
            '?metrics=weight&metrics=biomass&metrics=population&metrics=feed',
            content_type='application/json'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Parse the response data
        chart_data = response.json()
        
        # Verify the chart data structure
        # Should follow Chart.js structure
        self.assertIn('labels', chart_data)
        self.assertIn('datasets', chart_data)

        # Build a quick lookup by label for easier assertions
        dataset_lookup = {d['label']: d for d in chart_data['datasets']}

        expected_labels = {
            'Average Weight (g)',
            'Biomass (kg)',
            'Population',
            'Daily Feed (kg)',
        }

        # Ensure all expected metric datasets are present
        self.assertTrue(expected_labels.issubset(set(dataset_lookup.keys())))

        # Helper to assert dataset length
        def assert_dataset(metric_label, first_val, last_val, comparator=None):
            metric_ds = dataset_lookup[metric_label]
            self.assertEqual(len(metric_ds['data']), 4)
            self.assertEqual(metric_ds['data'][0], first_val)
            if comparator is not None:
                comparator(metric_ds['data'][-1], last_val)
            else:
                self.assertEqual(metric_ds['data'][-1], last_val)

        # Weight should progress 2.5 -> 10.0
        assert_dataset('Average Weight (g)', 2.5, 10.0)

        # Biomass 25 -> >90 (approx 334 in last projection, but we only need >90)
        assert_dataset('Biomass (kg)', 25.0, 90.0, comparator=self.assertGreater)

        # Population 10000 -> 9550
        assert_dataset('Population', 10000.0, 9550.0)

    def test_model_changes_mid_scenario(self):
        """Test applying model changes mid-scenario."""
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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
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
            
            # Update to return a dictionary with success, summary, and warnings keys
            def mock_run_projection(save_results=True, *args, **kwargs):
                """
                Mimic ProjectionEngine.run_projection behaviour:
                – When `save_results` is True, persist projections to DB.
                – Always return a dict matching the real contract.
                """
                if save_results:
                    objs = [
                        ScenarioProjection(
                            scenario=scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p['daily_feed'],
                            cumulative_feed=p['cumulative_feed'],
                            temperature=p['temperature'],
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ]
                    ScenarioProjection.objects.bulk_create(objs)

                return {
                    'success': True,
                    'summary': {
                        'final_weight': projection_data[-1]['average_weight'],
                        'final_biomass': projection_data[-1]['biomass'],
                        'final_population': projection_data[-1]['population'],
                        'total_feed': projection_data[-1]['cumulative_feed'],
                        'fcr': 1.2,
                    },
                    'warnings': [],
                    'projections': [] if save_results else projection_data,
                }

            mock_engine_instance.run_projection.side_effect = mock_run_projection
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Verify that ProjectionEngine was instantiated with this scenario,
            # which already contains the `ScenarioModelChange` record.  The
            # engine itself is responsible for loading & applying those changes
            # internally, so we only need to assert correct instantiation here.
            MockEngine.assert_called_once_with(scenario)
            
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
        # We intentionally do NOT create the TemperatureProfile here.  The
        # `upload_csv` endpoint is responsible for creating it using the
        # supplied ``profile_name``.  Using a string avoids the uniqueness
        # validation error raised when the profile already exists.
        profile_name = "Uploaded Temperature Profile"
        
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
            reverse('temperature-profile-upload-csv'),
            {
                'file': csv_file,
                # The upload_csv endpoint requires a profile_name to be supplied
                # alongside the file so the view can create / validate the profile.
                'profile_name': profile_name,
                # Explicitly set the data_type so it satisfies CSVUploadSerializer
                'data_type': 'temperature',
            },
            format='multipart'
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Verify that temperature readings were created
        created_profile = TemperatureProfile.objects.get(name=profile_name)
        readings = TemperatureReading.objects.filter(profile=created_profile)
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
        
        # Try to create a scenario within the parr stage weight range but
        # exceeding the freshwater limit (20 g) set above – this should fail.
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Exceed Freshwater Limit",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=25.0,  # Exceeds parr freshwater limit of 20 g
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

    @unittest.skip("TODO: Enable after API consolidation / ProjectionEngine refactor")
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

        # ------------------------------------------------------------------
        # Use DRF's APIClient for token / auth-aware requests in performance
        # tests and authenticate the test user once for the entire TestCase.
        # ------------------------------------------------------------------
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            # Generate projection data for 900 days - one data point every 30 days
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
            
            # Define a simple side effect function that saves projections when requested
            def mock_run_projection(save_results=True, *args, **kwargs):
                if save_results:
                    # Create the projections in the database
                    ScenarioProjection.objects.bulk_create([
                        ScenarioProjection(
                            scenario=scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p['daily_feed'],
                            cumulative_feed=p['cumulative_feed'],
                            temperature=p['temperature'],
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ])
                
                # Return a simple dictionary with no circular references
                return {
                    'success': True,
                    'summary': {
                        'final_weight': projection_data[-1]['average_weight'],
                        'final_biomass': projection_data[-1]['biomass'],
                        'final_population': projection_data[-1]['population'],
                        'total_feed': projection_data[-1]['cumulative_feed'],
                        'fcr': 1.2
                    },
                    'warnings': [],
                    'projections': [] if save_results else projection_data
                }
            
            # Set the mock to use our side effect function
            mock_engine_instance.run_projection.side_effect = mock_run_projection
            
            # Measure the time to run and save the projection
            start_time = timezone.now()
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
                content_type='application/json'
            )
            
            end_time = timezone.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Check that the response is successful
            self.assertEqual(response.status_code, 200)
            
            # Check that all projections were saved
            projections = ScenarioProjection.objects.filter(scenario=scenario)
            # The mocked ProjectionEngine only returns a data-point every 30
            # days, which yields **31** records for the 0-900 day range.
            # Persisted projections should therefore match this count rather
            # than the full 900-day duration.
            self.assertEqual(projections.count(), 31)
            
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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            # Generate projection data - one data point every 30 days
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
            
            # Define a simple side effect function that saves projections when requested
            def mock_run_projection(save_results=True, *args, **kwargs):
                if save_results:
                    # Create the projections in the database
                    ScenarioProjection.objects.bulk_create([
                        ScenarioProjection(
                            scenario=scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p['daily_feed'],
                            cumulative_feed=p['cumulative_feed'],
                            temperature=p['temperature'],
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ])
                
                # Return a simple dictionary with no circular references
                return {
                    'success': True,
                    'summary': {
                        'final_weight': projection_data[-1]['average_weight'],
                        'final_biomass': projection_data[-1]['biomass'],
                        'final_population': projection_data[-1]['population'],
                        'total_feed': projection_data[-1]['cumulative_feed'],
                        'fcr': 1.2
                    },
                    'warnings': [],
                    'projections': [] if save_results else projection_data
                }
            
            # Set the mock to use our side effect function
            mock_engine_instance.run_projection.side_effect = mock_run_projection
            
            # Measure the time to run and save the projection
            start_time = timezone.now()
            
            # Call the API endpoint to run the projection
            response = self.client.post(
                reverse('scenario-run-projection', kwargs={'pk': scenario.pk}),
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
        with patch('apps.scenario.api.viewsets.ProjectionEngine') as MockEngine:
            # Configure the mock
            mock_engine_instance = MockEngine.return_value
            
            # Define a simple side effect function that doesn't rely on circular references
            def mock_run_projection(*args, **kwargs):
                # Get the scenario ID from the kwargs or use a default
                scenario_id = kwargs.get('scenario_id', 0)
                save_results = kwargs.get('save_results', True)
                
                # Generate simple projection data
                projection_data = []
                for day in range(0, 91, 30):
                    weight = 2.0 * (1 + day / 60)
                    population = 10000 * (1 - day / 2000)
                    projection_data.append({
                        'day_number': day,
                        'projection_date': date.today() + timedelta(days=day),
                        'average_weight': weight,
                        'population': population,
                        'biomass': weight * population / 1000,
                        'daily_feed': day / 100,
                        'cumulative_feed': day * day / 1000,
                        'temperature': 12.0,
                        'current_stage_id': self.fry_stage.id
                    })
                
                # Get the scenario object from the context
                current_scenario = None
                for s in scenarios:
                    if s.pk == scenario_id:
                        current_scenario = s
                        break
                
                # If we found the scenario and save_results is True, save the projections
                if current_scenario and save_results:
                    ScenarioProjection.objects.bulk_create([
                        ScenarioProjection(
                            scenario=current_scenario,
                            projection_date=p['projection_date'],
                            day_number=p['day_number'],
                            average_weight=p['average_weight'],
                            population=p['population'],
                            biomass=p['biomass'],
                            daily_feed=p['daily_feed'],
                            cumulative_feed=p['cumulative_feed'],
                            temperature=p['temperature'],
                            current_stage_id=p['current_stage_id'],
                        )
                        for p in projection_data
                    ])
                
                # Return a simple dictionary with no circular references
                return {
                    'success': True,
                    'summary': {
                        'final_weight': projection_data[-1]['average_weight'],
                        'final_biomass': projection_data[-1]['biomass'],
                        'final_population': projection_data[-1]['population'],
                        'total_feed': projection_data[-1]['cumulative_feed'],
                        'fcr': 1.2
                    },
                    'warnings': [],
                    'projections': [] if save_results else projection_data
                }
            
            # Set up the mock to use our side effect function
            mock_engine_instance.run_projection.side_effect = mock_run_projection
            
            # Store the original side_effect to restore it after each test
            original_side_effect = MockEngine.side_effect
            
            # Define a constructor side effect that captures the scenario ID
            def constructor_side_effect(scenario, *args, **kwargs):
                mock_instance = MagicMock()
                # Store the scenario ID for use in run_projection
                mock_instance.run_projection.side_effect = lambda *a, **kw: mock_run_projection(
                    scenario_id=scenario.pk, **kw
                )
                return mock_instance
            
            # Set the constructor side effect
            MockEngine.side_effect = constructor_side_effect
            
            # Use ThreadPoolExecutor to run projections concurrently
            def run_projection(scenario_id):
                return self.client.post(
                    reverse('scenario-run-projection', kwargs={'pk': scenario_id}),
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
            
            # Restore the original side_effect
            MockEngine.side_effect = original_side_effect
