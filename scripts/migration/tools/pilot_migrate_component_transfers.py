#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk transfers (movements) for one stitched population component.

Source (FishTalk): dbo.PublicTransfers keyed by (OperationID, SourcePop, DestPop).
  - PublicTransfers.OperationID -> Operations.StartTime (transfer timestamp)
  - PublicTransfers.ShareCountForward / ShareBiomassForward are used to estimate counts/biomass moved.

Target (AquaMind):
  - apps.batch.models.BatchTransferWorkflow (1 per FishTalk OperationID)
  - apps.batch.models.TransferAction (1 per FishTalk edge SourcePop->DestPop)

Important:
  - This is a *best-effort* backfill: FishTalk transfers can represent splits/merges;
    AquaMind TransferAction requires absolute transferred_count and biomass.
    We estimate using the source population snapshot near the operation time.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from bisect import bisect_right
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
from django.db.models import Max
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch, BatchTransferWorkflow, TransferAction, LifeCycleStage
from apps.batch.models.assignment import BatchContainerAssignment
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


def stage_at(events: list[tuple[datetime, str]], when: datetime) -> str:
    if not events:
        return ""
    if timezone.is_aware(when):
        when = timezone.make_naive(when)
    idx = bisect_right(events, (when, "\uffff")) - 1
    if idx < 0:
        return ""
    return events[idx][1]


def stage_slug(stage_name: str) -> str:
    return "".join(ch for ch in stage_name.upper() if ch.isalnum())[:4]


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC FRY", "GREEN EGG", "EYE-EGG")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE")):
        return "Adult"
    if "BROODSTOCK" in upper:
        return "Adult"
    return None


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


def lookup_status_snapshot(extractor: BaseExtractor, *, population_id: str, at_time: datetime) -> tuple[int, Decimal]:
    ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
            "FROM dbo.PublicStatusValues "
            f"WHERE PopulationID = '{population_id}' AND StatusTime <= '{ts}' "
            "ORDER BY StatusTime DESC"
        ),
        headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
    )
    if not rows:
        rows = extractor._run_sqlcmd(
            query=(
                "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                "FROM dbo.PublicStatusValues "
                f"WHERE PopulationID = '{population_id}' AND StatusTime >= '{ts}' "
                "ORDER BY StatusTime ASC"
            ),
            headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
        )

    count = 0
    biomass = Decimal("0.00")
    if rows:
        try:
            count = int(round(float(rows[0].get("CurrentCount") or 0)))
        except Exception:
            count = 0
        biomass = to_decimal(rows[0].get("CurrentBiomassKg"), places="0.01") or Decimal("0.00")

    return max(count, 0), biomass


def lookup_project_info(extractor: BaseExtractor, *, population_id: str) -> tuple[str | None, str | None, str | None]:
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT ProjectNumber, InputYear, RunningNumber "
            "FROM dbo.Populations "
            f"WHERE PopulationID = '{population_id}'"
        ),
        headers=["ProjectNumber", "InputYear", "RunningNumber"],
    )
    if not rows:
        return None, None, None
    row = rows[0]
    project_number = (row.get("ProjectNumber") or "").strip() or None
    input_year = (row.get("InputYear") or "").strip() or None
    running_number = (row.get("RunningNumber") or "").strip() or None
    return project_number, input_year, running_number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate transfer workflows/actions for a stitched FishTalk component")
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
        raise SystemExit("No users exist in AquaMind DB; cannot create transfer workflows")

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    project_number, input_year, running_number = lookup_project_info(
        extractor, population_id=component_key
    )

    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    transfer_rows = extractor._run_sqlcmd(
        query=(
            "SELECT pt.OperationID, "
            "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
            "CONVERT(varchar(36), pt.SourcePop) AS SourcePop, "
            "CONVERT(varchar(36), pt.DestPop) AS DestPop, "
            "CONVERT(varchar(64), pt.ShareCountForward) AS ShareCountForward, "
            "CONVERT(varchar(64), pt.ShareBiomassForward) AS ShareBiomassForward "
            "FROM dbo.PublicTransfers pt "
            "JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"WHERE (pt.SourcePop IN ({in_clause}) OR pt.DestPop IN ({in_clause})) "
            f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
            "ORDER BY o.StartTime ASC"
        ),
        headers=[
            "OperationID",
            "OperationStartTime",
            "SourcePop",
            "DestPop",
            "ShareCountForward",
            "ShareBiomassForward",
        ],
    )

    stages_raw = extractor._run_sqlcmd(
        query="SELECT StageID, StageName FROM dbo.ProductionStages",
        headers=["StageID", "StageName"],
    )
    stage_name_by_id = {row["StageID"]: (row.get("StageName", "") or "").strip() for row in stages_raw}

    stage_events_raw = extractor._run_sqlcmd(
        query=(
            "SELECT pps.PopulationID, pps.StageID, pps.StartTime "
            "FROM dbo.PopulationProductionStages pps "
            + (
                "JOIN dbo.Populations p ON p.PopulationID = pps.PopulationID "
                f"WHERE p.ProjectNumber = '{project_number}' "
                f"AND p.InputYear = '{input_year}' "
                f"AND p.RunningNumber = '{running_number}'"
                if project_number and input_year and running_number
                else f"WHERE pps.PopulationID IN ({in_clause})"
            )
        ),
        headers=["PopulationID", "StageID", "StartTime"],
    )

    stage_events: dict[str, list[tuple[datetime, str]]] = {}
    for row in stage_events_raw:
        ts = parse_dt(row.get("StartTime", ""))
        if ts is None:
            continue
        stage_name = stage_name_by_id.get(row.get("StageID", ""), "")
        stage_events.setdefault(row["PopulationID"], []).append((ts, stage_name))
    for pop_id, events in stage_events.items():
        events.sort(key=lambda item: item[0])

    stage_events_all: list[dict[str, object]] = []
    for pop_id, events in stage_events.items():
        for ts, stage_name in events:
            mapped_name = fishtalk_stage_to_aquamind(stage_name)
            if not mapped_name:
                continue
            stage_events_all.append(
                {
                    "population_id": pop_id,
                    "stage": mapped_name,
                    "transition_time": ts,
                }
            )

    stage_events_all.sort(
        key=lambda item: (
            item["transition_time"],
            item["stage"],
            item["population_id"],
        )
    )

    collapsed_events: list[dict[str, object]] = []
    for event in stage_events_all:
        if not collapsed_events or event["stage"] != collapsed_events[-1]["stage"]:
            collapsed_events.append(event)

    stage_transitions: list[dict[str, object]] = []
    for idx in range(1, len(collapsed_events)):
        prev = collapsed_events[idx - 1]
        curr = collapsed_events[idx]
        stage_transitions.append(
            {
                "population_id": curr["population_id"],
                "from_stage": prev["stage"],
                "to_stage": curr["stage"],
                "transition_time": curr["transition_time"],
            }
        )

    # Keep only internal edges (both endpoints in component) to avoid linking outside batches.
    transfer_rows = [
        row
        for row in transfer_rows
        if (row.get("SourcePop") in population_ids and row.get("DestPop") in population_ids)
    ]

    if args.dry_run:
        print(f"[dry-run] Would migrate {len(transfer_rows)} PublicTransfers edges into batch={batch.batch_number}")
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)

    # Group edges by operation.
    by_op: dict[str, list[dict[str, str]]] = {}
    for row in transfer_rows:
        op_id = (row.get("OperationID") or "").strip()
        if not op_id:
            continue
        by_op.setdefault(op_id, []).append(row)

    created_wf = updated_wf = created_actions = updated_actions = skipped = 0
    created_stage_wf = updated_stage_wf = created_stage_actions = updated_stage_actions = skipped_stage = 0

    with transaction.atomic():
        history_user = user
        history_reason = f"FishTalk migration: transfers for component {component_key}"
        for op_id, edges in by_op.items():
            op_time = parse_dt(edges[0].get("OperationStartTime") or "")
            if op_time is None:
                skipped += len(edges)
                continue
            op_time = ensure_aware(op_time)
            op_date = op_time.date()

            # Pick lifecycle stage context from the first source/dest assignment.
            source_stage = None
            dest_stage = None
            source_stage_name = None
            dest_stage_name = None
            for edge in edges:
                src = (edge.get("SourcePop") or "").strip()
                dst = (edge.get("DestPop") or "").strip()
                if not source_stage and src in assignment_by_pop:
                    source_stage = assignment_by_pop[src].lifecycle_stage
                if not dest_stage and dst in assignment_by_pop:
                    dest_stage = assignment_by_pop[dst].lifecycle_stage
                if not source_stage_name and src in stage_events:
                    source_stage_name = stage_at(stage_events.get(src, []), op_time)
                if not dest_stage_name and dst in stage_events:
                    dest_stage_name = stage_at(stage_events.get(dst, []), op_time)
            source_stage = source_stage or LifeCycleStage.objects.first()
            if source_stage is None:
                raise SystemExit("Missing LifeCycleStage master data")

            if source_stage_name:
                mapped_name = fishtalk_stage_to_aquamind(source_stage_name)
                if mapped_name:
                    source_stage = LifeCycleStage.objects.filter(name=mapped_name).first() or source_stage
            if dest_stage_name:
                mapped_name = fishtalk_stage_to_aquamind(dest_stage_name)
                if mapped_name:
                    dest_stage = LifeCycleStage.objects.filter(name=mapped_name).first() or dest_stage

            workflow_type = "CONTAINER_REDISTRIBUTION"
            if dest_stage and source_stage and getattr(dest_stage, "id", None) != getattr(source_stage, "id", None):
                workflow_type = "LIFECYCLE_TRANSITION"

            wf_map = get_external_map("TransferOperation", op_id)
            if wf_map:
                workflow = BatchTransferWorkflow.objects.get(pk=wf_map.target_object_id)
                # Don't overwrite user-entered notes; just keep FishTalk reference.
                workflow.planned_start_date = op_date
                workflow.source_lifecycle_stage = source_stage
                workflow.dest_lifecycle_stage = dest_stage
                workflow.workflow_type = workflow_type
                save_with_history(workflow, user=history_user, reason=history_reason)
                updated_wf += 1
            else:
                wf_number = f"FT-TRF-{op_date.strftime('%Y%m%d')}-{op_id[:8]}"[:50]
                workflow = BatchTransferWorkflow(
                    workflow_number=wf_number,
                    batch=batch,
                    workflow_type=workflow_type,
                    source_lifecycle_stage=source_stage,
                    dest_lifecycle_stage=dest_stage,
                    status="DRAFT",
                    planned_start_date=op_date,
                    planned_completion_date=op_date,
                    initiated_by=user,
                    notes=f"FishTalk OperationID={op_id}",
                )
                save_with_history(workflow, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="TransferOperation",
                    source_identifier=str(op_id),
                    defaults={
                        "target_app_label": workflow._meta.app_label,
                        "target_model": workflow._meta.model_name,
                        "target_object_id": workflow.pk,
                        "metadata": {"operation_start_time": edges[0].get("OperationStartTime")},
                    },
                )
                created_wf += 1

            # Build per-source snapshot so multiple edges from same source are sequentially allocated.
            edges_sorted = sorted(
                edges,
                key=lambda e: (
                    (e.get("SourcePop") or ""),
                    # Desc by max share to allocate larger first
                    -(float(e.get("ShareBiomassForward") or 0) if str(e.get("ShareBiomassForward") or "").strip() else 0.0),
                    (e.get("DestPop") or ""),
                ),
            )

            source_remaining: dict[str, tuple[int, Decimal]] = {}

            max_action_number = (
                workflow.actions.aggregate(max_action_number=Max("action_number"))[
                    "max_action_number"
                ]
                or 0
            )

            for idx, edge in enumerate(edges_sorted, start=max_action_number + 1):
                src = (edge.get("SourcePop") or "").strip()
                dst = (edge.get("DestPop") or "").strip()
                if not src or not dst:
                    skipped += 1
                    continue
                if src not in assignment_by_pop or dst not in assignment_by_pop:
                    skipped += 1
                    continue

                if src not in source_remaining:
                    source_remaining[src] = lookup_status_snapshot(extractor, population_id=src, at_time=op_time)

                src_count_before, src_biomass_before = source_remaining[src]

                share_count = float(edge.get("ShareCountForward") or 0) if str(edge.get("ShareCountForward") or "").strip() else 0.0
                share_biom = float(edge.get("ShareBiomassForward") or 0) if str(edge.get("ShareBiomassForward") or "").strip() else 0.0
                share_count = max(0.0, min(1.0, share_count))
                share_biom = max(0.0, min(1.0, share_biom))

                est_count = int(round(src_count_before * (share_count or share_biom))) if src_count_before > 0 else 0
                if est_count <= 0 and (share_count > 0 or share_biom > 0) and src_count_before > 0:
                    est_count = 1
                est_count = min(est_count, src_count_before) if src_count_before > 0 else est_count

                est_biomass = (src_biomass_before * Decimal(str(share_biom or share_count))).quantize(Decimal("0.01")) if src_biomass_before > 0 else Decimal("0.00")

                # Sequentially reduce remaining for this source to avoid double-counting.
                new_src_count = max(0, src_count_before - est_count)
                new_src_biomass = max(Decimal("0.00"), (src_biomass_before - est_biomass).quantize(Decimal("0.01")))
                source_remaining[src] = (new_src_count, new_src_biomass)

                if est_count <= 0:
                    skipped += 1
                    continue

                action_identifier = f"{op_id}:{src}:{dst}"
                action_map = get_external_map("PublicTransferEdge", action_identifier)

                defaults = {
                    "workflow": workflow,
                    "action_number": idx,
                    "source_assignment": assignment_by_pop[src],
                    "dest_assignment": assignment_by_pop[dst],
                    "source_population_before": max(src_count_before, est_count),
                    "transferred_count": est_count,
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": est_biomass,
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "planned_date": op_date,
                    "actual_execution_date": op_date,
                    "transfer_method": None,
                    "notes": f"FishTalk OperationID={op_id}; share_count={share_count}; share_biomass={share_biom}",
                }

                if action_map:
                    action = TransferAction.objects.get(pk=action_map.target_object_id)
                    for k, v in defaults.items():
                        setattr(action, k, v)
                    save_with_history(action, user=history_user, reason=history_reason)
                    updated_actions += 1
                else:
                    action_number = defaults["action_number"]
                    while TransferAction.objects.filter(
                        workflow=workflow, action_number=action_number
                    ).exists():
                        action_number += 1
                    defaults["action_number"] = action_number
                    action = TransferAction(**defaults)
                    save_with_history(action, user=history_user, reason=history_reason)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="PublicTransferEdge",
                        source_identifier=action_identifier,
                        defaults={
                            "target_app_label": action._meta.app_label,
                            "target_model": action._meta.model_name,
                            "target_object_id": action.pk,
                            "metadata": {"operation_id": op_id, "source_pop": src, "dest_pop": dst},
                        },
                    )
                    created_actions += 1

            # Finalize workflow summary.
            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.actual_start_date = op_date
            workflow.actual_completion_date = op_date
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            workflow.completed_by = user
            save_with_history(workflow, user=history_user, reason=history_reason)
            workflow.recalculate_totals()

        for transition in stage_transitions:
            from_stage_name = transition["from_stage"]
            to_stage_name = transition["to_stage"]
            transition_time = transition["transition_time"]
            pop_id = transition["population_id"]

            source_stage = LifeCycleStage.objects.filter(name=from_stage_name).first()
            dest_stage = LifeCycleStage.objects.filter(name=to_stage_name).first()
            if not source_stage or not dest_stage:
                skipped_stage += 1
                continue

            if isinstance(transition_time, datetime):
                transition_time = ensure_aware(transition_time)
            op_date = transition_time.date()

            transition_key_time = transition_time.strftime("%Y%m%d%H%M%S")
            transition_identifier = (
                f"{component_key}:{from_stage_name}:{to_stage_name}:{transition_key_time}"
            )
            wf_map = get_external_map("PopulationStageTransition", transition_identifier)
            if wf_map:
                workflow = BatchTransferWorkflow.objects.get(pk=wf_map.target_object_id)
                workflow.source_lifecycle_stage = source_stage
                workflow.dest_lifecycle_stage = dest_stage
                workflow.workflow_type = "LIFECYCLE_TRANSITION"
                workflow.status = "COMPLETED"
                workflow.planned_start_date = op_date
                workflow.planned_completion_date = op_date
                workflow.actual_start_date = op_date
                workflow.actual_completion_date = op_date
                workflow.completed_by = user
                workflow.notes = f"FishTalk stage transition {from_stage_name}→{to_stage_name}; PopulationID={pop_id}"
                save_with_history(workflow, user=history_user, reason=history_reason)
                updated_stage_wf += 1
            else:
                wf_number = (
                    f"FT-STG-{op_date.strftime('%Y%m%d')}-{stage_slug(from_stage_name)}-"
                    f"{stage_slug(to_stage_name)}-{component_key[:6]}"
                )[:50]
                workflow = BatchTransferWorkflow(
                    workflow_number=wf_number,
                    batch=batch,
                    workflow_type="LIFECYCLE_TRANSITION",
                    source_lifecycle_stage=source_stage,
                    dest_lifecycle_stage=dest_stage,
                    status="COMPLETED",
                    planned_start_date=op_date,
                    planned_completion_date=op_date,
                    actual_start_date=op_date,
                    actual_completion_date=op_date,
                    initiated_by=user,
                    completed_by=user,
                    notes=f"FishTalk stage transition {from_stage_name}→{to_stage_name}; PopulationID={pop_id}",
                )
                save_with_history(workflow, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PopulationStageTransition",
                    source_identifier=transition_identifier,
                    defaults={
                        "target_app_label": workflow._meta.app_label,
                        "target_model": workflow._meta.model_name,
                        "target_object_id": workflow.pk,
                        "metadata": {
                            "population_id": pop_id,
                            "from_stage": from_stage_name,
                            "to_stage": to_stage_name,
                            "transition_time": transition_time.isoformat(),
                        },
                    },
                )
                created_stage_wf += 1

            source_assignment = assignment_by_pop.get(pop_id) or next(
                iter(assignment_by_pop.values()), None
            )
            if not source_assignment:
                skipped_stage += 1
                continue

            count, biomass = lookup_status_snapshot(extractor, population_id=pop_id, at_time=transition_time)
            action_identifier = f"{transition_identifier}:action"
            action_map = get_external_map("PopulationStageTransitionAction", action_identifier)
            action_defaults = {
                "workflow": workflow,
                "action_number": 1,
                "source_assignment": source_assignment,
                "dest_assignment": source_assignment,
                "source_population_before": max(count, 0),
                "transferred_count": max(count, 0),
                "mortality_during_transfer": 0,
                "transferred_biomass_kg": biomass,
                "allow_mixed": False,
                "status": "COMPLETED",
                "planned_date": op_date,
                "actual_execution_date": op_date,
                "transfer_method": None,
                "notes": (
                    f"FishTalk stage transition {from_stage_name}→{to_stage_name}; PopulationID={pop_id}"
                ),
            }

            if action_map:
                action = TransferAction.objects.get(pk=action_map.target_object_id)
                for k, v in action_defaults.items():
                    setattr(action, k, v)
                save_with_history(action, user=history_user, reason=history_reason)
                updated_stage_actions += 1
            else:
                action = TransferAction(**action_defaults)
                save_with_history(action, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PopulationStageTransitionAction",
                    source_identifier=action_identifier,
                    defaults={
                        "target_app_label": action._meta.app_label,
                        "target_model": action._meta.model_name,
                        "target_object_id": action.pk,
                        "metadata": {
                            "population_id": pop_id,
                            "from_stage": from_stage_name,
                            "to_stage": to_stage_name,
                        },
                    },
                )
                created_stage_actions += 1

            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            save_with_history(workflow, user=history_user, reason=history_reason)
            workflow.recalculate_totals()

    print(
        f"Migrated transfers for component_key={component_key} into batch={batch.batch_number} "
        f"(workflows created={created_wf}, updated={updated_wf}; actions created={created_actions}, updated={updated_actions}, skipped={skipped}; "
        f"stage workflows created={created_stage_wf}, updated={updated_stage_wf}; "
        f"stage actions created={created_stage_actions}, updated={updated_stage_actions}, skipped={skipped_stage})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
