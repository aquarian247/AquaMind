#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Scenario Data for FCR Testing

This script creates scenario data for FCR enhancement testing:
- Temperature profile for TGC calculations
- FCR model data in inventory_batchfeedingsummary
- TGC model data (simulated)
- Mortality model data (simulated)
- Scenario data when batch reaches fry stage
"""

import os
import sys
import django
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
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
    BatchFeedingSummary, ContainerFeedingSummary, Feed,
    FeedPurchase, FeedStock, FeedingEvent
)
from apps.environmental.models import EnvironmentalReading, EnvironmentalParameter
from apps.infrastructure.models import Container

def create_temperature_profile():
    """Create temperature profile data for the batch period"""
    print("Creating temperature profile data...")

    # Get batch
    try:
        batch = Batch.objects.get(batch_number="TEST-2024-001")
    except Batch.DoesNotExist:
        print("Batch not found. Please run create_batch.py first.")
        return None

    # Get or create temperature parameter
    try:
        temp_param = EnvironmentalParameter.objects.get(name='Temperature')
    except EnvironmentalParameter.DoesNotExist:
        print("Creating temperature parameter...")
        temp_param = EnvironmentalParameter.objects.create(
            name='Temperature',
            unit='°C',
            description='Water temperature',
            min_value=0,
            max_value=25
        )
        print(f"Temperature parameter created: {temp_param.name} (ID: {temp_param.id})")

    # Create temperature readings for the entire batch period
    current_date = batch.start_date
    end_date = batch.expected_end_date

    readings_created = 0
    while current_date <= end_date:
        # Seasonal temperature variation (simplified)
        day_of_year = current_date.timetuple().tm_yday
        base_temp = 8.0 + 4.0 * math.sin((day_of_year - 172) / 365 * 2 * math.pi)  # Seasonal variation

        # Create 4 readings per day
        for hour in [6, 12, 18, 24]:
            reading_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour-1))
            reading_time = reading_time.replace(tzinfo=timezone.utc)

            # Add some variation
            temperature = base_temp + random.uniform(-1.0, 1.0)

            # Get active containers for this date
            active_assignments = BatchContainerAssignment.objects.filter(
                batch=batch,
                assignment_date__lte=current_date
            ).filter(
                models_Q(departure_date__isnull=True) | models_Q(departure_date__gte=current_date)
            ).select_related('container')

            for assignment in active_assignments:
                EnvironmentalReading.objects.get_or_create(
                    container=assignment.container,
                    parameter=temp_param,
                    reading_time=reading_time,
                    defaults={
                        'batch_container_assignment': assignment,
                        'batch': batch,
                        'value': Decimal(str(round(temperature, 2))),
                    }
                )
                readings_created += 1

        current_date += timedelta(days=1)

    print(f"Temperature readings created: {readings_created}")
    return readings_created

def create_fcr_data():
    """Create FCR data for the batch"""
    print("Creating FCR data...")

    try:
        batch = Batch.objects.get(batch_number="TEST-2024-001")
    except Batch.DoesNotExist:
        print("Batch not found. Please run create_batch.py first.")
        return None

    # Get feed types
    feeds = list(Feed.objects.all())
    if not feeds:
        print("No feed types found. Please run create_batch.py first.")
        return None

    # Create feeding events and FCR summaries
    current_date = batch.start_date
    end_date = batch.expected_end_date

    # Get all assignments for the batch
    assignments = BatchContainerAssignment.objects.filter(batch=batch).select_related('container')

    feeding_events_created = 0
    summaries_created = 0

    while current_date <= end_date:
        for assignment in assignments:
            # Only create feeding events for active assignments
            if not (assignment.assignment_date <= current_date and
                    (assignment.departure_date is None or assignment.departure_date >= current_date)):
                continue

            # Create 4 feeding events per day for feeding stages
            feeding_stages = ['Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']
            if assignment.lifecycle_stage.name in feeding_stages:
                for hour in [6, 12, 18, 24]:
                    feeding_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                    feeding_time = feeding_time.replace(tzinfo=timezone.utc)

                    # Select feed based on stage
                    feed = feeds[min(len(feeds)-1, feeding_stages.index(assignment.lifecycle_stage.name))]

                    # Calculate feed amount (simplified)
                    biomass = assignment.biomass_kg or Decimal('1.0')
                    feed_amount = biomass * Decimal('0.02')  # 2% of biomass

                    FeedingEvent.objects.get_or_create(
                        batch=batch,
                        container=assignment.container,
                        batch_assignment=assignment,
                        feed=feed,
                        feeding_date=current_date,
                        feeding_time=feeding_time.time(),
                        defaults={
                            'amount_kg': feed_amount,
                            'batch_biomass_kg': biomass,
                            'feeding_percentage': (feed_amount / biomass) * 100,
                            'method': 'AUTOMATIC',
                            'notes': f'Automated feeding for {assignment.lifecycle_stage.name}'
                        }
                    )
                    feeding_events_created += 1

        # Create weekly FCR summaries
        if current_date.weekday() == 6:  # Sunday
            for assignment in assignments:
                if assignment.lifecycle_stage.name in ['Fry', 'Parr', 'Smolt', 'Post-Smolt', 'Adult']:
                    # Calculate FCR for the week
                    week_start = current_date - timedelta(days=6)
                    week_end = current_date

                    # Get feeding events for this week
                    week_feed = FeedingEvent.objects.filter(
                        batch_assignment=assignment,
                        feeding_date__gte=week_start,
                        feeding_date__lte=week_end
                    ).aggregate(total_feed=Sum('amount_kg'))['total_feed'] or Decimal('0')

                    # Simulate biomass gain (simplified)
                    biomass_gain = assignment.biomass_kg * Decimal('0.05')  # 5% weekly growth

                    if biomass_gain > 0:
                        fcr = week_feed / biomass_gain
                        confidence = 'HIGH' if week_feed > 0 else 'LOW'

                        ContainerFeedingSummary.objects.get_or_create(
                            batch=assignment.batch,
                            container_assignment=assignment,
                            period_start=week_start,
                            period_end=week_end,
                            defaults={
                                'total_feed_kg': week_feed,
                                'starting_biomass_kg': assignment.biomass_kg,
                                'ending_biomass_kg': assignment.biomass_kg + biomass_gain,
                                'growth_kg': biomass_gain,
                                'fcr': fcr,
                                'confidence_level': confidence,
                                'estimation_method': 'MEASURED' if week_feed > 0 else 'INTERPOLATED',
                                'data_points': 7
                            }
                        )
                        summaries_created += 1

        current_date += timedelta(days=1)

    print(f"Feeding events created: {feeding_events_created}")
    print(f"FCR summaries created: {summaries_created}")
    return feeding_events_created, summaries_created

def create_scenario_data():
    """Create scenario data for testing frontend FCR features"""
    print("Creating scenario data for frontend testing...")

    try:
        batch = Batch.objects.get(batch_number="TEST-2024-001")
    except Batch.DoesNotExist:
        print("Batch not found. Please run create_batch.py first.")
        return None

    # Find fry stage assignments (around day 90)
    fry_date = batch.start_date + timedelta(days=90)
    fry_assignments = BatchContainerAssignment.objects.filter(
        batch=batch,
        lifecycle_stage__name='Fry',
        assignment_date__lte=fry_date
    ).filter(
        models_Q(departure_date__isnull=True) | models_Q(departure_date__gte=fry_date)
    )

    print(f"Found {fry_assignments.count()} fry stage assignments at day 90")

    # Create scenario-like data structures (simplified for testing)
    scenario_data = {
        'scenario_id': 'TEST-SCENARIO-001',
        'name': 'FCR Test Scenario - Fry Stage',
        'batch_id': batch.id,
        'start_date': fry_date,
        'duration_days': 760,  # Remaining days to harvest
        'initial_population': sum(a.population_count for a in fry_assignments),
        'initial_biomass': sum(a.biomass_kg for a in fry_assignments),
        'fcr_model': {
            'model_id': 'FCR-TEST-001',
            'name': 'Test FCR Model',
            'stages': [
                {'stage': 'Fry', 'fcr_value': 0.8, 'duration_days': 90},
                {'stage': 'Parr', 'fcr_value': 0.9, 'duration_days': 90},
                {'stage': 'Smolt', 'fcr_value': 1.0, 'duration_days': 90},
                {'stage': 'Post-Smolt', 'fcr_value': 1.1, 'duration_days': 90},
                {'stage': 'Adult', 'fcr_value': 1.2, 'duration_days': 400},
            ]
        },
        'tgc_model': {
            'model_id': 'TGC-TEST-001',
            'name': 'Test TGC Model',
            'tgc_value': 2.5,
            'exponent_n': 1.0,
            'exponent_m': 0.333,
            'temperature_profile': {
                'profile_id': 'TEMP-TEST-001',
                'name': 'Faroe Islands Temperature Profile',
                'avg_temperature': 8.5,
                'seasonal_variation': True
            }
        },
        'mortality_model': {
            'model_id': 'MORT-TEST-001',
            'name': 'Test Mortality Model',
            'daily_rate': 0.005,
            'stage_overrides': [
                {'stage': 'Fry', 'daily_rate': 0.008},
                {'stage': 'Adult', 'daily_rate': 0.002}
            ]
        },
        'projections': []
    }

    # Create weekly projections for the remaining period
    current_date = fry_date
    population = scenario_data['initial_population']
    biomass = scenario_data['initial_biomass']

    while current_date <= batch.expected_end_date:
        # Simple growth projection
        daily_growth = biomass * Decimal('0.02')  # 2% daily growth
        biomass += daily_growth

        # Mortality
        daily_mortality = int(population * Decimal('0.005'))
        population -= daily_mortality

        # FCR calculation
        daily_feed = daily_growth * Decimal('1.0')  # FCR = 1.0
        fcr = daily_feed / daily_growth if daily_growth > 0 else Decimal('0')

        projection = {
            'date': current_date.isoformat(),
            'day_number': (current_date - fry_date).days,
            'population': population,
            'biomass': float(biomass),
            'daily_growth': float(daily_growth),
            'daily_feed': float(daily_feed),
            'fcr': float(fcr),
            'temperature': 8.5 + 2.0 * (1 + ((current_date - fry_date).days / 365 * 2 * 3.14159).sin()),  # Seasonal temp
        }
        scenario_data['projections'].append(projection)

        current_date += timedelta(days=7)  # Weekly projections

    print(f"Created scenario with {len(scenario_data['projections'])} weekly projections")

    # Save scenario data as JSON (simplified - in real implementation would use proper models)
    import json
    scenario_file = os.path.join(os.path.dirname(__file__), 'test_scenario_data.json')
    with open(scenario_file, 'w') as f:
        json.dump(scenario_data, f, indent=2, default=str)

    print(f"Scenario data saved to: {scenario_file}")
    return scenario_data

def main():
    """Main execution"""
    print("Starting AquaMind Scenario Data Generation...")
    print("=" * 60)

    try:
        # Create temperature profile
        temp_readings = create_temperature_profile()

        # Create FCR data
        feeding_data = create_fcr_data()

        # Create scenario data
        scenario = create_scenario_data()

        print("=" * 60)
        print("Scenario data generation completed successfully!")
        print(f"- Temperature readings: {temp_readings}")
        print(f"- Feeding events: {feeding_data[0] if feeding_data else 0}")
        print(f"- FCR summaries: {feeding_data[1] if feeding_data else 0}")
        print(f"- Scenario projections: {len(scenario['projections']) if scenario else 0}")

    except Exception as e:
        print(f"Error during scenario data generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
