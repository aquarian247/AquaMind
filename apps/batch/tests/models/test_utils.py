"""
Shared test utilities for batch app model tests.

This module contains common setup functions and helpers for batch app model tests.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    GrowthSample,
    MortalityEvent,
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


def create_test_user():
    """Create and return a test user for API authentication."""
    return get_user_model().objects.create_user(
        username="testuser",
        password="testpass",
        email="test@example.com"
    )


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


def create_test_container(hall=None, container_type=None, name="Test Container"):
    """Create and return a test Container."""
    if not hall:
        hall = create_test_hall()
    
    if not container_type:
        container_type = create_test_container_type()
    
    container, created = Container.objects.get_or_create(
        name=name,
        hall=hall,
        defaults={
            'container_type': container_type,
            'volume_m3': 50.0,
            'max_biomass_kg': 500.0
        }
    )
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
    
    batch, created = Batch.objects.get_or_create(
        batch_number=batch_number,
        defaults={
            'species': species,
            'lifecycle_stage': lifecycle_stage,
            'start_date': date.today() - timedelta(days=30),
            'expected_end_date': date.today() + timedelta(days=335)
        }
    )
    return batch


def create_test_batch_with_assignment(
    species=None,
    lifecycle_stage=None,
    batch_number="BATCH001",
    container=None,
    population_count=1000,
    avg_weight_g=Decimal("10.0")
):
    """
    Create and return a test Batch with a BatchContainerAssignment.
    
    This ensures that calculated fields on the Batch will have proper values.
    """
    batch = create_test_batch(species, lifecycle_stage, batch_number)
    
    if not container:
        container = create_test_container()
    
    if not lifecycle_stage:
        lifecycle_stage = batch.lifecycle_stage
    
    assignment = BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        lifecycle_stage=lifecycle_stage,
        population_count=population_count,
        avg_weight_g=avg_weight_g,
        assignment_date=date.today(),
        is_active=True
    )
    
    # Refresh batch to ensure calculated fields are updated
    batch.refresh_from_db()
    
    return batch, assignment


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


def create_test_growth_sample(
    assignment=None,
    sample_size=50,
    avg_weight_g=Decimal("10.0"),
    avg_length_cm=Decimal("10.0")
):
    """Create and return a test GrowthSample."""
    if not assignment:
        assignment = create_test_batch_container_assignment()
    
    return GrowthSample.objects.create(
        assignment=assignment,
        sample_date=date.today(),
        sample_size=sample_size,
        avg_weight_g=avg_weight_g,
        avg_length_cm=avg_length_cm
    )


def create_test_mortality_event(
    batch=None,
    count=100,
    biomass_kg=Decimal("1.0"),
    cause="DISEASE",
    description="Test mortality event"
):
    """Create and return a test MortalityEvent."""
    if not batch:
        batch = create_test_batch()
    
    return MortalityEvent.objects.create(
        batch=batch,
        event_date=date.today(),
        count=count,
        biomass_kg=biomass_kg,
        cause=cause,
        description=description
    )


