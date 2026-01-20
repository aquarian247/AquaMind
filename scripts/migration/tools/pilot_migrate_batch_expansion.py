#!/usr/bin/env python3
# flake8: noqa
"""Expand batch migration to process multiple project batches from recommended_batches.csv.

This script orchestrates migration of multiple batches by:
1. Reading project batches from project_batches.csv (with --min-stages filter)
2. Filtering out already-migrated batches (via ExternalIdMap)
3. Running migration pipeline for each batch sequentially or in parallel

Usage:
    # Dry run - see what would be migrated
    python pilot_migrate_batch_expansion.py --min-stages 5 --limit 10 --dry-run

    # Migrate next 50 batches with 5+ stages
    python pilot_migrate_batch_expansion.py --min-stages 5 --limit 50

    # Migrate all batches with 5+ stages (527 total)
    python pilot_migrate_batch_expansion.py --min-stages 5

    # Filter by active status only
    python pilot_migrate_batch_expansion.py --min-stages 5 --active-only
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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

from apps.migration_support.models import ExternalIdMap


PROJECT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching"
LOG_DIR = PROJECT_ROOT / "scripts" / "migration" / "logs" / "batch_expansion"


@dataclass
class ProjectBatch:
    """Project batch from CSV."""
    project_key: str
    project_number: str
    input_year: str
    running_number: str
    population_count: int
    stages: str
    stage_count: int
    is_active: bool
    earliest_start: str
    latest_activity: str
    representative_name: str


def load_project_batches(min_stages: int = 5, active_only: bool = False) -> List[ProjectBatch]:
    """Load project batches from CSV with filters."""
    csv_path = PROJECT_STITCHING_DIR / "project_batches.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Project batches file not found: {csv_path}\n"
            "Run project_based_stitching_report.py first."
        )

    batches = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_count = int(row.get("stage_count", 0))
            is_active = row.get("is_active", "").lower() == "true"

            # Apply filters
            if stage_count < min_stages:
                continue
            if active_only and not is_active:
                continue

            batches.append(ProjectBatch(
                project_key=row.get("project_key", ""),
                project_number=row.get("project_number", ""),
                input_year=row.get("input_year", ""),
                running_number=row.get("running_number", ""),
                population_count=int(row.get("population_count", 0)),
                stages=row.get("aquamind_stages", ""),
                stage_count=stage_count,
                is_active=is_active,
                earliest_start=row.get("earliest_start", ""),
                latest_activity=row.get("latest_activity", ""),
                representative_name=row.get("representative_name", ""),
            ))

    # Sort by latest_activity (most recent first for active batches)
    batches.sort(key=lambda b: b.latest_activity, reverse=True)
    return batches


def get_migrated_project_keys() -> set:
    """Get project keys that have already been migrated.
    
    The migration uses PopulationComponent with the first population_id as source_identifier.
    We need to map project_keys to their first population_id and check ExternalIdMap.
    """
    migrated = set()
    
    # Load project_population_members.csv to get first population_id per project
    members_path = PROJECT_STITCHING_DIR / "project_population_members.csv"
    if not members_path.exists():
        return migrated
    
    # Build mapping: project_key -> first population_id
    project_first_pop = {}
    with members_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_key = row.get("project_key", "")
            pop_id = row.get("population_id", "")
            if project_key and pop_id and project_key not in project_first_pop:
                project_first_pop[project_key] = pop_id
    
    # Get all migrated population component IDs
    migrated_pop_ids = set(
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="PopulationComponent",
        ).values_list("source_identifier", flat=True)
    )
    
    # Find project_keys whose first population has been migrated
    for project_key, first_pop_id in project_first_pop.items():
        if first_pop_id in migrated_pop_ids:
            migrated.add(project_key)
    
    return migrated


def run_batch_migration(
    project_key: str,
    skip_environmental: bool = True,
    skip_feed_inventory: bool = True,
    timeout: int = 600,
) -> dict:
    """Run migration pipeline for a single project batch."""
    script_path = PROJECT_ROOT / "scripts" / "migration" / "tools" / "pilot_migrate_project_batch.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--project-key", project_key,
    ]
    
    if skip_environmental:
        cmd.append("--skip-environmental")
    if skip_feed_inventory:
        cmd.append("--skip-feed-inventory")
    
    env = os.environ.copy()
    env["SKIP_CELERY_SIGNALS"] = "1"
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        elapsed = time.time() - start_time
        
        return {
            "project_key": project_key,
            "success": result.returncode == 0,
            "elapsed_seconds": round(elapsed, 1),
            "stdout": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
            "stderr": result.stderr[-500:] if len(result.stderr) > 500 else result.stderr,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "project_key": project_key,
            "success": False,
            "elapsed_seconds": timeout,
            "error": f"Timeout after {timeout}s",
        }
    except Exception as e:
        return {
            "project_key": project_key,
            "success": False,
            "elapsed_seconds": time.time() - start_time,
            "error": str(e),
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expand batch migration to process multiple project batches"
    )
    parser.add_argument(
        "--min-stages",
        type=int,
        default=5,
        help="Minimum number of lifecycle stages (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of batches to migrate (default: all)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only migrate active batches",
    )
    parser.add_argument(
        "--include-environmental",
        action="store_true",
        help="Include environmental data migration (slow)",
    )
    parser.add_argument(
        "--include-feed-inventory",
        action="store_true",
        help="Include feed inventory migration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without running",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout per batch in seconds (default: 600)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 70)
    print("BATCH MIGRATION EXPANSION")
    print("=" * 70)
    
    # Load project batches
    print(f"\nLoading project batches (min {args.min_stages} stages)...")
    all_batches = load_project_batches(
        min_stages=args.min_stages,
        active_only=args.active_only,
    )
    print(f"  Found {len(all_batches)} batches matching criteria")
    
    # Filter out already migrated
    print("\nChecking for already-migrated batches...")
    migrated_keys = get_migrated_project_keys()
    print(f"  Already migrated: {len(migrated_keys)} batches")
    
    batches_to_migrate = [b for b in all_batches if b.project_key not in migrated_keys]
    print(f"  Remaining to migrate: {len(batches_to_migrate)} batches")
    
    # Apply limit
    if args.limit and len(batches_to_migrate) > args.limit:
        batches_to_migrate = batches_to_migrate[:args.limit]
        print(f"  Limited to: {args.limit} batches")
    
    if not batches_to_migrate:
        print("\n[INFO] No batches to migrate")
        return 0
    
    # Show summary
    active_count = sum(1 for b in batches_to_migrate if b.is_active)
    completed_count = len(batches_to_migrate) - active_count
    
    print(f"\n" + "-" * 70)
    print("MIGRATION PLAN")
    print("-" * 70)
    print(f"  Batches to migrate: {len(batches_to_migrate)}")
    print(f"    Active: {active_count}")
    print(f"    Completed: {completed_count}")
    print(f"  Skip environmental: {not args.include_environmental}")
    print(f"  Skip feed inventory: {not args.include_feed_inventory}")
    
    if args.dry_run:
        print("\n[DRY RUN] Batches that would be migrated:")
        for i, batch in enumerate(batches_to_migrate[:20], 1):
            status = "ACTIVE" if batch.is_active else "COMPLETED"
            print(f"  {i:3}. {batch.project_key:<12} | {status:<10} | {batch.stage_count} stages | {batch.population_count:3} pops | {batch.representative_name[:40]}")
        if len(batches_to_migrate) > 20:
            print(f"  ... and {len(batches_to_migrate) - 20} more")
        return 0
    
    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"expansion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Run migrations
    print(f"\n" + "-" * 70)
    print("RUNNING MIGRATIONS")
    print("-" * 70)
    
    success_count = 0
    error_count = 0
    total_time = 0
    errors = []
    
    for i, batch in enumerate(batches_to_migrate, 1):
        print(f"\n[{i}/{len(batches_to_migrate)}] Migrating {batch.project_key}...")
        
        result = run_batch_migration(
            batch.project_key,
            skip_environmental=not args.include_environmental,
            skip_feed_inventory=not args.include_feed_inventory,
            timeout=args.timeout,
        )
        
        total_time += result.get("elapsed_seconds", 0)
        
        if result["success"]:
            success_count += 1
            print(f"  [OK] Completed in {result['elapsed_seconds']:.1f}s")
        else:
            error_count += 1
            error_msg = result.get("error", result.get("stderr", "Unknown error"))
            errors.append({"project_key": batch.project_key, "error": error_msg[:200]})
            print(f"  [ERROR] {error_msg[:100]}")
        
        # Log to file
        with log_file.open("a") as f:
            f.write(f"{datetime.now().isoformat()} | {batch.project_key} | ")
            f.write(f"{'OK' if result['success'] else 'ERROR'} | {result.get('elapsed_seconds', 0):.1f}s\n")
    
    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  Total batches: {len(batches_to_migrate)}")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"  Average per batch: {total_time/len(batches_to_migrate):.1f}s")
    print(f"  Log file: {log_file}")
    
    if errors:
        print(f"\nErrors:")
        for e in errors[:5]:
            print(f"  {e['project_key']}: {e['error'][:100]}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    if error_count == 0:
        print("\n[SUCCESS] All batches migrated successfully!")
        return 0
    else:
        print(f"\n[WARNING] {error_count} batches had errors")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
