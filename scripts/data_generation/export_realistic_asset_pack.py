#!/usr/bin/env python3
# flake8: noqa
"""
Export migrated infrastructure and naming references for realistic test data generation.

This script produces a machine-readable reference pack that another agent/session can
consume when updating data generation scripts to use familiar migrated assets.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.db.models import Count, Q, Sum


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

import django  # noqa: E402

django.setup()

from apps.batch.models import Batch  # noqa: E402
from apps.batch.models.assignment import BatchContainerAssignment  # noqa: E402
from apps.infrastructure.models import (  # noqa: E402
    Area,
    Container,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.migration_support.models import ExternalIdMap  # noqa: E402


STATIC_HALL_STAGE_MAPS: dict[str, dict[str, str]] = {
    "S24 Strond": {
        "A H\u00d8LL": "Egg&Alevin",
        "B H\u00d8LL": "Fry",
        "C H\u00d8LL": "Parr",
        "D H\u00d8LL": "Parr",
        "E H\u00d8LL": "Smolt",
        "F H\u00d8LL": "Smolt",
        "G H\u00d8LL": "Post-Smolt",
        "H H\u00d8LL": "Post-Smolt",
        "I H\u00d8LL": "Post-Smolt",
        "J H\u00d8LL": "Post-Smolt",
    },
    "S03 Nor\u00f0toftir": {
        "KLEKING": "Egg&Alevin",
        "5 M H\u00d8LL": "Fry",
        "11 H\u00d8LL A": "Smolt",
        "11 H\u00d8LL B": "Smolt",
        "18 H\u00d8LL A": "Post-Smolt",
        "18 H\u00d8LL B": "Post-Smolt",
        "800 H\u00d8LL": "Parr",
        "900 H\u00d8LL": "Parr",
    },
    "S08 Gj\u00f3gv": {
        "KLEKING": "Egg&Alevin",
        "STARTF\u00d3\u00d0RING": "Fry",
        "T-H\u00d8LL": "Post-Smolt",
    },
    "S16 Glyvradalur": {
        "A H\u00d8LL": "Egg&Alevin",
        "B H\u00d8LL": "Fry",
        "C H\u00d8LL": "Parr",
        "D H\u00d8LL": "Smolt",
        "E1 H\u00d8LL": "Post-Smolt",
        "E2 H\u00d8LL": "Post-Smolt",
        "KLEKIH\u00d8LL": "Egg&Alevin",
        "STARTF\u00d3\u00d0RINGSH\u00d8LL": "Fry",
    },
    "S21 Vi\u00f0arei\u00f0i": {
        "5M": "Fry",
        "A": "Parr",
        "BA": "Parr",
        "BB": "Parr",
        "C": "Smolt",
        "D": "Smolt",
        "E": "Post-Smolt",
        "F": "Post-Smolt",
        "ROGN": "Egg&Alevin",
    },
    "FW22 Applecross": {
        "A1": "Egg&Alevin",
        "A2": "Egg&Alevin",
        "B1": "Fry",
        "B2": "Fry",
        "C1": "Parr",
        "C2": "Parr",
        "D1": "Smolt",
        "D2": "Smolt",
        "E1": "Post-Smolt",
        "E2": "Post-Smolt",
    },
}


def decimal_to_str(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(Decimal("0.01")))


def clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_target_map(
    *,
    source_model: str,
    target_ids: list[int],
) -> dict[int, ExternalIdMap]:
    if not target_ids:
        return {}
    mappings = (
        ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=source_model,
            target_object_id__in=target_ids,
        )
        .order_by("updated_at")
    )
    by_target: dict[int, ExternalIdMap] = {}
    for mapping in mappings:
        by_target[int(mapping.target_object_id)] = mapping
    return by_target


def export_geographies(output_dir: Path) -> tuple[list[Geography], list[dict[str, Any]]]:
    geographies = list(Geography.objects.order_by("name"))
    rows: list[dict[str, Any]] = []
    for geo in geographies:
        rows.append(
            {
                "geography_id": geo.id,
                "name": geo.name,
                "description": geo.description or "",
                "station_count": geo.stations.count(),
                "area_count": geo.areas.count(),
            }
        )

    write_csv(
        output_dir / "infrastructure_geographies.csv",
        fieldnames=["geography_id", "name", "description", "station_count", "area_count"],
        rows=rows,
    )
    return geographies, rows


def export_stations(output_dir: Path) -> tuple[list[FreshwaterStation], list[dict[str, Any]]]:
    stations = list(
        FreshwaterStation.objects.select_related("geography").order_by("geography__name", "name")
    )
    station_maps = build_target_map(
        source_model="OrgUnit_FW",
        target_ids=[station.id for station in stations],
    )
    rows: list[dict[str, Any]] = []
    for station in stations:
        mapping = station_maps.get(int(station.id))
        rows.append(
            {
                "station_id": station.id,
                "station_name": station.name,
                "station_type": station.station_type,
                "geography": station.geography.name,
                "hall_count": station.halls.count(),
                "active": station.active,
                "latitude": str(station.latitude),
                "longitude": str(station.longitude),
                "source_orgunit_id": mapping.source_identifier if mapping else "",
            }
        )

    write_csv(
        output_dir / "infrastructure_stations.csv",
        fieldnames=[
            "station_id",
            "station_name",
            "station_type",
            "geography",
            "hall_count",
            "active",
            "latitude",
            "longitude",
            "source_orgunit_id",
        ],
        rows=rows,
    )
    return stations, rows


def export_halls(output_dir: Path) -> tuple[list[Hall], list[dict[str, Any]]]:
    halls = list(
        Hall.objects.select_related("freshwater_station__geography").order_by(
            "freshwater_station__geography__name",
            "freshwater_station__name",
            "name",
        )
    )
    rows: list[dict[str, Any]] = []
    for hall in halls:
        rows.append(
            {
                "hall_id": hall.id,
                "hall_name": hall.name,
                "station_id": hall.freshwater_station_id,
                "station_name": hall.freshwater_station.name,
                "geography": hall.freshwater_station.geography.name,
                "container_count": hall.containers.count(),
                "active": hall.active,
                "description": hall.description or "",
            }
        )

    write_csv(
        output_dir / "infrastructure_halls.csv",
        fieldnames=[
            "hall_id",
            "hall_name",
            "station_id",
            "station_name",
            "geography",
            "container_count",
            "active",
            "description",
        ],
        rows=rows,
    )
    return halls, rows


def export_areas(output_dir: Path) -> tuple[list[Area], list[dict[str, Any]]]:
    areas = list(
        Area.objects.select_related(
            "geography",
            "area_group",
            "area_group__parent",
        ).order_by("geography__name", "name")
    )
    area_maps = build_target_map(
        source_model="OrgUnit_Sea",
        target_ids=[area.id for area in areas],
    )
    rows: list[dict[str, Any]] = []
    for area in areas:
        mapping = area_maps.get(int(area.id))
        rows.append(
            {
                "area_id": area.id,
                "area_name": area.name,
                "geography": area.geography.name,
                "area_group": area.area_group.name if area.area_group_id else "",
                "area_group_parent": (
                    area.area_group.parent.name
                    if area.area_group_id and area.area_group.parent_id
                    else ""
                ),
                "container_count": area.containers.count(),
                "active": area.active,
                "latitude": str(area.latitude),
                "longitude": str(area.longitude),
                "max_biomass_kg": decimal_to_str(area.max_biomass),
                "source_orgunit_id": mapping.source_identifier if mapping else "",
            }
        )

    write_csv(
        output_dir / "infrastructure_areas.csv",
        fieldnames=[
            "area_id",
            "area_name",
            "geography",
            "area_group",
            "area_group_parent",
            "container_count",
            "active",
            "latitude",
            "longitude",
            "max_biomass_kg",
            "source_orgunit_id",
        ],
        rows=rows,
    )
    return areas, rows


def export_containers(output_dir: Path) -> tuple[list[Container], list[dict[str, Any]]]:
    containers = list(
        Container.objects.select_related(
            "container_type",
            "hall__freshwater_station__geography",
            "area__geography",
            "carrier",
            "parent_container",
        ).order_by("name")
    )
    container_maps = build_target_map(
        source_model="Containers",
        target_ids=[container.id for container in containers],
    )

    rows: list[dict[str, Any]] = []
    for container in containers:
        mapping = container_maps.get(int(container.id))
        metadata = mapping.metadata if mapping else {}
        location_context = "unknown"
        geography_name = ""
        station_name = ""
        hall_name = ""
        area_name = ""
        carrier_name = ""
        if container.hall_id:
            location_context = "hall"
            hall_name = container.hall.name
            station_name = container.hall.freshwater_station.name
            geography_name = container.hall.freshwater_station.geography.name
        elif container.area_id:
            location_context = "area"
            area_name = container.area.name
            geography_name = container.area.geography.name
        elif container.carrier_id:
            location_context = "carrier"
            carrier_name = container.carrier.name

        rows.append(
            {
                "container_id": container.id,
                "container_name": container.name,
                "container_type": container.container_type.name,
                "container_category": container.container_type.category,
                "location_context": location_context,
                "geography": geography_name,
                "station_name": station_name,
                "hall_name": hall_name,
                "area_name": area_name,
                "carrier_name": carrier_name,
                "volume_m3": decimal_to_str(container.volume_m3),
                "max_biomass_kg": decimal_to_str(container.max_biomass_kg),
                "hierarchy_role": container.hierarchy_role,
                "parent_container_id": container.parent_container_id or "",
                "parent_container_name": (
                    container.parent_container.name if container.parent_container_id else ""
                ),
                "active": container.active,
                "source_container_id": mapping.source_identifier if mapping else "",
                "source_official_id": str(metadata.get("official_id") or ""),
                "source_org_unit_id": str(metadata.get("org_unit_id") or ""),
            }
        )

    write_csv(
        output_dir / "infrastructure_containers.csv",
        fieldnames=[
            "container_id",
            "container_name",
            "container_type",
            "container_category",
            "location_context",
            "geography",
            "station_name",
            "hall_name",
            "area_name",
            "carrier_name",
            "volume_m3",
            "max_biomass_kg",
            "hierarchy_role",
            "parent_container_id",
            "parent_container_name",
            "active",
            "source_container_id",
            "source_official_id",
            "source_org_unit_id",
        ],
        rows=rows,
    )
    return containers, rows


def export_static_hall_stage_mapping(output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site_name, hall_map in STATIC_HALL_STAGE_MAPS.items():
        for hall_label, lifecycle_stage in hall_map.items():
            rows.append(
                {
                    "site_name": site_name,
                    "hall_label": hall_label,
                    "lifecycle_stage": lifecycle_stage,
                    "mapping_type": "static_tooling_map",
                }
            )

    rows.sort(key=lambda row: (row["site_name"], row["hall_label"]))
    write_csv(
        output_dir / "hall_stage_mapping_static.csv",
        fieldnames=["site_name", "hall_label", "lifecycle_stage", "mapping_type"],
        rows=rows,
    )
    return rows


def export_observed_hall_stage_mapping(output_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assignments = (
        BatchContainerAssignment.objects.select_related(
            "container__hall__freshwater_station__geography",
            "lifecycle_stage",
        )
        .filter(container__hall__isnull=False)
        .order_by("container__hall__freshwater_station__name", "container__hall__name")
    )

    hall_stats: dict[tuple[str, str, str], dict[str, Any]] = {}
    hall_stage_rows: list[dict[str, Any]] = []

    for assignment in assignments.iterator(chunk_size=2000):
        hall = assignment.container.hall
        station = hall.freshwater_station
        geography = station.geography
        lifecycle_stage = assignment.lifecycle_stage.name
        key = (geography.name, station.name, hall.name)

        if key not in hall_stats:
            hall_stats[key] = {
                "rows_total": 0,
                "population_total": 0,
                "first_assignment_date": assignment.assignment_date,
                "last_assignment_date": assignment.assignment_date,
                "stage_rows": Counter(),
                "stage_population": defaultdict(int),
            }

        stats = hall_stats[key]
        stats["rows_total"] += 1
        stats["population_total"] += int(assignment.population_count or 0)
        stats["stage_rows"][lifecycle_stage] += 1
        stats["stage_population"][lifecycle_stage] += int(assignment.population_count or 0)
        if assignment.assignment_date < stats["first_assignment_date"]:
            stats["first_assignment_date"] = assignment.assignment_date
        if assignment.assignment_date > stats["last_assignment_date"]:
            stats["last_assignment_date"] = assignment.assignment_date

    dominant_rows: list[dict[str, Any]] = []
    for (geography_name, station_name, hall_name), stats in sorted(hall_stats.items()):
        dominant_stage = ""
        dominant_stage_rows = 0
        dominant_stage_population = 0
        if stats["stage_rows"]:
            dominant_stage = sorted(
                stats["stage_rows"].keys(),
                key=lambda stage: (
                    stats["stage_rows"][stage],
                    stats["stage_population"][stage],
                    stage,
                ),
                reverse=True,
            )[0]
            dominant_stage_rows = int(stats["stage_rows"][dominant_stage])
            dominant_stage_population = int(stats["stage_population"][dominant_stage])

        stage_breakdown = {
            stage: {
                "assignment_rows": int(stats["stage_rows"][stage]),
                "population_total": int(stats["stage_population"][stage]),
            }
            for stage in sorted(stats["stage_rows"].keys())
        }

        dominant_rows.append(
            {
                "geography": geography_name,
                "station_name": station_name,
                "hall_name": hall_name,
                "dominant_lifecycle_stage": dominant_stage,
                "dominant_stage_rows": dominant_stage_rows,
                "dominant_stage_population": dominant_stage_population,
                "assignment_rows_total": int(stats["rows_total"]),
                "population_total": int(stats["population_total"]),
                "first_assignment_date": stats["first_assignment_date"],
                "last_assignment_date": stats["last_assignment_date"],
                "stage_breakdown_json": json.dumps(stage_breakdown, sort_keys=True),
            }
        )

        for stage_name, stage_rows in sorted(stats["stage_rows"].items()):
            hall_stage_rows.append(
                {
                    "geography": geography_name,
                    "station_name": station_name,
                    "hall_name": hall_name,
                    "lifecycle_stage": stage_name,
                    "assignment_rows": int(stage_rows),
                    "population_total": int(stats["stage_population"][stage_name]),
                    "is_dominant_stage": stage_name == dominant_stage,
                }
            )

    write_csv(
        output_dir / "hall_stage_mapping_observed_dominant.csv",
        fieldnames=[
            "geography",
            "station_name",
            "hall_name",
            "dominant_lifecycle_stage",
            "dominant_stage_rows",
            "dominant_stage_population",
            "assignment_rows_total",
            "population_total",
            "first_assignment_date",
            "last_assignment_date",
            "stage_breakdown_json",
        ],
        rows=dominant_rows,
    )
    write_csv(
        output_dir / "hall_stage_mapping_observed_full.csv",
        fieldnames=[
            "geography",
            "station_name",
            "hall_name",
            "lifecycle_stage",
            "assignment_rows",
            "population_total",
            "is_dominant_stage",
        ],
        rows=hall_stage_rows,
    )
    return dominant_rows, hall_stage_rows


def infer_batch_geography(batch: Batch) -> str:
    active_assignments = batch.batch_assignments.filter(is_active=True)
    assignment_qs = active_assignments if active_assignments.exists() else batch.batch_assignments.all()
    geography_counts: Counter[str] = Counter()
    for row in assignment_qs.values(
        "container__hall__freshwater_station__geography__name",
        "container__area__geography__name",
    ):
        hall_geo = row.get("container__hall__freshwater_station__geography__name")
        area_geo = row.get("container__area__geography__name")
        if hall_geo:
            geography_counts[hall_geo] += 1
        elif area_geo:
            geography_counts[area_geo] += 1
    if not geography_counts:
        return ""
    return geography_counts.most_common(1)[0][0]


def export_batch_reference(output_dir: Path, batch_limit: int) -> tuple[list[Batch], list[dict[str, Any]]]:
    batches = list(
        Batch.objects.select_related("lifecycle_stage")
        .annotate(
            total_assignments=Count("batch_assignments"),
            active_assignments=Count("batch_assignments", filter=Q(batch_assignments__is_active=True)),
            active_population=Sum(
                "batch_assignments__population_count",
                filter=Q(batch_assignments__is_active=True),
            ),
        )
        .order_by("-updated_at")[:batch_limit]
    )

    component_maps = {
        int(mapping.target_object_id): mapping
        for mapping in ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="PopulationComponent",
            target_app_label="batch",
            target_model="batch",
            target_object_id__in=[batch.id for batch in batches],
        )
    }

    rows: list[dict[str, Any]] = []
    for batch in batches:
        component_map = component_maps.get(int(batch.id))
        rows.append(
            {
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "status": batch.status,
                "lifecycle_stage": batch.lifecycle_stage.name,
                "start_date": batch.start_date,
                "actual_end_date": batch.actual_end_date or "",
                "geography_hint": infer_batch_geography(batch),
                "total_assignments": int(batch.total_assignments or 0),
                "active_assignments": int(batch.active_assignments or 0),
                "active_population": int(batch.active_population or 0),
                "source_component_key": component_map.source_identifier if component_map else "",
                "notes": batch.notes or "",
            }
        )

    write_csv(
        output_dir / "batch_name_reference.csv",
        fieldnames=[
            "batch_id",
            "batch_number",
            "status",
            "lifecycle_stage",
            "start_date",
            "actual_end_date",
            "geography_hint",
            "total_assignments",
            "active_assignments",
            "active_population",
            "source_component_key",
            "notes",
        ],
        rows=rows,
    )
    return batches, rows


def write_readme(output_dir: Path, summary: dict[str, Any]) -> None:
    readme = f"""# Realistic Asset Reference Pack

Generated at: `{summary["generated_at_utc"]}` UTC

Purpose:
- Provide familiar migrated infrastructure names and related mapping hints for test data generation updates.
- Give another agent/session a single machine-readable package to consume directly.

Files:
- `infrastructure_geographies.csv`: geography-level inventory.
- `infrastructure_stations.csv`: freshwater stations with source org-unit identifiers.
- `infrastructure_halls.csv`: halls grouped under stations.
- `infrastructure_areas.csv`: sea areas with source org-unit identifiers.
- `infrastructure_containers.csv`: containers with location context (`hall` or `area` or `carrier`), `volume_m3`, `max_biomass_kg`, and source metadata.
- `hall_stage_mapping_static.csv`: static hall->stage map used by migration tooling for known sites.
- `hall_stage_mapping_observed_dominant.csv`: dominant observed stage by hall from migrated assignment history.
- `hall_stage_mapping_observed_full.csv`: full per-hall stage distribution from assignment history.
- `batch_name_reference.csv`: recent batch names and metadata suitable for realistic naming in synthetic data scripts.
- `asset_reference_summary.json`: export counts and basic diagnostics.

Suggested consumption order for script updates:
1. Use `infrastructure_containers.csv` as the primary source of familiar names and capacities.
2. Use `hall_stage_mapping_static.csv` first where available; fall back to `hall_stage_mapping_observed_dominant.csv`.
3. Use `batch_name_reference.csv` to seed realistic batch naming and geography hints.
4. Keep generated data deterministic by pinning selected IDs/names in your config templates.

Notes:
- Some names include Faroese characters; files are UTF-8 encoded.
- `max_biomass_kg` can be zero for migrated containers when source data did not provide a value.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export migrated asset references for realistic test data generation.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "scripts" / "data_generation" / "reference_pack" / "latest"),
        help="Directory where the reference pack will be written.",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=400,
        help="Number of recent batches to include in batch_name_reference.csv",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    clean_output_dir(output_dir)

    geographies, geographies_rows = export_geographies(output_dir)
    stations, stations_rows = export_stations(output_dir)
    halls, halls_rows = export_halls(output_dir)
    areas, areas_rows = export_areas(output_dir)
    containers, containers_rows = export_containers(output_dir)
    static_map_rows = export_static_hall_stage_mapping(output_dir)
    observed_dominant_rows, observed_full_rows = export_observed_hall_stage_mapping(output_dir)
    batches, batch_rows = export_batch_reference(output_dir, batch_limit=max(args.batch_limit, 1))

    summary = {
        "generated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "output_dir": str(output_dir),
        "counts": {
            "geographies": len(geographies_rows),
            "freshwater_stations": len(stations_rows),
            "halls": len(halls_rows),
            "areas": len(areas_rows),
            "containers": len(containers_rows),
            "hall_stage_mapping_static_rows": len(static_map_rows),
            "hall_stage_mapping_observed_dominant_rows": len(observed_dominant_rows),
            "hall_stage_mapping_observed_full_rows": len(observed_full_rows),
            "batch_reference_rows": len(batch_rows),
        },
        "container_location_context_counts": dict(
            Counter(row["location_context"] for row in containers_rows)
        ),
        "active_containers": sum(1 for row in containers_rows if str(row["active"]).lower() == "true"),
        "inactive_containers": sum(1 for row in containers_rows if str(row["active"]).lower() != "true"),
        "batch_limit": int(args.batch_limit),
    }

    (output_dir / "asset_reference_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_readme(output_dir, summary)

    print("Realistic asset reference pack exported")
    print(f"Output: {output_dir}")
    print(
        "Counts: "
        f"stations={summary['counts']['freshwater_stations']}, "
        f"halls={summary['counts']['halls']}, "
        f"areas={summary['counts']['areas']}, "
        f"containers={summary['counts']['containers']}, "
        f"batch_refs={summary['counts']['batch_reference_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
