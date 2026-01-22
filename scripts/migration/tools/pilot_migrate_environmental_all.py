#!/usr/bin/env python3
# flake8: noqa
"""Run environmental migration for all project-based batches.

This script iterates over the project batch migration output folders and
executes environmental migration using a shared ETLDataLoader when CSV mode
is enabled.

Usage:
    # Dry run for all batches (CSV mode)
    python pilot_migrate_environmental_all.py --use-csv scripts/migration/data/extract/ --dry-run

    # Full run for all batches (CSV mode)
    python pilot_migrate_environmental_all.py --use-csv scripts/migration/data/extract/

    # Limit to first 10 batches, daily-only
    python pilot_migrate_environmental_all.py --use-csv scripts/migration/data/extract/ --limit 10 --daily-only
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import multiprocessing as mp
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

from scripts.migration.tools.etl_loader import ETLDataLoader
from scripts.migration.tools.pilot_migrate_component_environmental import migrate_component_environmental


DEFAULT_REPORT_ROOT = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_batch_migration"


def find_report_dirs(report_root: Path) -> list[Path]:
    if not report_root.exists():
        return []
    return sorted(
        path for path in report_root.iterdir()
        if path.is_dir() and (path / "population_members.csv").exists()
    )


def read_component_key(members_path: Path) -> str:
    with members_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            component_key = (row.get("component_key") or "").strip()
            if component_key:
                return component_key
    return ""


def process_report_dir(args: tuple) -> dict:
    report_dir, component_key, options = args
    try:
        result = migrate_component_environmental(
            report_dir=Path(report_dir),
            component_key=component_key,
            daily_only=options["daily_only"],
            limit=options["row_limit"],
            dry_run=options["dry_run"],
            use_csv_dir=options["use_csv"],
            use_sqlite_path=options["use_sqlite"],
            loader=None,
        )
        return {
            "dir": report_dir,
            "component_key": component_key,
            "success": result == 0,
            "error": None if result == 0 else f"Non-zero return: {result}",
        }
    except Exception as exc:
        return {"dir": report_dir, "component_key": component_key, "success": False, "error": str(exc)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run environmental migration for all project batches")
    parser.add_argument(
        "--report-root",
        default=str(DEFAULT_REPORT_ROOT),
        help="Root directory containing project batch migration folders",
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
        help="Use SQLite index for environmental readings (recommended for parallel runs)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of batches to process (0 = no limit)",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=0,
        help="Limit readings per table for each batch (0 = no limit)",
    )
    parser.add_argument(
        "--daily-only",
        action="store_true",
        help="Use Ext_DailySensorReadings_v2 only (skip time-series)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_root = Path(args.report_root)
    report_dirs = find_report_dirs(report_root)
    if not report_dirs:
        print(f"No batch report directories found in {report_root}")
        return 1

    if args.limit and args.limit > 0:
        report_dirs = report_dirs[:args.limit]

    if args.workers > 1 and args.use_csv and not args.use_sqlite:
        print("For --workers > 1, use --use-sqlite to avoid loading full CSV per worker.")
        return 1

    loader = None
    if args.workers == 1 and (args.use_csv or args.use_sqlite):
        loader = ETLDataLoader(args.use_csv, sqlite_path=args.use_sqlite)

    print("\n" + "=" * 70)
    print("ENVIRONMENTAL MIGRATION (ALL PROJECT BATCHES)")
    print("=" * 70)
    print(f"Batches found: {len(report_dirs)}")
    print(f"CSV mode: {'ON' if args.use_csv else 'OFF'}")
    print(f"SQLite mode: {'ON' if args.use_sqlite else 'OFF'}")
    print(f"Daily-only: {args.daily_only}")
    print(f"Dry run: {args.dry_run}")
    print(f"Workers: {args.workers}")
    print()

    start_time = time.time()
    errors = []

    if args.workers > 1:
        tasks = []
        for report_dir in report_dirs:
            members_path = report_dir / "population_members.csv"
            component_key = read_component_key(members_path)
            if not component_key:
                errors.append({"dir": str(report_dir), "error": "Missing component_key in population_members.csv"})
                continue
            tasks.append(
                (
                    str(report_dir),
                    component_key,
                    {
                        "daily_only": args.daily_only,
                        "row_limit": args.row_limit,
                        "dry_run": args.dry_run,
                        "use_csv": args.use_csv,
                        "use_sqlite": args.use_sqlite,
                    },
                )
            )

        with mp.Pool(processes=min(args.workers, len(tasks))) as pool:
            for idx, result in enumerate(pool.imap_unordered(process_report_dir, tasks), 1):
                status = "OK" if result["success"] else "ERROR"
                print(f"[{idx}/{len(tasks)}] {status} {result['component_key']}")
                if not result["success"]:
                    errors.append({"dir": result["dir"], "error": result["error"]})
    else:
        for idx, report_dir in enumerate(report_dirs, 1):
            members_path = report_dir / "population_members.csv"
            component_key = read_component_key(members_path)
            if not component_key:
                errors.append({"dir": str(report_dir), "error": "Missing component_key in population_members.csv"})
                print(f"[{idx}/{len(report_dirs)}] ERROR: Missing component_key in {members_path}")
                continue

            print(f"[{idx}/{len(report_dirs)}] Processing {component_key} ({report_dir.name})")
            try:
                result = migrate_component_environmental(
                    report_dir=report_dir,
                    component_key=component_key,
                    daily_only=args.daily_only,
                    limit=args.row_limit,
                    dry_run=args.dry_run,
                    use_csv_dir=args.use_csv,
                    use_sqlite_path=args.use_sqlite,
                    loader=loader,
                )
                if result != 0:
                    errors.append({"dir": str(report_dir), "error": f"Non-zero return: {result}"})
            except Exception as exc:
                errors.append({"dir": str(report_dir), "error": str(exc)})
                print(f"  ERROR: {exc}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Batches processed: {len(report_dirs)}")
    print(f"Elapsed: {elapsed/60:.1f} minutes")
    print(f"Errors: {len(errors)}")
    if errors[:5]:
        print("\nSample errors:")
        for error in errors[:5]:
            print(f"  {error['dir']}: {error['error']}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
