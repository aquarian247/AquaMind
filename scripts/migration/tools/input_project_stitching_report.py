#!/usr/bin/env python3
"""Build input-project-based batch stitching report from CSV extracts.

This report uses InputProjects + FishGroupHistory to include *all* populations
linked to an input project (not just Ext_Inputs_v2 rows), so the batch has full
history from earliest egg placement.

Outputs (compatible with pilot_migrate_input_batch.py):
  - input_batches.csv
  - input_population_members.csv
  - input_records.csv (from ext_inputs, optional metadata)
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

AQUAMIND_STAGES_ORDERED = ["Egg&Alevin", "Fry", "Parr", "Smolt", "Post-Smolt", "Adult"]
STAGE_ORDER = {stage: i for i, stage in enumerate(AQUAMIND_STAGES_ORDERED)}

FAROE_SITE_KEYWORDS = {"north", "south", "west", "east", "faroe", "føroyar", "streymoy"}
SCOTLAND_SITE_KEYWORDS = {"scotland", "scottish", "uk", "loch"}


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_float(value: str) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def fishtalk_stage_to_aquamind(stage_name: str) -> str | None:
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


def determine_geography(site_name: str, site_group: str | None = None) -> str:
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@dataclass
class InputBatch:
    batch_key: str
    input_name: str
    input_number: str
    year_class: str
    populations: list[dict[str, str]] = field(default_factory=list)
    aquamind_stages: set[str] = field(default_factory=set)
    geographies: set[str] = field(default_factory=set)
    earliest_start: datetime | None = None
    latest_activity: datetime | None = None
    total_fish: float = 0.0
    total_biomass: float = 0.0
    validation_issues: list[str] = field(default_factory=list)

    @property
    def span_days(self) -> int:
        if self.earliest_start and self.latest_activity:
            return (self.latest_activity - self.earliest_start).days
        return 0

    @property
    def has_single_geography(self) -> bool:
        known = {g for g in self.geographies if g != "Unknown"}
        return len(known) <= 1

    @property
    def has_fw_and_sea(self) -> bool:
        fw = {"Egg&Alevin", "Fry", "Parr", "Smolt"}
        sea = {"Post-Smolt", "Adult"}
        return bool(self.aquamind_stages & fw) and bool(self.aquamind_stages & sea)

    @property
    def stage_coverage_count(self) -> int:
        return len(self.aquamind_stages)

    @property
    def is_valid(self) -> bool:
        return self.has_single_geography


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Input-project stitching report from CSV extracts")
    parser.add_argument(
        "--extract-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"),
        help="Directory containing extracted CSV files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "output" / "input_stitching"),
        help="Directory to write output CSV files",
    )
    parser.add_argument(
        "--since",
        help="Only include input projects whose earliest population start >= YYYY-MM-DD",
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
        help="Maximum time span in days for validation (default: 900)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    extract_dir = Path(args.extract_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    since_dt = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None

    input_projects = read_csv(extract_dir / "input_projects.csv")
    fish_group_history = read_csv(extract_dir / "fish_group_history.csv")
    populations = read_csv(extract_dir / "populations.csv")
    containers = read_csv(extract_dir / "containers.csv")
    org_units = read_csv(extract_dir / "org_units.csv")
    grouped_org = read_csv(extract_dir / "grouped_organisation.csv")
    stage_events = read_csv(extract_dir / "population_stages.csv")
    stage_defs = read_csv(extract_dir / "production_stages.csv")
    ext_inputs = read_csv(extract_dir / "ext_inputs.csv")

    pop_by_id = {row.get("PopulationID", ""): row for row in populations}
    container_by_id = {row.get("ContainerID", ""): row for row in containers}
    org_by_id = {row.get("OrgUnitID", ""): row for row in org_units}
    geo_by_container = {
        row.get("ContainerID", ""): (row.get("Site", "") or "", row.get("SiteGroup", "") or "")
        for row in grouped_org
    }
    stage_name_by_id = {row.get("StageID", ""): (row.get("StageName") or "").strip() for row in stage_defs}

    stages_by_pop: dict[str, list[tuple[datetime, str]]] = {}
    for row in stage_events:
        pop_id = row.get("PopulationID", "")
        stage_id = row.get("StageID", "")
        stage_name = stage_name_by_id.get(stage_id, "")
        ts = parse_dt(row.get("StartTime", ""))
        if not pop_id or not stage_name or ts is None:
            continue
        stages_by_pop.setdefault(pop_id, []).append((ts, stage_name))

    for pop_id in stages_by_pop:
        stages_by_pop[pop_id].sort(key=lambda x: x[0])

    pop_ids_by_project: dict[str, list[str]] = {}
    for row in fish_group_history:
        proj_id = row.get("InputProjectID", "")
        pop_id = row.get("PopulationID", "")
        if proj_id and pop_id:
            pop_ids_by_project.setdefault(proj_id, []).append(pop_id)

    inputs_by_pop: dict[str, list[dict[str, str]]] = {}
    for row in ext_inputs:
        pop_id = row.get("PopulationID", "")
        if not pop_id:
            continue
        inputs_by_pop.setdefault(pop_id, []).append(row)

    batches: list[InputBatch] = []
    pop_rows: list[dict[str, object]] = []
    input_rows: list[dict[str, object]] = []

    base_key_counts: dict[str, int] = {}
    for proj in input_projects:
        base_name = (proj.get("ProjectName") or "").strip()
        base_number = (proj.get("ProjectNumber") or "").strip()
        base_year = (proj.get("YearClass") or "").strip()
        base_key = f"{base_name}|{base_number}|{base_year}"
        base_key_counts[base_key] = base_key_counts.get(base_key, 0) + 1

    for proj in input_projects:
        proj_id = proj.get("InputProjectID", "")
        if not proj_id:
            continue

        pop_ids = pop_ids_by_project.get(proj_id, [])
        if not pop_ids:
            continue

        input_name = (proj.get("ProjectName") or "").strip()
        input_number = (proj.get("ProjectNumber") or "").strip()
        year_class = (proj.get("YearClass") or "").strip()
        base_key = f"{input_name}|{input_number}|{year_class}"
        if base_key_counts.get(base_key, 0) > 1:
            batch_key = f"{base_key}|{proj_id}"
        else:
            batch_key = base_key

        batch = InputBatch(
            batch_key=batch_key,
            input_name=input_name,
            input_number=input_number,
            year_class=year_class,
        )

        starts: list[datetime] = []
        ends: list[datetime] = []

        for pop_id in pop_ids:
            pop_row = pop_by_id.get(pop_id, {})
            container_id = pop_row.get("ContainerID", "") or ""
            start_time = parse_dt(pop_row.get("StartTime", ""))
            end_time = parse_dt(pop_row.get("EndTime", ""))

            if start_time is None:
                continue

            container_row = container_by_id.get(container_id, {})
            org_unit_id = container_row.get("OrgUnitID", "") or ""
            org_name = (org_by_id.get(org_unit_id, {}).get("Name", "") or "").strip()
            container_name = (container_row.get("ContainerName", "") or "").strip()

            site_name, site_group = geo_by_container.get(container_id, ("", ""))
            geography = determine_geography(site_name, site_group)

            stage_list = [name for _, name in stages_by_pop.get(pop_id, [])]
            aquamind = []
            for stage in stage_list:
                mapped = fishtalk_stage_to_aquamind(stage)
                if mapped and mapped not in aquamind:
                    aquamind.append(mapped)

            fishtalk_stages_str = ", ".join(stage_list)
            aquamind_stages_str = ", ".join(aquamind)

            pop_rows.append(
                {
                    "batch_key": batch_key,
                    "population_id": pop_id,
                    "container_id": container_id,
                    "container_name": container_name,
                    "org_unit_name": org_name,
                    "geography": geography,
                    "start_time": start_time.isoformat(sep=" "),
                    "end_time": end_time.isoformat(sep=" ") if end_time else "",
                    "fishtalk_stages": fishtalk_stages_str,
                    "aquamind_stages": aquamind_stages_str,
                }
            )

            batch.geographies.add(geography)
            batch.aquamind_stages.update(aquamind)
            starts.append(start_time)
            if end_time:
                ends.append(end_time)

            for inp in inputs_by_pop.get(pop_id, []):
                input_rows.append(
                    {
                        "batch_key": batch_key,
                        "population_id": pop_id,
                        "input_name": inp.get("InputName", ""),
                        "input_number": inp.get("InputNumber", ""),
                        "year_class": inp.get("YearClass", ""),
                        "supplier_id": inp.get("SupplierID", ""),
                        "start_time": inp.get("StartTime", ""),
                        "input_count": inp.get("InputCount", ""),
                        "input_biomass_kg": inp.get("InputBiomass", ""),
                        "fish_type": inp.get("FishType", ""),
                        "broodstock": inp.get("Broodstock", ""),
                    }
                )

                batch.total_fish += parse_float(inp.get("InputCount", "0"))
                batch.total_biomass += parse_float(inp.get("InputBiomass", "0"))

        if not starts:
            continue

        batch.earliest_start = min(starts)
        batch.latest_activity = max(ends) if ends else max(starts)

        if since_dt and batch.earliest_start < since_dt:
            continue

        if batch.total_fish < args.min_fish:
            batch.validation_issues.append(
                f"Low fish count: {batch.total_fish:,.0f} (expected >= {args.min_fish:,})"
            )

        if batch.span_days > args.max_span_days:
            batch.validation_issues.append(
                f"Span too long: {batch.span_days} days (max {args.max_span_days})"
            )

        batches.append(batch)

    batch_rows: list[dict[str, object]] = []
    for batch in batches:
        stages_str = ", ".join(s for s in AQUAMIND_STAGES_ORDERED if s in batch.aquamind_stages)
        geos_str = ", ".join(sorted(batch.geographies))
        issues_str = "; ".join(batch.validation_issues) if batch.validation_issues else ""

        batch_rows.append(
            {
                "batch_key": batch.batch_key,
                "input_name": batch.input_name,
                "input_number": batch.input_number,
                "year_class": batch.year_class,
                "population_count": sum(1 for row in pop_rows if row["batch_key"] == batch.batch_key),
                "total_fish": f"{batch.total_fish:,.0f}",
                "total_biomass_kg": f"{batch.total_biomass:,.2f}",
                "span_days": batch.span_days,
                "aquamind_stages": stages_str,
                "stage_count": batch.stage_coverage_count,
                "geographies": geos_str,
                "has_single_geography": batch.has_single_geography,
                "has_fw_and_sea": batch.has_fw_and_sea,
                "is_active": True if batch.latest_activity else False,
                "is_valid": batch.is_valid and batch.span_days <= args.max_span_days,
                "validation_issues": issues_str,
                "earliest_start": batch.earliest_start.isoformat(sep=" ") if batch.earliest_start else "",
                "latest_activity": batch.latest_activity.isoformat(sep=" ") if batch.latest_activity else "",
            }
        )

    def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in fieldnames})

    write_csv(
        output_dir / "input_batches.csv",
        fieldnames=[
            "batch_key",
            "input_name",
            "input_number",
            "year_class",
            "population_count",
            "total_fish",
            "total_biomass_kg",
            "span_days",
            "aquamind_stages",
            "stage_count",
            "geographies",
            "has_single_geography",
            "has_fw_and_sea",
            "is_active",
            "is_valid",
            "validation_issues",
            "earliest_start",
            "latest_activity",
        ],
        rows=batch_rows,
    )

    write_csv(
        output_dir / "input_population_members.csv",
        fieldnames=[
            "batch_key",
            "population_id",
            "container_id",
            "container_name",
            "org_unit_name",
            "geography",
            "start_time",
            "end_time",
            "fishtalk_stages",
            "aquamind_stages",
        ],
        rows=pop_rows,
    )

    write_csv(
        output_dir / "input_records.csv",
        fieldnames=[
            "batch_key",
            "population_id",
            "input_name",
            "input_number",
            "year_class",
            "supplier_id",
            "start_time",
            "input_count",
            "input_biomass_kg",
            "fish_type",
            "broodstock",
        ],
        rows=input_rows,
    )

    print(f"Wrote {output_dir / 'input_batches.csv'}")
    print(f"Wrote {output_dir / 'input_population_members.csv'}")
    print(f"Wrote {output_dir / 'input_records.csv'}")
    print(f"Input projects processed: {len(batches):,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
