#!/usr/bin/env python3
"""Pilot migrate FishTalk lice samples for one stitched population component.

Source (FishTalk):
  - dbo.PublicLiceSamples (PopulationID, SampleID, SampleDate, NumberOfFish)
  - dbo.PublicLiceSampleData (SampleID, LiceStagesID, LiceCount)
  - dbo.LiceStages (LiceStagesID, DefaultText)

Target (AquaMind): apps.health.models.LiceCount (+ LiceType lookup).

Notes:
  - FishTalk LiceCount values are stored as float but appear to be whole counts
    (total lice observed across sampled fish). We round to int for AquaMind.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch
from apps.batch.models.assignment import BatchContainerAssignment
from apps.health.models import LiceCount, LiceType
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


User = get_user_model()

REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None

    cleaned = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.utc)


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    start_time: datetime
    end_time: datetime | None


def load_members_from_report(report_dir: Path, *, component_id: int | None, component_key: str | None) -> list[ComponentMember]:
    import csv

    path = report_dir / "population_members.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if component_id is not None and row.get("component_id") != str(component_id):
                continue
            if component_key is not None and row.get("component_key") != component_key:
                continue
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(ComponentMember(population_id=row.get("population_id", ""), start_time=start, end_time=end))

    members.sort(key=lambda m: m.start_time)
    return members


def resolve_component_key(report_dir: Path, *, component_id: int | None, component_key: str | None) -> str:
    if component_key:
        return component_key
    if component_id is None:
        raise ValueError("Provide --component-id or --component-key")

    import csv

    path = report_dir / "population_members.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("component_id") == str(component_id) and row.get("component_key"):
                return row["component_key"]

    raise ValueError("Unable to resolve component_key from report")


def parse_lice_stage(stage_text: str) -> tuple[str, str, str, str]:
    """Return (species, gender, development_stage, description)."""

    raw = (stage_text or "").strip()
    upper = raw.upper()

    # Species
    if "LEPO" in upper or "LEPEO" in upper:
        species = "Lepeophtheirus salmonis"
    elif "CALI" in upper or "CALIGUS" in upper:
        species = "Caligus elongatus"
    else:
        species = "Unknown"

    # Gender
    if "FEMALE" in upper:
        gender = "female"
    elif "MALE" in upper:
        gender = "male"
    else:
        gender = "unknown"

    # Development stage
    stage = "unknown"
    if "COPEP" in upper:
        stage = "copepodid"
    elif "CHALIM" in upper:
        stage = "chalimus"
    elif "PRE ADULT" in upper or "PREADULT" in upper:
        stage = "pre-adult"
    elif "ADULT" in upper:
        if "WITH STRINGS" in upper:
            stage = "adult_with_strings"
        elif "WITHOUT STRINGS" in upper:
            stage = "adult_without_strings"
        else:
            stage = "adult"
    elif "MOBILE" in upper or "MOVABLE" in upper:
        stage = "mobile"
    elif "ALL STAGES" in upper:
        stage = "all_stages"

    return species, gender, stage, raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate lice samples for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot create LiceCount.user")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    sample_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), pls.PopulationID) AS PopulationID, "
            "CONVERT(varchar(36), pls.SampleID) AS SampleID, "
            "CONVERT(varchar(19), pls.SampleDate, 120) AS SampleDate, "
            "CONVERT(varchar(32), pls.NumberOfFish) AS NumberOfFish "
            "FROM dbo.PublicLiceSamples pls "
            f"WHERE pls.PopulationID IN ({in_clause}) "
            f"AND pls.SampleDate >= '{start_str}' AND pls.SampleDate <= '{end_str}' "
            "ORDER BY pls.SampleDate ASC"
        ),
        headers=["PopulationID", "SampleID", "SampleDate", "NumberOfFish"],
    )
    sample_ids = [row.get("SampleID") for row in sample_rows if row.get("SampleID")]

    if not sample_ids:
        print(f"No lice samples found for component_key={component_key} (batch={batch.batch_number})")
        return 0

    # Fetch data rows for those samples.
    sample_in_clause = ",".join(f"'{sid}'" for sid in sample_ids)
    data_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), psd.SampleID) AS SampleID, "
            "CONVERT(varchar(32), psd.LiceStagesID) AS LiceStagesID, "
            "CONVERT(varchar(64), psd.LiceCount) AS LiceCount "
            "FROM dbo.PublicLiceSampleData psd "
            f"WHERE psd.SampleID IN ({sample_in_clause})"
        ),
        headers=["SampleID", "LiceStagesID", "LiceCount"],
    )

    stage_ids = sorted({row.get("LiceStagesID") for row in data_rows if row.get("LiceStagesID")})
    stage_name_by_id: dict[str, str] = {}
    if stage_ids:
        stage_in_clause = ",".join(str(int(sid)) for sid in stage_ids if str(sid).strip().isdigit())
        if stage_in_clause:
            stage_rows = extractor._run_sqlcmd(
                query=(
                    "SELECT CONVERT(varchar(32), ls.LiceStagesID) AS LiceStagesID, "
                    "ISNULL(ls.DefaultText, '') AS DefaultText "
                    "FROM dbo.LiceStages ls "
                    f"WHERE ls.LiceStagesID IN ({stage_in_clause})"
                ),
                headers=["LiceStagesID", "DefaultText"],
            )
            stage_name_by_id = {row.get("LiceStagesID", ""): (row.get("DefaultText") or "").strip() for row in stage_rows}

    if args.dry_run:
        print(
            f"[dry-run] Would migrate lice samples into batch={batch.batch_number}: "
            f"samples={len(sample_rows)}, sample_data_rows={len(data_rows)}"
        )
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)

    sample_by_id = {row.get("SampleID"): row for row in sample_rows}
    created = updated = skipped = 0

    with transaction.atomic():
        history_reason = f"FishTalk migration: lice for component {component_key}"
        for row in data_rows:
            sample_id = (row.get("SampleID") or "").strip()
            stage_id = (row.get("LiceStagesID") or "").strip()
            if not sample_id or not stage_id:
                skipped += 1
                continue

            sample = sample_by_id.get(sample_id) or {}
            population_id = (sample.get("PopulationID") or "").strip()
            sample_date = parse_dt(sample.get("SampleDate") or "")
            if not population_id or sample_date is None:
                skipped += 1
                continue

            try:
                fish_sampled = int(round(float(sample.get("NumberOfFish") or 0)))
            except Exception:
                fish_sampled = 0
            if fish_sampled <= 0:
                skipped += 1
                continue

            raw_count = (row.get("LiceCount") or "").strip()
            try:
                count_float = float(raw_count)
            except Exception:
                count_float = 0.0
            if count_float <= 0:
                skipped += 1
                continue

            count_value = int(round(count_float))
            stage_text = stage_name_by_id.get(stage_id, "")
            species, gender, development_stage, stage_desc = parse_lice_stage(stage_text or f"LiceStagesID={stage_id}")

            lice_type, _ = LiceType.objects.get_or_create(
                species=species,
                gender=gender,
                development_stage=development_stage,
                defaults={"description": stage_desc},
            )

            assignment = assignment_by_pop.get(population_id)
            container = assignment.container if assignment else None

            notes = (
                f"FishTalk lice sample SampleID={sample_id}; PopulationID={population_id}; "
                f"LiceStagesID={stage_id}; Stage='{stage_desc}'; RawCount={raw_count}"
            )

            defaults = {
                "batch": batch,
                "assignment": assignment,
                "container": container,
                "user": user,
                "count_date": ensure_aware(sample_date),
                "lice_type": lice_type,
                "count_value": count_value,
                "fish_sampled": fish_sampled,
                "notes": notes,
                "detection_method": "manual",
            }

            source_identifier = f"{sample_id}:{stage_id}"
            mapped = get_external_map("PublicLiceSampleData", source_identifier)
            if mapped:
                obj = LiceCount.objects.get(pk=mapped.target_object_id)
                for k, v in defaults.items():
                    setattr(obj, k, v)
                save_with_history(obj, user=user, reason=history_reason)
                updated += 1
            else:
                obj = LiceCount(**defaults)
                save_with_history(obj, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PublicLiceSampleData",
                    source_identifier=source_identifier,
                    defaults={
                        "target_app_label": obj._meta.app_label,
                        "target_model": obj._meta.model_name,
                        "target_object_id": obj.pk,
                        "metadata": {"sample_id": sample_id, "lice_stage_id": stage_id, "population_id": population_id},
                    },
                )
                created += 1

    print(
        f"Migrated lice counts for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, sample_rows={len(sample_rows)}, data_rows={len(data_rows)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
