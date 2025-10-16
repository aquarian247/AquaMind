#!/usr/bin/env python3
"""Quick test script for Phase 3 - simplified version"""
import os, sys, django
from datetime import date, timedelta
from decimal import Decimal

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.utils import timezone
from apps.batch.models import Batch, Species, LifeCycleStage, BatchContainerAssignment
from apps.infrastructure.models import Geography, FreshwaterStation, Hall, Container

# Test parameters
START_DATE = date(2024, 1, 1)
EGGS = 3500000
GEOGRAPHY = "Faroe Islands"

print(f"\nTesting Phase 3 with:")
print(f"  Start: {START_DATE}")
print(f"  Eggs: {EGGS:,}")
print(f"  Geography: {GEOGRAPHY}")

# Get geography
geo = Geography.objects.filter(name=GEOGRAPHY).first()
print(f"\n✓ Geography: {geo.name} (ID: {geo.id})")

# Get station
station = FreshwaterStation.objects.filter(geography=geo).first()
print(f"✓ Station: {station.name}")

# Get species & stages
species = Species.objects.filter(name="Atlantic Salmon").first()
stages = list(LifeCycleStage.objects.filter(species=species).order_by('order'))
print(f"✓ Species: {species.name}")
print(f"✓ Stages: {len(stages)}")

# Create test batch
batch = Batch.objects.create(
    batch_number=f"TEST-{START_DATE.year}-001",
    species=species,
    lifecycle_stage=stages[0],
    start_date=START_DATE,
    notes="Phase 3 test batch"
)
print(f"\n✓ Created batch: {batch.batch_number}")

# Get Hall A
hall_a = Hall.objects.filter(freshwater_station=station, name__contains="-Hall-A").first()
containers = Container.objects.filter(hall=hall_a).order_by('name')[:10]
print(f"✓ Hall A: {hall_a.name} ({containers.count()} containers)")

# Create assignments
eggs_per_container = EGGS // 10
for container in containers:
    BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        lifecycle_stage=stages[0],
        assignment_date=START_DATE,
        population_count=eggs_per_container,
        avg_weight_g=Decimal('0.1'),
        biomass_kg=Decimal(str(eggs_per_container * 0.1 / 1000)),
        is_active=True
    )

print(f"✓ Created 10 assignments ({eggs_per_container:,} eggs each)")
print(f"\n✅ Phase 3 test successful! Batch ID: {batch.id}")
print(f"\nNow implementing full Phase 3 event engine...")
