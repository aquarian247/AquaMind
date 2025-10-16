"""
Helper utilities for scenario tests.

This module provides helper functions for scenario tests to ensure test isolation
and prevent data conflicts between test runs.
"""
import uuid
import random
import string
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.batch.models import Species, LifeCycleStage, Batch
from apps.infrastructure.models import Geography, Area, Container, ContainerType
from ..models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel,
    FCRModelStage, MortalityModel, Scenario, ScenarioProjection,
    BiologicalConstraints, StageConstraint
)

User = get_user_model()


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique ID for test data.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        A unique string ID
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{random_part}"


def generate_unique_name(base_name: str) -> str:
    """
    Generate a unique name for test objects.
    
    Args:
        base_name: Base name to use
        
    Returns:
        A unique name with a random suffix
    """
    return f"{base_name}-{uuid.uuid4().hex[:8]}"


@transaction.atomic
def create_test_species(name: Optional[str] = None) -> Species:
    """
    Create a test species with a unique name.
    
    Args:
        name: Optional name for the species
        
    Returns:
        The created Species instance
    """
    species_name = name or f"Test Species {generate_unique_id()}"
    return Species.objects.create(
        name=species_name,
        scientific_name=f"Scientificus {species_name.lower()}",
        optimal_temperature_min=8.0,
        optimal_temperature_max=14.0
    )


@transaction.atomic
def create_test_lifecycle_stages(species: Species) -> Dict[str, LifeCycleStage]:
    """
    Create a complete set of lifecycle stages for testing.
    
    Args:
        species: The species to create lifecycle stages for
        
    Returns:
        Dictionary of created lifecycle stages by name
    """
    stages_data = [
        ('egg', 'Egg', 0.1, 0.3, 1),
        ('alevin', 'Alevin', 0.3, 1.0, 2),
        ('fry', 'Fry', 1.0, 5.0, 3),
        ('parr', 'Parr', 5.0, 50.0, 4),
        ('smolt', 'Smolt', 50.0, 150.0, 5),
        ('post_smolt', 'Post-Smolt', 150.0, 1000.0, 6),
        ('harvest', 'Harvest', 1000.0, 10000.0, 7)
    ]
    
    stages = {}
    for name, display, min_weight, max_weight, order in stages_data:
        stage = LifeCycleStage.objects.create(
            name=name,
            species=species,
            order=order,
            description=display,
            expected_weight_min_g=min_weight,
            expected_weight_max_g=max_weight
        )
        stages[name] = stage
    
    return stages


@transaction.atomic
def create_test_batch(species: Optional[Species] = None,
                     lifecycle_stage: Optional[LifeCycleStage] = None,
                     batch_number: Optional[str] = None) -> Batch:
    """
    Create a test batch with unique batch number.
    
    Args:
        species: Optional species for the batch
        lifecycle_stage: Optional lifecycle stage for the batch
        batch_number: Optional batch number
        
    Returns:
        The created Batch instance
    """
    if not species:
        species = create_test_species()
    
    if not lifecycle_stage:
        lifecycle_stage = LifeCycleStage.objects.filter(species=species).first()
        if not lifecycle_stage:
            stages = create_test_lifecycle_stages(species)
            lifecycle_stage = stages['fry']
    
    if not batch_number:
        batch_number = f"BATCH-{generate_unique_id()}"
    
    return Batch.objects.create(
        batch_number=batch_number,
        species=species,
        lifecycle_stage=lifecycle_stage,
        start_date=date.today() - timedelta(days=30),
        expected_end_date=date.today() + timedelta(days=335),
        status="ACTIVE",
        batch_type="STANDARD"
    )


@transaction.atomic
def create_test_temperature_profile(name: Optional[str] = None,
                                  days: int = 365) -> TemperatureProfile:
    """
    Create a test temperature profile with readings.
    
    Args:
        name: Optional name for the profile
        days: Number of days to create readings for
        
    Returns:
        The created TemperatureProfile instance
    """
    profile_name = name or f"Test Temperature Profile {generate_unique_id()}"
    profile = TemperatureProfile.objects.create(name=profile_name)
    
    # Add temperature readings with day numbers
    for day_num in range(1, days + 1):  # CHANGED: 1-based day numbers
        TemperatureReading.objects.create(
            profile=profile,
            day_number=day_num,  # CHANGED FROM reading_date
            temperature=10 + ((day_num - 1) % 10) * 0.5  # Vary between 10-15°C
        )
    
    return profile


@transaction.atomic
def create_test_tgc_model(profile: Optional[TemperatureProfile] = None,
                        name: Optional[str] = None) -> TGCModel:
    """
    Create a test TGC model.
    
    Args:
        profile: Optional temperature profile to use
        name: Optional name for the model
        
    Returns:
        The created TGCModel instance
    """
    if not profile:
        profile = create_test_temperature_profile()
    
    model_name = name or f"Test TGC Model {generate_unique_id()}"
    
    return TGCModel.objects.create(
        name=model_name,
        location="Test Location",
        release_period="Spring",
        tgc_value=0.025,
        exponent_n=0.33,
        exponent_m=0.66,
        profile=profile
    )


@transaction.atomic
def create_test_fcr_model(lifecycle_stages: Optional[Dict[str, LifeCycleStage]] = None,
                        name: Optional[str] = None) -> FCRModel:
    """
    Create a test FCR model with stages.
    
    Args:
        lifecycle_stages: Optional dictionary of lifecycle stages
        name: Optional name for the model
        
    Returns:
        The created FCRModel instance
    """
    model_name = name or f"Test FCR Model {generate_unique_id()}"
    model = FCRModel.objects.create(name=model_name)
    
    if not lifecycle_stages:
        species = create_test_species()
        lifecycle_stages = create_test_lifecycle_stages(species)
    
    # Add FCR stages
    for stage_name, stage in lifecycle_stages.items():
        FCRModelStage.objects.create(
            model=model,
            stage=stage,
            fcr_value=1.0 + (float(stage.expected_weight_min_g or 0)) / 1000,
            duration_days=60
        )
    
    return model


@transaction.atomic
def create_test_mortality_model(name: Optional[str] = None) -> MortalityModel:
    """
    Create a test mortality model.
    
    Args:
        name: Optional name for the model
        
    Returns:
        The created MortalityModel instance
    """
    model_name = name or f"Test Mortality Model {generate_unique_id()}"
    
    return MortalityModel.objects.create(
        name=model_name,
        frequency="daily",
        rate=0.05
    )


@transaction.atomic
def create_test_biological_constraints(user: Optional[User] = None,
                                     name: Optional[str] = None) -> BiologicalConstraints:
    """
    Create test biological constraints with stage constraints.
    
    Args:
        user: Optional user to set as creator
        name: Optional name for the constraints
        
    Returns:
        The created BiologicalConstraints instance
    """
    if not user:
        user = User.objects.first() or User.objects.create_user(
            username=f"testuser-{generate_unique_id()}",
            password="password123"
        )
    
    constraints_name = name or f"Test Constraints {generate_unique_id()}"
    
    constraints = BiologicalConstraints.objects.create(
        name=constraints_name,
        description="Test biological constraints",
        is_active=True,
        created_by=user
    )
    
    # Add stage constraints
    stages_data = [
        ('egg', 0.1, 0.3, None),
        ('alevin', 0.3, 1.0, None),
        ('fry', 1.0, 5.0, None),
        ('parr', 5.0, 50.0, 50.0),
        ('smolt', 50.0, 150.0, 150.0),
        ('post_smolt', 150.0, 1000.0, None),
        ('harvest', 1000.0, 10000.0, None)
    ]
    
    for stage, min_w, max_w, fw_limit in stages_data:
        StageConstraint.objects.create(
            constraint_set=constraints,
            lifecycle_stage=stage,
            min_weight_g=min_w,
            max_weight_g=max_w,
            max_freshwater_weight_g=fw_limit
        )
    
    return constraints


@transaction.atomic
def create_test_scenario(user: Optional[User] = None,
                       name: Optional[str] = None,
                       models: Optional[Dict[str, Any]] = None) -> Scenario:
    """
    Create a test scenario with all required models.
    
    Args:
        user: Optional user to set as creator
        name: Optional name for the scenario
        models: Optional dictionary of models to use
        
    Returns:
        The created Scenario instance
    """
    if not user:
        user = User.objects.first() or User.objects.create_user(
            username=f"testuser-{generate_unique_id()}",
            password="password123"
        )
    
    scenario_name = name or f"Test Scenario {generate_unique_id()}"
    
    if not models:
        models = {}
    
    if 'tgc_model' not in models:
        models['tgc_model'] = create_test_tgc_model()
    
    if 'fcr_model' not in models:
        models['fcr_model'] = create_test_fcr_model()
    
    if 'mortality_model' not in models:
        models['mortality_model'] = create_test_mortality_model()
    
    if 'biological_constraints' not in models:
        models['biological_constraints'] = create_test_biological_constraints(user=user)
    
    return Scenario.objects.create(
        name=scenario_name,
        start_date=date.today(),
        duration_days=600,
        initial_count=10000,
        initial_weight=50.0,
        genotype="Atlantic Salmon",
        supplier="Test Supplier",
        tgc_model=models['tgc_model'],
        fcr_model=models['fcr_model'],
        mortality_model=models['mortality_model'],
        biological_constraints=models['biological_constraints'],
        created_by=user
    )


def get_scenario_api_url(action: str, pk: Optional[int] = None, 
                       use_reverse: bool = True) -> str:
    """
    Get a URL for a scenario API endpoint.
    
    This function supports both direct URL construction and Django's reverse()
    function, depending on the current API namespace configuration.
    
    Args:
        action: The action name (e.g., 'list', 'detail', 'run_projection')
        pk: Optional primary key for detail URLs
        use_reverse: Whether to use Django's reverse function (requires 'api' namespace)
        
    Returns:
        The API URL as a string
    """
    if use_reverse:
        if action == 'list':
            return reverse('scenario-list')
        elif action == 'detail':
            return reverse('scenario-detail', kwargs={'pk': pk})
        else:
            return reverse(f'api:scenario-{action}', kwargs={'pk': pk})
    else:
        # Direct URL construction (fallback if reverse fails)
        if action == 'list':
            return '/api/v1/scenario/scenarios/'
        elif action == 'detail':
            return f'/api/v1/scenario/scenarios/{pk}/'
        else:
            return f'/api/v1/scenario/scenarios/{pk}/{action.replace("_", "-")}/'


def create_test_projection_data(days: int = 90, 
                              start_weight: float = 5.0,
                              start_count: int = 10000,
                              lifecycle_stages: Optional[Dict[str, LifeCycleStage]] = None) -> List[Dict[str, Any]]:
    """
    Create test projection data for mocking ProjectionEngine.
    
    Args:
        days: Number of days to simulate
        start_weight: Starting weight in grams
        start_count: Starting population count
        lifecycle_stages: Optional dictionary of lifecycle stages
        
    Returns:
        List of projection data dictionaries
    """
    if not lifecycle_stages:
        species = create_test_species()
        lifecycle_stages = create_test_lifecycle_stages(species)
    
    stages_list = sorted(
        [(k, v) for k, v in lifecycle_stages.items()], 
        key=lambda x: x[1].order
    )
    
    projections = []
    current_weight = start_weight
    current_count = start_count
    current_stage = None
    cumulative_feed = 0.0
    
    # Find appropriate starting stage based on weight
    for stage_name, stage in stages_list:
        if (stage.expected_weight_min_g <= current_weight <= stage.expected_weight_max_g):
            current_stage = stage
            break
    
    if not current_stage:
        current_stage = stages_list[0][1]  # Default to first stage
    
    start_date = date.today()
    
    for day in range(days + 1):
        # Simple growth model for testing
        if day > 0:
            daily_growth = current_weight * 0.015  # 1.5% daily growth
            current_weight += daily_growth
            
            # Simple mortality model
            daily_mortality = current_count * 0.0005  # 0.05% daily mortality
            current_count -= daily_mortality
            
            # Simple feed calculation
            daily_feed = current_count * current_weight * 0.02 / 1000  # 2% body weight
            cumulative_feed += daily_feed
            
            # Check for stage transition
            for stage_name, stage in stages_list:
                if (stage.order > current_stage.order and 
                    stage.expected_weight_min_g <= current_weight <= stage.expected_weight_max_g):
                    current_stage = stage
                    break
        else:
            daily_feed = 0.0
        
        # Create projection data point
        projections.append({
            'day_number': day,
            'projection_date': start_date + timedelta(days=day),
            'average_weight': round(current_weight, 2),
            'population': round(current_count, 0),
            'biomass': round(current_weight * current_count / 1000, 2),
            'daily_feed': round(daily_feed, 2),
            'cumulative_feed': round(cumulative_feed, 2),
            'temperature': 12.0,
            'current_stage_id': current_stage.id
        })
    
    return projections
