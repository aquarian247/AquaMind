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
from collections import Counter
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

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()


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


def load_input_batch_info(batch_key: str) -> InputBatchInfo | None:
    """Load batch summary info for a given input batch key."""
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


def load_input_populations(batch_key: str) -> list[PopulationMember]:
    """Load population members for a given input batch key."""
    members_file = INPUT_STITCHING_DIR / "input_population_members.csv"
    if not members_file.exists():
        raise FileNotFoundError(
            f"Input population members file not found: {members_file}\n"
            "Run input_based_stitching_report.py first."
        )

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


def parse_batch_key(batch_key: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in batch_key.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Invalid batch_key format: {batch_key}")
    return parts[0], parts[1], parts[2]


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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
        return [pid for pid in population_ids if pid]

    # SQL fallback
    from scripts.migration.extractors.base import BaseExtractor, ExtractionContext

    extractor = BaseExtractor(ExtractionContext(profile="fishtalk_readonly"))
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), PopulationID) AS PopulationID "
            "FROM dbo.Ext_Inputs_v2 "
            f"WHERE InputName = '{input_name}' AND InputNumber = {input_number} AND YearClass = '{year_class}'"
        ),
        headers=["PopulationID"],
    )
    return [row.get("PopulationID", "") for row in rows if row.get("PopulationID")]


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
    dry_run: bool = False,
    batch_number: str | None = None,
    external_mixing_status_multiplier: float | None = None,
    skip_synthetic_stage_transitions: bool = False,
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
    if script_name == "pilot_migrate_component.py" and external_mixing_status_multiplier is not None:
        cmd.extend(
            [
                "--external-mixing-status-multiplier",
                str(external_mixing_status_multiplier),
            ]
        )

    if script_name == "pilot_migrate_component_transfers.py":
        cmd.append("--use-subtransfers")
        if skip_synthetic_stage_transitions:
            cmd.append("--skip-synthetic-stage-transitions")

    if use_csv and script_name in CSV_SUPPORTED_SCRIPTS:
        cmd.extend(["--use-csv", use_csv])
    elif use_csv:
        print(f"  [INFO] {script_name} does not support --use-csv; using SQL")

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate an input-based batch (Ext_Inputs_v2) from FishTalk to AquaMind"
    )
    parser.add_argument(
        "--batch-key",
        help="Input batch key in format 'InputName|InputNumber|YearClass' (e.g., 'Heyst 2018|1|2018')",
    )
    parser.add_argument(
        "--batch-number",
        help="Override the generated batch number",
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
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
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
            "Legacy behavior: synthesize assignment-derived stage transition workflows/actions "
            "during transfer migration."
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

    if not args.batch_key:
        print("Error: --batch-key is required")
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

    batch_key = args.batch_key

    print(f"\n{'='*70}")
    print(f"INPUT-BASED BATCH MIGRATION")
    print("=" * 70)
    print(f"Batch Key: {batch_key}")
    print()

    # Load batch info
    batch_info = load_input_batch_info(batch_key)
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
        members = load_input_populations(batch_key)

    if not members:
        print(f"[ERROR] No populations found for batch key: {batch_key}")
        return 1

    print(f"  Found {len(members)} populations")

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
    members = sorted(members, key=lambda m: m.start_time or datetime.min)
    component_key_override = None
    if args.full_lifecycle:
        sea_population_ids = load_sea_population_ids(batch_key, use_csv=args.use_csv)
        if sea_population_ids:
            component_key_override = sea_population_ids[0]
    csv_path = generate_component_csv(
        batch_key,
        members,
        output_dir,
        component_key_override=component_key_override,
    )

    # Determine the component_key (first population ID unless overridden)
    component_key = component_key_override or members[0].population_id

    print(f"\nComponent key for migration: {component_key}")
    batch_number_override = args.batch_number or batch_info.input_name
    if not args.include_synthetic_stage_transitions:
        print("Transfer migration will skip synthetic stage-transition workflows/actions (edge-backed only).")

    if args.dry_run:
        print("\n[DRY RUN] Would run the following scripts:")
        planned_scripts = []
        for script in PIPELINE_CORE_SCRIPT_ORDER + PIPELINE_PARALLEL_SCRIPT_ORDER + PIPELINE_TAIL_SCRIPT_ORDER:
            if script == "pilot_migrate_component_environmental.py" and args.skip_environmental:
                continue
            if script == "pilot_migrate_component_feed_inventory.py" and args.skip_feed_inventory:
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
        if script == "pilot_migrate_component_environmental.py" and args.skip_environmental:
            continue
        if script == "pilot_migrate_component_feed_inventory.py" and args.skip_feed_inventory:
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
            dry_run=args.dry_run,
            batch_number=batch_number_override,
            external_mixing_status_multiplier=args.external_mixing_status_multiplier,
            skip_synthetic_stage_transitions=not args.include_synthetic_stage_transitions,
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
                        dry_run=args.dry_run,
                        batch_number=batch_number_override,
                        external_mixing_status_multiplier=args.external_mixing_status_multiplier,
                        skip_synthetic_stage_transitions=not args.include_synthetic_stage_transitions,
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
