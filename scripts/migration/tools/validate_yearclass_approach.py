#!/usr/bin/env python3
"""Validate year-class extraction approach across multiple project tuples.

This script tests the year-class extraction method on a sample of project tuples
to verify it provides reliable batch identification across the dataset.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "scripts" / "migration" / "output" / "project_stitching"
PROJECT_BATCHES_CSV = OUTPUT_DIR / "project_batches.csv"
PROJECT_POPULATION_MEMBERS_CSV = OUTPUT_DIR / "project_population_members.csv"

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "mai": 5, "des": 12, "okt": 10, "mars": 3,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def extract_yearclass_from_name(name: str) -> Optional[tuple[int, int]]:
    """Extract year-class (year, month) from population name."""
    if not name:
        return None
    
    name_lower = name.lower()
    
    # Pattern 1: Parenthesized year-class like "(MAI/JUN 23)" or "(JUN 23)"
    paren_match = re.search(r'\(([a-zA-Z/]+)\s*(\d{2})\)', name)
    if paren_match:
        month_str = paren_match.group(1).split('/')[0].lower()
        year_short = int(paren_match.group(2))
        year = 2000 + year_short if year_short < 50 else 1900 + year_short
        month = MONTH_MAP.get(month_str)
        if month:
            return (year, month)
    
    # Pattern 2: Month + Year like "feb24", "Mars 2024"
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
    
    # Pattern 3: Quarter notation like "24Q1"
    quarter_match = re.search(r'(\d{2})Q([1-4])', name)
    if quarter_match:
        year_short = int(quarter_match.group(1))
        quarter = int(quarter_match.group(2))
        year = 2000 + year_short
        month = (quarter - 1) * 3 + 1
        return (year, month)
    
    # Pattern 4: Year only like "2023"
    year_only_match = re.search(r'\b(20\d{2})\b', name)
    if year_only_match:
        year = int(year_only_match.group(1))
        return (year, 1)
    
    return None


def yearclass_to_quarter(yc: Optional[tuple[int, int]]) -> Optional[str]:
    """Convert year-class to quarter string."""
    if not yc:
        return None
    year, month = yc
    quarter = (month - 1) // 3 + 1
    return f"{year}-Q{quarter}"


def main():
    print("=" * 80)
    print("YEAR-CLASS EXTRACTION VALIDATION")
    print("=" * 80)
    
    # Load population members
    populations_by_project = defaultdict(list)
    total_populations = 0
    
    with open(PROJECT_POPULATION_MEMBERS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_key = row["project_key"]
            name = row.get("population_name", "") or ""
            populations_by_project[project_key].append(name)
            total_populations += 1
    
    print(f"\nLoaded {total_populations} populations across {len(populations_by_project)} project tuples")
    
    # Load project batches for time span info
    project_spans = {}
    with open(PROJECT_BATCHES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_key = row["project_key"]
            earliest = row.get("earliest_start", "")
            latest = row.get("latest_activity", "")
            if earliest and latest:
                try:
                    start = datetime.fromisoformat(earliest.replace(" ", "T"))
                    end = datetime.fromisoformat(latest.replace(" ", "T"))
                    span_days = (end - start).days
                    project_spans[project_key] = span_days
                except:
                    pass
    
    # Analyze year-class extraction
    extraction_stats = {
        "total_pops": 0,
        "extracted": 0,
        "projects_analyzed": 0,
        "projects_single_cohort": 0,
        "projects_multi_cohort": 0,
    }
    
    cohort_counts = defaultdict(int)  # How many cohorts per project
    problematic_projects = []  # Projects with >1 cohort AND >180 day span
    
    for project_key, names in populations_by_project.items():
        extraction_stats["projects_analyzed"] += 1
        
        cohorts_in_project = set()
        extracted_count = 0
        
        for name in names:
            extraction_stats["total_pops"] += 1
            yc = extract_yearclass_from_name(name)
            if yc:
                extraction_stats["extracted"] += 1
                extracted_count += 1
                quarter = yearclass_to_quarter(yc)
                cohorts_in_project.add(quarter)
        
        num_cohorts = len(cohorts_in_project) if cohorts_in_project else 1
        cohort_counts[num_cohorts] += 1
        
        if num_cohorts == 1:
            extraction_stats["projects_single_cohort"] += 1
        else:
            extraction_stats["projects_multi_cohort"] += 1
            
            # Check if this is actually problematic (long span)
            span = project_spans.get(project_key, 0)
            if span > 180:
                problematic_projects.append({
                    "project_key": project_key,
                    "span_days": span,
                    "num_cohorts": num_cohorts,
                    "cohorts": sorted(cohorts_in_project) if cohorts_in_project else [],
                    "population_count": len(names),
                })
    
    # Print summary
    print(f"\n{'='*80}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*80}")
    
    extraction_rate = extraction_stats["extracted"] / extraction_stats["total_pops"] * 100
    print(f"\nYear-class extraction rate: {extraction_stats['extracted']}/{extraction_stats['total_pops']} ({extraction_rate:.1f}%)")
    
    print(f"\nProject tuple cohort distribution:")
    for num_cohorts in sorted(cohort_counts.keys()):
        count = cohort_counts[num_cohorts]
        pct = count / extraction_stats["projects_analyzed"] * 100
        print(f"  {num_cohorts} cohort(s): {count} projects ({pct:.1f}%)")
    
    single_cohort_rate = extraction_stats["projects_single_cohort"] / extraction_stats["projects_analyzed"] * 100
    print(f"\nSingle-cohort projects: {single_cohort_rate:.1f}% - These can be migrated as-is")
    
    print(f"\n{'='*80}")
    print("PROBLEMATIC PROJECTS (>1 cohort AND >180 day span)")
    print(f"{'='*80}")
    
    problematic_projects.sort(key=lambda x: x["span_days"], reverse=True)
    
    print(f"\nFound {len(problematic_projects)} projects that need cohort splitting:")
    for proj in problematic_projects[:20]:
        cohorts_str = ", ".join(proj["cohorts"][:4])
        if len(proj["cohorts"]) > 4:
            cohorts_str += f" +{len(proj['cohorts'])-4} more"
        print(f"  {proj['project_key']}: {proj['span_days']} days, {proj['num_cohorts']} cohorts ({cohorts_str})")
    
    if len(problematic_projects) > 20:
        print(f"  ... and {len(problematic_projects)-20} more")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if extraction_rate > 70:
        print("\n✓ Year-class extraction has good coverage (>70%)")
        print("\nImplementation strategy:")
        print("1. For single-cohort projects: Migrate directly as one batch")
        print(f"   ({extraction_stats['projects_single_cohort']} projects, {single_cohort_rate:.1f}%)")
        print("\n2. For multi-cohort projects: Split by year-class quarter")
        print(f"   ({extraction_stats['projects_multi_cohort']} projects)")
        print("\n3. For populations without extractable year-class:")
        print("   - Fall back to time-gap splitting (90-day threshold)")
        print("   - Or assign to nearest cohort by start date")
    else:
        print("\n⚠ Year-class extraction coverage is low (<70%)")
        print("Consider combining with time-gap approach")
    
    # Example batch key format
    print(f"\n{'='*80}")
    print("PROPOSED BATCH KEY FORMAT")
    print(f"{'='*80}")
    print("\nSingle-cohort project:  1/24/27")
    print("Multi-cohort project:   1/24/58:2023-Q2 (cohort suffix)")
    print("\nThis allows:")
    print("  - Direct migration of single-cohort projects (no change)")
    print("  - Explicit cohort selection for multi-cohort projects")
    print("  - Backward compatibility with existing scripts")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
