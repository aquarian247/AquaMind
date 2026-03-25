#!/usr/bin/env python3
"""Audit live assignment lifecycle stages against priority-hall expectations."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
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

from apps.batch.models.assignment import BatchContainerAssignment
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map


DEFAULT_QUEUE_CSV = PROJECT_ROOT / "scripts" / "migration" / "output" / "priority_hall_stage_backfill_queue_20260325.csv"
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_batch_migration"
DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


def load_grouping(csv_dir: Path) -> dict[str, dict[str, str]]:
    path = csv_dir / "grouped_organisation.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing grouped organisation extract: {path}")
    grouping: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-csv", type=Path, default=DEFAULT_QUEUE_CSV)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--output-path", type=Path, required=True)
    args = parser.parse_args()

    grouping = load_grouping(args.csv_dir)
    mapped_rows: list[dict[str, str]] = []
    with args.queue_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("has_population_component_map") or "").lower() != "true":
                continue
            mapped_rows.append(row)

    report_summaries: list[dict[str, object]] = []
    residual_mismatch_count = 0
    for row in mapped_rows:
        members_path = args.report_root / (row.get("report_dir") or "") / "population_members.csv"
        if not members_path.exists():
            continue
        mismatches: list[dict[str, object]] = []
        with members_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for member in reader:
                container_id = (member.get("container_id") or "").strip()
                group = grouping.get(container_id, {})
                site = group.get("site", "")
                container_group = group.get("container_group", "")
                if not is_priority_hall_site(site):
                    continue
                expected_stage = stage_from_hall(site, container_group)
                if not expected_stage:
                    continue
                assignment_map = get_assignment_external_map(
                    (member.get("population_id") or "").strip(),
                    component_key=(row.get("component_key") or "").strip(),
                    allow_legacy_fallback=True,
                )
                if assignment_map is None:
                    continue
                assignment = BatchContainerAssignment.objects.select_related("lifecycle_stage").get(
                    pk=assignment_map.target_object_id
                )
                actual_stage = assignment.lifecycle_stage.name if assignment.lifecycle_stage else ""
                if actual_stage == expected_stage:
                    continue
                mismatches.append(
                    {
                        "population_id": (member.get("population_id") or "").strip(),
                        "population_name": (member.get("population_name") or "").strip(),
                        "assignment_id": assignment.id,
                        "site": site,
                        "container_group": container_group,
                        "expected_stage": expected_stage,
                        "actual_stage": actual_stage,
                    }
                )
        if mismatches:
            residual_mismatch_count += len(mismatches)
            report_summaries.append(
                {
                    "report_dir": row.get("report_dir") or "",
                    "batch_id": row.get("batch_id") or "",
                    "batch_number": row.get("batch_number") or "",
                    "mismatch_count": len(mismatches),
                    "examples": mismatches[:5],
                }
            )

    payload = {
        "mapped_report_count": len(mapped_rows),
        "residual_assignment_mismatch_count": residual_mismatch_count,
        "affected_reports": len(report_summaries),
        "reports": report_summaries,
    }
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
