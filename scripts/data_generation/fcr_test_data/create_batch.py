#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Batch Creation and Progression

This script creates a batch with 3.5M eggs and progresses it through lifecycle stages:
- Start date calculated so fish reach sea area at day 400
- 90 days per freshwater stage (5 stages = 450 days)
- 400 days in sea area
- Total: 850 days from start
- Distribute evenly into containers
"""

import os
import sys
import django
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import (
    Batch, Species, LifeCycleStage, BatchContainerAssignment,
    MortalityEvent, GrowthSample
)
from apps.infrastructure.models import Container, Geography
from apps.inventory.models import Feed

def create_species_and_stages():
    """Create salmon species and lifecycle stages if they don't exist"""
    print("Creating species and lifecycle stages...")

    # Create salmon species
    species, created = Species.objects.get_or_create(
        name="Atlantic Salmon",
        defaults={
            'scientific_name': 'Salmo salar',
        }
    )
    print(f"Species created: {species.name} (ID: {species.id})")

    # Create lifecycle stages
    stages = [
        ('Egg&Alevin', 'Egg & Alevin stage', 1),
        ('Fry', 'Fry stage', 2),
        ('Parr', 'Parr stage', 3),
        ('Smolt', 'Smolt stage', 4),
        ('Post-Smolt', 'Post-Smolt stage', 5),
        ('Adult', 'Adult stage', 6),
    ]

    lifecycle_stages = {}
    for name, desc, order in stages:
        stage, created = LifeCycleStage.objects.get_or_create(
            name=name,
            species=species,
            defaults={
                'description': desc,
                'order': order,
            }
        )
        lifecycle_stages[name] = stage
        print(f"Lifecycle stage created: {stage.name} (ID: {stage.id})")

    return species, lifecycle_stages

def create_batch(species, lifecycle_stages):
    """Create batch with 3.5M eggs"""
    print("Creating salmon batch...")

    # Calculate start date: 850 days ago (5*90 + 400)
    total_days = 5 * 90 + 400  # 850 days
    start_date = (datetime.now(timezone.utc) - timedelta(days=total_days)).date()

    batch, created = Batch.objects.get_or_create(
        batch_number="TEST-2024-001",
        defaults={
            'species': species,
            'lifecycle_stage': lifecycle_stages['Egg&Alevin'],
            'status': 'ACTIVE',
            'batch_type': 'STANDARD',
            'start_date': start_date,
            'expected_end_date': start_date + timedelta(days=850),
            'notes': 'Test batch for FCR analysis with 3.5M eggs'
        }
    )
    print(f"Batch created: {batch.batch_number} (ID: {batch.id})")
    print(f"- Start date: {batch.start_date}")
    print(f"- Expected end: {batch.expected_end_date}")
    print(f"- Total duration: {(batch.expected_end_date - batch.start_date).days} days")

    return batch

def get_containers_by_stage():
    """Get containers grouped by lifecycle stage"""
    print("Retrieving containers...")

    containers_by_stage = {
        'Egg&Alevin': Container.objects.filter(
            hall__name__startswith='Hall A',
            container_type__name__contains='Egg'
        )[:10],  # 10 containers for eggs
        'Fry': Container.objects.filter(
            hall__name__startswith='Hall B',
            container_type__name__contains='Fry'
        )[:10],  # 10 containers for fry
        'Parr': Container.objects.filter(
            hall__name__startswith='Hall C',
            container_type__name__contains='Parr'
        )[:10],  # 10 containers for parr
        'Smolt': Container.objects.filter(
            hall__name__startswith='Hall D',
            container_type__name__contains='Smolt'
        )[:10],  # 10 containers for smolt
        'Post-Smolt': Container.objects.filter(
            hall__name__startswith='Hall E',
            container_type__name__contains='Post-Smolt'
        )[:10],  # 10 containers for post-smolt
        'Adult': Container.objects.filter(
            area__name__contains='Sea Area'
        )[:20]  # 20 rings for adult
    }

    for stage, containers in containers_by_stage.items():
        print(f"- {stage}: {containers.count()} containers")

    return containers_by_stage

def distribute_batch_to_containers(batch, lifecycle_stages, containers_by_stage):
    """Distribute batch evenly into containers through lifecycle stages"""
    print("Distributing batch to containers...")

    total_eggs = 3500000  # 3.5M eggs
    assignments = []

    # Stage progression timeline
    stage_timeline = {
        'Egg&Alevin': {'days': 90, 'population_per_container': total_eggs // 10},  # Evenly distributed to 10 containers
        'Fry': {'days': 90, 'population_per_container': total_eggs // 10},
        'Parr': {'days': 90, 'population_per_container': total_eggs // 10},
        'Smolt': {'days': 90, 'population_per_container': total_eggs // 10},
        'Post-Smolt': {'days': 90, 'population_per_container': total_eggs // 10},
        'Adult': {'days': 400, 'population_per_container': total_eggs // 20}  # Distributed to 20 rings
    }

    current_date = batch.start_date
    survival_rate = Decimal('0.95')  # 95% survival per stage

    for stage_name, config in stage_timeline.items():
        stage = lifecycle_stages[stage_name]
        containers = containers_by_stage[stage_name]
        pop_per_container = config['population_per_container']

        print(f"\nProcessing {stage_name} stage:")
        print(f"- Containers: {containers.count()}")
        print(f"- Population per container: {pop_per_container:,}")
        print(f"- Stage duration: {config['days']} days")
        print(f"- Start date: {current_date}")

        for i, container in enumerate(containers):
            # Create assignment
            assignment = BatchContainerAssignment.objects.create(
                batch=batch,
                container=container,
                lifecycle_stage=stage,
                population_count=pop_per_container,
                avg_weight_g=Decimal('0.001') if stage_name == 'Egg&Alevin' else Decimal('0.1') if stage_name == 'Fry' else Decimal('1.0'),  # Initial weights
                biomass_kg=Decimal(str(pop_per_container)) * (Decimal('0.001') if stage_name == 'Egg&Alevin' else Decimal('0.1') if stage_name == 'Fry' else Decimal('1.0')) / 1000,
                assignment_date=current_date,
                is_active=True,
                notes=f'{stage_name} assignment #{i+1}'
            )
            assignments.append(assignment)
            print(f"  - Assignment created: {container.name} (ID: {assignment.id})")

        # Update survival for next stage
        if stage_name != 'Adult':
            total_eggs = int(total_eggs * survival_rate)

        # Move to next stage
        current_date += timedelta(days=config['days'])

        # Close previous assignments and create new ones for next stage
        if stage_name != 'Adult':
            for assignment in assignments:
                if assignment.lifecycle_stage == stage:
                    assignment.departure_date = current_date
                    assignment.is_active = False
                    assignment.save()

    print("\nBatch distribution completed!")
    print(f"- Total assignments created: {len(assignments)}")
    print(f"- Final date: {current_date}")

    return assignments

def create_feed_data():
    """Create basic feed types for testing"""
    print("Creating feed data...")

    feed_types = [
        ('Starter Feed', 'MICRO', 0.5, 45.0, 15.0, 25.0),
        ('Grower Feed', 'SMALL', 1.0, 42.0, 18.0, 22.0),
        ('Finisher Feed', 'MEDIUM', 2.0, 40.0, 20.0, 20.0),
    ]

    feeds = []
    for name, size, pellet_size, protein, fat, carb in feed_types:
        feed, created = Feed.objects.get_or_create(
            name=name,
            defaults={
                'brand': 'TestFeed',
                'size_category': size,
                'pellet_size_mm': Decimal(str(pellet_size)),
                'protein_percentage': Decimal(str(protein)),
                'fat_percentage': Decimal(str(fat)),
                'carbohydrate_percentage': Decimal(str(carb)),
                'is_active': True,
                'description': f'Test feed for {size.lower()} fish'
            }
        )
        feeds.append(feed)
        print(f"Feed created: {feed.name} (ID: {feed.id})")

    return feeds

def main():
    """Main execution"""
    print("Starting AquaMind Batch Creation and Progression...")
    print("=" * 60)

    try:
        # Create species and stages
        species, lifecycle_stages = create_species_and_stages()

        # Create batch
        batch = create_batch(species, lifecycle_stages)

        # Get containers
        containers_by_stage = get_containers_by_stage()

        # Distribute batch
        assignments = distribute_batch_to_containers(batch, lifecycle_stages, containers_by_stage)

        # Create feed data
        feeds = create_feed_data()

        print("=" * 60)
        print("Batch setup completed successfully!")
        print(f"- Batch: {batch.batch_number}")
        print(f"- Species: {species.name}")
        print(f"- Total eggs: 3,500,000")
        print(f"- Assignments created: {len(assignments)}")
        print(f"- Feed types: {len(feeds)}")

    except Exception as e:
        print(f"Error during batch setup: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
