#!/usr/bin/env python3
"""Generate a FishTalk population stitching report.

FishTalk PopulationID changes on (at least) FW→sea transfers. This tool builds a
transfer graph from dbo.PublicTransfers (+ dbo.Operations timestamps) and
produces CSVs that help identify "logical batch" chains.
"""

from __future__ import annotations

import argparse
import csv
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_float(value: str) -> float | None:
    if value == "" or value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def add(self, x: str) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0

    def find(self, x: str) -> str:
        self.add(x)
        parent = self._parent[x]
        if parent != x:
            self._parent[x] = self.find(parent)
        return self._parent[x]

    def union(self, a: str, b: str) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        rank_a = self._rank[ra]
        rank_b = self._rank[rb]
        if rank_a < rank_b:
            self._parent[ra] = rb
        elif rank_a > rank_b:
            self._parent[rb] = ra
        else:
            self._parent[rb] = ra
            self._rank[ra] = rank_a + 1


SEA_STAGE_MARKERS = ("ONGROW", "GROWER", "GRILSE")
FRESHWATER_STAGE_MARKERS = (
    "EGG",
    "ALEVIN",
    "SAC",
    "FRY",
    "PARR",
    "SMOLT",
)


def stage_bucket(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(marker in upper for marker in SEA_STAGE_MARKERS):
        return "sea"
    if any(marker in upper for marker in FRESHWATER_STAGE_MARKERS):
        return "freshwater"
    return None


@dataclass(frozen=True)
class PopulationInfo:
    population_id: str
    container_id: str
    name: str
    start_time: datetime | None
    end_time: datetime | None


def load_manual_links(path: Path) -> list[tuple[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Manual links CSV {path} has no headers")
        normalized = {name.lower(): name for name in reader.fieldnames}
        from_key = normalized.get("from_population_id") or normalized.get("source_population_id")
        to_key = normalized.get("to_population_id") or normalized.get("dest_population_id")
        if not from_key or not to_key:
            raise ValueError(
                "Manual links CSV must have headers 'from_population_id' and 'to_population_id' "
                "(or 'source_population_id'/'dest_population_id')."
            )
        links: list[tuple[str, str]] = []
        for row in reader:
            src = (row.get(from_key) or "").strip()
            dst = (row.get(to_key) or "").strip()
            if src and dst:
                links.append((src, dst))
        return links


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FishTalk population stitching report")
    parser.add_argument("--profile", default="fishtalk_readonly", help="migration_config.json sqlserver profile")
    parser.add_argument("--since", help="Only include transfers with Operations.StartTime >= YYYY-MM-DD")
    parser.add_argument("--strong-threshold", type=float, default=0.8, help="Share threshold for auto-linking")
    parser.add_argument("--manual-links", help="CSV with from_population_id,to_population_id to union into groups")
    parser.add_argument(
        "--output-dir",
        default=str((PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching").as_posix()),
        help="Directory to write CSV outputs",
    )
    parser.add_argument("--print-top", type=int, default=20, help="Print top N stitch candidates to stdout")
    return parser


def stage_at(events: list[tuple[datetime, str]], when: datetime) -> str:
    if not events:
        return ""
    idx = bisect_right(events, (when, "\uffff")) - 1
    if idx < 0:
        return ""
    return events[idx][1]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in fieldnames})


def main() -> int:
    args = build_parser().parse_args()

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    extractor = BaseExtractor(ExtractionContext(profile=args.profile))

    ops_filter = ""
    if args.since:
        ops_filter = f"WHERE o.StartTime >= '{args.since}'"

    transfers = extractor._run_sqlcmd(
        query=(
            "SELECT pt.OperationID, o.StartTime, pt.SourcePop, pt.DestPop, "
            "pt.ShareCountForward, pt.ShareBiomassForward "
            "FROM dbo.PublicTransfers pt "
            "JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"{ops_filter}"
        ),
        headers=[
            "OperationID",
            "OperationStartTime",
            "SourcePop",
            "DestPop",
            "ShareCountForward",
            "ShareBiomassForward",
        ],
    )

    population_infos_raw = extractor._run_sqlcmd(
        query=(
            "SELECT DISTINCT p.PopulationID, p.ContainerID, p.PopulationName, p.StartTime, p.EndTime "
            "FROM dbo.Populations p "
            "JOIN ("
            "  SELECT pt.SourcePop AS PopulationID "
            "  FROM dbo.PublicTransfers pt JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"  {ops_filter} "
            "  UNION "
            "  SELECT pt.DestPop AS PopulationID "
            "  FROM dbo.PublicTransfers pt JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"  {ops_filter} "
            ") ids ON ids.PopulationID = p.PopulationID"
        ),
        headers=["PopulationID", "ContainerID", "PopulationName", "StartTime", "EndTime"],
    )

    pop_info: dict[str, PopulationInfo] = {}
    for row in population_infos_raw:
        pop_info[row["PopulationID"]] = PopulationInfo(
            population_id=row["PopulationID"],
            container_id=row.get("ContainerID", ""),
            name=row.get("PopulationName", ""),
            start_time=parse_dt(row.get("StartTime", "")),
            end_time=parse_dt(row.get("EndTime", "")),
        )

    stages_raw = extractor._run_sqlcmd(
        query="SELECT StageID, StageName FROM dbo.ProductionStages",
        headers=["StageID", "StageName"],
    )
    stage_name_by_id = {row["StageID"]: row.get("StageName", "") for row in stages_raw}

    stage_events_raw = extractor._run_sqlcmd(
        query=(
            "SELECT pps.PopulationID, pps.StageID, pps.StartTime "
            "FROM dbo.PopulationProductionStages pps "
            "JOIN ("
            "  SELECT pt.SourcePop AS PopulationID "
            "  FROM dbo.PublicTransfers pt JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"  {ops_filter} "
            "  UNION "
            "  SELECT pt.DestPop AS PopulationID "
            "  FROM dbo.PublicTransfers pt JOIN dbo.Operations o ON o.OperationID = pt.OperationID "
            f"  {ops_filter} "
            ") ids ON ids.PopulationID = pps.PopulationID"
        ),
        headers=["PopulationID", "StageID", "StartTime"],
    )

    stage_events: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for row in stage_events_raw:
        ts = parse_dt(row.get("StartTime", ""))
        if ts is None:
            continue
        stage_name = stage_name_by_id.get(row.get("StageID", ""), "")
        stage_events[row["PopulationID"]].append((ts, stage_name))
    for pop_id, events in stage_events.items():
        events.sort(key=lambda item: item[0])

    uf = UnionFind()

    strong_threshold = float(args.strong_threshold)
    strong_edges: list[dict[str, object]] = []
    weak_cross_stage: list[dict[str, object]] = []

    for row in transfers:
        src = row.get("SourcePop", "")
        dst = row.get("DestPop", "")
        if not src or not dst or src == dst:
            continue
        share_count = parse_float(row.get("ShareCountForward", "")) or 0.0
        share_biomass = parse_float(row.get("ShareBiomassForward", "")) or 0.0
        share = max(share_count, share_biomass)

        op_time = parse_dt(row.get("OperationStartTime", ""))
        src_stage = stage_at(stage_events.get(src, []), op_time) if op_time else ""
        dst_stage = stage_at(stage_events.get(dst, []), op_time) if op_time else ""

        edge = {
            "operation_id": row.get("OperationID", ""),
            "operation_start_time": row.get("OperationStartTime", ""),
            "source_population_id": src,
            "source_name": pop_info.get(src, PopulationInfo(src, "", "", None, None)).name,
            "source_stage": src_stage,
            "dest_population_id": dst,
            "dest_name": pop_info.get(dst, PopulationInfo(dst, "", "", None, None)).name,
            "dest_stage": dst_stage,
            "share_count_forward": share_count,
            "share_biomass_forward": share_biomass,
        }

        if share >= strong_threshold:
            uf.union(src, dst)
            strong_edges.append(edge)
        else:
            if stage_bucket(src_stage) == "freshwater" and stage_bucket(dst_stage) == "sea":
                weak_cross_stage.append(edge)

    if args.manual_links:
        manual = load_manual_links(Path(args.manual_links))
        for src, dst in manual:
            uf.union(src, dst)

    # Assign deterministic component ids.
    #
    # Union-Find root IDs depend on union order. To make component ids stable
    # across runs, we derive a deterministic component_key = min(population_id)
    # per component, sort by that, and then enumerate.
    members_by_root: dict[str, list[str]] = defaultdict(list)
    for pop_id in pop_info.keys():
        members_by_root[uf.find(pop_id)].append(pop_id)

    components_sorted: list[list[str]] = sorted(members_by_root.values(), key=lambda ids: min(ids))
    component_by_pop: dict[str, int] = {}
    component_key_by_id: dict[int, str] = {}
    pops_by_component: dict[int, list[str]] = defaultdict(list)
    for comp_id, pop_ids in enumerate(components_sorted, start=1):
        component_key_by_id[comp_id] = min(pop_ids)
        for pop_id in pop_ids:
            component_by_pop[pop_id] = comp_id
            pops_by_component[comp_id].append(pop_id)

    # Membership export (useful for picking pilot chains)
    population_rows: list[dict[str, object]] = []
    for pop_id, info in pop_info.items():
        events = stage_events.get(pop_id, [])
        first_stage = events[0][1] if events else ""
        last_stage = events[-1][1] if events else ""
        comp_id = component_by_pop.get(pop_id, "")
        population_rows.append(
            {
                "component_id": comp_id,
                "component_key": component_key_by_id.get(comp_id, "") if isinstance(comp_id, int) else "",
                "population_id": pop_id,
                "population_name": info.name,
                "container_id": info.container_id,
                "start_time": info.start_time.isoformat(sep=" ") if info.start_time else "",
                "end_time": info.end_time.isoformat(sep=" ") if info.end_time else "",
                "first_stage": first_stage,
                "last_stage": last_stage,
            }
        )

    write_csv(
        output_dir / "population_members.csv",
        fieldnames=[
            "component_id",
            "component_key",
            "population_id",
            "population_name",
            "container_id",
            "start_time",
            "end_time",
            "first_stage",
            "last_stage",
        ],
        rows=population_rows,
    )

    components_rows: list[dict[str, object]] = []
    for comp_id, pop_ids in sorted(pops_by_component.items(), key=lambda item: item[0]):
        infos = [pop_info[p] for p in pop_ids if p in pop_info]
        starts = [i.start_time for i in infos if i.start_time]
        ends = [i.end_time for i in infos if i.end_time]
        earliest = min(starts) if starts else None
        latest = max(ends) if ends else (max(starts) if starts else None)

        names = [i.name for i in infos if i.name]
        transportpop_count = sum(1 for name in names if "TRANSPORTPOP" in name.upper())
        representative_id = ""
        representative_name = ""
        for info in sorted(infos, key=lambda i: i.start_time or datetime.min):
            if "TRANSPORTPOP" in (info.name or "").upper():
                continue
            representative_id = info.population_id
            representative_name = info.name
            break
        if not representative_name and infos:
            representative_id = infos[0].population_id
            representative_name = infos[0].name

        buckets: Counter[str] = Counter()
        for pop_id in pop_ids:
            for _, stage_name in stage_events.get(pop_id, []):
                bucket = stage_bucket(stage_name)
                if bucket:
                    buckets[bucket] += 1

        components_rows.append(
            {
                "component_id": comp_id,
                "component_key": component_key_by_id.get(comp_id, ""),
                "population_count": len(pop_ids),
                "earliest_start_time": earliest.isoformat(sep=" ") if earliest else "",
                "latest_end_time": latest.isoformat(sep=" ") if latest else "",
                "representative_population_id": representative_id,
                "representative_name": representative_name,
                "contains_freshwater_stages": buckets.get("freshwater", 0) > 0,
                "contains_sea_stages": buckets.get("sea", 0) > 0,
                "transportpop_population_count": transportpop_count,
            }
        )

    write_csv(
        output_dir / "components.csv",
        fieldnames=[
            "component_id",
            "component_key",
            "population_count",
            "earliest_start_time",
            "latest_end_time",
            "representative_population_id",
            "representative_name",
            "contains_freshwater_stages",
            "contains_sea_stages",
            "transportpop_population_count",
        ],
        rows=components_rows,
    )

    # Strong edge report
    for edge in strong_edges:
        edge["component_id"] = component_by_pop.get(edge["source_population_id"], "")
        comp_id = edge["component_id"]
        edge["component_key"] = component_key_by_id.get(comp_id, "") if isinstance(comp_id, int) else ""

    write_csv(
        output_dir / "strong_links.csv",
        fieldnames=[
            "operation_id",
            "operation_start_time",
            "component_id",
            "component_key",
            "source_population_id",
            "source_name",
            "source_stage",
            "dest_population_id",
            "dest_name",
            "dest_stage",
            "share_count_forward",
            "share_biomass_forward",
        ],
        rows=strong_edges,
    )

    # Manual review candidates: FW→sea links below threshold.
    weak_cross_stage.sort(key=lambda r: (r.get("share_biomass_forward", 0.0) or 0.0), reverse=True)
    write_csv(
        output_dir / "manual_review_candidates.csv",
        fieldnames=[
            "operation_id",
            "operation_start_time",
            "source_population_id",
            "source_name",
            "source_stage",
            "dest_population_id",
            "dest_name",
            "dest_stage",
            "share_count_forward",
            "share_biomass_forward",
        ],
        rows=weak_cross_stage,
    )

    # Print quick summary + top stitch candidates
    print("Population stitching report")
    print(f"Transfers loaded: {len(transfers):,}")
    print(f"Populations referenced: {len(pop_info):,}")
    print(f"Strong edges (>= {strong_threshold}): {len(strong_edges):,}")
    print(f"Components (strong edges): {len(pops_by_component):,}")
    print(f"Outputs written to: {output_dir.resolve()}")

    top_n = int(args.print_top)
    top_strong_cross: list[dict[str, object]] = []
    for edge in strong_edges:
        if stage_bucket(edge.get("source_stage", "")) == "freshwater" and stage_bucket(edge.get("dest_stage", "")) == "sea":
            top_strong_cross.append(edge)
    top_strong_cross.sort(key=lambda r: (r.get("operation_start_time", "")), reverse=True)
    if top_strong_cross:
        print("\nTop strong FW→sea stitch edges:")
        for edge in top_strong_cross[:top_n]:
            print(
                f"  {edge['operation_start_time']} | {edge['source_name']} ({edge['source_stage']}) -> "
                f"{edge['dest_name']} ({edge['dest_stage']}) | share_biom={edge['share_biomass_forward']}"
            )
    else:
        print("\nNo strong FW→sea stitch edges detected (try lowering --strong-threshold or widening --since).")

    if weak_cross_stage:
        print("\nTop manual-review FW→sea candidates (below threshold):")
        for edge in weak_cross_stage[:top_n]:
            print(
                f"  {edge['operation_start_time']} | {edge['source_name']} ({edge['source_stage']}) -> "
                f"{edge['dest_name']} ({edge['dest_stage']}) | share_biom={edge['share_biomass_forward']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
