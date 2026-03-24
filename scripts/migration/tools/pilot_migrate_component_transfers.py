#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk transfers (movements) for one stitched population component.

This script supports two transfer data sources:
1. **SubTransfers (recommended)**: Active through 2025, use with --use-subtransfers
2. **PublicTransfers (legacy)**: Broken since Jan 2023, default for backward compatibility

SubTransfers tracks actual fish movements with granular population chains:
  - SourcePopBefore -> SourcePopAfter (remnant chain)
  - SourcePopBefore -> DestPopAfter (transfer to new location)

Target (AquaMind):
  - apps.batch.models.BatchTransferWorkflow (1 per FishTalk OperationID)
  - apps.batch.models.TransferAction (1 per FishTalk edge SourcePop->DestPop)

Important:
  - This is a *best-effort* backfill: FishTalk transfers can represent splits/merges;
    AquaMind TransferAction requires absolute transferred_count and biomass.
    We estimate using the source population snapshot near the operation time.
  - Assignment-derived synthetic stage-transition workflows/actions are disabled by
    default. Enable explicitly only for legacy diagnostics.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone
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
from django.db.models import Max, Min, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch, BatchTransferWorkflow, TransferAction, LifeCycleStage
from apps.batch.models.assignment import BatchContainerAssignment
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.tools.etl_loader import ETLDataLoader
from scripts.migration.tools.pilot_migrate_component import (
    stage_from_hall,
    hall_label_from_group,
    normalize_label,
)
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map


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


def get_external_map(
    source_model: str,
    source_identifier: str,
    *,
    component_key: str | None = None,
) -> ExternalIdMap | None:
    if source_model == "Populations":
        return get_assignment_external_map(
            str(source_identifier),
            component_key=component_key,
        )
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


def canonicalize_same_stage_superseded_assignment(
    assignment: BatchContainerAssignment | None,
    *,
    batch: Batch,
    dest_stage: LifeCycleStage | None,
    op_date: date,
) -> BatchContainerAssignment | None:
    """Promote same-day superseded relay rows to their surviving companion.

    Component migration can leave short same-container/same-stage relay populations
    as dead-end history rows. Some are zero-suppressed, while others keep their
    direct transfer count. Transfer traceability should bind to the longer-lived
    companion assignment that carries the merged downstream lineage instead.
    """
    if assignment is None:
        return None
    if assignment.batch_id != batch.id:
        return assignment
    if assignment.assignment_date != op_date:
        return assignment
    if assignment.departure_date is None or assignment.departure_date > assignment.assignment_date:
        return assignment

    stage_id = dest_stage.id if dest_stage is not None else assignment.lifecycle_stage_id
    if not stage_id:
        return assignment

    companions = list(
        BatchContainerAssignment.objects.filter(
            batch=batch,
            container_id=assignment.container_id,
            lifecycle_stage_id=stage_id,
            assignment_date=assignment.assignment_date,
        )
        .exclude(pk=assignment.pk)
        .order_by("id")
    )
    if not companions:
        return assignment

    longer_lived_companions = [
        candidate
        for candidate in companions
        if candidate.departure_date is None
        or candidate.departure_date > assignment.assignment_date
    ]
    if not longer_lived_companions:
        return assignment

    def candidate_key(candidate: BatchContainerAssignment) -> tuple[int, int, int, int, int]:
        longer_lived = int(
            candidate.departure_date is None
            or candidate.departure_date > candidate.assignment_date
        )
        non_zero = int(int(candidate.population_count or 0) > 0)
        departure_ordinal = (candidate.departure_date or date.max).toordinal()
        return (
            longer_lived,
            non_zero,
            departure_ordinal,
            int(candidate.population_count or 0),
            candidate.pk,
        )

    canonical = max(longer_lived_companions, key=candidate_key)
    if candidate_key(canonical) <= candidate_key(assignment):
        return assignment
    return canonical


STAGE_ORDER = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_INDEX = {name: idx for idx, name in enumerate(STAGE_ORDER)}


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


def load_members_from_chain(chain_dir: Path, *, chain_id: str) -> list[ComponentMember]:
    """Load members from SubTransfers-based chain stitching output."""
    import csv

    path = chain_dir / "batch_chains.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing chain file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("chain_id") != chain_id:
                continue
            
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(ComponentMember(
                population_id=row.get("population_id", ""),
                start_time=start,
                end_time=end,
            ))

    members.sort(key=lambda m: m.start_time)
    return members


def load_subtransfers_from_csv(csv_dir: Path, population_ids: set[str]) -> list[dict]:
    """Load SubTransfers rows for operations initiated by in-scope source populations."""
    import csv

    path = csv_dir / "sub_transfers.csv"
    if not path.exists():
        return []

    scoped_operation_ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            op_id = (row.get("OperationID") or "").strip()
            src_before = (row.get("SourcePopBefore") or "").strip()
            if op_id and src_before in population_ids:
                scoped_operation_ids.add(op_id)

    if not scoped_operation_ids:
        return []

    transfers: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            op_id = (row.get("OperationID") or "").strip()
            if op_id in scoped_operation_ids:
                transfers.append(row)

    return transfers


def load_stage_names_from_csv(csv_dir: Path) -> dict[str, str]:
    import csv

    path = csv_dir / "production_stages.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing production stages file: {path}")

    stage_name_by_id: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stage_id = (row.get("StageID") or "").strip()
            if not stage_id:
                continue
            stage_name_by_id[stage_id] = (row.get("StageName") or "").strip()

    return stage_name_by_id


def load_population_stages_from_csv(csv_dir: Path, population_ids: set[str]) -> list[dict]:
    import csv

    path = csv_dir / "population_stages.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing population stages file: {path}")

    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id and pop_id in population_ids:
                rows.append(row)

    return rows


def build_status_snapshot_index(csv_dir: Path, population_ids: set[str]) -> dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]]:
    import csv

    path = csv_dir / "status_values.csv"
    if not path.exists():
        return {}

    raw: dict[str, list[tuple[datetime, int, Decimal]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id or pop_id not in population_ids:
                continue
            ts = parse_dt(row.get("StatusTime", ""))
            if ts is None:
                continue
            ts = ensure_aware(ts)
            count_val = row.get("CurrentCount")
            biom_val = row.get("CurrentBiomassKg")
            try:
                count = int(float(count_val)) if count_val not in (None, "") else 0
            except ValueError:
                count = 0
            try:
                biomass = Decimal(str(biom_val)) if biom_val not in (None, "") else Decimal("0.00")
            except Exception:
                biomass = Decimal("0.00")
            raw.setdefault(pop_id, []).append((ts, count, biomass))

    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]] = {}
    for pop_id, items in raw.items():
        items.sort(key=lambda item: item[0])
        times = [item[0] for item in items]
        values = [(item[1], item[2]) for item in items]
        index[pop_id] = (times, values)

    return index


def lookup_status_snapshot_from_index(
    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]],
    population_id: str,
    at_time: datetime,
) -> tuple[int, Decimal]:
    if not index or population_id not in index:
        return 0, Decimal("0.00")
    times, values = index[population_id]
    if not times:
        return 0, Decimal("0.00")
    pos = bisect_right(times, at_time)
    if pos > 0:
        return values[pos - 1]
    if pos < len(values):
        return values[pos]
    return 0, Decimal("0.00")


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


CHAIN_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "chain_stitching"
DEST_ASSIGNMENT_SOURCE_MODEL = "SubTransferDestinationPopulationAssignment"
STAGE_BUCKET_WORKFLOW_SOURCE_MODEL = "TransferStageWorkflowBucket"
MIGRATION_TRANSPORT_BYPASS_NOTE = (
    "[migration_transport_bypass] FishTalk source data lacks deterministic "
    "per-leg transport handoff metadata (truck/vessel/trip/compartment + "
    "mandatory start snapshot chain). Migration persists historical transfer "
    "edges as completed direct actions and forces workflows non-dynamic."
)


def append_note_once(existing: str | None, note: str) -> str:
    current = (existing or "").strip()
    if note in current:
        return current
    return f"{current}\n{note}".strip()


def enforce_static_workflow_for_migration(
    workflow: BatchTransferWorkflow,
    *,
    history_user,
    history_reason: str,
) -> bool:
    """
    Keep migrated historical workflows out of runtime dynamic handoff semantics.

    Dynamic execution in AquaMind requires explicit start/complete handoff flow
    and mandatory transfer-start snapshots. FishTalk transfer extracts do not
    provide deterministic per-leg transport metadata for this path.
    """
    changed = False
    if workflow.is_dynamic_execution:
        workflow.is_dynamic_execution = False
        changed = True
    if workflow.dynamic_route_mode is not None:
        workflow.dynamic_route_mode = None
        changed = True
    if workflow.dynamic_completed_by_id is not None:
        workflow.dynamic_completed_by = None
        changed = True
    if workflow.dynamic_completed_at is not None:
        workflow.dynamic_completed_at = None
        changed = True
    updated_notes = append_note_once(workflow.notes, MIGRATION_TRANSPORT_BYPASS_NOTE)
    if updated_notes != (workflow.notes or "").strip():
        workflow.notes = updated_notes
        changed = True

    if changed:
        save_with_history(workflow, user=history_user, reason=history_reason)
    return changed


def parse_ratio(value: object) -> float:
    raw = str(value or "").strip()
    if not raw:
        return 0.0
    try:
        parsed = float(raw)
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, parsed))


def allocate_transfer_counts(total_count: int, ratios: list[float]) -> list[int]:
    if not ratios:
        return []
    if total_count <= 0:
        return [0 for _ in ratios]

    clamped = [max(0.0, float(r or 0.0)) for r in ratios]
    ratio_sum = sum(clamped)
    if ratio_sum <= 0:
        return [0 for _ in ratios]

    if ratio_sum > 1.0:
        effective = [r / ratio_sum for r in clamped]
        effective_sum = 1.0
    else:
        effective = clamped
        effective_sum = ratio_sum

    target_total = int(round(total_count * effective_sum))
    target_total = max(0, min(total_count, target_total))
    if target_total == 0 and any(r > 0 for r in effective):
        target_total = 1

    raw_allocations = [total_count * ratio for ratio in effective]
    allocated = [int(value) for value in raw_allocations]
    remainder = target_total - sum(allocated)
    if remainder > 0:
        order = sorted(
            range(len(raw_allocations)),
            key=lambda idx: (raw_allocations[idx] - allocated[idx], effective[idx], -idx),
            reverse=True,
        )
        for idx in order[:remainder]:
            allocated[idx] += 1
    elif remainder < 0:
        order = sorted(
            range(len(raw_allocations)),
            key=lambda idx: (raw_allocations[idx] - allocated[idx], effective[idx], idx),
        )
        remaining = abs(remainder)
        for idx in order:
            if remaining <= 0:
                break
            if allocated[idx] <= 0:
                continue
            allocated[idx] -= 1
            remaining -= 1

    return [max(0, value) for value in allocated]


def allocate_transfer_biomass(
    total_biomass: Decimal,
    total_count: int,
    allocated_counts: list[int],
) -> list[Decimal]:
    if not allocated_counts:
        return []
    if total_biomass <= Decimal("0.00") or total_count <= 0:
        return [Decimal("0.00") for _ in allocated_counts]

    transferred_total = sum(max(0, int(value)) for value in allocated_counts)
    if transferred_total <= 0:
        return [Decimal("0.00") for _ in allocated_counts]

    avg_kg_per_fish = total_biomass / Decimal(total_count)
    allocated = [
        (avg_kg_per_fish * Decimal(max(0, int(value)))).quantize(Decimal("0.01"))
        for value in allocated_counts
    ]
    target_total = (avg_kg_per_fish * Decimal(transferred_total)).quantize(Decimal("0.01"))
    current_total = sum(allocated, Decimal("0.00"))
    delta = target_total - current_total
    if delta != Decimal("0.00"):
        pivot = max(range(len(allocated)), key=lambda idx: allocated_counts[idx])
        adjusted = (allocated[pivot] + delta).quantize(Decimal("0.01"))
        allocated[pivot] = max(Decimal("0.00"), adjusted)

    return allocated


def expand_subtransfer_rows_for_source_scope(
    raw_rows: list[dict],
    source_population_ids: set[str],
) -> list[dict]:
    """Expand SubTransfers chains to root-source edges plus explicit bridge edges.

    FishTalk often models an in-scope split as:
      root SourcePopBefore -> SourcePopAfter (remnant)
      SourcePopAfter -> DestPopAfter (second/internal leg)

    We need root-source conservation edges for migration. If we keep only raw
    SourcePopBefore->DestPopAfter rows, the follow-on leg can stay tied to a
    zero-duration successor population and later allocate zero fish.

    FishTalk can continue an in-operation chain through either:
    - SourcePopAfter (residual branch), or
    - DestPopAfter (moved branch promoted to the next SourcePopBefore).

    The safe behavior is:
    - expand to root-source terminal edges first, then
    - preserve explicit DestPopBefore -> DestPopAfter bridge continuity edges
      so earlier contributors remain connected when FishTalk re-materializes a
      mixed destination population as a new population in the same container.

    Those bridge edges are required for GUI traceability through staged/0-day
    destination-population handoffs such as 5M -> A -> B chains. Without them,
    the first arriving assignment is visible but its later downstream fanout
    becomes disconnected as soon as FishTalk rolls the destination lane forward
    into a successor population.
    """
    rows_by_operation: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for idx, row in enumerate(raw_rows):
        op_id = (row.get("OperationID") or "").strip()
        if not op_id:
            continue
        rows_by_operation[op_id].append((idx, row))

    aggregates: defaultdict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"share_count": 0.0, "share_biomass": 0.0}
    )

    for op_id, indexed_rows in rows_by_operation.items():
        ordered_rows = sorted(
            indexed_rows,
            key=lambda item: (
                (item[1].get("OperationTime") or item[1].get("OperationStartTime") or "").strip(),
                item[0],
            ),
        )

        rows_by_source: dict[str, list[dict]] = defaultdict(list)
        source_before_in_op: set[str] = set()
        produced_nodes_in_op: set[str] = set()
        op_time_fallback = ""
        for _, row in ordered_rows:
            src_before = (row.get("SourcePopBefore") or row.get("SourcePop") or "").strip()
            if not src_before:
                continue
            rows_by_source[src_before].append(row)
            source_before_in_op.add(src_before)
            next_source = (row.get("SourcePopAfter") or "").strip()
            if next_source:
                produced_nodes_in_op.add(next_source)
            dest_after = (row.get("DestPopAfter") or row.get("DestPop") or "").strip()
            if dest_after:
                produced_nodes_in_op.add(dest_after)
            if not op_time_fallback:
                op_time_fallback = (
                    row.get("OperationTime")
                    or row.get("OperationStartTime")
                    or ""
                ).strip()

        root_sources = sorted(
            src
            for src in source_population_ids
            if src in source_before_in_op and src not in produced_nodes_in_op
        )
        if not root_sources:
            root_sources = sorted(
                src for src in source_population_ids if src in source_before_in_op
            )

        for root_source in root_sources:
            current_count_shares: dict[str, float] = {root_source: 1.0}
            current_biomass_shares: dict[str, float] = {root_source: 1.0}

            def apply_transfer_row(row: dict) -> None:
                src_before = (row.get("SourcePopBefore") or row.get("SourcePop") or "").strip()
                src_after = (row.get("SourcePopAfter") or "").strip()
                dst_before = (row.get("DestPopBefore") or "").strip()
                dst_after = (row.get("DestPopAfter") or row.get("DestPop") or "").strip()

                share_count_step = parse_ratio(
                    row.get("ShareCountFwd") or row.get("ShareCountForward")
                )
                share_biomass_step = parse_ratio(
                    row.get("ShareBiomFwd") or row.get("ShareBiomassForward")
                )
                if share_count_step <= 0 and share_biomass_step > 0:
                    share_count_step = share_biomass_step
                if share_biomass_step <= 0 and share_count_step > 0:
                    share_biomass_step = share_count_step

                moved_count_share = None
                moved_biomass_share = None

                if src_before in current_count_shares:
                    src_count_share = current_count_shares.get(src_before, 0.0)
                    moved_count_share = src_count_share * share_count_step
                    remaining_count_share = max(0.0, src_count_share - moved_count_share)
                    if src_after:
                        current_count_shares[src_after] = remaining_count_share
                    current_count_shares.pop(src_before, None)

                if src_before in current_biomass_shares:
                    src_biomass_share = current_biomass_shares.get(src_before, 0.0)
                    moved_biomass_share = src_biomass_share * share_biomass_step
                    remaining_biomass_share = max(0.0, src_biomass_share - moved_biomass_share)
                    if src_after:
                        current_biomass_shares[src_after] = remaining_biomass_share
                    current_biomass_shares.pop(src_before, None)

                dest_before_count_share = None
                if dst_before in current_count_shares:
                    dest_before_count_share = current_count_shares.pop(dst_before)

                dest_before_biomass_share = None
                if dst_before in current_biomass_shares:
                    dest_before_biomass_share = current_biomass_shares.pop(dst_before)

                if dst_after:
                    dest_count_share = 0.0
                    if dest_before_count_share is not None:
                        dest_count_share += dest_before_count_share
                    if moved_count_share is not None:
                        dest_count_share += moved_count_share
                    current_count_shares[dst_after] = dest_count_share

                    dest_biomass_share = 0.0
                    if dest_before_biomass_share is not None:
                        dest_biomass_share += dest_before_biomass_share
                    if moved_biomass_share is not None:
                        dest_biomass_share += moved_biomass_share
                    current_biomass_shares[dst_after] = dest_biomass_share

            pending = [row for _, row in ordered_rows]
            while pending:
                produced_candidates = {
                    (value or "").strip()
                    for row in pending
                    for value in (
                        row.get("SourcePopAfter"),
                        row.get("DestPopAfter"),
                        row.get("DestPop"),
                    )
                    if (value or "").strip()
                }
                progressed = False
                next_pending: list[dict] = []
                for row in pending:
                    src_before = (row.get("SourcePopBefore") or row.get("SourcePop") or "").strip()
                    dst_before = (row.get("DestPopBefore") or "").strip()
                    unresolved_dependency = any(
                        dep
                        and dep not in current_count_shares
                        and dep not in current_biomass_shares
                        and dep in produced_candidates
                        for dep in (src_before, dst_before)
                    )
                    if unresolved_dependency:
                        next_pending.append(row)
                        continue
                    apply_transfer_row(row)
                    progressed = True

                if not next_pending:
                    break
                if not progressed:
                    for row in next_pending:
                        apply_transfer_row(row)
                    break
                pending = next_pending

            for dest_pop, share_count in current_count_shares.items():
                share_biomass = current_biomass_shares.get(dest_pop, 0.0)
                if dest_pop == root_source:
                    continue
                if share_count <= 0 and share_biomass <= 0:
                    continue
                key = (op_id, op_time_fallback, root_source, dest_pop)
                aggregates[key]["share_count"] += share_count
                aggregates[key]["share_biomass"] += share_biomass

        # Preserve explicit destination-lane bridge continuity inside the same
        # operation. FishTalk emits these as DestPopBefore -> DestPopAfter when a
        # destination lane is re-materialized as a successor population after a
        # staged/0-day redistribution. They carry full continuity of the prior
        # destination population and are distinct from root-source conservation
        # edges.
        for _, row in ordered_rows:
            dest_before = (row.get("DestPopBefore") or "").strip()
            dest_after = (row.get("DestPopAfter") or row.get("DestPop") or "").strip()
            if not dest_before or not dest_after or dest_before == dest_after:
                continue
            if dest_before not in source_population_ids or dest_after not in source_population_ids:
                continue
            key = (op_id, op_time_fallback, dest_before, dest_after)
            aggregates[key]["share_count"] = max(aggregates[key]["share_count"], 1.0)
            aggregates[key]["share_biomass"] = max(aggregates[key]["share_biomass"], 1.0)

    expanded_rows: list[dict] = []
    for (op_id, op_time, source_pop, dest_pop), shares in sorted(aggregates.items()):
        share_count = max(0.0, shares["share_count"])
        share_biomass = max(0.0, shares["share_biomass"])
        if share_count <= 0 and share_biomass <= 0:
            continue
        expanded_rows.append(
            {
                "OperationID": op_id,
                "OperationStartTime": op_time,
                "SourcePop": source_pop,
                "DestPop": dest_pop,
                "ShareCountForward": f"{min(1.0, share_count):.12f}",
                "ShareBiomassForward": f"{min(1.0, share_biomass):.12f}",
            }
        )

    return expanded_rows


def load_population_containers_from_csv(csv_dir: Path) -> dict[str, str]:
    path = csv_dir / "populations.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing populations file: {path}")

    population_container: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id:
                continue
            population_container[pop_id] = (row.get("ContainerID") or "").strip()
    return population_container


def load_containers_from_csv(csv_dir: Path) -> dict[str, dict[str, str]]:
    path = csv_dir / "containers.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing containers file: {path}")

    containers: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if not container_id:
                continue
            containers[container_id] = {
                "name": (row.get("ContainerName") or "").strip(),
                "org_unit_id": (row.get("OrgUnitID") or "").strip(),
                "container_type": (row.get("ContainerType") or "").strip(),
            }
    return containers


def load_grouped_organisation_from_csv(csv_dir: Path) -> dict[str, dict[str, str]]:
    path = csv_dir / "grouped_organisation.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing grouped organisation file: {path}")

    grouped: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if not container_id:
                continue
            grouped[container_id] = {
                "site": (row.get("Site") or "").strip(),
                "container_group": (row.get("ContainerGroup") or "").strip(),
            }
    return grouped


def build_stage_bucket_identifier(
    *,
    component_key: str,
    station_site: str,
    workflow_type: str,
    source_stage_name: str,
    dest_stage_name: str,
) -> str:
    canonical = (
        f"{component_key}|site={station_site}|workflow_type={workflow_type}|"
        f"source_stage={source_stage_name}|dest_stage={dest_stage_name}"
    )
    site_token = "".join(ch for ch in station_site.upper() if ch.isalnum())[:20] or "UNKSITE"
    source_token = stage_slug(source_stage_name) or "UNKS"
    dest_token = stage_slug(dest_stage_name) or "UNKD"
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12].upper()
    return (
        f"{component_key[:36]}|{site_token}|{workflow_type}|{source_token}|{dest_token}|{digest}"
    )[:128]


def build_stage_bucket_workflow_number(identifier: str) -> str:
    digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest()[:10].upper()
    return f"FT-TRF-BKT-{digest}"[:50]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pilot migrate transfer workflows/actions for a stitched FishTalk component",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transfer data sources:
  --use-subtransfers: Use SubTransfers table (active through 2025, recommended for 2020+)
  Default: Use PublicTransfers (broken since Jan 2023, legacy only)
        """,
    )
    
    # SubTransfers-based stitching (recommended)
    chain_group = parser.add_argument_group("SubTransfers-based stitching (recommended)")
    chain_group.add_argument(
        "--chain-id",
        help="Chain ID from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)",
    )
    chain_group.add_argument(
        "--chain-dir",
        default=str(CHAIN_DIR_DEFAULT),
        help="Directory containing batch_chains.csv from scripts/migration/legacy/tools/subtransfer_chain_stitching.py (deprecated)",
    )
    
    # Project-based stitching (legacy)
    legacy_group = parser.add_argument_group("Project-based stitching (legacy)")
    legacy_group.add_argument("--component-id", type=int, help="Component id from components.csv")
    legacy_group.add_argument("--component-key", help="Stable component_key from components.csv")
    legacy_group.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    
    # Transfer data source options
    parser.add_argument(
        "--use-subtransfers",
        action="store_true",
        help="Use SubTransfers table instead of PublicTransfers (recommended for 2020+ batches)",
    )
    parser.add_argument(
        "--transfer-edge-scope",
        choices=["source-in-scope", "internal-only"],
        default="source-in-scope",
        help=(
            "Transfer edge inclusion policy after root-source SubTransfers expansion. "
            "'source-in-scope' keeps expanded edges whose root source belongs to the component "
            "(destination may be external). "
            "'internal-only' keeps the same expanded root-source edges but filters destinations "
            "to component members only."
        ),
    )
    parser.add_argument(
        "--workflow-grouping",
        choices=["stage-bucket", "operation"],
        default="stage-bucket",
        help=(
            "How transfer edges are grouped into workflows. "
            "'stage-bucket' groups by station + source/destination lifecycle stages; "
            "'operation' keeps legacy one-workflow-per-OperationID behavior."
        ),
    )
    synthetic_group = parser.add_mutually_exclusive_group()
    synthetic_group.add_argument(
        "--skip-synthetic-stage-transitions",
        dest="skip_synthetic_stage_transitions",
        action="store_true",
        help=(
            "Default behavior. Do not synthesize assignment-derived "
            "PopulationStageTransition workflows/actions; keep only transfer-edge-backed "
            "workflows/actions."
        ),
    )
    synthetic_group.add_argument(
        "--include-synthetic-stage-transitions",
        dest="skip_synthetic_stage_transitions",
        action="store_false",
        help=(
            "Legacy override. Synthesize assignment-derived PopulationStageTransition "
            "workflows/actions."
        ),
    )
    parser.set_defaults(skip_synthetic_stage_transitions=True)
    parser.add_argument(
        "--allow-dynamic-runtime-workflows",
        action="store_true",
        help=(
            "Keep inferred dynamic workflow semantics for migrated transfers. "
            "Default behavior forces migrated workflows to static mode to "
            "bypass mandatory runtime handoff/snapshot requirements when "
            "FishTalk transport metadata is incomplete."
        ),
    )
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
    print(
        "Transfer migration mode: "
        f"edge_scope={args.transfer_edge_scope}, workflow_grouping={args.workflow_grouping}"
    )
    if args.skip_synthetic_stage_transitions:
        print(
            "Synthetic stage-transition workflows/actions disabled "
            "(default migration guardrail)."
        )
    else:
        print(
            "WARNING: synthetic stage-transition workflows/actions enabled "
            "via --include-synthetic-stage-transitions."
        )
    if args.allow_dynamic_runtime_workflows:
        print(
            "Dynamic runtime workflow semantics: ENABLED "
            "(no migration transport bypass guardrail)."
        )
    else:
        print(
            "Dynamic runtime workflow semantics: DISABLED by migration guardrail "
            "(historical direct actions, non-dynamic workflows)."
        )
    
    # Determine which stitching approach to use
    use_chain_stitching = args.chain_id is not None
    use_project_stitching = args.component_id is not None or args.component_key is not None
    
    if not use_chain_stitching and not use_project_stitching:
        raise SystemExit(
            "Provide either:\n"
            "  SubTransfers-based: --chain-id CHAIN-00001\n"
            "  Project-based: --component-id or --component-key"
        )
    
    if use_chain_stitching and use_project_stitching:
        raise SystemExit("Cannot use both --chain-id and --component-id/--component-key")
    
    # Load members based on stitching approach
    if use_chain_stitching:
        chain_dir = Path(args.chain_dir)
        members = load_members_from_chain(chain_dir, chain_id=args.chain_id)
        if not members:
            raise SystemExit(f"No members found for chain {args.chain_id}")
        component_key = f"chain:{args.chain_id}"
        print(f"Loaded {len(members)} populations from chain {args.chain_id}")
        
        # For chain-based, default to SubTransfers
        if not args.use_subtransfers:
            print("Note: Using --use-subtransfers by default for chain-based stitching")
            args.use_subtransfers = True
    else:
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

    extractor = None if args.use_csv else BaseExtractor(ExtractionContext(profile=args.sql_profile))

    # For chain-based stitching, skip project lookup (not relevant)
    project_number, input_year, running_number = None, None, None
    if not use_chain_stitching and not args.use_csv:
        project_number, input_year, running_number = lookup_project_info(
            extractor, population_id=component_key
        )

    in_clause = ",".join(f"'{pid}'" for pid in population_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")
    pop_id_set = set(population_ids)
    status_index = build_status_snapshot_index(Path(args.use_csv), pop_id_set) if args.use_csv else {}

    # Load transfers from appropriate source
    if args.use_subtransfers:
        # Use SubTransfers (recommended for 2020+)
        if args.use_csv:
            # Load from CSV
            csv_dir = Path(args.use_csv)
            raw_transfers = load_subtransfers_from_csv(csv_dir, pop_id_set)
            expanded_transfers = expand_subtransfer_rows_for_source_scope(raw_transfers, pop_id_set)
            if args.transfer_edge_scope == "source-in-scope":
                transfer_rows = expanded_transfers
            else:
                transfer_rows = [
                    row for row in expanded_transfers if (row.get("DestPop") or "").strip() in pop_id_set
                ]
            print(
                f"Loaded {len(raw_transfers)} SubTransfers rows from CSV; "
                f"expanded to {len(transfer_rows)} scoped edges"
            )
        else:
            # Query from SQL
            raw_transfers = extractor._run_sqlcmd(
                query=(
                    "WITH scoped_ops AS ("
                    "SELECT DISTINCT st.OperationID "
                    "FROM dbo.SubTransfers st "
                    f"WHERE st.SourcePopBefore IN ({in_clause})"
                    ") "
                    "SELECT "
                    "st.OperationID, "
                    "CONVERT(varchar(36), st.SubTransferID) AS SubTransferID, "
                    "CONVERT(varchar(19), o.StartTime, 120) AS OperationTime, "
                    "CONVERT(varchar(36), st.SourcePopBefore) AS SourcePopBefore, "
                    "CONVERT(varchar(36), st.SourcePopAfter) AS SourcePopAfter, "
                    "CONVERT(varchar(36), st.DestPopAfter) AS DestPopAfter, "
                    "CONVERT(varchar(64), st.ShareCountFwd) AS ShareCountFwd, "
                    "CONVERT(varchar(64), st.ShareBiomFwd) AS ShareBiomFwd "
                    "FROM dbo.SubTransfers st "
                    "JOIN scoped_ops so ON so.OperationID = st.OperationID "
                    "JOIN dbo.Operations o ON o.OperationID = st.OperationID "
                    f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
                    "ORDER BY o.StartTime ASC, st.OperationID ASC, st.SubTransferID ASC"
                ),
                headers=[
                    "OperationID",
                    "SubTransferID",
                    "OperationTime",
                    "SourcePopBefore",
                    "SourcePopAfter",
                    "DestPopAfter",
                    "ShareCountFwd",
                    "ShareBiomFwd",
                ],
            )
            expanded_transfers = expand_subtransfer_rows_for_source_scope(raw_transfers, pop_id_set)
            if args.transfer_edge_scope == "source-in-scope":
                transfer_rows = expanded_transfers
            else:
                transfer_rows = [
                    row for row in expanded_transfers if (row.get("DestPop") or "").strip() in pop_id_set
                ]
            print(
                f"Loaded {len(raw_transfers)} SubTransfers rows from SQL; "
                f"expanded to {len(transfer_rows)} scoped edges"
            )
    else:
        # Use PublicTransfers (legacy, broken since Jan 2023)
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
        print(f"Loaded {len(transfer_rows)} PublicTransfers edges from SQL")

    if args.use_csv:
        csv_dir = Path(args.use_csv)
        stage_name_by_id = load_stage_names_from_csv(csv_dir)
        stage_events_raw = load_population_stages_from_csv(csv_dir, pop_id_set)
    else:
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

    transitions_by_pair: dict[tuple[str, str], list[BatchContainerAssignment]] = {}

    if args.transfer_edge_scope == "internal-only":
        transfer_rows = [
            row
            for row in transfer_rows
            if (row.get("SourcePop") in population_ids and row.get("DestPop") in population_ids)
        ]
    else:
        transfer_rows = [
            row
            for row in transfer_rows
            if row.get("SourcePop") in population_ids
        ]

    if args.workflow_grouping == "stage-bucket" and not args.use_csv:
        print(
            "WARNING: --workflow-grouping=stage-bucket requires --use-csv for hall-stage mapping; "
            "falling back to operation grouping."
        )
        args.workflow_grouping = "operation"

    population_container_by_id: dict[str, str] = {}
    grouped_org_by_container: dict[str, dict[str, str]] = {}
    container_info_by_id: dict[str, dict[str, str]] = {}
    if args.use_csv and args.workflow_grouping == "stage-bucket":
        csv_dir = Path(args.use_csv)
        population_container_by_id = load_population_containers_from_csv(csv_dir)
        grouped_org_by_container = load_grouped_organisation_from_csv(csv_dir)
        container_info_by_id = load_containers_from_csv(csv_dir)

    if args.dry_run:
        print(
            f"[dry-run] Would migrate {len(transfer_rows)} "
            f"{'SubTransfers' if args.use_subtransfers else 'PublicTransfers'} edges into batch={batch.batch_number}"
        )
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid, component_key=component_key)
        if mapped:
            assignment = BatchContainerAssignment.objects.filter(pk=mapped.target_object_id).first()
            if assignment:
                assignment_by_pop[pid] = assignment

    lifecycle_stage_by_name = {stage.name: stage for stage in LifeCycleStage.objects.all()}
    fallback_stage = LifeCycleStage.objects.first()
    if fallback_stage is None:
        raise SystemExit("Missing LifeCycleStage master data")

    created_wf = updated_wf = created_actions = updated_actions = skipped = 0
    created_stage_wf = updated_stage_wf = created_stage_actions = updated_stage_actions = skipped_stage = 0
    created_dest_assignments = reused_dest_assignments = 0
    canonicalized_dest_assignments = 0
    synced_dest_assignments = 0
    synced_source_stage_assignments = 0
    synced_source_count_assignments = 0
    forced_static_workflows = 0
    pruned_transfer_workflows = 0
    pruned_transfer_actions = 0
    skipped_reasons: defaultdict[str, int] = defaultdict(int)

    with transaction.atomic():
        history_user = user
        history_reason = f"FishTalk migration: transfers for component {component_key}"
        stage_prefix = f"{component_key}:"
        stage_wf_ids = list(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="PopulationStageTransition",
                source_identifier__startswith=stage_prefix,
            ).values_list("target_object_id", flat=True)
        )
        if stage_wf_ids:
            BatchTransferWorkflow.objects.filter(pk__in=stage_wf_ids).delete()
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model__in=["PopulationStageTransition", "PopulationStageTransitionAction"],
                source_identifier__startswith=stage_prefix,
            ).delete()

        batch_workflow_ids = set(
            BatchTransferWorkflow.objects.filter(batch=batch).values_list("id", flat=True)
        )
        transfer_workflow_source_models = {
            STAGE_BUCKET_WORKFLOW_SOURCE_MODEL,
            "TransferOperation",
        }
        existing_transfer_wf_maps = list(
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model__in=transfer_workflow_source_models,
                target_model="batchtransferworkflow",
                target_object_id__in=batch_workflow_ids,
            )
        )
        existing_transfer_wf_ids = sorted(
            {
                int(mapped.target_object_id)
                for mapped in existing_transfer_wf_maps
                if mapped.target_object_id
            }
        )
        if existing_transfer_wf_ids:
            existing_transfer_action_ids = list(
                TransferAction.objects.filter(workflow_id__in=existing_transfer_wf_ids)
                .values_list("id", flat=True)
            )
            if existing_transfer_action_ids:
                ExternalIdMap.objects.filter(
                    source_system="FishTalk",
                    source_model="PublicTransferEdge",
                    target_model="transferaction",
                    target_object_id__in=existing_transfer_action_ids,
                ).delete()
                pruned_transfer_actions = len(existing_transfer_action_ids)
            ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model__in=transfer_workflow_source_models,
                target_model="batchtransferworkflow",
                target_object_id__in=existing_transfer_wf_ids,
            ).delete()
            BatchTransferWorkflow.objects.filter(pk__in=existing_transfer_wf_ids).delete()
            pruned_transfer_workflows = len(existing_transfer_wf_ids)

        container_external_map_by_source: dict[str, ExternalIdMap | None] = {}
        container_by_source: dict[str, object] = {}
        hall_by_station_group: dict[tuple[int, str], object] = {}
        dest_assignment_ids_for_sync: set[int] = set()
        workflow_ids_for_sync: set[int] = set()
        source_assignment_ids_stage_synced: set[int] = set()
        source_assignment_ids_for_count_sync: set[int] = set()

        def bootstrap_destination_container(
            *,
            dest_container_id: str,
            source_assignment: BatchContainerAssignment,
        ):
            from apps.infrastructure.models import Container, Hall

            source_container = source_assignment.container
            source_hall = source_container.hall
            source_station = source_hall.freshwater_station if source_hall else None
            if source_station is None:
                skipped_reasons["missing_source_station_for_destination_container"] += 1
                return None

            group_meta = grouped_org_by_container.get(dest_container_id, {})
            dest_site = (group_meta.get("site") or "").strip()
            if dest_site and normalize_label(dest_site) != normalize_label(source_station.name):
                skipped_reasons["destination_site_mismatch_for_container_bootstrap"] += 1
                return None

            hall_label = hall_label_from_group(group_meta.get("container_group"))
            if not hall_label:
                hall_label = source_hall.name if source_hall else f"{source_station.name} Hall"
            hall_label = hall_label[:100]
            hall_key = (source_station.id, normalize_label(hall_label))
            hall = hall_by_station_group.get(hall_key)
            if hall is None:
                hall = Hall.objects.filter(
                    freshwater_station=source_station,
                    name=hall_label,
                ).first()
                if hall is None:
                    hall = Hall(
                        name=hall_label,
                        freshwater_station=source_station,
                        description="Auto-created by transfer migration for destination container bootstrap",
                        active=True,
                    )
                    save_with_history(hall, user=history_user, reason=history_reason)
                hall_by_station_group[hall_key] = hall

            dest_container_meta = container_info_by_id.get(dest_container_id, {})
            dest_container_name = (dest_container_meta.get("name") or "").strip()

            container = None
            if dest_container_name:
                container = (
                    Container.objects.filter(
                        hall__freshwater_station=source_station,
                        name=dest_container_name,
                    )
                    .order_by("id")
                    .first()
                )

            if container is None:
                container = Container(
                    name=(dest_container_name or f"FT-{dest_container_id[:8]}")[:100],
                    container_type=source_container.container_type,
                    hall=hall,
                    hierarchy_role=(source_container.hierarchy_role or "HOLDING"),
                    volume_m3=(source_container.volume_m3 or Decimal("1.00")),
                    max_biomass_kg=(source_container.max_biomass_kg or Decimal("1.00")),
                    feed_recommendations_enabled=source_container.feed_recommendations_enabled,
                    active=True,
                )
                save_with_history(container, user=history_user, reason=history_reason)

            container_map, _ = ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="Containers",
                source_identifier=dest_container_id,
                defaults={
                    "target_app_label": container._meta.app_label,
                    "target_model": container._meta.model_name,
                    "target_object_id": container.pk,
                    "metadata": {
                        "created_for_transfer_destination_bootstrap": True,
                        "component_key": component_key,
                        "site": group_meta.get("site"),
                        "container_group": group_meta.get("container_group"),
                        "container_name": dest_container_name,
                        "org_unit_id": dest_container_meta.get("org_unit_id"),
                    },
                },
            )
            container_external_map_by_source[dest_container_id] = container_map
            container_by_source[dest_container_id] = container
            return container

        def resolve_destination_assignment(
            *,
            dest_pop: str,
            op_date,
            dest_stage: LifeCycleStage,
            source_assignment: BatchContainerAssignment,
        ) -> BatchContainerAssignment | None:
            nonlocal created_dest_assignments, reused_dest_assignments
            nonlocal canonicalized_dest_assignments
            existing = assignment_by_pop.get(dest_pop)
            if existing:
                canonical = canonicalize_same_stage_superseded_assignment(
                    existing,
                    batch=batch,
                    dest_stage=dest_stage,
                    op_date=op_date,
                )
                if canonical is not existing:
                    canonicalized_dest_assignments += 1
                    assignment_by_pop[dest_pop] = canonical
                return canonical

            scoped_identifier = f"{component_key}:{dest_pop}"
            scoped_map = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model=DEST_ASSIGNMENT_SOURCE_MODEL,
                source_identifier=scoped_identifier,
            ).first()
            if scoped_map:
                assignment = BatchContainerAssignment.objects.filter(pk=scoped_map.target_object_id).first()
                if assignment:
                    canonical = canonicalize_same_stage_superseded_assignment(
                        assignment,
                        batch=batch,
                        dest_stage=dest_stage,
                        op_date=op_date,
                    )
                    if canonical is not assignment:
                        canonicalized_dest_assignments += 1
                        scoped_map.target_object_id = canonical.pk
                        scoped_map.metadata = {
                            **(scoped_map.metadata or {}),
                            "canonicalized_same_stage_superseded_destination": True,
                            "original_target_object_id": assignment.pk,
                        }
                        scoped_map.save(update_fields=["target_object_id", "metadata", "updated_at"])
                        assignment = canonical
                    assignment_by_pop[dest_pop] = assignment
                    dest_assignment_ids_for_sync.add(assignment.id)
                    return assignment

            mapped_assignment = get_external_map("Populations", dest_pop, component_key=component_key)
            if mapped_assignment:
                assignment = BatchContainerAssignment.objects.filter(pk=mapped_assignment.target_object_id).first()
                if assignment:
                    canonical = canonicalize_same_stage_superseded_assignment(
                        assignment,
                        batch=batch,
                        dest_stage=dest_stage,
                        op_date=op_date,
                    )
                    if canonical is not assignment:
                        canonicalized_dest_assignments += 1
                        assignment = canonical
                    assignment_by_pop[dest_pop] = assignment
                    return assignment

            dest_container_id = (population_container_by_id.get(dest_pop) or "").strip()
            if not dest_container_id:
                skipped_reasons["missing_destination_container_id"] += 1
                return None

            if dest_container_id not in container_external_map_by_source:
                container_external_map_by_source[dest_container_id] = get_external_map("Containers", dest_container_id)
            container_map = container_external_map_by_source.get(dest_container_id)
            if not container_map:
                container = bootstrap_destination_container(
                    dest_container_id=dest_container_id,
                    source_assignment=source_assignment,
                )
                if container is None:
                    skipped_reasons["unmapped_destination_container"] += 1
                    return None
            else:
                container = container_by_source.get(dest_container_id)
                if container is None:
                    from apps.infrastructure.models import Container

                    container = Container.objects.filter(pk=container_map.target_object_id).first()
                    container_by_source[dest_container_id] = container
            if container is None:
                container = bootstrap_destination_container(
                    dest_container_id=dest_container_id,
                    source_assignment=source_assignment,
                )
                if container is None:
                    skipped_reasons["missing_destination_container_record"] += 1
                    return None

            assignment = (
                BatchContainerAssignment.objects.filter(batch=batch, container=container, is_active=True)
                .order_by("assignment_date", "id")
                .first()
            )
            if assignment is None:
                assignment = BatchContainerAssignment(
                    batch=batch,
                    container=container,
                    lifecycle_stage=dest_stage,
                    population_count=0,
                    avg_weight_g=source_assignment.avg_weight_g,
                    biomass_kg=Decimal("0.00"),
                    assignment_date=op_date,
                    is_active=True,
                    notes=(
                        "FishTalk migration synthetic destination assignment for "
                        f"population {dest_pop}"
                    ),
                )
                save_with_history(assignment, user=history_user, reason=history_reason)
                created_dest_assignments += 1
            else:
                if assignment.lifecycle_stage_id != dest_stage.id and int(assignment.population_count or 0) <= 0:
                    assignment.lifecycle_stage = dest_stage
                    save_with_history(assignment, user=history_user, reason=history_reason)
                reused_dest_assignments += 1

            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model=DEST_ASSIGNMENT_SOURCE_MODEL,
                source_identifier=scoped_identifier,
                defaults={
                    "target_app_label": assignment._meta.app_label,
                    "target_model": assignment._meta.model_name,
                    "target_object_id": assignment.pk,
                    "metadata": {
                        "component_key": component_key,
                        "population_id": dest_pop,
                        "container_id": dest_container_id,
                        "created_for_transfer_migration": True,
                    },
                },
            )
            canonical = canonicalize_same_stage_superseded_assignment(
                assignment,
                batch=batch,
                dest_stage=dest_stage,
                op_date=op_date,
            )
            if canonical is not assignment:
                canonicalized_dest_assignments += 1
                assignment = canonical
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model=DEST_ASSIGNMENT_SOURCE_MODEL,
                    source_identifier=scoped_identifier,
                    defaults={
                        "target_app_label": assignment._meta.app_label,
                        "target_model": assignment._meta.model_name,
                        "target_object_id": assignment.pk,
                        "metadata": {
                            "component_key": component_key,
                            "population_id": dest_pop,
                            "container_id": dest_container_id,
                            "created_for_transfer_migration": True,
                            "canonicalized_same_stage_superseded_destination": True,
                        },
                    },
                )
            assignment_by_pop[dest_pop] = assignment
            dest_assignment_ids_for_sync.add(assignment.id)
            return assignment

        workflow_groups: dict[str, dict] = {}
        for row in transfer_rows:
            op_id = (row.get("OperationID") or "").strip()
            src = (row.get("SourcePop") or "").strip()
            dst = (row.get("DestPop") or "").strip()
            if not op_id or not src or not dst:
                skipped += 1
                skipped_reasons["missing_operation_or_population"] += 1
                continue

            op_time = parse_dt(row.get("OperationStartTime") or "")
            if op_time is None:
                skipped += 1
                skipped_reasons["missing_operation_start_time"] += 1
                continue
            op_time = ensure_aware(op_time)
            op_date = op_time.date()

            source_assignment = assignment_by_pop.get(src)
            if source_assignment is None:
                skipped += 1
                skipped_reasons["missing_source_assignment"] += 1
                continue

            source_stage = source_assignment.lifecycle_stage or fallback_stage
            dest_stage = source_stage
            workflow_type = "CONTAINER_REDISTRIBUTION"
            station_site = ""

            if args.workflow_grouping == "stage-bucket":
                src_container_id = (population_container_by_id.get(src) or "").strip()
                dst_container_id = (population_container_by_id.get(dst) or "").strip()
                src_group = grouped_org_by_container.get(src_container_id, {})
                dst_group = grouped_org_by_container.get(dst_container_id, {})
                src_site = (src_group.get("site") or "").strip()
                dst_site = (dst_group.get("site") or "").strip()
                if not src_site or not dst_site or src_site != dst_site:
                    skipped += 1
                    skipped_reasons["station_mismatch_or_missing"] += 1
                    continue
                src_stage_name = stage_from_hall(src_site, src_group.get("container_group"))
                dst_stage_name = stage_from_hall(dst_site, dst_group.get("container_group"))
                if not src_stage_name or not dst_stage_name:
                    skipped += 1
                    skipped_reasons["missing_hall_stage_mapping"] += 1
                    continue
                mapped_source_stage = lifecycle_stage_by_name.get(src_stage_name)
                mapped_dest_stage = lifecycle_stage_by_name.get(dst_stage_name)
                if mapped_source_stage is None or mapped_dest_stage is None:
                    skipped += 1
                    skipped_reasons["missing_lifecycle_stage_master"] += 1
                    continue
                source_stage = mapped_source_stage
                dest_stage = mapped_dest_stage
                station_site = src_site
                workflow_type = (
                    "CONTAINER_REDISTRIBUTION"
                    if src_stage_name == dst_stage_name
                    else "LIFECYCLE_TRANSITION"
                )
                workflow_identifier = build_stage_bucket_identifier(
                    component_key=component_key,
                    station_site=station_site,
                    workflow_type=workflow_type,
                    source_stage_name=source_stage.name,
                    dest_stage_name=dest_stage.name,
                )
                workflow_source_model = STAGE_BUCKET_WORKFLOW_SOURCE_MODEL
                workflow_source_identifier = workflow_identifier
            else:
                source_stage_name = stage_at(stage_events.get(src, []), op_time)
                dest_stage_name = stage_at(stage_events.get(dst, []), op_time)
                if source_stage_name:
                    mapped_source_name = fishtalk_stage_to_aquamind(source_stage_name)
                    if mapped_source_name and mapped_source_name in lifecycle_stage_by_name:
                        source_stage = lifecycle_stage_by_name[mapped_source_name]
                if dest_stage_name:
                    mapped_dest_name = fishtalk_stage_to_aquamind(dest_stage_name)
                    if mapped_dest_name and mapped_dest_name in lifecycle_stage_by_name:
                        dest_stage = lifecycle_stage_by_name[mapped_dest_name]
                if dest_stage.id != source_stage.id:
                    workflow_type = "LIFECYCLE_TRANSITION"
                workflow_source_model = "TransferOperation"
                workflow_source_identifier = op_id

            dest_assignment = assignment_by_pop.get(dst)
            if dest_assignment is not None:
                canonical = canonicalize_same_stage_superseded_assignment(
                    dest_assignment,
                    batch=batch,
                    dest_stage=dest_stage,
                    op_date=op_date,
                )
                if canonical is not dest_assignment:
                    canonicalized_dest_assignments += 1
                    assignment_by_pop[dst] = canonical
                    dest_assignment = canonical
            source_assignment_count = int(source_assignment.population_count or 0)
            if (
                args.workflow_grouping == "stage-bucket"
                and source_assignment.id not in source_assignment_ids_stage_synced
                and source_assignment.lifecycle_stage_id != source_stage.id
                and (
                    source_assignment.departure_date is not None
                    or source_assignment_count <= 0
                )
            ):
                source_assignment.lifecycle_stage = source_stage
                save_with_history(source_assignment, user=history_user, reason=history_reason)
                synced_source_stage_assignments += 1
                source_assignment_ids_stage_synced.add(source_assignment.id)

            if dest_assignment is None:
                dest_assignment = resolve_destination_assignment(
                    dest_pop=dst,
                    op_date=op_date,
                    dest_stage=dest_stage,
                    source_assignment=source_assignment,
                )
            if dest_assignment is None:
                skipped += 1
                skipped_reasons["missing_destination_assignment"] += 1
                continue
            if source_assignment.id == dest_assignment.id:
                skipped += 1
                skipped_reasons["self_loop_assignment_edge"] += 1
                continue

            workflow_group = workflow_groups.setdefault(
                workflow_source_identifier,
                {
                    "source_model": workflow_source_model,
                    "source_identifier": workflow_source_identifier,
                    "workflow_type": workflow_type,
                    "source_stage": source_stage,
                    "dest_stage": dest_stage,
                    "station_site": station_site,
                    "start_date": op_date,
                    "end_date": op_date,
                    "edges": [],
                },
            )
            workflow_group["start_date"] = min(workflow_group["start_date"], op_date)
            workflow_group["end_date"] = max(workflow_group["end_date"], op_date)
            workflow_group["edges"].append(
                {
                    "operation_id": op_id,
                    "operation_time": op_time,
                    "operation_date": op_date,
                    "source_pop": src,
                    "dest_pop": dst,
                    "source_assignment": source_assignment,
                    "dest_assignment": dest_assignment,
                    "share_count": parse_ratio(row.get("ShareCountForward")),
                    "share_biomass": parse_ratio(row.get("ShareBiomassForward")),
                }
            )

        for workflow_source_identifier, workflow_group in workflow_groups.items():
            workflow_source_model = workflow_group["source_model"]
            source_stage = workflow_group["source_stage"]
            dest_stage = workflow_group["dest_stage"]
            workflow_type = workflow_group["workflow_type"]
            start_date = workflow_group["start_date"]
            end_date = workflow_group["end_date"]

            wf_map = get_external_map(workflow_source_model, workflow_source_identifier)
            workflow = None
            if wf_map:
                workflow = BatchTransferWorkflow.objects.filter(pk=wf_map.target_object_id).first()

            if workflow:
                workflow.planned_start_date = start_date
                workflow.planned_completion_date = end_date
                workflow.source_lifecycle_stage = source_stage
                workflow.dest_lifecycle_stage = dest_stage
                workflow.workflow_type = workflow_type
                save_with_history(workflow, user=history_user, reason=history_reason)
                updated_wf += 1
            else:
                if workflow_source_model == STAGE_BUCKET_WORKFLOW_SOURCE_MODEL:
                    wf_number = build_stage_bucket_workflow_number(workflow_source_identifier)
                    notes = (
                        f"FishTalk stage-bucket transfer workflow; site={workflow_group['station_site'] or 'UNKNOWN'}; "
                        f"source_stage={source_stage.name}; dest_stage={dest_stage.name}"
                    )
                else:
                    op_id = workflow_source_identifier
                    wf_number = f"FT-TRF-{start_date.strftime('%Y%m%d')}-{op_id[:8]}"[:50]
                    notes = f"FishTalk OperationID={op_id}"
                workflow = BatchTransferWorkflow(
                    workflow_number=wf_number,
                    batch=batch,
                    workflow_type=workflow_type,
                    source_lifecycle_stage=source_stage,
                    dest_lifecycle_stage=dest_stage,
                    status="DRAFT",
                    planned_start_date=start_date,
                    planned_completion_date=end_date,
                    initiated_by=user,
                    notes=notes,
                )
                save_with_history(workflow, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model=workflow_source_model,
                    source_identifier=str(workflow_source_identifier),
                    defaults={
                        "target_app_label": workflow._meta.app_label,
                        "target_model": workflow._meta.model_name,
                        "target_object_id": workflow.pk,
                        "metadata": {
                            "workflow_grouping": args.workflow_grouping,
                            "edge_scope": args.transfer_edge_scope,
                            "station_site": workflow_group["station_site"],
                            "source_stage": source_stage.name,
                            "dest_stage": dest_stage.name,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                    },
                )
                created_wf += 1

            workflow_ids_for_sync.add(workflow.id)

            edges_sorted = sorted(
                workflow_group["edges"],
                key=lambda edge: (
                    edge["operation_time"],
                    edge["operation_id"],
                    edge["source_pop"],
                    edge["dest_pop"],
                ),
            )
            edges_by_source_operation: dict[tuple[str, str], list[dict]] = defaultdict(list)
            for edge in edges_sorted:
                edges_by_source_operation[(edge["operation_id"], edge["source_pop"])].append(edge)

            for (op_id, src), grouped_edges in edges_by_source_operation.items():
                op_time = grouped_edges[0]["operation_time"]
                if args.use_csv:
                    src_count_before, src_biomass_before = lookup_status_snapshot_from_index(
                        status_index, population_id=src, at_time=op_time
                    )
                else:
                    src_count_before, src_biomass_before = lookup_status_snapshot(
                        extractor, population_id=src, at_time=op_time
                    )

                ratios = [edge["share_count"] or edge["share_biomass"] for edge in grouped_edges]
                allocated_counts = allocate_transfer_counts(src_count_before, ratios)
                allocated_biomass = allocate_transfer_biomass(
                    src_biomass_before,
                    src_count_before,
                    allocated_counts,
                )

                for edge, est_count, est_biomass in zip(grouped_edges, allocated_counts, allocated_biomass):
                    edge["source_population_before_estimate"] = max(src_count_before, est_count)
                    edge["transferred_count_estimate"] = est_count
                    edge["transferred_biomass_estimate"] = est_biomass

            next_action_number = (
                workflow.actions.aggregate(max_action_number=Max("action_number"))["max_action_number"]
                or 0
            ) + 1

            for edge in edges_sorted:
                op_id = edge["operation_id"]
                src = edge["source_pop"]
                dst = edge["dest_pop"]
                op_time = edge["operation_time"]
                op_date = edge["operation_date"]
                source_assignment = edge["source_assignment"]
                dest_assignment = edge["dest_assignment"]
                source_assignment_ids_for_count_sync.add(source_assignment.id)

                src_count_before = int(edge.get("source_population_before_estimate") or 0)
                est_count = int(edge.get("transferred_count_estimate") or 0)
                est_biomass = edge.get("transferred_biomass_estimate") or Decimal("0.00")

                if est_count <= 0:
                    skipped += 1
                    skipped_reasons["zero_estimated_transfer"] += 1
                    continue

                action_identifier = f"{op_id}:{src}:{dst}"
                action_map = get_external_map("PublicTransferEdge", action_identifier)
                defaults = {
                    "workflow": workflow,
                    "source_assignment": source_assignment,
                    "dest_assignment": dest_assignment,
                    "source_population_before": max(src_count_before, est_count),
                    "transferred_count": est_count,
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": est_biomass,
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "created_via": "PLANNED",
                    "leg_type": None,
                    "planned_date": op_date,
                    "actual_execution_date": op_date,
                    "executed_at": op_time,
                    "transfer_method": None,
                    "notes": (
                        f"FishTalk OperationID={op_id}; share_count={edge['share_count']}; "
                        f"share_biomass={edge['share_biomass']}; grouping={args.workflow_grouping}"
                    ),
                }

                if action_map:
                    action = TransferAction.objects.filter(pk=action_map.target_object_id).first()
                    if not action:
                        action_map = None
                if action_map:
                    action = TransferAction.objects.get(pk=action_map.target_object_id)
                    for k, v in defaults.items():
                        setattr(action, k, v)
                    if not action.action_number:
                        action.action_number = next_action_number
                        next_action_number += 1
                    save_with_history(action, user=history_user, reason=history_reason)
                    updated_actions += 1
                else:
                    while TransferAction.objects.filter(workflow=workflow, action_number=next_action_number).exists():
                        next_action_number += 1
                    defaults["action_number"] = next_action_number
                    next_action_number += 1
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
                            "metadata": {
                                "operation_id": op_id,
                                "source_pop": src,
                                "dest_pop": dst,
                                "workflow_grouping": args.workflow_grouping,
                            },
                        },
                    )
                    created_actions += 1

            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = (
                Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            )
            workflow.actual_start_date = start_date
            workflow.actual_completion_date = end_date
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            workflow.completed_by = user if workflow.total_actions_planned else workflow.completed_by
            save_with_history(workflow, user=history_user, reason=history_reason)
            if not args.allow_dynamic_runtime_workflows:
                if enforce_static_workflow_for_migration(
                    workflow,
                    history_user=history_user,
                    history_reason=history_reason,
                ):
                    forced_static_workflows += 1
            workflow.recalculate_totals()

        for assignment_id in sorted(dest_assignment_ids_for_sync):
            if not workflow_ids_for_sync:
                break
            assignment = BatchContainerAssignment.objects.filter(pk=assignment_id).first()
            if assignment is None:
                continue
            aggregates = TransferAction.objects.filter(
                workflow_id__in=workflow_ids_for_sync,
                dest_assignment_id=assignment_id,
                status="COMPLETED",
            ).aggregate(
                total_count=Sum("transferred_count"),
                total_biomass=Sum("transferred_biomass_kg"),
                first_transfer_date=Min("actual_execution_date"),
            )
            target_count = int(aggregates.get("total_count") or 0)
            target_biomass = (aggregates.get("total_biomass") or Decimal("0.00")).quantize(Decimal("0.01"))
            target_start = aggregates.get("first_transfer_date") or assignment.assignment_date

            current_count = int(assignment.population_count or 0)
            current_biomass = (assignment.biomass_kg or Decimal("0.00")).quantize(Decimal("0.01"))
            changed = False
            if current_count != target_count:
                assignment.population_count = target_count
                changed = True
            if current_biomass != target_biomass:
                assignment.biomass_kg = target_biomass
                changed = True
            if assignment.assignment_date != target_start:
                assignment.assignment_date = target_start
                changed = True
            if not assignment.is_active:
                assignment.is_active = True
                changed = True
            if assignment.departure_date is not None:
                assignment.departure_date = None
                changed = True
            if changed:
                save_with_history(assignment, user=history_user, reason=history_reason)
                synced_dest_assignments += 1

        for assignment_id in sorted(source_assignment_ids_for_count_sync):
            if not workflow_ids_for_sync:
                break
            assignment = BatchContainerAssignment.objects.filter(pk=assignment_id).first()
            if assignment is None:
                continue
            if assignment.is_active or assignment.departure_date is None:
                continue
            if int(assignment.population_count or 0) > 0:
                continue

            aggregates = TransferAction.objects.filter(
                workflow_id__in=workflow_ids_for_sync,
                source_assignment_id=assignment_id,
                status="COMPLETED",
            ).aggregate(
                max_source_before=Max("source_population_before"),
                total_transferred=Sum("transferred_count"),
                total_transferred_biomass=Sum("transferred_biomass_kg"),
            )
            target_count = int(aggregates.get("max_source_before") or 0)
            if target_count <= 0:
                continue

            target_biomass = (assignment.biomass_kg or Decimal("0.00")).quantize(Decimal("0.01"))
            if target_biomass <= Decimal("0.00"):
                total_transferred = int(aggregates.get("total_transferred") or 0)
                total_transferred_biomass = (
                    aggregates.get("total_transferred_biomass") or Decimal("0.00")
                ).quantize(Decimal("0.01"))
                if total_transferred > 0 and total_transferred_biomass > Decimal("0.00"):
                    avg_weight_g = (
                        (total_transferred_biomass * Decimal("1000")) / Decimal(total_transferred)
                    ).quantize(Decimal("0.00001"))
                    target_biomass = (
                        (Decimal(target_count) * avg_weight_g) / Decimal("1000")
                    ).quantize(Decimal("0.01"))
                elif assignment.avg_weight_g and assignment.avg_weight_g > Decimal("0.00"):
                    target_biomass = (
                        (Decimal(target_count) * assignment.avg_weight_g) / Decimal("1000")
                    ).quantize(Decimal("0.01"))

            assignment.population_count = target_count
            assignment.biomass_kg = target_biomass
            save_with_history(assignment, user=history_user, reason=history_reason)
            synced_source_count_assignments += 1

        stage_assignments: dict[str, list[BatchContainerAssignment]] = {}
        if not args.skip_synthetic_stage_transitions:
            for assignment in batch.batch_assignments.select_related("lifecycle_stage"):
                if assignment.lifecycle_stage and assignment.lifecycle_stage.name in STAGE_INDEX:
                    stage_assignments.setdefault(assignment.lifecycle_stage.name, []).append(assignment)

        stage_start_dates: dict[str, datetime.date] = {}
        for stage_name, assignments in stage_assignments.items():
            stage_start_dates[stage_name] = min(a.assignment_date for a in assignments)

        ordered_stages = [name for name in STAGE_ORDER if name in stage_start_dates]
        transitions_by_pair = {}
        for idx in range(1, len(ordered_stages)):
            from_stage = ordered_stages[idx - 1]
            to_stage = ordered_stages[idx]
            transitions_by_pair[(from_stage, to_stage)] = list(stage_assignments.get(to_stage, []))

        for (from_stage_name, to_stage_name), transitions in transitions_by_pair.items():
            source_stage = LifeCycleStage.objects.filter(name=from_stage_name).first()
            dest_stage = LifeCycleStage.objects.filter(name=to_stage_name).first()
            if not source_stage or not dest_stage:
                skipped_stage += len(transitions)
                continue

            if not transitions:
                continue

            transition_times = [ensure_aware(datetime.combine(t.assignment_date, datetime.min.time())) for t in transitions]
            min_time = min(transition_times)
            max_time = max(transition_times)
            op_date = min_time.date()

            transition_identifier = f"{component_key}:{from_stage_name}:{to_stage_name}"
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
                planned_start_date=min_time.date(),
                planned_completion_date=max_time.date(),
                actual_start_date=min_time.date(),
                actual_completion_date=max_time.date(),
                initiated_by=user,
                completed_by=user,
                notes=f"FishTalk stage transition {from_stage_name}→{to_stage_name}; component={component_key}",
            )
            save_with_history(workflow, user=history_user, reason=history_reason)
            if not args.allow_dynamic_runtime_workflows:
                if enforce_static_workflow_for_migration(
                    workflow,
                    history_user=history_user,
                    history_reason=history_reason,
                ):
                    forced_static_workflows += 1
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationStageTransition",
                source_identifier=transition_identifier,
                defaults={
                    "target_app_label": workflow._meta.app_label,
                    "target_model": workflow._meta.model_name,
                    "target_object_id": workflow.pk,
                    "metadata": {
                        "from_stage": from_stage_name,
                        "to_stage": to_stage_name,
                        "transition_start": min_time.isoformat(),
                        "transition_end": max_time.isoformat(),
                    },
                },
            )
            created_stage_wf += 1

            action_number = 1
            from_assignments_sorted = sorted(
                stage_assignments.get(from_stage_name, []),
                key=lambda a: a.assignment_date,
            )
            for dest_assignment, transition_time in zip(transitions, transition_times):
                source_assignment = None
                for candidate in from_assignments_sorted:
                    if candidate.assignment_date <= dest_assignment.assignment_date:
                        source_assignment = candidate
                    else:
                        break
                if source_assignment is None:
                    source_assignment = dest_assignment

                count = dest_assignment.population_count or 0
                biomass = dest_assignment.biomass_kg or Decimal("0.00")
                action_identifier = f"{transition_identifier}:{dest_assignment.pk}"
                action_defaults = {
                    "workflow": workflow,
                    "action_number": action_number,
                    "source_assignment": source_assignment,
                    "dest_assignment": dest_assignment,
                    "source_population_before": max(count, 0),
                    "transferred_count": max(count, 0),
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": biomass,
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "created_via": "PLANNED",
                    "leg_type": None,
                    "planned_date": transition_time.date(),
                    "actual_execution_date": transition_time.date(),
                    "executed_at": transition_time,
                    "transfer_method": None,
                    "notes": (
                        f"FishTalk stage transition {from_stage_name}→{to_stage_name}; "
                        f"DestAssignment={dest_assignment.pk}"
                    ),
                }

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
                            "assignment_id": dest_assignment.pk,
                            "from_stage": from_stage_name,
                            "to_stage": to_stage_name,
                        },
                    },
                )
                created_stage_actions += 1
                action_number += 1

            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            save_with_history(workflow, user=history_user, reason=history_reason)
            workflow.recalculate_totals()

    if args.skip_synthetic_stage_transitions:
        print("Skipped synthetic PopulationStageTransition workflow/action generation (--skip-synthetic-stage-transitions).")

    print(
        f"Migrated transfers for component_key={component_key} into batch={batch.batch_number} "
        f"(workflows created={created_wf}, updated={updated_wf}, pruned={pruned_transfer_workflows}; "
        f"actions created={created_actions}, updated={updated_actions}, pruned={pruned_transfer_actions}, skipped={skipped}; "
        f"dest assignments created={created_dest_assignments}, reused={reused_dest_assignments}, "
        f"canonicalized={canonicalized_dest_assignments}, synced={synced_dest_assignments}; "
        f"source stage backfilled={synced_source_stage_assignments}, source count backfilled={synced_source_count_assignments}; "
        f"forced static workflows={forced_static_workflows}; "
        f"stage workflows created={created_stage_wf}, updated={updated_stage_wf}; "
        f"stage actions created={created_stage_actions}, updated={updated_stage_actions}, skipped={skipped_stage})"
    )
    if skipped_reasons:
        ordered = ", ".join(
            f"{reason}={count}"
            for reason, count in sorted(skipped_reasons.items(), key=lambda item: item[0])
        )
        print(f"Skipped transfer edge reasons: {ordered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
