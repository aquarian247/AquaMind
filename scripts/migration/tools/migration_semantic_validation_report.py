#!/usr/bin/env python3
# flake8: noqa
"""Compare FishTalk aggregates to AquaMind aggregates for a migrated component.

This is a semantic validation (not raw row counts) to verify that
domain totals and key metrics align after migration.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
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

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.batch.models import Batch, BatchComposition, MortalityEvent, GrowthSample, TransferAction
from apps.batch.models.assignment import BatchContainerAssignment
from apps.environmental.models import EnvironmentalReading
from apps.harvest.models import HarvestEvent, HarvestLot
from apps.health.models import JournalEntry, Treatment, LiceCount
from apps.inventory.models import FeedingEvent
from apps.migration_support.models import ExternalIdMap
from scripts.migration.tools.etl_loader import ETLDataLoader
from scripts.migration.tools.pilot_migrate_component import (
    DataSource as ComponentDataSource,
    build_conserved_population_counts,
)


REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"
STAGE_ORDER = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_INDEX = {name: idx for idx, name in enumerate(STAGE_ORDER)}
BRIDGE_MAX_DURATION_HOURS = 48
LINEAGE_FALLBACK_MAX_DEPTH = 14
DEFAULT_FISHGROUP_OUTLIER_ALLOWLIST: set[tuple[str, str, str]] = {
    ("23", "99", "23999.000"),
}


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


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    start_time: datetime
    end_time: datetime | None


@dataclass(frozen=True)
class PopulationMeta:
    fishgroup: str | None
    start_time: datetime | None
    end_time: datetime | None
    container_id: str | None


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


def load_population_metadata(csv_dir: str, population_ids: set[str]) -> dict[str, PopulationMeta]:
    if not population_ids:
        return {}
    path = Path(csv_dir) / "ext_populations.csv"
    if not path.exists():
        return {}

    metadata: dict[str, PopulationMeta] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id or pop_id not in population_ids:
                continue
            fishgroup_raw = (row.get("Fishgroup") or "").strip()
            metadata[pop_id] = PopulationMeta(
                fishgroup=fishgroup_raw or None,
                start_time=parse_dt(row.get("StartTime") or ""),
                end_time=parse_dt(row.get("EndTime") or ""),
                container_id=(row.get("ContainerID") or "").strip() or None,
            )
    return metadata


def parse_fishgroup_allowlist(raw_values: list[str] | None) -> set[tuple[str, str, str]]:
    patterns: set[tuple[str, str, str]] = set(DEFAULT_FISHGROUP_OUTLIER_ALLOWLIST)
    if not raw_values:
        return patterns

    for raw in raw_values:
        value = (raw or "").strip()
        if not value:
            continue
        parts = [part.strip().upper() for part in value.split("|")]
        if len(parts) != 3 or not all(parts):
            raise ValueError(
                "Invalid fishgroup allowlist entry. Expected format: "
                "'InputYear|InputNumber|Fishgroup' "
                f"(got '{raw}')."
            )
        patterns.add((parts[0], parts[1], parts[2]))
    return patterns


def build_expected_fishgroup(input_year: str, input_number: str, running_number: str) -> str | None:
    input_year_clean = (input_year or "").strip().upper()
    input_number_clean = (input_number or "").strip().upper()
    if not input_year_clean or not input_number_clean:
        return None

    try:
        running_number_int = int(round(float((running_number or "").strip())))
    except Exception:
        return None
    return f"{input_year_clean}{input_number_clean}.{running_number_int:04d}"


def summarize_fishgroup_format(
    *,
    scope_name: str,
    rows: list[dict],
    allowlist_patterns: set[tuple[str, str, str]],
    top_outlier_limit: int,
) -> dict:
    metrics = {
        "scope": scope_name,
        "rows_checked": 0,
        "matched_rows": 0,
        "matched_pct": 0.0,
        "outlier_rows": 0,
        "allowlisted_outlier_rows": 0,
        "non_allowlisted_outlier_rows": 0,
        "invalid_running_number_rows": 0,
        "top_non_allowlisted_outlier_patterns": [],
        "example_non_allowlisted_outliers": [],
    }
    outlier_pattern_counts: defaultdict[str, int] = defaultdict(int)
    non_allowlisted_examples: list[dict] = []

    for row in rows:
        metrics["rows_checked"] += 1
        input_year = (row.get("InputYear") or "").strip().upper()
        input_number = (row.get("InputNumber") or "").strip().upper()
        fishgroup = (row.get("Fishgroup") or "").strip().upper()
        running_number = (row.get("RunningNumber") or "").strip()
        population_id = (row.get("PopulationID") or "").strip()

        expected = build_expected_fishgroup(input_year, input_number, running_number)
        if expected is not None and fishgroup == expected:
            metrics["matched_rows"] += 1
            continue

        metrics["outlier_rows"] += 1
        if expected is None:
            metrics["invalid_running_number_rows"] += 1

        pattern_tuple = (input_year, input_number, fishgroup)
        pattern_label = f"{input_year}|{input_number}|{fishgroup}"
        if pattern_tuple in allowlist_patterns:
            metrics["allowlisted_outlier_rows"] += 1
            continue

        metrics["non_allowlisted_outlier_rows"] += 1
        outlier_pattern_counts[pattern_label] += 1
        if len(non_allowlisted_examples) < top_outlier_limit:
            non_allowlisted_examples.append(
                {
                    "population_id": population_id,
                    "fishgroup": fishgroup,
                    "input_year": input_year,
                    "input_number": input_number,
                    "running_number": running_number,
                    "expected": expected or "n/a",
                }
            )

    if metrics["rows_checked"] > 0:
        metrics["matched_pct"] = round(
            (metrics["matched_rows"] / metrics["rows_checked"]) * 100,
            2,
        )

    metrics["top_non_allowlisted_outlier_patterns"] = [
        {"pattern": pattern, "count": count}
        for pattern, count in sorted(
            outlier_pattern_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:top_outlier_limit]
    ]
    metrics["example_non_allowlisted_outliers"] = non_allowlisted_examples
    return metrics


def build_fishgroup_format_audit(
    *,
    csv_dir: str,
    population_ids: set[str],
    allowlist_patterns: set[tuple[str, str, str]],
    top_outlier_limit: int,
) -> dict:
    path = Path(csv_dir) / "ext_populations.csv"
    if not path.exists():
        return {
            "ext_populations_found": False,
            "allowlist_patterns": [
                f"{input_year}|{input_number}|{fishgroup}"
                for input_year, input_number, fishgroup in sorted(allowlist_patterns)
            ],
            "global": {},
            "component": {},
        }

    global_rows: list[dict] = []
    component_rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            global_rows.append(row)
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id and pop_id in population_ids:
                component_rows.append(row)

    return {
        "ext_populations_found": True,
        "allowlist_patterns": [
            f"{input_year}|{input_number}|{fishgroup}"
            for input_year, input_number, fishgroup in sorted(allowlist_patterns)
        ],
        "global": summarize_fishgroup_format(
            scope_name="global_extract",
            rows=global_rows,
            allowlist_patterns=allowlist_patterns,
            top_outlier_limit=top_outlier_limit,
        ),
        "component": summarize_fishgroup_format(
            scope_name="component_members",
            rows=component_rows,
            allowlist_patterns=allowlist_patterns,
            top_outlier_limit=top_outlier_limit,
        ),
    }


def build_subtransfer_indexes(
    sub_transfers: list[dict],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]], dict[str, list[dict]]]:
    incoming_by_dest_after: defaultdict[str, list[dict]] = defaultdict(list)
    incoming_by_source_after: defaultdict[str, list[dict]] = defaultdict(list)
    outgoing_by_pop: defaultdict[str, list[dict]] = defaultdict(list)

    for row in sub_transfers:
        dest_after = (row.get("DestPopAfter") or "").strip()
        source_after = (row.get("SourcePopAfter") or "").strip()
        dest_before = (row.get("DestPopBefore") or "").strip()
        src_before = (row.get("SourcePopBefore") or "").strip()
        if dest_after:
            incoming_by_dest_after[dest_after].append(row)
        if source_after:
            incoming_by_source_after[source_after].append(row)
        if dest_before:
            outgoing_by_pop[dest_before].append(row)
        if src_before:
            outgoing_by_pop[src_before].append(row)

    def row_time(row: dict) -> datetime:
        return parse_dt(row.get("OperationTime") or "") or datetime.min

    for rows in incoming_by_dest_after.values():
        rows.sort(key=row_time)
    for rows in incoming_by_source_after.values():
        rows.sort(key=row_time)
    for rows in outgoing_by_pop.values():
        rows.sort(key=row_time)
    return dict(incoming_by_dest_after), dict(incoming_by_source_after), dict(outgoing_by_pop)


def collect_lineage_graph_sources(
    *,
    dest_population_id: str,
    prev_stage: str | None,
    stage_by_pop: dict[str, str | None],
    incoming_by_dest_after: dict[str, list[dict]],
    incoming_by_source_after: dict[str, list[dict]],
    max_depth: int = LINEAGE_FALLBACK_MAX_DEPTH,
) -> set[str]:
    """Backtrace predecessors through explicit SubTransfer roles.

    Traversal uses only deterministic predecessor relations:
    - DestPopAfter <- SourcePopBefore
    - DestPopAfter <- DestPopBefore
    - SourcePopAfter <- SourcePopBefore
    """
    if prev_stage is None or max_depth <= 0:
        return set()

    source_populations: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(dest_population_id, 0)])
    seen_nodes: set[str] = {dest_population_id}

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue

        predecessor_nodes: set[str] = set()
        for row in incoming_by_dest_after.get(node, []):
            src_before = (row.get("SourcePopBefore") or "").strip()
            dst_before = (row.get("DestPopBefore") or "").strip()
            if src_before:
                predecessor_nodes.add(src_before)
            if dst_before:
                predecessor_nodes.add(dst_before)

        for row in incoming_by_source_after.get(node, []):
            src_before = (row.get("SourcePopBefore") or "").strip()
            if src_before:
                predecessor_nodes.add(src_before)

        for predecessor in predecessor_nodes:
            if predecessor in seen_nodes:
                continue
            seen_nodes.add(predecessor)

            if stage_by_pop.get(predecessor) == prev_stage:
                source_populations.add(predecessor)
                continue

            queue.append((predecessor, depth + 1))

    return source_populations


def classify_temporary_bridge_populations(
    *,
    population_ids: set[str],
    population_meta: dict[str, PopulationMeta],
    incoming_by_dest_after: dict[str, list[dict]],
    outgoing_by_pop: dict[str, list[dict]],
) -> set[str]:
    temporary_bridge_populations: set[str] = set()

    for pop_id in population_ids:
        meta = population_meta.get(pop_id)
        if not meta or not meta.start_time or not meta.end_time:
            continue

        lifetime_hours = (meta.end_time - meta.start_time).total_seconds() / 3600
        if lifetime_hours < 0 or lifetime_hours > BRIDGE_MAX_DURATION_HOURS:
            continue

        inbound_rows = incoming_by_dest_after.get(pop_id, [])
        outbound_rows = outgoing_by_pop.get(pop_id, [])
        if not inbound_rows or not outbound_rows:
            continue

        inbound_time = min(parse_dt(row.get("OperationTime") or "") or datetime.max for row in inbound_rows)
        outbound_time = min(parse_dt(row.get("OperationTime") or "") or datetime.max for row in outbound_rows)
        if inbound_time == datetime.max or outbound_time == datetime.max:
            continue
        if outbound_time < inbound_time:
            continue

        gap_hours = (outbound_time - inbound_time).total_seconds() / 3600
        if 0 <= gap_hours <= BRIDGE_MAX_DURATION_HOURS:
            temporary_bridge_populations.add(pop_id)

    return temporary_bridge_populations


def collect_transition_source_populations(
    *,
    dest_population_id: str,
    prev_stage: str | None,
    stage_by_pop: dict[str, str | None],
    incoming_by_dest_after: dict[str, list[dict]],
    incoming_by_source_after: dict[str, list[dict]],
    temporary_bridge_populations: set[str],
    lineage_fallback_max_depth: int = LINEAGE_FALLBACK_MAX_DEPTH,
    seen_destinations: set[str] | None = None,
) -> tuple[set[str], bool, bool]:
    if prev_stage is None:
        return set(), False, False
    if seen_destinations is None:
        seen_destinations = set()
    if dest_population_id in seen_destinations:
        return set(), False, False
    seen_destinations.add(dest_population_id)

    source_populations: set[str] = set()
    bridge_used = False
    lineage_graph_used = False
    for row in incoming_by_dest_after.get(dest_population_id, []):
        src_before = (row.get("SourcePopBefore") or "").strip()
        if src_before and stage_by_pop.get(src_before) == prev_stage:
            source_populations.add(src_before)

        # Some real stage-entry populations are created through a short-lived
        # intermediate DestPopBefore bridge population.
        bridge_dest_before = (row.get("DestPopBefore") or "").strip()
        if bridge_dest_before and bridge_dest_before in temporary_bridge_populations:
            bridge_used = True
            nested_sources, nested_bridge_used, nested_lineage_used = collect_transition_source_populations(
                dest_population_id=bridge_dest_before,
                prev_stage=prev_stage,
                stage_by_pop=stage_by_pop,
                incoming_by_dest_after=incoming_by_dest_after,
                incoming_by_source_after=incoming_by_source_after,
                temporary_bridge_populations=temporary_bridge_populations,
                lineage_fallback_max_depth=lineage_fallback_max_depth,
                seen_destinations=seen_destinations,
            )
            source_populations.update(nested_sources)
            bridge_used = bridge_used or nested_bridge_used
            lineage_graph_used = lineage_graph_used or nested_lineage_used

    if not source_populations:
        lineage_sources = collect_lineage_graph_sources(
            dest_population_id=dest_population_id,
            prev_stage=prev_stage,
            stage_by_pop=stage_by_pop,
            incoming_by_dest_after=incoming_by_dest_after,
            incoming_by_source_after=incoming_by_source_after,
            max_depth=max(to_int(lineage_fallback_max_depth), 0),
        )
        if lineage_sources:
            source_populations.update(lineage_sources)
            bridge_used = True
            lineage_graph_used = True

    return source_populations, bridge_used, lineage_graph_used


def to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def fmt(value: object, *, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, Decimal):
        quant = Decimal(f"1.{'0'*decimals}")
        return f"{value.quantize(quant)}"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def numeric_diff(left: object, right: object) -> str:
    if left is None or right is None:
        return "n/a"
    try:
        return fmt(to_decimal(left) - to_decimal(right))
    except Exception:
        return "n/a"


def harvest_sum(rows: list[dict], field: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        total += to_decimal(row.get(field) or 0)
    return total


def sum_int(rows: list[dict], field: str) -> int:
    total = 0
    for row in rows:
        raw = row.get(field)
        try:
            total += int(round(float(raw)))
        except Exception:
            continue
    return total


def to_int(value: object) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return 0


def resolve_effective_population_count(
    population_id: str,
    assignment_by_pop: dict[str, BatchContainerAssignment],
    conserved_counts: dict[str, int],
) -> int:
    assignment = assignment_by_pop.get(population_id)
    assignment_count = to_int(assignment.population_count if assignment else 0)
    if population_id in conserved_counts:
        conserved_count = to_int(conserved_counts.get(population_id) or 0)
        if conserved_count > 0:
            return conserved_count
    return assignment_count


def clamp_decimal(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    if value < low:
        return low
    if value > high:
        return high
    return value


def estimate_stage_outflow_to_external(
    population_ids: set[str],
    stage_by_pop: dict[str, str | None],
    data_source: ComponentDataSource,
) -> dict[str, int]:
    """Estimate outflow counts from component populations into external populations.

    Uses the same SubTransfers propagation logic as migration assignment conservation,
    seeded from Ext_Inputs_v2 counts. This is a conservative estimate.
    """
    if not population_ids:
        return {}

    input_counts = data_source.get_input_counts(sorted(population_ids))
    sub_transfers = data_source.get_subtransfers(population_ids)
    if not sub_transfers:
        return {}

    def row_time(row: dict) -> datetime:
        return parse_dt(row.get("OperationTime") or "") or datetime.min

    sub_transfers.sort(key=lambda r: (row_time(r), r.get("SubTransferID", "")))

    current_counts: dict[str, Decimal] = {}

    def seed_population(pop_id: str) -> Decimal:
        if pop_id in current_counts:
            return current_counts[pop_id]
        if pop_id in input_counts:
            count = Decimal(str(input_counts.get(pop_id) or 0))
        else:
            count = Decimal("0")
        current_counts[pop_id] = count
        return count

    for pop_id in input_counts:
        if pop_id in population_ids:
            seed_population(pop_id)

    outflow_by_stage: defaultdict[str, int] = defaultdict(int)

    for row in sub_transfers:
        src_before = (row.get("SourcePopBefore") or "").strip()
        src_after = (row.get("SourcePopAfter") or "").strip()
        dst_before = (row.get("DestPopBefore") or "").strip()
        dst_after = (row.get("DestPopAfter") or "").strip()
        share = clamp_decimal(to_decimal(row.get("ShareCountFwd") or 0), Decimal("0"), Decimal("1"))

        moved_count: Decimal | None = None

        if src_before in population_ids and src_before not in current_counts:
            seed_population(src_before)

        if src_before in current_counts:
            src_count = current_counts.get(src_before, Decimal("0"))
            moved_count = (src_count * share).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            remaining = src_count - moved_count
            if src_after and src_after in population_ids:
                current_counts[src_after] = remaining
            current_counts.pop(src_before, None)

        if dst_before in population_ids and dst_before not in current_counts:
            seed_population(dst_before)

        dest_before_count = None
        if dst_before in current_counts:
            dest_before_count = current_counts.pop(dst_before)

        if dst_after and dst_after in population_ids:
            dest_count = Decimal("0")
            if dest_before_count is not None:
                dest_count += dest_before_count
            if moved_count is not None:
                dest_count += moved_count
            current_counts[dst_after] = dest_count
        elif moved_count is not None and dst_after and dst_after not in population_ids:
            stage_name = stage_by_pop.get(src_before) or "Unknown"
            outflow_by_stage[stage_name] += int(moved_count)

    return dict(outflow_by_stage)


def load_population_container_context(
    *,
    loader: ETLDataLoader,
    population_ids: set[str],
) -> dict[str, dict[str, str]]:
    """Resolve population -> (container/site/prod_stage) metadata."""
    if not population_ids:
        return {}

    population_rows = loader.get_populations_by_ids(population_ids)
    container_ids = {
        (row.get("ContainerID") or "").strip()
        for row in population_rows
        if (row.get("ContainerID") or "").strip()
    }
    grouped_rows = loader.get_grouped_organisation_by_container_ids(container_ids)
    grouped_by_container: dict[str, dict[str, str]] = {}
    for row in grouped_rows:
        container_id = (row.get("ContainerID") or "").strip()
        if not container_id or container_id in grouped_by_container:
            continue
        grouped_by_container[container_id] = row

    context: dict[str, dict[str, str]] = {}
    for row in population_rows:
        population_id = (row.get("PopulationID") or "").strip()
        container_id = (row.get("ContainerID") or "").strip()
        grouped = grouped_by_container.get(container_id, {})
        context[population_id] = {
            "container_id": container_id,
            "site": (grouped.get("Site") or "").strip() or "Unknown",
            "site_group": (grouped.get("SiteGroup") or "").strip() or "Unknown",
            "prod_stage": (grouped.get("ProdStage") or "").strip() or "Unknown",
        }
    return context


def summarize_context_counts(
    *,
    context: dict[str, dict[str, str]],
    population_ids: set[str],
) -> dict:
    by_prod_stage: Counter[str] = Counter()
    by_site: Counter[str] = Counter()
    by_site_group: Counter[str] = Counter()
    marine_population_ids: list[str] = []
    for population_id in population_ids:
        meta = context.get(population_id) or {}
        prod_stage = (meta.get("prod_stage") or "Unknown").strip() or "Unknown"
        site = (meta.get("site") or "Unknown").strip() or "Unknown"
        site_group = (meta.get("site_group") or "Unknown").strip() or "Unknown"
        by_prod_stage[prod_stage] += 1
        by_site[site] += 1
        by_site_group[site_group] += 1
        if "MARINE" in prod_stage.upper():
            marine_population_ids.append(population_id)
    return {
        "population_count": len(population_ids),
        "marine_population_count": len(marine_population_ids),
        "marine_population_examples": sorted(marine_population_ids)[:10],
        "by_prod_stage": dict(sorted(by_prod_stage.items(), key=lambda item: (-item[1], item[0]))),
        "by_site": dict(sorted(by_site.items(), key=lambda item: (-item[1], item[0]))),
        "by_site_group": dict(sorted(by_site_group.items(), key=lambda item: (-item[1], item[0]))),
    }


def build_external_destination_evidence(
    *,
    population_ids: set[str],
    sub_transfers: list[dict],
    loader: ETLDataLoader,
) -> dict:
    """Classify outside-component destination evidence from SubTransfers.

    This is intentionally evidence-oriented:
    - direct edge counts by SubTransfers role (source/destination chains),
    - lineage reachability from component populations through SubTransfers graph,
    - destination metadata from grouped organisation (site/prod stage).
    """
    if not population_ids:
        return {}

    source_to_dest_external: list[tuple[str, str]] = []
    source_chain_external: list[tuple[str, str]] = []
    dest_chain_external: list[tuple[str, str]] = []
    external_direct_population_ids: set[str] = set()

    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for row in sub_transfers:
        src_before = (row.get("SourcePopBefore") or "").strip()
        src_after = (row.get("SourcePopAfter") or "").strip()
        dst_before = (row.get("DestPopBefore") or "").strip()
        dst_after = (row.get("DestPopAfter") or "").strip()

        if src_before:
            if src_after:
                adjacency[src_before].add(src_after)
            if dst_after:
                adjacency[src_before].add(dst_after)
        if dst_before and dst_after:
            adjacency[dst_before].add(dst_after)

        if src_before and dst_after and src_before in population_ids and dst_after not in population_ids:
            source_to_dest_external.append((src_before, dst_after))
            external_direct_population_ids.add(dst_after)
        if src_before and src_after and src_before in population_ids and src_after not in population_ids:
            source_chain_external.append((src_before, src_after))
            external_direct_population_ids.add(src_after)
        if dst_before and dst_after and dst_before in population_ids and dst_after not in population_ids:
            dest_chain_external.append((dst_before, dst_after))
            external_direct_population_ids.add(dst_after)

    context_direct = load_population_container_context(
        loader=loader,
        population_ids=external_direct_population_ids,
    )
    direct_population_summary = summarize_context_counts(
        context=context_direct,
        population_ids=external_direct_population_ids,
    )

    # Descendant reachability: component populations flowing through
    # SourcePopBefore -> {SourcePopAfter, DestPopAfter} and DestPopBefore -> DestPopAfter.
    reachable: set[str] = set(population_ids)
    queue: deque[str] = deque(population_ids)
    while queue:
        current = queue.popleft()
        for nxt in adjacency.get(current, set()):
            if nxt in reachable:
                continue
            reachable.add(nxt)
            queue.append(nxt)

    outside_descendants = reachable - population_ids
    context_descendants = load_population_container_context(
        loader=loader,
        population_ids=outside_descendants,
    )
    descendant_summary = summarize_context_counts(
        context=context_descendants,
        population_ids=outside_descendants,
    )

    def edge_context_counts(edges: list[tuple[str, str]]) -> dict:
        prod_counter: Counter[str] = Counter()
        site_counter: Counter[str] = Counter()
        for _, dst_pop in edges:
            meta = context_direct.get(dst_pop) or {}
            prod_counter[(meta.get("prod_stage") or "Unknown").strip() or "Unknown"] += 1
            site_counter[(meta.get("site") or "Unknown").strip() or "Unknown"] += 1
        return {
            "edge_count": len(edges),
            "by_prod_stage": dict(sorted(prod_counter.items(), key=lambda item: (-item[1], item[0]))),
            "by_site": dict(sorted(site_counter.items(), key=lambda item: (-item[1], item[0]))),
        }

    source_to_dest_summary = edge_context_counts(source_to_dest_external)
    source_chain_summary = edge_context_counts(source_chain_external)
    dest_chain_summary = edge_context_counts(dest_chain_external)

    marine_evidence = (
        direct_population_summary.get("marine_population_count", 0) > 0
        or descendant_summary.get("marine_population_count", 0) > 0
    )
    return {
        "direct_external_population_count": len(external_direct_population_ids),
        "source_to_dest_external": source_to_dest_summary,
        "source_chain_external": source_chain_summary,
        "dest_chain_external": dest_chain_summary,
        "direct_population_summary": direct_population_summary,
        "descendant_summary": descendant_summary,
        "marine_linkage_evidence": marine_evidence,
    }


def build_active_container_occupancy_evidence(
    *,
    assignments: list[BatchContainerAssignment],
    assignment_map_by_id: dict[int, ExternalIdMap],
    component_population_ids: set[str],
    loader: ETLDataLoader,
) -> dict:
    """Check latest non-zero holder per currently active migrated container assignment."""
    active_rows: list[dict] = []
    for assignment in assignments:
        if not assignment.is_active:
            continue
        mapping = assignment_map_by_id.get(assignment.id)
        if not mapping:
            continue
        metadata = mapping.metadata or {}
        source_container_id = (metadata.get("container_id") or "").strip()
        source_population_id = (mapping.source_identifier or "").strip()
        if not source_container_id or not source_population_id:
            continue
        active_rows.append(
            {
                "container_name": assignment.container.name if assignment.container_id else str(assignment.container_id),
                "source_container_id": source_container_id,
                "component_population_id": source_population_id,
            }
        )
    if not active_rows:
        return {}

    container_ids = {row["source_container_id"] for row in active_rows}
    all_populations = loader.get_all_populations()
    populations_by_container: defaultdict[str, set[str]] = defaultdict(set)
    for row in all_populations:
        container_id = (row.get("ContainerID") or "").strip()
        population_id = (row.get("PopulationID") or "").strip()
        if container_id in container_ids and population_id:
            populations_by_container[container_id].add(population_id)

    candidate_population_ids: set[str] = set()
    for population_ids in populations_by_container.values():
        candidate_population_ids.update(population_ids)
    if not candidate_population_ids:
        return {}

    latest_nonzero_by_population: dict[str, dict] = {}
    status_rows = loader.get_status_values_for_populations(candidate_population_ids)
    for row in status_rows:
        population_id = (row.get("PopulationID") or "").strip()
        status_time = (row.get("StatusTime") or "").strip()
        if not population_id or not status_time:
            continue
        try:
            status_count = float(row.get("CurrentCount") or 0)
        except Exception:
            status_count = 0
        try:
            status_biomass = float(row.get("CurrentBiomassKg") or 0)
        except Exception:
            status_biomass = 0
        if status_count <= 0 and status_biomass <= 0:
            continue
        current = latest_nonzero_by_population.get(population_id)
        if current is None or status_time > current["status_time"]:
            latest_nonzero_by_population[population_id] = {
                "status_time": status_time,
                "count": int(round(status_count)),
                "biomass_kg": status_biomass,
            }

    context = load_population_container_context(
        loader=loader,
        population_ids=candidate_population_ids,
    )
    occupancy_rows: list[dict] = []
    latest_holder_in_component_count = 0
    latest_holder_outside_component_count = 0
    unknown_holder_count = 0

    for active_row in sorted(active_rows, key=lambda row: row["container_name"]):
        container_id = active_row["source_container_id"]
        best_population_id: str | None = None
        best_status: dict | None = None
        for population_id in populations_by_container.get(container_id, set()):
            status = latest_nonzero_by_population.get(population_id)
            if not status:
                continue
            if best_status is None or status["status_time"] > best_status["status_time"]:
                best_status = status
                best_population_id = population_id

        if not best_population_id or not best_status:
            unknown_holder_count += 1
            occupancy_rows.append(
                {
                    "container_name": active_row["container_name"],
                    "source_container_id": container_id,
                    "component_population_id": active_row["component_population_id"],
                    "latest_population_id": None,
                    "latest_status_time": None,
                    "latest_count": None,
                    "latest_biomass_kg": None,
                    "latest_in_component": None,
                    "site": (context.get(active_row["component_population_id"], {}).get("site") or "Unknown"),
                    "prod_stage": (context.get(active_row["component_population_id"], {}).get("prod_stage") or "Unknown"),
                }
            )
            continue

        latest_in_component = best_population_id in component_population_ids
        if latest_in_component:
            latest_holder_in_component_count += 1
        else:
            latest_holder_outside_component_count += 1
        latest_context = context.get(best_population_id) or {}
        occupancy_rows.append(
            {
                "container_name": active_row["container_name"],
                "source_container_id": container_id,
                "component_population_id": active_row["component_population_id"],
                "latest_population_id": best_population_id,
                "latest_status_time": best_status["status_time"],
                "latest_count": best_status["count"],
                "latest_biomass_kg": round(best_status["biomass_kg"], 2),
                "latest_in_component": latest_in_component,
                "site": latest_context.get("site") or "Unknown",
                "prod_stage": latest_context.get("prod_stage") or "Unknown",
            }
        )

    return {
        "containers_checked": len(active_rows),
        "latest_holder_in_component_count": latest_holder_in_component_count,
        "latest_holder_outside_component_count": latest_holder_outside_component_count,
        "latest_holder_unknown_count": unknown_holder_count,
        "rows": occupancy_rows,
    }


def build_stage_sanity(
    *,
    batch: Batch,
    members: list[ComponentMember],
    population_ids: list[str],
    csv_dir: str,
    known_loss_count: int,
    stage_entry_window_days: int,
    lineage_fallback_max_depth: int = LINEAGE_FALLBACK_MAX_DEPTH,
) -> dict:
    stage_entry_window_days = max(to_int(stage_entry_window_days), 0)

    stage_rows_qs = (
        BatchContainerAssignment.objects.filter(batch=batch, lifecycle_stage__isnull=False)
        .values("lifecycle_stage__name", "lifecycle_stage__order")
        .annotate(
            population_total=Sum("population_count"),
            assignment_count=Count("id"),
            nonzero_assignment_count=Count("id", filter=Q(population_count__gt=0)),
        )
        .order_by("lifecycle_stage__order", "lifecycle_stage__name")
    )
    stage_rows = [
        {
            "stage": row.get("lifecycle_stage__name"),
            "order": row.get("lifecycle_stage__order") or STAGE_INDEX.get(row.get("lifecycle_stage__name"), 999),
            "population_total": to_int(row.get("population_total") or 0),
            "population_entry": 0,
            "entry_container_count": 0,
            "entry_date": None,
            "entry_window_end": None,
            "assignment_count": to_int(row.get("assignment_count") or 0),
            "nonzero_assignment_count": to_int(row.get("nonzero_assignment_count") or 0),
            "active_population_total": 0,
            "active_assignment_count": 0,
            "peak_concurrent_population": 0,
            "peak_concurrent_date": None,
            "full_to_entry_ratio": None,
            "full_to_peak_ratio": None,
            "entry_real_fishgroup_count": 0,
            "entry_bridge_excluded_count": 0,
            "entry_population_ids": [],
        }
        for row in stage_rows_qs
    ]
    stage_row_by_name = {row["stage"]: row for row in stage_rows}

    assignments = list(
        BatchContainerAssignment.objects.filter(batch=batch)
        .select_related("lifecycle_stage", "container")
        .only(
            "id",
            "lifecycle_stage__name",
            "lifecycle_stage__order",
            "assignment_date",
            "departure_date",
            "container_id",
            "container__name",
            "population_count",
            "is_active",
        )
    )
    assignment_maps = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="Populations",
        target_app_label="batch",
        target_model="batchcontainerassignment",
        target_object_id__in=[a.id for a in assignments],
    )
    assignment_map_by_id = {row.target_object_id: row for row in assignment_maps}
    pop_by_assignment_id = {row.target_object_id: row.source_identifier for row in assignment_maps}
    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    stage_by_pop: dict[str, str | None] = {}
    for assignment in assignments:
        pop_id = pop_by_assignment_id.get(assignment.id)
        if not pop_id:
            continue
        assignment_by_pop[pop_id] = assignment
        stage_by_pop[pop_id] = assignment.lifecycle_stage.name if assignment.lifecycle_stage else None

    member_by_pop = {member.population_id: member for member in members if member.population_id}
    component_data_source = ComponentDataSource(csv_dir=csv_dir)
    loader = ETLDataLoader(csv_dir)
    population_id_set = set(population_ids)
    sub_transfers = component_data_source.get_subtransfers(population_id_set)
    incoming_by_dest_after, incoming_by_source_after, outgoing_by_pop = build_subtransfer_indexes(sub_transfers)
    population_meta = load_population_metadata(csv_dir, population_id_set)
    temporary_bridge_populations = classify_temporary_bridge_populations(
        population_ids=population_id_set,
        population_meta=population_meta,
        incoming_by_dest_after=incoming_by_dest_after,
        outgoing_by_pop=outgoing_by_pop,
    )
    fishgroup_to_populations: defaultdict[str, set[str]] = defaultdict(set)
    for pop_id, meta in population_meta.items():
        if meta.fishgroup:
            fishgroup_to_populations[meta.fishgroup].add(pop_id)
    temporary_bridge_fishgroups = {
        fishgroup
        for fishgroup, grouped_populations in fishgroup_to_populations.items()
        if grouped_populations and all(pop in temporary_bridge_populations for pop in grouped_populations)
    }
    bridge_mixed_fishgroups = {
        fishgroup
        for fishgroup, grouped_populations in fishgroup_to_populations.items()
        if grouped_populations
        and any(pop in temporary_bridge_populations for pop in grouped_populations)
        and not all(pop in temporary_bridge_populations for pop in grouped_populations)
    }
    conserved_counts, superseded_same_stage = build_conserved_population_counts(
        members,
        component_data_source,
        stage_by_pop,
    )
    latest_status_time_by_pop = component_data_source.get_latest_status_by_population(population_ids)
    removal_counts_by_population = component_data_source.get_removal_counts_by_population(population_id_set)

    stage_nonzero_rows: defaultdict[str, list[dict]] = defaultdict(list)
    for assignment in assignments:
        if not assignment.lifecycle_stage or not assignment.assignment_date:
            continue
        assignment_count = to_int(assignment.population_count or 0)
        if assignment_count <= 0:
            continue
        stage_name = assignment.lifecycle_stage.name
        pop_id = pop_by_assignment_id.get(assignment.id)
        meta = population_meta.get(pop_id) if pop_id else None
        stage_nonzero_rows[stage_name].append(
            {
                "population_id": pop_id,
                "fishgroup": meta.fishgroup if meta else None,
                "assignment_date": assignment.assignment_date,
                "container_id": assignment.container_id,
                "population_count": assignment_count,
                "is_temporary_bridge": pop_id in temporary_bridge_populations if pop_id else False,
            }
        )

    real_stage_entry_fishgroups: set[str] = set()
    temporary_bridge_fishgroups_used: set[str] = set()
    for stage_name, rows in stage_nonzero_rows.items():
        stage_row = stage_row_by_name.get(stage_name)
        if not stage_row:
            continue

        all_stage_start = min(row["assignment_date"] for row in rows)
        real_rows = [row for row in rows if not row["is_temporary_bridge"]]
        selected_rows = real_rows if real_rows else rows
        stage_start = min(row["assignment_date"] for row in selected_rows)
        stage_window_end = stage_start + timedelta(days=stage_entry_window_days)

        window_rows = [row for row in selected_rows if row["assignment_date"] <= stage_window_end]
        bridge_rows_excluded = [
            row
            for row in rows
            if row["is_temporary_bridge"]
            and all_stage_start <= row["assignment_date"] <= stage_window_end
        ]
        max_row_by_container: dict[int, dict] = {}
        for row in window_rows:
            container_id = row["container_id"]
            current = max_row_by_container.get(container_id)
            if current is None or row["population_count"] > current["population_count"]:
                max_row_by_container[container_id] = row

        stage_entry_rows = list(max_row_by_container.values())
        stage_row["population_entry"] = sum(row["population_count"] for row in stage_entry_rows)
        stage_row["entry_container_count"] = len(stage_entry_rows)
        stage_row["entry_date"] = stage_start.isoformat()
        stage_row["entry_window_end"] = stage_window_end.isoformat()
        stage_row["entry_population_ids"] = sorted(
            {row["population_id"] for row in stage_entry_rows if row["population_id"]}
        )
        entry_fishgroups = {row["fishgroup"] for row in stage_entry_rows if row["fishgroup"]}
        stage_row["entry_real_fishgroup_count"] = len(entry_fishgroups)
        stage_row["entry_bridge_excluded_count"] = len(bridge_rows_excluded)

        real_stage_entry_fishgroups.update(entry_fishgroups)
        temporary_bridge_fishgroups_used.update(
            {row["fishgroup"] for row in bridge_rows_excluded if row["fishgroup"]}
        )

    max_interval_date = max(
        (
            assignment.departure_date
            or assignment.assignment_date
            for assignment in assignments
            if assignment.assignment_date
        ),
        default=None,
    )
    for assignment in assignments:
        if not assignment.lifecycle_stage:
            continue
        stage_name = assignment.lifecycle_stage.name
        stage_row = stage_row_by_name.get(stage_name)
        if not stage_row:
            continue
        assignment_count = to_int(assignment.population_count or 0)
        if assignment.is_active:
            stage_row["active_assignment_count"] += 1
            stage_row["active_population_total"] += max(assignment_count, 0)

    for stage_name, rows in stage_nonzero_rows.items():
        stage_row = stage_row_by_name.get(stage_name)
        if not stage_row:
            continue
        if not max_interval_date:
            continue

        interval_events: defaultdict = defaultdict(int)
        for row in rows:
            assignment_date = row.get("assignment_date")
            assignment_count = to_int(row.get("population_count") or 0)
            if not assignment_date or assignment_count <= 0:
                continue
            pop_id = row.get("population_id")
            assignment = assignment_by_pop.get(pop_id) if pop_id else None
            departure_date = assignment.departure_date if assignment else None
            interval_end_exclusive = (
                (departure_date + timedelta(days=1))
                if departure_date
                else (max_interval_date + timedelta(days=1))
            )
            interval_events[assignment_date] += assignment_count
            interval_events[interval_end_exclusive] -= assignment_count

        running_population = 0
        for event_date in sorted(interval_events):
            running_population += interval_events[event_date]
            if running_population > stage_row["peak_concurrent_population"]:
                stage_row["peak_concurrent_population"] = running_population
                stage_row["peak_concurrent_date"] = event_date.isoformat()

    for stage_row in stage_rows:
        full_population = to_int(stage_row.get("population_total") or 0)
        entry_population = to_int(stage_row.get("population_entry") or 0)
        peak_population = to_int(stage_row.get("peak_concurrent_population") or 0)
        stage_row["full_to_entry_ratio"] = (
            round(full_population / entry_population, 2)
            if entry_population > 0
            else None
        )
        stage_row["full_to_peak_ratio"] = (
            round(full_population / peak_population, 2)
            if peak_population > 0
            else None
        )

    mixed_rows = BatchComposition.objects.filter(mixed_batch=batch).count()

    transitions = []
    transition_lineage_graph_count = 0
    for idx in range(1, len(stage_rows)):
        prev_row = stage_rows[idx - 1]
        curr_row = stage_rows[idx]

        transition_basis = "entry_window"
        entry_window_reason = "no_entry_populations"
        source_population = to_int(prev_row["population_entry"])
        destination_population = to_int(curr_row["population_entry"])
        linked_source_populations: set[str] = set()
        linked_destination_populations: set[str] = set()
        entry_populations_with_external_sources: set[str] = set()
        bridge_used_for_transition = False
        lineage_graph_used_for_transition = False
        entry_populations = curr_row.get("entry_population_ids") or []
        if entry_populations:
            for dest_pop_id in entry_populations:
                has_external_source = False
                for incoming_row in incoming_by_dest_after.get(dest_pop_id, []):
                    source_before = (incoming_row.get("SourcePopBefore") or "").strip()
                    if source_before and source_before not in population_id_set:
                        has_external_source = True
                        break
                if not has_external_source:
                    for incoming_row in incoming_by_source_after.get(dest_pop_id, []):
                        source_before = (incoming_row.get("SourcePopBefore") or "").strip()
                        if source_before and source_before not in population_id_set:
                            has_external_source = True
                            break
                if has_external_source:
                    entry_populations_with_external_sources.add(dest_pop_id)

                source_populations, bridge_used, lineage_graph_used = collect_transition_source_populations(
                    dest_population_id=dest_pop_id,
                    prev_stage=prev_row["stage"],
                    stage_by_pop=stage_by_pop,
                    incoming_by_dest_after=incoming_by_dest_after,
                    incoming_by_source_after=incoming_by_source_after,
                    temporary_bridge_populations=temporary_bridge_populations,
                    lineage_fallback_max_depth=max(to_int(lineage_fallback_max_depth), 0),
                )
                if source_populations:
                    linked_destination_populations.add(dest_pop_id)
                    linked_source_populations.update(source_populations)
                    bridge_used_for_transition = bridge_used_for_transition or bridge_used
                    lineage_graph_used_for_transition = (
                        lineage_graph_used_for_transition or lineage_graph_used
                    )

        entry_population_count = len(entry_populations)
        has_full_entry_linkage = bool(entry_populations) and (
            len(linked_destination_populations) == len(entry_populations)
        )
        bridge_aware_eligible = has_full_entry_linkage

        if entry_populations:
            if not has_full_entry_linkage:
                entry_window_reason = "incomplete_linkage"
            elif not linked_source_populations:
                entry_window_reason = "no_linked_sources"
            elif not bridge_used_for_transition:
                entry_window_reason = "no_bridge_path"
            else:
                entry_window_reason = "bridge_aware"

        if linked_source_populations and has_full_entry_linkage:
            bridge_source_population = sum(
                resolve_effective_population_count(pop_id, assignment_by_pop, conserved_counts)
                for pop_id in linked_source_populations
            )
            bridge_destination_population = sum(
                resolve_effective_population_count(pop_id, assignment_by_pop, conserved_counts)
                for pop_id in entry_populations
            )
            bridge_delta = bridge_destination_population - bridge_source_population

            # If bridge-derived counts imply population growth without mixed-batch
            # evidence and some entry populations have external incoming sources,
            # treat linkage as incomplete for transition sanity gating.
            if (
                bridge_delta > 0
                and mixed_rows == 0
                and entry_populations_with_external_sources
            ):
                transition_basis = "entry_window"
                entry_window_reason = "incomplete_linkage"
            else:
                transition_basis = "fishgroup_bridge_aware"
                entry_window_reason = "bridge_aware" if bridge_used_for_transition else "direct_linkage"
                source_population = bridge_source_population
                destination_population = bridge_destination_population

        delta = destination_population - source_population
        transitions.append(
            {
                "from_stage": prev_row["stage"],
                "to_stage": curr_row["stage"],
                "from_population": source_population,
                "to_population": destination_population,
                "delta": delta,
                "drop": abs(delta) if delta < 0 else 0,
                "increase": delta if delta > 0 else 0,
                "unexplained_drop_vs_known_losses": max(0, abs(delta) - known_loss_count) if delta < 0 else 0,
                "basis": transition_basis,
                "entry_window_reason": entry_window_reason,
                "entry_population_count": entry_population_count,
                "entry_population_external_source_count": len(entry_populations_with_external_sources),
                "linked_source_population_count": len(linked_source_populations),
                "linked_destination_population_count": len(linked_destination_populations),
                "bridge_aware_eligible": bridge_aware_eligible,
                "lineage_graph_used": lineage_graph_used_for_transition,
            }
        )
        if transition_basis == "fishgroup_bridge_aware" and lineage_graph_used_for_transition:
            transition_lineage_graph_count += 1

    transition_basis_counts: defaultdict[str, int] = defaultdict(int)
    transition_entry_window_reason_counts: defaultdict[str, int] = defaultdict(int)
    for row in transitions:
        basis = (row.get("basis") or "entry_window").strip() or "entry_window"
        transition_basis_counts[basis] += 1
        reason = (row.get("entry_window_reason") or "unknown").strip() or "unknown"
        transition_entry_window_reason_counts[reason] += 1

    zero_assignment_total_count = 0
    zero_assignment_bridge_count = 0
    zero_assignment_population_ids: set[str] = set()
    for assignment in assignments:
        if to_int(assignment.population_count or 0) > 0:
            continue
        zero_assignment_total_count += 1
        pop_id = pop_by_assignment_id.get(assignment.id)
        if not pop_id:
            continue
        zero_assignment_population_ids.add(pop_id)
        if pop_id in temporary_bridge_populations:
            zero_assignment_bridge_count += 1

    # Same-stage superseded rows are intentionally zeroed by replay policy to
    # prevent double-counting in conservation chains. Track them separately from
    # true non-bridge anomalies.
    zero_assignment_superseded_population_ids = {
        pop_id
        for pop_id in zero_assignment_population_ids
        if pop_id in superseded_same_stage and pop_id not in temporary_bridge_populations
    }
    zero_assignment_superseded_count = len(zero_assignment_superseded_population_ids)

    # Some extract rows are ultra-short-lived orphan segments with zero conserved
    # count and no transfer edges/activity. Treat these as bridge-like zero rows.
    zero_assignment_orphan_short_population_ids: set[str] = set()
    candidate_zero_population_ids = (
        zero_assignment_population_ids
        - set(temporary_bridge_populations)
        - zero_assignment_superseded_population_ids
    )
    zero_assignment_activity_population_ids = (
        component_data_source.get_operational_activity_population_ids(candidate_zero_population_ids)
        if candidate_zero_population_ids
        else set()
    )
    for pop_id in candidate_zero_population_ids:
        if pop_id in zero_assignment_activity_population_ids:
            continue
        if to_int(conserved_counts.get(pop_id) or 0) != 0:
            continue
        meta = population_meta.get(pop_id)
        if not meta or not meta.start_time or not meta.end_time:
            continue
        lifetime_hours = (meta.end_time - meta.start_time).total_seconds() / 3600
        if lifetime_hours < 0 or lifetime_hours > BRIDGE_MAX_DURATION_HOURS:
            continue
        if incoming_by_dest_after.get(pop_id) or outgoing_by_pop.get(pop_id):
            continue
        zero_assignment_orphan_short_population_ids.add(pop_id)
    zero_assignment_orphan_short_count = len(zero_assignment_orphan_short_population_ids)

    # Some zero rows have no count evidence at all (no conserved baseline, no
    # status count, no known removals). These are deterministic empty segments
    # in source data and should not be treated as non-bridge regression failures.
    zero_assignment_no_count_evidence_population_ids: set[str] = set()

    # Some rows are fully depleted by known source removals (mortality/culling/
    # escapes) relative to conserved/status evidence and therefore end at zero
    # by construction.
    zero_assignment_depleted_known_loss_population_ids: set[str] = set()

    non_bridge_candidate_population_ids = (
        candidate_zero_population_ids - zero_assignment_orphan_short_population_ids
    )
    zero_assignment_status_count_by_pop: dict[str, int] = {}
    for pop_id in non_bridge_candidate_population_ids:
        assignment = assignment_by_pop.get(pop_id)
        member = member_by_pop.get(pop_id)
        if assignment is None or member is None:
            continue
        latest_status_time = latest_status_time_by_pop.get(pop_id)
        if member.end_time is None and latest_status_time:
            status_snapshot = component_data_source.get_status_snapshot(pop_id, latest_status_time)
        else:
            status_snapshot = component_data_source.get_status_snapshot(pop_id, member.start_time)
        zero_assignment_status_count_by_pop[pop_id] = to_int((status_snapshot or {}).get("CurrentCount") or 0)

    for pop_id in non_bridge_candidate_population_ids:
        conserved_count = to_int(conserved_counts.get(pop_id) or 0)
        status_count = to_int(zero_assignment_status_count_by_pop.get(pop_id) or 0)
        known_removals = to_int(removal_counts_by_population.get(pop_id) or 0)

        if conserved_count <= 0 and status_count <= 0 and known_removals <= 0:
            zero_assignment_no_count_evidence_population_ids.add(pop_id)
            continue

        if known_removals > 0:
            zero_assignment_depleted_known_loss_population_ids.add(pop_id)

    zero_assignment_no_count_evidence_count = len(zero_assignment_no_count_evidence_population_ids)
    zero_assignment_depleted_known_loss_count = len(zero_assignment_depleted_known_loss_population_ids)

    zero_assignment_non_bridge_count = max(
        0,
        zero_assignment_total_count
        - zero_assignment_bridge_count
        - zero_assignment_superseded_count
        - zero_assignment_orphan_short_count
        - zero_assignment_no_count_evidence_count
        - zero_assignment_depleted_known_loss_count,
    )

    status_fallback_stage_totals: defaultdict[str, int] = defaultdict(int)
    status_fallback_populations: list[dict] = []
    for pop_id in population_ids:
        assignment = assignment_by_pop.get(pop_id)
        member = member_by_pop.get(pop_id)
        if assignment is None or member is None:
            continue

        latest_status_time = latest_status_time_by_pop.get(pop_id)
        if member.end_time is None and latest_status_time:
            status_snapshot = component_data_source.get_status_snapshot(pop_id, latest_status_time)
        else:
            status_snapshot = component_data_source.get_status_snapshot(pop_id, member.start_time)

        status_count = to_int((status_snapshot or {}).get("CurrentCount") or 0)
        conserved_count = conserved_counts.get(pop_id)
        resolved_count = int(conserved_count) if conserved_count is not None else 0
        source = "conserved"
        if conserved_count is None:
            source = "status_no_conserved"
        elif resolved_count == 0 and status_count > 0:
            source = "status_when_conserved_zero"
        if pop_id in superseded_same_stage:
            source = "superseded_zero"

        if source == "status_when_conserved_zero":
            stage_name = assignment.lifecycle_stage.name if assignment.lifecycle_stage else "Unknown"
            assignment_count = to_int(assignment.population_count or 0)
            status_fallback_stage_totals[stage_name] += assignment_count
            status_fallback_populations.append(
                {
                    "population_id": pop_id,
                    "stage": stage_name,
                    "assignment_count": assignment_count,
                    "status_count": status_count,
                }
            )

    outflow_by_stage = estimate_stage_outflow_to_external(population_id_set, stage_by_pop, component_data_source)
    external_destination_evidence = build_external_destination_evidence(
        population_ids=population_id_set,
        sub_transfers=sub_transfers,
        loader=loader,
    )
    active_container_occupancy_evidence = build_active_container_occupancy_evidence(
        assignments=assignments,
        assignment_map_by_id=assignment_map_by_id,
        component_population_ids=population_id_set,
        loader=loader,
    )

    return {
        "stage_rows": stage_rows,
        "transitions": transitions,
        "mixed_rows": mixed_rows,
        "status_fallback_stage_totals": dict(status_fallback_stage_totals),
        "status_fallback_populations": sorted(
            status_fallback_populations,
            key=lambda row: row["assignment_count"],
            reverse=True,
        ),
        "outflow_by_stage": outflow_by_stage,
        "external_destination_evidence": external_destination_evidence,
        "active_container_occupancy_evidence": active_container_occupancy_evidence,
        "stage_entry_window_days": stage_entry_window_days,
        "lineage_fallback_max_depth": max(to_int(lineage_fallback_max_depth), 0),
        "transition_basis_counts": dict(transition_basis_counts),
        "transition_entry_window_reason_counts": dict(transition_entry_window_reason_counts),
        "transition_bridge_aware_count": transition_basis_counts.get("fishgroup_bridge_aware", 0),
        "transition_lineage_graph_count": transition_lineage_graph_count,
        "transition_entry_window_count": transition_basis_counts.get("entry_window", 0),
        "transition_count": len(transitions),
        "zero_assignment_total_count": zero_assignment_total_count,
        "zero_assignment_bridge_count": zero_assignment_bridge_count,
        "zero_assignment_superseded_count": zero_assignment_superseded_count,
        "zero_assignment_orphan_short_count": zero_assignment_orphan_short_count,
        "zero_assignment_no_count_evidence_count": zero_assignment_no_count_evidence_count,
        "zero_assignment_depleted_known_loss_count": zero_assignment_depleted_known_loss_count,
        "zero_assignment_non_bridge_count": zero_assignment_non_bridge_count,
        "fishgroup_classification": {
            "temporary_bridge_population_count": len(temporary_bridge_populations),
            "temporary_bridge_fishgroup_count": len(temporary_bridge_fishgroups),
            "bridge_mixed_fishgroup_count": len(bridge_mixed_fishgroups),
            "real_stage_entry_fishgroup_count": len(real_stage_entry_fishgroups),
            "example_temporary_bridge_fishgroups": sorted(temporary_bridge_fishgroups)[:10],
            "example_real_stage_entry_fishgroups": sorted(real_stage_entry_fishgroups)[:10],
            "entry_window_bridge_fishgroups": sorted(temporary_bridge_fishgroups_used)[:10],
        },
    }


def evaluate_regression_gates(
    *,
    stage_sanity: dict,
    zero_count_transfer_actions: int,
    max_non_bridge_zero_assignments: int,
) -> dict:
    transition_rows = list(stage_sanity.get("transitions", []))
    mixed_rows = to_int(stage_sanity.get("mixed_rows") or 0)
    transition_alert_excluded_incomplete_linkage_count = sum(
        1
        for row in transition_rows
        if (
            to_int(row.get("delta") or 0) > 0
            and mixed_rows == 0
            and (row.get("entry_window_reason") or "").strip() == "incomplete_linkage"
        )
    )
    transition_alert_count = sum(
        1
        for row in transition_rows
        if (
            to_int(row.get("delta") or 0) > 0
            and mixed_rows == 0
            and (row.get("entry_window_reason") or "").strip() != "incomplete_linkage"
        )
    )
    non_bridge_zero_assignments = to_int(stage_sanity.get("zero_assignment_non_bridge_count") or 0)

    checks = [
        {
            "name": "no_positive_transition_delta_without_mixed_batch",
            "passed": transition_alert_count == 0,
            "details": (
                "Positive stage transition deltas without mixed-batch composition rows: "
                f"{transition_alert_count}"
                + (
                    f" (excluded incomplete-linkage fallback rows: "
                    f"{transition_alert_excluded_incomplete_linkage_count})"
                )
            ),
        },
        {
            "name": "no_zero_count_transfer_actions",
            "passed": zero_count_transfer_actions == 0,
            "details": f"Transfer actions with transferred_count <= 0: {zero_count_transfer_actions}",
        },
        {
            "name": "non_bridge_zero_assignments_within_threshold",
            "passed": non_bridge_zero_assignments <= max_non_bridge_zero_assignments,
            "details": (
                "Assignments with population_count <= 0 after excluding temporary bridge, "
                "same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, "
                "and known-loss-depleted-zero rows: "
                f"{non_bridge_zero_assignments} (threshold: {max_non_bridge_zero_assignments})"
            ),
        },
    ]

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "transition_alert_count": transition_alert_count,
        "transition_alert_excluded_incomplete_linkage_count": transition_alert_excluded_incomplete_linkage_count,
        "zero_count_transfer_actions": zero_count_transfer_actions,
        "non_bridge_zero_assignments": non_bridge_zero_assignments,
        "max_non_bridge_zero_assignments": max_non_bridge_zero_assignments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic migration validation report")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--use-csv", type=str, metavar="CSV_DIR", required=True, help="CSV extract directory")
    parser.add_argument(
        "--stage-entry-window-days",
        type=int,
        default=2,
        help=(
            "Window length (days from first non-zero assignment per stage) used for "
            "stage-entry population sanity checks (default: 2)."
        ),
    )
    parser.add_argument(
        "--lineage-fallback-max-depth",
        type=int,
        default=LINEAGE_FALLBACK_MAX_DEPTH,
        help=(
            "Max predecessor-hop depth for deterministic SubTransfer lineage fallback "
            "when direct stage-entry linkage is missing (default: 14)."
        ),
    )
    parser.add_argument("--output", type=str, help="Optional output markdown path")
    parser.add_argument("--summary-json", type=str, help="Optional output JSON summary path")
    parser.add_argument(
        "--fishgroup-outlier-allowlist",
        action="append",
        default=[],
        metavar="INPUT_YEAR|INPUT_NUMBER|FISHGROUP",
        help=(
            "Allowlisted Fishgroup tuple-format outlier pattern (repeatable). "
            "Format: InputYear|InputNumber|Fishgroup"
        ),
    )
    parser.add_argument(
        "--fishgroup-outlier-top-n",
        type=int,
        default=5,
        help="Max top outlier patterns/examples to show in fishgroup format audit (default: 5).",
    )
    parser.add_argument(
        "--check-regression-gates",
        action="store_true",
        help="Fail with non-zero exit status if regression gates fail.",
    )
    parser.add_argument(
        "--max-non-bridge-zero-assignments",
        type=int,
        default=2,
        help=(
            "Regression gate threshold for non-bridge assignments with population_count <= 0 "
            "(default: 2)."
        ),
    )
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model="PopulationComponent", source_identifier=component_key
    ).first()
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.utcnow()) for m in members)

    loader = ETLDataLoader(args.use_csv)

    # FishTalk aggregates
    feeding_rows = loader.get_feeding_actions_for_populations(set(population_ids), window_start, window_end)
    ft_feed_events = len(feeding_rows)
    ft_feed_kg = sum(to_decimal(r.get("FeedAmountG") or 0) for r in feeding_rows) / Decimal("1000")

    mortality_rows = loader.get_mortality_actions_for_populations(set(population_ids), window_start, window_end)
    ft_mortality_events = len(mortality_rows)
    ft_mortality_count = sum_int(mortality_rows, "MortalityCount")
    ft_mortality_biomass = harvest_sum(mortality_rows, "MortalityBiomass")

    culling_rows = loader.get_culling_actions_for_populations(set(population_ids), window_start, window_end)
    ft_culling_events = len(culling_rows)
    ft_culling_count = sum_int(culling_rows, "CullingCount")
    ft_culling_biomass = harvest_sum(culling_rows, "CullingBiomass")

    escape_rows = loader.get_escape_actions_for_populations(set(population_ids), window_start, window_end)
    ft_escape_events = len(escape_rows)
    ft_escape_count = sum_int(escape_rows, "EscapeCount")
    ft_escape_biomass = harvest_sum(escape_rows, "EscapeBiomass")

    treatment_rows = loader.get_treatments_for_populations(set(population_ids), window_start, window_end)
    ft_treatment_events = len(treatment_rows)

    weight_rows = loader.get_weight_samples_for_populations(set(population_ids), window_start, window_end)
    ft_weight_samples = len(weight_rows)

    user_sample_rows = loader.get_user_sample_sessions(set(population_ids), window_start, window_end)
    ft_user_samples = len(user_sample_rows)

    lice_sample_rows, lice_data_rows, _ = loader.get_lice_samples_for_populations(
        set(population_ids), window_start, window_end
    )
    ft_lice_samples = len(lice_sample_rows)
    ft_lice_data_rows = len(lice_data_rows)
    ft_lice_fish_sampled = sum_int(lice_sample_rows, "NumberOfFish")
    ft_lice_total_count = sum_int(lice_data_rows, "LiceCount")

    harvest_rows = loader.get_harvest_results_for_populations(set(population_ids), window_start, window_end)
    ft_harvest_rows = len(harvest_rows)
    ft_harvest_count = sum_int(harvest_rows, "Count")
    ft_harvest_live = harvest_sum(harvest_rows, "GrossBiomass")
    ft_harvest_gutted = harvest_sum(harvest_rows, "NetBiomass")
    known_loss_count = ft_mortality_count + ft_culling_count + ft_escape_count + ft_harvest_count

    # AquaMind aggregates
    feeding_qs = FeedingEvent.objects.filter(batch=batch)
    am_feed_events = feeding_qs.count()
    am_feed_kg = feeding_qs.aggregate(total=Sum("amount_kg"))["total"] or Decimal("0")

    def mortality_by_source(source_model: str) -> tuple[int, Decimal, int]:
        ids = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=source_model,
            target_app_label="batch",
            target_model="mortalityevent",
        ).values_list("target_object_id", flat=True)
        qs = MortalityEvent.objects.filter(batch=batch, pk__in=ids)
        return (
            qs.count(),
            qs.aggregate(total=Sum("biomass_kg"))["total"] or Decimal("0"),
            qs.aggregate(total=Sum("count"))["total"] or 0,
        )

    am_mortality_events, am_mortality_biomass, am_mortality_count = mortality_by_source("Mortality")
    am_culling_events, am_culling_biomass, am_culling_count = mortality_by_source("Culling")
    am_escape_events, am_escape_biomass, am_escape_count = mortality_by_source("Escapes")

    am_treatment_events = Treatment.objects.filter(batch=batch).count()
    am_weight_samples = GrowthSample.objects.filter(assignment__batch=batch).count()
    am_user_samples = JournalEntry.objects.filter(batch=batch).count()

    lice_qs = LiceCount.objects.filter(batch=batch)
    am_lice_rows = lice_qs.count()
    am_lice_total_count = lice_qs.aggregate(total=Sum("count_value"))["total"] or 0

    lice_maps = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PublicLiceSampleData",
        target_app_label="health",
        target_model="licecount",
        target_object_id__in=lice_qs.values_list("id", flat=True),
    )
    sample_ids = {m.metadata.get("sample_id") for m in lice_maps if m.metadata and m.metadata.get("sample_id")}
    am_lice_sample_count = len(sample_ids)
    sample_fish = {}
    for m in lice_maps:
        sample_id = m.metadata.get("sample_id") if m.metadata else None
        if not sample_id or sample_id in sample_fish:
            continue
        try:
            lice_obj = lice_qs.get(id=m.target_object_id)
        except LiceCount.DoesNotExist:
            continue
        sample_fish[sample_id] = lice_obj.fish_sampled
    am_lice_fish_sampled = sum(sample_fish.values())

    env_count = EnvironmentalReading.objects.filter(batch=batch).count()

    harvest_event_qs = HarvestEvent.objects.filter(batch=batch)
    harvest_lot_qs = HarvestLot.objects.filter(event__batch=batch)
    am_harvest_events = harvest_event_qs.count()
    am_harvest_lots = harvest_lot_qs.count()
    am_harvest_count = harvest_lot_qs.aggregate(total=Sum("unit_count"))["total"] or 0
    am_harvest_live = harvest_lot_qs.aggregate(total=Sum("live_weight_kg"))["total"] or Decimal("0")
    am_harvest_gutted = harvest_lot_qs.aggregate(total=Sum("gutted_weight_kg"))["total"] or Decimal("0")

    mortality_biomass_source_sparse = (
        ft_mortality_count > 0
        and to_decimal(ft_mortality_biomass) <= Decimal("0")
        and to_decimal(am_mortality_biomass) > Decimal("0")
    )

    stage_sanity = build_stage_sanity(
        batch=batch,
        members=members,
        population_ids=population_ids,
        csv_dir=args.use_csv,
        known_loss_count=known_loss_count,
        stage_entry_window_days=args.stage_entry_window_days,
        lineage_fallback_max_depth=args.lineage_fallback_max_depth,
    )
    transfer_action_qs = TransferAction.objects.filter(workflow__batch=batch)
    total_transfer_actions = transfer_action_qs.count()
    zero_count_transfer_actions = transfer_action_qs.filter(transferred_count__lte=0).count()

    try:
        fishgroup_allowlist_patterns = parse_fishgroup_allowlist(args.fishgroup_outlier_allowlist)
    except ValueError as exc:
        raise SystemExit(str(exc))
    fishgroup_format_audit = build_fishgroup_format_audit(
        csv_dir=args.use_csv,
        population_ids=set(population_ids),
        allowlist_patterns=fishgroup_allowlist_patterns,
        top_outlier_limit=max(to_int(args.fishgroup_outlier_top_n), 1),
    )
    regression_gates = evaluate_regression_gates(
        stage_sanity=stage_sanity,
        zero_count_transfer_actions=zero_count_transfer_actions,
        max_non_bridge_zero_assignments=max(to_int(args.max_non_bridge_zero_assignments), 0),
    )

    def format_counts(counter: dict[str, int] | None, limit: int = 5) -> str:
        if not counter:
            return "-"
        rows = sorted(counter.items(), key=lambda item: (-to_int(item[1]), item[0]))[:limit]
        return ", ".join(f"{key}:{value}" for key, value in rows) if rows else "-"

    lines = []
    lines.append("# Semantic Migration Validation Report")
    lines.append("")
    lines.append(f"- Component key: `{component_key}`")
    lines.append(f"- Batch: `{batch.batch_number}` (id={batch.id})")
    lines.append(f"- Populations: {len(population_ids)}")
    lines.append(f"- Window: {window_start} → {window_end}")
    lines.append("")
    lines.append("| Metric | FishTalk | AquaMind | Diff (FT - AM) |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append(f"| Feeding events | {ft_feed_events} | {am_feed_events} | {numeric_diff(ft_feed_events, am_feed_events)} |")
    lines.append(f"| Feeding kg | {fmt(ft_feed_kg)} | {fmt(am_feed_kg)} | {numeric_diff(ft_feed_kg, am_feed_kg)} |")
    lines.append(f"| Mortality events | {ft_mortality_events} | {am_mortality_events} | {numeric_diff(ft_mortality_events, am_mortality_events)} |")
    lines.append(f"| Mortality count | {ft_mortality_count} | {am_mortality_count} | {numeric_diff(ft_mortality_count, am_mortality_count)} |")
    lines.append(f"| Mortality biomass kg | {fmt(ft_mortality_biomass)} | {fmt(am_mortality_biomass)} | {numeric_diff(ft_mortality_biomass, am_mortality_biomass)} |")
    lines.append(f"| Culling events | {ft_culling_events} | {am_culling_events} | {numeric_diff(ft_culling_events, am_culling_events)} |")
    lines.append(f"| Culling count | {ft_culling_count} | {am_culling_count} | {numeric_diff(ft_culling_count, am_culling_count)} |")
    lines.append(f"| Culling biomass kg | {fmt(ft_culling_biomass)} | {fmt(am_culling_biomass)} | {numeric_diff(ft_culling_biomass, am_culling_biomass)} |")
    lines.append(f"| Escape events | {ft_escape_events} | {am_escape_events} | {numeric_diff(ft_escape_events, am_escape_events)} |")
    lines.append(f"| Escape count | {ft_escape_count} | {am_escape_count} | {numeric_diff(ft_escape_count, am_escape_count)} |")
    lines.append(f"| Escape biomass kg | {fmt(ft_escape_biomass)} | {fmt(am_escape_biomass)} | {numeric_diff(ft_escape_biomass, am_escape_biomass)} |")
    lines.append(f"| Treatments | {ft_treatment_events} | {am_treatment_events} | {numeric_diff(ft_treatment_events, am_treatment_events)} |")
    lines.append(f"| Growth samples | {ft_weight_samples} | {am_weight_samples} | {numeric_diff(ft_weight_samples, am_weight_samples)} |")
    lines.append(f"| Health journal entries | {ft_user_samples} | {am_user_samples} | {numeric_diff(ft_user_samples, am_user_samples)} |")
    lines.append(f"| Lice samples | {ft_lice_samples} | {am_lice_sample_count} | {numeric_diff(ft_lice_samples, am_lice_sample_count)} |")
    lines.append(f"| Lice data rows | {ft_lice_data_rows} | {am_lice_rows} | {numeric_diff(ft_lice_data_rows, am_lice_rows)} |")
    lines.append(f"| Lice total count | {ft_lice_total_count} | {am_lice_total_count} | {numeric_diff(ft_lice_total_count, am_lice_total_count)} |")
    lines.append(f"| Fish sampled (lice) | {ft_lice_fish_sampled} | {am_lice_fish_sampled} | {numeric_diff(ft_lice_fish_sampled, am_lice_fish_sampled)} |")
    lines.append(f"| Environmental readings | n/a (sqlite) | {env_count} | n/a |")
    lines.append(f"| Harvest rows | {ft_harvest_rows} | {am_harvest_lots} | {numeric_diff(ft_harvest_rows, am_harvest_lots)} |")
    lines.append(f"| Harvest events | n/a | {am_harvest_events} | n/a |")
    lines.append(f"| Harvest count | {ft_harvest_count} | {am_harvest_count} | {numeric_diff(ft_harvest_count, am_harvest_count)} |")
    lines.append(f"| Harvest live kg | {fmt(ft_harvest_live)} | {fmt(am_harvest_live)} | {numeric_diff(ft_harvest_live, am_harvest_live)} |")
    lines.append(f"| Harvest gutted kg | {fmt(ft_harvest_gutted)} | {fmt(am_harvest_gutted)} | {numeric_diff(ft_harvest_gutted, am_harvest_gutted)} |")
    lines.append("")
    if mortality_biomass_source_sparse:
        lines.append(
            "- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; "
            "AquaMind mortality biomass is derived from status/assignment context. "
            "This row is informational and is not a regression gate criterion."
        )
        lines.append("")
    lines.append("## Lifecycle Stage Sanity")
    lines.append("")
    lines.append(f"- Mixed-batch composition rows: {stage_sanity['mixed_rows']}")
    lines.append(
        f"- Known removal count (mortality + culling + escapes + harvest): {known_loss_count}"
    )
    lines.append(
        f"- Stage-entry window used for transition sanity: {stage_sanity['stage_entry_window_days']} day(s)"
    )
    transition_count = to_int(stage_sanity.get("transition_count") or 0)
    bridge_aware_count = to_int(stage_sanity.get("transition_bridge_aware_count") or 0)
    entry_window_count = to_int(stage_sanity.get("transition_entry_window_count") or 0)
    if transition_count > 0:
        bridge_aware_pct = (bridge_aware_count / transition_count) * 100
        entry_window_pct = (entry_window_count / transition_count) * 100
        lines.append(
            "- Transition basis usage: "
            f"{bridge_aware_count}/{transition_count} bridge-aware ({bridge_aware_pct:.1f}%), "
            f"{entry_window_count}/{transition_count} entry-window ({entry_window_pct:.1f}%)."
        )
    lines.append(
        "- Lineage fallback max depth: "
        f"{stage_sanity.get('lineage_fallback_max_depth', LINEAGE_FALLBACK_MAX_DEPTH)} hop(s)."
    )
    lines.append(
        "- Bridge-aware transitions using lineage-graph fallback: "
        f"{stage_sanity.get('transition_lineage_graph_count', 0)}"
    )
    lines.append(
        "- Assignment zero-count rows (population_count <= 0): "
        f"{stage_sanity.get('zero_assignment_total_count', 0)} total, "
        f"{stage_sanity.get('zero_assignment_bridge_count', 0)} bridge-classified, "
        f"{stage_sanity.get('zero_assignment_superseded_count', 0)} same-stage superseded-zero, "
        f"{stage_sanity.get('zero_assignment_orphan_short_count', 0)} short-lived orphan-zero, "
        f"{stage_sanity.get('zero_assignment_no_count_evidence_count', 0)} no-count-evidence-zero, "
        f"{stage_sanity.get('zero_assignment_depleted_known_loss_count', 0)} known-loss-depleted-zero, "
        f"{stage_sanity.get('zero_assignment_non_bridge_count', 0)} non-bridge."
    )
    lines.append(
        "- Transfer actions with transferred_count <= 0: "
        f"{zero_count_transfer_actions} of {total_transfer_actions}."
    )
    fishgroup_classification = stage_sanity.get("fishgroup_classification") or {}
    if fishgroup_classification:
        lines.append(
            "- Fishgroup classification: "
            f"{fishgroup_classification.get('temporary_bridge_fishgroup_count', 0)} temporary bridge fishgroups, "
            f"{fishgroup_classification.get('real_stage_entry_fishgroup_count', 0)} real stage-entry fishgroups, "
            f"{fishgroup_classification.get('temporary_bridge_population_count', 0)} temporary bridge populations."
        )
    lines.append("")
    lines.append(
        "| Stage | Entry population | Active population | Peak concurrent population | Full summed population | "
        "Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | "
        "Bridge fishgroups excluded | Non-zero assignments | Total assignments |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for row in stage_sanity["stage_rows"]:
        full_to_entry_ratio = row.get("full_to_entry_ratio")
        full_to_peak_ratio = row.get("full_to_peak_ratio")
        lines.append(
            f"| {row['stage']} | {row['population_entry']} | {row.get('active_population_total', 0)} | "
            f"{row.get('peak_concurrent_population', 0)} | {row['population_total']} | "
            f"{full_to_entry_ratio if full_to_entry_ratio is not None else '-'} | "
            f"{full_to_peak_ratio if full_to_peak_ratio is not None else '-'} | "
            f"{row['entry_date'] or '-'} | {row['entry_window_end'] or '-'} | {row['entry_container_count']} | "
            f"{row.get('entry_real_fishgroup_count', 0)} | {row.get('entry_bridge_excluded_count', 0)} | "
            f"{row['nonzero_assignment_count']} | {row['assignment_count']} |"
        )
    lines.append("")
    lines.append(
        "- Transition deltas below use bridge-aware linked source populations when available "
        "(counts prefer SubTransfer-conserved values, fallback to assignment counts); "
        "otherwise they fall back to stage entry-window populations."
    )
    lines.append("")
    lines.append(
        "| Transition | From population | To population | Delta | Entry populations | "
        "Linked destinations | Bridge-aware eligible | Basis | Sanity check |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |")
    for row in stage_sanity["transitions"]:
        label = f"{row['from_stage']} -> {row['to_stage']}"
        delta = row["delta"]
        basis_raw = row.get("basis") or "entry_window"
        if basis_raw == "fishgroup_bridge_aware":
            if (row.get("entry_window_reason") or "").strip() == "direct_linkage":
                basis = (
                    "Bridge-aware (direct edge linkage; linked sources: "
                    f"{row.get('linked_source_population_count', 0)})"
                )
            else:
                basis = f"Bridge-aware (linked sources: {row.get('linked_source_population_count', 0)})"
            if row.get("lineage_graph_used"):
                basis += "; lineage graph fallback used"
        else:
            reason = row.get("entry_window_reason") or "entry_window"
            if reason == "incomplete_linkage":
                basis = "Entry window (incomplete linkage)"
            elif reason == "no_linked_sources":
                basis = "Entry window (no linked sources)"
            elif reason == "no_bridge_path":
                basis = "Entry window (no bridge path)"
            elif reason == "no_entry_populations":
                basis = "Entry window (no entry populations)"
            else:
                basis = "Entry window"
        sanity = "OK"
        if delta > 0 and stage_sanity["mixed_rows"] > 0:
            sanity = "Increase observed; mixed-batch composition present"
        elif delta > 0:
            if (row.get("entry_window_reason") or "").strip() == "incomplete_linkage":
                sanity = "WARN: positive delta under incomplete linkage fallback"
            else:
                sanity = "ALERT: population increases without mixed-batch composition"
        elif row["drop"] > 0 and row["unexplained_drop_vs_known_losses"] > 0:
            sanity = (
                "WARN: stage drop exceeds total known removals by "
                f"{row['unexplained_drop_vs_known_losses']}"
            )
        lines.append(
            f"| {label} | {row.get('from_population', 0)} | {row.get('to_population', 0)} | {delta} | "
            f"{row.get('entry_population_count', 0)} | {row.get('linked_destination_population_count', 0)} | "
            f"{'yes' if row.get('bridge_aware_eligible') else 'no'} | {basis} | {sanity} |"
        )

    if fishgroup_classification:
        lines.append("")
        lines.append("### Fishgroup Classification Samples")
        lines.append("")
        temp_examples = fishgroup_classification.get("example_temporary_bridge_fishgroups") or []
        real_examples = fishgroup_classification.get("example_real_stage_entry_fishgroups") or []
        if temp_examples:
            lines.append(
                "- Temporary bridge fishgroup examples: "
                + ", ".join(f"`{fishgroup}`" for fishgroup in temp_examples)
            )
        if real_examples:
            lines.append(
                "- Real stage-entry fishgroup examples: "
                + ", ".join(f"`{fishgroup}`" for fishgroup in real_examples)
            )
        bridge_examples = fishgroup_classification.get("entry_window_bridge_fishgroups") or []
        if bridge_examples:
            lines.append(
                "- Bridge fishgroups excluded from stage-entry windows: "
                + ", ".join(f"`{fishgroup}`" for fishgroup in bridge_examples)
            )

    lines.append("")
    lines.append("### Fishgroup Format Audit")
    lines.append("")
    lines.append(
        "- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`"
    )
    lines.append("| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for scope_key, scope_label in (("component", "Component"), ("global", "Global extract")):
        scope = fishgroup_format_audit.get(scope_key) or {}
        if not scope:
            continue
        lines.append(
            f"| {scope_label} | {scope.get('rows_checked', 0)} | {scope.get('matched_rows', 0)} | "
            f"{scope.get('matched_pct', 0)} | {scope.get('outlier_rows', 0)} | "
            f"{scope.get('allowlisted_outlier_rows', 0)} | {scope.get('non_allowlisted_outlier_rows', 0)} |"
        )

    allowlist_patterns = fishgroup_format_audit.get("allowlist_patterns") or []
    if allowlist_patterns:
        lines.append(
            "- Outlier allowlist patterns: "
            + ", ".join(f"`{pattern}`" for pattern in allowlist_patterns)
        )

    global_audit = fishgroup_format_audit.get("global") or {}
    top_patterns = global_audit.get("top_non_allowlisted_outlier_patterns") or []
    if top_patterns:
        lines.append("")
        lines.append("| Top non-allowlisted outlier pattern | Rows |")
        lines.append("| --- | ---: |")
        for row in top_patterns:
            lines.append(f"| `{row.get('pattern', '')}` | {row.get('count', 0)} |")

    if stage_sanity["status_fallback_stage_totals"]:
        lines.append("")
        lines.append("### Count Provenance")
        lines.append("")
        lines.append(
            "- Populations where assignment count came from status snapshot fallback "
            "(conserved transfer count was zero):"
        )
        lines.append("| Stage | Population count from fallback |")
        lines.append("| --- | ---: |")
        for stage_name in sorted(
            stage_sanity["status_fallback_stage_totals"],
            key=lambda s: STAGE_INDEX.get(s, 999),
        ):
            lines.append(
                f"| {stage_name} | {stage_sanity['status_fallback_stage_totals'][stage_name]} |"
            )

        top_fallback = stage_sanity["status_fallback_populations"][:5]
        if top_fallback:
            lines.append("")
            lines.append("| PopulationID | Stage | Assignment count | Status snapshot count |")
            lines.append("| --- | --- | ---: | ---: |")
            for row in top_fallback:
                lines.append(
                    f"| `{row['population_id']}` | {row['stage']} | {row['assignment_count']} | {row['status_count']} |"
                )

    if stage_sanity["outflow_by_stage"]:
        lines.append("")
        lines.append("### Estimated Outflow To Populations Outside Selected Component")
        lines.append("")
        lines.append(
            "- Conservative estimate from SubTransfers propagation (component-population sources only). "
            "This means outside the selected stitched population set, not necessarily another station:"
        )
        lines.append("| Source stage | Estimated transferred count to populations outside selected component |")
        lines.append("| --- | ---: |")
        for stage_name in sorted(stage_sanity["outflow_by_stage"], key=lambda s: STAGE_INDEX.get(s, 999)):
            lines.append(f"| {stage_name} | {stage_sanity['outflow_by_stage'][stage_name]} |")

    external_destination_evidence = stage_sanity.get("external_destination_evidence") or {}
    if external_destination_evidence:
        lines.append("")
        lines.append("### Outside-Component Destination Evidence")
        lines.append("")
        lines.append(
            "- This evidence is derived from SubTransfers graph links and grouped-organisation context; "
            "it indicates destinations outside the selected stitched population set."
        )
        lines.append(
            f"- Marine linkage evidence: {'YES' if external_destination_evidence.get('marine_linkage_evidence') else 'NO'}"
        )
        lines.append(
            f"- Direct external destination populations (any role): "
            f"{external_destination_evidence.get('direct_external_population_count', 0)}"
        )
        lines.append("")
        lines.append("| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |")
        lines.append("| --- | ---: | --- | --- |")
        role_rows = (
            ("SourcePopBefore -> DestPopAfter", external_destination_evidence.get("source_to_dest_external") or {}),
            ("SourcePopBefore -> SourcePopAfter", external_destination_evidence.get("source_chain_external") or {}),
            ("DestPopBefore -> DestPopAfter", external_destination_evidence.get("dest_chain_external") or {}),
        )
        for label, role_payload in role_rows:
            lines.append(
                f"| {label} | {role_payload.get('edge_count', 0)} | "
                f"{format_counts(role_payload.get('by_prod_stage') or {})} | "
                f"{format_counts(role_payload.get('by_site') or {})} |"
            )

        lines.append("")
        lines.append("| Destination set | Populations | Marine populations | By prod stage | By site | By site group |")
        lines.append("| --- | ---: | ---: | --- | --- | --- |")
        for label, payload in (
            ("Direct external populations", external_destination_evidence.get("direct_population_summary") or {}),
            ("Reachable outside descendants", external_destination_evidence.get("descendant_summary") or {}),
        ):
            lines.append(
                f"| {label} | {payload.get('population_count', 0)} | {payload.get('marine_population_count', 0)} | "
                f"{format_counts(payload.get('by_prod_stage') or {})} | "
                f"{format_counts(payload.get('by_site') or {})} | "
                f"{format_counts(payload.get('by_site_group') or {})} |"
            )

    active_container_occupancy_evidence = stage_sanity.get("active_container_occupancy_evidence") or {}
    if active_container_occupancy_evidence:
        lines.append("")
        lines.append("### Active Container Latest Holder Evidence")
        lines.append("")
        lines.append(
            "- For each currently active migrated assignment container, this shows the latest non-zero "
            "status holder in source data."
        )
        lines.append(
            f"- Containers checked: {active_container_occupancy_evidence.get('containers_checked', 0)}; "
            f"latest holder in selected component: {active_container_occupancy_evidence.get('latest_holder_in_component_count', 0)}; "
            f"latest holder outside selected component: {active_container_occupancy_evidence.get('latest_holder_outside_component_count', 0)}; "
            f"unknown latest holder: {active_container_occupancy_evidence.get('latest_holder_unknown_count', 0)}."
        )
        lines.append("")
        lines.append(
            "| Container | Source container id | Component population | Latest holder population | "
            "Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |"
        )
        lines.append("| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |")
        for row in active_container_occupancy_evidence.get("rows", []):
            in_component_value = row.get("latest_in_component")
            if in_component_value is None:
                in_component_label = "unknown"
            else:
                in_component_label = "yes" if in_component_value else "no"
            latest_count = row.get("latest_count")
            latest_biomass_kg = row.get("latest_biomass_kg")
            lines.append(
                f"| {row.get('container_name') or '-'} | {row.get('source_container_id') or '-'} | "
                f"`{row.get('component_population_id') or '-'}` | "
                f"`{row.get('latest_population_id') or '-'}` | {in_component_label} | "
                f"{latest_count if latest_count is not None else '-'} | "
                f"{latest_biomass_kg if latest_biomass_kg is not None else '-'} | "
                f"{row.get('latest_status_time') or '-'} | {row.get('site') or '-'} | {row.get('prod_stage') or '-'} |"
            )

    lines.append("")
    lines.append("### Regression Gates")
    lines.append("")
    lines.append("| Gate | Result | Details |")
    lines.append("| --- | --- | --- |")
    for check in regression_gates["checks"]:
        lines.append(
            f"| `{check['name']}` | {'PASS' if check['passed'] else 'FAIL'} | {check['details']} |"
        )
    lines.append(
        f"- Overall gate result: {'PASS' if regression_gates['passed'] else 'FAIL'}"
        + (" (enforced)" if args.check_regression_gates else " (advisory)")
    )

    summary_payload = {
        "component_key": component_key,
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
        },
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "population_count": len(population_ids),
        "known_loss_count": known_loss_count,
        "stage_sanity": {
            "mixed_rows": stage_sanity.get("mixed_rows", 0),
            "stage_entry_window_days": stage_sanity.get("stage_entry_window_days", 0),
            "lineage_fallback_max_depth": stage_sanity.get("lineage_fallback_max_depth", 0),
            "transition_count": stage_sanity.get("transition_count", 0),
            "transition_bridge_aware_count": stage_sanity.get("transition_bridge_aware_count", 0),
            "transition_lineage_graph_count": stage_sanity.get("transition_lineage_graph_count", 0),
            "transition_entry_window_count": stage_sanity.get("transition_entry_window_count", 0),
            "transition_basis_counts": stage_sanity.get("transition_basis_counts", {}),
            "transition_entry_window_reason_counts": stage_sanity.get("transition_entry_window_reason_counts", {}),
            "zero_assignment_total_count": stage_sanity.get("zero_assignment_total_count", 0),
            "zero_assignment_bridge_count": stage_sanity.get("zero_assignment_bridge_count", 0),
            "zero_assignment_superseded_count": stage_sanity.get("zero_assignment_superseded_count", 0),
            "zero_assignment_orphan_short_count": stage_sanity.get("zero_assignment_orphan_short_count", 0),
            "zero_assignment_no_count_evidence_count": stage_sanity.get("zero_assignment_no_count_evidence_count", 0),
            "zero_assignment_depleted_known_loss_count": stage_sanity.get("zero_assignment_depleted_known_loss_count", 0),
            "zero_assignment_non_bridge_count": stage_sanity.get("zero_assignment_non_bridge_count", 0),
            "stage_rows": stage_sanity.get("stage_rows", []),
            "outflow_by_stage": stage_sanity.get("outflow_by_stage", {}),
            "external_destination_evidence": stage_sanity.get("external_destination_evidence", {}),
            "active_container_occupancy_evidence": stage_sanity.get("active_container_occupancy_evidence", {}),
            "transitions": stage_sanity.get("transitions", []),
        },
        "transfer_actions": {
            "total_count": total_transfer_actions,
            "zero_count": zero_count_transfer_actions,
        },
        "fishgroup_classification": stage_sanity.get("fishgroup_classification", {}),
        "fishgroup_format_audit": fishgroup_format_audit,
        "metric_comparability": {
            "mortality_biomass_source_sparse": mortality_biomass_source_sparse,
            "mortality_biomass_gate_criterion": False,
        },
        "regression_gates": regression_gates,
    }

    output = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(output)

    if args.summary_json:
        Path(args.summary_json).write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote summary JSON to {args.summary_json}")

    if args.check_regression_gates and not regression_gates["passed"]:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
