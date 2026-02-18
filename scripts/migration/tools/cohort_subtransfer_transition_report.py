#!/usr/bin/env python3
"""Report deterministic stage transitions from SubTransfers lineage.

Given an Ext_Inputs batch key (InputName + InputNumber + YearClass),
this tool reconstructs descendant populations through SubTransfers and emits
source-backed transition edges (SourcePopBefore -> DestPopAfter).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CSV_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
DEFAULT_STAGE_MAP = (
    "ROGN=Egg&Alevin,5M=Fry,A=Parr,BA=Parr,BB=Parr,"
    "C=Smolt,D=Smolt,E=Post-Smolt,F=Post-Smolt"
)
ROLE_SOURCE_BEFORE = "SourcePopBefore"
ROLE_SOURCE_AFTER = "SourcePopAfter"
ROLE_DEST_BEFORE = "DestPopBefore"
ROLE_DEST_AFTER = "DestPopAfter"
OP_TIME_FMT = "%Y-%m-%d %H:%M:%S"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_stage_map(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for chunk in raw.split(","):
        chunk = normalize(chunk)
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Invalid stage-map entry: {chunk}")
        key, value = chunk.split("=", 1)
        mapping[normalize(key).upper()] = normalize(value)
    return mapping


def hall_prefix(container_group: str) -> str:
    text = normalize(container_group)
    if not text:
        return ""
    return text.split()[0].upper()


def build_population_maps(
    populations: list[dict[str, str]],
    grouped_org: list[dict[str, str]],
    containers: list[dict[str, str]],
) -> tuple[dict[str, str], dict[str, dict[str, str]], dict[str, str]]:  # noqa: C901
    pop_to_container: dict[str, str] = {}
    for row in populations:
        pop_id = normalize(row.get("PopulationID"))
        if pop_id:
            pop_to_container[pop_id] = normalize(row.get("ContainerID"))

    container_info: dict[str, dict[str, str]] = {}
    for row in grouped_org:
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in container_info:
            container_info[container_id] = row

    container_name: dict[str, str] = {}
    for row in containers:
        container_id = normalize(row.get("ContainerID"))
        if container_id and container_id not in container_name:
            container_name[container_id] = normalize(row.get("ContainerName"))

    return pop_to_container, container_info, container_name


def collect_seed_populations(
    ext_inputs: list[dict[str, str]],
    *,
    input_name: str,
    input_number: str,
    year_class: str,
) -> set[str]:  # noqa: C901
    seeds: set[str] = set()
    for row in ext_inputs:
        if normalize(row.get("InputName")) != input_name:
            continue
        if normalize(row.get("InputNumber")) != input_number:
            continue
        if normalize(row.get("YearClass")) != year_class:
            continue
        pop_id = normalize(row.get("PopulationID"))
        if pop_id:
            seeds.add(pop_id)
    return seeds


def build_lineage_adjacency(
    sub_transfers: list[dict[str, str]],
) -> dict[str, set[str]]:  # noqa: C901
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in sub_transfers:
        source_before = normalize(row.get(ROLE_SOURCE_BEFORE))
        source_after = normalize(row.get(ROLE_SOURCE_AFTER))
        dest_before = normalize(row.get(ROLE_DEST_BEFORE))
        dest_after = normalize(row.get(ROLE_DEST_AFTER))
        if source_before and source_after:
            adjacency[source_before].add(source_after)
        if source_before and dest_after:
            adjacency[source_before].add(dest_after)
        if dest_before and dest_after:
            adjacency[dest_before].add(dest_after)
    return adjacency


def traverse_lineage(
    seeds: set[str],
    adjacency: dict[str, set[str]],
    max_depth: int,
) -> set[str]:  # noqa: C901
    visited: set[str] = set(seeds)
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds)
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for nxt in adjacency.get(node, set()):
            if nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt, depth + 1))
    return visited


def stage_for_population(
    population_id: str,
    pop_to_container: dict[str, str],
    container_info: dict[str, dict[str, str]],
    stage_map: dict[str, str],
) -> str:
    container_id = pop_to_container.get(population_id, "")
    info = container_info.get(container_id) or {}
    prefix = hall_prefix(normalize(info.get("ContainerGroup")))
    return stage_map.get(prefix, "UNKNOWN")


def build_transition_rows(
    sub_transfers: list[dict[str, str]],
    lineage_populations: set[str],
    pop_to_container: dict[str, str],
    container_info: dict[str, dict[str, str]],
    container_name: dict[str, str],
    stage_map: dict[str, str],
    station_filter: str | None,
) -> list[dict[str, str]]:  # noqa: C901
    rows: list[dict[str, str]] = []
    station = normalize(station_filter) if station_filter else ""
    for row in sub_transfers:
        source_pop = normalize(row.get(ROLE_SOURCE_BEFORE))
        target_pop = normalize(row.get(ROLE_DEST_AFTER))
        if not source_pop or not target_pop:
            continue
        if (
            source_pop not in lineage_populations
            or target_pop not in lineage_populations
        ):
            continue

        source_container = pop_to_container.get(source_pop, "")
        target_container = pop_to_container.get(target_pop, "")
        source_info = container_info.get(source_container) or {}
        target_info = container_info.get(target_container) or {}

        source_site = normalize(source_info.get("Site"))
        target_site = normalize(target_info.get("Site"))
        if station and (source_site != station or target_site != station):
            continue

        source_hall_prefix = hall_prefix(
            normalize(source_info.get("ContainerGroup"))
        )
        target_hall_prefix = hall_prefix(
            normalize(target_info.get("ContainerGroup"))
        )
        source_stage = stage_for_population(
            source_pop,
            pop_to_container,
            container_info,
            stage_map,
        )
        target_stage = stage_for_population(
            target_pop,
            pop_to_container,
            container_info,
            stage_map,
        )
        rows.append(
            {
                "operation_id": normalize(row.get("OperationID")),
                "operation_time": normalize(row.get("OperationTime")),
                "source_population_id": source_pop,
                "target_population_id": target_pop,
                "source_container": container_name.get(source_container, ""),
                "target_container": container_name.get(target_container, ""),
                "source_site": source_site,
                "target_site": target_site,
                "source_hall_prefix": source_hall_prefix,
                "target_hall_prefix": target_hall_prefix,
                "source_stage": source_stage,
                "target_stage": target_stage,
                "source_prod_stage": normalize(source_info.get("ProdStage")),
                "target_prod_stage": normalize(target_info.get("ProdStage")),
            }
        )
    return rows


def stage_windows(  # noqa: C901
    rows: list[dict[str, str]],
) -> dict[str, dict[str, str | int]]:
    pair_times: dict[str, list[datetime]] = defaultdict(list)
    pair_counts: Counter[str] = Counter()
    for row in rows:
        key = f"{row['source_stage']}->{row['target_stage']}"
        pair_counts[key] += 1
        text = normalize(row.get("operation_time"))
        if not text:
            continue
        try:
            pair_times[key].append(datetime.strptime(text, OP_TIME_FMT))
        except ValueError:
            continue
    result: dict[str, dict[str, str | int]] = {}
    for key, count in sorted(pair_counts.items()):
        times = pair_times.get(key, [])
        result[key] = {
            "count": int(count),
            "min_time": times[0].isoformat(sep=" ") if times else "",
            "max_time": times[-1].isoformat(sep=" ") if times else "",
        }
        if times:
            result[key]["min_time"] = min(times).isoformat(sep=" ")
            result[key]["max_time"] = max(times).isoformat(sep=" ")
    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic stage-transition report from SubTransfers"
        )
    )
    parser.add_argument("--input-name", required=True)
    parser.add_argument("--input-number", required=True)
    parser.add_argument("--year-class", required=True)
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="Extract CSV directory",
    )
    parser.add_argument(
        "--hall-stage-map",
        default=DEFAULT_STAGE_MAP,
        help="Comma-separated map, e.g. ROGN=Egg&Alevin,5M=Fry",
    )
    parser.add_argument(
        "--station-site",
        help="Optional exact site filter (e.g. 'S21 Viðareiði')",
    )
    parser.add_argument("--lineage-max-depth", type=int, default=25)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    stage_map = parse_stage_map(args.hall_stage_map)

    ext_inputs = load_csv_rows(csv_dir / "ext_inputs.csv")
    populations = load_csv_rows(csv_dir / "populations.csv")
    grouped_org = load_csv_rows(csv_dir / "grouped_organisation.csv")
    sub_transfers = load_csv_rows(csv_dir / "sub_transfers.csv")
    containers = load_csv_rows(csv_dir / "containers.csv")

    pop_to_container, container_info, container_name = build_population_maps(
        populations,
        grouped_org,
        containers,
    )

    seeds = collect_seed_populations(
        ext_inputs,
        input_name=args.input_name,
        input_number=args.input_number,
        year_class=args.year_class,
    )
    if not seeds:
        raise SystemExit("No seed populations found for provided batch key")

    adjacency = build_lineage_adjacency(sub_transfers)
    lineage = traverse_lineage(
        seeds,
        adjacency,
        args.lineage_max_depth,
    )

    rows = build_transition_rows(
        sub_transfers,
        lineage,
        pop_to_container,
        container_info,
        container_name,
        stage_map,
        args.station_site,
    )

    rows.sort(
        key=lambda row: (
            row["operation_time"],
            row["operation_id"],
            row["source_container"],
            row["target_container"],
        )
    )

    site_counts = Counter()
    stage_counts = Counter()
    for pop_id in lineage:
        container_id = pop_to_container.get(pop_id, "")
        info = container_info.get(container_id) or {}
        site_counts[normalize(info.get("Site"))] += 1
        stage_counts[
            stage_for_population(
                pop_id,
                pop_to_container,
                container_info,
                stage_map,
            )
        ] += 1

    windows = stage_windows(rows)
    summary = {
        "batch_key": {
            "input_name": args.input_name,
            "input_number": args.input_number,
            "year_class": args.year_class,
        },
        "seed_population_count": len(seeds),
        "lineage_population_count": len(lineage),
        "lineage_site_counts": dict(site_counts),
        "lineage_stage_counts": dict(stage_counts),
        "station_site_filter": normalize(args.station_site),
        "stage_transition_pair_windows": windows,
        "edge_csv": str(Path(args.output_csv)),
    }

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output_csv, rows)

    summary_json = Path(args.summary_json)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Cohort SubTransfers Deterministic Transition Evidence")
    lines.append("")
    lines.append("## Batch key")
    lines.append("")
    lines.append(f"- InputName: `{args.input_name}`")
    lines.append(f"- InputNumber: `{args.input_number}`")
    lines.append(f"- YearClass: `{args.year_class}`")
    if normalize(args.station_site):
        lines.append(f"- Site filter: `{normalize(args.station_site)}`")
    lines.append("")
    lines.append("## Lineage reconstruction")
    lines.append("")
    lines.append(f"- Seed populations: `{len(seeds)}`")
    lines.append(f"- Lineage populations: `{len(lineage)}`")
    lines.append(f"- Site counts: `{dict(site_counts)}`")
    lines.append(f"- Stage counts: `{dict(stage_counts)}`")
    lines.append("")
    lines.append("## Transition windows (SB->DA)")
    lines.append("")
    for key, payload in windows.items():
        lines.append(
            f"- `{key}`: count `{payload['count']}`, "
            f"window `{payload['min_time']}` -> `{payload['max_time']}`"
        )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- Edge CSV: `{output_csv}`")
    lines.append(f"- Summary JSON: `{summary_json}`")
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {output_csv}")
    print(f"Wrote {summary_json}")
    print(f"Wrote {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
