#!/usr/bin/env python3
"""Analyze InternalDelivery -> Operations -> Actions -> Populations linkages."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


BASE_DIR = Path("/Users/aquarian247/Projects/AquaMind")
DEFAULT_INPUT_DIR = BASE_DIR / "scripts/migration/data/extract"


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle))


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="InternalDelivery linkage report")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output", required=True)
    parser.add_argument("--input-site", help="Site name (e.g., S16 Glyvradalur)")
    parser.add_argument("--input-project-id", help="InputProjectID to check")
    parser.add_argument("--input-project-name", help="InputProjectName for display")
    parser.add_argument("--sea-name-pattern", default=r"S16 .*\(AUG 24\)", help="Regex to match sea population names")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    internal = load_csv(input_dir / "internal_delivery.csv")
    operations = load_csv(input_dir / "internal_delivery_operations.csv")
    actions = load_csv(input_dir / "internal_delivery_actions.csv")
    ext_pop = load_csv(input_dir / "ext_populations.csv")
    containers = load_csv(input_dir / "containers.csv")
    grouped = load_csv(input_dir / "grouped_organisation.csv")
    org_units = load_csv(input_dir / "org_units.csv")
    fish_group_history = load_csv(input_dir / "fish_group_history.csv")

    # Lookups
    site_name_by_id = {row["OrgUnitID"]: row["Name"] for row in org_units if row.get("OrgUnitID")}
    container_name = {row["ContainerID"]: row.get("ContainerName", "") for row in containers}
    container_site = {row["ContainerID"]: row.get("Site", "") for row in grouped}

    pop_name = {row["PopulationID"]: row.get("PopulationName", "") for row in ext_pop}
    pop_container = {row["PopulationID"]: row.get("ContainerID", "") for row in ext_pop}
    pop_site = {pid: container_site.get(cid, "") for pid, cid in pop_container.items()}

    # Filter internal delivery by site if requested
    for row in internal:
        row["InputSiteName"] = site_name_by_id.get(row.get("InputSiteID", ""), "")

    internal_scoped = [row for row in internal if (not args.input_site or row.get("InputSiteName") == args.input_site)]

    # Operations lookup
    op_info = {row["OperationID"]: row for row in operations if row.get("OperationID")}

    sales_ops = [row.get("SalesOperationID") for row in internal_scoped if row.get("SalesOperationID")]
    sales_ops_set = set(sales_ops)

    actions_scoped = [row for row in actions if row.get("OperationID") in sales_ops_set]

    # Populations in actions
    action_pop_ids = [row.get("PopulationID") for row in actions_scoped if row.get("PopulationID")]
    action_pop_set = set(action_pop_ids)

    # Match to input project populations
    project_pop_set = set()
    if args.input_project_id:
        project_pop_set = {row["PopulationID"] for row in fish_group_history if row.get("InputProjectID") == args.input_project_id}

    project_action_overlap = project_pop_set & action_pop_set if project_pop_set else set()

    # Sea name pattern matching
    sea_regex = re.compile(args.sea_name_pattern, re.IGNORECASE)
    sea_pop_ids = {pid for pid, name in pop_name.items() if name and sea_regex.search(name)}
    sea_action_overlap = sea_pop_ids & action_pop_set if sea_pop_ids else set()

    # Aggregations
    site_counts = Counter(pop_site.get(pid, "") or "(unknown)" for pid in action_pop_set)
    name_counts = Counter(pop_name.get(pid, "") or "" for pid in action_pop_set)

    # Per operation summary
    op_summary = []
    for op_id in sales_ops_set:
        op_actions = [row for row in actions_scoped if row.get("OperationID") == op_id]
        pop_ids = {row.get("PopulationID") for row in op_actions if row.get("PopulationID")}
        sites = sorted({pop_site.get(pid, "") for pid in pop_ids if pop_site.get(pid, "")})
        op = op_info.get(op_id, {})
        op_summary.append({
            "operation_id": op_id,
            "start_time": op.get("StartTime", ""),
            "operation_type": op.get("OperationType", ""),
            "action_count": len(op_actions),
            "population_count": len(pop_ids),
            "sites": ", ".join(sites),
        })

    op_summary.sort(key=lambda row: row.get("start_time") or "")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("# InternalDelivery Linkage Scan\n\n")
        handle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        handle.write("## Scope\n")
        handle.write(f"- Input site filter: {args.input_site or 'None'}\n")
        handle.write(f"- InputProjectID: {args.input_project_id or 'None'}\n")
        if args.input_project_name:
            handle.write(f"- InputProjectName: {args.input_project_name}\n")
        handle.write(f"- Sea name regex: `{args.sea_name_pattern}`\n\n")

        handle.write("## InternalDelivery Summary\n")
        handle.write(f"- Total InternalDelivery rows: {len(internal)}\n")
        handle.write(f"- Scoped InternalDelivery rows: {len(internal_scoped)}\n")
        handle.write(f"- SalesOperationIDs in scope: {len(sales_ops_set)}\n")
        handle.write(f"- Actions linked to SalesOperationIDs: {len(actions_scoped)}\n")
        handle.write(f"- Distinct action populations: {len(action_pop_set)}\n\n")

        handle.write("## InputOperationID Coverage\n")
        null_input_ops = sum(1 for row in internal_scoped if not row.get("InputOperationID"))
        handle.write(f"- Null InputOperationID rows: {null_input_ops} of {len(internal_scoped)}\n\n")

        handle.write("## Action Population Site Distribution (scoped)\n")
        for site, count in site_counts.most_common():
            if not site:
                site = "(unknown)"
            handle.write(f"- {site}: {count}\n")
        handle.write("\n")

        handle.write("## Action Population Names (top 10)\n")
        for name, count in name_counts.most_common(10):
            display = name or "(blank)"
            handle.write(f"- {display}: {count}\n")
        handle.write("\n")

        if args.input_project_id:
            handle.write("## Fish Group Overlap\n")
            handle.write(f"- FishGroupHistory populations: {len(project_pop_set)}\n")
            handle.write(f"- Overlap with InternalDelivery actions: {len(project_action_overlap)}\n")
            handle.write("\n")

        if sea_pop_ids:
            handle.write("## Sea Population Name Match\n")
            handle.write(f"- Populations matching regex: {len(sea_pop_ids)}\n")
            handle.write(f"- Overlap with InternalDelivery actions: {len(sea_action_overlap)}\n")
            if sea_action_overlap:
                handle.write("- Matching populations:\n")
                for pid in sorted(sea_action_overlap):
                    handle.write(f"  - {pop_name.get(pid, pid)} ({pop_site.get(pid, '')})\n")
            handle.write("\n")

        handle.write("## SalesOperation Summary (scoped)\n")
        handle.write("| OperationID | StartTime | OperationType | Actions | Populations | Sites |\n")
        handle.write("| --- | --- | --- | --- | --- | --- |\n")
        for row in op_summary:
            handle.write(
                f"| {row['operation_id']} | {row['start_time']} | {row['operation_type']} | {row['action_count']} | {row['population_count']} | {row['sites']} |\n"
            )


if __name__ == "__main__":
    raise SystemExit(main())
