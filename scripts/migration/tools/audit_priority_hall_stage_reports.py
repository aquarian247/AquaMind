#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.tools.hall_stage_rules import is_priority_hall_site, stage_from_hall

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


def classify_focus(site: str) -> str:
    upper = (site or "").upper()
    if upper.startswith("FW"):
        return "Scotland_FW"
    if upper.startswith("S") and not upper.startswith("SF "):
        return "Faroe_S"
    if upper.startswith("BRS"):
        return "Broodstock_BRS"
    if upper.startswith("L"):
        return "Broodstock_L"
    return "Other"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit generated input-batch report dirs for authoritative hall-stage mismatches."
    )
    parser.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    parser.add_argument("--csv-dir", default=str(DEFAULT_CSV_DIR))
    parser.add_argument(
        "--output-prefix",
        help="Optional output prefix for .csv and .json artifacts.",
    )
    args = parser.parse_args()

    report_root = Path(args.report_root)
    csv_dir = Path(args.csv_dir)
    grouping = load_grouping(csv_dir)

    mismatches: list[dict[str, str | int]] = []
    summary_by_report: dict[str, dict[str, object]] = {}

    for report_dir in sorted(path for path in report_root.iterdir() if path.is_dir()):
        members_path = report_dir / "population_members.csv"
        if not members_path.exists():
            continue

        report_mismatches: list[dict[str, str | int]] = []
        with members_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                container_id = (row.get("container_id") or "").strip()
                if not container_id:
                    continue
                group_meta = grouping.get(container_id, {})
                site = group_meta.get("site", "")
                container_group = group_meta.get("container_group", "")
                if not is_priority_hall_site(site):
                    continue
                expected_stage = stage_from_hall(site, container_group)
                if not expected_stage:
                    continue
                first_stage = (row.get("first_stage") or "").strip()
                last_stage = (row.get("last_stage") or "").strip()
                if first_stage == expected_stage and last_stage == expected_stage:
                    continue

                mismatch = {
                    "report_dir": report_dir.name,
                    "component_key": (row.get("component_key") or "").strip(),
                    "population_id": (row.get("population_id") or "").strip(),
                    "population_name": (row.get("population_name") or "").strip(),
                    "container_id": container_id,
                    "site": site,
                    "container_group": container_group,
                    "focus": classify_focus(site),
                    "expected_stage": expected_stage,
                    "first_stage": first_stage,
                    "last_stage": last_stage,
                    "start_time": (row.get("start_time") or "").strip(),
                    "end_time": (row.get("end_time") or "").strip(),
                }
                report_mismatches.append(mismatch)
                mismatches.append(mismatch)

        if report_mismatches:
            summary_by_report[report_dir.name] = {
                "report_dir": report_dir.name,
                "mismatch_count": len(report_mismatches),
                "focuses": sorted({str(row["focus"]) for row in report_mismatches}),
                "sites": sorted({str(row["site"]) for row in report_mismatches}),
                "container_groups": sorted(
                    {str(row["container_group"]) for row in report_mismatches}
                ),
                "examples": [
                    {
                        "population_name": row["population_name"],
                        "expected_stage": row["expected_stage"],
                        "first_stage": row["first_stage"],
                        "last_stage": row["last_stage"],
                    }
                    for row in report_mismatches[:5]
                ],
            }

    print(f"Priority-hall mismatch rows: {len(mismatches)}")
    print(f"Report dirs affected: {len(summary_by_report)}")
    if summary_by_report:
        by_focus = defaultdict(int)
        for row in mismatches:
            by_focus[str(row["focus"])] += 1
        print("By focus:")
        for focus, count in sorted(by_focus.items()):
            print(f"  {focus}: {count}")
        print("Top affected report dirs:")
        for report_name, report_summary in sorted(
            summary_by_report.items(),
            key=lambda item: int(item[1]["mismatch_count"]),
            reverse=True,
        )[:20]:
            print(
                f"  {report_name}: {report_summary['mismatch_count']} "
                f"({', '.join(report_summary['sites'])})"
            )

    if args.output_prefix:
        output_prefix = Path(args.output_prefix)
        output_prefix.parent.mkdir(parents=True, exist_ok=True)

        csv_path = output_prefix.with_suffix(".csv")
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "report_dir",
                "component_key",
                "population_id",
                "population_name",
                "container_id",
                "site",
                "container_group",
                "focus",
                "expected_stage",
                "first_stage",
                "last_stage",
                "start_time",
                "end_time",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(mismatches)

        json_path = output_prefix.with_suffix(".json")
        json_path.write_text(
            json.dumps(
                {
                    "mismatch_row_count": len(mismatches),
                    "report_dir_count": len(summary_by_report),
                    "reports": list(summary_by_report.values()),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {csv_path}")
        print(f"Wrote {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
