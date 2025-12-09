#!/usr/bin/env python3
"""
Seed PlannedActivity records for existing batches using Activity Templates.

This script generates PlannedActivity records for batches that were created
before templates existed. It uses the templates created by 
01_initialize_activity_templates.py to ensure consistent, realistic data.

Key Features:
- Uses DAY_OFFSET templates to generate activities based on batch start_date
- Idempotent: clears existing PlannedActivity records before seeding
- Links activities to batch's associated scenario
- Calculates due dates correctly based on batch age

Usage:
    python scripts/data_generation/seed_planned_activities.py
    python scripts/data_generation/seed_planned_activities.py --limit 50
    python scripts/data_generation/seed_planned_activities.py --dry-run
"""
import os
import sys
import argparse
from datetime import timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from apps.planning.models import PlannedActivity, ActivityTemplate
from apps.batch.models import Batch


def seed_planned_activities_from_templates(limit=None, dry_run=False):
    """
    Generate PlannedActivity records for existing batches using templates.
    
    Args:
        limit: Maximum number of batches to process (None = all)
        dry_run: If True, don't actually create records
    
    Returns:
        dict with statistics about created records
    """
    print("=" * 80)
    print("SEED PLANNED ACTIVITIES FROM TEMPLATES")
    print("=" * 80)
    print()
    
    # Get admin user for created_by
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("❌ Error: 'admin' user not found. Please create an admin user first.")
        return {'success': False, 'error': 'admin user not found'}
    
    print(f"Using admin user: {admin_user.username} (id={admin_user.id})")
    
    # Get active templates with DAY_OFFSET trigger
    templates = ActivityTemplate.objects.filter(
        is_active=True,
        trigger_type='DAY_OFFSET'
    ).order_by('day_offset')
    
    if not templates.exists():
        print("❌ Error: No active DAY_OFFSET templates found.")
        print("   Run 01_initialize_activity_templates.py first.")
        return {'success': False, 'error': 'no templates'}
    
    print(f"Found {templates.count()} active templates")
    print()
    
    # Get ACTIVE batches only - completed/harvested batches don't need planned activities
    # This is realistic: you plan for ongoing work, not historical batches
    batches = Batch.objects.filter(
        status='ACTIVE',
        scenarios__isnull=False
    ).select_related('lifecycle_stage').prefetch_related('scenarios').distinct()
    
    if limit:
        batches = batches[:limit]
    
    batch_list = list(batches)
    
    if not batch_list:
        print("❌ Error: No batches with scenarios found.")
        return {'success': False, 'error': 'no batches'}
    
    print(f"Processing {len(batch_list)} batches with scenarios")
    print()
    
    if dry_run:
        print("DRY RUN - No records will be created")
        print()
    
    # Clear existing PlannedActivity records (idempotent)
    if not dry_run:
        existing_count = PlannedActivity.objects.count()
        if existing_count > 0:
            print(f"Clearing {existing_count} existing PlannedActivity records...")
            PlannedActivity.objects.all().delete()
            print()
    
    # Track statistics
    stats = {
        'batches_processed': 0,
        'activities_created': 0,
        'activities_pending': 0,
        'activities_completed': 0,
        'by_type': {},
    }
    
    today = timezone.now().date()
    
    with transaction.atomic():
        for batch in batch_list:
            scenario = batch.scenarios.first()
            if not scenario:
                continue
            
            batch_start = batch.start_date
            batch_age_days = (today - batch_start).days
            
            for template in templates:
                # Calculate due date from batch start
                due_date = batch_start + timedelta(days=template.day_offset)
                
                # Determine status based on due date
                # (We only process ACTIVE batches, so no need to check batch.status)
                if due_date < today:
                    # Past due - mark as completed (operational reality)
                    status = 'COMPLETED'
                    completed_at = timezone.make_aware(
                        timezone.datetime.combine(due_date, timezone.datetime.min.time())
                    )
                    completed_by = admin_user
                else:
                    # Future - pending
                    status = 'PENDING'
                    completed_at = None
                    completed_by = None
                
                if not dry_run:
                    PlannedActivity.objects.create(
                        scenario=scenario,
                        batch=batch,
                        activity_type=template.activity_type,
                        due_date=due_date,
                        status=status,
                        notes=template.notes_template,
                        created_by=admin_user,
                        completed_at=completed_at,
                        completed_by=completed_by,
                    )
                
                # Update stats
                stats['activities_created'] += 1
                stats['by_type'][template.activity_type] = stats['by_type'].get(template.activity_type, 0) + 1
                if status == 'PENDING':
                    stats['activities_pending'] += 1
                else:
                    stats['activities_completed'] += 1
            
            stats['batches_processed'] += 1
            
            # Progress indicator
            if stats['batches_processed'] % 20 == 0:
                print(f"  Processed {stats['batches_processed']}/{len(batch_list)} batches...")
    
    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Batches processed: {stats['batches_processed']}")
    print(f"Activities created: {stats['activities_created']}")
    print(f"  Pending: {stats['activities_pending']}")
    print(f"  Completed: {stats['activities_completed']}")
    print()
    print("By Activity Type:")
    for activity_type, count in sorted(stats['by_type'].items()):
        print(f"  {activity_type}: {count}")
    print()
    
    # KPI preview
    if not dry_run and stats['activities_created'] > 0:
        print("KPI Preview:")
        overdue = PlannedActivity.objects.filter(
            status='PENDING', 
            due_date__lt=today
        ).count()
        upcoming = PlannedActivity.objects.filter(
            status='PENDING',
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7)
        ).count()
        print(f"  Overdue: {overdue}")
        print(f"  Upcoming (7 days): {upcoming}")
        print()
    
    if not dry_run:
        print("✅ SEED COMPLETED SUCCESSFULLY")
    
    stats['success'] = True
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Seed PlannedActivity records from Activity Templates'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of batches to process (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating'
    )
    args = parser.parse_args()
    
    result = seed_planned_activities_from_templates(
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    if not result.get('success'):
        sys.exit(1)


if __name__ == '__main__':
    main()
