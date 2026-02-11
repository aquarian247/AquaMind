#!/usr/bin/env python3
"""Build deterministic FW->Sea linkage evidence for a stitched component.

This script intentionally avoids heuristics. It uses:
- stitched component population IDs (`population_members.csv`),
- SubTransfers graph edges (`sub_transfers.csv`),
- explicit destination context fields from grouped organisation
  (`Site`, `SiteGroup`, `ProdStage`).

Evidence is considered "marine" only when destination `ProdStage`
explicitly contains "Marine" (case-insensitive).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def normalize(value: str | None) -> str:
    return (value or "").strip()


def load_component_members(
    *,
    report_dir: Path,
    component_key: str | None,
    component_id: str | None,
) -> tuple[str, str | None, set[str]]:
    members_path = report_dir / "population_members.csv"
    if not members_path.exists():
        raise FileNotFoundError(f"Missing report file: {members_path}")

    rows: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    with members_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
            key = normalize(row.get("component_key"))
            cid = normalize(row.get("component_id"))
            if key:
                seen_keys.add(key)
            if cid:
                seen_ids.add(cid)

    selected_key = normalize(component_key)
    selected_id = normalize(component_id)

    if not selected_key and not selected_id:
        if len(seen_keys) == 1:
            selected_key = next(iter(seen_keys))
        elif len(seen_ids) == 1:
            selected_id = next(iter(seen_ids))
        else:
            raise ValueError(
                "Provide --component-key or --component-id when report contains multiple components."
            )

    population_ids: set[str] = set()
    resolved_key = selected_key
    resolved_id = selected_id or None
    for row in rows:
        row_key = normalize(row.get("component_key"))
        row_id = normalize(row.get("component_id"))
        if selected_key and row_key != selected_key:
            continue
        if selected_id and row_id != selected_id:
            continue
        population_id = normalize(row.get("population_id"))
        if population_id:
            population_ids.add(population_id)
        if not resolved_key and row_key:
            resolved_key = row_key
        if not resolved_id and row_id:
            resolved_id = row_id

    if not population_ids:
        raise ValueError(
            f"No component members found for component_key={selected_key!r} component_id={selected_id!r}."
        )

    return resolved_key, resolved_id, population_ids


def load_subtransfers_for_component(csv_dir: Path, component_population_ids: set[str]) -> list[dict[str, str]]:
    path = csv_dir / "sub_transfers.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV extract file: {path}")

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            src_before = normalize(row.get("SourcePopBefore"))
            src_after = normalize(row.get("SourcePopAfter"))
            dst_before = normalize(row.get("DestPopBefore"))
            dst_after = normalize(row.get("DestPopAfter"))
            if (
                src_before in component_population_ids
                or src_after in component_population_ids
                or dst_before in component_population_ids
                or dst_after in component_population_ids
            ):
                rows.append(row)
    return rows


def build_external_edges(
    *,
    component_population_ids: set[str],
    subtransfer_rows: list[dict[str, str]],
) -> tuple[
    dict[str, set[str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[dict[str, str]],
    set[str],
]:
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    source_to_dest_external: list[tuple[str, str]] = []
    source_chain_external: list[tuple[str, str]] = []
    dest_chain_external: list[tuple[str, str]] = []
    direct_edge_rows: list[dict[str, str]] = []
    direct_external_population_ids: set[str] = set()

    for row in subtransfer_rows:
        src_before = normalize(row.get("SourcePopBefore"))
        src_after = normalize(row.get("SourcePopAfter"))
        dst_before = normalize(row.get("DestPopBefore"))
        dst_after = normalize(row.get("DestPopAfter"))

        if src_before:
            if src_after:
                adjacency[src_before].add(src_after)
            if dst_after:
                adjacency[src_before].add(dst_after)
        if dst_before and dst_after:
            adjacency[dst_before].add(dst_after)

        if src_before and dst_after and src_before in component_population_ids and dst_after not in component_population_ids:
            source_to_dest_external.append((src_before, dst_after))
            direct_external_population_ids.add(dst_after)
            direct_edge_rows.append(
                {
                    "role": "SourcePopBefore -> DestPopAfter",
                    "src_population_id": src_before,
                    "dst_population_id": dst_after,
                    "subtransfer_id": normalize(row.get("SubTransferID")),
                    "operation_id": normalize(row.get("OperationID")),
                    "operation_time": normalize(row.get("OperationTime")),
                }
            )

        if src_before and src_after and src_before in component_population_ids and src_after not in component_population_ids:
            source_chain_external.append((src_before, src_after))
            direct_external_population_ids.add(src_after)
            direct_edge_rows.append(
                {
                    "role": "SourcePopBefore -> SourcePopAfter",
                    "src_population_id": src_before,
                    "dst_population_id": src_after,
                    "subtransfer_id": normalize(row.get("SubTransferID")),
                    "operation_id": normalize(row.get("OperationID")),
                    "operation_time": normalize(row.get("OperationTime")),
                }
            )

        if dst_before and dst_after and dst_before in component_population_ids and dst_after not in component_population_ids:
            dest_chain_external.append((dst_before, dst_after))
            direct_external_population_ids.add(dst_after)
            direct_edge_rows.append(
                {
                    "role": "DestPopBefore -> DestPopAfter",
                    "src_population_id": dst_before,
                    "dst_population_id": dst_after,
                    "subtransfer_id": normalize(row.get("SubTransferID")),
                    "operation_id": normalize(row.get("OperationID")),
                    "operation_time": normalize(row.get("OperationTime")),
                }
            )

    return (
        adjacency,
        source_to_dest_external,
        source_chain_external,
        dest_chain_external,
        direct_edge_rows,
        direct_external_population_ids,
    )


def traverse_descendants(component_population_ids: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    reachable: set[str] = set(component_population_ids)
    queue: deque[str] = deque(component_population_ids)
    while queue:
        current = queue.popleft()
        for nxt in adjacency.get(current, set()):
            if not nxt or nxt in reachable:
                continue
            reachable.add(nxt)
            queue.append(nxt)
    return reachable - component_population_ids


def load_population_context(csv_dir: Path, population_ids: set[str]) -> dict[str, dict[str, str]]:
    if not population_ids:
        return {}

    populations_path = csv_dir / "populations.csv"
    grouped_path = csv_dir / "grouped_organisation.csv"
    if not populations_path.exists():
        raise FileNotFoundError(f"Missing CSV extract file: {populations_path}")
    if not grouped_path.exists():
        raise FileNotFoundError(f"Missing CSV extract file: {grouped_path}")

    pop_rows: dict[str, dict[str, str]] = {}
    container_ids: set[str] = set()
    with populations_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            population_id = normalize(row.get("PopulationID"))
            if population_id not in population_ids:
                continue
            container_id = normalize(row.get("ContainerID"))
            if container_id:
                container_ids.add(container_id)
            pop_rows[population_id] = {
                "population_name": normalize(row.get("PopulationName")) or "Unknown",
                "container_id": container_id or "Unknown",
            }

    grouped_by_container: dict[str, dict[str, str]] = {}
    with grouped_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = normalize(row.get("ContainerID"))
            if not container_id or container_id not in container_ids:
                continue
            if container_id in grouped_by_container:
                continue
            grouped_by_container[container_id] = row

    context: dict[str, dict[str, str]] = {}
    for population_id in population_ids:
        pop_meta = pop_rows.get(population_id) or {}
        container_id = normalize(pop_meta.get("container_id")) or "Unknown"
        grouped = grouped_by_container.get(container_id) or {}
        context[population_id] = {
            "population_name": normalize(pop_meta.get("population_name")) or "Unknown",
            "container_id": container_id,
            "site": normalize(grouped.get("Site")) or "Unknown",
            "site_group": normalize(grouped.get("SiteGroup")) or "Unknown",
            "prod_stage": normalize(grouped.get("ProdStage")) or "Unknown",
            "container_group": normalize(grouped.get("ContainerGroup")) or "Unknown",
            "company": normalize(grouped.get("Company")) or "Unknown",
        }
    return context


def summarize_context(context: dict[str, dict[str, str]], population_ids: set[str], max_examples: int) -> dict:
    by_prod_stage: Counter[str] = Counter()
    by_site: Counter[str] = Counter()
    by_site_group: Counter[str] = Counter()
    marine_ids: list[str] = []
    non_hatchery_ids: list[str] = []

    for population_id in sorted(population_ids):
        meta = context.get(population_id) or {}
        prod_stage = normalize(meta.get("prod_stage")) or "Unknown"
        site = normalize(meta.get("site")) or "Unknown"
        site_group = normalize(meta.get("site_group")) or "Unknown"

        by_prod_stage[prod_stage] += 1
        by_site[site] += 1
        by_site_group[site_group] += 1

        upper_stage = prod_stage.upper()
        if "MARINE" in upper_stage:
            marine_ids.append(population_id)
        if upper_stage not in {"", "UNKNOWN", "HATCHERY"}:
            non_hatchery_ids.append(population_id)

    return {
        "population_count": len(population_ids),
        "explicit_marine_population_count": len(marine_ids),
        "explicit_marine_population_examples": marine_ids[:max_examples],
        "explicit_non_hatchery_population_count": len(non_hatchery_ids),
        "explicit_non_hatchery_population_examples": non_hatchery_ids[:max_examples],
        "by_prod_stage": dict(sorted(by_prod_stage.items(), key=lambda item: (-item[1], item[0]))),
        "by_site": dict(sorted(by_site.items(), key=lambda item: (-item[1], item[0]))),
        "by_site_group": dict(sorted(by_site_group.items(), key=lambda item: (-item[1], item[0]))),
    }


def summarize_edge_context(edges: list[tuple[str, str]], context: dict[str, dict[str, str]]) -> dict:
    by_prod_stage: Counter[str] = Counter()
    by_site: Counter[str] = Counter()
    by_site_group: Counter[str] = Counter()
    dst_unique: set[str] = set()
    for _, dst_population_id in edges:
        dst_unique.add(dst_population_id)
        meta = context.get(dst_population_id) or {}
        by_prod_stage[normalize(meta.get("prod_stage")) or "Unknown"] += 1
        by_site[normalize(meta.get("site")) or "Unknown"] += 1
        by_site_group[normalize(meta.get("site_group")) or "Unknown"] += 1
    return {
        "edge_count": len(edges),
        "unique_destination_population_count": len(dst_unique),
        "by_prod_stage": dict(sorted(by_prod_stage.items(), key=lambda item: (-item[1], item[0]))),
        "by_site": dict(sorted(by_site.items(), key=lambda item: (-item[1], item[0]))),
        "by_site_group": dict(sorted(by_site_group.items(), key=lambda item: (-item[1], item[0]))),
    }


def format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counts.items())


def build_markdown_report(summary: dict) -> str:
    lines: list[str] = []
    lines.append("# Deterministic FW->Sea Evidence Report")
    lines.append("")
    lines.append(f"- Component key: `{summary.get('component_key')}`")
    lines.append(f"- Component id: `{summary.get('component_id') or 'n/a'}`")
    lines.append(f"- Component populations: {summary.get('component_population_count', 0)}")
    lines.append(f"- SubTransfers rows considered: {summary.get('subtransfer_rows_considered', 0)}")
    lines.append("")
    lines.append("## Deterministic Criteria")
    lines.append("")
    lines.append("- Marine linkage evidence is `YES` only if destination `ProdStage` explicitly contains `Marine`.")
    lines.append("- Heuristic name/date matching is not used in this report.")
    lines.append("")
    lines.append("## Topline")
    lines.append("")
    lines.append(f"- Direct external destination populations: {summary.get('direct_external_population_count', 0)}")
    lines.append(f"- Reachable outside descendants: {summary.get('outside_descendant_population_count', 0)}")
    lines.append(
        f"- Marine linkage evidence: {'YES' if summary.get('marine_linkage_evidence') else 'NO'}"
    )
    lines.append("")
    lines.append("| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites | Destination site groups |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for label, payload in (
        ("SourcePopBefore -> DestPopAfter", summary.get("source_to_dest_external") or {}),
        ("SourcePopBefore -> SourcePopAfter", summary.get("source_chain_external") or {}),
        ("DestPopBefore -> DestPopAfter", summary.get("dest_chain_external") or {}),
    ):
        lines.append(
            f"| {label} | {payload.get('edge_count', 0)} | "
            f"{format_counts(payload.get('by_prod_stage') or {})} | "
            f"{format_counts(payload.get('by_site') or {})} | "
            f"{format_counts(payload.get('by_site_group') or {})} |"
        )

    lines.append("")
    lines.append("| Destination set | Populations | Explicit marine populations | Explicit non-hatchery populations | By prod stage | By site | By site group |")
    lines.append("| --- | ---: | ---: | ---: | --- | --- | --- |")
    for label, payload in (
        ("Direct external populations", summary.get("direct_population_summary") or {}),
        ("Reachable outside descendants", summary.get("descendant_summary") or {}),
    ):
        lines.append(
            f"| {label} | {payload.get('population_count', 0)} | "
            f"{payload.get('explicit_marine_population_count', 0)} | "
            f"{payload.get('explicit_non_hatchery_population_count', 0)} | "
            f"{format_counts(payload.get('by_prod_stage') or {})} | "
            f"{format_counts(payload.get('by_site') or {})} | "
            f"{format_counts(payload.get('by_site_group') or {})} |"
        )

    example_rows = summary.get("direct_external_edge_examples") or []
    if example_rows:
        lines.append("")
        lines.append("## Direct External Edge Examples")
        lines.append("")
        lines.append("| Role | Src population | Dst population | Dst site | Dst prod stage | Operation time |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in example_rows:
            lines.append(
                f"| {row.get('role') or '-'} | {row.get('src_population_id') or '-'} | "
                f"{row.get('dst_population_id') or '-'} | {row.get('dst_site') or '-'} | "
                f"{row.get('dst_prod_stage') or '-'} | {row.get('operation_time') or '-'} |"
            )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic FW->Sea evidence from SubTransfers + grouped organisation context"
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        help="Directory containing population_members.csv for the stitched component",
    )
    parser.add_argument("--component-key", help="Optional component key filter")
    parser.add_argument("--component-id", help="Optional component id filter")
    parser.add_argument(
        "--csv-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"),
        help="CSV extract directory",
    )
    parser.add_argument("--output-md", help="Optional output markdown path")
    parser.add_argument("--output-json", help="Optional output JSON path")
    parser.add_argument("--max-example-populations", type=int, default=10)
    parser.add_argument("--max-example-edges", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_dir = Path(args.report_dir)
    csv_dir = Path(args.csv_dir)

    component_key, component_id, component_population_ids = load_component_members(
        report_dir=report_dir,
        component_key=args.component_key,
        component_id=args.component_id,
    )
    subtransfer_rows = load_subtransfers_for_component(csv_dir, component_population_ids)
    (
        adjacency,
        source_to_dest_external,
        source_chain_external,
        dest_chain_external,
        direct_edge_rows,
        direct_external_population_ids,
    ) = build_external_edges(
        component_population_ids=component_population_ids,
        subtransfer_rows=subtransfer_rows,
    )

    outside_descendants = traverse_descendants(component_population_ids, adjacency)
    context_population_ids = direct_external_population_ids | outside_descendants
    context = load_population_context(csv_dir, context_population_ids)

    direct_population_summary = summarize_context(
        context,
        direct_external_population_ids,
        max_examples=max(args.max_example_populations, 0),
    )
    descendant_summary = summarize_context(
        context,
        outside_descendants,
        max_examples=max(args.max_example_populations, 0),
    )

    marine_linkage_evidence = (
        direct_population_summary.get("explicit_marine_population_count", 0) > 0
        or descendant_summary.get("explicit_marine_population_count", 0) > 0
    )

    direct_edge_examples: list[dict[str, str]] = []
    max_examples = max(args.max_example_edges, 0)
    for row in direct_edge_rows[:max_examples]:
        dst_population_id = row.get("dst_population_id") or ""
        dst_meta = context.get(dst_population_id) or {}
        direct_edge_examples.append(
            {
                **row,
                "dst_site": normalize(dst_meta.get("site")) or "Unknown",
                "dst_site_group": normalize(dst_meta.get("site_group")) or "Unknown",
                "dst_prod_stage": normalize(dst_meta.get("prod_stage")) or "Unknown",
            }
        )

    summary = {
        "component_key": component_key,
        "component_id": component_id,
        "component_population_count": len(component_population_ids),
        "subtransfer_rows_considered": len(subtransfer_rows),
        "direct_external_population_count": len(direct_external_population_ids),
        "outside_descendant_population_count": len(outside_descendants),
        "source_to_dest_external": summarize_edge_context(source_to_dest_external, context),
        "source_chain_external": summarize_edge_context(source_chain_external, context),
        "dest_chain_external": summarize_edge_context(dest_chain_external, context),
        "direct_population_summary": direct_population_summary,
        "descendant_summary": descendant_summary,
        "marine_linkage_evidence": marine_linkage_evidence,
        "direct_external_edge_examples": direct_edge_examples,
    }

    markdown_report = build_markdown_report(summary)

    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(markdown_report, encoding="utf-8")
        print(f"Wrote report to {output_md}")
    else:
        print(markdown_report)

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote summary JSON to {output_json}")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
