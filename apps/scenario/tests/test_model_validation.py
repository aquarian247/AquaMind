"""
Model validation tests for scenario planning.

These tests verify field constraints, validation rules, and integrity constraints
for all scenario planning models, ensuring data integrity and business rules are enforced.
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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


class TGCModelValidationTests(TestCase):
    """Tests for TGC model field validation."""
    
    def setUp(self):
        """Set up test data."""
        self.profile = TemperatureProfile.objects.create(
            name="Test Temperature Profile"
        )
        self.valid_data = {
            "name": "Valid TGC Model",
            "location": "Test Location",
            "release_period": "Spring",
            "tgc_value": 0.025,
            "exponent_n": 0.33,
            "exponent_m": 0.66,
            "profile": self.profile
        }

    def test_tgc_value_constraints(self):
        """Test tgc_value must be positive."""
        # Test with negative value
        model = TGCModel(
            **{**self.valid_data, "tgc_value": -0.025}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
        
        # Test with zero value
        model = TGCModel(
            **{**self.valid_data, "tgc_value": 0}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test with very small positive value (should be valid)
        model = TGCModel(
            **{**self.valid_data, "tgc_value": 0.0001}
        )
        model.full_clean()  # Should not raise
    
    def test_exponent_constraints(self):
        """Test exponent values can be any float."""
        # Test with negative exponents (should be valid)
        model = TGCModel(
            **{**self.valid_data, "exponent_n": -0.5, "exponent_m": -0.7}
        )
        model.full_clean()  # Should not raise
        
        # Test with zero exponents (should be valid)
        model = TGCModel(
            **{**self.valid_data, "exponent_n": 0, "exponent_m": 0}
        )
        model.full_clean()  # Should not raise
        
        # Test with large exponents (should be valid)
        model = TGCModel(
            **{**self.valid_data, "exponent_n": 10.0, "exponent_m": 20.0}
        )
        model.full_clean()  # Should not raise
    
    def test_required_fields(self):
        """Test required fields validation."""
        # Test missing name
        model = TGCModel(
            **{k: v for k, v in self.valid_data.items() if k != "name"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing location
        model = TGCModel(
            **{k: v for k, v in self.valid_data.items() if k != "location"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing release_period
        model = TGCModel(
            **{k: v for k, v in self.valid_data.items() if k != "release_period"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing tgc_value
        model = TGCModel(
            **{k: v for k, v in self.valid_data.items() if k != "tgc_value"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing profile
        model = TGCModel(
            **{k: v for k, v in self.valid_data.items() if k != "profile"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
    
    def test_string_length_validation(self):
        """Test string length validation."""
        # Test name max length (255)
        long_name = "X" * 255
        model = TGCModel(
            **{**self.valid_data, "name": long_name}
        )
        model.full_clean()  # Should not raise
        
        # Test name too long
        too_long_name = "X" * 256
        model = TGCModel(
            **{**self.valid_data, "name": too_long_name}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test location max length (255)
        long_location = "X" * 255
        model = TGCModel(
            **{**self.valid_data, "location": long_location}
        )
        model.full_clean()  # Should not raise
        
        # Test location too long
        too_long_location = "X" * 256
        model = TGCModel(
            **{**self.valid_data, "location": too_long_location}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test release_period max length (255)
        long_release = "X" * 255
        model = TGCModel(
            **{**self.valid_data, "release_period": long_release}
        )
        model.full_clean()  # Should not raise
        
        # Test release_period too long
        too_long_release = "X" * 256
        model = TGCModel(
            **{**self.valid_data, "release_period": too_long_release}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
    
    def test_profile_relationship_validation(self):
        """Test profile relationship validation."""
        # Test with non-existent profile ID
        with self.assertRaises(ValueError):
            TGCModel.objects.create(
                **{**self.valid_data, "profile_id": 999999}
            )
        
        # Test with deleted profile
        profile_to_delete = TemperatureProfile.objects.create(
            name="Profile To Delete"
        )
        model = TGCModel.objects.create(
            **{**self.valid_data, "name": "Model With Deleted Profile", "profile": profile_to_delete}
        )
        # PROTECT should prevent deletion of profile
        with self.assertRaises(IntegrityError):
            profile_to_delete.delete()
    
    def test_name_uniqueness(self):
        """Test name must be unique."""
        # Create first model
        TGCModel.objects.create(**self.valid_data)
        
        # Try to create another with same name
        with self.assertRaises(IntegrityError):
            TGCModel.objects.create(**self.valid_data)  # Same name
            
        # Different name should work
        TGCModel.objects.create(
            **{**self.valid_data, "name": "Different Name"}
        )


class FCRModelValidationTests(TestCase):
    """Tests for FCR model field validation."""
    
    def setUp(self):
        """Set up test data."""
        self.species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar"
        )
        self.stage = LifecycleStage.objects.create(
            name="fry",
            species=self.species,
            order=3,
            expected_weight_min_g=1.0,
            expected_weight_max_g=5.0
        )
        self.fcr_model = FCRModel.objects.create(
            name="Test FCR Model"
        )
        self.fcr_stage_data = {
            "model": self.fcr_model,
            "stage": self.stage,
            "fcr_value": 1.2,
            "duration_days": 90
        }

    def test_fcr_model_name_uniqueness(self):
        """Test FCR model name must be unique."""
        # Try to create another with same name
        with self.assertRaises(IntegrityError):
            FCRModel.objects.create(name="Test FCR Model")
            
        # Different name should work
        FCRModel.objects.create(name="Different FCR Model")
    
    def test_fcr_model_name_required(self):
        """Test FCR model name is required."""
        with self.assertRaises(ValidationError):
            model = FCRModel(name=None)
            model.full_clean()
            
        with self.assertRaises(IntegrityError):
            FCRModel.objects.create(name=None)
    
    def test_fcr_stage_field_constraints(self):
        """Test FCRModelStage field constraints."""
        # Test fcr_value must be positive
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                **{**self.fcr_stage_data, "fcr_value": -1.2}
            )
            stage.full_clean()
            
        # Test fcr_value zero
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                **{**self.fcr_stage_data, "fcr_value": 0}
            )
            stage.full_clean()
            
        # Test duration_days must be positive
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                **{**self.fcr_stage_data, "duration_days": 0}
            )
            stage.full_clean()
            
        with self.assertRaises(ValidationError):
            stage = FCRModelStage(
                **{**self.fcr_stage_data, "duration_days": -30}
            )
            stage.full_clean()
    
    def test_fcr_stage_relationship_validation(self):
        """Test FCRModelStage relationship validation."""
        # Test with non-existent model ID
        with self.assertRaises(ValueError):
            FCRModelStage.objects.create(
                **{**self.fcr_stage_data, "model_id": 999999}
            )
            
        # Test with non-existent stage ID
        with self.assertRaises(ValueError):
            FCRModelStage.objects.create(
                **{**self.fcr_stage_data, "stage_id": 999999}
            )
            
        # Test with deleted stage
        stage_to_delete = LifecycleStage.objects.create(
            name="stage_to_delete",
            species=self.species,
            order=10,
            expected_weight_min_g=10.0,
            expected_weight_max_g=20.0
        )
        fcr_stage = FCRModelStage.objects.create(
            model=self.fcr_model,
            stage=stage_to_delete,
            fcr_value=1.3,
            duration_days=60
        )
        # PROTECT should prevent deletion of stage
        with self.assertRaises(IntegrityError):
            stage_to_delete.delete()
    
    def test_fcr_stage_unique_together(self):
        """Test model and stage must be unique together."""
        # Create first stage
        FCRModelStage.objects.create(**self.fcr_stage_data)
        
        # Try to create another with same model and stage
        with self.assertRaises(IntegrityError):
            FCRModelStage.objects.create(**self.fcr_stage_data)
            
        # Different stage should work
        different_stage = LifecycleStage.objects.create(
            name="different_stage",
            species=self.species,
            order=4,
            expected_weight_min_g=5.0,
            expected_weight_max_g=10.0
        )
        FCRModelStage.objects.create(
            **{**self.fcr_stage_data, "stage": different_stage}
        )
        
        # Different model should work
        different_model = FCRModel.objects.create(name="Different FCR Model")
        FCRModelStage.objects.create(
            **{**self.fcr_stage_data, "model": different_model}
        )


class MortalityModelValidationTests(TestCase):
    """Tests for Mortality model field validation."""
    
    def setUp(self):
        """Set up test data."""
        self.valid_data = {
            "name": "Test Mortality Model",
            "frequency": "daily",
            "rate": 0.1
        }

    def test_rate_percentage_bounds(self):
        """Test rate percentage must be between 0 and 100."""
        # Test negative rate
        model = MortalityModel(
            **{**self.valid_data, "rate": -0.1}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test rate > 100
        model = MortalityModel(
            **{**self.valid_data, "rate": 100.1}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test boundary values
        # 0 is valid
        model = MortalityModel(
            **{**self.valid_data, "rate": 0}
        )
        model.full_clean()  # Should not raise
        
        # 100 is valid
        model = MortalityModel(
            **{**self.valid_data, "rate": 100}
        )
        model.full_clean()  # Should not raise
    
    def test_frequency_choices_validation(self):
        """Test frequency must be one of the valid choices."""
        # Test valid choices
        for freq in ['daily', 'weekly']:
            model = MortalityModel(
                **{**self.valid_data, "frequency": freq}
            )
            model.full_clean()  # Should not raise
            
        # Test invalid choice
        model = MortalityModel(
            **{**self.valid_data, "frequency": "monthly"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test empty choice
        model = MortalityModel(
            **{**self.valid_data, "frequency": ""}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
    
    def test_name_uniqueness(self):
        """Test name must be unique."""
        # Create first model
        MortalityModel.objects.create(**self.valid_data)
        
        # Try to create another with same name
        with self.assertRaises(IntegrityError):
            MortalityModel.objects.create(**self.valid_data)
            
        # Different name should work
        MortalityModel.objects.create(
            **{**self.valid_data, "name": "Different Name"}
        )
    
    def test_required_fields(self):
        """Test required fields validation."""
        # Test missing name
        model = MortalityModel(
            **{k: v for k, v in self.valid_data.items() if k != "name"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing frequency
        model = MortalityModel(
            **{k: v for k, v in self.valid_data.items() if k != "frequency"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()
            
        # Test missing rate
        model = MortalityModel(
            **{k: v for k, v in self.valid_data.items() if k != "rate"}
        )
        with self.assertRaises(ValidationError):
            model.full_clean()


class ScenarioValidationTests(TestCase):
    """Tests for Scenario model field validation."""
    
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
        self.stage = LifecycleStage.objects.create(
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
        self.freshwater_tgc = TGCModel.objects.create(
            name="Freshwater TGC Model",
            location="Freshwater Location",
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
        
        # Valid scenario data
        self.valid_data = {
            "name": "Test Scenario",
            "start_date": date.today(),
            "duration_days": 90,
            "initial_count": 10000,
            "genotype": "Standard",
            "supplier": "Test Supplier",
            "initial_weight": 2.5,
            "tgc_model": self.tgc_model,
            "fcr_model": self.fcr_model,
            "mortality_model": self.mortality_model,
            "batch": self.batch,
            "biological_constraints": self.constraints,
            "created_by": self.user
        }

    def test_initial_weight_validation(self):
        """Test initial_weight validation."""
        # Test negative initial_weight
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": -1.0}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test zero initial_weight
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": 0}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test None initial_weight (should be valid as it's nullable)
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": None}
        )
        scenario.full_clean()  # Should not raise
    
    def test_duration_days_validation(self):
        """Test duration_days validation."""
        # Test negative duration_days
        scenario = Scenario(
            **{**self.valid_data, "duration_days": -1}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test zero duration_days
        scenario = Scenario(
            **{**self.valid_data, "duration_days": 0}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test very large duration_days (should be valid)
        scenario = Scenario(
            **{**self.valid_data, "duration_days": 10000}
        )
        scenario.full_clean()  # Should not raise
    
    def test_initial_count_validation(self):
        """Test initial_count validation."""
        # Test negative initial_count
        scenario = Scenario(
            **{**self.valid_data, "initial_count": -1}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test zero initial_count
        scenario = Scenario(
            **{**self.valid_data, "initial_count": 0}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test very large initial_count (should be valid)
        scenario = Scenario(
            **{**self.valid_data, "initial_count": 10000000}
        )
        scenario.full_clean()  # Should not raise
    
    def test_start_date_validation(self):
        """Test start_date validation."""
        # Test None start_date
        scenario = Scenario(
            **{**self.valid_data, "start_date": None}
        )
        with self.assertRaises(ValidationError):
            scenario.full_clean()
            
        # Test past date (should be valid)
        past_date = date.today() - timedelta(days=365)
        scenario = Scenario(
            **{**self.valid_data, "start_date": past_date}
        )
        scenario.full_clean()  # Should not raise
        
        # Test future date (should be valid)
        future_date = date.today() + timedelta(days=365)
        scenario = Scenario(
            **{**self.valid_data, "start_date": future_date}
        )
        scenario.full_clean()  # Should not raise
    
    def test_biological_constraint_validation(self):
        """Test biological constraint validation."""
        # Test weight within constraints
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": 3.0}
        )
        scenario.full_clean()  # Should not raise
        
        # Test weight below min constraint
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": 0.5}
        )
        with self.assertRaises(ValidationError):
            scenario.clean()
            
        # Test weight above max constraint
        scenario = Scenario(
            **{**self.valid_data, "initial_weight": 10.0}
        )
        with self.assertRaises(ValidationError):
            scenario.clean()
    
    def test_freshwater_weight_limits(self):
        """Test freshwater weight limits."""
        # Test weight at freshwater limit
        scenario = Scenario(
            **{
                **self.valid_data, 
                "initial_weight": 5.0,
                "tgc_model": self.freshwater_tgc
            }
        )
        scenario.full_clean()  # Should not raise
        
        # Test weight above freshwater limit
        scenario = Scenario(
            **{
                **self.valid_data, 
                "initial_weight": 5.1,
                "tgc_model": self.freshwater_tgc
            }
        )
        with self.assertRaises(ValidationError):
            scenario.clean()
    
    def test_cascade_vs_protect_behavior(self):
        """Test CASCADE vs PROTECT behavior for model references."""
        # Create a scenario
        scenario = Scenario.objects.create(**self.valid_data)
        
        # Test PROTECT behavior for TGC model
        with self.assertRaises(IntegrityError):
            self.tgc_model.delete()
            
        # Test PROTECT behavior for FCR model
        with self.assertRaises(IntegrityError):
            self.fcr_model.delete()
            
        # Test PROTECT behavior for mortality model
        with self.assertRaises(IntegrityError):
            self.mortality_model.delete()
            
        # Test SET_NULL behavior for batch
        self.batch.delete()
        scenario.refresh_from_db()
        self.assertIsNone(scenario.batch)
        
        # Test SET_NULL behavior for biological constraints
        self.constraints.delete()
        scenario.refresh_from_db()
        self.assertIsNone(scenario.biological_constraints)
        
        # Test SET_NULL behavior for user
        self.user.delete()
        scenario.refresh_from_db()
        self.assertIsNone(scenario.created_by)


class BiologicalConstraintsValidationTests(TestCase):
    """Tests for BiologicalConstraints model validation."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass"
        )
        self.valid_data = {
            "name": "Test Constraints",
            "description": "Test constraint set",
            "is_active": True,
            "created_by": self.user
        }

    def test_name_uniqueness(self):
        """Test name must be unique."""
        # Create first constraints
        BiologicalConstraints.objects.create(**self.valid_data)
        
        # Try to create another with same name
        with self.assertRaises(IntegrityError):
            BiologicalConstraints.objects.create(**self.valid_data)
            
        # Different name should work
        BiologicalConstraints.objects.create(
            **{**self.valid_data, "name": "Different Name"}
        )
    
    def test_name_required(self):
        """Test name is required."""
        with self.assertRaises(ValidationError):
            constraints = BiologicalConstraints(
                **{k: v for k, v in self.valid_data.items() if k != "name"}
            )
            constraints.full_clean()
    
    def test_active_status_behavior(self):
        """Test active status behavior."""
        # Test default is True
        constraints = BiologicalConstraints.objects.create(
            **{k: v for k, v in self.valid_data.items() if k != "is_active"}
        )
        self.assertTrue(constraints.is_active)
        
        # Test can set to False
        constraints = BiologicalConstraints.objects.create(
            **{**self.valid_data, "name": "Inactive Constraints", "is_active": False}
        )
        self.assertFalse(constraints.is_active)
    
    def test_created_by_relationship(self):
        """Test created_by relationship."""
        # Test can be null
        constraints = BiologicalConstraints.objects.create(
            **{k: v for k, v in self.valid_data.items() if k != "created_by"}
        )
        self.assertIsNone(constraints.created_by)
        
        # Test SET_NULL behavior
        constraints = BiologicalConstraints.objects.create(
            **{**self.valid_data, "name": "User Constraints"}
        )
        self.assertEqual(constraints.created_by, self.user)
        
        # Delete user and check constraint still exists with null created_by
        self.user.delete()
        constraints.refresh_from_db()
        self.assertIsNone(constraints.created_by)
    
    def test_stage_constraint_validation(self):
        """Test stage constraint validation."""
        constraints = BiologicalConstraints.objects.create(
            **{**self.valid_data, "name": "Stage Constraints"}
        )
        
        # Test valid stage constraint
        stage_constraint = StageConstraint(
            constraint_set=constraints,
            lifecycle_stage=LifecycleStageChoices.FRY,
            min_weight_g=1.0,
            max_weight_g=5.0,
            min_temperature_c=8.0,
            max_temperature_c=14.0
        )
        stage_constraint.full_clean()  # Should not raise
        stage_constraint.save()
        
        # Test min_weight_g > max_weight_g
        with self.assertRaises(ValidationError):
            stage_constraint = StageConstraint(
                constraint_set=constraints,
                lifecycle_stage=LifecycleStageChoices.SMOLT,
                min_weight_g=10.0,
                max_weight_g=5.0,  # Invalid: less than min_weight_g
                min_temperature_c=8.0,
                max_temperature_c=14.0
            )
            stage_constraint.full_clean()
            
        # Test min_temperature_c > max_temperature_c
        with self.assertRaises(ValidationError):
            stage_constraint = StageConstraint(
                constraint_set=constraints,
                lifecycle_stage=LifecycleStageChoices.SMOLT,
                min_weight_g=5.0,
                max_weight_g=10.0,
                min_temperature_c=15.0,
                max_temperature_c=10.0  # Invalid: less than min_temperature_c
            )
            stage_constraint.full_clean()


class ScenarioModelChangeValidationTests(TestCase):
    """Tests for ScenarioModelChange validation."""
    
    def setUp(self):
        """Set up test data."""
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
        
        # Valid model change data
        self.valid_data = {
            "scenario": self.scenario,
            "change_day": 90,
            "new_tgc_model": self.tgc_model2,
            "new_fcr_model": self.fcr_model2,
            "new_mortality_model": self.mortality_model2
        }

    def test_change_day_validation(self):
        """Test change_day validation."""
        # Test negative change_day
        change = ScenarioModelChange(
            **{**self.valid_data, "change_day": -1}
        )
        with self.assertRaises(ValidationError):
            change.full_clean()
            
        # Test zero change_day
        change = ScenarioModelChange(
            **{**self.valid_data, "change_day": 0}
        )
        change.full_clean()  # Day 0 should be valid
            
        # Test change_day > scenario duration
        change = ScenarioModelChange(
            **{**self.valid_data, "change_day": 200}  # > 180 days
        )
        # This should be allowed, as the scenario duration might be extended later
        change.full_clean()  # Should not raise
    
    def test_at_least_one_model_must_change(self):
        """Test at least one model must change."""
        # Test no models changed
        with self.assertRaises(ValidationError):
            change = ScenarioModelChange(
                scenario=self.scenario,
                change_day=90,
                new_tgc_model=None,
                new_fcr_model=None,
                new_mortality_model=None
            )
            change.full_clean()
            
        # Test only TGC model changed
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=90,
            new_tgc_model=self.tgc_model2,
            new_fcr_model=None,
            new_mortality_model=None
        )
        change.full_clean()  # Should not raise
        
        # Test only FCR model changed
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=90,
            new_tgc_model=None,
            new_fcr_model=self.fcr_model2,
            new_mortality_model=None
        )
        change.full_clean()  # Should not raise
        
        # Test only mortality model changed
        change = ScenarioModelChange(
            scenario=self.scenario,
            change_day=90,
            new_tgc_model=None,
            new_fcr_model=None,
            new_mortality_model=self.mortality_model2
        )
        change.full_clean()  # Should not raise
    
    def test_protect_behavior_on_model_deletion(self):
        """Test PROTECT behavior on model deletion."""
        # Create a model change
        change = ScenarioModelChange.objects.create(**self.valid_data)
        
        # Test PROTECT behavior for TGC model
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.tgc_model2.delete()
        
        # Test PROTECT behavior for FCR model
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.fcr_model2.delete()
        
        # Test PROTECT behavior for mortality model
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                self.mortality_model2.delete()
        
        # Test CASCADE behavior for scenario
        self.scenario.delete()
        self.assertEqual(ScenarioModelChange.objects.filter(id=change.id).count(), 0)
    
    def test_scenario_relationship_required(self):
        """Test scenario relationship is required."""
        with self.assertRaises(ValidationError):
            change = ScenarioModelChange(
                **{k: v for k, v in self.valid_data.items() if k != "scenario"}
            )
            change.full_clean()
            
        with self.assertRaises(IntegrityError):
            ScenarioModelChange.objects.create(
                **{k: v for k, v in self.valid_data.items() if k != "scenario"}
            )
    
    def test_history_tracking(self):
        """Test history tracking for model changes."""
        # Create a model change
        change = ScenarioModelChange.objects.create(**self.valid_data)
        
        # Check history record was created
        self.assertEqual(change.history.count(), 1)
        
        # Update and check for new history record
        change.change_day = 100
        change.save()
        self.assertEqual(change.history.count(), 2)
        self.assertEqual(change.history.earliest().change_day, 90)
        self.assertEqual(change.history.latest().change_day, 100)
