#!/usr/bin/env python3
"""Build a targeted FW->Sea manual case pack from persisted evidence artifacts.

Outputs:
- population_members.csv suitable for pilot_migrate_component.py
- exact_transfer_events.csv/json for exact InternalDelivery replay
- summary.json with pack statistics
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_STITCHING_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching"
RAW_EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"


REPORT_FIELDNAMES = [
    "component_id",
    "component_key",
    "population_id",
    "population_name",
    "container_id",
    "start_time",
    "end_time",
    "first_stage",
    "last_stage",
]

EVENT_FIELDNAMES = [
    "event_id",
    "lineage_class",
    "source_population_id",
    "source_population_name",
    "source_site",
    "source_container",
    "sales_operation_id",
    "input_operation_id",
    "sale_timestamp",
    "input_start_time",
    "destination_population_id",
    "destination_population_name",
    "destination_site_code",
    "destination_site_name",
    "destination_container",
    "destination_ring_text",
    "transferred_count",
    "avg_weight_g",
    "transferred_biomass_kg",
    "notes",
]


@dataclass(frozen=True)
class ReportRow:
    population_id: str
    population_name: str
    container_id: str
    start_time: str
    end_time: str
    first_stage: str
    last_stage: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build targeted FW->Sea manual case pack")
    parser.add_argument("--batch-number", required=True)
    parser.add_argument("--component-key", required=True)
    parser.add_argument("--fw-batch-key", required=True)
    parser.add_argument("--fw-members-file", required=True, help="full_lifecycle_population_members_*.csv")
    parser.add_argument("--operation-ledger-csv", required=True)
    parser.add_argument("--sales-linkage-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_ring_text(value: str | None) -> str:
    raw = (value or "").upper()
    for token in ("RINGUR", "RING"):
        raw = raw.replace(token, "")
    return "".join(ch for ch in raw if ch.isalnum())


def parse_stage_bounds(aquamind_stages: str | None) -> tuple[str, str]:
    tokens = [token.strip() for token in str(aquamind_stages or "").split(",") if token.strip()]
    if not tokens:
        return "", ""
    return tokens[0], tokens[-1]


def build_report_row(full_lifecycle_row: dict) -> ReportRow:
    first_stage, last_stage = parse_stage_bounds(full_lifecycle_row.get("aquamind_stages"))
    return ReportRow(
        population_id=(full_lifecycle_row.get("population_id") or "").strip(),
        population_name=(full_lifecycle_row.get("population_name") or "").strip(),
        container_id=(full_lifecycle_row.get("container_id") or "").strip(),
        start_time=(full_lifecycle_row.get("start_time") or "").strip(),
        end_time=(full_lifecycle_row.get("end_time") or "").strip(),
        first_stage=first_stage,
        last_stage=last_stage,
    )


def read_full_lifecycle_index(path: Path) -> dict[str, dict]:
    rows = load_csv_rows(path)
    return {
        (row.get("population_id") or "").strip(): row
        for row in rows
        if (row.get("population_id") or "").strip()
    }


def read_raw_population_index() -> dict[str, dict]:
    path = RAW_EXTRACT_DIR / "populations.csv"
    return {
        (row.get("PopulationID") or "").strip(): row
        for row in load_csv_rows(path)
        if (row.get("PopulationID") or "").strip()
    }


def quantize_kg(count: int, avg_weight_g: Decimal) -> Decimal:
    return ((Decimal(count) * avg_weight_g) / Decimal("1000")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    fw_members_path = Path(args.fw_members_file)
    if not fw_members_path.is_absolute():
        fw_members_path = (PROJECT_ROOT / fw_members_path).resolve()

    ledger_rows = load_csv_rows(Path(args.operation_ledger_csv))
    sales_linkage_rows = load_csv_rows(Path(args.sales_linkage_csv))
    fw_members_rows = load_csv_rows(fw_members_path)

    canonical_ledger_rows = [
        row
        for row in ledger_rows
        if (row.get("population_representation_index") or "").strip() == "1"
    ]
    if not canonical_ledger_rows:
        raise SystemExit("No canonical ledger rows found (population_representation_index=1).")

    fw_source_rows = [
        row
        for row in fw_members_rows
        if (row.get("source_batch_key") or "").strip() == args.fw_batch_key
    ]
    if not fw_source_rows:
        raise SystemExit(
            f"No FW source rows found in {fw_members_path} for source_batch_key={args.fw_batch_key!r}."
        )

    stitching_cache: dict[Path, dict[str, dict]] = {fw_members_path: read_full_lifecycle_index(fw_members_path)}
    raw_population_index = read_raw_population_index()

    report_rows_by_population: dict[str, ReportRow] = {}
    for row in fw_source_rows:
        report_row = build_report_row(row)
        report_rows_by_population[report_row.population_id] = report_row

    for row in canonical_ledger_rows:
        member_file_name = (row.get("population_member_file") or "").strip()
        member_population_id = (row.get("population_id") or "").strip()
        if not member_file_name or not member_population_id:
            raise SystemExit(
                f"Ledger row {row.get('manual_event_id')!r} is missing population-member reference."
            )
        member_file_path = (INPUT_STITCHING_DIR / member_file_name).resolve()
        if member_file_path not in stitching_cache:
            stitching_cache[member_file_path] = read_full_lifecycle_index(member_file_path)
        member_row = stitching_cache[member_file_path].get(member_population_id)
        if member_row is None:
            raise SystemExit(
                f"Population {member_population_id} from {member_file_name} "
                f"not found for ledger row {row.get('manual_event_id')!r}."
            )
        report_row = build_report_row(member_row)
        report_rows_by_population[report_row.population_id] = report_row

    sales_index: defaultdict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in sales_linkage_rows:
        sales_op = (row.get("SalesOperationID") or "").strip()
        input_op = (row.get("InputOperationID") or "").strip()
        if not sales_op or not input_op:
            continue
        sales_index[(sales_op, input_op)].append(row)

    fw_population_name_by_id = {
        report_row.population_id: report_row.population_name
        for report_row in report_rows_by_population.values()
    }

    exact_event_rows: list[dict] = []
    source_population_ids: set[str] = set()
    for row in canonical_ledger_rows:
        manual_event_id = (row.get("manual_event_id") or "").strip()
        sales_op = (row.get("sales_operation_id") or "").strip()
        input_op = (row.get("input_operation_id") or "").strip()
        source_container = (row.get("source_container") or "").strip()
        source_site = (row.get("source_site") or "").strip()
        destination_ring_text = (row.get("destination_ring_text") or "").strip()
        fish_count = int(round(float(row.get("fish_count") or 0)))
        avg_weight_g = Decimal(str(row.get("avg_weight_g") or 0)).quantize(Decimal("0.01"))

        candidates = list(sales_index.get((sales_op, input_op), []))
        if not candidates:
            raise SystemExit(f"No sales-linkage extract rows found for ledger row {manual_event_id}.")

        narrowed = [
            candidate
            for candidate in candidates
            if (candidate.get("SourceContainerName") or "").strip() == source_container
            and (candidate.get("SourceSite") or "").strip() == source_site
            and int(round(float(candidate.get("StatusSalesCount") or 0))) == fish_count
        ]
        if len(narrowed) > 1:
            ring_key = normalize_ring_text(destination_ring_text)
            ring_filtered = [
                candidate
                for candidate in narrowed
                if normalize_ring_text(candidate.get("RingText")) == ring_key
            ]
            if ring_filtered:
                narrowed = ring_filtered
        if len(narrowed) != 1:
            raise SystemExit(
                f"Unable to uniquely resolve source population for ledger row {manual_event_id}: "
                f"matched {len(narrowed)} candidate(s)."
            )

        matched = narrowed[0]
        source_population_id = (matched.get("PopulationID") or "").strip()
        if not source_population_id:
            raise SystemExit(f"Matched sales-linkage row for {manual_event_id} has no PopulationID.")
        source_population_ids.add(source_population_id)

        exact_event_rows.append(
            {
                "event_id": manual_event_id,
                "lineage_class": (row.get("lineage_class") or "").strip(),
                "source_population_id": source_population_id,
                "source_population_name": fw_population_name_by_id.get(source_population_id, ""),
                "source_site": source_site,
                "source_container": source_container,
                "sales_operation_id": sales_op,
                "input_operation_id": input_op,
                "sale_timestamp": (
                    f"{(row.get('sale_date') or '').strip()} {(row.get('sale_time') or '').strip()}".strip()
                ),
                "input_start_time": (row.get("input_start_time") or "").strip(),
                "destination_population_id": (row.get("population_id") or "").strip(),
                "destination_population_name": (row.get("population_name") or "").strip(),
                "destination_site_code": (row.get("destination_site_code") or "").strip(),
                "destination_site_name": (row.get("destination_site_name") or "").strip(),
                "destination_container": (row.get("target_container") or "").strip(),
                "destination_ring_text": destination_ring_text,
                "transferred_count": fish_count,
                "avg_weight_g": str(avg_weight_g),
                "transferred_biomass_kg": str(quantize_kg(fish_count, avg_weight_g)),
                "notes": (row.get("notes") or "").strip(),
            }
        )

    missing_fw_source_rows = sorted(source_population_ids - set(report_rows_by_population))
    if missing_fw_source_rows:
        for population_id in missing_fw_source_rows:
            raw_row = raw_population_index.get(population_id)
            if raw_row is None:
                raise SystemExit(
                    "Resolved source populations are missing from both the FW member set "
                    "and raw populations extract: "
                    + ", ".join(missing_fw_source_rows[:10])
                )
            report_rows_by_population[population_id] = ReportRow(
                population_id=population_id,
                population_name=args.batch_number,
                container_id=(raw_row.get("ContainerID") or "").strip(),
                start_time=(raw_row.get("StartTime") or "").strip(),
                end_time=(raw_row.get("EndTime") or "").strip(),
                first_stage="",
                last_stage="",
            )

    for row in exact_event_rows:
        source_population_id = row["source_population_id"]
        report_row = report_rows_by_population.get(source_population_id)
        if report_row is not None and report_row.population_name:
            row["source_population_name"] = report_row.population_name

    report_rows_sorted = sorted(
        report_rows_by_population.values(),
        key=lambda row: (row.start_time, row.population_name, row.population_id),
    )

    report_path = output_dir / "population_members.csv"
    with report_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDNAMES)
        writer.writeheader()
        for row in report_rows_sorted:
            writer.writerow(
                {
                    "component_id": args.component_key,
                    "component_key": args.component_key,
                    "population_id": row.population_id,
                    "population_name": row.population_name,
                    "container_id": row.container_id,
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "first_stage": row.first_stage,
                    "last_stage": row.last_stage,
                }
            )

    exact_events_csv_path = output_dir / "exact_transfer_events.csv"
    with exact_events_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDNAMES)
        writer.writeheader()
        for row in exact_event_rows:
            source_population_id = str(row.get("source_population_id") or "").strip()
            source_report_row = report_rows_by_population.get(source_population_id)
            if source_report_row is not None and source_report_row.population_name:
                row["source_population_name"] = source_report_row.population_name
            writer.writerow(row)

    exact_events_json_path = output_dir / "exact_transfer_events.json"
    for row in exact_event_rows:
        source_population_id = str(row.get("source_population_id") or "").strip()
        source_report_row = report_rows_by_population.get(source_population_id)
        if source_report_row is not None and source_report_row.population_name:
            row["source_population_name"] = source_report_row.population_name
    exact_events_json_path.write_text(
        json.dumps(
            {
                "batch_number": args.batch_number,
                "component_key": args.component_key,
                "fw_batch_key": args.fw_batch_key,
                "row_count": len(exact_event_rows),
                "rows": exact_event_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "batch_number": args.batch_number,
        "component_key": args.component_key,
        "fw_batch_key": args.fw_batch_key,
        "member_count": len(report_rows_sorted),
        "fw_member_count": len(fw_source_rows),
        "sea_member_count": len(report_rows_sorted) - len(fw_source_rows),
        "exact_event_count": len(exact_event_rows),
        "distinct_workflow_pair_count": len(
            {
                (row["sales_operation_id"], row["input_operation_id"])
                for row in exact_event_rows
            }
        ),
        "total_transferred_count": sum(int(row["transferred_count"]) for row in exact_event_rows),
        "output_files": {
            "population_members_csv": str(report_path),
            "exact_transfer_events_csv": str(exact_events_csv_path),
            "exact_transfer_events_json": str(exact_events_json_path),
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        f"Built targeted FW->Sea case pack at {output_dir} "
        f"(members={summary['member_count']}, exact_events={summary['exact_event_count']}, "
        f"workflows={summary['distinct_workflow_pair_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
