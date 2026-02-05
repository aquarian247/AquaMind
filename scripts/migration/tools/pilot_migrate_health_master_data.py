#!/usr/bin/env python3
# flake8: noqa
"""Migrate health master data from FishTalk to AquaMind.

This script migrates:
1. Mortality Cause Groups → MortalityReason (parent=null)
2. Mortality Causes → MortalityReason (with parent FK)
3. VaccineTypes → VaccinationType
4. Sample types → SampleType
5. Score-like health parameters → HealthParameter
6. Treatment Types → (for reference, stored in metadata)

Notes:
- FishTalk "Culling" is both a mortality reason AND an activity - we flag it
- Health parameters are inferred from FishTalk sample attribute names (score-like only).
- FishParameterScore data requires per-fish sample values; not seeded here.

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

from apps.health.models import HealthParameter, MortalityReason, SampleType, VaccinationType
from apps.health.models.health_observation import ParameterScoreDefinition
from apps.health.models.mortality import MortalityRecord
from apps.health.models.treatment import Treatment
from apps.health.models.lab_sample import HealthLabSample
from apps.health.models.health_observation import FishParameterScore
from django.db.models import Q
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


def normalize_prefixed_name(obj, raw_name: str) -> bool:
    """If object name starts with 'FT-' and raw name is free, rename it."""
    if not obj or not raw_name:
        return False
    if obj.name == raw_name:
        return False
    if not obj.name.startswith("FT-"):
        return False
    model = obj.__class__
    if model.objects.filter(name=raw_name).exclude(pk=obj.pk).exists():
        return False
    obj.name = raw_name
    obj.save()
    return True


def load_used_mortality_cause_ids(csv_dir: Path | None) -> set[str]:
    if not csv_dir:
        return set()
    cause_ids: set[str] = set()
    for filename, column in (
        ("mortality_actions.csv", "MortalityCauseID"),
        ("culling.csv", "CullingCauseID"),
        ("spawning_selection.csv", "CullingCauseID"),
    ):
        path = csv_dir / filename
        if not path.exists():
            continue
        import csv

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                value = (row.get(column) or "").strip()
                if value:
                    cause_ids.add(value)
    return cause_ids


def load_used_vaccine_type_ids(csv_dir: Path | None) -> set[str]:
    if not csv_dir:
        return set()
    path = csv_dir / "treatments.csv"
    if not path.exists():
        return set()
    import csv

    ids: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            value = (row.get("VaccineType") or "").strip()
            if value:
                ids.add(value)
    return ids


def load_used_sample_type_names(csv_dir: Path | None) -> set[str]:
    if not csv_dir:
        return set()
    path = csv_dir / "user_sample_types.csv"
    if not path.exists():
        return set()
    import csv

    names: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("SampleTypeName") or "").strip()
            if name:
                names.add(name)
    return names


def load_used_health_parameter_names(csv_dir: Path | None) -> set[str]:
    if not csv_dir:
        return set()
    path = csv_dir / "user_sample_attributes.csv"
    if not path.exists():
        return set()
    import csv

    names: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("AttributeName") or "").strip()
            if name:
                names.add(name)
    return names


def migrate_mortality_cause_groups(
    extractor,
    dry_run: bool = False,
    used_group_ids: set[str] | None = None,
) -> dict:
    """Migrate FishTalk mortality cause groups as top-level MortalityReason."""
    print("\n--- Mortality Cause Groups ---")
    
    groups = extractor._run_sqlcmd(
        query="SELECT MortalityCauseGroupID, Name FROM dbo.Ext_MortalityCauseGroups_v2 ORDER BY Name",
        headers=["MortalityCauseGroupID", "Name"]
    )
    
    if used_group_ids:
        groups = [g for g in groups if (g.get("MortalityCauseGroupID") or "").strip() in used_group_ids]

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
                if not dry_run:
                    reason = MortalityReason.objects.filter(pk=existing.target_object_id).first()
                    if reason:
                        normalize_prefixed_name(reason, name)
                skipped += 1
                continue
            
            # Create or get MortalityReason
            reason, was_created = MortalityReason.objects.get_or_create(
                name=name,
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


def migrate_mortality_causes(
    extractor,
    dry_run: bool = False,
    used_cause_ids: set[str] | None = None,
) -> tuple[dict, set[str]]:
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
    
    if used_cause_ids:
        causes = [c for c in causes if (c.get("MortalityCauseID") or "").strip() in used_cause_ids]

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
        group_ids = {c.get("MortalityCauseGroupID", "").strip() for c in causes if c.get("MortalityCauseGroupID")}
        return {"causes": len(causes)}, group_ids
    
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
                if not dry_run:
                    reason = MortalityReason.objects.filter(pk=existing.target_object_id).first()
                    if reason:
                        normalize_prefixed_name(reason, name)
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
                name=name,
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
    group_ids = {c.get("MortalityCauseGroupID", "").strip() for c in causes if c.get("MortalityCauseGroupID")}
    return {"created": created, "skipped": skipped}, group_ids


def migrate_vaccination_types(
    extractor,
    dry_run: bool = False,
    csv_dir: Path | None = None,
    used_type_ids: set[str] | None = None,
) -> dict:
    """Migrate FishTalk vaccination types as VaccinationType."""
    print("\n--- Vaccination Types ---")
    
    rows: list[dict] = []
    if csv_dir:
        csv_path = csv_dir / "vaccine_types.csv"
        if csv_path.exists():
            import csv
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
    if not rows:
        # Actual columns: VaccineTypeID, VaccineName
        rows = extractor._run_sqlcmd(
            query="SELECT VaccineTypeID, VaccineName FROM dbo.VaccineTypes ORDER BY VaccineName",
            headers=["VaccineTypeID", "VaccineName"],
        )
    
    if used_type_ids:
        rows = [r for r in rows if (r.get("VaccineTypeID") or "").strip() in used_type_ids]

    print(f"  Found {len(rows)} vaccination types in FishTalk")
    
    if dry_run:
        for m in rows[:15]:
            print(f"    Would create: {m.get('VaccineName', 'N/A')}")
        if len(rows) > 15:
            print(f"    ... and {len(rows) - 15} more")
        return {"types": len(rows)}
    
    created = 0
    skipped = 0
    
    with transaction.atomic():
        for m in rows:
            vaccine_id = (m.get("VaccineTypeID") or "").strip()
            name = (m.get("VaccineName") or "").strip()
            
            if not vaccine_id or not name:
                skipped += 1
                continue
            
            # Check if already migrated
            existing = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="VaccineType",
                source_identifier=vaccine_id,
            ).first()
            
            if existing:
                vac = VaccinationType.objects.filter(pk=existing.target_object_id).first()
                if vac:
                    normalize_prefixed_name(vac, name)
                skipped += 1
                continue
            
            # Create VaccinationType
            vac_type, was_created = VaccinationType.objects.get_or_create(
                name=name,
                defaults={
                    "manufacturer": "FishTalk Migration",
                    "dosage": "",
                    "description": f"FishTalk vaccination type: {name}",
                }
            )
            
            if was_created:
                created += 1
            
            # Track mapping
            ExternalIdMap.objects.create(
                source_system="FishTalk",
                source_model="VaccineType",
                source_identifier=vaccine_id,
                target_app_label="health",
                target_model="vaccinationtype",
                target_object_id=vac_type.pk,
                metadata={"original_name": name},
            )
    
    print(f"  Created: {created}, Skipped: {skipped}")
    return {"created": created, "skipped": skipped}


def migrate_sample_types(
    extractor,
    dry_run: bool = False,
    csv_dir: Path | None = None,
    used_names: set[str] | None = None,
) -> dict:
    """Migrate FishTalk sample types as SampleType."""
    print("\n--- Sample Types ---")

    names: set[str] = set(used_names or [])
    if not names:
        rows = extractor._run_sqlcmd(
            query="SELECT UserSampleTypeID, DefaultText FROM dbo.UserSampleType ORDER BY DefaultText",
            headers=["UserSampleTypeID", "DefaultText"],
        )
        for row in rows:
            name = (row.get("DefaultText") or "").strip()
            if name:
                names.add(name)

    names = {n for n in names if n}
    print(f"  Found {len(names)} sample types in FishTalk")

    if dry_run:
        for name in sorted(names)[:15]:
            print(f"    Would create: {name}")
        if len(names) > 15:
            print(f"    ... and {len(names) - 15} more")
        return {"types": len(names)}

    created = 0
    skipped = 0
    with transaction.atomic():
        for name in sorted(names):
            st, was_created = SampleType.objects.get_or_create(
                name=name,
                defaults={"description": f"FishTalk sample type: {name}"},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

    print(f"  Created: {created}, Skipped: {skipped}")
    return {"created": created, "skipped": skipped}


def _infer_score_range(name: str) -> tuple[int, int] | None:
    import re

    pattern = re.compile(r"[\[\(]\s*(\d+)\s*-\s*(\d+)\s*[\]\)]")
    match = pattern.search(name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def migrate_health_parameters(
    extractor,
    dry_run: bool = False,
    csv_dir: Path | None = None,
    used_names: set[str] | None = None,
) -> dict:
    """Seed HealthParameter from FishTalk sample attribute names."""
    print("\n--- Health Parameters ---")

    attr_names: set[str] = set(used_names or [])
    if not attr_names:
        rows = extractor._run_sqlcmd(
            query="SELECT AttributeID, Name FROM dbo.FishGroupAttributes ORDER BY Name",
            headers=["AttributeID", "Name"],
        )
        for row in rows:
            name = (row.get("Name") or "").strip()
            if name:
                attr_names.add(name)

    # Only keep score-like parameters (avoid numeric measurements)
    score_names = sorted(
        name for name in attr_names
        if "score" in name.lower() or _infer_score_range(name)
    )

    print(f"  Found {len(score_names)} score-like parameters in FishTalk")

    if dry_run:
        for name in score_names[:15]:
            print(f"    Would create: {name}")
        if len(score_names) > 15:
            print(f"    ... and {len(score_names) - 15} more")
        return {"parameters": len(score_names)}

    created = 0
    skipped = 0
    definitions_created = 0
    with transaction.atomic():
        for name in score_names:
            score_range = _infer_score_range(name) or (0, 5)
            hp, was_created = HealthParameter.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"FishTalk health parameter: {name}",
                    "min_score": score_range[0],
                    "max_score": score_range[1],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

            # Ensure score definitions exist
            for score_value in range(score_range[0], score_range[1] + 1):
                _, def_created = ParameterScoreDefinition.objects.get_or_create(
                    parameter=hp,
                    score_value=score_value,
                    defaults={"label": f"Score {score_value}"},
                )
                if def_created:
                    definitions_created += 1

    print(f"  Created: {created}, Skipped: {skipped}, Definitions: {definitions_created}")
    return {"created": created, "skipped": skipped, "definitions": definitions_created}


def prune_unused_master_data(
    *,
    used_cause_ids: set[str],
    used_group_ids: set[str],
    used_vaccine_type_ids: set[str],
    used_sample_type_names: set[str],
    used_parameter_names: set[str],
    dry_run: bool,
) -> dict:
    print("\n--- Prune Unused Master Data ---")

    results: dict[str, int] = {}

    # Mortality reasons (FishTalk sourced only)
    mortality_maps = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model__in=["MortalityCause", "MortalityCauseGroup"],
    )
    cause_keep_ids = set()
    group_keep_ids = set()
    if used_cause_ids:
        cause_keep_ids.update(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="MortalityCause",
                source_identifier__in=used_cause_ids,
            ).values_list("target_object_id", flat=True)
        )
    if used_group_ids:
        group_keep_ids.update(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="MortalityCauseGroup",
                source_identifier__in=used_group_ids,
            ).values_list("target_object_id", flat=True)
        )

    keep_reason_ids = set(MortalityRecord.objects.values_list("reason_id", flat=True))
    keep_reason_ids.update(cause_keep_ids)
    keep_reason_ids.update(group_keep_ids)
    # Keep parents of kept reasons (avoid orphaning group labels)
    keep_reason_ids.update(
        MortalityReason.objects.filter(id__in=keep_reason_ids).values_list("parent_id", flat=True)
    )

    candidate_reason_ids = list(mortality_maps.values_list("target_object_id", flat=True))
    reasons_to_delete = (
        MortalityReason.objects.filter(id__in=candidate_reason_ids)
        .exclude(id__in=keep_reason_ids)
        .exclude(mortality_records__isnull=False)
    )
    delete_reason_ids = list(reasons_to_delete.values_list("id", flat=True))
    if delete_reason_ids:
        if not dry_run:
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                target_model="mortalityreason",
                target_object_id__in=delete_reason_ids,
            ).delete()
            reasons_to_delete.delete()
    results["mortality_reasons_deleted"] = len(delete_reason_ids)

    # Vaccination types (FishTalk sourced only)
    vacc_keep_ids = set(
        Treatment.objects.exclude(vaccination_type__isnull=True).values_list("vaccination_type_id", flat=True)
    )
    if used_vaccine_type_ids:
        vacc_keep_ids.update(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="VaccineType",
                source_identifier__in=used_vaccine_type_ids,
            ).values_list("target_object_id", flat=True)
        )

    vacc_maps = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model__in=["VaccineType", "VaccinationMethod"],
    )
    vacc_candidate_ids = list(vacc_maps.values_list("target_object_id", flat=True))
    vacc_to_delete = (
        VaccinationType.objects.filter(id__in=vacc_candidate_ids)
        .exclude(id__in=vacc_keep_ids)
        .exclude(treatments__isnull=False)
    )
    delete_vacc_ids = list(vacc_to_delete.values_list("id", flat=True))
    if delete_vacc_ids:
        if not dry_run:
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                target_model="vaccinationtype",
                target_object_id__in=delete_vacc_ids,
            ).delete()
            vacc_to_delete.delete()
    results["vaccination_types_deleted"] = len(delete_vacc_ids)

    # Sample types (only FishTalk-tagged)
    sample_to_delete = SampleType.objects.filter(
        description__startswith="FishTalk sample type:"
    ).exclude(name__in=used_sample_type_names).exclude(lab_samples__isnull=False)
    delete_sample_ids = list(sample_to_delete.values_list("id", flat=True))
    if delete_sample_ids and not dry_run:
        sample_to_delete.delete()
    results["sample_types_deleted"] = len(delete_sample_ids)

    # Health parameters (only FishTalk-tagged)
    param_keep_ids = set(
        FishParameterScore.objects.values_list("parameter_id", flat=True)
    )
    if used_parameter_names:
        param_keep_ids.update(
            HealthParameter.objects.filter(name__in=used_parameter_names).values_list("id", flat=True)
        )
    params_to_delete = (
        HealthParameter.objects.filter(description__startswith="FishTalk health parameter:")
        .exclude(id__in=param_keep_ids)
    )
    delete_param_ids = list(params_to_delete.values_list("id", flat=True))
    if delete_param_ids and not dry_run:
        params_to_delete.delete()
    results["health_parameters_deleted"] = len(delete_param_ids)

    print(
        f"  Deleted: mortality_reasons={results['mortality_reasons_deleted']}, "
        f"vaccinations={results['vaccination_types_deleted']}, "
        f"sample_types={results['sample_types_deleted']}, "
        f"health_parameters={results['health_parameters_deleted']}"
    )
    return results


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
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory when available",
    )
    parser.add_argument(
        "--include-unused",
        action="store_true",
        help="Include unused master data (default filters by referenced values when CSVs are provided)",
    )
    parser.add_argument(
        "--prune-unused",
        action="store_true",
        help="Delete unused FishTalk-seeded master data (safe: skips anything referenced in AquaMind)",
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
    csv_dir = Path(args.use_csv) if args.use_csv else None
    used_cause_ids = set()
    used_group_ids: set[str] | None = None
    used_vaccine_type_ids = set()
    used_sample_type_names = set()
    used_parameter_names = set()
    if csv_dir and not args.include_unused:
        used_cause_ids = load_used_mortality_cause_ids(csv_dir)
        used_vaccine_type_ids = load_used_vaccine_type_ids(csv_dir)
        used_sample_type_names = load_used_sample_type_names(csv_dir)
        used_parameter_names = load_used_health_parameter_names(csv_dir)
    
    results = {}
    
    # Migrate mortality cause groups (top level)
    # Migrate mortality causes (with parent links)
    causes_result, used_group_ids = migrate_mortality_causes(
        extractor,
        dry_run=args.dry_run,
        used_cause_ids=used_cause_ids or None,
    )
    results["causes"] = causes_result

    # Migrate mortality cause groups (top level) after causes to avoid unused
    results["groups"] = migrate_mortality_cause_groups(
        extractor,
        dry_run=args.dry_run,
        used_group_ids=used_group_ids if not args.include_unused else None,
    )
    
    # Migrate vaccination types
    results["vaccinations"] = migrate_vaccination_types(
        extractor,
        dry_run=args.dry_run,
        csv_dir=csv_dir,
        used_type_ids=used_vaccine_type_ids or None,
    )

    # Migrate sample types
    results["sample_types"] = migrate_sample_types(
        extractor,
        dry_run=args.dry_run,
        csv_dir=csv_dir,
        used_names=used_sample_type_names or None,
    )

    # Migrate health parameters (score-like)
    results["health_parameters"] = migrate_health_parameters(
        extractor,
        dry_run=args.dry_run,
        csv_dir=csv_dir,
        used_names=used_parameter_names or None,
    )

    if args.prune_unused and not args.dry_run:
        results["pruned"] = prune_unused_master_data(
            used_cause_ids=used_cause_ids,
            used_group_ids=used_group_ids or set(),
            used_vaccine_type_ids=used_vaccine_type_ids,
            used_sample_type_names=used_sample_type_names,
            used_parameter_names=used_parameter_names,
            dry_run=args.dry_run,
        )
    
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
