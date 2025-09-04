#!/usr/bin/env python3
"""
AquaMind Enhanced Feeding Data Generation

This script generates realistic daily feeding events from fry stage onwards
using the provided aquaculture parameters table.
"""

import os
import sys
import django
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db.models import Sum, Q as models_Q
from apps.batch.models import Batch, BatchContainerAssignment
from apps.inventory.models import (
    ContainerFeedingSummary, FeedingEvent, Feed
)

def get_stage_parameters():
    """Get realistic parameters for each lifecycle stage"""
    return {
        'Fry': {
            'duration_days': 90,
            'fcr_range': (1.0, 1.2),
            'tgc_range': (2.0, 2.5),
            'mortality_rate': 0.07,  # 7% average
            'growth_rate_range': (0.03, 0.06),  # g/day
            'initial_weight': 0.05,  # g
            'final_weight': 5.0,  # g
            'feedings_per_day': 4  # 4x daily feeding
        },
        'Parr': {
            'duration_days': 90,
            'fcr_range': (1.0, 1.1),
            'tgc_range': (2.5, 3.0),
            'mortality_rate': 0.07,
            'growth_rate_range': (0.4, 0.6),
            'initial_weight': 5.0,
            'final_weight': 50.0,
            'feedings_per_day': 4
        },
        'Smolt': {
            'duration_days': 90,
            'fcr_range': (1.1, 1.2),
            'tgc_range': (2.5, 3.0),
            'mortality_rate': 0.07,
            'growth_rate_range': (0.8, 1.2),
            'initial_weight': 50.0,
            'final_weight': 150.0,
            'feedings_per_day': 4
        },
        'Post-Smolt': {
            'duration_days': 90,
            'fcr_range': (1.1, 1.2),
            'tgc_range': (3.0, 3.5),
            'mortality_rate': 0.07,
            'growth_rate_range': (2.5, 3.5),
            'initial_weight': 150.0,
            'final_weight': 400.0,
            'feedings_per_day': 4
        },
        'Adult': {
            'duration_days': 400,
            'fcr_range': (1.2, 1.3),
            'tgc_range': (3.0, 3.2),
            'mortality_rate': 0.12,  # 12% average
            'growth_rate_range': (10.0, 15.0),
            'initial_weight': 400.0,
            'final_weight': 6000.0,  # 6kg average
            'feedings_per_day': 2  # 2x daily feeding for adults
        }
    }

def clear_existing_feeding_data():
    """Clear existing feeding data to regenerate cleanly"""
    print("Clearing existing feeding data...")

    FeedingEvent.objects.all().delete()
    ContainerFeedingSummary.objects.all().delete()

    print("Existing feeding data cleared.")

def get_feed_for_stage(stage_name):
    """Get appropriate feed type for each stage"""
    feed_mapping = {
        'Fry': 'Starter Feed',
        'Parr': 'Starter Feed',
        'Smolt': 'Grower Feed',
        'Post-Smolt': 'Grower Feed',
        'Adult': 'Finisher Feed'
    }

    try:
        return Feed.objects.get(name=feed_mapping.get(stage_name, 'Starter Feed'))
    except Feed.DoesNotExist:
        return Feed.objects.first()  # Fallback to any feed

def generate_daily_feeding_events():
    """Generate daily feeding events for all feeding stages"""
    print("Generating daily feeding events...")

    try:
        batch = Batch.objects.get(batch_number="TEST-2024-001")
    except Batch.DoesNotExist:
        print("Batch not found. Please run create_batch.py first.")
        return 0

    stage_params = get_stage_parameters()
    feeding_events_created = 0

    # Get all assignments for feeding stages
    feeding_stages = ['Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']
    assignments = BatchContainerAssignment.objects.filter(
        batch=batch,
        lifecycle_stage__name__in=feeding_stages
    ).select_related('lifecycle_stage', 'container').order_by('assignment_date')

    print(f"Found {assignments.count()} assignments in feeding stages")

    for assignment in assignments:
        stage_name = assignment.lifecycle_stage.name
        if stage_name not in stage_params:
            continue

        params = stage_params[stage_name]
        feed = get_feed_for_stage(stage_name)

        # Calculate stage timeline
        stage_start = assignment.assignment_date
        stage_end = assignment.departure_date or batch.expected_end_date

        print(f"Processing {stage_name} stage for container {assignment.container.name}")
        print(f"  Stage duration: {(stage_end - stage_start).days} days")
        print(f"  Feedings per day: {params['feedings_per_day']}")

        # Generate daily feeding events
        current_date = stage_start
        day_counter = 0

        while current_date <= stage_end:
            # Calculate current weight based on growth progression
            days_into_stage = (current_date - stage_start).days
            progress_ratio = min(days_into_stage / params['duration_days'], 1.0)

            # Linear weight progression for simplicity
            current_weight = params['initial_weight'] + (
                (params['final_weight'] - params['initial_weight']) * progress_ratio
            )

            # Calculate daily feed requirement based on FCR
            biomass_kg = (assignment.population_count * current_weight) / 1000000  # Convert to kg
            avg_fcr = (params['fcr_range'][0] + params['fcr_range'][1]) / 2
            daily_feed_total = Decimal(str(biomass_kg)) * Decimal(str(avg_fcr))

            # Distribute feed across feeding times
            feed_per_meal = daily_feed_total / params['feedings_per_day']

            # Generate feeding events for this day
            feeding_times = []
            if params['feedings_per_day'] == 4:
                feeding_times = [6, 12, 18, 21]  # 6am, 12pm, 6pm, 9pm
            elif params['feedings_per_day'] == 2:
                feeding_times = [6, 18]  # 6am, 6pm

            for hour in feeding_times:
                feeding_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                feeding_time = feeding_time.replace(tzinfo=timezone.utc)

                # Add some variation to feed amount (±10%)
                variation = Decimal(str(random.uniform(0.9, 1.1)))
                actual_feed = feed_per_meal * variation

                FeedingEvent.objects.create(
                    batch=batch,
                    container=assignment.container,
                    batch_assignment=assignment,
                    feed=feed,
                    feeding_date=current_date,
                    feeding_time=feeding_time.time(),
                    amount_kg=actual_feed,
                    batch_biomass_kg=Decimal(str(biomass_kg)),
                    feeding_percentage=(actual_feed / Decimal(str(biomass_kg))) * 100 if biomass_kg > 0 else Decimal('0'),
                    method='AUTOMATIC',
                    notes=f'Daily feeding for {stage_name} stage - Meal {feeding_times.index(hour) + 1}/{len(feeding_times)}'
                )
                feeding_events_created += 1

            current_date += timedelta(days=1)
            day_counter += 1

            if day_counter % 30 == 0:  # Progress update every 30 days
                print(f"  Processed {day_counter} days...")

        print(f"  Created {params['feedings_per_day'] * (stage_end - stage_start).days} feeding events for {stage_name}")

    print(f"Total feeding events created: {feeding_events_created}")
    return feeding_events_created

def generate_fcr_summaries():
    """Generate weekly FCR summaries with realistic calculations"""
    print("Generating FCR summaries...")

    try:
        batch = Batch.objects.get(batch_number="TEST-2024-001")
    except Batch.DoesNotExist:
        print("Batch not found. Please run create_batch.py first.")
        return 0

    stage_params = get_stage_parameters()
    summaries_created = 0

    # Get all assignments for feeding stages
    feeding_stages = ['Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']
    assignments = BatchContainerAssignment.objects.filter(
        batch=batch,
        lifecycle_stage__name__in=feeding_stages
    ).select_related('lifecycle_stage', 'container')

    current_date = batch.start_date
    end_date = batch.expected_end_date

    while current_date <= end_date:
        week_start = current_date
        week_end = min(current_date + timedelta(days=6), end_date)

        print(f"Processing FCR summary for week of {week_start}")

        for assignment in assignments:
            stage_name = assignment.lifecycle_stage.name
            if stage_name not in stage_params:
                continue

            # Check if assignment is active during this week
            if not (assignment.assignment_date <= week_end and
                    (assignment.departure_date is None or assignment.departure_date >= week_start)):
                continue

            # Get feeding events for this week
            week_feed = FeedingEvent.objects.filter(
                batch_assignment=assignment,
                feeding_date__gte=week_start,
                feeding_date__lte=week_end
            ).aggregate(total_feed=Sum('amount_kg'))['total_feed'] or Decimal('0')

            # Calculate biomass change (simplified)
            params = stage_params[stage_name]
            days_into_stage = (week_start - assignment.assignment_date).days
            progress_ratio = min(days_into_stage / params['duration_days'], 1.0)

            biomass_start = assignment.biomass_kg or Decimal('1.0')
            # Assume 5% weekly growth for FCR calculation
            biomass_growth = biomass_start * Decimal('0.05')
            biomass_end = biomass_start + biomass_growth

            # Calculate FCR
            if biomass_growth > 0 and week_feed > 0:
                fcr = week_feed / biomass_growth
                confidence = 'HIGH' if week_feed > 0 else 'LOW'
            else:
                fcr = Decimal('0')
                confidence = 'LOW'

            ContainerFeedingSummary.objects.get_or_create(
                batch=assignment.batch,
                container_assignment=assignment,
                period_start=week_start,
                period_end=week_end,
                defaults={
                    'total_feed_kg': week_feed,
                    'starting_biomass_kg': biomass_start,
                    'ending_biomass_kg': biomass_end,
                    'growth_kg': biomass_growth,
                    'fcr': fcr,
                    'confidence_level': confidence,
                    'estimation_method': 'MEASURED' if week_feed > 0 else 'INTERPOLATED',
                    'data_points': 7
                }
            )
            summaries_created += 1

        current_date = week_end + timedelta(days=1)

    print(f"FCR summaries created: {summaries_created}")
    return summaries_created

def main():
    """Main execution"""
    print("Starting Enhanced AquaMind Feeding Data Generation...")
    print("=" * 60)

    try:
        # Clear existing data
        clear_existing_feeding_data()

        # Generate new feeding events
        feeding_events = generate_daily_feeding_events()

        # Generate FCR summaries
        summaries = generate_fcr_summaries()

        print("=" * 60)
        print("Enhanced feeding data generation completed successfully!")
        print(f"- Feeding events: {feeding_events}")
        print(f"- FCR summaries: {summaries}")

        # Show sample statistics
        print("\nSample statistics:")
        total_feed = FeedingEvent.objects.aggregate(total=Sum('amount_kg'))['total'] or 0
        print(".2f")

        # Show feeding events by stage
        from django.db.models import Count
        stage_counts = FeedingEvent.objects.values('batch_assignment__lifecycle_stage__name').annotate(
            count=Count('id')
        ).order_by('batch_assignment__lifecycle_stage__name')

        print("\nFeeding events by stage:")
        for item in stage_counts:
            print(f"  {item['batch_assignment__lifecycle_stage__name']:12}: {item['count']} events")

    except Exception as e:
        print(f"Error during feeding data generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
