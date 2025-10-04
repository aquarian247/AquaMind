"""
Tests for ScenarioModelChange validation.

Comprehensive tests for change_day validation and boundary conditions.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date

from apps.scenario.models import (
    Scenario, ScenarioModelChange, TGCModel, FCRModel, MortalityModel,
    TemperatureProfile, TemperatureReading
)

User = get_user_model()


class ScenarioModelChangeValidationTestCase(TestCase):
    """Test ScenarioModelChange validation logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Profile"
        )
        TemperatureReading.objects.create(
            profile=self.temp_profile,
            reading_date=date(2024, 1, 1),
            temperature=12.0
        )

        # Create two TGC models
        self.tgc_model1 = TGCModel.objects.create(
            name="TGC Model 1",
            location="Location 1",
            release_period="January",
            tgc_value=0.025,
            profile=self.temp_profile
        )
        self.tgc_model2 = TGCModel.objects.create(
            name="TGC Model 2",
            location="Location 2",
            release_period="April",
            tgc_value=0.030,
            profile=self.temp_profile
        )

        # Create two FCR models
        self.fcr_model1 = FCRModel.objects.create(name="FCR Model 1")
        self.fcr_model2 = FCRModel.objects.create(name="FCR Model 2")

        # Create two mortality models
        self.mortality_model1 = MortalityModel.objects.create(
            name="Mortality Model 1",
            frequency="daily",
            rate=0.1
        )
        self.mortality_model2 = MortalityModel.objects.create(
            name="Mortality Model 2",
            frequency="daily",
            rate=0.2
        )

        # Create scenario
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date(2024, 1, 1),
            duration_days=180,
            initial_count=10000,
            initial_weight=5.0,
            genotype="Standard",
            supplier="Test Supplier",
            tgc_model=self.tgc_model1,
            fcr_model=self.fcr_model1,
            mortality_model=self.mortality_model1,
            created_by=self.user
        )

    def test_change_day_zero_rejected(self):
        """Test that change_day=0 is rejected."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=0,
            new_tgc_model=self.tgc_model2
        )

        with self.assertRaises(ValidationError) as cm:
            change.full_clean()

        error_msg = str(cm.exception)
        self.assertIn('change_day', error_msg)
        self.assertIn('at least 1', error_msg)

    def test_change_day_one_accepted(self):
        """Test that change_day=1 is accepted (first simulation day)."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=1,
            new_tgc_model=self.tgc_model2
        )

        # Should not raise
        change.full_clean()
        change.save()
        self.assertEqual(change.change_day, 1)

    def test_change_day_mid_simulation_accepted(self):
        """Test that mid-simulation changes are accepted."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=90,
            new_tgc_model=self.tgc_model2
        )

        change.full_clean()
        change.save()
        self.assertEqual(change.change_day, 90)

    def test_change_day_last_day_accepted(self):
        """Test that change on last day is accepted."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=180,  # Last day of 180-day scenario
            new_tgc_model=self.tgc_model2
        )

        change.full_clean()
        change.save()
        self.assertEqual(change.change_day, 180)

    def test_change_day_exceeds_duration_rejected(self):
        """Test that change_day beyond scenario duration is rejected."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=200,  # > 180 days
            new_tgc_model=self.tgc_model2
        )

        with self.assertRaises(ValidationError) as cm:
            change.full_clean()

        error_msg = str(cm.exception)
        self.assertIn('exceeds scenario duration', error_msg)

    def test_change_day_negative_rejected(self):
        """Test that negative change_day is rejected."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=-10,
            new_tgc_model=self.tgc_model2
        )

        with self.assertRaises(ValidationError):
            change.full_clean()

    def test_multiple_changes_at_different_days(self):
        """Test multiple changes at different days."""
        # Create first change
        ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=30,
            new_tgc_model=self.tgc_model2
        )

        # Create second change
        ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=60,
            new_fcr_model=self.fcr_model2
        )

        # Create third change
        ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=90,
            new_mortality_model=self.mortality_model2
        )

        self.assertEqual(self.scenario.model_changes.count(), 3)

    def test_error_message_is_helpful(self):
        """Test that error messages provide helpful guidance."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=0,
            new_tgc_model=self.tgc_model2
        )

        with self.assertRaises(ValidationError) as cm:
            change.full_clean()

        error_msg = str(cm.exception)
        # Should explain day 1 is first simulation day
        self.assertIn('Day 1', error_msg)
        self.assertIn('first', error_msg.lower())

    def test_at_least_one_model_required(self):
        """Test that at least one model must be specified."""
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=90
            # No models specified
        )

        with self.assertRaises(ValidationError) as cm:
            change.full_clean()

        error_msg = str(cm.exception)
        self.assertIn('At least one', error_msg)

    def test_single_model_change_allowed(self):
        """Test that changing just one model is allowed."""
        # Just TGC
        tgc_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=30,
            new_tgc_model=self.tgc_model2
        )
        self.assertIsNotNone(tgc_change.change_id)

        # Just FCR
        fcr_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=60,
            new_fcr_model=self.fcr_model2
        )
        self.assertIsNotNone(fcr_change.change_id)

        # Just Mortality
        mort_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=90,
            new_mortality_model=self.mortality_model2
        )
        self.assertIsNotNone(mort_change.change_id)