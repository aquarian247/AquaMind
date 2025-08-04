"""
Tests for scenario planning models.

This module contains comprehensive tests for all models in the scenario planning app,
covering model creation, validation, relationships, and constraints.
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

from apps.scenario.models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel, 
    FCRModelStage, MortalityModel, Scenario, ScenarioModelChange,
    BiologicalConstraints, StageConstraint, TGCModelStage,
    FCRModelStageOverride, MortalityModelStage, LifecycleStageChoices
)
from apps.batch.models import LifeCycleStage, Batch, Species

User = get_user_model()


class TemperatureProfileModelTests(TestCase):
    """Tests for the TemperatureProfile model."""

    def setUp(self):
        """Set up test data."""
        self.profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )

    def test_string_representation(self):
        """Test the string representation of a TemperatureProfile."""
        self.assertEqual(str(self.profile), "Test Temperature Profile")

    def test_unique_name_constraint(self):
        """Test that profile names must be unique."""
        with self.assertRaises(IntegrityError):
            TemperatureProfile.objects.create(name="Test Temperature Profile")

    def test_name_max_length(self):
        """Test that name field respects max_length."""
        # Create a profile with a name at max length
        long_name = "X" * 255
        profile = TemperatureProfile.objects.create(name=long_name)
        self.assertEqual(profile.name, long_name)

        # Try to create a profile with a name that's too long
        too_long_name = "X" * 256
        with self.assertRaises(Exception):
            TemperatureProfile.objects.create(name=too_long_name)

    def test_timestamps_auto_creation(self):
        """Test that created_at and updated_at are automatically set."""
        self.assertIsNotNone(self.profile.created_at)
        self.assertIsNotNone(self.profile.updated_at)


class TemperatureReadingModelTests(TestCase):
    """Tests for the TemperatureReading model."""

    def setUp(self):
        """Set up test data."""
        self.profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.reading = TemperatureReading.objects.create(
            profile=self.profile,
            reading_date=date.today(),
            temperature=12.5
        )

    def test_string_representation(self):
        """Test the string representation of a TemperatureReading."""
        expected = f"Test Temperature Profile - {date.today()}: 12.5°C"
        self.assertEqual(str(self.reading), expected)

    def test_profile_relationship(self):
        """Test the relationship to TemperatureProfile."""
        self.assertEqual(self.reading.profile, self.profile)
        self.assertEqual(self.profile.readings.count(), 1)
        self.assertEqual(self.profile.readings.first(), self.reading)

    def test_unique_together_constraint(self):
        """Test that profile and reading_date must be unique together."""
        with self.assertRaises(IntegrityError):
            TemperatureReading.objects.create(
                profile=self.profile,
                reading_date=date.today(),
                temperature=13.0
            )

    def test_temperature_validation(self):
        """Test temperature field validation."""
        # Valid temperatures
        valid_temps = [-10.0, 0.0, 25.5, 35.0]
        for temp in valid_temps:
            reading = TemperatureReading(
                profile=self.profile,
                reading_date=date.today() + timedelta(days=len(valid_temps)),
                temperature=temp
            )
            reading.full_clean()  # Should not raise ValidationError
            reading.save()

        # Temperature readings should be ordered by date
        readings = self.profile.readings.all()
        self.assertEqual(len(readings), len(valid_temps) + 1)  # +1 for the setUp reading


class TGCModelTests(TestCase):
    """Tests for the TGCModel model."""

    def setUp(self):
        """Set up test data."""
        self.profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            exponent_n=0.33,
            exponent_m=0.66,
            profile=self.profile
        )

    def test_string_representation(self):
        """Test the string representation of a TGCModel."""
        expected = "Test TGC Model (Test Location)"
        self.assertEqual(str(self.tgc_model), expected)

    def test_field_validation(self):
        """Test field validation for TGCModel."""
        # Test tgc_value validation (must be positive)
        with self.assertRaises(ValidationError):
            model = TGCModel(
                name="Invalid TGC Model",
                location="Test Location",
                release_period="Spring",
                tgc_value=-0.025,  # Invalid negative value
                exponent_n=0.33,
                exponent_m=0.66,
                profile=self.profile
            )
            model.full_clean()

    def test_unique_name_constraint(self):
        """Test that model names must be unique."""
        with self.assertRaises(IntegrityError):
            TGCModel.objects.create(
                name="Test TGC Model",  # Duplicate name
                location="Another Location",
                release_period="Fall",
                tgc_value=0.030,
                exponent_n=0.33,
                exponent_m=0.66,
                profile=self.profile
            )

    def test_profile_relationship(self):
        """Test the relationship to TemperatureProfile."""
        self.assertEqual(self.tgc_model.profile, self.profile)
        self.assertEqual(self.profile.tgc_models.count(), 1)
        self.assertEqual(self.profile.tgc_models.first(), self.tgc_model)

    def test_history_tracking(self):
        """Test history tracking for TGCModel."""
        # Check that history record was created
        self.assertEqual(self.tgc_model.history.count(), 1)

        # Update the model and check for new history record
        self.tgc_model.tgc_value = 0.030
        self.tgc_model.save()
        self.assertEqual(self.tgc_model.history.count(), 2)

        # Check that history record contains the old value
        self.assertEqual(self.tgc_model.history.earliest().tgc_value, 0.025)
        self.assertEqual(self.tgc_model.history.latest().tgc_value, 0.030)


class FCRModelTests(TestCase):
    """Tests for the FCRModel and FCRModelStage models."""

    def setUp(self):
        """Set up test data."""
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        # Create FCR model
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR Model"
        )
        
        # Create FCR model stage
        self.fcr_stage = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.stage,
            fcr_value=1.2,
            duration_days=90
        )

    def test_fcr_model_string_representation(self):
        """Test the string representation of an FCRModel."""
        self.assertEqual(str(self.fcr_model), "Test FCR Model")

    def test_fcr_stage_string_representation(self):
        """Test the string representation of an FCRModelStage."""
        expected = f"Test FCR Model - {self.stage.name}: 1.2"
        self.assertEqual(str(self.fcr_stage), expected)

    def test_fcr_model_unique_name_constraint(self):
        """Test that FCR model names must be unique."""
        with self.assertRaises(IntegrityError):
            FCRModel.objects.create(name="Test FCR Model")

    def test_fcr_stage_validation(self):
        """Test validation for FCRModelStage."""
        # Test fcr_value validation (must be positive)
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                model=self.fcr_model,
                stage=self.stage,
                fcr_value=-1.2,  # Invalid negative value
                duration_days=90
            )
            stage.full_clean()

        # Test duration_days validation (must be positive)
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                model=self.fcr_model,
                stage=self.stage,
                fcr_value=1.2,
                duration_days=0  # Invalid zero value
            )
            stage.full_clean()

    def test_fcr_stage_unique_constraint(self):
        """Test that model and stage must be unique together."""
        with self.assertRaises(IntegrityError):
            FCRModelStage.objects.create(
                model=self.fcr_model,
                stage=self.stage,  # Duplicate stage for this model
                fcr_value=1.3,
                duration_days=60
            )

    def test_fcr_model_history_tracking(self):
        """Test history tracking for FCRModel."""
        # Check that history record was created
        self.assertEqual(self.fcr_model.history.count(), 1)

        # Update the model and check for new history record
        self.fcr_model.name = "Updated FCR Model"
        self.fcr_model.save()
        self.assertEqual(self.fcr_model.history.count(), 2)

        # Check that history record contains the old value
        self.assertEqual(self.fcr_model.history.earliest().name, "Test FCR Model")
        self.assertEqual(self.fcr_model.history.latest().name, "Updated FCR Model")


class MortalityModelTests(TestCase):
    """Tests for the MortalityModel model."""

    def setUp(self):
        """Set up test data."""
        self.mortality_model = MortalityModel.objects.create(
            name="Test Mortality Model",
            frequency="daily",
            rate=0.1
        )

    def test_string_representation(self):
        """Test the string representation of a MortalityModel."""
        expected = "Test Mortality Model (0.1% daily)"
        self.assertEqual(str(self.mortality_model), expected)

    def test_frequency_choices(self):
        """Test frequency choices validation."""
        # Valid frequencies
        valid_frequencies = ['daily', 'weekly']
        for i, freq in enumerate(valid_frequencies):
            model = MortalityModel.objects.create(
                name=f"Mortality Model {i}",
                frequency=freq,
                rate=0.1
            )
            self.assertEqual(model.frequency, freq)

        # Invalid frequency
        with self.assertRaises(ValidationError):
            model = MortalityModel(
                name="Invalid Frequency Model",
                frequency="monthly",  # Invalid choice
                rate=0.1
            )
            model.full_clean()

    def test_rate_bounds_validation(self):
        """Test rate bounds validation."""
        # Test lower bound (must be >= 0)
        with self.assertRaises(ValidationError):
            model = MortalityModel(
                name="Negative Rate Model",
                frequency="daily",
                rate=-0.1  # Invalid negative value
            )
            model.full_clean()

        # Test upper bound (must be <= 100)
        with self.assertRaises(ValidationError):
            model = MortalityModel(
                name="Excessive Rate Model",
                frequency="daily",
                rate=101.0  # Invalid value > 100
            )
            model.full_clean()

        # Test valid values at boundaries
        valid_rates = [0.0, 0.001, 50.0, 100.0]
        for i, rate in enumerate(valid_rates):
            model = MortalityModel.objects.create(
                name=f"Boundary Rate Model {i}",
                frequency="daily",
                rate=rate
            )
            self.assertEqual(model.rate, rate)

    def test_unique_name_constraint(self):
        """Test that model names must be unique."""
        with self.assertRaises(IntegrityError):
            MortalityModel.objects.create(
                name="Test Mortality Model",  # Duplicate name
                frequency="weekly",
                rate=0.5
            )

    def test_history_tracking(self):
        """Test history tracking for MortalityModel."""
        # Check that history record was created
        self.assertEqual(self.mortality_model.history.count(), 1)

        # Update the model and check for new history record
        self.mortality_model.rate = 0.2
        self.mortality_model.save()
        self.assertEqual(self.mortality_model.history.count(), 2)

        # Check that history record contains the old value
        self.assertEqual(self.mortality_model.history.earliest().rate, 0.1)
        self.assertEqual(self.mortality_model.history.latest().rate, 0.2)


class ScenarioModelTests(TestCase):
    """Tests for the Scenario model."""

    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        
        # Create a batch
        self.batch = Batch.objects.create(
            name="Test Batch",
            species=self.species,
            initial_count=10000,
            created_by=self.user
        )
        
        # Create temperature profile and TGC model
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            profile=self.temp_profile
        )
        
        # Create FCR model and stage
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR Model"
        )
        self.fcr_stage = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.stage,
            fcr_value=1.2,
            duration_days=90
        )
        
        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Test Mortality Model",
            frequency="daily",
            rate=0.1
        )
        
        # Create biological constraints
        self.constraints = BiologicalConstraints.objects.create(
            name="Test Constraints",
            description="Test constraint set",
            created_by=self.user
        )
        
        # Create stage constraint
        self.stage_constraint = StageConstraint.objects.create(
            constraint_set=self.constraints,
            lifecycle_stage=LifecycleStageChoices.FRY,
            min_weight_g=1.0,
            max_weight_g=5.0,
            min_temperature_c=8.0,
            max_temperature_c=14.0,
            typical_duration_days=30,
            max_freshwater_weight_g=5.0
        )
        
        # Create scenario
        self.scenario = Scenario.objects.create(
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
            batch=self.batch,
            biological_constraints=self.constraints,
            created_by=self.user
        )

    def test_string_representation(self):
        """Test the string representation of a Scenario."""
        self.assertEqual(str(self.scenario), "Test Scenario")

    def test_field_validation(self):
        """Test field validation for Scenario."""
        # Test duration_days validation (must be positive)
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Invalid Duration Scenario",
                start_date=date.today(),
                duration_days=0,  # Invalid zero value
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=2.5,
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model
            )
            scenario.full_clean()

        # Test initial_count validation (must be positive)
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Invalid Count Scenario",
                start_date=date.today(),
                duration_days=90,
                initial_count=0,  # Invalid zero value
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=2.5,
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model
            )
            scenario.full_clean()

        # Test initial_weight validation (must be positive if provided)
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Invalid Weight Scenario",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=-1.0,  # Invalid negative value
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model
            )
            scenario.full_clean()

    def test_clean_method_with_biological_constraints(self):
        """Test clean method with biological constraints."""
        # Test valid weight within constraints
        scenario = Scenario(
            name="Valid Constraint Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=3.0,  # Valid weight for fry stage (1.0-5.0)
            tgc_model=self.tgc_model,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints
        )
        scenario.clean()  # Should not raise ValidationError
        scenario.save()

        # Test invalid weight outside constraints
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Invalid Constraint Scenario",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=10.0,  # Invalid weight for fry stage (> 5.0)
                tgc_model=self.tgc_model,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                biological_constraints=self.constraints
            )
            scenario.clean()

        # Test freshwater limit constraint
        # Create a TGC model with "freshwater" in location
        freshwater_tgc = TGCModel.objects.create(
            name="Freshwater TGC Model",
            location="Freshwater Location",
            release_period="Spring",
            tgc_value=0.025,
            profile=self.temp_profile
        )

        # Test scenario with weight at freshwater limit
        scenario = Scenario(
            name="Freshwater Limit Scenario",
            start_date=date.today(),
            duration_days=90,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=5.0,  # At max_freshwater_weight_g limit
            tgc_model=freshwater_tgc,
            fcr_model=self.fcr_model,
            mortality_model=self.mortality_model,
            biological_constraints=self.constraints
        )
        scenario.clean()  # Should not raise ValidationError
        scenario.save()

        # Test scenario exceeding freshwater limit
        with self.assertRaises(ValidationError):
            scenario = Scenario(
                name="Exceed Freshwater Limit",
                start_date=date.today(),
                duration_days=90,
                initial_count=10000,
                genotype="Standard",
                supplier="Test Supplier",
                initial_weight=5.1,  # Exceeds max_freshwater_weight_g
                tgc_model=freshwater_tgc,
                fcr_model=self.fcr_model,
                mortality_model=self.mortality_model,
                biological_constraints=self.constraints
            )
            scenario.clean()

    def test_relationships(self):
        """Test relationships to batch and models."""
        self.assertEqual(self.scenario.batch, self.batch)
        self.assertEqual(self.scenario.tgc_model, self.tgc_model)
        self.assertEqual(self.scenario.fcr_model, self.fcr_model)
        self.assertEqual(self.scenario.mortality_model, self.mortality_model)
        self.assertEqual(self.scenario.biological_constraints, self.constraints)
        self.assertEqual(self.scenario.created_by, self.user)

    def test_history_tracking(self):
        """Test history tracking for Scenario."""
        # Check that history record was created
        self.assertEqual(self.scenario.history.count(), 1)

        # Update the scenario and check for new history record
        self.scenario.initial_count = 12000
        self.scenario.save()
        self.assertEqual(self.scenario.history.count(), 2)

        # Check that history record contains the old value
        self.assertEqual(self.scenario.history.earliest().initial_count, 10000)
        self.assertEqual(self.scenario.history.latest().initial_count, 12000)


class ScenarioModelChangeTests(TestCase):
    """Tests for the ScenarioModelChange model."""

    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        
        # Create temperature profile and TGC models
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.tgc_model1 = TGCModel.objects.create(
            name="TGC Model 1",
            location="Location 1",
            release_period="Spring",
            tgc_value=0.025,
            profile=self.temp_profile
        )
        self.tgc_model2 = TGCModel.objects.create(
            name="TGC Model 2",
            location="Location 2",
            release_period="Summer",
            tgc_value=0.030,
            profile=self.temp_profile
        )
        
        # Create FCR models
        self.fcr_model1 = FCRModel.objects.create(name="FCR Model 1")
        self.fcr_model2 = FCRModel.objects.create(name="FCR Model 2")
        
        # Create mortality models
        self.mortality_model1 = MortalityModel.objects.create(
            name="Mortality Model 1",
            frequency="daily",
            rate=0.1
        )
        self.mortality_model2 = MortalityModel.objects.create(
            name="Mortality Model 2",
            frequency="weekly",
            rate=0.5
        )
        
        # Create scenario
        self.scenario = Scenario.objects.create(
            name="Test Scenario",
            start_date=date.today(),
            duration_days=180,
            initial_count=10000,
            genotype="Standard",
            supplier="Test Supplier",
            initial_weight=2.5,
            tgc_model=self.tgc_model1,
            fcr_model=self.fcr_model1,
            mortality_model=self.mortality_model1,
            created_by=self.user
        )
        
        # Create scenario model change
        self.model_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=90,
            new_tgc_model=self.tgc_model2,
            new_fcr_model=self.fcr_model2,
            new_mortality_model=self.mortality_model2
        )

    def test_string_representation(self):
        """Test the string representation of a ScenarioModelChange."""
        expected = f"Test Scenario - Day 90 change"
        self.assertEqual(str(self.model_change), expected)

    def test_relationships(self):
        """Test relationships to Scenario and models."""
        self.assertEqual(self.model_change.scenario, self.scenario)
        self.assertEqual(self.model_change.new_tgc_model, self.tgc_model2)
        self.assertEqual(self.model_change.new_fcr_model, self.fcr_model2)
        self.assertEqual(self.model_change.new_mortality_model, self.mortality_model2)

    def test_change_day_validation(self):
        """Test change_day validation (must be positive)."""
        with self.assertRaises(ValidationError):
            change = ScenarioModelChange(
                scenario=self.scenario,
                change_day=-1,  # Invalid negative value
                new_tgc_model=self.tgc_model2
            )
            change.full_clean()

    def test_partial_model_changes(self):
        """Test that partial model changes are allowed."""
        # Change only TGC model
        tgc_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=30,
            new_tgc_model=self.tgc_model2,
            new_fcr_model=None,
            new_mortality_model=None
        )
        self.assertEqual(tgc_change.new_tgc_model, self.tgc_model2)
        self.assertIsNone(tgc_change.new_fcr_model)
        self.assertIsNone(tgc_change.new_mortality_model)

        # Change only FCR model
        fcr_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=60,
            new_tgc_model=None,
            new_fcr_model=self.fcr_model2,
            new_mortality_model=None
        )
        self.assertIsNone(fcr_change.new_tgc_model)
        self.assertEqual(fcr_change.new_fcr_model, self.fcr_model2)
        self.assertIsNone(fcr_change.new_mortality_model)

        # Change only mortality model
        mortality_change = ScenarioModelChange.objects.create(
            scenario=self.scenario,
            change_day=120,
            new_tgc_model=None,
            new_fcr_model=None,
            new_mortality_model=self.mortality_model2
        )
        self.assertIsNone(mortality_change.new_tgc_model)
        self.assertIsNone(mortality_change.new_fcr_model)
        self.assertEqual(mortality_change.new_mortality_model, self.mortality_model2)

    def test_history_tracking(self):
        """Test history tracking for ScenarioModelChange."""
        # Check that history record was created
        self.assertEqual(self.model_change.history.count(), 1)

        # Update the model change and check for new history record
        self.model_change.change_day = 100
        self.model_change.save()
        self.assertEqual(self.model_change.history.count(), 2)

        # Check that history record contains the old value
        self.assertEqual(self.model_change.history.earliest().change_day, 90)
        self.assertEqual(self.model_change.history.latest().change_day, 100)


class BiologicalConstraintsTests(TestCase):
    """Tests for the BiologicalConstraints and StageConstraint models."""

    def setUp(self):
        """Set up test data."""
        # Create a user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        
        # Create biological constraints
        self.constraints = BiologicalConstraints.objects.create(
            name="Test Constraints",
            description="Test constraint set",
            created_by=self.user
        )
        
        # Create stage constraints for different lifecycle stages
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

    def test_biological_constraints_string_representation(self):
        """Test the string representation of BiologicalConstraints."""
        self.assertEqual(str(self.constraints), "Test Constraints")

    def test_stage_constraint_string_representation(self):
        """Test the string representation of StageConstraint."""
        expected = "Test Constraints - Fry"
        self.assertEqual(str(self.fry_constraint), expected)

    def test_unique_name_constraint(self):
        """Test that constraint set names must be unique."""
        with self.assertRaises(IntegrityError):
            BiologicalConstraints.objects.create(
                name="Test Constraints",  # Duplicate name
                description="Another constraint set",
                created_by=self.user
            )

    def test_stage_constraint_unique_together(self):
        """Test that constraint_set and lifecycle_stage must be unique together."""
        with self.assertRaises(IntegrityError):
            StageConstraint.objects.create(
                constraint_set=self.constraints,
                lifecycle_stage=LifecycleStageChoices.FRY,  # Duplicate stage for this constraint set
                min_weight_g=0.8,
                max_weight_g=4.5,
                min_temperature_c=7.0,
                max_temperature_c=15.0
            )

    def test_weight_range_validation(self):
        """Test that min_weight_g must be less than max_weight_g."""
        with self.assertRaises(ValidationError):
            constraint = StageConstraint(
                constraint_set=self.constraints,
                lifecycle_stage=LifecycleStageChoices.SMOLT,
                min_weight_g=50.0,
                max_weight_g=40.0,  # Invalid: less than min_weight_g
                min_temperature_c=5.0,
                max_temperature_c=15.0
            )
            constraint.full_clean()

    def test_relationships(self):
        """Test relationships between BiologicalConstraints and StageConstraints."""
        self.assertEqual(self.fry_constraint.constraint_set, self.constraints)
        self.assertEqual(self.parr_constraint.constraint_set, self.constraints)
        self.assertEqual(self.constraints.stage_constraints.count(), 2)
        self.assertIn(self.fry_constraint, self.constraints.stage_constraints.all())
        self.assertIn(self.parr_constraint, self.constraints.stage_constraints.all())


class StageSpecificOverrideTests(TestCase):
    """Tests for TGCModelStage, FCRModelStageOverride, and MortalityModelStage models."""

    def setUp(self):
        """Set up test data."""
        # Create species and lifecycle stages
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.fry_stage = LifeCycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        self.smolt_stage = LifeCycleStage.objects.create(
            name="smolt",
            species=self.species,
            order=5,
            expected_weight_min_g=50.0,
            expected_weight_max_g=150.0
        )
        
        # Create temperature profile and TGC model
        self.temp_profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.tgc_model = TGCModel.objects.create(
            name="Test TGC Model",
            location="Test Location",
            release_period="Spring",
            tgc_value=0.025,
            profile=self.temp_profile
        )
        
        # Create TGC model stage override
        self.tgc_stage = TGCModelStage.objects.create(
            tgc_model=self.tgc_model,
            lifecycle_stage=LifecycleStageChoices.FRY,
            tgc_value=Decimal('0.0300'),
            temperature_exponent=Decimal('1.0'),
            weight_exponent=Decimal('0.333')
        )
        
        # Create FCR model and stage
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR Model"
        )
        self.fcr_stage = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=self.fry_stage,
            fcr_value=1.2,
            duration_days=30
        )
        
        # Create FCR model stage override
        self.fcr_override = FCRModelStageOverride.objects.create(
            fcr_stage=self.fcr_stage,
            min_weight_g=Decimal('1.0'),
            max_weight_g=Decimal('3.0'),
            fcr_value=Decimal('1.1')
        )
        
        # Create mortality model
        self.mortality_model = MortalityModel.objects.create(
            name="Test Mortality Model",
            frequency="daily",
            rate=0.1
        )
        
        # Create mortality model stage override
        self.mortality_stage = MortalityModelStage.objects.create(
            mortality_model=self.mortality_model,
            lifecycle_stage=LifecycleStageChoices.FRY,
            daily_rate_percent=Decimal('0.05')
        )

    def test_tgc_model_stage_string_representation(self):
        """Test the string representation of TGCModelStage."""
        expected = "Test TGC Model - Fry"
        self.assertEqual(str(self.tgc_stage), expected)

    def test_fcr_model_stage_override_string_representation(self):
        """Test the string representation of FCRModelStageOverride."""
        expected = f"{self.fcr_stage} (1.0g-3.0g): 1.1"
        self.assertEqual(str(self.fcr_override), expected)

    def test_mortality_model_stage_string_representation(self):
        """Test the string representation of MortalityModelStage."""
        expected = "Test Mortality Model - Fry"
        self.assertEqual(str(self.mortality_stage), expected)

    def test_tgc_model_stage_unique_constraint(self):
        """Test that tgc_model and lifecycle_stage must be unique together."""
        with self.assertRaises(IntegrityError):
            TGCModelStage.objects.create(
                tgc_model=self.tgc_model,
                lifecycle_stage=LifecycleStageChoices.FRY,  # Duplicate stage for this model
                tgc_value=Decimal('0.0320'),
                temperature_exponent=Decimal('1.0'),
                weight_exponent=Decimal('0.333')
            )

    def test_mortality_model_stage_unique_constraint(self):
        """Test that mortality_model and lifecycle_stage must be unique together."""
        with self.assertRaises(IntegrityError):
            MortalityModelStage.objects.create(
                mortality_model=self.mortality_model,
                lifecycle_stage=LifecycleStageChoices.FRY,  # Duplicate stage for this model
                daily_rate_percent=Decimal('0.06')
            )

    def test_fcr_override_weight_range_validation(self):
        """Test that min_weight_g must be less than max_weight_g."""
        with self.assertRaises(ValidationError):
            override = FCRModelStageOverride(
                fcr_stage=self.fcr_stage,
                min_weight_g=Decimal('4.0'),
                max_weight_g=Decimal('3.0'),  # Invalid: less than min_weight_g
                fcr_value=Decimal('1.3')
            )
            override.full_clean()

    def test_mortality_stage_weekly_rate_calculation(self):
        """Test that weekly_rate_percent is calculated from daily_rate_percent."""
        # Create a mortality stage without specifying weekly_rate_percent
        stage = MortalityModelStage.objects.create(
            mortality_model=self.mortality_model,
            lifecycle_stage=LifecycleStageChoices.SMOLT,
            daily_rate_percent=Decimal('0.1')
        )
        
        # Check that weekly_rate_percent was calculated
        self.assertIsNotNone(stage.weekly_rate_percent)
        
        # Calculate expected weekly rate: (1 - (1 - 0.1/100)^7) * 100
        daily_survival = 1 - (Decimal('0.1') / 100)
        weekly_survival = daily_survival ** 7
        expected_weekly_rate = (1 - weekly_survival) * 100
        
        # Compare with a small tolerance for floating-point differences
        self.assertAlmostEqual(
            float(stage.weekly_rate_percent),
            float(expected_weekly_rate),
            places=4
        )

    def test_multiple_fcr_overrides_for_stage(self):
        """Test that multiple FCR overrides can exist for different weight ranges."""
        # Create another override for a different weight range
        another_override = FCRModelStageOverride.objects.create(
            fcr_stage=self.fcr_stage,
            min_weight_g=Decimal('3.0'),
            max_weight_g=Decimal('5.0'),
            fcr_value=Decimal('1.3')
        )
        
        # Check that both overrides exist for the same FCR stage
        overrides = self.fcr_stage.overrides.all()
        self.assertEqual(overrides.count(), 2)
        self.assertIn(self.fcr_override, overrides)
        self.assertIn(another_override, overrides)
