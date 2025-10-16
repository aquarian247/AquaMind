#!/usr/bin/env python3
"""
AquaMind Test Data Generation - Phase 0: Cleanup Existing Data

This script removes all existing batch and event data while preserving infrastructure.
Run this BEFORE Phase 1 to start with a clean slate.

Deletes (in FK-safe order):
- Feeding events and summaries
- Environmental readings
- Health records (journals, samples, mortality, treatments, lice counts)
- Growth samples
- Batch transfers and composition
- Container assignments
- Batches
- All associated history tables (auto-cascade)

Preserves:
- Infrastructure (geographies, stations, halls, containers, sensors)
- Master data (species, lifecycle stages, feed types, etc.)
"""

import os
import sys
import django

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import transaction
from apps.batch.models import (
    Batch, BatchContainerAssignment, BatchTransfer, 
    MortalityEvent, GrowthSample, BatchComposition
)
from apps.inventory.models import (
    FeedingEvent, ContainerFeedingSummary, BatchFeedingSummary,
    FeedContainerStock
)
from apps.environmental.models import EnvironmentalReading
from apps.health.models import (
    JournalEntry, HealthSamplingEvent, IndividualFishObservation,
    MortalityRecord, LiceCount, Treatment, HealthLabSample
)


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def get_counts():
    """Get current counts of all event data"""
    return {
        'batches': Batch.objects.count(),
        'assignments': BatchContainerAssignment.objects.count(),
        'transfers': BatchTransfer.objects.count(),
        'compositions': BatchComposition.objects.count(),
        'mortality_events': MortalityEvent.objects.count(),
        'growth_samples': GrowthSample.objects.count(),
        'feeding_events': FeedingEvent.objects.count(),
        'container_summaries': ContainerFeedingSummary.objects.count(),
        'batch_summaries': BatchFeedingSummary.objects.count(),
        'environmental_readings': EnvironmentalReading.objects.count(),
        'journal_entries': JournalEntry.objects.count(),
        'health_samplings': HealthSamplingEvent.objects.count(),
        'fish_observations': IndividualFishObservation.objects.count(),
        'mortality_records': MortalityRecord.objects.count(),
        'lice_counts': LiceCount.objects.count(),
        'treatments': Treatment.objects.count(),
        'lab_samples': HealthLabSample.objects.count(),
    }


def print_counts(counts, title):
    """Print counts in a formatted table"""
    print(f"\n{title}:")
    print("-" * 80)
    
    # Group by category
    categories = {
        'Batch Management': ['batches', 'assignments', 'transfers', 'compositions'],
        'Growth & Mortality': ['growth_samples', 'mortality_events'],
        'Feeding & Inventory': ['feeding_events', 'container_summaries', 'batch_summaries'],
        'Environmental': ['environmental_readings'],
        'Health Monitoring': ['journal_entries', 'health_samplings', 'fish_observations', 
                             'mortality_records', 'lice_counts', 'treatments', 'lab_samples'],
    }
    
    for category, fields in categories.items():
        print(f"\n{category}:")
        for field in fields:
            if field in counts:
                name = field.replace('_', ' ').title()
                print(f"  {name:.<40} {counts[field]:>10,}")
    
    total = sum(counts.values())
    print(f"\n{'Total Records':.<40} {total:>10,}")
    print("-" * 80)


def cleanup_data(dry_run=False, confirmed=False):
    """Delete all event data in FK-safe order"""
    
    if dry_run:
        print_section("DRY RUN MODE - No data will be deleted")
    else:
        print_section("DELETING DATA - This cannot be undone!")
    
    # Get before counts
    before = get_counts()
    print_counts(before, "Current Data Counts")
    
    if sum(before.values()) == 0:
        print("\n✓ No event data found - database is already clean!")
        return 0
    
    if not dry_run and not confirmed:
        response = input("\n⚠️  Are you sure you want to delete all this data? (type 'DELETE' to confirm): ")
        if response != 'DELETE':
            print("\n✗ Cleanup cancelled")
            return 1
    
    deleted_counts = {}
    
    try:
        with transaction.atomic():
            print_section("Deleting Event Data (in FK-safe order)")
            
            # Step 1: Delete feeding summaries (depend on assignments and events)
            print("Step 1: Deleting feeding summaries...")
            deleted_counts['container_summaries'] = ContainerFeedingSummary.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['container_summaries']:,} container feeding summaries")
            
            deleted_counts['batch_summaries'] = BatchFeedingSummary.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['batch_summaries']:,} batch feeding summaries")
            
            # Step 2: Delete feeding events
            print("\nStep 2: Deleting feeding events...")
            deleted_counts['feeding_events'] = FeedingEvent.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['feeding_events']:,} feeding events")
            
            # Step 3: Delete environmental readings
            print("\nStep 3: Deleting environmental readings...")
            deleted_counts['environmental_readings'] = EnvironmentalReading.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['environmental_readings']:,} environmental readings")
            
            # Step 4: Delete health records (various types)
            print("\nStep 4: Deleting health records...")
            
            # Individual fish observations (depends on sampling events)
            deleted_counts['fish_observations'] = IndividualFishObservation.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['fish_observations']:,} fish observations")
            
            # Health sampling events
            deleted_counts['health_samplings'] = HealthSamplingEvent.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['health_samplings']:,} health sampling events")
            
            # Lab samples
            deleted_counts['lab_samples'] = HealthLabSample.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['lab_samples']:,} lab samples")
            
            # Treatments
            deleted_counts['treatments'] = Treatment.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['treatments']:,} treatments")
            
            # Lice counts
            deleted_counts['lice_counts'] = LiceCount.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['lice_counts']:,} lice counts")
            
            # Mortality records
            deleted_counts['mortality_records'] = MortalityRecord.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['mortality_records']:,} mortality records")
            
            # Journal entries
            deleted_counts['journal_entries'] = JournalEntry.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['journal_entries']:,} journal entries")
            
            # Step 5: Delete batch-level records
            print("\nStep 5: Deleting batch records...")
            
            # Growth samples (depends on assignments)
            deleted_counts['growth_samples'] = GrowthSample.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['growth_samples']:,} growth samples")
            
            # Mortality events
            deleted_counts['mortality_events'] = MortalityEvent.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['mortality_events']:,} mortality events")
            
            # Batch compositions
            deleted_counts['compositions'] = BatchComposition.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['compositions']:,} batch compositions")
            
            # Batch transfers
            deleted_counts['transfers'] = BatchTransfer.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['transfers']:,} batch transfers")
            
            # Container assignments
            deleted_counts['assignments'] = BatchContainerAssignment.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['assignments']:,} container assignments")
            
            # Batches (top-level)
            deleted_counts['batches'] = Batch.objects.all().delete()[0]
            print(f"  ✓ Deleted {deleted_counts['batches']:,} batches")
            
            # Step 6: Reset feed container stock (optional - keep initial inventory)
            print("\nStep 6: Feed inventory status...")
            stock_count = FeedContainerStock.objects.count()
            print(f"  ℹ  Preserved {stock_count:,} feed container stock records (initial inventory)")
            
            if dry_run:
                print("\n⚠️  DRY RUN - Rolling back transaction (no changes made)")
                raise Exception("Dry run - rolling back")
            
    except Exception as e:
        if dry_run and "Dry run" in str(e):
            print("\n✓ Dry run complete - no data was actually deleted")
            return 0
        else:
            print(f"\n✗ Error during cleanup: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Get after counts
    print_section("Cleanup Complete!")
    after = get_counts()
    print_counts(after, "Remaining Data Counts")
    
    # Summary
    print_section("Deletion Summary")
    total_deleted = sum(deleted_counts.values())
    print(f"Total records deleted: {total_deleted:,}")
    print("\n✓ All event data has been removed")
    print("✓ Infrastructure and master data preserved")
    print("✓ History tables automatically cleaned (cascade)")
    print("\nDatabase is now ready for Phase 1: Bootstrap Infrastructure")
    
    return 0


def main():
    """Main execution"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  AquaMind - Phase 0: Cleanup Existing Data".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    import argparse
    parser = argparse.ArgumentParser(description='Cleanup existing test data')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt (use with caution!)')
    args = parser.parse_args()
    
    try:
        return cleanup_data(dry_run=args.dry_run, confirmed=args.confirm)
    except KeyboardInterrupt:
        print("\n\n✗ Cleanup cancelled by user")
        return 1


if __name__ == '__main__':
    sys.exit(main())
