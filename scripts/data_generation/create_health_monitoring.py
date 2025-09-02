#!/usr/bin/env python
"""
Create Health Monitoring Data
Generates health observations, journal entries, and sampling events tied to real batch assignments.
"""
import os
import sys
import django
import random
from decimal import Decimal
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.health.models import HealthParameter, HealthSamplingEvent, JournalEntry
from apps.batch.models import BatchContainerAssignment
from apps.infrastructure.models import Container
from django.contrib.auth import get_user_model

User = get_user_model()

def create_health_monitoring():
    """
    Create health monitoring data tied to real batch assignments.

    This function is rerunnable - it will only create health data for dates that don't
    already have entries for the same assignment/date combination.
    """

    print("=== CREATING HEALTH MONITORING DATA ===")

    # Check existing health data
    existing_sampling = HealthSamplingEvent.objects.count()
    existing_journal = JournalEntry.objects.count()
    print(f"📊 Existing health sampling events: {existing_sampling}")
    print(f"📊 Existing journal entries: {existing_journal}")

    # Determine date range first
    assignments_all = BatchContainerAssignment.objects.filter(departure_date__isnull=True)
    if assignments_all.exists():
        assignment_dates = list(assignments_all.values_list('assignment_date', flat=True))
        start_date = min(assignment_dates)
        # Process 2 years of data for substantial transaction volumes
        end_date = min(start_date + timedelta(days=730), max(assignment_dates))
    else:
        # Fallback to original range if no assignments
        start_date = date(2015, 1, 1)
        end_date = date(2018, 1, 15)

    # Now get active assignments that qualify for our processing date range
    active_assignments = BatchContainerAssignment.objects.filter(
        departure_date__isnull=True,
        assignment_date__lte=end_date
    ).select_related('batch', 'container')

    if not active_assignments.exists():
        print("❌ No active batch assignments found in processing range.")
        return 0

    # Get or create health parameters
    health_params = [
        'Gill Health',
        'Skin Condition',
        'Fecal Score',
        'Sea Lice Count',
        'Wound Assessment',
        'Parasite Load'
    ]

    created_params = []
    for param_name in health_params:
        param, created = HealthParameter.objects.get_or_create(
            name=param_name,
            defaults={
                'description_score_1': f'Excellent {param_name.lower()}',
                'description_score_2': f'Good {param_name.lower()}',
                'description_score_3': f'Fair {param_name.lower()}',
                'description_score_4': f'Poor {param_name.lower()}',
                'description_score_5': f'Critical {param_name.lower()}',
                'is_active': True
            }
        )
        if created:
            created_params.append(param)

    print(f"✅ Created/verified {len(health_params)} health parameters")

    # Get or create system user for health monitoring
    system_user, _ = User.objects.get_or_create(
        username='health_monitor',
        defaults={'email': 'health@aquamind.com', 'first_name': 'Health', 'last_name': 'Monitor'}
    )

    # Create health sampling events and journal entries
    sampling_count = 0
    journal_count = 0

    current_date = start_date

    print(f"📅 Processing date range: {start_date} to {end_date}")
    print(f"👥 Active assignments to process: {active_assignments.count()}")

    while current_date <= end_date:
        for assignment in active_assignments:
            # Check if assignment is active during this processing period
            if assignment.assignment_date <= current_date:
                # Check if we already have health data for this assignment and date
                existing_sampling = HealthSamplingEvent.objects.filter(
                    assignment=assignment,
                    sampling_date=current_date
                ).exists()

                existing_journal = JournalEntry.objects.filter(
                    batch=assignment.batch,
                    container=assignment.container,
                    entry_date=current_date
                ).exists()

                if not existing_sampling and not existing_journal:
                    # Debug: Show we're processing this assignment
                    if assignment.id == active_assignments[0].id and current_date == start_date:
                        print(f"🔍 Processing assignment {assignment.id} on {current_date}")

                    # Weekly health sampling (every 7 days, 30% chance)
                    if current_date.day % 7 == 0 and random.random() < 0.3:
                        # Create health sampling event
                        sampling_event = HealthSamplingEvent.objects.create(
                            assignment=assignment,
                            sampling_date=current_date,
                            number_of_fish_sampled=random.randint(20, 50),
                            avg_weight_g=Decimal(str(random.uniform(100, 500))),
                            std_dev_weight_g=Decimal(str(random.uniform(10, 50))),
                            min_weight_g=Decimal(str(random.uniform(80, 150))),
                            max_weight_g=Decimal(str(random.uniform(400, 600))),
                            avg_length_cm=Decimal(str(random.uniform(15, 35))),
                            std_dev_length_cm=Decimal(str(random.uniform(2, 8))),
                            min_length_cm=Decimal(str(random.uniform(12, 20))),
                            max_length_cm=Decimal(str(random.uniform(30, 40))),
                            avg_k_factor=Decimal(str(random.uniform(1.0, 1.8)))
                        )
                        sampling_count += 1

                        # Create corresponding journal entry
                        JournalEntry.objects.create(
                            batch=assignment.batch,
                            container=assignment.container,
                            user=system_user,
                            entry_date=current_date,
                            category='observation',
                            severity='low',
                            description=f'Routine health sampling completed. {sampling_event.number_of_fish_sampled} fish examined. Average weight: {sampling_event.avg_weight_g:.1f}g, K-factor: {sampling_event.avg_k_factor:.2f}',
                            resolution_status=True,
                            resolution_notes='Normal health parameters observed'
                        )
                        journal_count += 1

                    # Occasional health issues (5% chance per day)
                    elif random.random() < 0.05:
                        severity = random.choice(['low', 'medium', 'high'])
                        issue_type = random.choice(['parasite', 'wound', 'infection', 'stress'])

                        journal_entry = JournalEntry.objects.create(
                            batch=assignment.batch,
                            container=assignment.container,
                            user=system_user,
                            entry_date=current_date,
                            category='issue',
                            severity=severity,
                            description=f'Health concern detected: {issue_type} issue in {assignment.container.name}. Monitoring closely.',
                            resolution_status=False
                        )
                        journal_count += 1

        current_date += timedelta(days=1)

        # Progress indicator
        if current_date.day == 1 and current_date.month % 3 == 0:
            print(f"  Processing {current_date.strftime('%Y-%m')}...")

    print(f"✅ Created {sampling_count} new health sampling events")
    print(f"✅ Created {journal_count} new journal entries")

    if sampling_count == 0 and journal_count == 0:
        print("📊 No new health data created - existing data covers the date range")
    else:
        print(f"📅 Date range: {start_date} to {end_date}")

    # Show final summary statistics (includes existing + new)
    final_sampling = HealthSamplingEvent.objects.count()
    final_journal = JournalEntry.objects.count()

    # Show severity breakdown
    severity_counts = {}
    for entry in JournalEntry.objects.all():
        severity = entry.severity or 'unknown'
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    print("\n=== HEALTH MONITORING SUMMARY ===")
    print(f"Total sampling events: {final_sampling}")
    print(f"Total journal entries: {final_journal}")
    print("Severity breakdown:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count}")

    return sampling_count + journal_count

if __name__ == '__main__':
    create_health_monitoring()
