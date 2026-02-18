#!/usr/bin/env python3
"""Build a deterministic trace-target pack for FWSEA blocker cohorts.

Tooling-only diagnostics:
- no runtime/API/UI coupling,
- no migration-policy mutation.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_DIR = (
    PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
)
DEFAULT_CLASSIFICATIONS = "reverse_flow_fw_only"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def load_csv_rows(
    path: Path,
    *,
    required: bool = True,
) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required CSV file: {path}")
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def classify_stage(value: str) -> str:
    upper = normalize(value).upper()
    if "MARINE" in upper:
        return "marine"
    if "HATCHERY" in upper or "FRESH" in upper or "FW" in upper:
        return "fw"
    return "unknown"


def parse_start_time(value: str) -> datetime | None:
    text = normalize(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def compact_counter(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    pairs = [f"{key}:{value}" for key, value in sorted(counter.items())]
    return ",".join(pairs)


def load_operation_context(
    csv_dir: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, object]]]:  # noqa: C901
    operation_rows = load_csv_rows(
        csv_dir / "internal_delivery_operations.csv",
        required=True,
    )
    action_rows = load_csv_rows(
        csv_dir / "internal_delivery_actions.csv",
        required=True,
    )
    metadata_rows = load_csv_rows(
        csv_dir / "internal_delivery_action_metadata.csv",
        required=True,
    )
    population_rows = load_csv_rows(csv_dir / "populations.csv", required=True)
    grouped_rows = load_csv_rows(
        csv_dir / "grouped_organisation.csv",
        required=True,
    )

    operations_by_id: dict[str, dict[str, str]] = {}
    for row in operation_rows:
        op_id = normalize(row.get("OperationID"))
        if op_id:
            operations_by_id[op_id] = row

    population_to_container: dict[str, str] = {}
    for row in population_rows:
        pop_id = normalize(row.get("PopulationID"))
        container_id = normalize(row.get("ContainerID"))
        if pop_id:
            population_to_container[pop_id] = container_id

    container_to_stage_text: dict[str, str] = {}
    for row in grouped_rows:
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in container_to_stage_text:
            container_to_stage_text[container_id] = normalize(
                row.get("ProdStage")
            )

    operation_context: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "action_count": 0,
            "population_ids": set(),
            "parameter_counts": Counter(),
            "metadata_row_count": 0,
            "trip_rows": 0,
            "guid_rows": 0,
            "stage_class_counts": Counter(),
        }
    )

    for row in action_rows:
        op_id = normalize(row.get("OperationID"))
        if not op_id:
            continue
        pop_id = normalize(row.get("PopulationID"))
        ctx = operation_context[op_id]
        ctx["action_count"] = int(ctx["action_count"]) + 1
        if pop_id:
            population_ids = ctx["population_ids"]
            assert isinstance(population_ids, set)
            population_ids.add(pop_id)

    for row in metadata_rows:
        op_id = normalize(row.get("OperationID"))
        if not op_id:
            continue
        ctx = operation_context[op_id]
        ctx["metadata_row_count"] = int(ctx["metadata_row_count"]) + 1
        parameter_counts = ctx["parameter_counts"]
        assert isinstance(parameter_counts, Counter)
        param_id = normalize(row.get("ParameterID"))
        if param_id:
            parameter_counts[param_id] += 1
        if normalize(row.get("TripID")):
            ctx["trip_rows"] = int(ctx["trip_rows"]) + 1
        if normalize(row.get("ParameterGuid")):
            ctx["guid_rows"] = int(ctx["guid_rows"]) + 1

    for op_id, ctx in operation_context.items():
        stage_counts: Counter[str] = Counter()
        population_ids = ctx["population_ids"]
        assert isinstance(population_ids, set)
        for pop_id in population_ids:
            container_id = population_to_container.get(pop_id, "")
            stage_text = container_to_stage_text.get(container_id, "")
            stage_counts[classify_stage(stage_text)] += 1
        ctx["stage_class_counts"] = stage_counts

    return operations_by_id, operation_context


def operation_profile(
    operation_id: str,
    operations_by_id: dict[str, dict[str, str]],
    operation_context: dict[str, dict[str, object]],
) -> dict[str, object]:
    op_row = operations_by_id.get(operation_id, {})
    ctx = operation_context.get(operation_id, {})

    population_ids = ctx.get("population_ids")
    parameter_counts = ctx.get("parameter_counts")
    stage_class_counts = ctx.get("stage_class_counts")

    pop_count = len(population_ids) if isinstance(population_ids, set) else 0
    param_counter = (
        parameter_counts
        if isinstance(parameter_counts, Counter)
        else Counter()
    )
    stage_counter = (
        stage_class_counts
        if isinstance(stage_class_counts, Counter)
        else Counter()
    )

    return {
        "operation_id": operation_id,
        "start_time": normalize(op_row.get("StartTime")),
        "end_time": normalize(op_row.get("EndTime")),
        "operation_type": normalize(op_row.get("OperationType")),
        "comment": normalize(op_row.get("Comment")),
        "action_count": int(ctx.get("action_count") or 0),
        "population_count": pop_count,
        "metadata_row_count": int(ctx.get("metadata_row_count") or 0),
        "trip_rows": int(ctx.get("trip_rows") or 0),
        "guid_rows": int(ctx.get("guid_rows") or 0),
        "parameter_counts": param_counter,
        "stage_class_counts": stage_counter,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic FWSEA trace-target pack "
            "from matrix artifacts"
        )
    )
    parser.add_argument(
        "--matrix-summary-json",
        required=True,
        help="Matrix summary JSON from fwsea_endpoint_gate_matrix.py",
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="Extract CSV directory (default: scripts/migration/data/extract)",
    )
    parser.add_argument(
        "--classifications",
        default=DEFAULT_CLASSIFICATIONS,
        help="Comma-separated classification filter",
    )
    parser.add_argument(
        "--output-md",
        required=True,
        help="Output markdown report path",
    )
    parser.add_argument(
        "--output-tsv",
        help=(
            "Optional TSV output path "
            "(default: sibling of --output-md)"
        ),
    )
    parser.add_argument("--summary-json", help="Optional JSON summary output path")
    return parser.parse_args()


def main() -> int:  # noqa: C901
    args = parse_args()
    matrix_summary_path = Path(args.matrix_summary_json)
    csv_dir = Path(args.csv_dir)
    selected_classes = {
        normalize(value)
        for value in args.classifications.split(",")
        if normalize(value)
    }

    matrix_payload = json.loads(matrix_summary_path.read_text(encoding="utf-8"))
    matrix_rows = matrix_payload.get("rows") or []
    matrix_dir = matrix_summary_path.parent

    trace_targets: list[dict[str, str]] = []
    for matrix_row in matrix_rows:
        classification = normalize(matrix_row.get("classification"))
        if classification not in selected_classes:
            continue
        gate_summary_name = normalize(matrix_row.get("gate_summary"))
        if not gate_summary_name:
            continue
        gate_summary_path = matrix_dir / gate_summary_name
        if not gate_summary_path.exists():
            continue
        gate_payload = json.loads(
            gate_summary_path.read_text(encoding="utf-8")
        )
        for example in gate_payload.get("examples") or []:
            reason = normalize(example.get("reason"))
            if not reason or reason == "deterministic":
                continue
            sales_operation_id = normalize(
                example.get("sales_operation_id")
            )
            input_operation_id = normalize(
                example.get("input_operation_id")
            )
            if not sales_operation_id and not input_operation_id:
                continue
            trace_targets.append(
                {
                    "batch_name": normalize(matrix_row.get("batch_name")),
                    "component_key": normalize(matrix_row.get("component_key")),
                    "classification": classification,
                    "reason": reason,
                    "direction": normalize(example.get("direction")),
                    "sales_operation_id": sales_operation_id,
                    "input_operation_id": input_operation_id,
                    "source_component_population_count": str(
                        int(example.get("source_component_population_count") or 0)
                    ),
                    "target_population_count": str(
                        int(example.get("target_population_count") or 0)
                    ),
                }
            )

    unique_targets: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for row in trace_targets:
        key = (
            row["batch_name"],
            row["sales_operation_id"],
            row["input_operation_id"],
            row["reason"],
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_targets.append(row)

    operations_by_id, operation_context = load_operation_context(csv_dir)

    enriched_rows: list[dict[str, object]] = []
    unique_operation_ids: set[str] = set()
    reason_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()

    for target in unique_targets:
        sales_operation_id = target["sales_operation_id"]
        input_operation_id = target["input_operation_id"]
        if sales_operation_id:
            unique_operation_ids.add(sales_operation_id)
        if input_operation_id:
            unique_operation_ids.add(input_operation_id)

        sales = operation_profile(
            sales_operation_id,
            operations_by_id,
            operation_context,
        )
        input_side = operation_profile(
            input_operation_id,
            operations_by_id,
            operation_context,
        )

        sales_start = parse_start_time(str(sales.get("start_time") or ""))
        input_start = parse_start_time(str(input_side.get("start_time") or ""))
        delta_minutes: int | None = None
        if sales_start and input_start:
            delta = input_start - sales_start
            delta_minutes = int(delta.total_seconds() // 60)

        row = {
            "batch_name": target["batch_name"],
            "component_key": target["component_key"],
            "classification": target["classification"],
            "reason": target["reason"],
            "direction": target["direction"],
            "source_component_population_count": int(
                target["source_component_population_count"]
            ),
            "target_population_count": int(target["target_population_count"]),
            "sales_operation_id": sales_operation_id,
            "sales_start_time": sales["start_time"],
            "sales_operation_type": sales["operation_type"],
            "sales_action_count": sales["action_count"],
            "sales_population_count": sales["population_count"],
            "sales_stage_class_counts": compact_counter(
                sales["stage_class_counts"]
            ),
            "sales_parameter_counts": compact_counter(sales["parameter_counts"]),
            "sales_trip_rows": sales["trip_rows"],
            "sales_guid_rows": sales["guid_rows"],
            "input_operation_id": input_operation_id,
            "input_start_time": input_side["start_time"],
            "input_operation_type": input_side["operation_type"],
            "input_action_count": input_side["action_count"],
            "input_population_count": input_side["population_count"],
            "input_stage_class_counts": compact_counter(
                input_side["stage_class_counts"]
            ),
            "input_parameter_counts": compact_counter(
                input_side["parameter_counts"]
            ),
            "input_trip_rows": input_side["trip_rows"],
            "input_guid_rows": input_side["guid_rows"],
            "pair_start_delta_minutes": delta_minutes,
        }
        enriched_rows.append(row)
        reason_counts[row["reason"]] += 1
        direction_counts[row["direction"]] += 1
        classification_counts[row["classification"]] += 1

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_tsv = (
        Path(args.output_tsv)
        if args.output_tsv
        else output_md.with_suffix(".tsv")
    )

    tsv_headers = [
        "batch_name",
        "component_key",
        "classification",
        "reason",
        "direction",
        "source_component_population_count",
        "target_population_count",
        "sales_operation_id",
        "sales_start_time",
        "sales_operation_type",
        "sales_action_count",
        "sales_population_count",
        "sales_stage_class_counts",
        "sales_parameter_counts",
        "sales_trip_rows",
        "sales_guid_rows",
        "input_operation_id",
        "input_start_time",
        "input_operation_type",
        "input_action_count",
        "input_population_count",
        "input_stage_class_counts",
        "input_parameter_counts",
        "input_trip_rows",
        "input_guid_rows",
        "pair_start_delta_minutes",
    ]
    with output_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tsv_headers, delimiter="\t")
        writer.writeheader()
        for row in enriched_rows:
            writer.writerow(row)

    lines: list[str] = []
    lines.append("# FWSEA Trace Target Pack")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- Matrix summary: `{matrix_summary_path}`")
    lines.append(f"- CSV directory: `{csv_dir}`")
    lines.append(
        f"- Classification filter: {', '.join(sorted(selected_classes)) or '(none)'}"
    )
    lines.append(f"- Trace target rows: {len(enriched_rows)}")
    lines.append(f"- Unique operation IDs: {len(unique_operation_ids)}")
    lines.append("")
    lines.append("## Target Mix")
    lines.append("")
    for key, count in sorted(
        classification_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- classification `{key}`: {count}")
    for key, count in sorted(
        reason_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- reason `{key}`: {count}")
    for key, count in sorted(
        direction_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"- direction `{key}`: {count}")
    lines.append("")
    lines.append(
        "| batch | class | reason | direction | sales op (type/time) | input op (type/time) | "
        "sales params | input params | sales stage mix | input stage mix | delta min |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |"
    )
    for row in enriched_rows:
        sales_desc = (
            f"{row['sales_operation_id']} "
            f"(t{row['sales_operation_type'] or '-'} "
            f"@ {row['sales_start_time'] or '-'})"
        )
        input_desc = (
            f"{row['input_operation_id']} "
            f"(t{row['input_operation_type'] or '-'} "
            f"@ {row['input_start_time'] or '-'})"
        )
        lines.append(
            f"| {row['batch_name']} | {row['classification']} | "
            f"{row['reason']} | {row['direction']} | "
            f"{sales_desc} | {input_desc} | {row['sales_parameter_counts']} | "
            f"{row['input_parameter_counts']} | {row['sales_stage_class_counts']} | "
            f"{row['input_stage_class_counts']} | "
            f"{row['pair_start_delta_minutes'] if row['pair_start_delta_minutes'] is not None else 'n/a'} |"
        )
    lines.append("")
    lines.append("## XE Target Operation IDs")
    lines.append("")
    lines.append("Use this ID set in `OperationID` predicates for SQL trace capture.")
    lines.append("")
    for op_id in sorted(unique_operation_ids):
        lines.append(f"- `{op_id}`")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Trace target TSV: `{output_tsv}`")
    if args.summary_json:
        lines.append(f"- Trace target JSON: `{Path(args.summary_json)}`")

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = {
        "matrix_summary_json": str(matrix_summary_path),
        "csv_dir": str(csv_dir),
        "classification_filter": sorted(selected_classes),
        "trace_target_count": len(enriched_rows),
        "unique_operation_count": len(unique_operation_ids),
        "classification_counts": dict(sorted(classification_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "direction_counts": dict(sorted(direction_counts.items())),
        "operation_ids": sorted(unique_operation_ids),
        "rows": enriched_rows,
    }
    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(f"Wrote {output_md}")
    print(f"Wrote {output_tsv}")
    if args.summary_json:
        print(f"Wrote {Path(args.summary_json)}")
    print(
        f"Trace rows={len(enriched_rows)} "
        f"unique_operations={len(unique_operation_ids)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

