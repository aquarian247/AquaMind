#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk harvest results for one stitched population component.

Source (FishTalk): dbo.HarvestResult keyed by ActionID.
  - HarvestResult.ActionID -> Action.PopulationID (+ OperationID -> Operations.StartTime)
  - HarvestResult.QualityID / ConditionID -> ProductGrade (lookup)

Target (AquaMind): apps.harvest.models.HarvestEvent + HarvestLot
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
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
from apps.harvest.models import HarvestEvent, HarvestLot, ProductGrade
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
        "%Y-%m-%d",
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
    return timezone.make_aware(dt, dt_timezone.utc)


def to_decimal(value: object, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


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


def build_grade(quality_id: str, quality_name: str, condition_id: str, condition_name: str) -> tuple[str, str, str]:
    quality_id = (quality_id or "").strip()
    quality_name = (quality_name or "").strip()
    condition_id = (condition_id or "").strip()
    condition_name = (condition_name or "").strip()

    code_parts = []
    if quality_id:
        code_parts.append(f"Q{quality_id}")
    elif quality_name:
        code_parts.append(quality_name)
    if condition_id:
        code_parts.append(f"C{condition_id}")
    code = "FT-" + "-".join(code_parts) if code_parts else "FT-UNKNOWN"
    code = code[:50]

    name_parts = []
    if quality_name:
        name_parts.append(quality_name)
    if condition_name:
        name_parts.append(condition_name)
    name = " / ".join(name_parts) if name_parts else code

    desc = "FishTalk Harvest grade"
    if quality_name or quality_id:
        desc += f"; Quality={quality_name or quality_id}"
    if condition_name or condition_id:
        desc += f"; Condition={condition_name or condition_id}"
    return code, name[:100], desc[:2000]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate harvest results for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
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

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    if args.use_csv:
        loader = ETLDataLoader(args.use_csv)
        rows = loader.get_harvest_results_for_populations(
            set(population_ids),
            start_time=window_start,
            end_time=window_end,
        )
        extractor = None
    else:
        extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        query = (
            "SELECT "
            "CONVERT(varchar(36), h.ActionID) AS ActionID, "
            "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
            "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
            "CONVERT(varchar(32), h.Count) AS Count, "
            "CONVERT(varchar(64), h.GrossBiomass) AS GrossBiomass, "
            "CONVERT(varchar(64), h.NetBiomass) AS NetBiomass, "
            "CONVERT(varchar(32), h.QualityID) AS QualityID, "
            "ISNULL(hq.Name, '') AS QualityName, "
            "CONVERT(varchar(32), h.ConditionID) AS ConditionID, "
            "ISNULL(hc.DefaultText, '') AS ConditionName, "
            "CONVERT(varchar(64), h.FromWeight) AS FromWeight, "
            "CONVERT(varchar(64), h.ToWeight) AS ToWeight, "
            "CONVERT(varchar(64), h.IncomeTotal) AS IncomeTotal, "
            "ISNULL(h.BatchID, '') AS BatchID, "
            "CONVERT(varchar(19), h.PackingDate, 120) AS PackingDate, "
            "ISNULL(h.DocumentID, '') AS DocumentID, "
            "ISNULL(h.Comment, '') AS Comment "
            "FROM dbo.HarvestResult h "
            "JOIN dbo.Action a ON a.ActionID = h.ActionID "
            "JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.Ext_HarvestQuality_v2 hq ON hq.HarvestQualityID = h.QualityID "
            "LEFT JOIN dbo.HarvestCondition hc ON hc.HarvestConditionID = h.ConditionID "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND o.StartTime >= '{window_start.strftime('%Y-%m-%d %H:%M:%S')}' "
            f"AND o.StartTime <= '{window_end.strftime('%Y-%m-%d %H:%M:%S')}' "
            "ORDER BY o.StartTime ASC"
        )
        rows = extractor._run_sqlcmd(
            query=query,
            headers=[
                "ActionID",
                "PopulationID",
                "OperationStartTime",
                "Count",
                "GrossBiomass",
                "NetBiomass",
                "QualityID",
                "QualityName",
                "ConditionID",
                "ConditionName",
                "FromWeight",
                "ToWeight",
                "IncomeTotal",
                "BatchID",
                "PackingDate",
                "DocumentID",
                "Comment",
            ],
        )

    if args.dry_run:
        print(f"[dry-run] Would migrate {len(rows)} FishTalk harvest rows into batch={batch.batch_number}")
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)

    rows_by_action: dict[str, list[dict]] = {}
    for row in rows:
        action_id = (row.get("ActionID") or "").strip()
        if not action_id:
            continue
        rows_by_action.setdefault(action_id, []).append(row)

    created_events = updated_events = 0
    created_lots = updated_lots = skipped = 0
    with transaction.atomic():
        history_reason = f"FishTalk migration: harvest for component {component_key}"
        for action_id, action_rows in rows_by_action.items():
            # sort for stable indexing
            action_rows.sort(
                key=lambda r: (
                    (r.get("QualityID") or ""),
                    (r.get("ConditionID") or ""),
                    (r.get("FromWeight") or ""),
                    (r.get("ToWeight") or ""),
                    (r.get("Count") or ""),
                )
            )
            population_id = (action_rows[0].get("PopulationID") or "").strip()
            if not population_id:
                skipped += len(action_rows)
                continue

            assignment = assignment_by_pop.get(population_id)
            if not assignment or assignment.batch_id != batch.id:
                skipped += len(action_rows)
                continue

            when = parse_dt(action_rows[0].get("PackingDate") or "") or parse_dt(
                action_rows[0].get("OperationStartTime") or ""
            )
            if when is None:
                skipped += len(action_rows)
                continue
            when = ensure_aware(when)

            document_id = (action_rows[0].get("DocumentID") or "").strip()

            event_defaults = {
                "batch": batch,
                "assignment": assignment,
                "event_date": when,
                "document_ref": document_id[:100],
            }

            mapped_event = get_external_map("HarvestAction", action_id)
            if mapped_event:
                event = HarvestEvent.objects.get(pk=mapped_event.target_object_id)
                for k, v in event_defaults.items():
                    setattr(event, k, v)
                save_with_history(event, user=None, reason=history_reason)
                updated_events += 1
            else:
                event = HarvestEvent(**event_defaults)
                save_with_history(event, user=None, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="HarvestAction",
                    source_identifier=str(action_id),
                    defaults={
                        "target_app_label": event._meta.app_label,
                        "target_model": event._meta.model_name,
                        "target_object_id": event.pk,
                        "metadata": {
                            "population_id": population_id,
                            "document_id": document_id,
                        },
                    },
                )
                created_events += 1

            for idx, row in enumerate(action_rows, start=1):
                count_raw = (row.get("Count") or "").strip()
                try:
                    count = int(round(float(count_raw)))
                except Exception:
                    count = 0
                if count <= 0:
                    skipped += 1
                    continue

                live_weight = to_decimal(row.get("GrossBiomass"), places="0.001") or Decimal("0.000")
                gutted_weight = to_decimal(row.get("NetBiomass"), places="0.001")

                quality_id = row.get("QualityID") or ""
                quality_name = row.get("QualityName") or ""
                condition_id = row.get("ConditionID") or ""
                condition_name = row.get("ConditionName") or ""
                code, name, desc = build_grade(quality_id, quality_name, condition_id, condition_name)

                grade, _ = ProductGrade.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "description": desc,
                    },
                )

                source_identifier = f"{action_id}:{idx}"
                lot_defaults = {
                    "event": event,
                    "product_grade": grade,
                    "live_weight_kg": live_weight,
                    "gutted_weight_kg": gutted_weight if gutted_weight and gutted_weight > 0 else None,
                    "unit_count": count,
                }

                mapped_lot = get_external_map("HarvestResult", source_identifier)
                if mapped_lot:
                    lot = HarvestLot.objects.get(pk=mapped_lot.target_object_id)
                    for k, v in lot_defaults.items():
                        setattr(lot, k, v)
                    save_with_history(lot, user=None, reason=history_reason)
                    updated_lots += 1
                else:
                    lot = HarvestLot(**lot_defaults)
                    save_with_history(lot, user=None, reason=history_reason)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="HarvestResult",
                        source_identifier=source_identifier,
                        defaults={
                            "target_app_label": lot._meta.app_label,
                            "target_model": lot._meta.model_name,
                            "target_object_id": lot.pk,
                            "metadata": {
                                "action_id": action_id,
                                "population_id": population_id,
                                "quality_id": quality_id,
                                "condition_id": condition_id,
                            },
                        },
                    )
                    created_lots += 1

    print(
        f"Migrated harvest for component_key={component_key} into batch={batch.batch_number} "
        f"(events created={created_events}, updated={updated_events}; "
        f"lots created={created_lots}, updated={updated_lots}, skipped={skipped})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
