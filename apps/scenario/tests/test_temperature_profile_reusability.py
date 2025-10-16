"""
Test temperature profile reusability across different scenario start dates.

This test verifies that temperature profiles can be reused across scenarios
with different start dates, ensuring that Day 1 of any scenario using the
same profile gets the same temperature value.
"""
from datetime import date
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.scenario.models import (
    TemperatureProfile, TemperatureReading, TGCModel,
    Scenario, ScenarioProjection, FCRModel, FCRModelStage,
    MortalityModel
)
from apps.batch.models import LifeCycleStage, Species
from apps.scenario.services.calculations.tgc_calculator import TGCCalculator
from apps.scenario.services.calculations.projection_engine import ProjectionEngine


class TemperatureProfileReusabilityTests(TestCase):
    """Test that temperature profiles work regardless of scenario start date."""

    def setUp(self):
        """Create test data."""
        # Create temperature profile with 100 days of data
        self.temp_profile = TemperatureProfile.objects.create(
            name="Reusability Test Profile"
        )

        # Add temperature readings with distinct pattern for testing
        for day_num in range(1, 101):  # 100 days
            temp = 10.0 + (day_num % 10) * 0.5  # 10.0, 10.5, 11.0, ..., 14.5, repeat
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                day_number=day_num,
                temperature=temp
            )

        # Create TGC model using this profile
        self.tgc_model = TGCModel.objects.create(
            name="Reusability Test TGC",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=1.8,
            exponent_m=-0.2,
            profile=self.temp_profile
        )

    def test_temperature_profile_reusable_across_start_dates(self):
        """Verify temperature profiles work regardless of scenario start date."""

        # Create species and lifecycle stage
        species = Species.objects.create(
            name='Test Species',
            scientific_name='Test scientific'
        )
        fry_stage = LifeCycleStage.objects.create(
            name='fry',
            species=species,
            order=1,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )

        # Create FCR and mortality models (required for scenarios)
        fcr_model = FCRModel.objects.create(name="Test FCR")
        FCRModelStage.objects.create(
            model=fcr_model,
            stage=fry_stage,
            fcr_value=1.0,
            duration_days=90
        )

        mortality_model = MortalityModel.objects.create(
            name="Test Mortality",
            rate=0.01,
            frequency='daily'
        )

        # Create user
        User = get_user_model()
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create two scenarios with DIFFERENT start dates but SAME TGC model
        scenario_jan = Scenario.objects.create(
            name="Jan Start Scenario",
            start_date=date(2024, 1, 1),
            duration_days=10,  # Very short duration for faster testing
            initial_count=10000,
            initial_weight=50.0,
            genotype="Test Genotype",
            supplier="Test Supplier",
            tgc_model=self.tgc_model,
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            created_by=user
        )

        scenario_apr = Scenario.objects.create(
            name="Apr Start Scenario",
            start_date=date(2024, 4, 1),  # Different start date!
            duration_days=10,
            initial_count=10000,
            initial_weight=50.0,
            genotype="Test Genotype",
            supplier="Test Supplier",
            tgc_model=self.tgc_model,  # SAME TGC model (same temp profile)
            fcr_model=fcr_model,
            mortality_model=mortality_model,
            created_by=user
        )

        # Test temperature lookup directly - this is the core functionality we fixed
        calculator_jan = TGCCalculator(scenario_jan.tgc_model)
        calculator_apr = TGCCalculator(scenario_apr.tgc_model)

        # Both scenarios should get the SAME temperature for Day 1
        # This proves the profile is reusable across different start dates
        temp_jan_day1 = calculator_jan._get_temperature_for_day(1)
        temp_apr_day1 = calculator_apr._get_temperature_for_day(1)

        # Get expected temperature for profile Day 1
        profile_day1_temp = self.temp_profile.readings.get(day_number=1).temperature

        # CRITICAL ASSERTIONS: Both calculators should return the same temperature
        self.assertEqual(
            temp_jan_day1, profile_day1_temp,
            "Jan scenario should use Profile Day 1 temperature"
        )
        self.assertEqual(
            temp_apr_day1, profile_day1_temp,
            "Apr scenario should use Profile Day 1 temperature"
        )
        self.assertEqual(
            temp_jan_day1, temp_apr_day1,
            "Both scenarios should get identical temperatures for Day 1"
        )

        # Test Day 5 as well to ensure consistency across the profile
        temp_jan_day5 = calculator_jan._get_temperature_for_day(5)
        temp_apr_day5 = calculator_apr._get_temperature_for_day(5)
        profile_day5_temp = self.temp_profile.readings.get(day_number=5).temperature

        self.assertEqual(temp_jan_day5, profile_day5_temp)
        self.assertEqual(temp_apr_day5, profile_day5_temp)
        self.assertEqual(temp_jan_day5, temp_apr_day5)

        # The profiles are now truly reusable!
        # This proves that changing from reading_date to day_number fixed the issue.

    def test_day_number_uniqueness_constraint(self):
        """Verify that day_number must be unique per profile."""
        # This should work
        TemperatureReading.objects.create(
            profile=self.temp_profile,
            day_number=101,  # New day number
            temperature=15.0
        )

        # This should fail (duplicate day_number for same profile)
        with self.assertRaises(IntegrityError):
            TemperatureReading.objects.create(
                profile=self.temp_profile,
                day_number=101,  # Duplicate
                temperature=16.0
            )

    def test_day_number_validation(self):
        """Verify day_number validation (must be >= 1)."""

        # Invalid day numbers
        for day_num in [0, -1, -100]:
            reading = TemperatureReading(
                profile=self.temp_profile,
                day_number=day_num,
                temperature=10.0
            )
            with self.assertRaises(ValidationError):
                reading.full_clean()

        # Valid day numbers - create separate profiles for each to avoid unique constraint
        for day_num in [1, 100, 900]:
            temp_profile = TemperatureProfile.objects.create(name=f"Test Profile {day_num}")
            reading = TemperatureReading(
                profile=temp_profile,
                day_number=day_num,
                temperature=10.0
            )
            reading.full_clean()  # Should not raise
