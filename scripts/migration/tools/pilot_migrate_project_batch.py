#!/usr/bin/env python3
# flake8: noqa
"""Migrate a project-based batch from FishTalk to AquaMind.

This script reads from the project-based stitching output and runs the full
migration pipeline for a single project batch identified by its project_key
(ProjectNumber/InputYear/RunningNumber).

It generates compatible CSV files and then runs all the existing migration
scripts in sequence.
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

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


PROJECT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching"
COMPONENT_OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_batch_migration"


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
    population_name: str
    container_id: str
    start_time: datetime | None
    end_time: datetime | None
    fishtalk_stages: str
    aquamind_stages: str


def load_project_populations(project_key: str) -> list[PopulationMember]:
    """Load population members for a given project key."""
    members_file = PROJECT_STITCHING_DIR / "project_population_members.csv"
    if not members_file.exists():
        raise FileNotFoundError(
            f"Project population members file not found: {members_file}\n"
            "Run project_based_stitching_report.py first."
        )

    members = []
    with members_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("project_key") != project_key:
                continue
            members.append(
                PopulationMember(
                    population_id=row.get("population_id", ""),
                    population_name=row.get("population_name", ""),
                    container_id=row.get("container_id", ""),
                    start_time=parse_dt(row.get("start_time", "")),
                    end_time=parse_dt(row.get("end_time", "")),
                    fishtalk_stages=row.get("fishtalk_stages", ""),
                    aquamind_stages=row.get("aquamind_stages", ""),
                )
            )

    return members


def generate_component_csv(project_key: str, members: list[PopulationMember], output_dir: Path) -> Path:
    """Generate a component-style population_members.csv for the existing migration scripts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use the first part of the project key as a pseudo component_id
    component_id = project_key.replace("/", "_")
    component_key = members[0].population_id if members else project_key

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
                    "population_name": member.population_name,
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
                "representative_name": members[0].population_name if members else "",
                "contains_freshwater_stages": has_fw,
                "contains_sea_stages": has_sea,
                "transportpop_population_count": 0,
            }
        )

    return csv_path


def run_migration_script(script_name: str, component_key: str, report_dir: Path, dry_run: bool = False) -> bool:
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

    if dry_run:
        cmd.append("--dry-run")

    print(f"  Running: {script_name}...")
    env = os.environ.copy()
    env["SKIP_CELERY_SIGNALS"] = "1"

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate a project-based batch from FishTalk to AquaMind"
    )
    parser.add_argument(
        "--project-key",
        required=True,
        help="Project key in format 'ProjectNumber/InputYear/RunningNumber' (e.g., '1/24/27')",
    )
    parser.add_argument(
        "--batch-number",
        help="Override the generated batch number",
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_key = args.project_key

    print(f"\n{'='*60}")
    print(f"PROJECT BATCH MIGRATION: {project_key}")
    print("=" * 60)

    # Load population members for this project
    print(f"\nLoading populations for project {project_key}...")
    members = load_project_populations(project_key)

    if not members:
        print(f"[ERROR] No populations found for project key: {project_key}")
        print("Available project keys can be found in:")
        print(f"  {PROJECT_STITCHING_DIR / 'recommended_batches.csv'}")
        return 1

    print(f"  Found {len(members)} populations")

    # Show stage coverage
    stages = set()
    for m in members:
        stages.update(s.strip() for s in m.aquamind_stages.split(",") if s.strip())
    print(f"  AquaMind stages: {', '.join(sorted(stages))}")

    # Generate component-style CSV
    output_dir = COMPONENT_OUTPUT_DIR / project_key.replace("/", "_")
    print(f"\nGenerating component CSV in: {output_dir}")
    csv_path = generate_component_csv(project_key, members, output_dir)

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
    print("\n" + "-" * 60)
    print("RUNNING MIGRATION PIPELINE")
    print("-" * 60)

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
        if run_migration_script(script_name, component_key, output_dir, dry_run=args.dry_run):
            success_count += 1
        else:
            failed_scripts.append(script_name)
            # Continue with remaining scripts even if one fails

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Project: {project_key}")
    print(f"Populations: {len(members)}")
    print(f"Scripts completed: {success_count}/{len(scripts)}")

    if failed_scripts:
        print(f"\nFailed scripts:")
        for script in failed_scripts:
            print(f"  - {script}")
        return 1

    print("\n[SUCCESS] Migration completed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
