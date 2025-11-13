#!/usr/bin/env python3
"""
Cleanup Script: Remove all batch-related data while preserving infrastructure

This script deletes:
- All batches and related events
- Feed purchases (AUTO-* only)
- Feed container stock
- Historical records

This script preserves:
- Infrastructure (stations, halls, containers, sensors)
- Master data (species, stages, parameters, feeds)
- Geographies
"""

import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import (
    Batch, BatchContainerAssignment, GrowthSample, MortalityEvent, BatchCreationWorkflow, CreationAction,
    BatchTransferWorkflow, TransferAction
)
from apps.environmental.models import EnvironmentalReading
from apps.inventory.models import FeedingEvent, FeedPurchase, FeedContainerStock
from apps.health.models import JournalEntry
from apps.harvest.models import HarvestEvent, HarvestLot


def cleanup_batch_data():
    """Remove all batch-related data"""
    
    print(f"\n{'='*80}")
    print("BATCH DATA CLEANUP")
    print(f"{'='*80}\n")
    
    print("⚠️  This will delete ALL batch-related data!")
    print("Infrastructure and master data will be preserved.\n")
    
    # Count records before deletion
    counts = {
        'Batches': Batch.objects.count(),
        'Assignments': BatchContainerAssignment.objects.count(),
        'Creation Workflows': BatchCreationWorkflow.objects.count(),
        'Creation Actions': CreationAction.objects.count(),
        'Transfer Workflows': BatchTransferWorkflow.objects.count(),
        'Transfer Actions': TransferAction.objects.count(),
        'Environmental Readings': EnvironmentalReading.objects.count(),
        'Feeding Events': FeedingEvent.objects.count(),
        'Mortality Events': MortalityEvent.objects.count(),
        'Growth Samples': GrowthSample.objects.count(),
        'Journal Entries': JournalEntry.objects.count(),
        'Feed Purchases (AUTO)': FeedPurchase.objects.filter(batch_number__startswith='AUTO').count(),
        'Feed Stock': FeedContainerStock.objects.count(),
    }
    
    print("Records to be deleted:")
    for name, count in counts.items():
        print(f"  {name:30s}: {count:>8,}")
    
    total = sum(counts.values())
    print(f"\n  {'Total':30s}: {total:>8,}\n")
    
    if total == 0:
        print("✓ No batch data found. Database is already clean.\n")
        return
    
    # Confirm deletion
    response = input("Continue with deletion? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("\n✗ Cleanup cancelled.\n")
        return
    
    print(f"\n{'='*80}")
    print("DELETING DATA")
    print(f"{'='*80}\n")

    # Delete in correct order (respecting foreign keys)

    print("Deleting transfer actions...")
    count = TransferAction.objects.count()
    TransferAction.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting transfer workflows...")
    count = BatchTransferWorkflow.objects.count()
    BatchTransferWorkflow.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting creation actions...")
    count = CreationAction.objects.count()
    CreationAction.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting creation workflows...")
    count = BatchCreationWorkflow.objects.count()
    BatchCreationWorkflow.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting harvest lots...")
    count = HarvestLot.objects.count()
    HarvestLot.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting harvest events...")
    count = HarvestEvent.objects.count()
    HarvestEvent.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting growth samples...")
    count = GrowthSample.objects.count()
    GrowthSample.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting mortality events...")
    count = MortalityEvent.objects.count()
    MortalityEvent.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting journal entries...")
    count = JournalEntry.objects.count()
    JournalEntry.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting feeding events...")
    count = FeedingEvent.objects.count()
    FeedingEvent.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting environmental readings...")
    count = EnvironmentalReading.objects.count()
    EnvironmentalReading.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting batch assignments...")
    count = BatchContainerAssignment.objects.count()
    BatchContainerAssignment.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting batches...")
    count = Batch.objects.count()
    Batch.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting feed container stock...")
    count = FeedContainerStock.objects.count()
    FeedContainerStock.objects.all().delete()
    print(f"  ✓ Deleted {count:,} records")

    print("Deleting auto-generated feed purchases...")
    count = FeedPurchase.objects.filter(batch_number__startswith='AUTO').count()
    FeedPurchase.objects.filter(batch_number__startswith='AUTO').delete()
    print(f"  ✓ Deleted {count:,} records")
    
    print(f"\n{'='*80}")
    print("CLEANUP COMPLETE")
    print(f"{'='*80}\n")
    
    print("✓ All batch data deleted successfully")
    print("✓ Infrastructure preserved")
    print("✓ Master data preserved")
    print("\nReady for fresh data generation.\n")


if __name__ == '__main__':
    cleanup_batch_data()
