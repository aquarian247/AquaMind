#!/usr/bin/env python3
# flake8: noqa
"""Generate a FishTalk population stitching report using Ext_Inputs_v2 (egg deliveries).

BREAKTHROUGH (2026-01-22): The Ext_Inputs_v2 table tracks egg inputs/deliveries from suppliers.
This is the TRUE biological batch identifier - each batch key (InputName + InputNumber + YearClass)
represents a cohort of fish from a single egg fertilization event.

Unlike scripts/migration/legacy/tools/project_based_stitching_report.py (deprecated) which uses administrative project tuples that can mix
multiple year-classes, this script groups populations by their biological origin.

Batch Key: InputName + InputNumber + YearClass

Example valid batches from actual FishTalk data:
- "22S1 LHS | 2 | 2021" = 317 populations, 42-day span, 6.9M fish
- "Heyst 2023 | 1 | 2023" = 108 populations, 275-day span, 6.3M fish

Validations applied:
1. Single geography (batch stays in ONE station → ONE sea area)
2. Valid stage progression (Egg&Alevin → Fry → Parr → Smolt → Post-Smolt → Adult)
3. Time span < 900 days (typical lifecycle 2-2.5 years)
4. Fish count validation (expected 1-3M per batch, flag outliers)

Usage:
    python input_based_stitching_report.py
    python input_based_stitching_report.py --min-fish 1000000 --max-span-days 900
    python input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
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
    """Parse datetime from FishTalk string format."""
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_float(value: str) -> float:
    """Parse float from string, return 0.0 on error."""
    if not value:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


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


AQUAMIND_STAGES_ORDERED = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_ORDER = {stage: i for i, stage in enumerate(AQUAMIND_STAGES_ORDERED)}

# Geography determination - sites in Faroe Islands
FAROE_SITE_KEYWORDS = {"north", "south", "west", "east", "faroe", "føroyar", "streymoy"}
SCOTLAND_SITE_KEYWORDS = {"scotland", "scottish", "uk", "loch"}


def determine_geography(site_name: str, site_group: str | None = None) -> str:
    """Determine geography (Faroe Islands or Scotland) from site info."""
    if site_group:
        sg_lower = site_group.lower()
        if sg_lower in ("west", "north", "south", "east"):
            return "Faroe Islands"
    
    if site_name:
        name_lower = site_name.lower()
        if any(kw in name_lower for kw in FAROE_SITE_KEYWORDS):
            return "Faroe Islands"
        if any(kw in name_lower for kw in SCOTLAND_SITE_KEYWORDS):
            return "Scotland"
    
    return "Unknown"


@dataclass
class PopulationInfo:
    """Information about a single population in FishTalk."""
    population_id: str
    container_id: str
    container_name: str = ""
    org_unit_id: str = ""
    org_unit_name: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    stages: list[str] = field(default_factory=list)
    aquamind_stages: set[str] = field(default_factory=set)
    geography: str = "Unknown"


@dataclass
class InputInfo:
    """Information about an input record from Ext_Inputs_v2."""
    population_id: str
    input_name: str
    input_number: str
    year_class: str
    supplier_id: str
    start_time: datetime | None
    input_count: float
    input_biomass: float
    fish_type: str
    broodstock: str


@dataclass
class InputBatch:
    """A biological batch identified by InputName + InputNumber + YearClass."""
    batch_key: str  # "InputName|InputNumber|YearClass"
    input_name: str
    input_number: str
    year_class: str
    inputs: list[InputInfo] = field(default_factory=list)
    populations: list[PopulationInfo] = field(default_factory=list)
    aquamind_stages: set[str] = field(default_factory=set)
    fishtalk_stages: set[str] = field(default_factory=set)
    geographies: set[str] = field(default_factory=set)
    earliest_start: datetime | None = None
    latest_end: datetime | None = None
    latest_activity: datetime | None = None
    total_fish: float = 0.0
    total_biomass: float = 0.0
    
    # Validation flags
    is_valid: bool = True
    validation_issues: list[str] = field(default_factory=list)
    
    @property
    def span_days(self) -> int:
        """Calculate the time span in days between earliest and latest activity."""
        if self.earliest_start and self.latest_activity:
            return (self.latest_activity - self.earliest_start).days
        return 0
    
    @property
    def has_single_geography(self) -> bool:
        """Check if batch stays in a single geography (excluding Unknown)."""
        known_geos = {g for g in self.geographies if g != "Unknown"}
        return len(known_geos) <= 1
    
    @property
    def has_valid_stage_progression(self) -> bool:
        """Check if stages follow biological order (no backwards jumps)."""
        if not self.aquamind_stages:
            return True
        
        ordered_stages = [s for s in AQUAMIND_STAGES_ORDERED if s in self.aquamind_stages]
        if len(ordered_stages) <= 1:
            return True
        
        # Check that stages are contiguous or reasonable
        indices = [STAGE_ORDER[s] for s in ordered_stages]
        return indices == sorted(indices)
    
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
    
    def validate(self, max_span_days: int = 900, min_fish: int = 100000) -> None:
        """Run validations and set is_valid flag."""
        self.validation_issues = []
        
        # Check single geography
        if not self.has_single_geography:
            self.validation_issues.append(
                f"Multiple geographies: {', '.join(sorted(self.geographies))}"
            )
        
        # Check time span
        if self.span_days > max_span_days:
            self.validation_issues.append(
                f"Time span too long: {self.span_days} days (max {max_span_days})"
            )
        
        # Check fish count (flag if too low but don't invalidate)
        if self.total_fish < min_fish:
            self.validation_issues.append(
                f"Low fish count: {self.total_fish:,.0f} (expected >= {min_fish:,})"
            )
        
        # Check stage progression
        if not self.has_valid_stage_progression:
            self.validation_issues.append("Invalid stage progression (out of order)")
        
        # A batch is valid if it has single geography and reasonable time span
        self.is_valid = self.has_single_geography and self.span_days <= max_span_days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FishTalk input-based population stitching report (Ext_Inputs_v2)"
    )
    parser.add_argument(
        "--profile",
        default="fishtalk_readonly",
        help="migration_config.json sqlserver profile",
    )
    parser.add_argument(
        "--since",
        help="Only include inputs with StartTime >= YYYY-MM-DD",
    )
    parser.add_argument(
        "--min-populations",
        type=int,
        default=2,
        help="Minimum number of populations per batch (default: 2)",
    )
    parser.add_argument(
        "--min-fish",
        type=int,
        default=100000,
        help="Minimum fish count per batch for validation (default: 100000)",
    )
    parser.add_argument(
        "--max-span-days",
        type=int,
        default=900,
        help="Maximum time span in days (default: 900, ~2.5 years)",
    )
    parser.add_argument(
        "--valid-only",
        action="store_true",
        help="Only output batches that pass all validations",
    )
    parser.add_argument(
        "--require-sea",
        action="store_true",
        help="Only include batches that have sea stages (Adult/Post-Smolt)",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Only include batches with activity in 2024-2025",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            (PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching").as_posix()
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
        date_filter = f"AND i.StartTime >= '{args.since}'"

    print("=" * 70)
    print("INPUT-BASED BATCH IDENTIFICATION (Ext_Inputs_v2)")
    print("=" * 70)
    print(f"Profile: {args.profile}")
    print(f"Output: {output_dir}")
    print()

    # Step 1: Load Ext_Inputs_v2 data
    print("Step 1: Loading Ext_Inputs_v2 (egg input records)...")
    inputs_raw = extractor._run_sqlcmd(
        query=f"""
            SELECT 
                CONVERT(varchar(36), i.PopulationID) AS PopulationID,
                ISNULL(i.InputName, '') AS InputName,
                ISNULL(CONVERT(varchar(10), i.InputNumber), '0') AS InputNumber,
                ISNULL(i.YearClass, '') AS YearClass,
                CONVERT(varchar(36), i.Supplier) AS SupplierID,
                CONVERT(varchar(23), i.StartTime, 121) AS StartTime,
                ISNULL(CONVERT(varchar(32), i.InputCount), '0') AS InputCount,
                ISNULL(CONVERT(varchar(32), i.InputBiomass), '0') AS InputBiomass,
                ISNULL(i.FishType, '') AS FishType,
                ISNULL(i.Broodstock, '') AS Broodstock
            FROM dbo.Ext_Inputs_v2 i
            WHERE i.InputName IS NOT NULL 
              AND i.YearClass IS NOT NULL
              {date_filter}
        """,
        headers=[
            "PopulationID", "InputName", "InputNumber", "YearClass", "SupplierID",
            "StartTime", "InputCount", "InputBiomass", "FishType", "Broodstock",
        ],
    )
    print(f"  Loaded {len(inputs_raw):,} input records")

    # Step 2: Load Populations with container info
    print("Step 2: Loading Populations...")
    populations_raw = extractor._run_sqlcmd(
        query="""
            SELECT 
                CONVERT(varchar(36), p.PopulationID) AS PopulationID,
                CONVERT(varchar(36), p.ContainerID) AS ContainerID,
                CONVERT(varchar(23), p.StartTime, 121) AS StartTime,
                CONVERT(varchar(23), p.EndTime, 121) AS EndTime
            FROM dbo.Populations p
        """,
        headers=["PopulationID", "ContainerID", "StartTime", "EndTime"],
    )
    print(f"  Loaded {len(populations_raw):,} populations")

    # Build population lookup
    pop_lookup: dict[str, dict] = {
        row["PopulationID"]: row for row in populations_raw
    }

    # Step 3: Load Containers with org unit info
    print("Step 3: Loading Containers and OrgUnits...")
    containers_raw = extractor._run_sqlcmd(
        query="""
            SELECT 
                CONVERT(varchar(36), c.ContainerID) AS ContainerID,
                c.ContainerName,
                CONVERT(varchar(36), c.OrgUnitID) AS OrgUnitID
            FROM dbo.Containers c
        """,
        headers=["ContainerID", "ContainerName", "OrgUnitID"],
    )
    container_lookup: dict[str, dict] = {
        row["ContainerID"]: row for row in containers_raw
    }
    print(f"  Loaded {len(containers_raw):,} containers")

    # Load org units
    org_units_raw = extractor._run_sqlcmd(
        query="""
            SELECT 
                CONVERT(varchar(36), ou.OrgUnitID) AS OrgUnitID,
                ou.Name AS OrgUnitName
            FROM dbo.OrganisationUnit ou
        """,
        headers=["OrgUnitID", "OrgUnitName"],
    )
    org_unit_lookup: dict[str, str] = {
        row["OrgUnitID"]: row.get("OrgUnitName", "") or "" for row in org_units_raw
    }
    print(f"  Loaded {len(org_units_raw):,} org units")

    # Try to load grouped organisation for geography
    print("Step 4: Loading geography info (Ext_GroupedOrganisation_v2)...")
    try:
        grouped_org_raw = extractor._run_sqlcmd(
            query="""
                SELECT 
                    CONVERT(varchar(36), ContainerID) AS ContainerID,
                    Site,
                    SiteGroup
                FROM dbo.Ext_GroupedOrganisation_v2
            """,
            headers=["ContainerID", "Site", "SiteGroup"],
        )
        container_geo_lookup: dict[str, tuple[str, str]] = {
            row["ContainerID"]: (row.get("Site", "") or "", row.get("SiteGroup", "") or "")
            for row in grouped_org_raw
        }
        print(f"  Loaded {len(grouped_org_raw):,} grouped org records")
    except Exception as e:
        print(f"  Warning: Could not load Ext_GroupedOrganisation_v2: {e}")
        container_geo_lookup = {}

    # Step 5: Load production stages
    print("Step 5: Loading production stages...")
    stages_raw = extractor._run_sqlcmd(
        query="SELECT StageID, StageName FROM dbo.ProductionStages",
        headers=["StageID", "StageName"],
    )
    stage_name_by_id = {row["StageID"]: (row.get("StageName") or "").strip() for row in stages_raw}

    # Load population stage events
    stage_events_raw = extractor._run_sqlcmd(
        query="""
            SELECT 
                CONVERT(varchar(36), pps.PopulationID) AS PopulationID,
                pps.StageID,
                CONVERT(varchar(23), pps.StartTime, 121) AS StartTime
            FROM dbo.PopulationProductionStages pps
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

    # Step 6: Build Input batches
    print("\nStep 6: Building Input-based batches...")
    
    # Parse input records
    input_records: list[InputInfo] = []
    for row in inputs_raw:
        input_records.append(InputInfo(
            population_id=row["PopulationID"],
            input_name=row.get("InputName", "").strip(),
            input_number=row.get("InputNumber", "0").strip(),
            year_class=row.get("YearClass", "").strip(),
            supplier_id=row.get("SupplierID", "") or "",
            start_time=parse_dt(row.get("StartTime", "")),
            input_count=parse_float(row.get("InputCount", "0")),
            input_biomass=parse_float(row.get("InputBiomass", "0")),
            fish_type=row.get("FishType", "").strip(),
            broodstock=row.get("Broodstock", "").strip(),
        ))

    # Group inputs by batch key
    batches_by_key: dict[str, InputBatch] = {}
    
    for inp in input_records:
        if not inp.input_name or not inp.year_class:
            continue
        
        batch_key = f"{inp.input_name}|{inp.input_number}|{inp.year_class}"
        
        if batch_key not in batches_by_key:
            batches_by_key[batch_key] = InputBatch(
                batch_key=batch_key,
                input_name=inp.input_name,
                input_number=inp.input_number,
                year_class=inp.year_class,
            )
        
        batch = batches_by_key[batch_key]
        batch.inputs.append(inp)
        batch.total_fish += inp.input_count
        batch.total_biomass += inp.input_biomass
        
        # Update time bounds from input
        if inp.start_time:
            if batch.earliest_start is None or inp.start_time < batch.earliest_start:
                batch.earliest_start = inp.start_time
            if batch.latest_activity is None or inp.start_time > batch.latest_activity:
                batch.latest_activity = inp.start_time
        
        # Build population info
        pop_data = pop_lookup.get(inp.population_id)
        if pop_data:
            container_id = pop_data.get("ContainerID", "") or ""
            container_data = container_lookup.get(container_id, {})
            container_name = container_data.get("ContainerName", "") or ""
            org_unit_id = container_data.get("OrgUnitID", "") or ""
            org_unit_name = org_unit_lookup.get(org_unit_id, "")
            
            # Get geography
            site_info = container_geo_lookup.get(container_id, ("", ""))
            geography = determine_geography(site_info[0] or org_unit_name, site_info[1])
            
            # Get stages
            stage_events = stage_events_by_pop.get(inp.population_id, [])
            stage_names = [s[1] for s in stage_events]
            aquamind_stages = {
                fishtalk_stage_to_aquamind(s) for s in stage_names 
                if fishtalk_stage_to_aquamind(s)
            }
            
            pop_info = PopulationInfo(
                population_id=inp.population_id,
                container_id=container_id,
                container_name=container_name,
                org_unit_id=org_unit_id,
                org_unit_name=org_unit_name,
                start_time=parse_dt(pop_data.get("StartTime", "")),
                end_time=parse_dt(pop_data.get("EndTime", "")),
                stages=stage_names,
                aquamind_stages=aquamind_stages,
                geography=geography,
            )
            
            batch.populations.append(pop_info)
            batch.aquamind_stages.update(aquamind_stages)
            batch.fishtalk_stages.update(stage_names)
            batch.geographies.add(geography)
            
            # Update time bounds from population
            if pop_info.start_time:
                if batch.earliest_start is None or pop_info.start_time < batch.earliest_start:
                    batch.earliest_start = pop_info.start_time
            if pop_info.end_time:
                if batch.latest_end is None or pop_info.end_time > batch.latest_end:
                    batch.latest_end = pop_info.end_time
                if batch.latest_activity is None or pop_info.end_time > batch.latest_activity:
                    batch.latest_activity = pop_info.end_time
            elif pop_info.start_time:
                if batch.latest_activity is None or pop_info.start_time > batch.latest_activity:
                    batch.latest_activity = pop_info.start_time

    print(f"  Found {len(batches_by_key):,} unique input batches")

    # Step 7: Validate batches
    print("\nStep 7: Validating batches...")
    for batch in batches_by_key.values():
        batch.validate(max_span_days=args.max_span_days, min_fish=args.min_fish)
    
    valid_batches = [b for b in batches_by_key.values() if b.is_valid]
    print(f"  Valid batches: {len(valid_batches):,}")

    # Step 8: Filter batches based on criteria
    filtered_batches: list[InputBatch] = []
    for batch in batches_by_key.values():
        if args.valid_only and not batch.is_valid:
            continue
        if len(batch.populations) < args.min_populations:
            continue
        if args.require_sea and not batch.has_fw_and_sea:
            continue
        if args.active_only and not batch.is_active:
            continue
        filtered_batches.append(batch)

    # Sort by fish count (descending), then stage coverage
    filtered_batches.sort(
        key=lambda b: (
            b.is_valid,
            b.total_fish,
            b.stage_coverage_count,
            b.latest_activity or datetime.min,
        ),
        reverse=True,
    )

    print(f"  Filtered batches meeting criteria: {len(filtered_batches):,}")

    # Step 9: Write output CSVs
    print("\nStep 8: Writing output files...")
    
    # Write main batch summary CSV
    batch_rows: list[dict[str, object]] = []
    for batch in filtered_batches:
        stages_str = ", ".join(
            s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
        )
        geos_str = ", ".join(sorted(batch.geographies))
        issues_str = "; ".join(batch.validation_issues) if batch.validation_issues else ""
        
        batch_rows.append({
            "batch_key": batch.batch_key,
            "input_name": batch.input_name,
            "input_number": batch.input_number,
            "year_class": batch.year_class,
            "population_count": len(batch.populations),
            "total_fish": f"{batch.total_fish:,.0f}",
            "total_biomass_kg": f"{batch.total_biomass:,.2f}",
            "span_days": batch.span_days,
            "aquamind_stages": stages_str,
            "stage_count": batch.stage_coverage_count,
            "geographies": geos_str,
            "has_single_geography": batch.has_single_geography,
            "has_fw_and_sea": batch.has_fw_and_sea,
            "is_active": batch.is_active,
            "is_valid": batch.is_valid,
            "validation_issues": issues_str,
            "earliest_start": batch.earliest_start.isoformat(sep=" ") if batch.earliest_start else "",
            "latest_activity": batch.latest_activity.isoformat(sep=" ") if batch.latest_activity else "",
        })

    write_csv(
        output_dir / "input_batches.csv",
        fieldnames=[
            "batch_key", "input_name", "input_number", "year_class",
            "population_count", "total_fish", "total_biomass_kg", "span_days",
            "aquamind_stages", "stage_count", "geographies",
            "has_single_geography", "has_fw_and_sea", "is_active", "is_valid",
            "validation_issues", "earliest_start", "latest_activity",
        ],
        rows=batch_rows,
    )
    print(f"  Written: {output_dir / 'input_batches.csv'}")

    # Write population members CSV
    pop_rows: list[dict[str, object]] = []
    for batch in filtered_batches:
        for pop in batch.populations:
            stages_str = ", ".join(pop.stages) if pop.stages else ""
            aquamind_str = ", ".join(
                s for s in AQUAMIND_STAGES_ORDERED if s in pop.aquamind_stages
            )
            pop_rows.append({
                "batch_key": batch.batch_key,
                "population_id": pop.population_id,
                "container_id": pop.container_id,
                "container_name": pop.container_name,
                "org_unit_name": pop.org_unit_name,
                "geography": pop.geography,
                "start_time": pop.start_time.isoformat(sep=" ") if pop.start_time else "",
                "end_time": pop.end_time.isoformat(sep=" ") if pop.end_time else "",
                "fishtalk_stages": stages_str,
                "aquamind_stages": aquamind_str,
            })

    write_csv(
        output_dir / "input_population_members.csv",
        fieldnames=[
            "batch_key", "population_id", "container_id", "container_name",
            "org_unit_name", "geography", "start_time", "end_time",
            "fishtalk_stages", "aquamind_stages",
        ],
        rows=pop_rows,
    )
    print(f"  Written: {output_dir / 'input_population_members.csv'}")

    # Write raw input records CSV
    input_rows: list[dict[str, object]] = []
    for batch in filtered_batches:
        for inp in batch.inputs:
            input_rows.append({
                "batch_key": batch.batch_key,
                "population_id": inp.population_id,
                "input_name": inp.input_name,
                "input_number": inp.input_number,
                "year_class": inp.year_class,
                "supplier_id": inp.supplier_id,
                "start_time": inp.start_time.isoformat(sep=" ") if inp.start_time else "",
                "input_count": f"{inp.input_count:,.0f}",
                "input_biomass_kg": f"{inp.input_biomass:,.2f}",
                "fish_type": inp.fish_type,
                "broodstock": inp.broodstock,
            })

    write_csv(
        output_dir / "input_records.csv",
        fieldnames=[
            "batch_key", "population_id", "input_name", "input_number", "year_class",
            "supplier_id", "start_time", "input_count", "input_biomass_kg",
            "fish_type", "broodstock",
        ],
        rows=input_rows,
    )
    print(f"  Written: {output_dir / 'input_records.csv'}")

    # Print summary
    print("\n" + "=" * 70)
    print("INPUT-BASED STITCHING REPORT SUMMARY")
    print("=" * 70)
    print(f"Total input records: {len(inputs_raw):,}")
    print(f"Total input batches: {len(batches_by_key):,}")
    print(f"Valid batches: {len(valid_batches):,}")
    print(f"Filtered batches: {len(filtered_batches):,}")

    # Statistics breakdown
    with_sea = sum(1 for b in filtered_batches if b.has_fw_and_sea)
    active = sum(1 for b in filtered_batches if b.is_active)
    single_geo = sum(1 for b in filtered_batches if b.has_single_geography)
    
    print(f"\nBatch statistics:")
    print(f"  With FW + Sea stages: {with_sea}")
    print(f"  Active (2024-2025): {active}")
    print(f"  Single geography: {single_geo}")
    
    # Fish count distribution
    fish_counts = [b.total_fish for b in filtered_batches]
    if fish_counts:
        print(f"\nFish count distribution:")
        print(f"  Min: {min(fish_counts):,.0f}")
        print(f"  Max: {max(fish_counts):,.0f}")
        print(f"  Avg: {sum(fish_counts)/len(fish_counts):,.0f}")
        
    # Span distribution
    spans = [b.span_days for b in filtered_batches if b.span_days > 0]
    if spans:
        print(f"\nTime span distribution (days):")
        print(f"  Min: {min(spans)}")
        print(f"  Max: {max(spans)}")
        print(f"  Avg: {sum(spans)/len(spans):.0f}")

    print(f"\nOutputs written to: {output_dir.resolve()}")

    # Print top candidates
    print(f"\n{'='*70}")
    print(f"TOP {args.print_top} BATCH CANDIDATES")
    print("=" * 70)

    for i, batch in enumerate(filtered_batches[: args.print_top], start=1):
        stages_str = ", ".join(
            s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
        )
        valid_str = "VALID" if batch.is_valid else "INVALID"
        active_str = "ACTIVE" if batch.is_active else "completed"
        geo_str = ", ".join(sorted(batch.geographies))
        
        print(
            f"{i:2}. {batch.input_name[:30]:30} | YC:{batch.year_class:4} | "
            f"{len(batch.populations):3} pops | {batch.total_fish/1e6:.1f}M fish | "
            f"{batch.span_days:3}d | {valid_str}"
        )
        print(f"    Stages: {stages_str}")
        print(f"    Geography: {geo_str} | {active_str}")
        if batch.validation_issues:
            print(f"    Issues: {'; '.join(batch.validation_issues)}")
        print()

    # Recommend best candidates for migration
    best_candidates = [
        b for b in filtered_batches 
        if b.is_valid and b.has_fw_and_sea and b.total_fish >= 1_000_000
    ]
    if not best_candidates:
        best_candidates = [
            b for b in filtered_batches 
            if b.is_valid and b.total_fish >= 500_000
        ][:15]

    if best_candidates:
        print(f"\n{'='*70}")
        print("RECOMMENDED FOR MIGRATION (Valid, FW+Sea, >=1M fish)")
        print("=" * 70)
        
        recommended_rows = []
        for i, batch in enumerate(best_candidates[:15], start=1):
            stages_str = ", ".join(
                s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages
            )
            print(
                f"{i:2}. {batch.input_name} | YC:{batch.year_class} | "
                f"{batch.total_fish/1e6:.1f}M fish | {batch.span_days}d"
            )
            
            recommended_rows.append({
                "batch_key": batch.batch_key,
                "input_name": batch.input_name,
                "input_number": batch.input_number,
                "year_class": batch.year_class,
                "population_count": len(batch.populations),
                "total_fish": f"{batch.total_fish:,.0f}",
                "span_days": batch.span_days,
                "stages": stages_str,
                "is_active": batch.is_active,
                "earliest_start": batch.earliest_start.isoformat(sep=" ") if batch.earliest_start else "",
                "latest_activity": batch.latest_activity.isoformat(sep=" ") if batch.latest_activity else "",
            })

        write_csv(
            output_dir / "recommended_batches.csv",
            fieldnames=[
                "batch_key", "input_name", "input_number", "year_class",
                "population_count", "total_fish", "span_days", "stages",
                "is_active", "earliest_start", "latest_activity",
            ],
            rows=recommended_rows,
        )
        print(f"\nRecommended batches written to: {output_dir / 'recommended_batches.csv'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
