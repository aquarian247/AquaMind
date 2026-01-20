#!/usr/bin/env python3
# flake8: noqa
"""Migrate health master data from FishTalk to AquaMind.

This script migrates:
1. Mortality Cause Groups → MortalityReason (parent=null)
2. Mortality Causes → MortalityReason (with parent FK)
3. Vaccination Methods → VaccinationType
4. Treatment Types → (for reference, stored in metadata)

Notes:
- FishTalk "Culling" is both a mortality reason AND an activity - we flag it
- Health Parameters (0-3 scoring) are NOT in FishTalk - only Scotland uses health scoring
- Faroes use Excel for health parameters, not FishTalk

Usage:
    # Dry run
    python pilot_migrate_health_master_data.py --dry-run

    # Full migration
    python pilot_migrate_health_master_data.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

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

from django.db import transaction, connection
from django.contrib.auth import get_user_model

from apps.health.models import MortalityReason, VaccinationType
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

User = get_user_model()


def check_and_add_parent_field():
    """Check if MortalityReason has parent FK, add if missing."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'health_mortalityreason' AND column_name = 'parent_id'
        """)
        result = cursor.fetchone()
        
        if result:
            print("  parent_id field already exists")
            return True
        
        # Add the parent FK
        print("  Adding parent_id field to MortalityReason...")
        cursor.execute("""
            ALTER TABLE health_mortalityreason 
            ADD COLUMN parent_id BIGINT NULL 
            REFERENCES health_mortalityreason(id) ON DELETE SET NULL
        """)
        cursor.execute("""
            CREATE INDEX health_mortalityreason_parent_idx 
            ON health_mortalityreason(parent_id)
        """)
        print("  parent_id field added successfully")
        return True


def migrate_mortality_cause_groups(extractor, dry_run: bool = False) -> dict:
    """Migrate FishTalk mortality cause groups as top-level MortalityReason."""
    print("\n--- Mortality Cause Groups ---")
    
    groups = extractor._run_sqlcmd(
        query="SELECT MortalityCauseGroupID, Name FROM dbo.Ext_MortalityCauseGroups_v2 ORDER BY Name",
        headers=["MortalityCauseGroupID", "Name"]
    )
    
    print(f"  Found {len(groups)} cause groups in FishTalk")
    
    if dry_run:
        for g in groups:
            print(f"    Would create: {g.get('Name', 'N/A')}")
        return {"groups": len(groups)}
    
    created = 0
    skipped = 0
    
    with transaction.atomic():
        for g in groups:
            group_id = g.get("MortalityCauseGroupID", "").strip()
            name = g.get("Name", "").strip()
            
            if not group_id or not name:
                skipped += 1
                continue
            
            # Check if already migrated
            existing = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="MortalityCauseGroup",
                source_identifier=group_id,
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Create or get MortalityReason
            reason, was_created = MortalityReason.objects.get_or_create(
                name=f"FT-{name}",
                defaults={"description": f"FishTalk Mortality Cause Group: {name}"}
            )
            
            if was_created:
                created += 1
            
            # Track mapping
            ExternalIdMap.objects.create(
                source_system="FishTalk",
                source_model="MortalityCauseGroup",
                source_identifier=group_id,
                target_app_label="health",
                target_model="mortalityreason",
                target_object_id=reason.pk,
                metadata={"original_name": name, "is_group": True},
            )
    
    print(f"  Created: {created}, Skipped: {skipped}")
    return {"created": created, "skipped": skipped}


def migrate_mortality_causes(extractor, dry_run: bool = False) -> dict:
    """Migrate FishTalk mortality causes as child MortalityReason."""
    print("\n--- Mortality Causes ---")
    
    causes = extractor._run_sqlcmd(
        query="""
        SELECT MortalityCauseID, Name, MortalityCauseGroupID 
        FROM dbo.Ext_MortalityCauses_v2 
        ORDER BY Name
        """,
        headers=["MortalityCauseID", "Name", "MortalityCauseGroupID"]
    )
    
    print(f"  Found {len(causes)} causes in FishTalk")
    
    # Flag problematic "Culling" entry
    culling_entries = [c for c in causes if "culling" in c.get("Name", "").lower()]
    if culling_entries:
        print(f"  [WARNING] Found {len(culling_entries)} 'Culling' entries - these are both mortality and activity")
    
    if dry_run:
        for c in causes[:15]:
            group_id = c.get("MortalityCauseGroupID", "N/A")
            print(f"    Would create: {c.get('Name', 'N/A')} (group: {group_id})")
        if len(causes) > 15:
            print(f"    ... and {len(causes) - 15} more")
        return {"causes": len(causes)}
    
    created = 0
    skipped = 0
    
    with transaction.atomic():
        for c in causes:
            cause_id = c.get("MortalityCauseID", "").strip()
            name = c.get("Name", "").strip()
            group_id = c.get("MortalityCauseGroupID", "").strip()
            
            if not cause_id or not name:
                skipped += 1
                continue
            
            # Check if already migrated
            existing = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="MortalityCause",
                source_identifier=cause_id,
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Find parent reason (from group migration)
            parent = None
            if group_id:
                parent_map = ExternalIdMap.objects.filter(
                    source_system="FishTalk",
                    source_model="MortalityCauseGroup",
                    source_identifier=group_id,
                ).first()
                if parent_map:
                    parent = MortalityReason.objects.filter(pk=parent_map.target_object_id).first()
            
            # Build description
            description = f"FishTalk Mortality Cause: {name}"
            # Check for culling-related terms in name
            if "culling" in name.lower() or "cull" in name.lower():
                description += " [Also used for culling operations]"
            
            # Create MortalityReason
            reason, was_created = MortalityReason.objects.get_or_create(
                name=f"FT-{name}",
                defaults={"description": description}
            )
            
            # Set parent if field exists and parent found
            if parent:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE health_mortalityreason SET parent_id = %s WHERE id = %s",
                            [parent.pk, reason.pk]
                        )
                except Exception as e:
                    print(f"    [WARNING] Could not set parent for {name}: {e}")
            
            if was_created:
                created += 1
            
            # Track mapping
            ExternalIdMap.objects.create(
                source_system="FishTalk",
                source_model="MortalityCause",
                source_identifier=cause_id,
                target_app_label="health",
                target_model="mortalityreason",
                target_object_id=reason.pk,
                metadata={
                    "original_name": name,
                    "is_cause": True,
                    "group_id": group_id,
                },
            )
    
    print(f"  Created: {created}, Skipped: {skipped}")
    return {"created": created, "skipped": skipped}


def migrate_vaccination_methods(extractor, dry_run: bool = False) -> dict:
    """Migrate FishTalk vaccination methods as VaccinationType."""
    print("\n--- Vaccination Methods ---")
    
    # Actual columns: VaccinationMethodID, DefaultText, Active, SystemDelivered
    methods = extractor._run_sqlcmd(
        query="SELECT VaccinationMethodID, DefaultText, Active FROM dbo.Ext_VaccinationMethod_v2",
        headers=["VaccinationMethodID", "DefaultText", "Active"]
    )
    
    print(f"  Found {len(methods)} vaccination methods in FishTalk")
    
    if dry_run:
        for m in methods:
            active = "Active" if m.get('Active') == '1' else "Inactive"
            print(f"    Would create: {m.get('DefaultText', 'N/A')} [{active}]")
        return {"methods": len(methods)}
    
    created = 0
    skipped = 0
    
    with transaction.atomic():
        for m in methods:
            method_id = m.get("VaccinationMethodID", "").strip()
            name = m.get("DefaultText", "").strip()
            is_active = m.get("Active", "1")
            
            if not method_id or not name:
                skipped += 1
                continue
            
            # Check if already migrated
            existing = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="VaccinationMethod",
                source_identifier=method_id,
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Create VaccinationType
            vac_type, was_created = VaccinationType.objects.get_or_create(
                name=f"FT-{name}",
                defaults={
                    "manufacturer": "FishTalk Migration",
                    "dosage": "",
                    "description": f"FishTalk vaccination method: {name}",
                }
            )
            
            if was_created:
                created += 1
            
            # Track mapping
            ExternalIdMap.objects.create(
                source_system="FishTalk",
                source_model="VaccinationMethod",
                source_identifier=method_id,
                target_app_label="health",
                target_model="vaccinationtype",
                target_object_id=vac_type.pk,
                metadata={"original_name": name, "is_active": is_active},
            )
    
    print(f"  Created: {created}, Skipped: {skipped}")
    return {"created": created, "skipped": skipped}


def migrate_treatment_types(extractor, dry_run: bool = False) -> dict:
    """Extract and document FishTalk treatment types (for reference)."""
    print("\n--- Treatment Types (Reference) ---")
    
    # Actual columns: TreatmentTypesID, DefaultText, Active, SystemDelivered
    types = extractor._run_sqlcmd(
        query="SELECT TreatmentTypesID, DefaultText, Active FROM dbo.Ext_TreatmentTypes_v2",
        headers=["TreatmentTypesID", "DefaultText", "Active"]
    )
    
    print(f"  Found {len(types)} treatment types in FishTalk")
    
    active_count = sum(1 for t in types if t.get("Active") == "1")
    
    print(f"    Active: {active_count}")
    
    for t in types[:10]:
        status = "Active" if t.get("Active") == "1" else "Inactive"
        print(f"    - {t.get('DefaultText', 'N/A')} [{status}]")
    if len(types) > 10:
        print(f"    ... and {len(types) - 10} more")
    
    # Treatment types are stored as metadata - AquaMind uses treatments differently
    return {"types": len(types), "active": active_count}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate health master data from FishTalk"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without executing",
    )
    parser.add_argument(
        "--skip-schema-check",
        action="store_true",
        help="Skip adding parent_id field to MortalityReason",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 70)
    print("HEALTH MASTER DATA MIGRATION")
    print("=" * 70)
    
    if args.dry_run:
        print("[DRY RUN MODE]")
    
    # Check/add parent field
    if not args.skip_schema_check and not args.dry_run:
        print("\nChecking MortalityReason schema...")
        try:
            check_and_add_parent_field()
        except Exception as e:
            print(f"  [WARNING] Could not add parent field: {e}")
            print("  Continuing with flat structure...")
    
    # Connect to FishTalk
    extractor = BaseExtractor(ExtractionContext(profile="fishtalk_readonly"))
    
    results = {}
    
    # Migrate mortality cause groups (top level)
    results["groups"] = migrate_mortality_cause_groups(extractor, dry_run=args.dry_run)
    
    # Migrate mortality causes (with parent links)
    results["causes"] = migrate_mortality_causes(extractor, dry_run=args.dry_run)
    
    # Migrate vaccination methods
    results["vaccinations"] = migrate_vaccination_methods(extractor, dry_run=args.dry_run)
    
    # Document treatment types
    results["treatments"] = migrate_treatment_types(extractor, dry_run=args.dry_run)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for category, data in results.items():
        if isinstance(data, dict) and "created" in data:
            print(f"  {category}: {data.get('created', 0)} created, {data.get('skipped', 0)} skipped")
        else:
            print(f"  {category}: {data}")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes made")
    else:
        print("\n[SUCCESS] Health master data migrated")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
