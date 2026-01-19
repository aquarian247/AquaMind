#!/usr/bin/env python3
"""Pilot migrate FishTalk health *journal entries* for one stitched population component.

Source (FishTalk):
  - UserSample rows are keyed by ActionID (sampling session) and contain per-fish rows.
  - UserSampleTypes (ActionID -> UserSampleTypeID) + UserSampleType(DefaultText) provide sample type names.
  - UserSampleParameterValue holds per-fish attribute values keyed by (ActionID, MeasID, AttributeID).

Target (AquaMind):
  - apps.health.models.JournalEntry (narrative / log entry)

This script creates **one JournalEntry per FishTalk sampling ActionID**, summarising:
  - sample types
  - sample size
  - basic weight stats (when available)
  - aggregated attribute scores (avg/min/max) when available

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
from django.utils import timezone
from scripts.migration.history import save_with_history

from apps.batch.models.assignment import BatchContainerAssignment
from apps.health.models import JournalEntry
from apps.migration_support.models import ExternalIdMap
from django.contrib.auth import get_user_model
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


def to_int(value: str) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None


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
    parser = argparse.ArgumentParser(description="Pilot migrate FishTalk health journal entries for a stitched component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    return parser


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.get_current_timezone())


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

    from apps.batch.models import Batch

    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot create JournalEntry.user")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    if not population_ids:
        raise SystemExit("No population ids found in report")

    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    # 1) Sampling sessions (one per ActionID)
    sessions = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), us.ActionID) AS ActionID, "
            "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
            "CONVERT(varchar(23), COALESCE(o.StartTime, o.RegistrationTime), 121) AS SampleTime, "
            "CONVERT(varchar(32), COUNT(*)) AS SampleRows, "
            "CONVERT(varchar(32), SUM(CASE WHEN us.Returned = 1 THEN 1 ELSE 0 END)) AS ReturnedRows, "
            "CONVERT(varchar(32), AVG(CAST(us.LivingWeight AS float))) AS AvgWeightG, "
            "CONVERT(varchar(32), MIN(us.LivingWeight)) AS MinWeightG, "
            "CONVERT(varchar(32), MAX(us.LivingWeight)) AS MaxWeightG "
            "FROM dbo.UserSample us "
            "JOIN dbo.Action a ON a.ActionID = us.ActionID "
            "LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) >= '{start_str}' "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) <= '{end_str}' "
            "GROUP BY us.ActionID, a.PopulationID, COALESCE(o.StartTime, o.RegistrationTime) "
            "ORDER BY COALESCE(o.StartTime, o.RegistrationTime) ASC"
        ),
        headers=[
            "ActionID",
            "PopulationID",
            "SampleTime",
            "SampleRows",
            "ReturnedRows",
            "AvgWeightG",
            "MinWeightG",
            "MaxWeightG",
        ],
    )

    # 2) Sample types (many per ActionID)
    sample_types_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), ust.ActionID) AS ActionID, "
            "CONVERT(varchar(32), ust.SampleType) AS UserSampleTypeID, "
            "ISNULL(st.DefaultText, '') AS SampleTypeName "
            "FROM dbo.UserSampleTypes ust "
            "JOIN dbo.Action a ON a.ActionID = ust.ActionID "
            "LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.UserSampleType st ON st.UserSampleTypeID = ust.SampleType "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) >= '{start_str}' "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) <= '{end_str}' "
            "ORDER BY ust.ActionID, ust.SampleType"
        ),
        headers=["ActionID", "UserSampleTypeID", "SampleTypeName"],
    )

    types_by_action: dict[str, list[str]] = {}
    for row in sample_types_rows:
        aid = (row.get("ActionID") or "").strip()
        name = (row.get("SampleTypeName") or "").strip() or f"UserSampleTypeID={row.get('UserSampleTypeID')}"
        if not aid:
            continue
        types_by_action.setdefault(aid, [])
        if name not in types_by_action[aid]:
            types_by_action[aid].append(name)

    # 3) Attribute aggregates (scores etc)
    attr_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), uspv.ActionID) AS ActionID, "
            "CONVERT(varchar(32), uspv.AttributeID) AS AttributeID, "
            "ISNULL(fga.Name, '') AS AttributeName, "
            "'INT' AS ValueType, "
            "CONVERT(varchar(32), AVG(CAST(uspv.IntValue AS float))) AS AvgValue, "
            "CONVERT(varchar(32), MIN(uspv.IntValue)) AS MinValue, "
            "CONVERT(varchar(32), MAX(uspv.IntValue)) AS MaxValue, "
            "CONVERT(varchar(32), COUNT(*)) AS N "
            "FROM dbo.UserSampleParameterValue uspv "
            "JOIN dbo.Action a ON a.ActionID = uspv.ActionID "
            "LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.FishGroupAttributes fga ON fga.AttributeID = uspv.AttributeID "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) >= '{start_str}' "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) <= '{end_str}' "
            "AND uspv.IntValue IS NOT NULL "
            "GROUP BY uspv.ActionID, uspv.AttributeID, fga.Name "
            "UNION ALL "
            "SELECT CONVERT(varchar(36), uspv.ActionID) AS ActionID, "
            "CONVERT(varchar(32), uspv.AttributeID) AS AttributeID, "
            "ISNULL(fga.Name, '') AS AttributeName, "
            "'FLOAT' AS ValueType, "
            "CONVERT(varchar(32), AVG(CAST(uspv.FloatValue AS float))) AS AvgValue, "
            "CONVERT(varchar(32), MIN(uspv.FloatValue)) AS MinValue, "
            "CONVERT(varchar(32), MAX(uspv.FloatValue)) AS MaxValue, "
            "CONVERT(varchar(32), COUNT(*)) AS N "
            "FROM dbo.UserSampleParameterValue uspv "
            "JOIN dbo.Action a ON a.ActionID = uspv.ActionID "
            "LEFT JOIN dbo.Operations o ON o.OperationID = a.OperationID "
            "LEFT JOIN dbo.FishGroupAttributes fga ON fga.AttributeID = uspv.AttributeID "
            f"WHERE a.PopulationID IN ({in_clause}) "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) >= '{start_str}' "
            f"AND COALESCE(o.StartTime, o.RegistrationTime) <= '{end_str}' "
            "AND uspv.FloatValue IS NOT NULL "
            "GROUP BY uspv.ActionID, uspv.AttributeID, fga.Name "
            "ORDER BY ActionID, AttributeID, ValueType"
        ),
        headers=[
            "ActionID",
            "AttributeID",
            "AttributeName",
            "ValueType",
            "AvgValue",
            "MinValue",
            "MaxValue",
            "N",
        ],
    )

    attrs_by_action: dict[str, list[dict[str, str]]] = {}
    for row in attr_rows:
        aid = (row.get("ActionID") or "").strip()
        if not aid:
            continue
        attrs_by_action.setdefault(aid, []).append(row)

    if args.dry_run:
        print(
            f"[dry-run] Batch={batch.batch_number} sample_actions={len(sessions)} "
            f"sample_types_rows={len(sample_types_rows)} attr_rows={len(attr_rows)}"
        )
        return 0

    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        history_reason = f"FishTalk migration: health journal for component {component_key}"
        for session in sessions:
            action_id = (session.get("ActionID") or "").strip()
            population_id = (session.get("PopulationID") or "").strip()
            sample_time = parse_dt(session.get("SampleTime") or "")
            if not action_id or not population_id or sample_time is None:
                skipped += 1
                continue

            assignment_map = get_external_map("Populations", population_id)
            if not assignment_map:
                skipped += 1
                continue
            assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)
            if assignment.batch_id != batch.id:
                skipped += 1
                continue

            sample_rows = to_int(session.get("SampleRows")) or 0
            returned_rows = to_int(session.get("ReturnedRows")) or 0
            avg_w = to_decimal(session.get("AvgWeightG"), places="0.01")
            min_w = to_decimal(session.get("MinWeightG"), places="0.01")
            max_w = to_decimal(session.get("MaxWeightG"), places="0.01")

            type_names = types_by_action.get(action_id, [])
            types_label = ", ".join(type_names) if type_names else "(no type)"

            # Build a compact attribute summary (top N by name).
            attr_summaries: list[str] = []
            for row in sorted(attrs_by_action.get(action_id, []), key=lambda r: (r.get("AttributeName") or "", r.get("ValueType") or "")):
                name = (row.get("AttributeName") or "").strip() or f"Attr {row.get('AttributeID')}"
                avg_val = to_decimal(row.get("AvgValue"), places="0.01")
                if avg_val is None:
                    continue
                value_type = (row.get("ValueType") or "").strip() or "VAL"
                attr_summaries.append(f"{name}({value_type}) avg={avg_val}")

            attr_summaries = attr_summaries[:12]
            attrs_label = "; ".join(attr_summaries)

            description = f"FishTalk health sample: {types_label}."
            detail = f"FishTalk UserSample ActionID={action_id}; PopulationID={population_id}; n={sample_rows}; returned={returned_rows}."
            if avg_w is not None:
                detail = f"{detail} weight_g avg={avg_w}"
                if min_w is not None and max_w is not None:
                    detail = f"{detail} (min={min_w}, max={max_w})"
                detail = f"{detail}."
            if attrs_label:
                detail = f"{detail} Attributes: {attrs_label}."

            entry_dt = ensure_aware(sample_time)

            entry_map = get_external_map("UserSampleAction", action_id)
            if entry_map:
                entry = JournalEntry.objects.get(pk=entry_map.target_object_id)
                entry.batch = batch
                entry.container = assignment.container
                entry.user = user
                entry.entry_date = entry_dt
                entry.category = "sample"
                entry.severity = "low"
                entry.description = description
                entry.resolution_status = True
                entry.resolution_notes = detail
                save_with_history(entry, user=user, reason=history_reason)
                updated += 1
                continue

            entry = JournalEntry(
                batch=batch,
                container=assignment.container,
                user=user,
                entry_date=entry_dt,
                category="sample",
                severity="low",
                description=description,
                resolution_status=True,
                resolution_notes=detail,
            )
            save_with_history(entry, user=user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="UserSampleAction",
                source_identifier=str(action_id),
                defaults={
                    "target_app_label": entry._meta.app_label,
                    "target_model": entry._meta.model_name,
                    "target_object_id": entry.pk,
                    "metadata": {
                        "component_key": component_key,
                        "population_id": population_id,
                        "sample_time": session.get("SampleTime"),
                        "sample_types": type_names,
                        "sample_rows": sample_rows,
                        "returned_rows": returned_rows,
                        "avg_weight_g": str(avg_w) if avg_w is not None else None,
                        "min_weight_g": str(min_w) if min_w is not None else None,
                        "max_weight_g": str(max_w) if max_w is not None else None,
                        "attribute_summaries": attr_summaries,
                    },
                },
            )
            created += 1

    print(
        f"Migrated health journal entries for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, sample_actions={len(sessions)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
