#!/usr/bin/env python3
"""Backfill deterministic priority-hall stage corrections for mapped batches."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db
from scripts.migration.tools.hall_stage_rules import is_priority_hall_site, stage_from_hall

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.batch.models import Batch
from apps.batch.models.assignment import BatchContainerAssignment
from apps.batch.models.species import LifeCycleStage
from scripts.migration.history import save_with_history
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map


DEFAULT_QUEUE_CSV = PROJECT_ROOT / "scripts" / "migration" / "output" / "priority_hall_stage_backfill_queue_20260325.csv"
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


@dataclass(frozen=True)
class BatchResult:
    report_dir: str
    batch_id: str
    batch_number: str
    component_key: str
    mismatch_count: int
    changed_report_rows: int
    changed_assignments: int
    missing_assignment_maps: int
    batch_stage_before: str
    batch_stage_after: str
    success: bool
    error: str
    duration_sec: float
    log_path: str


def load_grouping(csv_dir: Path) -> dict[str, dict[str, str]]:
    grouping_path = csv_dir / "grouped_organisation.csv"
    if not grouping_path.exists():
        raise FileNotFoundError(f"Missing grouped organisation extract: {grouping_path}")

    grouping: dict[str, dict[str, str]] = {}
    with grouping_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if not container_id:
                continue
            grouping[container_id] = {
                "site": (row.get("Site") or "").strip(),
                "container_group": (row.get("ContainerGroup") or "").strip(),
            }
    return grouping


def relevant_assignment_date(assignment: BatchContainerAssignment) -> date:
    return assignment.departure_date or assignment.assignment_date or date.min


def recompute_batch_stage(batch: Batch) -> LifeCycleStage | None:
    assignments = list(
        BatchContainerAssignment.objects.filter(batch=batch).select_related("lifecycle_stage")
    )
    if not assignments:
        return None

    active = [
        assignment
        for assignment in assignments
        if assignment.is_active and (assignment.population_count or 0) > 0 and assignment.lifecycle_stage
    ]
    candidates = active
    if not candidates:
        latest_date = max(relevant_assignment_date(assignment) for assignment in assignments)
        candidates = [
            assignment
            for assignment in assignments
            if relevant_assignment_date(assignment) == latest_date and assignment.lifecycle_stage
        ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda assignment: (
            assignment.lifecycle_stage.order,
            relevant_assignment_date(assignment),
            assignment.id,
        ),
    ).lifecycle_stage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-csv", type=Path, default=DEFAULT_QUEUE_CSV)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mapped-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = args.output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    grouping = load_grouping(args.csv_dir)
    lifecycle_stage_by_name = {
        stage.name: stage for stage in LifeCycleStage.objects.all()
    }
    User = get_user_model()
    history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    history_reason = "FishTalk migration: priority-hall stage backfill"

    with args.queue_csv.open("r", encoding="utf-8", newline="") as handle:
        queue_rows = list(csv.DictReader(handle))
    if args.mapped_only:
        queue_rows = [
            row for row in queue_rows if (row.get("has_population_component_map") or "").lower() == "true"
        ]
    if args.limit is not None:
        queue_rows = queue_rows[: args.limit]

    started_at = datetime.now(timezone.utc)
    results: list[BatchResult] = []

    for index, row in enumerate(queue_rows, start=1):
        report_dir_name = (row.get("report_dir") or "").strip()
        batch_id = (row.get("batch_id") or "").strip()
        batch_number = (row.get("batch_number") or "").strip()
        component_key = (row.get("component_key") or "").strip()
        mismatch_count = int(row.get("mismatch_count") or 0)
        log_path = logs_dir / f"{index:03d}_{report_dir_name}.log"
        started = time.monotonic()
        log_lines: list[str] = [
            f"report_dir={report_dir_name}",
            f"batch_id={batch_id}",
            f"batch_number={batch_number}",
            f"component_key={component_key}",
            f"queued_mismatch_count={mismatch_count}",
        ]

        try:
            report_dir = args.report_root / report_dir_name
            members_path = report_dir / "population_members.csv"
            if not members_path.exists():
                raise FileNotFoundError(f"Missing report members file: {members_path}")
            with members_path.open("r", encoding="utf-8", newline="") as handle:
                report_rows = list(csv.DictReader(handle))
                fieldnames = list(report_rows[0].keys()) if report_rows else []

            changed_population_to_stage: dict[str, str] = {}
            changed_report_rows = 0
            site_counter: Counter[str] = Counter()
            hall_counter: Counter[str] = Counter()
            for report_row in report_rows:
                container_id = (report_row.get("container_id") or "").strip()
                group_meta = grouping.get(container_id, {})
                site = group_meta.get("site", "")
                container_group = group_meta.get("container_group", "")
                if not is_priority_hall_site(site):
                    continue
                expected_stage = stage_from_hall(site, container_group)
                if not expected_stage:
                    continue
                first_stage = (report_row.get("first_stage") or "").strip()
                last_stage = (report_row.get("last_stage") or "").strip()
                if first_stage == expected_stage and last_stage == expected_stage:
                    continue
                report_row["first_stage"] = expected_stage
                report_row["last_stage"] = expected_stage
                population_id = (report_row.get("population_id") or "").strip()
                if population_id:
                    changed_population_to_stage[population_id] = expected_stage
                changed_report_rows += 1
                site_counter[site] += 1
                hall_counter[f"{site} / {container_group}"] += 1

            batch_stage_before = ""
            batch_stage_after = ""
            changed_assignments = 0
            missing_assignment_maps = 0

            if not args.dry_run:
                with transaction.atomic():
                    if changed_report_rows and fieldnames:
                        with members_path.open("w", encoding="utf-8", newline="") as handle:
                            writer = csv.DictWriter(handle, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(report_rows)

                    if batch_id:
                        batch = Batch.objects.get(pk=int(batch_id))
                        batch_stage_before = batch.lifecycle_stage.name if batch.lifecycle_stage else ""

                        updated_assignment_ids: set[int] = set()
                        for population_id, expected_stage in changed_population_to_stage.items():
                            assignment_map = get_assignment_external_map(
                                population_id,
                                component_key=component_key,
                                allow_legacy_fallback=True,
                            )
                            if assignment_map is None:
                                missing_assignment_maps += 1
                                continue
                            assignment = BatchContainerAssignment.objects.select_related("lifecycle_stage").get(
                                pk=assignment_map.target_object_id
                            )
                            stage = lifecycle_stage_by_name.get(expected_stage)
                            if stage is None:
                                raise ValueError(f"Missing LifeCycleStage '{expected_stage}'")
                            if assignment.id in updated_assignment_ids:
                                continue
                            if assignment.lifecycle_stage_id != stage.id:
                                assignment.lifecycle_stage = stage
                                save_with_history(
                                    assignment,
                                    user=history_user,
                                    reason=history_reason,
                                )
                                changed_assignments += 1
                            updated_assignment_ids.add(assignment.id)

                        batch_stage_after_obj = recompute_batch_stage(batch)
                        batch_stage_after = batch_stage_after_obj.name if batch_stage_after_obj else ""
                        if batch.lifecycle_stage_id != (batch_stage_after_obj.id if batch_stage_after_obj else None):
                            batch.lifecycle_stage = batch_stage_after_obj
                            save_with_history(
                                batch,
                                user=history_user,
                                reason=history_reason,
                            )
                        batch.refresh_from_db()
                        batch_stage_after = batch.lifecycle_stage.name if batch.lifecycle_stage else ""
            else:
                if batch_id:
                    batch = Batch.objects.get(pk=int(batch_id))
                    batch_stage_before = batch.lifecycle_stage.name if batch.lifecycle_stage else ""
                    batch_stage_after_obj = recompute_batch_stage(batch)
                    batch_stage_after = (
                        batch_stage_after_obj.name if batch_stage_after_obj else batch_stage_before
                    )

            log_lines.append(f"changed_report_rows={changed_report_rows}")
            log_lines.append(f"changed_assignments={changed_assignments}")
            log_lines.append(f"missing_assignment_maps={missing_assignment_maps}")
            log_lines.append(f"batch_stage_before={batch_stage_before}")
            log_lines.append(f"batch_stage_after={batch_stage_after}")
            if site_counter:
                log_lines.append("changed_sites=" + "; ".join(f"{site}:{count}" for site, count in sorted(site_counter.items())))
            if hall_counter:
                log_lines.append("changed_halls=" + "; ".join(f"{hall}:{count}" for hall, count in sorted(hall_counter.items())))

            result = BatchResult(
                report_dir=report_dir_name,
                batch_id=batch_id,
                batch_number=batch_number,
                component_key=component_key,
                mismatch_count=mismatch_count,
                changed_report_rows=changed_report_rows,
                changed_assignments=changed_assignments,
                missing_assignment_maps=missing_assignment_maps,
                batch_stage_before=batch_stage_before,
                batch_stage_after=batch_stage_after,
                success=True,
                error="",
                duration_sec=round(time.monotonic() - started, 3),
                log_path=str(log_path),
            )
        except Exception as exc:
            log_lines.append(f"error={exc}")
            result = BatchResult(
                report_dir=report_dir_name,
                batch_id=batch_id,
                batch_number=batch_number,
                component_key=component_key,
                mismatch_count=mismatch_count,
                changed_report_rows=0,
                changed_assignments=0,
                missing_assignment_maps=0,
                batch_stage_before="",
                batch_stage_after="",
                success=False,
                error=str(exc),
                duration_sec=round(time.monotonic() - started, 3),
                log_path=str(log_path),
            )

        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        results.append(result)
        status = "OK" if result.success else "FAIL"
        print(
            f"[{index}/{len(queue_rows)}] {status} {report_dir_name} "
            f"rows={result.changed_report_rows} assignments={result.changed_assignments} "
            f"batch_stage={result.batch_stage_before}->{result.batch_stage_after} "
            f"({result.duration_sec:.3f}s)"
        )
        if not result.success and not args.continue_on_error:
            break

    finished_at = datetime.now(timezone.utc)
    summary = {
        "queue_csv": str(args.queue_csv),
        "report_root": str(args.report_root),
        "csv_dir": str(args.csv_dir),
        "dry_run": args.dry_run,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "attempted": len(results),
        "succeeded": sum(1 for item in results if item.success),
        "failed": sum(1 for item in results if not item.success),
        "changed_report_rows": sum(item.changed_report_rows for item in results),
        "changed_assignments": sum(item.changed_assignments for item in results),
        "missing_assignment_maps": sum(item.missing_assignment_maps for item in results),
        "batch_stage_changes": [
            {
                "report_dir": item.report_dir,
                "batch_id": item.batch_id,
                "batch_number": item.batch_number,
                "before": item.batch_stage_before,
                "after": item.batch_stage_after,
            }
            for item in results
            if item.success and item.batch_stage_before != item.batch_stage_after
        ],
        "failed_report_dirs": [item.report_dir for item in results if not item.success],
    }

    summary_json = args.output_dir / "run_summary.json"
    summary_csv = args.output_dir / "run_summary.csv"
    summary_json.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": [item.__dict__ for item in results],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].__dict__.keys()) if results else [])
        if results:
            writer.writeheader()
            for item in results:
                writer.writerow(item.__dict__)

    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
