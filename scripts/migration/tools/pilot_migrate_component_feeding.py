#!/usr/bin/env python3
"""Pilot migrate FishTalk feeding events for one stitched population component.

This script assumes the component has already been migrated into AquaMind via
`pilot_migrate_component.py`, which creates the Batch + BatchContainerAssignments
and the corresponding ExternalIdMap entries.

FishTalk schema note:
  - dbo.Feeding is keyed by ActionID.
  - dbo.Action links ActionID -> PopulationID (+ OperationID -> Operations.StartTime).

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

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

User = get_user_model()

from apps.batch.models.assignment import BatchContainerAssignment
from apps.inventory.models import Feed, FeedingEvent
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


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


def normalize_method(value: str) -> str:
    upper = (value or "").strip().upper()
    if upper in {"AUTOMATIC", "AUTO", "AUT", "HUON"}:
        return "AUTOMATIC"
    if upper in {"BROADCAST", "BROAD"}:
        return "BROADCAST"
    return "MANUAL"


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    population_name: str
    container_id: str
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
                    population_name=row.get("population_name", ""),
                    container_id=row.get("container_id", ""),
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate feeding events for a stitched FishTalk component")
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

    # Lazily import Batch to avoid cyclic imports in some Django setups.
    from apps.batch.models import Batch

    batch = Batch.objects.get(pk=batch_map.target_object_id)

    population_ids = sorted({m.population_id for m in members if m.population_id})
    if not population_ids:
        raise SystemExit("No population ids found in report")

    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    feeding_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), f.ActionID) AS ActionID, "
            "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
            "CONVERT(varchar(23), COALESCE(o.StartTime, f.OperationStartTime), 121) AS FeedingTime, "
            "CONVERT(varchar(32), f.FeedAmount) AS FeedAmountG, "
            "CONVERT(varchar(64), f.FeedBatchID) AS FeedBatchID, "
            "ISNULL(fb.BatchNumber, '') AS FeedBatchNumber, "
            "CONVERT(varchar(64), COALESCE(f.FeedTypeID, fb.FeedTypeID)) AS FeedTypeID, "
            "ISNULL(ft.Name, '') AS FeedTypeName, "
            "CONVERT(varchar(23), sb.StatusTime, 121) AS StatusTimeBefore, "
            "CONVERT(varchar(32), sb.CurrentBiomassKg) AS BiomassBeforeKg, "
            "CONVERT(varchar(32), sb.CurrentCount) AS PopulationCountBefore, "
            "CONVERT(varchar(23), sa.StatusTime, 121) AS StatusTimeAfter, "
            "CONVERT(varchar(32), sa.CurrentBiomassKg) AS BiomassAfterKg, "
            "CONVERT(varchar(32), sa.CurrentCount) AS PopulationCountAfter, "
            "ISNULL(CONVERT(varchar(64), f.ImportedFrom), '') AS ImportedFrom, "
            "REPLACE(REPLACE(REPLACE(ISNULL(o.Comment, ''), '|', '/'), CHAR(13), ' '), CHAR(10), ' ') AS OperationComment "
            "FROM dbo.Feeding f "
            "JOIN dbo.Action a ON a.ActionID = f.ActionID "
            "LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.FeedBatch fb ON fb.FeedBatchID = f.FeedBatchID "
            "LEFT JOIN dbo.FeedTypes ft ON ft.FeedTypeID = COALESCE(f.FeedTypeID, fb.FeedTypeID) "
            "OUTER APPLY ( "
            "  SELECT TOP 1 psv.StatusTime, psv.CurrentBiomassKg, psv.CurrentCount "
            "  FROM dbo.PublicStatusValues psv "
            "  WHERE psv.PopulationID = a.PopulationID "
            "    AND psv.StatusTime <= COALESCE(o.StartTime, f.OperationStartTime) "
            "  ORDER BY psv.StatusTime DESC "
            ") sb "
            "OUTER APPLY ( "
            "  SELECT TOP 1 psv.StatusTime, psv.CurrentBiomassKg, psv.CurrentCount "
            "  FROM dbo.PublicStatusValues psv "
            "  WHERE psv.PopulationID = a.PopulationID "
            "    AND psv.StatusTime >= COALESCE(o.StartTime, f.OperationStartTime) "
            "  ORDER BY psv.StatusTime ASC "
            ") sa "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND COALESCE(o.StartTime, f.OperationStartTime) >= '{start_str}' "
            f"AND COALESCE(o.StartTime, f.OperationStartTime) <= '{end_str}' "
            "ORDER BY COALESCE(o.StartTime, f.OperationStartTime) ASC"
        ),
        headers=[
            "ActionID",
            "PopulationID",
            "FeedingTime",
            "FeedAmountG",
            "FeedBatchID",
            "FeedBatchNumber",
            "FeedTypeID",
            "FeedTypeName",
            "StatusTimeBefore",
            "BiomassBeforeKg",
            "PopulationCountBefore",
            "StatusTimeAfter",
            "BiomassAfterKg",
            "PopulationCountAfter",
            "ImportedFrom",
            "OperationComment",
        ],
    )

    hw_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), hw.FeedingID) AS FeedingID, "
            "CONVERT(varchar(36), hw.FTActionID) AS ActionID, "
            "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
            "CONVERT(varchar(23), hw.StartTime, 121) AS FeedingTime, "
            "CONVERT(varchar(32), hw.FeedAmount) AS FeedAmountG, "
            "CONVERT(varchar(23), sb.StatusTime, 121) AS StatusTimeBefore, "
            "CONVERT(varchar(32), sb.CurrentBiomassKg) AS BiomassBeforeKg, "
            "CONVERT(varchar(32), sb.CurrentCount) AS PopulationCountBefore, "
            "CONVERT(varchar(23), sa.StatusTime, 121) AS StatusTimeAfter, "
            "CONVERT(varchar(32), sa.CurrentBiomassKg) AS BiomassAfterKg, "
            "CONVERT(varchar(32), sa.CurrentCount) AS PopulationCountAfter, "
            "CONVERT(varchar(36), hw.HWUnitID) AS HWUnitID, "
            "CONVERT(varchar(36), hw.HWSiloID) AS HWSiloID, "
            "ISNULL(hw.StopReason, '') AS StopReason "
            "FROM dbo.HWFeeding hw "
            "JOIN dbo.Action a ON a.ActionID = hw.FTActionID "
            "OUTER APPLY ( "
            "  SELECT TOP 1 psv.StatusTime, psv.CurrentBiomassKg, psv.CurrentCount "
            "  FROM dbo.PublicStatusValues psv "
            "  WHERE psv.PopulationID = a.PopulationID "
            "    AND psv.StatusTime <= hw.StartTime "
            "  ORDER BY psv.StatusTime DESC "
            ") sb "
            "OUTER APPLY ( "
            "  SELECT TOP 1 psv.StatusTime, psv.CurrentBiomassKg, psv.CurrentCount "
            "  FROM dbo.PublicStatusValues psv "
            "  WHERE psv.PopulationID = a.PopulationID "
            "    AND psv.StatusTime >= hw.StartTime "
            "  ORDER BY psv.StatusTime ASC "
            ") sa "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND hw.StartTime >= '{start_str}' AND hw.StartTime <= '{end_str}' "
            "ORDER BY hw.StartTime ASC"
        ),
        headers=[
            "FeedingID",
            "ActionID",
            "PopulationID",
            "FeedingTime",
            "FeedAmountG",
            "StatusTimeBefore",
            "BiomassBeforeKg",
            "PopulationCountBefore",
            "StatusTimeAfter",
            "BiomassAfterKg",
            "PopulationCountAfter",
            "HWUnitID",
            "HWSiloID",
            "StopReason",
        ],
    )

    # Tag the source model for idempotent mapping.
    events: list[tuple[str, dict[str, str]]] = [("Feeding", row) for row in feeding_rows] + [
        ("HWFeeding", row) for row in hw_rows
    ]
    events.sort(key=lambda item: item[1].get("FeedingTime") or "")

    if args.dry_run:
        print(
            f"[dry-run] Batch={batch.batch_number} Feeding(rows)={len(feeding_rows)} HWFeeding(rows)={len(hw_rows)}"
        )
        return 0

    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        history_reason = f"FishTalk migration: feeding for component {component_key}"
        for source_model, row in events:
            feeding_id = row.get("FeedingID") if source_model == "HWFeeding" else row.get("ActionID")
            population_id = row.get("PopulationID")
            if not feeding_id or not population_id:
                skipped += 1
                continue

            # Resolve assignment via the PopulationID mapping (avoids same-day date ambiguity).
            assignment_map = get_external_map("Populations", population_id)
            if not assignment_map:
                skipped += 1
                continue
            assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)
            if assignment.batch_id != batch.id:
                skipped += 1
                continue

            dt = parse_dt(row.get("FeedingTime", ""))
            if dt is None:
                skipped += 1
                continue

            amount_g = to_decimal(row.get("FeedAmountG", ""), places="0.0001")
            if amount_g is None or amount_g <= 0:
                skipped += 1
                continue

            # FishTalk Feeding/HWFeeding amounts are stored in grams.
            amount_kg = (amount_g / Decimal("1000")).quantize(Decimal("0.0001"))
            if amount_kg <= 0:
                skipped += 1
                continue

            biomass_before = to_decimal(row.get("BiomassBeforeKg", ""), places="0.01")
            biomass_after = to_decimal(row.get("BiomassAfterKg", ""), places="0.01")

            biomass: Decimal | None = None
            if biomass_before is not None and biomass_before > 0:
                biomass = biomass_before
            elif biomass_after is not None and biomass_after > 0:
                biomass = biomass_after
            elif assignment.biomass_kg and assignment.biomass_kg > 0:
                biomass = assignment.biomass_kg

            # If we can't find a sane biomass, skip rather than overflowing feeding_percentage.
            if biomass is None or biomass <= 0:
                skipped += 1
                continue

            feed_type_id = (row.get("FeedTypeID") or "").strip()
            feed_type_name = (row.get("FeedTypeName") or "").strip()
            feed_batch_id = (row.get("FeedBatchID") or "").strip()
            feed_batch_number = (row.get("FeedBatchNumber") or "").strip()

            feed_key = feed_batch_number or feed_batch_id or feed_type_name or feed_type_id or "UNKNOWN"
            feed_display = feed_type_name or (f"FishTalk FeedType {feed_type_id}" if feed_type_id else "FishTalk Feed")
            if feed_batch_number:
                feed_display = f"{feed_display} ({feed_batch_number})"

            feed, _ = Feed.objects.get_or_create(
                name=f"FT-{feed_display}"[:100],
                brand="FishTalk Import",
                defaults={
                    "size_category": "MEDIUM",
                    "protein_percentage": Decimal("45.0"),
                    "fat_percentage": Decimal("20.0"),
                    "carbohydrate_percentage": Decimal("15.0"),
                    "description": "Auto-created for FishTalk migration",
                    "is_active": True,
                },
            )

            imported_from = (row.get("ImportedFrom") or "").strip()
            method = "AUTOMATIC" if (source_model == "HWFeeding" or (imported_from and imported_from != "0")) else "MANUAL"
            method = normalize_method(method)

            status_before = (row.get("StatusTimeBefore") or "").strip()
            status_after = (row.get("StatusTimeAfter") or "").strip()
            op_comment = (row.get("OperationComment") or "").strip()
            stop_reason = (row.get("StopReason") or "").strip()
            notes = f"FishTalk {source_model} id={feeding_id}; PopulationID={population_id}; Feed={feed_key}."
            if status_before or status_after:
                notes = f"{notes} StatusBefore={status_before or 'n/a'}; StatusAfter={status_after or 'n/a'}."
            if op_comment:
                notes = f"{notes} OperationComment: {op_comment}"
            if stop_reason:
                notes = f"{notes} StopReason: {stop_reason}"

            event_map = get_external_map(source_model, feeding_id)
            if event_map:
                event = FeedingEvent.objects.get(pk=event_map.target_object_id)
                event.batch = batch
                event.batch_assignment = assignment
                event.container = assignment.container
                event.feed = feed
                event.feeding_date = dt.date()
                event.feeding_time = dt.time()
                event.amount_kg = amount_kg
                event.batch_biomass_kg = biomass
                event.method = method
                event.notes = notes
                save_with_history(event, user=history_user, reason=history_reason)
                updated += 1
                continue

            event = FeedingEvent(
                batch=batch,
                batch_assignment=assignment,
                container=assignment.container,
                feed=feed,
                feeding_date=dt.date(),
                feeding_time=dt.time(),
                amount_kg=amount_kg,
                batch_biomass_kg=biomass,
                feed_cost=Decimal("0.00"),
                method=method,
                notes=notes,
            )
            save_with_history(event, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model=source_model,
                source_identifier=str(feeding_id),
                defaults={
                    "target_app_label": event._meta.app_label,
                    "target_model": event._meta.model_name,
                    "target_object_id": event.pk,
                    "metadata": {
                        "component_key": component_key,
                        "population_id": population_id,
                        "action_id": row.get("ActionID"),
                        "feed_batch_id": feed_batch_id,
                        "feed_batch_number": feed_batch_number,
                        "feed_type_id": feed_type_id,
                        "feed_type_name": feed_type_name,
                        "feeding_time": row.get("FeedingTime"),
                        "amount_g": str(amount_g),
                        "amount_kg": str(amount_kg),
                        "biomass_kg": str(biomass),
                        "method": method,
                    },
                },
            )
            created += 1

    print(
        f"Migrated feeding events for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, source_rows={len(events)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
