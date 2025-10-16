"""
Tests for scenario serializer weight validation.

Tests ensure that the serializer properly validates initial_weight
requirements for new scenarios.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from datetime import date

from apps.scenario.api.serializers.scenario import ScenarioSerializer
from apps.scenario.models import (
    TGCModel, FCRModel, MortalityModel,
    TemperatureProfile, TemperatureReading
)
from apps.batch.models import Species, LifeCycleStage

User = get_user_model()


class ScenarioSerializerWeightValidationTestCase(TestCase):
    """Test weight validation in ScenarioSerializer."""

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
            order=1
        )

        # Create temperature profile
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Profile"
        )
        TemperatureReading.objects.create(
            profile=self.temp_profile,
            day_number=1,
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

        # Create FCR model
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR"
        )

        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Low Mortality",
            frequency="daily",
            rate=0.1
        )

        # Create request factory
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/api/v1/scenario/scenarios/')
        self.request.user = self.user

    def test_serializer_rejects_null_weight_for_new_scenario(self):
        """Test that serializer rejects null weight for new scenarios."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            # initial_weight is omitted (None)
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('initial_weight', serializer.errors)
        error_msg = str(serializer.errors['initial_weight'][0])
        self.assertIn('required', error_msg.lower())

    def test_serializer_accepts_valid_weight_for_new_scenario(self):
        """Test that serializer accepts valid weight for new scenarios."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 50.0,  # Valid weight
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_rejects_zero_weight(self):
        """Test that serializer rejects zero weight."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 0.0,  # Zero weight
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('initial_weight', serializer.errors)

    def test_serializer_rejects_negative_weight(self):
        """Test that serializer rejects negative weight."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': -5.0,  # Negative weight
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('initial_weight', serializer.errors)

    def test_serializer_rejects_extremely_small_weight(self):
        """Test that serializer rejects extremely small weight."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 0.001,  # Too small
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('initial_weight', serializer.errors)

    def test_serializer_rejects_extremely_large_weight(self):
        """Test that serializer rejects extremely large weight."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 15000.0,  # Too large (15kg)
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('initial_weight', serializer.errors)

    def test_serializer_accepts_small_valid_weight(self):
        """Test that serializer accepts small valid weight (egg stage)."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 0.1,  # Egg stage
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_accepts_large_valid_weight(self):
        """Test that serializer accepts large valid weight (harvest ready)."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            'initial_weight': 5000.0,  # 5kg fish
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_error_message_is_helpful(self):
        """Test that error message provides helpful guidance."""
        data = {
            'name': 'Test Scenario',
            'start_date': '2024-01-01',
            'duration_days': 90,
            'initial_count': 10000,
            # initial_weight is omitted
            'genotype': 'TestGenotype',
            'supplier': 'TestSupplier',
            'tgc_model': self.tgc_model.model_id,
            'fcr_model': self.fcr_model.model_id,
            'mortality_model': self.mortality_model.model_id
        }

        serializer = ScenarioSerializer(
            data=data,
            context={'request': self.request}
        )

        self.assertFalse(serializer.is_valid())
        error_msg = str(serializer.errors['initial_weight'][0])

        # Should provide helpful examples
        has_example = "50.0" in error_msg or "0.1" in error_msg
        self.assertTrue(
            has_example,
            "Error message should provide weight examples"
        )
        self.assertIn("grams", error_msg.lower())
