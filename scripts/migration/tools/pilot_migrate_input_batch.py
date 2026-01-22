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
3. Runs all migration scripts in sequence
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
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


INPUT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching"
BATCH_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
CSV_SUPPORTED_SCRIPTS = {
    "pilot_migrate_component.py",
    "pilot_migrate_component_transfers.py",
    "pilot_migrate_component_feeding.py",
    "pilot_migrate_component_mortality.py",
    "pilot_migrate_component_environmental.py",
}


DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


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


def generate_component_csv(batch_key: str, members: list[PopulationMember], output_dir: Path) -> Path:
    """Generate a component-style population_members.csv for the existing migration scripts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use a sanitized batch key as component_id
    component_id = batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")
    component_key = members[0].population_id if members else batch_key

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


def run_migration_script(script_name: str, component_key: str, report_dir: Path, 
                         use_csv: str | None = None, dry_run: bool = False) -> bool:
    """Run a migration script with the given component key."""
    script_path = PROJECT_ROOT / "scripts" / "migration" / "tools" / script_name

    if not script_path.exists():
        print(f"  [SKIP] Script not found: {script_path}")
        return True

    cmd = [
        sys.executable,
        str(script_path),
        "--component-key",
        component_key,
        "--report-dir",
        str(report_dir),
    ]

    if script_name == "pilot_migrate_component_transfers.py":
        cmd.append("--use-subtransfers")

    if use_csv and script_name in CSV_SUPPORTED_SCRIPTS:
        cmd.extend(["--use-csv", use_csv])
    elif use_csv:
        print(f"  [INFO] {script_name} does not support --use-csv; using SQL")

    if dry_run:
        cmd.append("--dry-run")

    print(f"  Running: {script_name}...")
    env = os.environ.copy()
    env["SKIP_CELERY_SIGNALS"] = "1"
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode != 0:
            print(f"  [ERROR] {script_name} failed with code {result.returncode}")
            print(f"  STDOUT: {result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout}")
            print(f"  STDERR: {result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr}")
            return False

        # Print last few lines of output
        lines = result.stdout.strip().split("\n")
        for line in lines[-5:]:
            print(f"    {line}")

        return True

    except subprocess.TimeoutExpired:
        print(f"  [ERROR] {script_name} timed out after 600 seconds")
        return False
    except Exception as e:
        print(f"  [ERROR] {script_name} failed: {e}")
        return False


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

    # Generate component-style CSV
    # Use sanitized batch key for directory name
    dir_name = batch_key.replace("|", "_").replace(" ", "_").replace("/", "_")
    output_dir = BATCH_OUTPUT_DIR / dir_name
    print(f"\nGenerating component CSV in: {output_dir}")
    csv_path = generate_component_csv(batch_key, members, output_dir)

    # Determine the component_key (first population ID)
    component_key = members[0].population_id

    print(f"\nComponent key for migration: {component_key}")

    if args.dry_run:
        print("\n[DRY RUN] Would run the following scripts:")
        scripts = [
            "pilot_migrate_component.py",
            "pilot_migrate_component_transfers.py",
            "pilot_migrate_component_feeding.py",
            "pilot_migrate_component_mortality.py",
            "pilot_migrate_component_treatments.py",
            "pilot_migrate_component_lice.py",
            "pilot_migrate_component_health_journal.py",
        ]
        if not args.skip_environmental:
            scripts.append("pilot_migrate_component_environmental.py")
        if not args.skip_feed_inventory:
            scripts.append("pilot_migrate_component_feed_inventory.py")
        for script in scripts:
            print(f"  - {script}")
        return 0

    # Run migration scripts in sequence
    print("\n" + "-" * 70)
    print("RUNNING MIGRATION PIPELINE")
    print("-" * 70)

    scripts = [
        ("pilot_migrate_component.py", "Infrastructure + Batch + Assignments"),
        ("pilot_migrate_component_transfers.py", "Transfer Workflows"),
        ("pilot_migrate_component_feeding.py", "Feeding Events"),
        ("pilot_migrate_component_mortality.py", "Mortality Events"),
        ("pilot_migrate_component_treatments.py", "Treatments"),
        ("pilot_migrate_component_lice.py", "Lice Counts"),
        ("pilot_migrate_component_health_journal.py", "Health Journal"),
    ]

    if not args.skip_environmental:
        scripts.append(("pilot_migrate_component_environmental.py", "Environmental Readings"))

    if not args.skip_feed_inventory:
        scripts.append(("pilot_migrate_component_feed_inventory.py", "Feed Inventory"))

    success_count = 0
    failed_scripts = []

    for script_name, description in scripts:
        print(f"\n[{success_count + 1}/{len(scripts)}] {description}")
        if run_migration_script(script_name, component_key, output_dir, 
                               use_csv=args.use_csv, dry_run=args.dry_run):
            success_count += 1
        else:
            failed_scripts.append(script_name)
            # Continue with remaining scripts even if one fails

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Batch Key: {batch_key}")
    print(f"Input Name: {batch_info.input_name}")
    print(f"Year Class: {batch_info.year_class}")
    print(f"Populations: {len(members)}")
    print(f"Total Fish: {batch_info.total_fish:,.0f}")
    print(f"Scripts completed: {success_count}/{len(scripts)}")

    if failed_scripts:
        print(f"\nFailed scripts:")
        for script in failed_scripts:
            print(f"  - {script}")
        return 1

    print("\n[SUCCESS] Migration completed!")
    print(f"\nNext steps:")
    print(f"  1. Verify in GUI: http://localhost:8001/admin/batch/batch/")
    print(f"  2. Run counts report: python scripts/migration/tools/migration_counts_report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
