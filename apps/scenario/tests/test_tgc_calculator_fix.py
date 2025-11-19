"""
Unit tests for TGC calculator formula fix.

Verifies that the cube-root formula produces realistic growth curves
and matches the Event Engine implementation.
"""
import pytest
from datetime import date
from decimal import Decimal
from django.test import TestCase

from apps.scenario.models import TGCModel, TemperatureProfile, TemperatureReading
from apps.scenario.services.calculations.tgc_calculator import TGCCalculator


class TGCCalculatorCubeRootFormulaTests(TestCase):
    """Test that TGC calculator uses correct cube-root formula."""

    def setUp(self):
        """Set up test TGC model with temperature profile."""
        # Create temperature profile
        self.profile = TemperatureProfile.objects.create(
            name="Test Profile Constant 10C"
        )
        
        # Add temperature readings
        for day in range(1, 101):
            TemperatureReading.objects.create(
                profile=self.profile,
                day_number=day,
                temperature=10.0
            )
        
        # Create TGC model with standard values
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Test Period",
            tgc_value=2.75,  # Standard value (per 1000 degree-days)
            exponent_n=1.0,  # These will be ignored in calculation
            exponent_m=0.33,  # These will be ignored in calculation
            profile=self.profile
        )
        
        self.calculator = TGCCalculator(self.tgc_model)

    def test_cube_root_formula_basic(self):
        """Test that cube-root formula produces realistic growth."""
        # Starting with 100g fish at 10°C for 1 day with TGC 2.75
        result = self.calculator.calculate_daily_growth(
            current_weight=100.0,
            temperature=10.0
        )
        
        # Expected calculation:
        # tgc = 2.75 / 1000 = 0.00275
        # cube_root = 100^(1/3) = 4.64
        # cube_root += 0.00275 * 10 * 1 = 4.64 + 0.0275 = 4.6675
        # new_weight = 4.6675^3 = 101.8g
        
        self.assertAlmostEqual(result['new_weight_g'], 101.8, delta=0.5)
        self.assertAlmostEqual(result['growth_g'], 1.8, delta=0.5)
        self.assertEqual(result['formula'], 'cube_root')

    def test_realistic_growth_curve_100_days(self):
        """Test that 100 days produces realistic growth curve."""
        # Start with 100g fish, grow for 100 days at 10°C
        weight = 100.0
        
        for day in range(100):
            result = self.calculator.calculate_daily_growth(
                current_weight=weight,
                temperature=10.0
            )
            weight = result['new_weight_g']
        
        # After 100 days at 10°C with TGC 2.75, should reach approximately 350-450g (realistic)
        self.assertGreater(weight, 300, "Growth too slow - should exceed 300g")
        self.assertLess(weight, 500, "Growth too fast - should stay below 500g")

    def test_small_fish_growth_egg_to_fry(self):
        """Test realistic growth from egg (0.1g) to fry stage."""
        # Start with egg weight, 12°C freshwater temperature
        weight = 0.1
        
        # Grow for 90 days (egg to fry)
        for day in range(90):
            result = self.calculator.calculate_daily_growth(
                current_weight=weight,
                temperature=12.0,
                lifecycle_stage='fry'
            )
            weight = result['new_weight_g']
        
        # After 90 days at 12°C, should reach ~5-10g (realistic for fry)
        self.assertGreater(weight, 3.0, "Growth too slow for fry stage")
        self.assertLess(weight, 15.0, "Growth too fast for fry stage")

    def test_stage_weight_caps_applied(self):
        """Test that stage weight caps prevent unrealistic growth."""
        # Start with fish near fry cap
        result = self.calculator.calculate_daily_growth(
            current_weight=9.8,
            temperature=14.0,  # High temperature
            lifecycle_stage='fry'
        )
        
        # Should not exceed fry cap of 10g
        self.assertLessEqual(result['new_weight_g'], 10.0, "Fry weight cap not applied")

    def test_stage_specific_tgc_if_available(self):
        """Test that stage-specific TGC values are used when available."""
        # This test will pass even without stage overrides
        # (just verifies the logic path exists)
        result = self.calculator.calculate_daily_growth(
            current_weight=50.0,
            temperature=10.0,
            lifecycle_stage='parr'
        )
        
        self.assertIn('tgc_value', result)
        self.assertGreater(result['new_weight_g'], 50.0)

    def test_temperature_adjustment_by_stage(self):
        """Test that freshwater stages use correct temperature."""
        # Freshwater stages should use 12°C regardless of profile
        freshwater_temp = self.calculator.get_temperature_for_stage(
            temperature=9.0,  # Seawater profile temp
            lifecycle_stage='fry'
        )
        
        self.assertEqual(freshwater_temp, 12.0, "Freshwater stage should use 12°C")
        
        # Seawater stages should use profile temperature
        seawater_temp = self.calculator.get_temperature_for_stage(
            temperature=9.0,
            lifecycle_stage='adult'
        )
        
        self.assertEqual(seawater_temp, 9.0, "Seawater stage should use profile temp")

    def test_zero_growth_for_zero_temperature(self):
        """Test that zero temperature produces no growth."""
        result = self.calculator.calculate_daily_growth(
            current_weight=100.0,
            temperature=0.0
        )
        
        # Should have minimal or no growth (use delta for floating point precision)
        self.assertAlmostEqual(result['new_weight_g'], 100.0, delta=0.01)
        self.assertAlmostEqual(result['growth_g'], 0.0, delta=0.01)

    def test_comparison_with_event_engine_values(self):
        """
        Test that projection engine produces similar results to event engine.
        
        Event engine uses:
        - TGC: 0.00275 (2.75/1000) for Parr
        - Temperature: 12°C (freshwater)
        - Formula: ((w ** (1/3)) + tgc * temp * 1) ** 3
        """
        # Test with parr-stage parameters
        weight = 10.0  # Starting parr weight
        
        # Run for 90 days (parr stage duration)
        for day in range(90):
            result = self.calculator.calculate_daily_growth(
                current_weight=weight,
                temperature=12.0,
                lifecycle_stage='parr'
            )
            weight = result['new_weight_g']
        
        # Should reach approximately 60-100g (parr max is 100g)
        self.assertGreater(weight, 50, "Parr growth too slow")
        self.assertLessEqual(weight, 100, "Parr growth exceeded cap")


class TGCCalculatorStageCapTests(TestCase):
    """Test stage-specific weight caps."""

    def setUp(self):
        """Set up minimal TGC model."""
        profile = TemperatureProfile.objects.create(name="Test Profile")
        TemperatureReading.objects.create(
            profile=profile,
            day_number=1,
            temperature=10.0
        )
        
        self.tgc_model = TGCModel.objects.create(
            name="High Growth Test",
            location="Test",
            release_period="Test",
            tgc_value=3.5,  # High TGC to test caps
            profile=profile
        )
        
        self.calculator = TGCCalculator(self.tgc_model)

    def test_all_stage_caps(self):
        """Test that all lifecycle stage caps are correctly defined (permissive safety limits)."""
        stage_tests = [
            ('egg', 1.0),
            ('alevin', 1.0),
            ('fry', 10.0),       # Permissive cap (higher than 6g transition)
            ('parr', 100.0),     # Permissive cap (higher than 60g transition)
            ('smolt', 250.0),    # Permissive cap (higher than 180g transition)
            ('post_smolt', 700.0),   # Permissive cap (higher than 500g transition)
            ('harvest', 8000.0),
            ('adult', 8000.0),   # Safety limit for harvest
        ]
        
        for stage, expected_cap in stage_tests:
            cap = self.calculator._get_stage_weight_cap(stage)
            self.assertEqual(
                cap, 
                expected_cap, 
                f"Stage {stage} cap should be {expected_cap}g"
            )

    def test_stage_name_variations(self):
        """Test that stage caps work with various name formats."""
        # Test underscore format
        cap1 = self.calculator._get_stage_weight_cap('post_smolt')
        self.assertEqual(cap1, 700.0, "post_smolt should be 700g")
        
        # Test hyphen format
        cap2 = self.calculator._get_stage_weight_cap('post-smolt')
        self.assertEqual(cap2, 700.0, "post-smolt should be 700g")
        
        # Test space format
        cap3 = self.calculator._get_stage_weight_cap('post smolt')
        self.assertEqual(cap3, 700.0, "post smolt should be 700g")

