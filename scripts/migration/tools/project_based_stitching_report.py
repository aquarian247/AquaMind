#!/usr/bin/env python3
"""Generate a FishTalk population stitching report using project identifiers.

Unlike population_stitching_report.py which relies on PublicTransfers (broken since Jan 2023),
this script groups populations by (ProjectNumber, InputYear, RunningNumber) tuple to form
logical batches that span FW and sea stages.

This approach bypasses the missing FW→sea transfer records and creates unified components
based on FishTalk's own project grouping.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
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


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
    """Map FishTalk stage names to AquaMind lifecycle stages."""
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC", "GREEN", "EYE")):
        return "Egg&Alevin"
    if "FRY" in upper:
        return "Fry"
    if "PARR" in upper:
        return "Parr"
    if "SMOLT" in upper and ("POST" in upper or "LARGE" in upper):
        return "Post-Smolt"
    if "SMOLT" in upper:
        return "Smolt"
    if any(token in upper for token in ("ONGROW", "GROWER", "GRILSE")):
        return "Adult"
    if "BROODSTOCK" in upper:
        return "Adult"
    return None


def stage_bucket(stage_name: str) -> str | None:
    """Classify stage as freshwater or sea."""
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(marker in upper for marker in ("ONGROW", "GROWER", "GRILSE")):
        return "sea"
    if any(marker in upper for marker in ("EGG", "ALEVIN", "SAC", "FRY", "PARR", "SMOLT")):
        return "freshwater"
    return None


AQUAMIND_STAGES_ORDERED = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]


@dataclass
class PopulationInfo:
    population_id: str
    container_id: str
    name: str
    project_number: str
    input_year: str
    running_number: str
    start_time: datetime | None
    end_time: datetime | None
    stages: list[str] = field(default_factory=list)
    aquamind_stages: set[str] = field(default_factory=set)


@dataclass
class ProjectBatch:
    project_key: str  # "ProjectNumber/InputYear/RunningNumber"
    project_number: str
    input_year: str
    running_number: str
    populations: list[PopulationInfo] = field(default_factory=list)
    aquamind_stages: set[str] = field(default_factory=set)
    fishtalk_stages: set[str] = field(default_factory=set)
    earliest_start: datetime | None = None
    latest_end: datetime | None = None
    latest_activity: datetime | None = None

    @property
    def has_all_stages(self) -> bool:
        return len(self.aquamind_stages) == 6

    @property
    def has_fw_and_sea(self) -> bool:
        fw_stages = {"Egg&Alevin", "Fry", "Parr", "Smolt"}
        sea_stages = {"Post-Smolt", "Adult"}
        has_fw = bool(self.aquamind_stages & fw_stages)
        has_sea = bool(self.aquamind_stages & sea_stages)
        return has_fw and has_sea

    @property
    def stage_coverage_count(self) -> int:
        return len(self.aquamind_stages)

    @property
    def is_active(self) -> bool:
        """Consider active if latest activity is in 2024 or 2025."""
        if not self.latest_activity:
            return False
        return self.latest_activity.year >= 2024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FishTalk project-based population stitching report"
    )
    parser.add_argument(
        "--profile",
        default="fishtalk_readonly",
        help="migration_config.json sqlserver profile",
    )
    parser.add_argument(
        "--since",
        help="Only include populations with StartTime >= YYYY-MM-DD",
    )
    parser.add_argument(
        "--min-stages",
        type=int,
        default=4,
        help="Minimum number of AquaMind stages required (default: 4)",
    )
    parser.add_argument(
        "--require-sea",
        action="store_true",
        help="Only include batches that have sea stages (Adult)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only include batches with activity in 2024-2025",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            (PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching").as_posix()
        ),
        help="Directory to write CSV outputs",
    )
    parser.add_argument(
        "--print-top",
        type=int,
        default=20,
        help="Print top N batch candidates to stdout",
    )
    return parser


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: ("" if row.get(key) is None else row.get(key)) for key in fieldnames}
            )


def main() -> int:
    args = build_parser().parse_args()

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    extractor = BaseExtractor(ExtractionContext(profile=args.profile))

    # Build date filter
    date_filter = ""
    if args.since:
        date_filter = f"AND p.StartTime >= '{args.since}'"

    print("Loading populations from FishTalk...")

    # Query all populations with project identifiers
    populations_raw = extractor._run_sqlcmd(
        query=f"""
            SELECT 
                CONVERT(varchar(36), p.PopulationID) AS PopulationID,
                CONVERT(varchar(36), p.ContainerID) AS ContainerID,
                p.PopulationName,
                ISNULL(CONVERT(varchar(50), p.ProjectNumber), '') AS ProjectNumber,
                ISNULL(CONVERT(varchar(50), p.InputYear), '') AS InputYear,
                ISNULL(CONVERT(varchar(50), p.RunningNumber), '') AS RunningNumber,
                CONVERT(varchar(23), p.StartTime, 121) AS StartTime,
                CONVERT(varchar(23), p.EndTime, 121) AS EndTime
            FROM dbo.Populations p
            WHERE p.ProjectNumber IS NOT NULL 
              AND p.InputYear IS NOT NULL
              {date_filter}
        """,
        headers=[
            "PopulationID",
            "ContainerID",
            "PopulationName",
            "ProjectNumber",
            "InputYear",
            "RunningNumber",
            "StartTime",
            "EndTime",
        ],
    )

    print(f"  Loaded {len(populations_raw):,} populations with project identifiers")

    # Query all production stages
    print("Loading production stages...")
    stages_raw = extractor._run_sqlcmd(
        query="SELECT StageID, StageName FROM dbo.ProductionStages",
        headers=["StageID", "StageName"],
    )
    stage_name_by_id = {row["StageID"]: (row.get("StageName") or "").strip() for row in stages_raw}

    # Query population stage events
    print("Loading population stage events...")
    stage_events_raw = extractor._run_sqlcmd(
        query=f"""
            SELECT 
                CONVERT(varchar(36), pps.PopulationID) AS PopulationID,
                pps.StageID,
                CONVERT(varchar(23), pps.StartTime, 121) AS StartTime
            FROM dbo.PopulationProductionStages pps
            JOIN dbo.Populations p ON p.PopulationID = pps.PopulationID
            WHERE p.ProjectNumber IS NOT NULL
              AND p.InputYear IS NOT NULL
              {date_filter}
        """,
        headers=["PopulationID", "StageID", "StartTime"],
    )

    print(f"  Loaded {len(stage_events_raw):,} stage events")

    # Build stage events by population
    stage_events_by_pop: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for row in stage_events_raw:
        ts = parse_dt(row.get("StartTime", ""))
        if ts is None:
            continue
        stage_name = stage_name_by_id.get(row.get("StageID", ""), "")
        if stage_name:
            stage_events_by_pop[row["PopulationID"]].append((ts, stage_name))

    for pop_id in stage_events_by_pop:
        stage_events_by_pop[pop_id].sort(key=lambda x: x[0])

    # Build population info objects
    pop_info: dict[str, PopulationInfo] = {}
    for row in populations_raw:
        pop_id = row["PopulationID"]
        stages = stage_events_by_pop.get(pop_id, [])
        stage_names = [s[1] for s in stages]
        aquamind_stages = {
            fishtalk_stage_to_aquamind(s) for s in stage_names if fishtalk_stage_to_aquamind(s)
        }

        pop_info[pop_id] = PopulationInfo(
            population_id=pop_id,
            container_id=row.get("ContainerID", "") or "",
            name=row.get("PopulationName", "") or "",
            project_number=(row.get("ProjectNumber") or "").strip(),
            input_year=(row.get("InputYear") or "").strip(),
            running_number=(row.get("RunningNumber") or "").strip(),
            start_time=parse_dt(row.get("StartTime", "")),
            end_time=parse_dt(row.get("EndTime", "")),
            stages=stage_names,
            aquamind_stages=aquamind_stages,
        )

    # Group by project tuple
    print("Grouping populations by project identifiers...")
    batches_by_key: dict[str, ProjectBatch] = {}

    for pop in pop_info.values():
        if not pop.project_number or not pop.input_year:
            continue

        key = f"{pop.project_number}/{pop.input_year}/{pop.running_number}"

        if key not in batches_by_key:
            batches_by_key[key] = ProjectBatch(
                project_key=key,
                project_number=pop.project_number,
                input_year=pop.input_year,
                running_number=pop.running_number,
            )

        batch = batches_by_key[key]
        batch.populations.append(pop)
        batch.aquamind_stages.update(pop.aquamind_stages)
        batch.fishtalk_stages.update(pop.stages)

        # Update time bounds
        if pop.start_time:
            if batch.earliest_start is None or pop.start_time < batch.earliest_start:
                batch.earliest_start = pop.start_time
        if pop.end_time:
            if batch.latest_end is None or pop.end_time > batch.latest_end:
                batch.latest_end = pop.end_time
            if batch.latest_activity is None or pop.end_time > batch.latest_activity:
                batch.latest_activity = pop.end_time
        elif pop.start_time:
            if batch.latest_activity is None or pop.start_time > batch.latest_activity:
                batch.latest_activity = pop.start_time

    print(f"  Found {len(batches_by_key):,} unique project batches")

    # Filter batches based on criteria
    filtered_batches: list[ProjectBatch] = []
    for batch in batches_by_key.values():
        if batch.stage_coverage_count < args.min_stages:
            continue
        if args.require_sea and "Adult" not in batch.aquamind_stages:
            continue
        if args.active_only and not batch.is_active:
            continue
        filtered_batches.append(batch)

    # Sort by stage coverage (descending) then by latest activity (descending)
    filtered_batches.sort(
        key=lambda b: (
            b.stage_coverage_count,
            b.has_all_stages,
            b.is_active,
            b.latest_activity or datetime.min,
        ),
        reverse=True,
    )

    print(f"  {len(filtered_batches):,} batches meet criteria (min_stages={args.min_stages})")

    # Write batch candidates CSV
    batch_rows: list[dict[str, object]] = []
    for batch in filtered_batches:
        stages_str = ", ".join(
            s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
        )
        batch_rows.append(
            {
                "project_key": batch.project_key,
                "project_number": batch.project_number,
                "input_year": batch.input_year,
                "running_number": batch.running_number,
                "population_count": len(batch.populations),
                "aquamind_stages": stages_str,
                "stage_count": batch.stage_coverage_count,
                "has_all_stages": batch.has_all_stages,
                "has_fw_and_sea": batch.has_fw_and_sea,
                "is_active": batch.is_active,
                "earliest_start": batch.earliest_start.isoformat(sep=" ") if batch.earliest_start else "",
                "latest_end": batch.latest_end.isoformat(sep=" ") if batch.latest_end else "",
                "latest_activity": batch.latest_activity.isoformat(sep=" ") if batch.latest_activity else "",
                "representative_name": batch.populations[0].name if batch.populations else "",
            }
        )

    write_csv(
        output_dir / "project_batches.csv",
        fieldnames=[
            "project_key",
            "project_number",
            "input_year",
            "running_number",
            "population_count",
            "aquamind_stages",
            "stage_count",
            "has_all_stages",
            "has_fw_and_sea",
            "is_active",
            "earliest_start",
            "latest_end",
            "latest_activity",
            "representative_name",
        ],
        rows=batch_rows,
    )

    # Write population members CSV
    pop_rows: list[dict[str, object]] = []
    for batch in filtered_batches:
        for pop in batch.populations:
            stages_str = ", ".join(pop.stages) if pop.stages else ""
            aquamind_str = ", ".join(
                s for s in AQUAMIND_STAGES_ORDERED if s in pop.aquamind_stages
            )
            pop_rows.append(
                {
                    "project_key": batch.project_key,
                    "population_id": pop.population_id,
                    "population_name": pop.name,
                    "container_id": pop.container_id,
                    "start_time": pop.start_time.isoformat(sep=" ") if pop.start_time else "",
                    "end_time": pop.end_time.isoformat(sep=" ") if pop.end_time else "",
                    "fishtalk_stages": stages_str,
                    "aquamind_stages": aquamind_str,
                }
            )

    write_csv(
        output_dir / "project_population_members.csv",
        fieldnames=[
            "project_key",
            "population_id",
            "population_name",
            "container_id",
            "start_time",
            "end_time",
            "fishtalk_stages",
            "aquamind_stages",
        ],
        rows=pop_rows,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("PROJECT-BASED STITCHING REPORT")
    print("=" * 60)
    print(f"Total populations with project IDs: {len(pop_info):,}")
    print(f"Total project batches: {len(batches_by_key):,}")
    print(f"Batches meeting criteria: {len(filtered_batches):,}")

    # Stage coverage summary
    all_6 = sum(1 for b in filtered_batches if b.has_all_stages)
    has_5 = sum(1 for b in filtered_batches if b.stage_coverage_count == 5)
    has_4 = sum(1 for b in filtered_batches if b.stage_coverage_count == 4)
    active = sum(1 for b in filtered_batches if b.is_active)
    fw_sea = sum(1 for b in filtered_batches if b.has_fw_and_sea)

    print(f"\nStage coverage breakdown:")
    print(f"  All 6 stages: {all_6}")
    print(f"  5 stages: {has_5}")
    print(f"  4 stages: {has_4}")
    print(f"  Has FW + Sea: {fw_sea}")
    print(f"  Active (2024-2025): {active}")

    print(f"\nOutputs written to: {output_dir.resolve()}")

    # Print top candidates
    print(f"\n{'='*60}")
    print(f"TOP {args.print_top} BATCH CANDIDATES")
    print("=" * 60)

    for i, batch in enumerate(filtered_batches[: args.print_top], start=1):
        stages_str = ", ".join(
            s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
        )
        active_str = "ACTIVE" if batch.is_active else "completed"
        print(
            f"{i:2}. {batch.project_key:20} | {len(batch.populations):3} pops | "
            f"{batch.stage_coverage_count}/6 stages | {active_str:9} | {stages_str}"
        )
        if batch.populations:
            print(f"    Representative: {batch.populations[0].name}")
            print(
                f"    Time span: {batch.earliest_start.strftime('%Y-%m-%d') if batch.earliest_start else '?'} "
                f"to {batch.latest_activity.strftime('%Y-%m-%d') if batch.latest_activity else '?'}"
            )

    # Recommend best candidates for migration
    best_candidates = [
        b for b in filtered_batches if b.has_all_stages and b.is_active and b.has_fw_and_sea
    ]
    if not best_candidates:
        best_candidates = [
            b for b in filtered_batches if b.stage_coverage_count >= 5 and b.has_fw_and_sea
        ]
    if not best_candidates:
        best_candidates = [b for b in filtered_batches if b.has_fw_and_sea][:15]

    if best_candidates:
        print(f"\n{'='*60}")
        print("RECOMMENDED FOR MIGRATION (FW+Sea, most stages, active)")
        print("=" * 60)
        for i, batch in enumerate(best_candidates[:15], start=1):
            stages_str = ", ".join(
                s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
            )
            print(f"{i:2}. {batch.project_key} ({batch.stage_coverage_count}/6 stages)")

        # Write recommended batches to separate file
        recommended_rows = [
            {
                "project_key": b.project_key,
                "population_count": len(b.populations),
                "stage_count": b.stage_coverage_count,
                "stages": ", ".join(s for s in AQUAMIND_STAGES_ORDERED if s in b.aquamind_stages),
                "is_active": b.is_active,
                "earliest_start": b.earliest_start.isoformat(sep=" ") if b.earliest_start else "",
                "latest_activity": b.latest_activity.isoformat(sep=" ") if b.latest_activity else "",
            }
            for b in best_candidates[:15]
        ]
        write_csv(
            output_dir / "recommended_batches.csv",
            fieldnames=[
                "project_key",
                "population_count",
                "stage_count",
                "stages",
                "is_active",
                "earliest_start",
                "latest_activity",
            ],
            rows=recommended_rows,
        )
        print(f"\nRecommended batches written to: {output_dir / 'recommended_batches.csv'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
