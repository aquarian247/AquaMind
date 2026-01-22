#!/usr/bin/env python3
"""Analyze a project tuple to understand why it spans multiple cohorts.

This script investigates batch identification issues by:
1. Loading all populations for a given project tuple
2. Analyzing their timeline, stages, and containers
3. Testing cohort-splitting strategies
4. Outputting detailed analysis for debugging

Usage:
    python scripts/migration/tools/analyze_batch_cohorts.py --project-key "1/24/58"
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# CSV data paths
EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
POPULATIONS_CSV = EXTRACT_DIR / "populations.csv"
POPULATION_STAGES_CSV = EXTRACT_DIR / "population_stages.csv"
PRODUCTION_STAGES_CSV = EXTRACT_DIR / "production_stages.csv"
SUB_TRANSFERS_CSV = EXTRACT_DIR / "sub_transfers.csv"
CONTAINERS_CSV = EXTRACT_DIR / "containers.csv"

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)

# Biological stage order (index = expected order)
STAGE_ORDER = {
    "Egg": 0, "Green egg": 0, "Eye-egg": 0,
    "Sac Fry/Alevin": 1, "Alevin": 1,
    "Fry": 2,
    "Parr": 3,
    "Smolt": 4, "Large Smolt": 4,
    "Ongrowing": 5, "Grower": 5, "Grilse": 5,
    "Broodstock": 6,
}

AQUAMIND_STAGE_MAP = {
    "Egg": "Egg&Alevin", "Green egg": "Egg&Alevin", "Eye-egg": "Egg&Alevin",
    "Sac Fry/Alevin": "Egg&Alevin", "Alevin": "Egg&Alevin",
    "Fry": "Fry",
    "Parr": "Parr",
    "Smolt": "Smolt", "Large Smolt": "Post-Smolt",
    "Ongrowing": "Adult", "Grower": "Adult", "Grilse": "Adult",
    "Broodstock": "Adult",
}


def parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@dataclass
class Population:
    population_id: str
    project_key: str
    container_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    stages: list[tuple[datetime, str]] = field(default_factory=list)
    
    @property
    def first_stage(self) -> Optional[str]:
        if self.stages:
            return self.stages[0][1]
        return None
    
    @property
    def stage_order_value(self) -> int:
        """Return biological order of first stage (lower = earlier in lifecycle)."""
        if self.first_stage:
            return STAGE_ORDER.get(self.first_stage, 99)
        return 99
    
    @property
    def aquamind_stage(self) -> Optional[str]:
        if self.first_stage:
            return AQUAMIND_STAGE_MAP.get(self.first_stage)
        return None


def load_stage_names() -> dict[str, str]:
    """Load StageID -> StageName mapping."""
    stage_names = {}
    with open(PRODUCTION_STAGES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_names[row["StageID"]] = row["StageName"]
    return stage_names


def load_population_stages(stage_names: dict[str, str]) -> dict[str, list[tuple[datetime, str]]]:
    """Load all population stage events."""
    stages_by_pop: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    
    with open(POPULATION_STAGES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pop_id = row["PopulationID"]
            stage_id = row["StageID"]
            start_time = parse_dt(row.get("StartTime", ""))
            
            stage_name = stage_names.get(stage_id, "Unknown")
            if start_time:
                stages_by_pop[pop_id].append((start_time, stage_name))
    
    # Sort by time
    for pop_id in stages_by_pop:
        stages_by_pop[pop_id].sort(key=lambda x: x[0])
    
    return stages_by_pop


def load_populations_for_project(project_key: str, stages_by_pop: dict) -> list[Population]:
    """Load all populations for a given project key."""
    parts = project_key.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid project key format: {project_key}. Expected X/Y/Z")
    
    target_proj, target_year, target_run = parts
    populations = []
    
    with open(POPULATIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            proj = (row.get("ProjectNumber") or "").strip()
            year = (row.get("InputYear") or "").strip()
            run = (row.get("RunningNumber") or "").strip()
            
            if proj == target_proj and year == target_year and run == target_run:
                pop_id = row["PopulationID"]
                populations.append(Population(
                    population_id=pop_id,
                    project_key=project_key,
                    container_id=row.get("ContainerID", ""),
                    start_time=parse_dt(row.get("StartTime", "")),
                    end_time=parse_dt(row.get("EndTime", "")),
                    stages=stages_by_pop.get(pop_id, []),
                ))
    
    return populations


def load_subtransfers() -> dict[str, list[dict]]:
    """Load SubTransfers indexed by source population."""
    transfers_by_source: dict[str, list[dict]] = defaultdict(list)
    
    with open(SUB_TRANSFERS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_pop = row.get("SourcePopBefore", "")
            if source_pop:
                transfers_by_source[source_pop].append({
                    "operation_id": row.get("OperationID", ""),
                    "source_before": source_pop,
                    "source_after": row.get("SourcePopAfter", ""),
                    "dest_after": row.get("DestPopAfter", ""),
                    "operation_time": parse_dt(row.get("OperationTime", "")),
                    "share_count": float(row.get("ShareCountFwd", 0) or 0),
                })
    
    return transfers_by_source


def find_origin_populations(populations: list[Population], transfers: dict) -> list[Population]:
    """Find populations that have no incoming transfers (origin populations)."""
    all_pop_ids = {p.population_id for p in populations}
    dest_pops = set()
    
    # Find all populations that are destinations of transfers
    for pop in populations:
        for transfer_list in transfers.values():
            for t in transfer_list:
                if t["dest_after"] in all_pop_ids:
                    dest_pops.add(t["dest_after"])
                if t["source_after"] in all_pop_ids and t["source_after"] != t["source_before"]:
                    dest_pops.add(t["source_after"])
    
    # Origin = populations not in dest_pops
    origins = [p for p in populations if p.population_id not in dest_pops]
    return origins


def cohort_split_by_time_gap(populations: list[Population], gap_days: int = 90) -> list[list[Population]]:
    """Split populations into cohorts based on time gaps between start times."""
    if not populations:
        return []
    
    # Sort by start time
    sorted_pops = sorted(
        [p for p in populations if p.start_time],
        key=lambda p: p.start_time
    )
    
    if not sorted_pops:
        return [populations]
    
    cohorts = []
    current_cohort = [sorted_pops[0]]
    
    for pop in sorted_pops[1:]:
        prev_time = current_cohort[-1].start_time
        gap = (pop.start_time - prev_time).days
        
        if gap > gap_days:
            cohorts.append(current_cohort)
            current_cohort = [pop]
        else:
            current_cohort.append(pop)
    
    if current_cohort:
        cohorts.append(current_cohort)
    
    # Add populations without start time to the first cohort
    no_time_pops = [p for p in populations if not p.start_time]
    if no_time_pops and cohorts:
        cohorts[0].extend(no_time_pops)
    
    return cohorts


def cohort_split_by_stage_and_time(populations: list[Population], window_days: int = 120) -> list[list[Population]]:
    """Split cohorts ensuring biological stage order makes sense within time windows."""
    if not populations:
        return []
    
    # Group by approximate "wave" - populations that start within window_days of each other
    # and have compatible starting stages
    sorted_pops = sorted(
        [p for p in populations if p.start_time],
        key=lambda p: p.start_time
    )
    
    if not sorted_pops:
        return [populations]
    
    cohorts = []
    current_cohort = [sorted_pops[0]]
    cohort_start = sorted_pops[0].start_time
    cohort_min_stage = sorted_pops[0].stage_order_value
    
    for pop in sorted_pops[1:]:
        days_from_start = (pop.start_time - cohort_start).days
        pop_stage_order = pop.stage_order_value
        
        # Check if this pop fits in current cohort:
        # 1. Within time window
        # 2. Stage is same or later than minimum stage seen (biological progression)
        if days_from_start <= window_days and pop_stage_order >= cohort_min_stage:
            current_cohort.append(pop)
            cohort_min_stage = min(cohort_min_stage, pop_stage_order)
        else:
            # Check for impossible case: earlier stage appearing later in time
            if pop_stage_order < cohort_min_stage and days_from_start > 30:
                # This is likely a new year-class - start new cohort
                cohorts.append(current_cohort)
                current_cohort = [pop]
                cohort_start = pop.start_time
                cohort_min_stage = pop_stage_order
            elif days_from_start > window_days:
                # Time gap too large - start new cohort
                cohorts.append(current_cohort)
                current_cohort = [pop]
                cohort_start = pop.start_time
                cohort_min_stage = pop_stage_order
            else:
                # Edge case - add to current
                current_cohort.append(pop)
    
    if current_cohort:
        cohorts.append(current_cohort)
    
    return cohorts


def validate_cohort(cohort: list[Population]) -> dict:
    """Validate if a cohort represents a valid biological batch."""
    if not cohort:
        return {"valid": False, "reason": "Empty cohort"}
    
    pops_with_time = [p for p in cohort if p.start_time]
    if not pops_with_time:
        return {"valid": False, "reason": "No timestamps"}
    
    min_time = min(p.start_time for p in pops_with_time)
    max_time = max(p.end_time or p.start_time for p in pops_with_time)
    span_days = (max_time - min_time).days
    
    # Check stage order
    stage_times = []
    for p in cohort:
        for stage_time, stage_name in p.stages:
            stage_order = STAGE_ORDER.get(stage_name, 99)
            stage_times.append((stage_time, stage_order, stage_name))
    
    stage_times.sort(key=lambda x: x[0])
    
    # Check for stage regression (earlier stages appearing after later stages)
    violations = []
    if len(stage_times) > 1:
        max_order_seen = stage_times[0][1]
        for st_time, st_order, st_name in stage_times[1:]:
            if st_order < max_order_seen - 1:  # Allow some flexibility
                violations.append(f"{st_name} at {st_time.date()} after stage order {max_order_seen}")
            max_order_seen = max(max_order_seen, st_order)
    
    # Collect unique stages
    unique_stages = set()
    for p in cohort:
        for _, stage_name in p.stages:
            unique_stages.add(stage_name)
    
    aquamind_stages = set()
    for p in cohort:
        if p.aquamind_stage:
            aquamind_stages.add(p.aquamind_stage)
    
    result = {
        "valid": len(violations) == 0 and span_days < 900,  # ~2.5 years max
        "population_count": len(cohort),
        "span_days": span_days,
        "min_date": min_time.date().isoformat(),
        "max_date": max_time.date().isoformat(),
        "fishtalk_stages": sorted(unique_stages),
        "aquamind_stages": sorted(aquamind_stages),
        "violations": violations[:5],  # Limit to first 5
    }
    
    if span_days > 900:
        result["reason"] = f"Span too long: {span_days} days"
    elif violations:
        result["reason"] = f"Stage violations: {len(violations)}"
    
    return result


def print_population_timeline(populations: list[Population], limit: int = 50):
    """Print a timeline of populations sorted by start time."""
    sorted_pops = sorted(
        [p for p in populations if p.start_time],
        key=lambda p: p.start_time
    )
    
    print(f"\n{'='*80}")
    print("POPULATION TIMELINE (sorted by start time)")
    print(f"{'='*80}")
    print(f"{'Start Date':<12} {'End Date':<12} {'Stage':<15} {'AquaMind':<12} {'PopID (first 8)'}")
    print("-" * 80)
    
    for pop in sorted_pops[:limit]:
        start = pop.start_time.date().isoformat() if pop.start_time else "?"
        end = pop.end_time.date().isoformat() if pop.end_time else "ongoing"
        stage = pop.first_stage or "?"
        aqua_stage = pop.aquamind_stage or "?"
        pop_short = pop.population_id[:8]
        print(f"{start:<12} {end:<12} {stage:<15} {aqua_stage:<12} {pop_short}")
    
    if len(sorted_pops) > limit:
        print(f"... and {len(sorted_pops) - limit} more populations")


def print_cohort_analysis(cohorts: list[list[Population]], method: str):
    """Print analysis of cohort splitting results."""
    print(f"\n{'='*80}")
    print(f"COHORT ANALYSIS: {method}")
    print(f"{'='*80}")
    print(f"Total cohorts: {len(cohorts)}")
    
    for i, cohort in enumerate(cohorts, 1):
        validation = validate_cohort(cohort)
        status = "✓ VALID" if validation["valid"] else "✗ INVALID"
        
        print(f"\nCohort {i}: {status}")
        print(f"  Populations: {validation['population_count']}")
        print(f"  Time span: {validation['min_date']} to {validation['max_date']} ({validation['span_days']} days)")
        print(f"  FishTalk stages: {', '.join(validation['fishtalk_stages'])}")
        print(f"  AquaMind stages: {', '.join(validation['aquamind_stages'])}")
        
        if validation.get("violations"):
            print(f"  Violations: {validation['violations'][:3]}")
        if validation.get("reason"):
            print(f"  Reason: {validation['reason']}")


def main():
    parser = argparse.ArgumentParser(description="Analyze batch cohorts for a project tuple")
    parser.add_argument("--project-key", required=True, help="Project key in X/Y/Z format (e.g., 1/24/58)")
    parser.add_argument("--gap-days", type=int, default=90, help="Gap threshold for time-based splitting")
    parser.add_argument("--window-days", type=int, default=120, help="Window for stage+time splitting")
    args = parser.parse_args()
    
    print(f"\n{'#'*80}")
    print(f"# BATCH COHORT ANALYSIS: {args.project_key}")
    print(f"{'#'*80}")
    
    # Load data
    print("\nLoading data...")
    stage_names = load_stage_names()
    print(f"  Loaded {len(stage_names)} stage definitions")
    
    stages_by_pop = load_population_stages(stage_names)
    print(f"  Loaded stages for {len(stages_by_pop)} populations")
    
    populations = load_populations_for_project(args.project_key, stages_by_pop)
    print(f"  Found {len(populations)} populations for project {args.project_key}")
    
    if not populations:
        print("ERROR: No populations found for this project key")
        return 1
    
    # Load transfers for origin detection
    transfers = load_subtransfers()
    print(f"  Loaded {len(transfers)} source populations with transfers")
    
    # Basic stats
    pops_with_time = [p for p in populations if p.start_time]
    if pops_with_time:
        min_start = min(p.start_time for p in pops_with_time)
        max_end = max(p.end_time or p.start_time for p in pops_with_time)
        total_span = (max_end - min_start).days
        print(f"\n  Total time span: {min_start.date()} to {max_end.date()} ({total_span} days)")
    
    # Stage distribution
    stage_counts = defaultdict(int)
    for pop in populations:
        if pop.first_stage:
            stage_counts[pop.first_stage] += 1
    
    print(f"\n  Stage distribution (first stage per population):")
    for stage in sorted(stage_counts.keys(), key=lambda s: STAGE_ORDER.get(s, 99)):
        print(f"    {stage}: {stage_counts[stage]}")
    
    # Print timeline
    print_population_timeline(populations)
    
    # Find origin populations
    origins = find_origin_populations(populations, transfers)
    print(f"\n{'='*80}")
    print("ORIGIN POPULATIONS (no incoming transfers)")
    print(f"{'='*80}")
    print(f"Found {len(origins)} origin populations:")
    for pop in sorted(origins, key=lambda p: p.start_time or datetime.max)[:20]:
        start = pop.start_time.date().isoformat() if pop.start_time else "?"
        stage = pop.first_stage or "?"
        print(f"  {start} | {stage:<15} | {pop.population_id[:8]}")
    
    # Test cohort splitting approaches
    
    # 1. Time-gap based splitting
    cohorts_time = cohort_split_by_time_gap(populations, args.gap_days)
    print_cohort_analysis(cohorts_time, f"Time Gap ({args.gap_days} days)")
    
    # 2. Stage + Time based splitting
    cohorts_stage = cohort_split_by_stage_and_time(populations, args.window_days)
    print_cohort_analysis(cohorts_stage, f"Stage + Time (window={args.window_days} days)")
    
    # Summary and recommendations
    print(f"\n{'='*80}")
    print("SUMMARY AND RECOMMENDATIONS")
    print(f"{'='*80}")
    
    valid_time_cohorts = sum(1 for c in cohorts_time if validate_cohort(c)["valid"])
    valid_stage_cohorts = sum(1 for c in cohorts_stage if validate_cohort(c)["valid"])
    
    print(f"Time-gap splitting: {valid_time_cohorts}/{len(cohorts_time)} valid cohorts")
    print(f"Stage+time splitting: {valid_stage_cohorts}/{len(cohorts_stage)} valid cohorts")
    
    if valid_stage_cohorts > valid_time_cohorts:
        print("\nRECOMMENDATION: Use stage+time cohort splitting")
    elif valid_time_cohorts > 0:
        print("\nRECOMMENDATION: Use time-gap cohort splitting")
    else:
        print("\nWARNING: Neither approach produces fully valid cohorts")
        print("Consider investigating SubTransfers chains for lineage tracing")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
