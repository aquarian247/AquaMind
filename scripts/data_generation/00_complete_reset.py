#!/usr/bin/env python3
"""
Complete Non-Interactive Data Reset

Cleans all batch data and reinitializes feed inventory.
Designed for automated workflows (no prompts).

Usage:
    python scripts/data_generation/00_complete_reset.py
    python scripts/data_generation/00_complete_reset.py --keep-infrastructure
"""

import os
import sys
import django
import argparse

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import Batch, BatchContainerAssignment, MortalityEvent, GrowthSample
from apps.inventory.models import FeedingEvent, FeedPurchase, FeedContainerStock
from apps.environmental.models import EnvironmentalReading
from apps.health.models import JournalEntry, LiceCount


def delete_batch_data():
    """Delete all batch-related data (non-interactive)"""
    print("\n" + "="*80)
    print("DELETING ALL BATCH DATA")
    print("="*80 + "\n")
    
    from apps.batch.models import (
        BatchTransferWorkflow, TransferAction,
        BatchCreationWorkflow, CreationAction
    )
    
    deletions = [
        ("Feeding Events", FeedingEvent.objects.all()),
        ("Environmental Readings", EnvironmentalReading.objects.all()),
        ("Mortality Events", MortalityEvent.objects.all()),
        ("Growth Samples", GrowthSample.objects.all()),
        ("Journal Entries", JournalEntry.objects.all()),
        ("Lice Counts", LiceCount.objects.all()),
        ("Transfer Actions", TransferAction.objects.all()),
        ("Transfer Workflows", BatchTransferWorkflow.objects.all()),
        ("Creation Actions", CreationAction.objects.all()),
        ("Creation Workflows", BatchCreationWorkflow.objects.all()),
        ("Assignments", BatchContainerAssignment.objects.all()),
        ("Batches", Batch.objects.all()),
        ("Feed Stock", FeedContainerStock.objects.all()),
        ("Feed Purchases", FeedPurchase.objects.all()),
    ]
    
    for name, queryset in deletions:
        count = queryset.count()
        if count > 0:
            queryset.delete()
            print(f"✓ Deleted {count:,} {name}")
        else:
            print(f"  Skipped {name} (empty)")
    
    print("\n✅ All batch data deleted\n")


def reinitialize_feed_inventory():
    """Reinitialize feed inventory (calls fix_feed_inventory.py)"""
    print("="*80)
    print("REINITIALIZING FEED INVENTORY")
    print("="*80 + "\n")
    
    import subprocess
    
    fix_script = os.path.join(
        os.path.dirname(__file__),
        'fix_feed_inventory.py'
    )
    
    result = subprocess.run(
        ['python', fix_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Feed inventory reinitialized")
        return True
    else:
        print("❌ Feed inventory initialization failed:")
        print(result.stderr)
        return False


def verify_system_ready():
    """Verify system is ready for batch generation"""
    print("="*80)
    print("SYSTEM VERIFICATION")
    print("="*80 + "\n")
    
    from apps.infrastructure.models import Container, FeedContainer
    from apps.inventory.models import Feed
    from apps.health.models import LiceType
    from apps.batch.models import LifeCycleStage
    
    checks = [
        ("Containers", Container.objects.count(), 2000, ">"),
        ("Feed Containers", FeedContainer.objects.count(), 200, ">"),
        ("Lifecycle Stages", LifeCycleStage.objects.count(), 6, ">="),
        ("Feed Types", Feed.objects.count(), 6, ">="),
        ("Feed Purchases", FeedPurchase.objects.count(), 200, ">"),
        ("Feed Stock", FeedContainerStock.objects.count(), 200, ">"),
        ("Lice Types", LiceType.objects.count(), 10, ">="),
        ("Batches", Batch.objects.count(), 0, "=="),
        ("Active Assignments", BatchContainerAssignment.objects.filter(is_active=True).count(), 0, "=="),
    ]
    
    all_pass = True
    for name, actual, expected, op in checks:
        if op == ">":
            passed = actual > expected
            status_msg = f"expected > {expected}"
        elif op == ">=":
            passed = actual >= expected
            status_msg = f"expected >= {expected}"
        elif op == "==":
            passed = actual == expected
            status_msg = f"expected == {expected}"
        else:
            passed = False
            status_msg = "unknown check"
        
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {actual:,} ({status_msg})")
        
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✅ System ready for batch generation!")
    else:
        print("\n❌ System not ready - fix errors above")
    
    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description='Complete non-interactive data reset'
    )
    parser.add_argument(
        '--keep-infrastructure',
        action='store_true',
        help='Skip infrastructure checks (faster)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Complete Data Reset (Non-Interactive)".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Step 1: Delete all batch data
        delete_batch_data()
        
        # Step 2: Reinitialize feed inventory
        if not reinitialize_feed_inventory():
            return 1
        
        # Step 3: Verify system
        if not verify_system_ready():
            return 1
        
        print("\n" + "="*80)
        print("✅ RESET COMPLETE - READY FOR BATCH GENERATION")
        print("="*80)
        print("\nNext steps:")
        print("  1. Test single batch:")
        print("     python scripts/data_generation/03_event_engine_core.py \\")
        print("       --start-date 2025-01-01 \\")
        print("       --eggs 3500000 \\")
        print("       --geography 'Faroe Islands' \\")
        print("       --duration 200")
        print()
        print("  2. Generate 20 batches:")
        print("     python scripts/data_generation/04_batch_orchestrator.py \\")
        print("       --execute \\")
        print("       --batches 20")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

