#!/usr/bin/env python3
"""Trace upstream transfer edges from sea populations using Ext_Transfers_v2."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtrace sea transfers using Ext_Transfers_v2")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--sea-sites", required=True, help="Comma-separated sea site names")
    parser.add_argument("--name-regex", help="Regex to filter sea population names")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    sea_sites = {s.strip() for s in args.sea_sites.split(",") if s.strip()}
    name_re = re.compile(args.name_regex, re.IGNORECASE) if args.name_regex else None

    ext_transfers = load_csv(input_dir / "ext_transfers.csv")
    ext_pop = load_csv(input_dir / "ext_populations.csv")
    containers = load_csv(input_dir / "containers.csv")
    grouped = load_csv(input_dir / "grouped_organisation.csv")

    container_site = {row["ContainerID"]: row.get("Site", "") for row in grouped if row.get("ContainerID")}
    container_prod = {row["ContainerID"]: row.get("ProdStage", "") for row in grouped if row.get("ContainerID")}
    pop_container = {row["PopulationID"]: row.get("ContainerID", "") for row in ext_pop if row.get("PopulationID")}
    pop_name = {row["PopulationID"]: row.get("PopulationName", "") for row in ext_pop if row.get("PopulationID")}
    pop_site = {pid: container_site.get(cid, "") for pid, cid in pop_container.items()}
    pop_prod = {pid: container_prod.get(cid, "") for pid, cid in pop_container.items()}

    # Sea population selection
    sea_pop_ids = []
    for pid, site in pop_site.items():
        if site not in sea_sites:
            continue
        if name_re and not name_re.search(pop_name.get(pid, "") or ""):
            continue
        sea_pop_ids.append(pid)

    sea_pop_set = set(sea_pop_ids)

    # Build reverse adjacency: dest -> sources
    rev = defaultdict(list)
    for row in ext_transfers:
        dest = (row.get("DestPop") or "").strip()
        src = (row.get("SourcePop") or "").strip()
        if dest and src:
            rev[dest].append(src)

    # BFS upstream
    edges = []
    visited = set(sea_pop_set)
    frontier = list(sea_pop_set)
    for depth in range(1, args.max_depth + 1):
        next_frontier = []
        for dest in frontier:
            for src in rev.get(dest, []):
                edges.append((depth, src, dest))
                if src not in visited:
                    visited.add(src)
                    next_frontier.append(src)
        frontier = next_frontier
        if not frontier:
            break

    # Summaries
    direct_edges = [e for e in edges if e[0] == 1]
    direct_sources = {src for _, src, _ in direct_edges}
    direct_source_sites = Counter(pop_site.get(src, "") or "(unknown)" for src in direct_sources)
    direct_source_prods = Counter(pop_prod.get(src, "") or "(unknown)" for src in direct_sources)

    upstream_sites = Counter(pop_site.get(pid, "") or "(unknown)" for pid in visited)
    upstream_prods = Counter(pop_prod.get(pid, "") or "(unknown)" for pid in visited)

    # Output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write("# Sea Transfer Backtrace (Ext_Transfers_v2)\n\n")
        handle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        handle.write("## Scope\n")
        handle.write(f"- Sea sites: {', '.join(sorted(sea_sites))}\n")
        handle.write(f"- Name regex: `{args.name_regex or 'None'}`\n")
        handle.write(f"- Max depth: {args.max_depth}\n\n")

        handle.write("## Sea population selection\n")
        handle.write(f"- Sea populations matched: {len(sea_pop_set)}\n\n")

        handle.write("## Direct upstream edges (depth=1)\n")
        handle.write(f"- Direct edges found: {len(direct_edges)}\n")
        handle.write(f"- Distinct direct source populations: {len(direct_sources)}\n\n")

        handle.write("### Direct source sites\n")
        for site, count in direct_source_sites.most_common():
            handle.write(f"- {site}: {count}\n")
        handle.write("\n")

        handle.write("### Direct source prod stages\n")
        for stage, count in direct_source_prods.most_common():
            handle.write(f"- {stage}: {count}\n")
        handle.write("\n")

        handle.write("## Upstream population footprint (all depths)\n")
        handle.write(f"- Unique upstream populations (incl. sea): {len(visited)}\n\n")
        handle.write("### Upstream sites\n")
        for site, count in upstream_sites.most_common():
            handle.write(f"- {site}: {count}\n")
        handle.write("\n")

        handle.write("### Upstream prod stages\n")
        for stage, count in upstream_prods.most_common():
            handle.write(f"- {stage}: {count}\n")
        handle.write("\n")

        handle.write("## Direct edge details (first 50)\n")
        handle.write("| Depth | SourcePop | SourceSite | SourceStage | SourceName | DestPop | DestSite | DestStage | DestName |\n")
        handle.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for depth, src, dest in edges[:50]:
            handle.write(
                f"| {depth} | {src} | {pop_site.get(src, '')} | {pop_prod.get(src, '')} | {pop_name.get(src, '')} | {dest} | {pop_site.get(dest, '')} | {pop_prod.get(dest, '')} | {pop_name.get(dest, '')} |\n"
            )


if __name__ == "__main__":
    raise SystemExit(main())
