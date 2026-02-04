#!/usr/bin/env python3
"""Analyze population names to extract year-class information.

FishTalk population names often contain year-class indicators like:
- "(MAI/JUN 23)" - eggs from May/June 2023
- "(JUN 23)" - eggs from June 2023
- "(DES 23)" - eggs from December 2023
- "feb24", "Mars 2024" - reference to input date

This script analyzes these patterns to propose year-class-based cohort splitting.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EXTRACT_DIR = PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching"
POPULATIONS_CSV = EXTRACT_DIR / "populations.csv"
POPULATION_STAGES_CSV = EXTRACT_DIR / "population_stages.csv"
PRODUCTION_STAGES_CSV = EXTRACT_DIR / "production_stages.csv"
# This file has population names from the stitching report
PROJECT_POPULATION_MEMBERS_CSV = OUTPUT_DIR / "project_population_members.csv"

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
)

# Month name mappings (Faroese/Danish/Norwegian/English)
MONTH_MAP = {
    # English
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    # Scandinavian
    "mai": 5, "des": 12, "okt": 10, "mars": 3,
    # Longer forms
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
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


def extract_yearclass_from_name(name: str) -> Optional[tuple[int, int]]:
    """Extract year-class (year, month) from population name.
    
    Returns (year, month) tuple or None if not found.
    """
    if not name:
        return None
    
    name_lower = name.lower()
    
    # Pattern 1: Parenthesized year-class like "(MAI/JUN 23)" or "(JUN 23)"
    paren_match = re.search(r'\(([a-zA-Z/]+)\s*(\d{2})\)', name)
    if paren_match:
        month_str = paren_match.group(1).split('/')[0].lower()  # Take first month if range
        year_short = int(paren_match.group(2))
        year = 2000 + year_short if year_short < 50 else 1900 + year_short
        
        month = MONTH_MAP.get(month_str)
        if month:
            return (year, month)
    
    # Pattern 2: Year indicators like "feb24", "Mars 2024", "feb 2024"
    month_year_match = re.search(r'([a-zA-Z]{3,})\s*(\d{2,4})', name_lower)
    if month_year_match:
        month_str = month_year_match.group(1)
        year_str = month_year_match.group(2)
        
        month = MONTH_MAP.get(month_str)
        if month:
            year = int(year_str)
            if year < 100:
                year = 2000 + year
            return (year, month)
    
    # Pattern 3: Quarter indicators like "24Q1" or "Q1 24"
    quarter_match = re.search(r'(\d{2})Q([1-4])', name) or re.search(r'Q([1-4])\s*(\d{2})', name)
    if quarter_match:
        groups = quarter_match.groups()
        if 'Q' in name[quarter_match.start():quarter_match.end()]:
            # "24Q1" format
            if quarter_match.group(0)[0].isdigit():
                year_short = int(groups[0])
                quarter = int(groups[1])
            else:
                quarter = int(groups[0])
                year_short = int(groups[1])
        else:
            year_short = int(groups[0])
            quarter = int(groups[1])
        
        year = 2000 + year_short
        month = (quarter - 1) * 3 + 1  # Q1->1, Q2->4, Q3->7, Q4->10
        return (year, month)
    
    # Pattern 4: Just year like "NH 2023" or "2023"
    year_only_match = re.search(r'\b(20\d{2})\b', name)
    if year_only_match:
        year = int(year_only_match.group(1))
        return (year, 1)  # Default to January
    
    return None


def yearclass_to_string(yc: Optional[tuple[int, int]]) -> str:
    """Convert year-class tuple to readable string."""
    if not yc:
        return "Unknown"
    year, month = yc
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{month_names[month]} {year}"


@dataclass
class PopulationYearClass:
    population_id: str
    name: str
    start_time: Optional[datetime]
    first_stage: Optional[str]
    yearclass: Optional[tuple[int, int]]
    
    @property
    def yearclass_str(self) -> str:
        return yearclass_to_string(self.yearclass)


def load_stage_names() -> dict[str, str]:
    stage_names = {}
    with open(PRODUCTION_STAGES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_names[row["StageID"]] = row["StageName"]
    return stage_names


def load_population_stages(stage_names: dict[str, str]) -> dict[str, str]:
    """Load first stage for each population."""
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
    
    first_stage = {}
    for pop_id in stages_by_pop:
        stages_by_pop[pop_id].sort(key=lambda x: x[0])
        if stages_by_pop[pop_id]:
            first_stage[pop_id] = stages_by_pop[pop_id][0][1]
    
    return first_stage


def load_populations_for_project(project_key: str, first_stage: dict) -> list[PopulationYearClass]:
    """Load populations with year-class extraction.
    
    Uses project_population_members.csv which has population names from the stitching report.
    """
    populations = []
    
    # First try project_population_members.csv which has names
    if PROJECT_POPULATION_MEMBERS_CSV.exists():
        with open(PROJECT_POPULATION_MEMBERS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("project_key") == project_key:
                    pop_id = row["population_id"]
                    name = row.get("population_name", "") or ""
                    
                    populations.append(PopulationYearClass(
                        population_id=pop_id,
                        name=name,
                        start_time=parse_dt(row.get("start_time", "")),
                        first_stage=first_stage.get(pop_id) or row.get("fishtalk_stages", "").split(",")[0].strip() if row.get("fishtalk_stages") else None,
                        yearclass=extract_yearclass_from_name(name),
                    ))
        return populations
    
    # Fallback to populations.csv (which lacks names)
    parts = project_key.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid project key format: {project_key}")
    
    target_proj, target_year, target_run = parts
    
    with open(POPULATIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            proj = (row.get("ProjectNumber") or "").strip()
            year = (row.get("InputYear") or "").strip()
            run = (row.get("RunningNumber") or "").strip()
            
            if proj == target_proj and year == target_year and run == target_run:
                pop_id = row["PopulationID"]
                name = row.get("PopulationName", "") or ""
                
                populations.append(PopulationYearClass(
                    population_id=pop_id,
                    name=name,
                    start_time=parse_dt(row.get("StartTime", "")),
                    first_stage=first_stage.get(pop_id),
                    yearclass=extract_yearclass_from_name(name),
                ))
    
    return populations


def analyze_yearclass_distribution(populations: list[PopulationYearClass]):
    """Analyze how populations distribute across year-classes."""
    by_yearclass: dict[str, list[PopulationYearClass]] = defaultdict(list)
    
    for pop in populations:
        by_yearclass[pop.yearclass_str].append(pop)
    
    print(f"\n{'='*80}")
    print("YEAR-CLASS DISTRIBUTION")
    print(f"{'='*80}")
    
    for yc_str in sorted(by_yearclass.keys()):
        pops = by_yearclass[yc_str]
        
        # Calculate time range
        pops_with_time = [p for p in pops if p.start_time]
        if pops_with_time:
            min_time = min(p.start_time for p in pops_with_time)
            max_time = max(p.start_time for p in pops_with_time)
            time_range = f"{min_time.date()} to {max_time.date()}"
        else:
            time_range = "?"
        
        # Stage distribution
        stage_counts = defaultdict(int)
        for p in pops:
            stage_counts[p.first_stage or "?"] += 1
        stages_str = ", ".join(f"{s}:{c}" for s, c in sorted(stage_counts.items()))
        
        print(f"\n{yc_str}: {len(pops)} populations")
        print(f"  Time range: {time_range}")
        print(f"  Stages: {stages_str}")
        print(f"  Names:")
        for p in pops[:5]:
            print(f"    - {p.name}")
        if len(pops) > 5:
            print(f"    ... and {len(pops)-5} more")


def propose_yearclass_cohorts(populations: list[PopulationYearClass]) -> dict[str, list[PopulationYearClass]]:
    """Group populations by year-class for cohort splitting."""
    cohorts: dict[str, list[PopulationYearClass]] = defaultdict(list)
    
    for pop in populations:
        if pop.yearclass:
            year, month = pop.yearclass
            # Group by quarter for more practical cohorts
            quarter = (month - 1) // 3 + 1
            cohort_key = f"{year}-Q{quarter}"
        else:
            cohort_key = "Unknown"
        
        cohorts[cohort_key].append(pop)
    
    return dict(cohorts)


def validate_yearclass_cohort(cohort: list[PopulationYearClass]) -> dict:
    """Validate if a year-class cohort makes biological sense."""
    pops_with_time = [p for p in cohort if p.start_time]
    
    if not pops_with_time:
        return {"valid": False, "reason": "No timestamps"}
    
    min_time = min(p.start_time for p in pops_with_time)
    max_time = max(p.start_time for p in pops_with_time)
    span_days = (max_time - min_time).days
    
    # Check for stage progression issues
    stage_order = {
        "Egg": 0, "Green egg": 0, "Eye-egg": 0,
        "Sac Fry/Alevin": 1, "Alevin": 1,
        "Fry": 2, "Parr": 3, "Smolt": 4, "Large Smolt": 4,
        "Ongrowing": 5, "Grower": 5, "Grilse": 5,
    }
    
    stage_by_time = []
    for p in pops_with_time:
        if p.first_stage:
            order = stage_order.get(p.first_stage, 99)
            stage_by_time.append((p.start_time, order, p.first_stage))
    
    stage_by_time.sort(key=lambda x: x[0])
    
    violations = []
    if len(stage_by_time) > 1:
        max_order_seen = stage_by_time[0][1]
        for st_time, st_order, st_name in stage_by_time[1:]:
            if st_order < max_order_seen - 1:  # Earlier stage appearing later
                violations.append(f"{st_name} at {st_time.date()}")
            max_order_seen = max(max_order_seen, st_order)
    
    return {
        "valid": len(violations) == 0 and span_days < 900,
        "population_count": len(cohort),
        "span_days": span_days,
        "min_date": min_time.date().isoformat(),
        "max_date": max_time.date().isoformat(),
        "violations": violations[:3],
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze year-class from population names")
    parser.add_argument("--project-key", required=True, help="Project key in X/Y/Z format")
    args = parser.parse_args()
    
    print(f"\n{'#'*80}")
    print(f"# YEAR-CLASS ANALYSIS: {args.project_key}")
    print(f"{'#'*80}")
    
    # Load data
    print("\nLoading data...")
    stage_names = load_stage_names()
    first_stage = load_population_stages(stage_names)
    populations = load_populations_for_project(args.project_key, first_stage)
    
    print(f"  Found {len(populations)} populations")
    
    # Test year-class extraction
    print(f"\n{'='*80}")
    print("YEAR-CLASS EXTRACTION TEST")
    print(f"{'='*80}")
    
    extracted = sum(1 for p in populations if p.yearclass)
    print(f"Successfully extracted year-class: {extracted}/{len(populations)} ({100*extracted/len(populations):.0f}%)")
    
    print("\nSample extractions:")
    for pop in populations[:10]:
        yc = pop.yearclass_str
        print(f"  '{pop.name}' -> {yc}")
    
    # Analyze distribution
    analyze_yearclass_distribution(populations)
    
    # Propose cohorts
    cohorts = propose_yearclass_cohorts(populations)
    
    print(f"\n{'='*80}")
    print("PROPOSED YEAR-CLASS COHORTS")
    print(f"{'='*80}")
    print(f"Total cohorts: {len(cohorts)}")
    
    for cohort_key in sorted(cohorts.keys()):
        pops = cohorts[cohort_key]
        validation = validate_yearclass_cohort(pops)
        status = "✓ VALID" if validation["valid"] else "✗ INVALID"
        
        print(f"\n{cohort_key}: {status}")
        print(f"  Populations: {validation['population_count']}")
        print(f"  Time span: {validation.get('min_date', '?')} to {validation.get('max_date', '?')} ({validation.get('span_days', '?')} days)")
        
        if validation.get("violations"):
            print(f"  Violations: {validation['violations']}")
    
    # Summary
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}")
    
    valid_cohorts = sum(1 for k, v in cohorts.items() if validate_yearclass_cohort(v)["valid"])
    print(f"Valid cohorts: {valid_cohorts}/{len(cohorts)}")
    
    if extracted > len(populations) * 0.7:
        print("\nYear-class extraction has good coverage (>70%).")
        print("RECOMMENDATION: Use year-class from population names for cohort splitting.")
        print("\nImplementation approach:")
        print("1. Parse (MONTH YY) pattern from population names")
        print("2. Group populations by year+quarter")
        print("3. Validate stage progression within each cohort")
        print("4. Split invalid cohorts further by time gaps")
    else:
        print("\nYear-class extraction has low coverage (<70%).")
        print("Consider combining with time-gap splitting for populations without year-class.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
