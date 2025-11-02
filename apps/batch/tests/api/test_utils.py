"""
Shared test utilities for batch app API tests.

This module contains common setup functions and helpers for batch app API tests.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment
)
from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType,
    Container
)
from apps.health.models import MortalityReason
from apps.users.models import UserProfile, Geography as UserGeography, Role, Subsidiary


def create_test_user(geography=UserGeography.SCOTLAND, role=Role.ADMIN, 
                    username="testuser"):
    """
    Create and return a test user with UserProfile for API authentication.
    
    Args:
        geography: Geography for RBAC (default: Scotland)
        role: Role for RBAC (default: Admin)
        username: Username (default: testuser)
    
    Returns:
        User instance with UserProfile for RBAC compatibility
    """
    user = get_user_model().objects.create_user(
        username=username,
        password="testpass",
        email=f"{username}@example.com"
    )
    
    # Create UserProfile for RBAC
    UserProfile.objects.create(
        user=user,
        geography=geography,
        role=role,
        subsidiary=Subsidiary.ALL
    )
    
    return user


def create_test_geography(name="Test Geography"):
    """Create and return a test Geography."""
    geography, created = Geography.objects.get_or_create(name=name)
    return geography


def create_test_freshwater_station(geography=None, name="Test Station"):
    """Create and return a test FreshwaterStation."""
    if not geography:
        geography = create_test_geography()
    
    station, created = FreshwaterStation.objects.get_or_create(
        name=name,
        defaults={
            'geography': geography,
            'latitude': Decimal("40.7128"),
            'longitude': Decimal("-74.0060")
        }
    )
    return station


def create_test_hall(station=None, name="Test Hall"):
    """Create and return a test Hall."""
    if not station:
        station = create_test_freshwater_station()
    
    hall, created = Hall.objects.get_or_create(
        name=name,
        freshwater_station=station
    )
    return hall


def create_test_container_type(name="Test Tank"):
    """Create and return a test ContainerType."""
    container_type, created = ContainerType.objects.get_or_create(
        name=name,
        defaults={
            'max_volume_m3': 100.0
        }
    )
    return container_type


def create_test_area(geography=None, name="Test Area"):
    """Create and return a test Area."""
    if not geography:
        geography = create_test_geography()

    area, created = Area.objects.get_or_create(
        name=name,
        geography=geography,
        defaults={
            'latitude': Decimal("40.7128"),
            'longitude': Decimal("-74.0060"),
            'max_biomass': 10000.0
        }
    )
    return area


def create_test_container(hall=None, area=None, container_type=None, name="Test Container"):
    """Create and return a test Container."""
    if not hall and not area:
        hall = create_test_hall()

    if not container_type:
        container_type = create_test_container_type()

    # Determine which location field to set
    defaults = {
        'container_type': container_type,
        'volume_m3': 50.0,
        'max_biomass_kg': 500.0
    }

    if hall:
        container, created = Container.objects.get_or_create(
            name=name,
            hall=hall,
            defaults=defaults
        )
    elif area:
        container, created = Container.objects.get_or_create(
            name=name,
            area=area,
            defaults=defaults
        )
    else:
        raise ValueError("Either hall or area must be provided")

    return container


def create_test_species(name="Test Species"):
    """Create and return a test Species."""
    species, created = Species.objects.get_or_create(
        name=name,
        defaults={
            'scientific_name': f"{name.lower().replace(' ', '_')} scientificus"
        }
    )
    return species


def create_test_lifecycle_stage(species=None, name="Test Stage", order=1):
    """Create and return a test LifecycleStage."""
    if not species:
        species = create_test_species()
    
    lifecycle_stage, created = LifeCycleStage.objects.get_or_create(
        name=name,
        species=species,
        defaults={
            'order': order
        }
    )
    return lifecycle_stage


def create_test_batch(species=None, lifecycle_stage=None, batch_number="BATCH001"):
    """Create and return a test Batch."""
    if not species:
        species = create_test_species()
    
    if not lifecycle_stage:
        lifecycle_stage = create_test_lifecycle_stage(species=species)
    
    return Batch.objects.create(
        batch_number=batch_number,
        species=species,
        lifecycle_stage=lifecycle_stage,
        start_date=date.today() - timedelta(days=30),
        expected_end_date=date.today() + timedelta(days=335)
    )


def create_test_batch_container_assignment(
    batch=None,
    container=None,
    lifecycle_stage=None,
    population_count=1000,
    avg_weight_g=Decimal("10.0"),
    notes="Test assignment"
):
    """Create and return a test BatchContainerAssignment with calculated biomass."""
    if not batch:
        batch = create_test_batch()
    
    if not container:
        container = create_test_container()
    
    if not lifecycle_stage:
        lifecycle_stage = batch.lifecycle_stage
    
    return BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        lifecycle_stage=lifecycle_stage,
        population_count=population_count,
        avg_weight_g=avg_weight_g,
        assignment_date=date.today(),
        is_active=True,
        notes=notes
    )


def create_test_mortality_reason(name="Test Reason"):
    """Create and return a test MortalityReason."""
    return MortalityReason.objects.create(name=name)
