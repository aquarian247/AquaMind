"""
Tests for projection engine weight validation.

Tests ensure that scenarios with null or invalid initial_weight
are properly rejected with clear error messages.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, FCRModelStage, MortalityModel,
    TemperatureProfile, TemperatureReading
)
from apps.scenario.services.calculations.projection_engine import (
    ProjectionEngine
)
from apps.batch.models import Species, LifeCycleStage

User = get_user_model()


class ProjectionEngineWeightValidationTestCase(TestCase):
    """Test weight validation in ProjectionEngine."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

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

        # Create temperature profile with multiple readings
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Profile"
        )
        # Add temperature readings for a full year
        for day_offset in range(365):
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                reading_date=date(2024, 1, 1) + timedelta(days=day_offset),
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

    def test_projection_rejects_null_initial_weight(self):
        """Test that projection engine rejects scenarios with null weight."""
        # Create scenario without calling save() to bypass model validation
        scenario = Scenario(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=None,  # Explicitly null
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)

        # Engine should have errors
        self.assertTrue(len(engine.errors) > 0)
        self.assertIn("initial_weight", engine.errors[0])
        self.assertIn("starting weight", engine.errors[0].lower())

        # Run projection should fail
        result = engine.run_projection(save_results=False)
        self.assertFalse(result['success'])
        self.assertTrue(len(result['errors']) > 0)

    def test_projection_rejects_zero_initial_weight(self):
        """Test that projection engine rejects scenarios with zero weight."""
        # Create scenario without calling save() to bypass model validation
        scenario = Scenario(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=0.0,  # Zero weight
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)

        # Engine should have errors
        self.assertTrue(len(engine.errors) > 0)
        self.assertIn("greater than 0", engine.errors[0])

    def test_projection_rejects_negative_initial_weight(self):
        """Test projection engine rejects scenarios with negative weight."""
        # Create scenario without calling save() to bypass model validation
        scenario = Scenario(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=-5.0,  # Negative weight
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)

        # Engine should have errors
        self.assertTrue(len(engine.errors) > 0)
        self.assertIn("greater than 0", engine.errors[0])

    def test_projection_works_with_valid_initial_weight(self):
        """Test that projection engine works with valid weight."""
        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=10,  # Short duration for faster test
            initial_count=10000,
            initial_weight=5.0,  # Valid weight
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)

        # Engine should not have errors
        self.assertEqual(len(engine.errors), 0)

        # Run projection should succeed
        result = engine.run_projection(save_results=False)
        self.assertTrue(result['success'])
        self.assertTrue(len(result['projections']) > 0)

    def test_projection_error_message_is_helpful(self):
        """Test that error message provides helpful guidance."""
        # Create scenario without calling save() to bypass model validation
        scenario = Scenario(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=90,
            initial_count=10000,
            initial_weight=None,
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)

        # Error message should be helpful
        error_msg = engine.errors[0]
        self.assertIn("grams", error_msg.lower())
        # Should provide examples
        has_example = "50.0" in error_msg or "0.1" in error_msg
        self.assertTrue(
            has_example,
            "Error message should provide weight examples"
        )

    def test_projection_works_with_very_small_weight(self):
        """Test projection with very small valid weight (egg stage)."""
        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=10,
            initial_count=10000,
            initial_weight=0.1,  # Egg stage weight
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)
        self.assertEqual(len(engine.errors), 0)

        result = engine.run_projection(save_results=False)
        self.assertTrue(result['success'])

    def test_projection_works_with_large_weight(self):
        """Test projection with large valid weight (harvest ready)."""
        scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=10,
            initial_count=10000,
            initial_weight=5000.0,  # 5kg fish
            genotype="TestGenotype",
            supplier="TestSupplier",
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            created_by=self.user
        )

        engine = ProjectionEngine(scenario)
        self.assertEqual(len(engine.errors), 0)

        result = engine.run_projection(save_results=False)
        self.assertTrue(result['success'])

