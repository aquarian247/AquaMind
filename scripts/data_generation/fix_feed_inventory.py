#!/usr/bin/env python3
"""
Quick Fix: Initialize Feed Inventory & Lice Types

This script fixes the missing feed inventory that causes 0 feeding events.
It's designed to be run non-interactively and is idempotent.
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.inventory.models import Feed, FeedPurchase, FeedContainerStock
from apps.infrastructure.models import FeedContainer
from apps.health.models import LiceType


def initialize_feed_inventory(force=True):
    """Initialize feed inventory in all feed containers"""
    print("\n" + "="*80)
    print("INITIALIZING FEED INVENTORY")
    print("="*80 + "\n")
    
    # Check if inventory already exists
    existing_stock = FeedContainerStock.objects.count()
    if existing_stock > 0 and not force:
        print(f"⚠ Found {existing_stock} existing feed stock entries")
        print("  Use --force to clear and recreate")
        return False
    
    if existing_stock > 0:
        print(f"✓ Clearing {existing_stock} existing stock entries...")
        FeedContainerStock.objects.all().delete()
        print(f"✓ Clearing {FeedPurchase.objects.count()} existing purchases...")
        FeedPurchase.objects.all().delete()
    
    # Get all feed containers
    feed_containers = FeedContainer.objects.filter(active=True)
    total_containers = feed_containers.count()
    
    if total_containers == 0:
        print("✗ No feed containers found! Run Phase 1 first.")
        return False
    
    print(f"✓ Found {total_containers} feed containers to stock\n")
    
    # Get feed types
    feed_types = Feed.objects.filter(is_active=True)
    if feed_types.count() == 0:
        print("✗ No feed types found! Run Phase 2 first.")
        return False
    
    print(f"✓ Found {feed_types.count()} feed types\n")
    
    # Purchase date: 30 days ago
    purchase_date = date.today() - timedelta(days=30)
    
    # Suppliers
    suppliers = ['BioMar', 'Skretting', 'Cargill', 'Aller Aqua']
    
    created_purchases = 0
    created_stock = 0
    
    print("Creating feed inventory...")
    for idx, container in enumerate(feed_containers, 1):
        # Select feed type based on container
        if 'Silo' in container.name or container.container_type == 'SILO':
            # Freshwater silos: use starter/grower feeds
            feed = feed_types.filter(name__contains='Starter').first() or feed_types.first()
            quantity_kg = Decimal('5000.0')  # 5 tonnes per silo
            cost_per_kg = Decimal('2.50')
        else:  # BARGE
            # Sea barges: use finisher feeds
            feed = feed_types.filter(name__contains='Finisher').first() or feed_types.last()
            quantity_kg = Decimal('25000.0')  # 25 tonnes per barge
            cost_per_kg = Decimal('2.00')
        
        # Select supplier (rotate)
        supplier = suppliers[idx % len(suppliers)]
        
        # Create FeedPurchase
        purchase = FeedPurchase.objects.create(
            feed=feed,
            purchase_date=purchase_date,
            supplier=supplier,
            batch_number=f"INIT-{purchase_date.strftime('%Y%m%d')}-{idx:04d}",
            quantity_kg=quantity_kg,
            cost_per_kg=cost_per_kg,
            expiry_date=purchase_date + timedelta(days=365),
            notes=f'Initial inventory for {container.name}',
        )
        created_purchases += 1
        
        # Create FeedContainerStock (FIFO entry)
        from django.utils import timezone
        stock = FeedContainerStock.objects.create(
            feed_container=container,
            feed_purchase=purchase,
            quantity_kg=quantity_kg,
            entry_date=timezone.make_aware(
                datetime.combine(purchase_date, datetime.min.time())
            ),
        )
        created_stock += 1
        
        if (idx % 50 == 0):
            print(f"  Processed {idx}/{total_containers} containers...")
    
    # Calculate total inventory
    total_inventory_kg = FeedContainerStock.objects.aggregate(
        total=django.db.models.Sum('quantity_kg')
    )['total'] or 0
    
    print(f"\n✓ Created {created_purchases} feed purchases")
    print(f"✓ Created {created_stock} feed stock entries")
    print(f"✓ Total initial inventory: {total_inventory_kg:,.0f} kg ({total_inventory_kg/1000:.0f} tonnes)\n")
    
    return True


def initialize_lice_types():
    """Initialize lice type master data"""
    print("\n" + "="*80)
    print("INITIALIZING LICE TYPES")
    print("="*80 + "\n")
    
    existing_count = LiceType.objects.count()
    if existing_count > 0:
        print(f"✓ Found {existing_count} existing lice types (skipping)")
        return True
    
    lice_types_data = [
        # Lepeophtheirus salmonis (primary sea lice species)
        ('Lepeophtheirus salmonis', 'copepodid', None, 'Free-swimming infective larvae'),
        ('Lepeophtheirus salmonis', 'chalimus', None, 'Attached juvenile stage (4 substages)'),
        ('Lepeophtheirus salmonis', 'pre-adult', 'male', 'Mobile pre-adult male'),
        ('Lepeophtheirus salmonis', 'pre-adult', 'female', 'Mobile pre-adult female'),
        ('Lepeophtheirus salmonis', 'adult', 'male', 'Adult male louse'),
        ('Lepeophtheirus salmonis', 'adult', 'female', 'Adult female louse (gravid)'),
        
        # Caligus elongatus (secondary species)
        ('Caligus elongatus', 'copepodid', None, 'Free-swimming infective larvae'),
        ('Caligus elongatus', 'chalimus', None, 'Attached juvenile stage'),
        ('Caligus elongatus', 'pre-adult', 'male', 'Mobile pre-adult male'),
        ('Caligus elongatus', 'pre-adult', 'female', 'Mobile pre-adult female'),
        ('Caligus elongatus', 'adult', 'male', 'Adult male louse'),
        ('Caligus elongatus', 'adult', 'female', 'Adult female louse'),
    ]
    
    created = 0
    for species, dev_stage, gender, description in lice_types_data:
        LiceType.objects.create(
            species=species,
            development_stage=dev_stage,
            gender=gender if gender else 'unknown',
            description=description  # Changed from 'notes' to 'description'
        )
        created += 1
    
    print(f"✓ Created {created} lice types\n")
    return True


def verify_initialization():
    """Verify that initialization was successful"""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80 + "\n")
    
    checks = [
        ("Feed Containers", FeedContainer.objects.count(), 200, ">"),
        ("Feed Types", Feed.objects.count(), 3, ">="),
        ("Feed Purchases", FeedPurchase.objects.count(), 200, ">"),
        ("Feed Stock Entries", FeedContainerStock.objects.count(), 200, ">"),
        ("Lice Types", LiceType.objects.count(), 10, ">="),
    ]
    
    all_pass = True
    for name, actual, expected, op in checks:
        if op == ">":
            passed = actual > expected
        else:
            passed = actual >= expected
        
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {actual} (expected {op} {expected})")
        
        if not passed:
            all_pass = False
    
    print()
    return all_pass


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix missing feed inventory and lice types'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Clear existing inventory and recreate'
    )
    
    args = parser.parse_args()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Quick Fix: Feed Inventory & Lice Types".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Initialize feed inventory
        if not initialize_feed_inventory(force=args.force):
            return 1
        
        # Initialize lice types
        if not initialize_lice_types():
            return 1
        
        # Verify
        if not verify_initialization():
            print("⚠ Some checks failed!")
            return 1
        
        print("="*80)
        print("✓ FEED INVENTORY INITIALIZATION COMPLETE!")
        print("="*80)
        print("\nNext steps:")
        print("1. Test single batch generation:")
        print("   python scripts/data_generation/03_event_engine_core.py \\")
        print("     --start-date 2025-01-01 \\")
        print("     --eggs 3500000 \\")
        print("     --geography 'Faroe Islands' \\")
        print("     --duration 200")
        print("\n2. Verify feeding events were created:")
        print("   SELECT COUNT(*) FROM inventory_feedingevent;")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

