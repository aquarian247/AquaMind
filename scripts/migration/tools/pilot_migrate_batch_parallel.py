#!/usr/bin/env python3
# flake8: noqa
"""Parallel batch migration from FishTalk to AquaMind.

Uses multiprocessing.Pool to migrate multiple batches concurrently.
Inherits parallelization pattern from test_data_generation/execute_batch_schedule.py.

Usage:
    # Dry run
    python pilot_migrate_batch_parallel.py --dry-run

    # Migrate with 8 workers
    python pilot_migrate_batch_parallel.py --workers 8 --limit 100

    # Full migration (all remaining batches)
    python pilot_migrate_batch_parallel.py --workers 10
"""

from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import os
import subprocess
import sys
import time
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

from apps.migration_support.models import ExternalIdMap

# Paths
PROJECT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching"
LOG_DIR = PROJECT_ROOT / "scripts" / "migration" / "logs"


def load_project_batches(min_stages: int = 5) -> list:
    """Load project batches from CSV with minimum stage requirement."""
    csv_path = PROJECT_STITCHING_DIR / "project_batches.csv"
    if not csv_path.exists():
        return []
    
    batches = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                stage_count = int(row.get("stage_count", 0))
            except ValueError:
                stage_count = 0
            
            if stage_count >= min_stages:
                batches.append({
                    "project_key": row.get("project_key", ""),
                    "stage_count": stage_count,
                    "population_count": int(row.get("population_count", 0)),
                    "status": row.get("status", ""),
                    "project_name": row.get("project_name", ""),
                })
    
    return batches


def get_migrated_project_keys() -> set:
    """Get project keys that have already been migrated."""
    migrated = set()
    
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


def migrate_single_batch(args):
    """Migrate a single batch via subprocess. Designed for parallel execution."""
    project_key, log_dir = args
    start_time = time.time()
    
    # Set up environment
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    env['DJANGO_SETTINGS_MODULE'] = 'aquamind.settings'
    
    cmd = [
        'python', 
        'scripts/migration/tools/pilot_migrate_project_batch.py',
        '--project-key', project_key,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=600,  # 10 minute timeout per batch
        )
        duration = time.time() - start_time
        
        # Write log
        if log_dir:
            log_path = Path(log_dir) / f"batch_{project_key.replace('/', '_')}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, 'w') as f:
                f.write(f"SUCCESS - Duration: {duration:.1f}s\n")
                f.write(f"{'='*60}\n")
                f.write(result.stdout)
        
        return {
            'success': True,
            'project_key': project_key,
            'duration': duration,
        }
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            'success': False,
            'project_key': project_key,
            'duration': duration,
            'error': 'Timeout (>10 minutes)',
        }
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        
        # Write error log
        if log_dir:
            log_path = Path(log_dir) / f"batch_{project_key.replace('/', '_')}_ERROR.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, 'w') as f:
                f.write(f"FAILED - Duration: {duration:.1f}s\n")
                f.write(f"{'='*60}\n")
                f.write("STDOUT:\n")
                f.write(e.stdout or "(empty)\n")
                f.write("\nSTDERR:\n")
                f.write(e.stderr or "(empty)\n")
        
        return {
            'success': False,
            'project_key': project_key,
            'duration': duration,
            'error': e.stderr[:200] if e.stderr else 'Unknown error',
        }


def partition_batches(batches: list, num_workers: int) -> list:
    """Partition batches across workers for balanced load."""
    # Sort by population count (larger batches take longer)
    sorted_batches = sorted(batches, key=lambda b: b['population_count'], reverse=True)
    
    # Round-robin distribution (ensures large batches spread across workers)
    partitions = [[] for _ in range(num_workers)]
    for i, batch in enumerate(sorted_batches):
        partitions[i % num_workers].append(batch)
    
    return partitions


def execute_partition(args):
    """Execute a partition of batches sequentially within a worker."""
    worker_id, batches, log_dir = args
    results = []
    
    for batch in batches:
        result = migrate_single_batch((batch['project_key'], log_dir))
        result['worker_id'] = worker_id
        results.append(result)
    
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parallel batch migration from FishTalk"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show migration plan without executing",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers (default: 8)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of batches to migrate",
    )
    parser.add_argument(
        "--min-stages",
        type=int,
        default=5,
        help="Minimum lifecycle stages per batch (default: 5)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only migrate ACTIVE batches",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=str(LOG_DIR / "batch_migration"),
        help="Directory for per-batch logs",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 70)
    print("PARALLEL BATCH MIGRATION")
    print("=" * 70)
    
    # Load batches
    print(f"\nLoading project batches (min {args.min_stages} stages)...")
    all_batches = load_project_batches(min_stages=args.min_stages)
    print(f"  Found {len(all_batches)} batches matching criteria")
    
    # Filter by status if requested
    if args.active_only:
        all_batches = [b for b in all_batches if b['status'] == 'ACTIVE']
        print(f"  Filtered to {len(all_batches)} ACTIVE batches")
    
    # Check already migrated
    print("\nChecking for already-migrated batches...")
    migrated_keys = get_migrated_project_keys()
    print(f"  Already migrated: {len(migrated_keys)} batches")
    
    # Filter to remaining
    remaining = [b for b in all_batches if b['project_key'] not in migrated_keys]
    print(f"  Remaining to migrate: {len(remaining)} batches")
    
    # Apply limit
    if args.limit and args.limit < len(remaining):
        remaining = remaining[:args.limit]
        print(f"  Limited to: {args.limit} batches")
    
    if not remaining:
        print("\n[INFO] No batches to migrate")
        return 0
    
    # Stats
    active_count = sum(1 for b in remaining if b['status'] == 'ACTIVE')
    completed_count = len(remaining) - active_count
    total_populations = sum(b['population_count'] for b in remaining)
    
    print(f"\n{'='*70}")
    print("MIGRATION PLAN")
    print(f"{'='*70}")
    print(f"  Batches to migrate: {len(remaining)}")
    print(f"    Active: {active_count}")
    print(f"    Completed: {completed_count}")
    print(f"  Total populations: {total_populations:,}")
    print(f"  Workers: {args.workers}")
    
    # Partition batches
    partitions = partition_batches(remaining, args.workers)
    print(f"\n  Worker distribution:")
    for i, partition in enumerate(partitions):
        pops = sum(b['population_count'] for b in partition)
        print(f"    Worker {i}: {len(partition)} batches, {pops:,} populations")
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would migrate {len(remaining)} batches with {args.workers} workers")
        print("\nSample batches:")
        for b in remaining[:10]:
            print(f"  - {b['project_key']} | {b['status']:9} | {b['population_count']:3} pops | {b['project_name'][:40]}")
        if len(remaining) > 10:
            print(f"  ... and {len(remaining) - 10} more")
        return 0
    
    # Create log directory
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("EXECUTING MIGRATION")
    print(f"{'='*70}")
    print(f"Logs: {args.log_dir}")
    print()
    
    start_time = time.time()
    
    # Prepare worker tasks
    worker_tasks = []
    for i, partition in enumerate(partitions):
        if partition:  # Skip empty partitions
            worker_tasks.append((f"worker_{i}", partition, str(log_dir)))
    
    # Execute with multiprocessing Pool
    results = []
    completed = 0
    
    with mp.Pool(processes=min(args.workers, len(worker_tasks))) as pool:
        for worker_results in pool.imap_unordered(execute_partition, worker_tasks):
            for result in worker_results:
                completed += 1
                status = "✅" if result['success'] else "❌"
                worker = result.get('worker_id', 'unknown')
                duration = result.get('duration', 0)
                print(f"[{completed}/{len(remaining)}] {status} {worker}: {result['project_key']} ({duration:.1f}s)")
                
                if not result['success']:
                    error = result.get('error', 'Unknown')[:80]
                    print(f"    Error: {error}")
                
                results.append(result)
    
    # Summary
    total_duration = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(remaining) - success_count
    
    print(f"\n{'='*70}")
    print("MIGRATION COMPLETE")
    print(f"{'='*70}")
    print(f"Total Time: {total_duration/60:.1f} minutes ({total_duration:.0f} seconds)")
    print(f"Success: {success_count}/{len(remaining)} ({100*success_count/len(remaining):.1f}%)")
    print(f"Failed: {fail_count}")
    print(f"Avg time per batch: {total_duration/len(remaining):.1f}s")
    
    if fail_count > 0:
        print("\nFailed Batches:")
        for r in results:
            if not r['success']:
                print(f"  - {r['project_key']}: {r.get('error', 'Unknown')[:60]}")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
