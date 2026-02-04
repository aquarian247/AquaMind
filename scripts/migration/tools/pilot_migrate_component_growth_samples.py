#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk weight samples into GrowthSample records.

Source (FishTalk):
  - dbo.Ext_WeightSamples_v2 (preferred)
  - dbo.PublicWeightSamples (fallback)

Target (AquaMind):
  - apps.batch.models.GrowthSample

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
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models.assignment import BatchContainerAssignment
from apps.batch.models import GrowthSample
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.tools.etl_loader import ETLDataLoader


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


def to_decimal(value: str, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


def to_int(value: str) -> int:
    if value is None:
        return 0
    raw = str(value).strip()
    if not raw:
        return 0
    try:
        return int(round(float(raw)))
    except Exception:
        return 0


def weight_to_grams(value: str) -> Decimal | None:
    raw = to_decimal(value, places="0.01")
    if raw is None or raw <= 0:
        return None
    # Heuristic: values <= 50 are likely kg, larger values assumed grams.
    grams = raw * Decimal("1000") if raw <= 50 else raw
    return grams.quantize(Decimal("0.01"))


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
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    start_time=start,
                    end_time=end,
                )
            )

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


def load_weight_samples_sql(
    extractor: BaseExtractor,
    population_ids: list[str],
    *,
    window_start: datetime,
    window_end: datetime,
) -> tuple[str, list[dict[str, str]]]:
    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    ext_query = (
        "SELECT CONVERT(varchar(36), ws.SampleID) AS SampleID, "
        "CONVERT(varchar(36), ws.PopulationID) AS PopulationID, "
        "CONVERT(varchar(23), ws.SampleDate, 121) AS SampleDate, "
        "CONVERT(varchar(32), ws.AvgWeight) AS AvgWeight, "
        "CONVERT(varchar(32), ws.CVPercent) AS CVPercent, "
        "CONVERT(varchar(32), ws.ConditionFactor) AS ConditionFactor, "
        "CONVERT(varchar(32), ws.NumberOfFish) AS NumberOfFish, "
        "CONVERT(varchar(5), ws.Corrective) AS Corrective, "
        "CONVERT(varchar(32), ws.SampleReason) AS SampleReason, "
        "CONVERT(varchar(32), ws.OperationType) AS OperationType "
        "FROM dbo.Ext_WeightSamples_v2 ws "
        f"WHERE ws.PopulationID IN ({in_clause}) "
        "AND ws.OperationType = 10 "
        f"AND ws.SampleDate >= '{start_str}' AND ws.SampleDate <= '{end_str}' "
        "ORDER BY ws.SampleDate ASC"
    )

    try:
        rows = extractor._run_sqlcmd(
            query=ext_query,
            headers=[
                "SampleID",
                "PopulationID",
                "SampleDate",
                "AvgWeight",
                "CVPercent",
                "ConditionFactor",
                "NumberOfFish",
                "Corrective",
                "SampleReason",
                "OperationType",
            ],
        )
        return "Ext_WeightSamples_v2", rows
    except Exception:
        rows = extractor._run_sqlcmd(
            query=(
                "SELECT CONVERT(varchar(36), ws.SampleID) AS SampleID, "
                "CONVERT(varchar(36), ws.PopulationID) AS PopulationID, "
                "CONVERT(varchar(23), ws.SampleDate, 121) AS SampleDate, "
                "CONVERT(varchar(32), ws.AvgWeight) AS AvgWeight, "
                "CONVERT(varchar(32), ws.CVPercent) AS CVPercent, "
                "CONVERT(varchar(32), ws.ConditionFactor) AS ConditionFactor, "
                "CONVERT(varchar(32), ws.NumberOfFish) AS NumberOfFish, "
                "CONVERT(varchar(5), ws.Corrective) AS Corrective, "
                "CONVERT(varchar(32), ws.SampleReason) AS SampleReason "
                "FROM dbo.PublicWeightSamples ws "
                f"WHERE ws.PopulationID IN ({in_clause}) "
                f"AND ws.SampleDate >= '{start_str}' AND ws.SampleDate <= '{end_str}' "
                "ORDER BY ws.SampleDate ASC"
            ),
            headers=[
                "SampleID",
                "PopulationID",
                "SampleDate",
                "AvgWeight",
                "CVPercent",
                "ConditionFactor",
                "NumberOfFish",
                "Corrective",
                "SampleReason",
            ],
        )
        return "PublicWeightSamples", rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate FishTalk weight samples for a stitched component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    if not population_ids:
        raise SystemExit("No population ids found in report")

    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    use_csv = args.use_csv is not None
    if use_csv:
        loader = ETLDataLoader(args.use_csv)
        rows = loader.get_weight_samples_for_populations(
            set(population_ids),
            start_time=window_start,
            end_time=window_end,
        )
        source_table = None
    else:
        extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
        source_table, rows = load_weight_samples_sql(
            extractor,
            population_ids,
            window_start=window_start,
            window_end=window_end,
        )

    if not rows:
        print(f"No weight samples found for component_key={component_key}")
        return 0

    if args.dry_run:
        print(f"[dry-run] Weight samples found: {len(rows)} rows")
        return 0

    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        history_reason = f"FishTalk migration: growth samples for component {component_key}"

        for row in rows:
            sample_id = (row.get("SampleID") or "").strip()
            population_id = (row.get("PopulationID") or "").strip()
            if not sample_id or not population_id:
                skipped += 1
                continue

            assignment_map = get_external_map("Populations", population_id)
            if not assignment_map:
                skipped += 1
                continue
            assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)

            sample_dt = parse_dt(row.get("SampleDate", ""))
            if sample_dt is None:
                skipped += 1
                continue

            avg_weight_g = weight_to_grams(row.get("AvgWeight", ""))
            if avg_weight_g is None:
                skipped += 1
                continue

            sample_size = max(to_int(row.get("NumberOfFish", "")), 0)
            condition_factor = to_decimal(row.get("ConditionFactor", ""), places="0.01")

            source_model = row.get("_source_table") or source_table or "WeightSamples"
            notes = f"FishTalk {source_model} SampleID={sample_id}; PopulationID={population_id}."
            if row.get("SampleReason"):
                notes = f"{notes} SampleReason={row.get('SampleReason')}"
            if row.get("OperationType"):
                notes = f"{notes} OperationType={row.get('OperationType')}"

            sample_map = get_external_map(source_model, sample_id)
            if sample_map:
                sample = GrowthSample.objects.get(pk=sample_map.target_object_id)
                sample.assignment = assignment
                sample.sample_date = sample_dt.date()
                sample.sample_size = sample_size
                sample.avg_weight_g = avg_weight_g
                sample.condition_factor = condition_factor
                sample.notes = notes
                save_with_history(sample, user=history_user, reason=history_reason)
                updated += 1
                continue

            sample = GrowthSample(
                assignment=assignment,
                sample_date=sample_dt.date(),
                sample_size=sample_size,
                avg_weight_g=avg_weight_g,
                condition_factor=condition_factor,
                notes=notes,
            )
            save_with_history(sample, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model=source_model,
                source_identifier=str(sample_id),
                defaults={
                    "target_app_label": sample._meta.app_label,
                    "target_model": sample._meta.model_name,
                    "target_object_id": sample.pk,
                    "metadata": {
                        "component_key": component_key,
                        "population_id": population_id,
                        "sample_date": row.get("SampleDate"),
                        "avg_weight": row.get("AvgWeight"),
                        "sample_size": row.get("NumberOfFish"),
                    },
                },
            )
            created += 1

    print(
        f"Migrated growth samples for component_key={component_key} "
        f"(created={created}, updated={updated}, skipped={skipped}, rows={len(rows)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
