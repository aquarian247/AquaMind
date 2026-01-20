#!/usr/bin/env python3
# flake8: noqa
"""Migrate feed inventory data from FishTalk to AquaMind.

This script migrates:
1. Feed Suppliers → Cached lookup (used for Feed.brand and FeedPurchase.supplier)
2. Feed Types → Feed model
3. Feed Stores → FeedContainer model
4. Feed Deliveries → FeedPurchase model

Usage:
    # Dry run
    python pilot_migrate_feed_inventory.py --dry-run

    # Full migration
    python pilot_migrate_feed_inventory.py

    # Specific phase
    python pilot_migrate_feed_inventory.py --only=feed-types
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.inventory.models import Feed, FeedPurchase, FeedContainerStock
from apps.infrastructure.models import FeedContainer, Hall, Area
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

User = get_user_model()


def get_migration_user():
    """Get or create migration user."""
    user, _ = User.objects.get_or_create(
        username="migration_system",
        defaults={"email": "migration@aquamind.local", "is_active": False},
    )
    return user


def load_supplier_lookup(extractor) -> dict:
    """Load FishTalk suppliers into a lookup dict."""
    print("\n--- Loading Supplier Lookup ---")
    
    suppliers = extractor._run_sqlcmd(
        query="SELECT FeedSupplierID, Name FROM dbo.Ext_FeedSuppliers_v2",
        headers=["FeedSupplierID", "Name"]
    )
    
    lookup = {}
    for s in suppliers:
        supplier_id = s.get("FeedSupplierID", "").strip()
        name = s.get("Name", "").strip()
        if supplier_id and name:
            lookup[supplier_id] = name
    
    print(f"  Loaded {len(lookup)} suppliers")
    return lookup


def migrate_feed_types(extractor, supplier_lookup: dict, dry_run: bool = False) -> dict:
    """Migrate FishTalk feed types to AquaMind Feed model."""
    print("\n" + "=" * 70)
    print("PHASE 1: FEED TYPES")
    print("=" * 70)
    
    feed_types = extractor._run_sqlcmd(
        query="SELECT FeedTypeID, Name, FeedSupplierID FROM dbo.Ext_FeedTypes_v2 WHERE Name IS NOT NULL",
        headers=["FeedTypeID", "Name", "FeedSupplierID"]
    )
    
    print(f"  Found {len(feed_types)} feed types in FishTalk")
    
    # Check already migrated
    existing_ids = set(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="FeedType",
        ).values_list("source_identifier", flat=True)
    )
    
    to_migrate = [ft for ft in feed_types if ft.get("FeedTypeID", "").strip() not in existing_ids]
    print(f"  Already migrated: {len(existing_ids)}")
    print(f"  To migrate: {len(to_migrate)}")
    
    if dry_run:
        for ft in to_migrate[:10]:
            supplier_id = ft.get("FeedSupplierID", "")
            supplier_name = supplier_lookup.get(supplier_id, "Unknown")
            print(f"    Would create: {ft.get('Name', 'N/A')} (brand: {supplier_name})")
        if len(to_migrate) > 10:
            print(f"    ... and {len(to_migrate) - 10} more")
        return {"total": len(feed_types), "to_migrate": len(to_migrate)}
    
    created = 0
    skipped = 0
    errors = []
    
    with transaction.atomic():
        for ft in to_migrate:
            try:
                feed_type_id = ft.get("FeedTypeID", "").strip()
                name = ft.get("Name", "").strip()
                supplier_id = ft.get("FeedSupplierID", "").strip()
                
                if not feed_type_id or not name:
                    skipped += 1
                    continue
                
                supplier_name = supplier_lookup.get(supplier_id, "FishTalk Import")
                
                # Parse pellet size from name if present (e.g., "Nutra ST 0,5" -> 0.5mm)
                pellet_size = None
                size_category = "MEDIUM"  # Default
                
                # Try to extract size from name
                import re
                size_match = re.search(r'(\d+[,.]?\d*)\s*(mm|p)?$', name, re.IGNORECASE)
                if size_match:
                    try:
                        size_str = size_match.group(1).replace(',', '.')
                        parsed_size = Decimal(size_str)
                        # Cap at 99.99 to fit the field (max_digits=5, decimal_places=2)
                        # Reasonable pellet sizes are 0.1mm to 20mm
                        if parsed_size <= Decimal("99.99"):
                            pellet_size = parsed_size
                        if parsed_size < 1:
                            size_category = "MICRO"
                        elif parsed_size < 3:
                            size_category = "SMALL"
                        elif parsed_size < 6:
                            size_category = "MEDIUM"
                        else:
                            size_category = "LARGE"
                    except:
                        pass
                
                # Create Feed
                feed, was_created = Feed.objects.get_or_create(
                    name=f"FT-{feed_type_id} {name}",
                    defaults={
                        "brand": supplier_name,
                        "size_category": size_category,
                        "pellet_size_mm": pellet_size,
                        "description": f"FishTalk feed type: {name}",
                    }
                )
                
                if was_created:
                    created += 1
                    
                    # Track mapping
                    ExternalIdMap.objects.create(
                        source_system="FishTalk",
                        source_model="FeedType",
                        source_identifier=feed_type_id,
                        target_app_label="inventory",
                        target_model="feed",
                        target_object_id=feed.pk,
                        metadata={"original_name": name, "supplier_id": supplier_id},
                    )
                else:
                    skipped += 1
                    
            except Exception as e:
                errors.append({"feed_type_id": feed_type_id, "error": str(e)})
    
    print(f"\n  Results: {created} created, {skipped} skipped, {len(errors)} errors")
    if errors[:3]:
        for e in errors[:3]:
            print(f"    Error: {e}")
    
    return {"created": created, "skipped": skipped, "errors": len(errors)}


def migrate_feed_stores(extractor, dry_run: bool = False) -> dict:
    """Migrate FishTalk feed stores to AquaMind FeedContainer model."""
    print("\n" + "=" * 70)
    print("PHASE 2: FEED STORES (Silos/Containers)")
    print("=" * 70)
    
    feed_stores = extractor._run_sqlcmd(
        query="""
        SELECT FeedStoreID, FeedStoreName, OrgUnitID, Active, Capacity, FeedStoreTypeID 
        FROM dbo.Ext_FeedStore_v2 
        WHERE FeedStoreName IS NOT NULL
        """,
        headers=["FeedStoreID", "FeedStoreName", "OrgUnitID", "Active", "Capacity", "FeedStoreTypeID"]
    )
    
    print(f"  Found {len(feed_stores)} feed stores in FishTalk")
    
    # Filter out system entries (zero GUID prefix)
    real_stores = [fs for fs in feed_stores if not fs.get("FeedStoreID", "").startswith("00000000-0000-0000")]
    print(f"  Real stores (excluding system entries): {len(real_stores)}")
    
    # Check already migrated
    existing_ids = set(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="FeedStore",
        ).values_list("source_identifier", flat=True)
    )
    
    to_migrate = [fs for fs in real_stores if fs.get("FeedStoreID", "").strip() not in existing_ids]
    print(f"  Already migrated: {len(existing_ids)}")
    print(f"  To migrate: {len(to_migrate)}")
    
    # Build OrgUnit → Hall/Area lookup
    hall_by_orgunit = {}
    area_by_orgunit = {}
    
    for hall in Hall.objects.all():
        hall_maps = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            target_model="hall",
            target_object_id=hall.pk,
        )
        for m in hall_maps:
            hall_by_orgunit[m.source_identifier] = hall
    
    for area in Area.objects.all():
        area_maps = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            target_model="area",
            target_object_id=area.pk,
        )
        for m in area_maps:
            area_by_orgunit[m.source_identifier] = area
    
    print(f"  Mapped {len(hall_by_orgunit)} halls, {len(area_by_orgunit)} areas")
    
    if dry_run:
        for fs in to_migrate[:10]:
            capacity = fs.get("Capacity", "0")
            org_unit = fs.get("OrgUnitID", "")
            location = "Hall" if org_unit in hall_by_orgunit else ("Area" if org_unit in area_by_orgunit else "Unknown")
            print(f"    Would create: {fs.get('FeedStoreName', 'N/A')} ({capacity}kg) [{location}]")
        if len(to_migrate) > 10:
            print(f"    ... and {len(to_migrate) - 10} more")
        return {"total": len(real_stores), "to_migrate": len(to_migrate)}
    
    created = 0
    skipped = 0
    no_location = 0
    errors = []
    
    # Get a default location if needed
    default_hall = Hall.objects.first()
    default_area = Area.objects.first()
    
    with transaction.atomic():
        for fs in to_migrate:
            try:
                store_id = fs.get("FeedStoreID", "").strip()
                name = fs.get("FeedStoreName", "").strip()
                org_unit = fs.get("OrgUnitID", "").strip()
                capacity_str = fs.get("Capacity", "0").strip()
                is_active = fs.get("Active", "1") == "1"
                
                if not store_id or not name:
                    skipped += 1
                    continue
                
                # Parse capacity
                try:
                    capacity = Decimal(capacity_str) if capacity_str else Decimal("0")
                except:
                    capacity = Decimal("0")
                
                # Determine container type from name
                container_type = "SILO"  # Default
                name_lower = name.lower()
                if "barge" in name_lower or "flyder" in name_lower:
                    container_type = "BARGE"
                elif "tank" in name_lower:
                    container_type = "TANK"
                
                # Find location
                hall = hall_by_orgunit.get(org_unit)
                area = area_by_orgunit.get(org_unit)
                
                if not hall and not area:
                    no_location += 1
                    # Use default location
                    if default_hall:
                        hall = default_hall
                    elif default_area:
                        area = default_area
                    else:
                        skipped += 1
                        continue
                
                # Create FeedContainer
                feed_container = FeedContainer.objects.create(
                    name=f"FT-{name}",
                    container_type=container_type,
                    hall=hall if hall else None,
                    area=area if not hall else None,
                    capacity_kg=capacity if capacity > 0 else Decimal("10000"),  # Default 10 tons
                    active=is_active,
                )
                
                created += 1
                
                # Track mapping
                ExternalIdMap.objects.create(
                    source_system="FishTalk",
                    source_model="FeedStore",
                    source_identifier=store_id,
                    target_app_label="infrastructure",
                    target_model="feedcontainer",
                    target_object_id=feed_container.pk,
                    metadata={"original_name": name, "org_unit": org_unit},
                )
                
            except Exception as e:
                errors.append({"store_id": store_id, "name": name, "error": str(e)})
    
    print(f"\n  Results: {created} created, {skipped} skipped, {no_location} used default location")
    if errors[:3]:
        for e in errors[:3]:
            print(f"    Error: {e}")
    
    return {"created": created, "skipped": skipped, "no_location": no_location, "errors": len(errors)}


def migrate_feed_deliveries(extractor, supplier_lookup: dict, dry_run: bool = False, limit: int = None) -> dict:
    """Migrate FishTalk feed deliveries to AquaMind FeedPurchase model."""
    print("\n" + "=" * 70)
    print("PHASE 3: FEED DELIVERIES (Purchases)")
    print("=" * 70)
    
    limit_clause = f"TOP {limit}" if limit else ""
    
    deliveries = extractor._run_sqlcmd(
        query=f"""
        SELECT {limit_clause} FeedReceptionID, AmountKg, Price, FeedTypeID, FeedStoreID, 
               SupplierID, BatchNumber, ReceptionDate
        FROM dbo.Ext_FeedDelivery_v2 
        WHERE AmountKg > 0
        ORDER BY ReceptionDate DESC
        """,
        headers=["FeedReceptionID", "AmountKg", "Price", "FeedTypeID", "FeedStoreID", 
                 "SupplierID", "BatchNumber", "ReceptionDate"]
    )
    
    print(f"  Found {len(deliveries)} feed deliveries in FishTalk")
    
    # Check already migrated - use composite key (ReceptionID + FeedTypeID)
    existing_ids = set(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="FeedDelivery",
        ).values_list("source_identifier", flat=True)
    )
    
    def make_composite_id(d):
        return f"{d.get('FeedReceptionID', '').strip()}_{d.get('FeedTypeID', '').strip()}"
    
    to_migrate = [d for d in deliveries if make_composite_id(d) not in existing_ids]
    print(f"  Already migrated: {len(existing_ids)}")
    print(f"  To migrate: {len(to_migrate)}")
    
    # Build lookups
    feed_by_type_id = {}
    for idmap in ExternalIdMap.objects.filter(source_system="FishTalk", source_model="FeedType"):
        feed = Feed.objects.filter(pk=idmap.target_object_id).first()
        if feed:
            feed_by_type_id[idmap.source_identifier] = feed
    
    container_by_store_id = {}
    for idmap in ExternalIdMap.objects.filter(source_system="FishTalk", source_model="FeedStore"):
        container = FeedContainer.objects.filter(pk=idmap.target_object_id).first()
        if container:
            container_by_store_id[idmap.source_identifier] = container
    
    print(f"  Mapped {len(feed_by_type_id)} feed types, {len(container_by_store_id)} containers")
    
    if dry_run:
        for d in to_migrate[:10]:
            amount = d.get("AmountKg", "0")
            feed_type_id = d.get("FeedTypeID", "")
            feed = feed_by_type_id.get(feed_type_id)
            feed_name = feed.name if feed else f"Unknown ({feed_type_id})"
            print(f"    Would create: {amount}kg of {feed_name[:40]} on {d.get('ReceptionDate', 'N/A')}")
        if len(to_migrate) > 10:
            print(f"    ... and {len(to_migrate) - 10} more")
        return {"total": len(deliveries), "to_migrate": len(to_migrate)}
    
    created = 0
    skipped = 0
    no_feed = 0
    errors = []
    
    for d in to_migrate:
        try:
            with transaction.atomic():
                reception_id = d.get("FeedReceptionID", "").strip()
                amount_str = d.get("AmountKg", "0").strip()
                price_str = d.get("Price", "").strip()
                feed_type_id = d.get("FeedTypeID", "").strip()
                store_id = d.get("FeedStoreID", "").strip()
                supplier_id = d.get("SupplierID", "").strip()
                batch_number = d.get("BatchNumber", "").strip()
                reception_date_str = d.get("ReceptionDate", "").strip()
                
                if not reception_id:
                    skipped += 1
                    continue
                
                # Parse amount
                try:
                    amount = Decimal(amount_str) if amount_str else Decimal("0")
                except:
                    amount = Decimal("0")
                
                if amount <= 0:
                    skipped += 1
                    continue
                
                # Get feed type
                feed = feed_by_type_id.get(feed_type_id)
                if not feed:
                    no_feed += 1
                    # Try to get any feed as fallback
                    feed = Feed.objects.first()
                    if not feed:
                        skipped += 1
                        continue
                
                # Parse price (total or per kg?)
                cost_per_kg = Decimal("0.01")  # Default
                if price_str:
                    try:
                        total_price = Decimal(price_str)
                        if total_price > 0 and amount > 0:
                            cost_per_kg = total_price / amount
                    except:
                        pass
                
                # Parse date
                purchase_date = None
                if reception_date_str:
                    try:
                        # Handle various date formats
                        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
                            try:
                                purchase_date = datetime.strptime(reception_date_str[:10], "%Y-%m-%d").date()
                                break
                            except:
                                continue
                    except:
                        pass
                
                if not purchase_date:
                    purchase_date = datetime.now().date()
                
                # Get supplier name
                supplier_name = supplier_lookup.get(supplier_id, "FishTalk Import")
                
                # Create FeedPurchase
                purchase = FeedPurchase.objects.create(
                    feed=feed,
                    purchase_date=purchase_date,
                    quantity_kg=amount,
                    cost_per_kg=cost_per_kg if cost_per_kg > 0 else Decimal("0.01"),
                    supplier=supplier_name,
                    batch_number=batch_number or f"FT-{reception_id[:8]}",
                    notes=f"FishTalk delivery {reception_id}",
                )
                
                created += 1
                
                # Track mapping with composite key (ReceptionID + FeedTypeID)
                composite_id = f"{reception_id}_{feed_type_id}"
                ExternalIdMap.objects.create(
                    source_system="FishTalk",
                    source_model="FeedDelivery",
                    source_identifier=composite_id,
                    target_app_label="inventory",
                    target_model="feedpurchase",
                    target_object_id=purchase.pk,
                    metadata={
                        "reception_id": reception_id,
                        "feed_type_id": feed_type_id,
                        "store_id": store_id,
                        "supplier_id": supplier_id,
                    },
                )
                
                # Create stock entry if we have a container
                container = container_by_store_id.get(store_id)
                if container:
                    FeedContainerStock.objects.create(
                        feed_container=container,
                        feed_purchase=purchase,
                        quantity_kg=amount,
                        entry_date=timezone.make_aware(datetime.combine(purchase_date, datetime.min.time())),
                    )
        except Exception as e:
            errors.append({"reception_id": reception_id, "error": str(e)})
    
    print(f"\n  Results: {created} created, {skipped} skipped, {no_feed} missing feed type")
    if errors[:3]:
        for e in errors[:3]:
            print(f"    Error: {e}")
    
    return {"created": created, "skipped": skipped, "no_feed": no_feed, "errors": len(errors)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate feed inventory data from FishTalk"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without executing",
    )
    parser.add_argument(
        "--only",
        choices=["feed-types", "feed-stores", "feed-deliveries"],
        help="Run only a specific migration phase",
    )
    parser.add_argument(
        "--delivery-limit",
        type=int,
        default=None,
        help="Limit number of deliveries to migrate (for testing)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 70)
    print("FEED INVENTORY MIGRATION")
    print("=" * 70)
    
    if args.dry_run:
        print("[DRY RUN MODE]")
    
    # Connect to FishTalk
    extractor = BaseExtractor(ExtractionContext(profile="fishtalk_readonly"))
    
    # Load supplier lookup (always needed)
    supplier_lookup = load_supplier_lookup(extractor)
    
    results = {}
    
    # Phase 1: Feed Types
    if not args.only or args.only == "feed-types":
        results["feed_types"] = migrate_feed_types(extractor, supplier_lookup, dry_run=args.dry_run)
    
    # Phase 2: Feed Stores (requires infrastructure to be migrated first)
    if not args.only or args.only == "feed-stores":
        results["feed_stores"] = migrate_feed_stores(extractor, dry_run=args.dry_run)
    
    # Phase 3: Feed Deliveries (requires feed types and stores)
    if not args.only or args.only == "feed-deliveries":
        results["feed_deliveries"] = migrate_feed_deliveries(
            extractor, supplier_lookup, 
            dry_run=args.dry_run, 
            limit=args.delivery_limit
        )
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for phase, data in results.items():
        if isinstance(data, dict):
            if "created" in data:
                print(f"  {phase}: {data.get('created', 0)} created, {data.get('skipped', 0)} skipped")
            else:
                print(f"  {phase}: {data.get('to_migrate', data.get('total', 0))} to migrate")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes made")
    else:
        print("\n[SUCCESS] Feed inventory migration completed")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
