"""
Integration tests for scenario planning.

These tests verify end-to-end workflows and integration between components
of the scenario planning system.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.scenario.models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel,
    FCRModelStage, MortalityModel, Scenario,
    BiologicalConstraints, StageConstraint,
    ScenarioProjection, ProjectionRun, LifecycleStageChoices
)
from apps.batch.models import LifeCycleStage, Batch, Species

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
        for i in range(365):  # One year of data
            temp = 10.0 + 5.0 * (1 + (i % 365) / 182.5)  # Seasonal variation
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                day_number=i + 1,  # 1-based day numbers
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
        
        # Create projection runs for both scenarios
        # For scenario 1
        run1 = ProjectionRun.objects.create(
            scenario=scenario1,
            run_number=1,
            label='Test Run',
            parameters_snapshot={},
            created_by=self.user
        )
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                projection_run=run1,
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
        run1.total_projections = 4
        run1.final_weight_g = 2.5 * (1 + 3)
        run1.final_biomass_kg = (2.5 * (1 + 3)) * (10000 - (3 * 150)) / 1000
        run1.save()
        
        # For scenario 2 (higher growth rate)
        run2 = ProjectionRun.objects.create(
            scenario=scenario2,
            run_number=1,
            label='Test Run',
            parameters_snapshot={},
            created_by=self.user
        )
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i * 1.2)  # 20% faster growth
            population = 10000 - (i * 150)  # Same mortality
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                projection_run=run2,
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
        run2.total_projections = 4
        run2.final_weight_g = 2.5 * (1 + 3 * 1.2)
        run2.final_biomass_kg = (2.5 * (1 + 3 * 1.2)) * (10000 - (3 * 150)) / 1000
        run2.save()
        
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
        
        # Create projection run and projections
        run = ProjectionRun.objects.create(
            scenario=scenario,
            run_number=1,
            label='Test Run',
            parameters_snapshot={},
            created_by=self.user
        )
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                projection_run=run,
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
        run.total_projections = 4
        run.final_weight_g = 2.5 * (1 + 3)
        run.final_biomass_kg = (2.5 * (1 + 3)) * (10000 - (3 * 150)) / 1000
        run.save()
        
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
        
        # Create projection run and projections
        run = ProjectionRun.objects.create(
            scenario=scenario,
            run_number=1,
            label='Test Run',
            parameters_snapshot={},
            created_by=self.user
        )
        for i, day in enumerate([0, 30, 60, 90]):
            weight = 2.5 * (1 + i)
            population = 10000 - (i * 150)
            biomass = weight * population / 1000
            ScenarioProjection.objects.create(
                projection_run=run,
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
        run.total_projections = 4
        run.final_weight_g = 2.5 * (1 + 3)
        run.final_biomass_kg = (2.5 * (1 + 3)) * (10000 - (3 * 150)) / 1000
        run.save()
        
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
            day_number = i + 1  # 1-based day numbers
            reading = readings.get(day_number=day_number)
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


