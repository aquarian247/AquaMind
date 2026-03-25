#!/usr/bin/env python3
# flake8: noqa
"""Migrate an input-based batch from FishTalk to AquaMind.

This script uses Ext_Inputs_v2 data (egg deliveries) to identify biological batches.
This is the CORRECT approach for batch identification - each batch key represents
a cohort from a single egg fertilization event.

Batch Key: InputName|InputNumber|YearClass

Examples:
    python pilot_migrate_input_batch.py --batch-key "Heyst 2018|1|2018"
    python pilot_migrate_input_batch.py --batch-key "Vár2018|1|2018" --dry-run

This script:
1. Reads from input_based_stitching_report.py output
2. Generates compatible CSV files for existing migration scripts
3. Runs migration scripts in a deterministic pipeline (optional parallel post-transfer phase)
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db
from scripts.migration.tools.extract_freshness_guard import (
    DEFAULT_BACKUP_HORIZON_DATE,
    evaluate_extract_freshness,
    print_summary as print_extract_freshness_summary,
)
from scripts.migration.tools.hall_stage_rules import canonicalize_stage_sequence
from scripts.migration.tools.migration_profiles import MIGRATION_PROFILE_NAMES

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from apps.batch.models import Batch
from apps.migration_support.models import ExternalIdMap


INPUT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching"
BATCH_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
CSV_SUPPORTED_SCRIPTS = {
    "pilot_migrate_component.py",
    "pilot_migrate_component_transfers.py",
    "pilot_migrate_component_feeding.py",
    "pilot_migrate_component_mortality.py",
    "pilot_migrate_component_culling.py",
    "pilot_migrate_component_escapes.py",
    "pilot_migrate_component_environmental.py",
    "pilot_migrate_component_growth_samples.py",
    "pilot_migrate_component_treatments.py",
    "pilot_migrate_component_lice.py",
    "pilot_migrate_component_health_journal.py",
    "pilot_migrate_component_feed_inventory.py",
    "pilot_migrate_component_harvest.py",
}

# Core order is fixed for correctness: assignments before transfers.
PIPELINE_CORE_SCRIPT_ORDER = [
    "pilot_migrate_component.py",
    "pilot_migrate_component_transfers.py",
]

# Post-transfer scripts can be run in parallel when explicitly enabled.
PIPELINE_PARALLEL_SCRIPT_ORDER = [
    "pilot_migrate_component_feeding.py",
    "pilot_migrate_component_growth_samples.py",
    "pilot_migrate_component_mortality.py",
    "pilot_migrate_component_culling.py",
    "pilot_migrate_component_escapes.py",
    "pilot_migrate_component_treatments.py",
    "pilot_migrate_component_lice.py",
    "pilot_migrate_component_health_journal.py",
    "pilot_migrate_component_harvest.py",
    "pilot_migrate_component_environmental.py",
]

# Feed inventory shares feed master data with feeding and stays serial.
PIPELINE_TAIL_SCRIPT_ORDER = [
    "pilot_migrate_component_feed_inventory.py",
]

PIPELINE_SCRIPT_LABELS = {
    "pilot_migrate_component.py": "Infrastructure + Batch + Assignments",
    "pilot_migrate_component_transfers.py": "Transfer Workflows",
    "pilot_migrate_component_feeding.py": "Feeding Events",
    "pilot_migrate_component_growth_samples.py": "Growth Samples",
    "pilot_migrate_component_mortality.py": "Mortality Events",
    "pilot_migrate_component_culling.py": "Culling Events",
    "pilot_migrate_component_escapes.py": "Escape Events",
    "pilot_migrate_component_treatments.py": "Treatments",
    "pilot_migrate_component_lice.py": "Lice Counts",
    "pilot_migrate_component_health_journal.py": "Health Journal",
    "pilot_migrate_component_harvest.py": "Harvest Results",
    "pilot_migrate_component_environmental.py": "Environmental Readings",
    "pilot_migrate_component_feed_inventory.py": "Feed Inventory",
}


DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", ascii_value).strip("_")
    return cleaned or "batch"


def compose_continuation_batch_name(
    fw_batch_name: str,
    sea_batch_name: str,
    *,
    max_length: int = 50,
) -> str:
    """Compose FW->Sea display name while preserving uniqueness constraints."""
    fw = (fw_batch_name or "").strip()
    sea = (sea_batch_name or "").strip()
    if not fw:
        return sea[:max_length]
    if not sea:
        return fw[:max_length]

    suffix = f" - {sea}"
    if fw.lower().endswith(suffix.lower()):
        return fw[:max_length]

    combined = f"{fw}{suffix}"
    if len(combined) <= max_length:
        return combined

    # Preserve full sea segment and trim FW prefix if necessary.
    if len(suffix) >= max_length:
        return combined[:max_length]
    trimmed_fw = fw[: max_length - len(suffix)].rstrip()
    return f"{trimmed_fw}{suffix}"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


@dataclass
class PopulationMember:
    population_id: str
    container_id: str
    container_name: str
    org_unit_name: str
    geography: str
    start_time: datetime | None
    end_time: datetime | None
    fishtalk_stages: str
    aquamind_stages: str


@dataclass
class InputBatchInfo:
    batch_key: str
    input_name: str
    input_number: str
    year_class: str
    population_count: int
    total_fish: float
    span_days: int
    aquamind_stages: str
    geographies: str
    is_valid: bool
    earliest_start: datetime | None
    latest_activity: datetime | None


@dataclass
class StationPreflightResult:
    input_project_sites: set[str]
    ext_input_sites: set[str]
    member_sites: set[str]
    mismatches: list[str]


@dataclass(frozen=True)
class ScriptRunResult:
    script_name: str
    success: bool
    duration_seconds: float


def load_input_batch_info(
    batch_key: str,
    *,
    use_csv: str | None = None,
) -> InputBatchInfo | None:
    """Load batch summary info for a given input batch key."""
    _ = use_csv  # reserved for future fallback lookup paths
    batches_file = INPUT_STITCHING_DIR / "input_batches.csv"
    if not batches_file.exists():
        raise FileNotFoundError(
            f"Input batches file not found: {batches_file}\n"
            "Run input_based_stitching_report.py first."
        )

    with batches_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("batch_key") != batch_key:
                continue
            
            # Parse total_fish (has comma formatting)
            total_fish_str = row.get("total_fish", "0").replace(",", "")
            try:
                total_fish = float(total_fish_str)
            except ValueError:
                total_fish = 0.0
            
            return InputBatchInfo(
                batch_key=row.get("batch_key", ""),
                input_name=row.get("input_name", ""),
                input_number=row.get("input_number", ""),
                year_class=row.get("year_class", ""),
                population_count=int(row.get("population_count", "0")),
                total_fish=total_fish,
                span_days=int(row.get("span_days", "0")),
                aquamind_stages=row.get("aquamind_stages", ""),
                geographies=row.get("geographies", ""),
                is_valid=row.get("is_valid", "").lower() == "true",
                earliest_start=parse_dt(row.get("earliest_start", "")),
                latest_activity=parse_dt(row.get("latest_activity", "")),
            )
    
    return None


def has_duplicate_input_name(input_name: str) -> bool:
    """Return True when stitched input batches contain >1 valid row for this input_name."""
    batches_file = INPUT_STITCHING_DIR / "input_batches.csv"
    if not batches_file.exists():
        return False
    seen_keys: set[str] = set()
    with batches_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("input_name", "").strip() != input_name:
                continue
            if row.get("is_valid", "").strip().lower() != "true":
                continue
            key = row.get("batch_key", "").strip()
            if not key:
                continue
            seen_keys.add(key)
            if len(seen_keys) > 1:
                return True
    return False


def load_input_populations(
    batch_key: str,
    *,
    use_csv: str | None = None,
    expand_subtransfer_descendants: bool = False,
) -> list[PopulationMember]:
    """Load population members for a given input batch key.

    When requested, recursively expands members via SubTransfers descendants so
    transfer/materialized holder populations are included in the component.
    """
    members_file = INPUT_STITCHING_DIR / "input_population_members.csv"
    if not members_file.exists():
        raise FileNotFoundError(
            f"Input population members file not found: {members_file}\n"
            "Run input_based_stitching_report.py first."
        )

    members: list[PopulationMember] = []
    with members_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("batch_key") != batch_key:
                continue
            members.append(
                PopulationMember(
                    population_id=row.get("population_id", ""),
                    container_id=row.get("container_id", ""),
                    container_name=row.get("container_name", ""),
                    org_unit_name=row.get("org_unit_name", ""),
                    geography=row.get("geography", ""),
                    start_time=parse_dt(row.get("start_time", "")),
                    end_time=parse_dt(row.get("end_time", "")),
                    fishtalk_stages=row.get("fishtalk_stages", ""),
                    aquamind_stages=row.get("aquamind_stages", ""),
                )
            )

    if not expand_subtransfer_descendants:
        return members
    if not use_csv:
        print(
            "[WARN] --expand-subtransfer-descendants requested without --use-csv; "
            "using stitched members only."
        )
        return members

    csv_dir = Path(use_csv)
    subtransfer_path = csv_dir / "sub_transfers.csv"
    populations_path = csv_dir / "populations.csv"
    containers_path = csv_dir / "containers.csv"
    grouped_path = csv_dir / "grouped_organisation.csv"
    org_units_path = csv_dir / "org_units.csv"
    population_stages_path = csv_dir / "population_stages.csv"
    production_stages_path = csv_dir / "production_stages.csv"
    required_paths = [
        subtransfer_path,
        populations_path,
        containers_path,
        grouped_path,
        org_units_path,
        population_stages_path,
        production_stages_path,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        print(
            "[WARN] Missing extract files for descendant expansion; "
            "using stitched members only."
        )
        for path in missing:
            print(f"       - {path}")
        return members

    seed_ids = {member.population_id for member in members if member.population_id}
    if not seed_ids:
        return members

    edges_by_source: dict[str, set[str]] = defaultdict(set)
    with subtransfer_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_before = (row.get("SourcePopBefore") or "").strip()
            if not source_before:
                continue
            source_after = (row.get("SourcePopAfter") or "").strip()
            dest_after = (row.get("DestPopAfter") or "").strip()
            if source_after:
                edges_by_source[source_before].add(source_after)
            if dest_after:
                edges_by_source[source_before].add(dest_after)

    reachable: set[str] = set(seed_ids)
    pending: deque[str] = deque(seed_ids)
    while pending:
        source_pop = pending.popleft()
        for child in edges_by_source.get(source_pop, set()):
            if child in reachable:
                continue
            reachable.add(child)
            pending.append(child)

    descendant_ids = sorted(reachable - seed_ids)
    if not descendant_ids:
        print("Expanded SubTransfers descendants: +0 populations (already fully covered).")
        return members

    populations_by_id: dict[str, dict[str, str]] = {}
    with populations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                populations_by_id[pop_id] = row

    container_rows_by_id: dict[str, dict[str, str]] = {}
    with containers_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if container_id:
                container_rows_by_id[container_id] = row

    # Keep the richest grouped row per container id.
    grouped_rows_by_container_id: dict[str, dict[str, str]] = {}
    grouped_row_score: dict[str, int] = {}
    with grouped_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if not container_id:
                continue
            score = 0
            if (row.get("Site") or "").strip():
                score += 1
            if (row.get("ContainerGroup") or "").strip():
                score += 1
            current_score = grouped_row_score.get(container_id, -1)
            if score >= current_score:
                grouped_rows_by_container_id[container_id] = row
                grouped_row_score[container_id] = score

    org_unit_name_by_id: dict[str, str] = {}
    with org_units_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            org_unit_id = (row.get("OrgUnitID") or "").strip()
            if not org_unit_id:
                continue
            org_unit_name_by_id[org_unit_id] = (row.get("Name") or "").strip()

    stage_name_by_id: dict[str, str] = {}
    with production_stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stage_id = (row.get("StageID") or "").strip()
            if not stage_id:
                continue
            stage_name_by_id[stage_id] = (row.get("StageName") or "").strip()

    stage_events_by_population: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    with population_stages_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id not in reachable:
                continue
            stage_time = parse_dt((row.get("StartTime") or "").strip())
            if stage_time is None:
                continue
            stage_name = stage_name_by_id.get((row.get("StageID") or "").strip(), "").strip()
            if not stage_name:
                continue
            stage_events_by_population[pop_id].append((stage_time, stage_name))
    for events in stage_events_by_population.values():
        events.sort(key=lambda event: event[0])

    default_geography = next((member.geography for member in members if member.geography), "Unknown")

    extra_members: list[PopulationMember] = []
    for pop_id in descendant_ids:
        pop_row = populations_by_id.get(pop_id)
        if pop_row is None:
            continue
        container_id = (pop_row.get("ContainerID") or "").strip()
        container_row = container_rows_by_id.get(container_id, {})
        grouped_row = grouped_rows_by_container_id.get(container_id, {})
        org_unit_id = (container_row.get("OrgUnitID") or "").strip()

        stage_events = stage_events_by_population.get(pop_id, [])
        fishtalk_tokens, aquamind_tokens = canonicalize_stage_sequence(
            [stage_name for _, stage_name in stage_events],
            site=grouped_row.get("Site"),
            container_group=grouped_row.get("ContainerGroup"),
        )

        extra_members.append(
            PopulationMember(
                population_id=pop_id,
                container_id=container_id,
                container_name=(container_row.get("ContainerName") or "").strip(),
                org_unit_name=(
                    (grouped_row.get("Site") or "").strip()
                    or org_unit_name_by_id.get(org_unit_id, "").strip()
                ),
                geography=default_geography,
                start_time=parse_dt((pop_row.get("StartTime") or "").strip()),
                end_time=parse_dt((pop_row.get("EndTime") or "").strip()),
                fishtalk_stages=", ".join(fishtalk_tokens),
                aquamind_stages=", ".join(aquamind_tokens),
            )
        )

    base_members = [member for member in members if member.population_id]
    base_ids = {member.population_id for member in base_members}
    extra_sorted = [
        member for member in extra_members if member.population_id and member.population_id not in base_ids
    ]
    extra_sorted.sort(
        key=lambda member: (
            member.start_time or datetime.min,
            member.end_time or datetime.max,
            member.population_id,
        )
    )
    expanded_members = [*base_members, *extra_sorted]

    print(
        "Expanded SubTransfers descendants: "
        f"+{len(expanded_members) - len(members)} populations "
        f"({len(members)} -> {len(expanded_members)} members)"
    )
    return expanded_members


def parse_batch_key(batch_key: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in batch_key.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Invalid batch_key format: {batch_key}")
    return parts[0], parts[1], parts[2]


def resolve_existing_component_key_for_batch_number(batch_number: str) -> str | None:
    """Return existing PopulationComponent source key for a batch_number, if any.

    This guards idempotent replays when stitching key-space changes but the target
    batch number already exists in AquaMind.
    """
    if not batch_number:
        return None
    batch = Batch.objects.filter(batch_number=batch_number).first()
    if batch is None:
        # Continuation runs can rename batches to "<FW> - <Sea>" while callers may
        # still reference the FW base name. Keep lookup backward-compatible.
        prefixed_name = f"{batch_number} - "
        batch = (
            Batch.objects.filter(batch_number__startswith=prefixed_name)
            .order_by("-updated_at", "-id")
            .first()
        )
    if batch is None:
        return None
    row = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PopulationComponent",
        target_app_label=batch._meta.app_label,
        target_model=batch._meta.model_name,
        target_object_id=batch.pk,
    ).first()
    if row is None:
        return None
    return (row.source_identifier or "").strip() or None


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def is_script_enabled(script_name: str, args: argparse.Namespace) -> bool:
    """Determine whether a pipeline script should run for current CLI args."""
    if args.only_environmental:
        return script_name == "pilot_migrate_component_environmental.py"
    if script_name == "pilot_migrate_component_environmental.py" and args.skip_environmental:
        return False
    if script_name == "pilot_migrate_component_feed_inventory.py" and args.skip_feed_inventory:
        return False
    return True


def evaluate_station_preflight(
    *,
    batch_key: str,
    members: list[PopulationMember],
    csv_dir: str | None,
) -> StationPreflightResult:
    """Cross-check station identity for a batch key before migration."""
    if not csv_dir:
        # No extract path; rely only on members/org_unit names.
        member_sites = {m.org_unit_name.strip() for m in members if m.org_unit_name.strip()}
        return StationPreflightResult(
            input_project_sites=set(),
            ext_input_sites=set(),
            member_sites=member_sites,
            mismatches=[],
        )

    input_name, input_number, year_class = parse_batch_key(batch_key)
    csv_path = Path(csv_dir)

    org_rows = load_csv_rows(csv_path / "org_units.csv")
    org_unit_name_by_id = {
        (row.get("OrgUnitID") or "").strip(): (row.get("Name") or "").strip()
        for row in org_rows
        if (row.get("OrgUnitID") or "").strip()
    }

    # 1) Site from InputProjects (authoritative project metadata).
    input_project_sites: set[str] = set()
    for row in load_csv_rows(csv_path / "input_projects.csv"):
        if (
            (row.get("ProjectName") or "").strip() == input_name
            and (row.get("ProjectNumber") or "").strip() == input_number
            and (row.get("YearClass") or "").strip() == year_class
        ):
            site_id = (row.get("SiteID") or "").strip()
            input_project_sites.add(org_unit_name_by_id.get(site_id, site_id))

    grouped_rows = load_csv_rows(csv_path / "grouped_organisation.csv")
    site_by_container = {
        (row.get("ContainerID") or "").strip(): (row.get("Site") or "").strip()
        for row in grouped_rows
        if (row.get("ContainerID") or "").strip()
    }

    # 2) Site from Ext_Inputs -> Population -> Container.
    pop_ids_for_key: set[str] = set()
    for row in load_csv_rows(csv_path / "ext_inputs.csv"):
        if (
            (row.get("InputName") or "").strip() == input_name
            and (row.get("InputNumber") or "").strip() == input_number
            and (row.get("YearClass") or "").strip() == year_class
        ):
            pop_id = (row.get("PopulationID") or "").strip()
            if pop_id:
                pop_ids_for_key.add(pop_id)

    container_by_population = {}
    for row in load_csv_rows(csv_path / "populations.csv"):
        pop_id = (row.get("PopulationID") or "").strip()
        if pop_id in pop_ids_for_key:
            container_by_population[pop_id] = (row.get("ContainerID") or "").strip()

    ext_input_sites: set[str] = set()
    for pop_id in pop_ids_for_key:
        container_id = container_by_population.get(pop_id, "")
        site = site_by_container.get(container_id, "")
        if site:
            ext_input_sites.add(site)

    # 3) Site from selected member populations in this migration run.
    member_sites = {m.org_unit_name.strip() for m in members if m.org_unit_name.strip()}
    member_container_ids = {m.container_id.strip() for m in members if m.container_id.strip()}
    for container_id in member_container_ids:
        site = site_by_container.get(container_id, "")
        if site:
            member_sites.add(site)

    mismatches: list[str] = []
    if input_project_sites and ext_input_sites and input_project_sites != ext_input_sites:
        mismatches.append(
            f"InputProjects sites {sorted(input_project_sites)} != Ext_Inputs sites {sorted(ext_input_sites)}"
        )
    if input_project_sites and member_sites and not member_sites.issubset(input_project_sites):
        mismatches.append(
            f"Member sites {sorted(member_sites)} not subset of InputProjects sites {sorted(input_project_sites)}"
        )
    if ext_input_sites and member_sites and not member_sites.issubset(ext_input_sites):
        mismatches.append(
            f"Member sites {sorted(member_sites)} not subset of Ext_Inputs sites {sorted(ext_input_sites)}"
        )

    return StationPreflightResult(
        input_project_sites=input_project_sites,
        ext_input_sites=ext_input_sites,
        member_sites=member_sites,
        mismatches=mismatches,
    )


def load_full_lifecycle_populations(batch_key: str, members_file: Path) -> list[PopulationMember]:
    """Load population members from full-lifecycle stitching output."""
    if not members_file.exists():
        raise FileNotFoundError(f"Full lifecycle members file not found: {members_file}")

    members = []
    with members_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("batch_key") != batch_key:
                continue
            members.append(
                PopulationMember(
                    population_id=row.get("population_id", ""),
                    container_id=row.get("container_id", ""),
                    container_name=row.get("container_name", ""),
                    org_unit_name=row.get("org_unit_name", ""),
                    geography=row.get("geography", ""),
                    start_time=parse_dt(row.get("start_time", "")),
                    end_time=parse_dt(row.get("end_time", "")),
                    fishtalk_stages=row.get("fishtalk_stages", ""),
                    aquamind_stages=row.get("aquamind_stages", ""),
                )
            )
    return members


def normalize_population_ids(values: list[str]) -> list[str]:
    """Normalize and dedupe population IDs while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        population_id = (value or "").strip().upper()
        if not population_id or population_id in seen:
            continue
        seen.add(population_id)
        normalized.append(population_id)
    return normalized


def load_subtransfer_rows_for_population_ids(
    population_ids: set[str],
    *,
    use_csv: str | None,
) -> list[dict[str, str]]:
    """Load SubTransfers rows that touch any of the provided population IDs."""
    if not population_ids:
        return []

    normalized_population_ids = {pid.strip().upper() for pid in population_ids if pid}
    if not normalized_population_ids:
        return []

    if use_csv:
        csv_path = Path(use_csv) / "sub_transfers.csv"
        if csv_path.exists():
            rows: list[dict[str, str]] = []
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    endpoints = [
                        (row.get("SourcePopBefore") or "").strip().upper(),
                        (row.get("SourcePopAfter") or "").strip().upper(),
                        (row.get("DestPopBefore") or "").strip().upper(),
                        (row.get("DestPopAfter") or "").strip().upper(),
                    ]
                    if any(endpoint in normalized_population_ids for endpoint in endpoints):
                        rows.append(row)
            return rows

    from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

    in_clause = ",".join(f"'{pid}'" for pid in sorted(normalized_population_ids))
    extractor = BaseExtractor(ExtractionContext(profile="fishtalk_readonly"))
    return extractor._run_sqlcmd(
        query=(
            "SELECT "
            "CONVERT(varchar(36), st.SourcePopBefore) AS SourcePopBefore, "
            "CONVERT(varchar(36), st.SourcePopAfter) AS SourcePopAfter, "
            "CONVERT(varchar(36), st.DestPopBefore) AS DestPopBefore, "
            "CONVERT(varchar(36), st.DestPopAfter) AS DestPopAfter "
            "FROM dbo.SubTransfers st "
            f"WHERE st.SourcePopBefore IN ({in_clause}) "
            f"OR st.SourcePopAfter IN ({in_clause}) "
            f"OR st.DestPopBefore IN ({in_clause}) "
            f"OR st.DestPopAfter IN ({in_clause})"
        ),
        headers=["SourcePopBefore", "SourcePopAfter", "DestPopBefore", "DestPopAfter"],
    )


def filter_full_lifecycle_members_by_anchor_lineage(
    members: list[PopulationMember],
    *,
    use_csv: str | None,
    anchor_population_ids: list[str],
    blocked_population_ids: list[str],
    include_ancestors: bool,
    lineage_max_hops: int,
) -> tuple[list[PopulationMember], dict[str, Any]]:
    """Restrict full-lifecycle members to anchor-scoped lineage subset."""
    normalized_anchor_ids = normalize_population_ids(anchor_population_ids)
    normalized_blocked_ids = normalize_population_ids(blocked_population_ids)
    if not normalized_anchor_ids:
        raise ValueError("Anchor lineage filter requires at least one --sea-anchor-population-id.")
    if normalized_blocked_ids and not normalized_anchor_ids:
        raise ValueError("--sea-block-population-id requires --sea-anchor-population-id.")

    members_by_population_id: dict[str, PopulationMember] = {}
    for member in members:
        pop_id = (member.population_id or "").strip().upper()
        if not pop_id:
            continue
        if pop_id not in members_by_population_id:
            members_by_population_id[pop_id] = member

    candidate_population_ids = set(members_by_population_id.keys())
    missing_anchor_ids = [pid for pid in normalized_anchor_ids if pid not in candidate_population_ids]
    if missing_anchor_ids:
        raise ValueError(
            "Anchor population IDs not present in loaded full-lifecycle members: "
            + ", ".join(missing_anchor_ids[:10])
        )

    subtransfer_rows = load_subtransfer_rows_for_population_ids(
        candidate_population_ids,
        use_csv=use_csv,
    )

    forward_edges: dict[str, set[str]] = defaultdict(set)
    reverse_edges: dict[str, set[str]] = defaultdict(set)

    def add_edge(src: str, dst: str) -> None:
        src_id = (src or "").strip().upper()
        dst_id = (dst or "").strip().upper()
        if not src_id or not dst_id or src_id == dst_id:
            return
        if src_id not in candidate_population_ids or dst_id not in candidate_population_ids:
            return
        forward_edges[src_id].add(dst_id)
        reverse_edges[dst_id].add(src_id)

    for row in subtransfer_rows:
        source_before = row.get("SourcePopBefore", "")
        source_after = row.get("SourcePopAfter", "")
        dest_before = row.get("DestPopBefore", "")
        dest_after = row.get("DestPopAfter", "")

        # Preserve directional lineage through SubTransfers.
        add_edge(source_before, source_after)
        add_edge(source_before, dest_after)
        add_edge(dest_before, dest_after)

    max_hops = max(1, int(lineage_max_hops or 1))

    def traverse(seed_ids: set[str], adjacency: dict[str, set[str]]) -> set[str]:
        seen: set[str] = set(seed_ids)
        frontier: set[str] = set(seed_ids)
        for _ in range(max_hops):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier.update(adjacency.get(node, set()))
            next_frontier -= seen
            if not next_frontier:
                break
            seen.update(next_frontier)
            frontier = next_frontier
        return seen

    seed_set = set(normalized_anchor_ids)
    descendant_ids = traverse(seed_set, forward_edges)
    if include_ancestors:
        ancestor_ids = traverse(seed_set, reverse_edges)
    else:
        ancestor_ids = set(seed_set)

    selected_population_ids = descendant_ids | ancestor_ids | seed_set
    selected_population_ids &= candidate_population_ids

    blocked_in_selected = sorted(set(normalized_blocked_ids).intersection(selected_population_ids))
    if blocked_in_selected:
        raise ValueError(
            "Blocked population IDs would be included by anchor lineage scope: "
            + ", ".join(blocked_in_selected[:10])
        )

    filtered_members = [
        member
        for member in members
        if (member.population_id or "").strip().upper() in selected_population_ids
    ]
    if not filtered_members:
        raise ValueError("Anchor lineage filter produced zero members; refusing to continue.")

    filtered_members.sort(key=lambda member: member.start_time or datetime.min)
    stats = {
        "input_members": len(members),
        "filtered_members": len(filtered_members),
        "anchor_population_ids": normalized_anchor_ids,
        "blocked_population_ids": normalized_blocked_ids,
        "lineage_include_ancestors": include_ancestors,
        "lineage_max_hops": max_hops,
        "subtransfer_rows_considered": len(subtransfer_rows),
        "selected_population_ids": len(selected_population_ids),
    }
    return filtered_members, stats


def full_lifecycle_members_path(batch_key: str) -> Path:
    slug = slugify(batch_key)
    return INPUT_STITCHING_DIR / f"full_lifecycle_population_members_{slug}.csv"


def load_sea_population_ids(batch_key: str, *, use_csv: str | None) -> list[str]:
    """Resolve sea population IDs for the given input batch key."""
    parts = [p.strip() for p in batch_key.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Invalid batch_key format: {batch_key}")
    input_name, input_number, year_class = parts[0], parts[1], parts[2]
    if use_csv:
        csv_path = Path(use_csv) / "ext_inputs.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing ext_inputs.csv: {csv_path}")
        population_ids = []
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (
                    row.get("InputName", "").strip() == input_name
                    and row.get("InputNumber", "").strip() == input_number
                    and row.get("YearClass", "").strip() == year_class
                ):
                    population_ids.append(row.get("PopulationID", ""))
        cleaned = sorted(
            {(pid or "").strip() for pid in population_ids if (pid or "").strip()},
            key=lambda value: value.upper(),
        )
        return cleaned

    # SQL fallback
    from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

    extractor = BaseExtractor(ExtractionContext(profile="fishtalk_readonly"))
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID "
            "FROM dbo.Ext_Inputs_v2 "
            f"WHERE InputName = '{input_name}' AND InputNumber = {input_number} AND YearClass = '{year_class}' "
            "ORDER BY PopulationID"
        ),
        headers=["PopulationID"],
    )
    cleaned = sorted(
        {
            (row.get("PopulationID", "") or "").strip()
            for row in rows
            if (row.get("PopulationID", "") or "").strip()
        },
        key=lambda value: value.upper(),
    )
    return cleaned


def generate_component_csv(
    batch_key: str,
    members: list[PopulationMember],
    output_dir: Path,
    *,
    component_key_override: str | None = None,
) -> Path:
    """Generate a component-style population_members.csv for the existing migration scripts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use a sanitized batch key as component_id
    component_id = batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")
    component_key = component_key_override or (members[0].population_id if members else batch_key)

    csv_path = output_dir / "population_members.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "component_id",
                "component_key",
                "population_id",
                "population_name",
                "container_id",
                "start_time",
                "end_time",
                "first_stage",
                "last_stage",
            ],
        )
        writer.writeheader()

        for member in members:
            # Parse stages to get first and last
            stages = member.fishtalk_stages.split(", ") if member.fishtalk_stages else []
            first_stage = stages[0] if stages else ""
            last_stage = stages[-1] if stages else ""

            writer.writerow(
                {
                    "component_id": component_id,
                    "component_key": component_key,
                    "population_id": member.population_id,
                    "population_name": member.container_name,  # Use container name as population name
                    "container_id": member.container_id,
                    "start_time": member.start_time.isoformat(sep=" ") if member.start_time else "",
                    "end_time": member.end_time.isoformat(sep=" ") if member.end_time else "",
                    "first_stage": first_stage,
                    "last_stage": last_stage,
                }
            )

    # Also generate a minimal components.csv
    components_path = output_dir / "components.csv"
    with components_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "component_id",
                "component_key",
                "population_count",
                "earliest_start_time",
                "latest_end_time",
                "representative_population_id",
                "representative_name",
                "contains_freshwater_stages",
                "contains_sea_stages",
                "transportpop_population_count",
            ],
        )
        writer.writeheader()

        starts = [m.start_time for m in members if m.start_time]
        ends = [m.end_time for m in members if m.end_time]
        earliest = min(starts) if starts else None
        latest = max(ends) if ends else None

        # Determine if contains FW and sea stages
        all_stages = " ".join(m.aquamind_stages for m in members)
        has_fw = any(s in all_stages for s in ["Egg&Alevin", "Fry", "Parr", "Smolt"])
        has_sea = any(s in all_stages for s in ["Post-Smolt", "Adult"])

        writer.writerow(
            {
                "component_id": component_id,
                "component_key": component_key,
                "population_count": len(members),
                "earliest_start_time": earliest.isoformat(sep=" ") if earliest else "",
                "latest_end_time": latest.isoformat(sep=" ") if latest else "",
                "representative_population_id": members[0].population_id if members else "",
                "representative_name": members[0].container_name if members else "",
                "contains_freshwater_stages": has_fw,
                "contains_sea_stages": has_sea,
                "transportpop_population_count": 0,
            }
        )

    return csv_path


def run_migration_script(
    script_name: str,
    component_key: str,
    report_dir: Path,
    *,
    use_csv: str | None = None,
    use_sqlite: str | None = None,
    dry_run: bool = False,
    batch_number: str | None = None,
    migration_profile: str | None = None,
    merge_existing_component_map: bool = False,
    external_mixing_status_multiplier: float | None = None,
    lifecycle_frontier_window_hours: int | None = None,
    skip_synthetic_stage_transitions: bool = False,
    transfer_edge_scope: str = "source-in-scope",
    timeout_seconds: int = 600,
    extra_env: dict[str, str] | None = None,
    announce: bool = True,
) -> ScriptRunResult:
    """Run a migration script with the given component key."""
    started = time.perf_counter()
    script_path = PROJECT_ROOT / "scripts" / "migration" / "tools" / script_name

    if not script_path.exists():
        print(f"  [SKIP] Script not found: {script_path}")
        return ScriptRunResult(
            script_name=script_name,
            success=True,
            duration_seconds=time.perf_counter() - started,
        )

    if use_csv and script_name not in CSV_SUPPORTED_SCRIPTS:
        print(f"  [SKIP] {script_name} does not support --use-csv; skipping to honor CSV-only mode")
        return ScriptRunResult(
            script_name=script_name,
            success=True,
            duration_seconds=time.perf_counter() - started,
        )

    cmd = [
        sys.executable,
        str(script_path),
        "--component-key",
        component_key,
        "--report-dir",
        str(report_dir),
    ]

    if script_name == "pilot_migrate_component.py" and batch_number:
        cmd.extend(["--batch-number", batch_number])
    if script_name == "pilot_migrate_component.py" and migration_profile:
        cmd.extend(["--migration-profile", migration_profile])
    if script_name == "pilot_migrate_component.py" and merge_existing_component_map:
        cmd.append("--merge-existing-component-map")
    if script_name == "pilot_migrate_component.py" and external_mixing_status_multiplier is not None:
        cmd.extend(
            [
                "--external-mixing-status-multiplier",
                str(external_mixing_status_multiplier),
            ]
        )
    if script_name == "pilot_migrate_component.py" and lifecycle_frontier_window_hours is not None:
        cmd.extend(
            [
                "--lifecycle-frontier-window-hours",
                str(lifecycle_frontier_window_hours),
            ]
        )

    if script_name == "pilot_migrate_component_transfers.py":
        cmd.append("--use-subtransfers")
        cmd.extend(["--transfer-edge-scope", transfer_edge_scope])
        if skip_synthetic_stage_transitions:
            cmd.append("--skip-synthetic-stage-transitions")
        else:
            cmd.append("--include-synthetic-stage-transitions")

    if use_csv and script_name in CSV_SUPPORTED_SCRIPTS:
        cmd.extend(["--use-csv", use_csv])
    elif use_csv:
        print(f"  [INFO] {script_name} does not support --use-csv; using SQL")
    if (
        use_sqlite
        and script_name == "pilot_migrate_component_environmental.py"
    ):
        cmd.extend(["--use-sqlite", use_sqlite])

    if dry_run:
        cmd.append("--dry-run")

    if announce:
        print(f"  Running: {script_name}...")
    env = os.environ.copy()
    env["SKIP_CELERY_SIGNALS"] = "1"
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if extra_env:
        env.update(extra_env)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration = time.perf_counter() - started

        if result.returncode != 0:
            print(f"  [ERROR] {script_name} failed with code {result.returncode}")
            print(f"  STDOUT: {result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout}")
            print(f"  STDERR: {result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr}")
            return ScriptRunResult(script_name=script_name, success=False, duration_seconds=duration)

        if announce:
            lines = result.stdout.strip().split("\n")
            for line in lines[-5:]:
                print(f"    {line}")

        return ScriptRunResult(script_name=script_name, success=True, duration_seconds=duration)

    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - started
        print(f"  [ERROR] {script_name} timed out after {timeout_seconds} seconds")
        return ScriptRunResult(script_name=script_name, success=False, duration_seconds=duration)
    except Exception as e:
        duration = time.perf_counter() - started
        print(f"  [ERROR] {script_name} failed: {e}")
        return ScriptRunResult(script_name=script_name, success=False, duration_seconds=duration)


def build_parallel_env(parallel_workers: int, parallel_blas_threads: int) -> dict[str, str]:
    """Thread caps to avoid oversubscription when running many CSV-heavy subprocesses."""
    if parallel_workers <= 1:
        return {}
    threads = str(max(1, parallel_blas_threads))
    return {
        "OMP_NUM_THREADS": threads,
        "OPENBLAS_NUM_THREADS": threads,
        "MKL_NUM_THREADS": threads,
        "VECLIB_MAXIMUM_THREADS": threads,
        "NUMEXPR_MAX_THREADS": threads,
    }


def build_full_lifecycle_members(
    batch_key: str,
    *,
    use_csv: str | None,
    include_fw_batches: list[str],
    skip_population_links: bool,
    heuristic_fw_sea: bool,
    heuristic_window_days: int,
    heuristic_min_score: int,
    heuristic_include_smolt: bool,
    max_fw_batches: int,
    max_pre_smolt_batches: int,
) -> bool:
    script_path = PROJECT_ROOT / "scripts" / "migration" / "analysis" / "input_full_lifecycle_stitching.py"
    if not script_path.exists():
        print(f"[ERROR] Missing full-lifecycle stitcher: {script_path}")
        return False

    cmd = [
        sys.executable,
        str(script_path),
        "--batch-key",
        batch_key,
        "--output-dir",
        str(INPUT_STITCHING_DIR),
    ]
    if use_csv:
        cmd.extend(["--csv-dir", use_csv])
    if skip_population_links:
        cmd.append("--skip-population-links")
    if max_fw_batches is not None:
        cmd.extend(["--max-fw-batches", str(max_fw_batches)])
    if max_pre_smolt_batches is not None:
        cmd.extend(["--max-pre-smolt-batches", str(max_pre_smolt_batches)])
    for fw_batch in include_fw_batches:
        cmd.extend(["--include-fw-batch", fw_batch])
    if heuristic_fw_sea:
        cmd.append("--heuristic-fw-sea")
        cmd.extend(["--heuristic-window-days", str(heuristic_window_days)])
        cmd.extend(["--heuristic-min-score", str(heuristic_min_score)])
        if heuristic_include_smolt:
            cmd.append("--heuristic-include-smolt")

    print("\nBuilding full-lifecycle population members...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("[ERROR] Full-lifecycle stitching timed out after 600 seconds")
        return False

    if result.returncode != 0:
        print("[ERROR] Full-lifecycle stitching failed")
        print(f"STDOUT: {result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout}")
        print(f"STDERR: {result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr}")
        return False

    print(result.stdout.strip().split("\n")[-1])
    return True


def list_available_batches() -> None:
    """List available input batches from the stitching report."""
    batches_file = INPUT_STITCHING_DIR / "input_batches.csv"
    if not batches_file.exists():
        print(f"No input batches file found at: {batches_file}")
        print("Run input_based_stitching_report.py first.")
        return

    print("\nAvailable Input-Based Batches:")
    print("=" * 100)
    print(f"{'Batch Key':<50} {'Pops':>6} {'Fish':>12} {'Days':>5} {'Valid':>6} {'Stages':<30}")
    print("-" * 100)

    with batches_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= 30:
                print("... (showing first 30 batches)")
                break
            
            batch_key = row.get("batch_key", "")[:50]
            pop_count = row.get("population_count", "0")
            total_fish = row.get("total_fish", "0")
            span_days = row.get("span_days", "0")
            is_valid = "Yes" if row.get("is_valid", "").lower() == "true" else "No"
            stages = row.get("aquamind_stages", "")[:30]
            
            print(f"{batch_key:<50} {pop_count:>6} {total_fish:>12} {span_days:>5} {is_valid:>6} {stages:<30}")
            count += 1

    print("-" * 100)
    print(f"\nFor recommended batches, see: {INPUT_STITCHING_DIR / 'recommended_batches.csv'}")


def _first_present_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
    return None


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def resolve_scope_batch_keys(scope_file: Path) -> tuple[list[str], dict[str, int]]:
    """Resolve batch keys from a scope CSV."""
    if not scope_file.exists():
        raise FileNotFoundError(f"Scope file does not exist: {scope_file}")

    with scope_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError(f"Scope file has no header row: {scope_file}")

        rows = list(reader)
        stats = {
            "scope_rows": len(rows),
            "rows_with_batch_key": 0,
            "rows_without_batch_key": 0,
            "population_rows": 0,
            "population_rows_unresolved": 0,
        }

        batch_col = _first_present_column(fieldnames, ["batch_key", "BatchKey", "batchKey"])
        pop_col = _first_present_column(fieldnames, ["population_id", "PopulationID", "populationId"])

        if batch_col:
            batch_keys_raw: list[str] = []
            for row in rows:
                value = (row.get(batch_col) or "").strip()
                if value:
                    stats["rows_with_batch_key"] += 1
                    batch_keys_raw.append(value)
                else:
                    stats["rows_without_batch_key"] += 1
            batch_keys = _dedupe_preserve_order(batch_keys_raw)
            if batch_keys:
                return batch_keys, stats

        if not pop_col:
            raise ValueError(
                "Scope file must include either batch_key or population id column "
                "(population_id / PopulationID)."
            )

        population_ids = _dedupe_preserve_order([(row.get(pop_col) or "").strip() for row in rows])
        stats["population_rows"] = len(population_ids)

        members_file = INPUT_STITCHING_DIR / "input_population_members.csv"
        if not members_file.exists():
            raise FileNotFoundError(
                "input_population_members.csv is required for population-id scope mapping. "
                f"Missing: {members_file}"
            )

        with members_file.open("r", encoding="utf-8", newline="") as f:
            member_reader = csv.DictReader(f)
            member_fields = member_reader.fieldnames or []
            member_pop_col = _first_present_column(
                member_fields, ["population_id", "PopulationID", "populationId"]
            )
            member_batch_col = _first_present_column(
                member_fields, ["batch_key", "BatchKey", "batchKey"]
            )
            if not member_pop_col or not member_batch_col:
                raise ValueError(
                    "input_population_members.csv is missing required columns "
                    "population_id and/or batch_key."
                )

            pop_to_batch: dict[str, str] = {}
            for row in member_reader:
                pop_id = (row.get(member_pop_col) or "").strip()
                batch_key = (row.get(member_batch_col) or "").strip()
                if pop_id and batch_key and pop_id not in pop_to_batch:
                    pop_to_batch[pop_id] = batch_key

        resolved_keys: list[str] = []
        for pop_id in population_ids:
            batch_key = pop_to_batch.get(pop_id)
            if batch_key:
                resolved_keys.append(batch_key)
            else:
                stats["population_rows_unresolved"] += 1

        return _dedupe_preserve_order(resolved_keys), stats


def run_scope_batches(args: argparse.Namespace, *, scope_file: Path) -> int:
    batch_keys, stats = resolve_scope_batch_keys(scope_file)
    if not batch_keys:
        print(f"[ERROR] No batch keys resolved from scope file: {scope_file}")
        print(f"Scope stats: {stats}")
        return 1

    if args.batch_number:
        print(
            "[ERROR] --batch-number cannot be combined with --scope-file "
            "(would force same batch number across many batches)."
        )
        return 1

    print("\n" + "=" * 70)
    print("SCOPE-BASED INPUT MIGRATION")
    print("=" * 70)
    print(f"Scope file: {scope_file}")
    print(f"Resolved batch keys: {len(batch_keys)}")
    print(f"Scope stats: {stats}")

    script_path = Path(__file__).resolve()
    failures: list[str] = []

    # Parent performs freshness preflight once; child invocations skip it.
    base_cmd = [
        sys.executable,
        str(script_path),
        "--skip-extract-freshness-preflight",
        "--migration-profile",
        args.migration_profile,
        "--parallel-workers",
        str(args.parallel_workers),
        "--parallel-blas-threads",
        str(args.parallel_blas_threads),
        "--script-timeout-seconds",
        str(args.script_timeout_seconds),
    ]

    if args.use_csv:
        base_cmd.extend(["--use-csv", args.use_csv])
    if args.use_sqlite:
        base_cmd.extend(["--use-sqlite", args.use_sqlite])
    if args.skip_environmental:
        base_cmd.append("--skip-environmental")
    if args.skip_feed_inventory:
        base_cmd.append("--skip-feed-inventory")
    if args.only_environmental:
        base_cmd.append("--only-environmental")
    if args.extract_fail_on_warnings:
        base_cmd.append("--extract-fail-on-warnings")
    if not args.extract_enforce_operation_stage_lag:
        base_cmd.append("--extract-allow-operation-stage-lag")
    if args.full_lifecycle:
        base_cmd.append("--full-lifecycle")
    if args.full_lifecycle_rebuild:
        base_cmd.append("--full-lifecycle-rebuild")
    if args.skip_population_links:
        base_cmd.append("--skip-population-links")
    if args.heuristic_fw_sea:
        base_cmd.append("--heuristic-fw-sea")
    if args.heuristic_include_smolt:
        base_cmd.append("--heuristic-include-smolt")
    if args.expected_site:
        base_cmd.extend(["--expected-site", args.expected_site])
    if args.allow_station_mismatch:
        base_cmd.append("--allow-station-mismatch")
    if args.include_synthetic_stage_transitions:
        base_cmd.append("--include-synthetic-stage-transitions")
    if args.transfer_edge_scope:
        base_cmd.extend(["--transfer-edge-scope", args.transfer_edge_scope])
    if args.expand_subtransfer_descendants:
        base_cmd.append("--expand-subtransfer-descendants")
    if args.external_mixing_status_multiplier is not None:
        base_cmd.extend(
            ["--external-mixing-status-multiplier", str(args.external_mixing_status_multiplier)]
        )
    if args.lifecycle_frontier_window_hours is not None:
        base_cmd.extend(
            ["--lifecycle-frontier-window-hours", str(args.lifecycle_frontier_window_hours)]
        )
    if args.dry_run:
        base_cmd.append("--dry-run")
    if args.full_lifecycle:
        base_cmd.extend(["--max-fw-batches", str(args.max_fw_batches)])
        base_cmd.extend(["--max-pre-smolt-batches", str(args.max_pre_smolt_batches)])
        base_cmd.extend(["--heuristic-window-days", str(args.heuristic_window_days)])
        base_cmd.extend(["--heuristic-min-score", str(args.heuristic_min_score)])
        if args.no_continuation_batch_name_concat:
            base_cmd.append("--no-continuation-batch-name-concat")
        for fw_batch in args.include_fw_batch:
            base_cmd.extend(["--include-fw-batch", fw_batch])
        for anchor_population_id in args.sea_anchor_population_id:
            base_cmd.extend(["--sea-anchor-population-id", anchor_population_id])
        for blocked_population_id in args.sea_block_population_id:
            base_cmd.extend(["--sea-block-population-id", blocked_population_id])
        base_cmd.extend(["--lineage-max-hops", str(args.lineage_max_hops)])
        if args.lineage_descendants_only:
            base_cmd.append("--lineage-descendants-only")
        if args.allow_full_sea_component_for_continuation:
            base_cmd.append("--allow-full-sea-component-for-continuation")

    for idx, batch_key in enumerate(batch_keys, start=1):
        cmd = [*base_cmd, "--batch-key", batch_key]
        print(f"\n[{idx}/{len(batch_keys)}] RUN {batch_key}")
        started = time.perf_counter()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        elapsed = time.perf_counter() - started

        if result.returncode == 0:
            print(f"[{idx}/{len(batch_keys)}] OK {elapsed:.1f}s")
            continue

        print(f"[{idx}/{len(batch_keys)}] ERROR {elapsed:.1f}s")
        failures.append(batch_key)
        if result.stdout:
            stdout_tail = "\n".join(result.stdout.strip().splitlines()[-20:])
            if stdout_tail:
                print(stdout_tail)
        if result.stderr:
            stderr_tail = "\n".join(result.stderr.strip().splitlines()[-20:])
            if stderr_tail:
                print(stderr_tail)

    print("\n" + "=" * 70)
    print("SCOPE MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Batches attempted: {len(batch_keys)}")
    print(f"Failures: {len(failures)}")
    if failures:
        print("Failed batch keys:")
        for batch_key in failures:
            print(f"  - {batch_key}")
        return 1

    print("[SUCCESS] Scope migration completed!")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate an input-based batch (Ext_Inputs_v2) from FishTalk to AquaMind"
    )
    parser.add_argument(
        "--batch-key",
        help="Input batch key in format 'InputName|InputNumber|YearClass' (e.g., 'Heyst 2018|1|2018')",
    )
    parser.add_argument(
        "--scope-file",
        type=str,
        default=None,
        help=(
            "Optional CSV scope input. Supported columns: batch_key, or "
            "population_id/PopulationID (mapped through input_population_members.csv)."
        ),
    )
    parser.add_argument(
        "--batch-number",
        help="Override the generated batch number",
    )
    parser.add_argument(
        "--migration-profile",
        default="fw_default",
        choices=MIGRATION_PROFILE_NAMES,
        help=(
            "Migration profile preset passed to pilot_migrate_component.py "
            "(default: fw_default)."
        ),
    )
    parser.add_argument(
        "--list-batches",
        action="store_true",
        help="List available input batches and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing to database",
    )
    parser.add_argument(
        "--skip-environmental",
        action="store_true",
        help="Skip environmental data migration (can be slow)",
    )
    parser.add_argument(
        "--skip-feed-inventory",
        action="store_true",
        help="Skip feed inventory migration",
    )
    parser.add_argument(
        "--only-environmental",
        action="store_true",
        help=(
            "Run only pilot_migrate_component_environmental.py for each batch "
            "(still builds component scope and performs station preflight)."
        ),
    )
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    parser.add_argument(
        "--use-sqlite",
        type=str,
        metavar="SQLITE_PATH",
        help=(
            "Optional environmental SQLite index forwarded to "
            "pilot_migrate_component_environmental.py. "
            "Recommended for large-scope environmental replays."
        ),
    )
    parser.add_argument(
        "--skip-extract-freshness-preflight",
        action="store_true",
        help=(
            "Skip CSV extract freshness/cutoff guard. "
            "Not recommended outside diagnostics."
        ),
    )
    parser.add_argument(
        "--extract-horizon-date",
        default=DEFAULT_BACKUP_HORIZON_DATE,
        help=(
            "Required horizon date (YYYY-MM-DD) for extract preflight. "
            "status_values/sub_transfers max dates must be >= this. "
            f"(default: {DEFAULT_BACKUP_HORIZON_DATE})"
        ),
    )
    parser.add_argument(
        "--extract-max-status-subtransfer-skew-hours",
        type=int,
        default=24,
        help=(
            "Preflight threshold for max skew between status_values and "
            "sub_transfers max timestamps (default: 24)."
        ),
    )
    parser.add_argument(
        "--extract-max-operation-stage-lag-days",
        type=int,
        default=14,
        help=(
            "Preflight threshold for operation_stage_changes lag behind "
            "status/sub anchor in days (default: 14)."
        ),
    )
    extract_lag_group = parser.add_mutually_exclusive_group()
    extract_lag_group.add_argument(
        "--extract-enforce-operation-stage-lag",
        dest="extract_enforce_operation_stage_lag",
        action="store_true",
        help=(
            "Treat operation_stage_changes lag threshold breaches as failures "
            "(default)."
        ),
    )
    extract_lag_group.add_argument(
        "--extract-allow-operation-stage-lag",
        dest="extract_enforce_operation_stage_lag",
        action="store_false",
        help=(
            "Downgrade operation_stage_changes lag threshold breaches to warnings."
        ),
    )
    parser.set_defaults(extract_enforce_operation_stage_lag=True)
    parser.add_argument(
        "--extract-fail-on-warnings",
        action="store_true",
        help="Fail extract preflight when warnings are present.",
    )
    parser.add_argument(
        "--full-lifecycle",
        action="store_true",
        help="Use full-lifecycle stitched population members (FW + Sea)",
    )
    parser.add_argument(
        "--full-lifecycle-rebuild",
        action="store_true",
        help="Rebuild full-lifecycle stitching output before migrating",
    )
    parser.add_argument(
        "--include-fw-batch",
        action="append",
        default=[],
        help="Explicit FW batch key(s) to include when building full-lifecycle output",
    )
    parser.add_argument(
        "--no-continuation-batch-name-concat",
        action="store_true",
        help=(
            "Disable default FW->Sea display naming for linked continuation runs. "
            "Default behavior renames to '<FW batch> - <Sea batch>' through normal "
            "batch save paths so history/audit records are written."
        ),
    )
    parser.add_argument(
        "--sea-anchor-population-id",
        action="append",
        default=[],
        help=(
            "Anchor sea PopulationID(s) for linked FW->Sea continuation. "
            "When set, full-lifecycle members are lineage-scoped to these anchors."
        ),
    )
    parser.add_argument(
        "--sea-block-population-id",
        action="append",
        default=[],
        help=(
            "PopulationID(s) that must NOT be included in selected continuation members. "
            "Used with --sea-anchor-population-id to hard-block known conflicting candidates."
        ),
    )
    parser.add_argument(
        "--lineage-max-hops",
        type=int,
        default=24,
        help=(
            "Max SubTransfers graph hops when deriving anchor lineage subset "
            "(default: 24)."
        ),
    )
    parser.add_argument(
        "--lineage-descendants-only",
        action="store_true",
        help=(
            "When anchor lineage scope is enabled, include descendants only "
            "(default includes ancestors and descendants)."
        ),
    )
    parser.add_argument(
        "--allow-full-sea-component-for-continuation",
        action="store_true",
        help=(
            "Override safety guard and allow linked continuation runs to ingest "
            "full sea-component membership without anchor scoping."
        ),
    )
    parser.add_argument(
        "--max-fw-batches",
        type=int,
        default=2,
        help="Limit selected FW batches in full-lifecycle stitching (default: 2)",
    )
    parser.add_argument(
        "--max-pre-smolt-batches",
        type=int,
        default=2,
        help="Limit pre-smolt batches in full-lifecycle stitching (default: 2)",
    )
    parser.add_argument(
        "--skip-population-links",
        action="store_true",
        help="Skip PopulationLink when building full-lifecycle output",
    )
    parser.add_argument(
        "--heuristic-fw-sea",
        action="store_true",
        help="Non-canonical: enable heuristic FW→Sea stitching when rebuilding full-lifecycle output",
    )
    parser.add_argument("--heuristic-window-days", type=int, default=60, help="Heuristic FW window in days")
    parser.add_argument("--heuristic-min-score", type=int, default=70, help="Minimum heuristic score to accept")
    parser.add_argument(
        "--heuristic-include-smolt",
        action="store_true",
        help="Allow Smolt halls as FW candidates (default: Post-Smolt only)",
    )
    parser.add_argument(
        "--expected-site",
        help="Optional exact site name guard (e.g., 'S21 Viðareiði'); migration aborts on mismatch",
    )
    parser.add_argument(
        "--allow-station-mismatch",
        action="store_true",
        help="Proceed even if station preflight detects site mismatches",
    )
    parser.add_argument(
        "--include-synthetic-stage-transitions",
        action="store_true",
        help=(
            "Force synthetic assignment-derived stage-transition workflows/actions "
            "during transfer migration regardless of run mode."
        ),
    )
    parser.add_argument(
        "--transfer-edge-scope",
        choices=["source-in-scope", "internal-only"],
        default="source-in-scope",
        help=(
            "Pass-through for pilot_migrate_component_transfers.py. "
            "SubTransfers are expanded to root-source conservation edges first. "
            "Use 'source-in-scope' as the safest FW default; use 'internal-only' "
            "only when you intentionally want to drop expanded destinations "
            "outside the migrated component."
        ),
    )
    parser.add_argument(
        "--expand-subtransfer-descendants",
        action="store_true",
        help=(
            "Expand stitched batch members recursively via SubTransfers descendants "
            "when running in --use-csv mode."
        ),
    )
    parser.add_argument(
        "--external-mixing-status-multiplier",
        type=float,
        help=(
            "Optional pass-through for pilot_migrate_component.py. "
            "When set, overrides conservative status fallback threshold for "
            "external-mixing populations."
        ),
    )
    parser.add_argument(
        "--lifecycle-frontier-window-hours",
        type=int,
        help=(
            "Optional pass-through for pilot_migrate_component.py lifecycle-stage "
            "selection near cutoff (hours)."
        ),
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help=(
            "Run post-transfer migration scripts in parallel with this worker count "
            "(default: 1 = fully sequential)."
        ),
    )
    parser.add_argument(
        "--parallel-blas-threads",
        type=int,
        default=1,
        help=(
            "Per-subprocess BLAS/vecLib thread cap when --parallel-workers > 1 "
            "(default: 1)."
        ),
    )
    parser.add_argument(
        "--script-timeout-seconds",
        type=int,
        default=900,
        help="Timeout per migration script subprocess (default: 900).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.list_batches:
        list_available_batches()
        return 0

    if not args.batch_key and not args.scope_file:
        print("Error: provide --batch-key or --scope-file")
        print("Use --list-batches to see available batches")
        return 1

    if args.parallel_workers < 1:
        print("Error: --parallel-workers must be >= 1")
        return 1
    if args.parallel_blas_threads < 1:
        print("Error: --parallel-blas-threads must be >= 1")
        return 1
    if args.script_timeout_seconds < 30:
        print("Error: --script-timeout-seconds must be >= 30")
        return 1
    if args.only_environmental and args.skip_environmental:
        print("Error: --only-environmental cannot be combined with --skip-environmental")
        return 1
    if args.use_sqlite and not Path(args.use_sqlite).exists():
        print(f"Error: --use-sqlite path does not exist: {args.use_sqlite}")
        return 1

    if args.use_csv and not args.skip_extract_freshness_preflight:
        freshness = evaluate_extract_freshness(
            csv_dir=Path(args.use_csv),
            horizon_date=args.extract_horizon_date,
            max_status_subtransfer_skew_hours=args.extract_max_status_subtransfer_skew_hours,
            max_operation_stage_lag_days=args.extract_max_operation_stage_lag_days,
            enforce_operation_stage_lag=args.extract_enforce_operation_stage_lag,
            fail_on_warnings=args.extract_fail_on_warnings,
        )
        print_extract_freshness_summary(freshness)
        if not freshness.passed:
            print(
                "\n[ERROR] Extract freshness preflight failed. "
                "Aborting migration to avoid stale/cutoff-debug loops."
            )
            return 1

    if args.scope_file and not args.batch_key:
        return run_scope_batches(args, scope_file=Path(args.scope_file))
    if args.scope_file and args.batch_key:
        print("[INFO] --scope-file provided with --batch-key; running single batch mode.")

    batch_key = args.batch_key

    print(f"\n{'='*70}")
    print(f"INPUT-BASED BATCH MIGRATION")
    print("=" * 70)
    print(f"Batch Key: {batch_key}")
    print(f"Migration Profile: {args.migration_profile}")
    print()

    # Load batch info
    batch_info = load_input_batch_info(batch_key, use_csv=args.use_csv)
    if not batch_info:
        print(f"[ERROR] Batch not found: {batch_key}")
        print("Use --list-batches to see available batches")
        return 1

    print(f"Input Name: {batch_info.input_name}")
    print(f"Year Class: {batch_info.year_class}")
    print(f"Populations: {batch_info.population_count}")
    print(f"Total Fish: {batch_info.total_fish:,.0f}")
    print(f"Time Span: {batch_info.span_days} days")
    print(f"Stages: {batch_info.aquamind_stages}")
    print(f"Geography: {batch_info.geographies}")
    print(f"Valid: {'Yes' if batch_info.is_valid else 'No'}")

    if not batch_info.is_valid:
        print(f"\n[WARNING] This batch is flagged as INVALID")
        print("Consider using a validated batch from recommended_batches.csv")

    # Load population members
    print(f"\nLoading populations for batch {batch_key}...")
    if args.full_lifecycle:
        members_file = full_lifecycle_members_path(batch_key)
        if args.full_lifecycle_rebuild or not members_file.exists():
            ok = build_full_lifecycle_members(
                batch_key,
                use_csv=args.use_csv,
                include_fw_batches=args.include_fw_batch,
                skip_population_links=args.skip_population_links,
                heuristic_fw_sea=args.heuristic_fw_sea,
                heuristic_window_days=args.heuristic_window_days,
                heuristic_min_score=args.heuristic_min_score,
                heuristic_include_smolt=args.heuristic_include_smolt,
                max_fw_batches=args.max_fw_batches,
                max_pre_smolt_batches=args.max_pre_smolt_batches,
            )
            if not ok:
                return 1
        members = load_full_lifecycle_populations(batch_key, members_file)
    else:
        members = load_input_populations(
            batch_key,
            use_csv=args.use_csv,
            expand_subtransfer_descendants=args.expand_subtransfer_descendants,
        )

    if not members:
        print(f"[ERROR] No populations found for batch key: {batch_key}")
        return 1

    raw_member_count = len(members)
    is_linked_full_lifecycle_continuation_run = bool(
        args.full_lifecycle and args.include_fw_batch and args.batch_number
    )
    anchor_population_ids = normalize_population_ids(args.sea_anchor_population_id)
    blocked_population_ids = normalize_population_ids(args.sea_block_population_id)

    if (anchor_population_ids or blocked_population_ids) and not args.full_lifecycle:
        print(
            "[ERROR] --sea-anchor-population-id/--sea-block-population-id require --full-lifecycle mode."
        )
        return 1

    if (
        is_linked_full_lifecycle_continuation_run
        and not args.allow_full_sea_component_for_continuation
        and not anchor_population_ids
    ):
        print(
            "[ERROR] Linked full-lifecycle continuation requires anchor lineage scope. "
            "Provide at least one --sea-anchor-population-id or explicitly set "
            "--allow-full-sea-component-for-continuation."
        )
        return 1

    if anchor_population_ids or blocked_population_ids:
        try:
            members, lineage_scope_stats = filter_full_lifecycle_members_by_anchor_lineage(
                members,
                use_csv=args.use_csv,
                anchor_population_ids=anchor_population_ids,
                blocked_population_ids=blocked_population_ids,
                include_ancestors=not args.lineage_descendants_only,
                lineage_max_hops=args.lineage_max_hops,
            )
        except ValueError as exc:
            print(f"[ERROR] Anchor lineage scope failed: {exc}")
            return 1

        print(
            "  Applied anchor lineage scope: "
            f"{lineage_scope_stats['filtered_members']}/{lineage_scope_stats['input_members']} populations "
            f"(anchors={len(lineage_scope_stats['anchor_population_ids'])}, "
            f"blocked={len(lineage_scope_stats['blocked_population_ids'])}, "
            f"hops={lineage_scope_stats['lineage_max_hops']}, "
            f"include_ancestors={lineage_scope_stats['lineage_include_ancestors']})"
        )

    print(f"  Found {len(members)} populations (raw={raw_member_count})")

    # Show stage coverage
    stages = set()
    for m in members:
        stages.update(s.strip() for s in m.aquamind_stages.split(",") if s.strip())
    print(f"  AquaMind stages: {', '.join(sorted(stages)) if stages else 'None'}")

    # Show geography
    geos = set(m.geography for m in members if m.geography and m.geography != "Unknown")
    print(f"  Geographies: {', '.join(sorted(geos)) if geos else 'Unknown'}")

    # Station/site preflight: prevents accidental migration into the wrong station set.
    preflight = evaluate_station_preflight(batch_key=batch_key, members=members, csv_dir=args.use_csv)
    print("\nStation preflight:")
    print(f"  InputProjects sites: {sorted(preflight.input_project_sites) or ['n/a']}")
    print(f"  Ext_Inputs sites: {sorted(preflight.ext_input_sites) or ['n/a']}")
    print(f"  Member-derived sites: {sorted(preflight.member_sites) or ['n/a']}")

    if args.expected_site:
        expected = args.expected_site.strip()
        expected_ok = (
            expected in preflight.member_sites
            and (not preflight.input_project_sites or expected in preflight.input_project_sites)
            and (not preflight.ext_input_sites or expected in preflight.ext_input_sites)
        )
        if not expected_ok:
            print(f"\n[ERROR] --expected-site '{expected}' does not match station evidence.")
            return 1

    if preflight.mismatches:
        print("\n[ERROR] Station preflight mismatches detected:")
        for issue in preflight.mismatches:
            print(f"  - {issue}")
        if not args.allow_station_mismatch:
            print("Use --allow-station-mismatch to override intentionally.")
            return 1
        print("[WARNING] Proceeding due to --allow-station-mismatch override.")

    # Generate component-style CSV
    # Use sanitized batch key for directory name
    dir_name = batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")
    output_dir = BATCH_OUTPUT_DIR / dir_name
    print(f"\nGenerating component CSV in: {output_dir}")
    # Ensure deterministic ordering
    members = sorted(
        members,
        key=lambda m: (m.start_time or datetime.min, (m.population_id or "")),
    )
    batch_number_override = args.batch_number or batch_info.input_name
    if (
        not args.batch_number
        and has_duplicate_input_name(batch_info.input_name)
        and batch_info.input_number
    ):
        batch_number_override = f"{batch_info.input_name} [{batch_info.input_number}]"

    component_key_override = None
    reuses_existing_component_map = False
    if args.full_lifecycle:
        # Continuation mode: if caller provided explicit FW linkage context and
        # target batch number, keep writing into that existing FW batch
        # component instead of creating a sea-keyed batch component.
        if args.include_fw_batch and args.batch_number:
            existing_component_key = resolve_existing_component_key_for_batch_number(
                args.batch_number
            )
            if existing_component_key:
                component_key_override = existing_component_key
                reuses_existing_component_map = True
                print(
                    "[INFO] Linked full-lifecycle run reusing existing component key "
                    f"{existing_component_key} for continuation batch_number "
                    f"'{args.batch_number}'"
                )
        if component_key_override is None:
            if anchor_population_ids:
                component_key_override = sorted(anchor_population_ids, key=str.upper)[0]
                print(
                    "[INFO] Anchor-scoped continuation key: "
                    f"{component_key_override}"
                )
            else:
                sea_population_ids = load_sea_population_ids(batch_key, use_csv=args.use_csv)
                if sea_population_ids:
                    component_key_override = sea_population_ids[0]
    if component_key_override is None:
        batch_number_candidates = [batch_number_override, batch_info.input_name]
        for target_batch_number in batch_number_candidates:
            if not target_batch_number:
                continue
            existing_component_key = resolve_existing_component_key_for_batch_number(
                target_batch_number
            )
            if not existing_component_key:
                continue
            component_key_override = existing_component_key
            reuses_existing_component_map = True
            print(
                "[INFO] Reusing existing component key "
                f"{existing_component_key} for batch_number '{target_batch_number}'"
            )
            break
    is_linked_full_lifecycle_continuation_run = bool(
        args.full_lifecycle and args.include_fw_batch and args.batch_number
    )
    if is_linked_full_lifecycle_continuation_run and not args.no_continuation_batch_name_concat:
        target_batch_number = compose_continuation_batch_name(
            args.batch_number,
            batch_info.input_name,
        )
        if target_batch_number != batch_number_override:
            print(
                "[INFO] Continuation naming: "
                f"'{batch_number_override}' -> '{target_batch_number}'"
            )
        batch_number_override = target_batch_number
    csv_path = generate_component_csv(
        batch_key,
        members,
        output_dir,
        component_key_override=component_key_override,
    )

    # Determine the component_key (first population ID unless overridden)
    component_key = component_key_override or members[0].population_id

    print(f"\nComponent key for migration: {component_key}")
    is_linked_full_lifecycle_run = bool(args.full_lifecycle and args.include_fw_batch)
    merge_existing_component_map = bool(
        is_linked_full_lifecycle_run and reuses_existing_component_map
    )
    if is_linked_full_lifecycle_run and not merge_existing_component_map:
        print(
            "[INFO] Linked full-lifecycle run has no existing component map; "
            "merge-existing-component-map is disabled for initial materialization."
        )
    transfer_include_synthetic_stage_transitions = bool(args.include_synthetic_stage_transitions)
    if transfer_include_synthetic_stage_transitions:
        print("Transfer migration synthetic stage transitions: ENABLED (CLI override).")
    else:
        if is_linked_full_lifecycle_run:
            print(
                "Transfer migration will skip synthetic stage-transition workflows/actions "
                "(edge-backed only; linked full-lifecycle default guardrail)."
            )
        else:
            print("Transfer migration will skip synthetic stage-transition workflows/actions (edge-backed only).")

    if args.dry_run:
        print("\n[DRY RUN] Would run the following scripts:")
        planned_scripts = []
        for script in PIPELINE_CORE_SCRIPT_ORDER + PIPELINE_PARALLEL_SCRIPT_ORDER + PIPELINE_TAIL_SCRIPT_ORDER:
            if not is_script_enabled(script, args):
                continue
            planned_scripts.append(script)
        for script in planned_scripts:
            print(f"  - {script}")
        if args.parallel_workers > 1:
            parallel_count = sum(1 for script in PIPELINE_PARALLEL_SCRIPT_ORDER if script in planned_scripts)
            print(
                "\nExecution plan: core scripts sequential, "
                f"{parallel_count} post-transfer scripts parallelized with {args.parallel_workers} workers, "
                "feed inventory serial tail."
            )
            print(
                f"Parallel BLAS/vecLib thread cap per subprocess: {args.parallel_blas_threads}"
            )
        return 0

    # Build enabled script list in deterministic order.
    enabled_scripts = []
    for script in PIPELINE_CORE_SCRIPT_ORDER + PIPELINE_PARALLEL_SCRIPT_ORDER + PIPELINE_TAIL_SCRIPT_ORDER:
        if not is_script_enabled(script, args):
            continue
        enabled_scripts.append(script)

    total_scripts = len(enabled_scripts)
    parallel_env = build_parallel_env(args.parallel_workers, args.parallel_blas_threads)

    # Run migration scripts in pipeline order (optional parallel post-transfer phase).
    print("\n" + "-" * 70)
    print("RUNNING MIGRATION PIPELINE")
    print("-" * 70)

    success_count = 0
    failed_scripts = []
    script_durations: dict[str, float] = {}
    sequence_index: dict[str, int] = {name: idx + 1 for idx, name in enumerate(enabled_scripts)}

    def run_serial(script_name: str) -> None:
        nonlocal success_count
        label = PIPELINE_SCRIPT_LABELS.get(script_name, script_name)
        idx = sequence_index[script_name]
        print(f"\n[{idx}/{total_scripts}] {label}")
        result = run_migration_script(
            script_name,
            component_key,
            output_dir,
            use_csv=args.use_csv,
            use_sqlite=args.use_sqlite,
            dry_run=args.dry_run,
            batch_number=batch_number_override,
            migration_profile=args.migration_profile,
            merge_existing_component_map=merge_existing_component_map,
            external_mixing_status_multiplier=args.external_mixing_status_multiplier,
            lifecycle_frontier_window_hours=args.lifecycle_frontier_window_hours,
            skip_synthetic_stage_transitions=not transfer_include_synthetic_stage_transitions,
            transfer_edge_scope=args.transfer_edge_scope,
            timeout_seconds=args.script_timeout_seconds,
            extra_env=parallel_env,
            announce=True,
        )
        script_durations[script_name] = result.duration_seconds
        print(f"    Duration: {result.duration_seconds:.1f}s")
        if result.success:
            success_count += 1
        else:
            failed_scripts.append(script_name)
            # Continue with remaining scripts even if one fails.

    core_scripts = [name for name in PIPELINE_CORE_SCRIPT_ORDER if name in sequence_index]
    parallel_scripts = [name for name in PIPELINE_PARALLEL_SCRIPT_ORDER if name in sequence_index]
    tail_scripts = [name for name in PIPELINE_TAIL_SCRIPT_ORDER if name in sequence_index]

    for script_name in core_scripts:
        run_serial(script_name)

    if parallel_scripts and args.parallel_workers > 1:
        workers = min(args.parallel_workers, len(parallel_scripts))
        print(
            "\n[Parallel phase] "
            f"{len(parallel_scripts)} scripts with {workers} workers "
            f"(BLAS threads/subprocess={args.parallel_blas_threads})"
        )
        futures: dict[Any, str] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for script_name in parallel_scripts:
                idx = sequence_index[script_name]
                label = PIPELINE_SCRIPT_LABELS.get(script_name, script_name)
                print(f"  - queued [{idx}/{total_scripts}] {label}")
                futures[
                    executor.submit(
                        run_migration_script,
                        script_name,
                        component_key,
                        output_dir,
                        use_csv=args.use_csv,
                        use_sqlite=args.use_sqlite,
                        dry_run=args.dry_run,
                        batch_number=batch_number_override,
                        migration_profile=args.migration_profile,
                        merge_existing_component_map=merge_existing_component_map,
                        external_mixing_status_multiplier=args.external_mixing_status_multiplier,
                        lifecycle_frontier_window_hours=args.lifecycle_frontier_window_hours,
                        skip_synthetic_stage_transitions=not transfer_include_synthetic_stage_transitions,
                        transfer_edge_scope=args.transfer_edge_scope,
                        timeout_seconds=args.script_timeout_seconds,
                        extra_env=parallel_env,
                        announce=False,
                    )
                ] = script_name

            for future in as_completed(futures):
                script_name = futures[future]
                idx = sequence_index[script_name]
                label = PIPELINE_SCRIPT_LABELS.get(script_name, script_name)
                try:
                    result = future.result()
                except Exception as exc:
                    result = ScriptRunResult(script_name=script_name, success=False, duration_seconds=0.0)
                    print(f"  [ERROR] [{idx}/{total_scripts}] {label} crashed: {exc}")
                script_durations[script_name] = result.duration_seconds
                if result.success:
                    success_count += 1
                    print(f"  [OK] [{idx}/{total_scripts}] {label} ({result.duration_seconds:.1f}s)")
                else:
                    failed_scripts.append(script_name)
                    print(f"  [ERROR] [{idx}/{total_scripts}] {label} ({result.duration_seconds:.1f}s)")
    else:
        for script_name in parallel_scripts:
            run_serial(script_name)

    for script_name in tail_scripts:
        run_serial(script_name)

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Batch Key: {batch_key}")
    print(f"Input Name: {batch_info.input_name}")
    print(f"Year Class: {batch_info.year_class}")
    print(f"Populations: {len(members)}")
    print(f"Total Fish: {batch_info.total_fish:,.0f}")
    print(f"Scripts completed: {success_count}/{total_scripts}")
    if args.parallel_workers > 1:
        print(f"Parallel workers: {args.parallel_workers}")
        print(f"BLAS thread cap: {args.parallel_blas_threads}")

    if script_durations:
        print("\nScript durations (seconds):")
        for script_name, duration in sorted(script_durations.items(), key=lambda item: item[1], reverse=True):
            label = PIPELINE_SCRIPT_LABELS.get(script_name, script_name)
            print(f"  - {label}: {duration:.1f}")

    if failed_scripts:
        print(f"\nFailed scripts:")
        for script in sorted(set(failed_scripts)):
            print(f"  - {script}")
        return 1

    print("\n[SUCCESS] Migration completed!")
    print(f"\nNext steps:")
    print(f"  1. Verify in GUI: http://localhost:8001/admin/batch/batch/")
    print(f"  2. Run counts report: python scripts/migration/tools/migration_counts_report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
