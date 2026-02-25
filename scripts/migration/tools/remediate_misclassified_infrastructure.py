#!/usr/bin/env python3
"""Remediate misclassified marine containers under freshwater stations.

This tool addresses legacy migration runs where marine sites (for example A* in
Faroe context) were materialized as FreshwaterStation/Hall instead of Area.
It is intentionally migration-tooling only and keeps runtime FishTalk-agnostic.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.safety import (  # noqa: E402
    assert_default_db_is_migration_db,
    configure_migration_environment,
)

configure_migration_environment()

import django  # noqa: E402

django.setup()
assert_default_db_is_migration_db()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402

from apps.infrastructure.models import (  # noqa: E402
    Area,
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.migration_support.models import ExternalIdMap  # noqa: E402
from scripts.migration.history import save_with_history  # noqa: E402
from scripts.migration.loaders.infrastructure import (  # noqa: E402
    infer_bucket_from_grouping,
    normalize_label,
    resolve_site_grouping,
)

SITE_CODE_RE = re.compile(r"\b([A-Za-z]+[0-9]{1,3})\b")
GUID_NAME_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)


@dataclass
class MovePlan:
    container_id: int
    container_name: str
    source_container_id: str
    from_hall_id: int
    from_hall_name: str
    from_station_id: int
    from_station_name: str
    source_site: str
    source_site_group: str
    source_prod_stage: str
    target_geography: str
    target_area_name: str


@dataclass
class StationGeographyPlan:
    station_id: int
    station_name: str
    from_geography: str
    to_geography: str
    evidence_votes: int
    evidence_total: int


@dataclass
class HallCollapsePlan:
    source_hall_id: int
    source_hall_name: str
    target_hall_name: str
    station_id: int
    station_name: str
    container_count: int


def parse_site_code(site_name: str | None) -> str:
    label = normalize_label(site_name)
    if not label:
        return ""
    match = SITE_CODE_RE.search(label)
    return match.group(1).upper() if match else ""


def load_grouped_organisation(csv_dir: Path) -> dict[str, dict[str, str]]:
    path = csv_dir / "grouped_organisation.csv"
    grouped: dict[str, dict[str, str]] = {}
    if not path.exists():
        return grouped

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            container_id = (row.get("ContainerID") or "").strip()
            if not container_id:
                continue
            existing = grouped.get(container_id)
            current_score = int(bool((row.get("Site") or "").strip())) + int(
                bool((row.get("ProdStage") or "").strip())
            )
            if existing is not None:
                existing_score = int(bool(existing.get("Site"))) + int(bool(existing.get("ProdStage")))
                if existing_score >= current_score:
                    continue
            grouped[container_id] = {
                "Site": (row.get("Site") or "").strip(),
                "SiteGroup": (row.get("SiteGroup") or "").strip(),
                "ProdStage": (row.get("ProdStage") or "").strip(),
                "ContainerGroup": (row.get("ContainerGroup") or "").strip(),
                "ContainerGroupID": (row.get("ContainerGroupID") or "").strip(),
                "StandName": (row.get("StandName") or "").strip(),
                "StandID": (row.get("StandID") or "").strip(),
            }
    return grouped


def build_container_external_map() -> dict[int, ExternalIdMap]:
    by_target: dict[int, ExternalIdMap] = {}
    qs = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="Containers",
    ).order_by("updated_at")
    for mapping in qs.iterator():
        by_target[int(mapping.target_object_id)] = mapping
    return by_target


def resolve_target_geography(site: str, site_group: str, fallback_geography: str) -> str:
    geo_name, _ = resolve_site_grouping(site, site_group)
    if geo_name:
        return geo_name
    site_code = parse_site_code(site)
    if site_code.startswith("A"):
        return "Faroe Islands"
    return fallback_geography


def build_move_plan(
    *,
    csv_dir: Path,
) -> tuple[list[MovePlan], dict[str, int]]:
    grouped = load_grouped_organisation(csv_dir)
    ext_by_target = build_container_external_map()
    stats = {
        "hall_containers_scanned": 0,
        "without_external_map": 0,
        "without_grouped_org_row": 0,
        "inferred_sea_bucket": 0,
        "already_area_or_carrier": 0,
    }

    plans: list[MovePlan] = []
    containers = (
        Container.objects.select_related("hall__freshwater_station__geography")
        .filter(hall__isnull=False, area__isnull=True, carrier__isnull=True)
        .order_by("id")
    )
    for container in containers.iterator():
        stats["hall_containers_scanned"] += 1
        mapping = ext_by_target.get(int(container.id))
        if mapping is None:
            stats["without_external_map"] += 1
            continue
        source_container_id = (mapping.source_identifier or "").strip()
        if not source_container_id:
            stats["without_external_map"] += 1
            continue
        grouping = grouped.get(source_container_id)
        if grouping is None:
            stats["without_grouped_org_row"] += 1
            continue

        source_site = grouping.get("Site") or ""
        source_prod_stage = grouping.get("ProdStage") or ""
        inferred_bucket = infer_bucket_from_grouping(
            source_site,
            source_prod_stage,
        )
        if inferred_bucket != "sea":
            continue

        stats["inferred_sea_bucket"] += 1
        station = container.hall.freshwater_station
        target_geo = resolve_target_geography(
            source_site,
            grouping.get("SiteGroup") or "",
            station.geography.name,
        )
        target_area_name = normalize_label(source_site) or station.name
        plans.append(
            MovePlan(
                container_id=int(container.id),
                container_name=container.name,
                source_container_id=source_container_id,
                from_hall_id=int(container.hall_id),
                from_hall_name=container.hall.name,
                from_station_id=int(station.id),
                from_station_name=station.name,
                source_site=source_site,
                source_site_group=grouping.get("SiteGroup") or "",
                source_prod_stage=source_prod_stage,
                target_geography=target_geo,
                target_area_name=target_area_name,
            )
        )

    return plans, stats


def build_station_geography_plan(
    *,
    csv_dir: Path,
) -> tuple[list[StationGeographyPlan], dict[str, int]]:
    grouped = load_grouped_organisation(csv_dir)
    ext_by_target = build_container_external_map()
    stats = {
        "station_geo_hall_containers_scanned": 0,
        "station_geo_without_external_map": 0,
        "station_geo_without_grouped_org_row": 0,
        "station_geo_with_resolved_votes": 0,
    }
    votes_by_station: dict[int, Counter[str]] = defaultdict(Counter)

    containers = (
        Container.objects.select_related("hall__freshwater_station__geography")
        .filter(hall__isnull=False, area__isnull=True, carrier__isnull=True)
        .order_by("id")
    )
    for container in containers.iterator():
        stats["station_geo_hall_containers_scanned"] += 1
        mapping = ext_by_target.get(int(container.id))
        if mapping is None:
            stats["station_geo_without_external_map"] += 1
            continue
        source_container_id = (mapping.source_identifier or "").strip()
        if not source_container_id:
            stats["station_geo_without_external_map"] += 1
            continue
        grouping = grouped.get(source_container_id)
        if grouping is None:
            stats["station_geo_without_grouped_org_row"] += 1
            continue
        target_geo = resolve_target_geography(
            grouping.get("Site") or "",
            grouping.get("SiteGroup") or "",
            "",
        )
        if not target_geo:
            continue
        station_id = int(container.hall.freshwater_station_id)
        votes_by_station[station_id][target_geo] += 1
        stats["station_geo_with_resolved_votes"] += 1

    plans: list[StationGeographyPlan] = []
    for station_id, votes in votes_by_station.items():
        station = FreshwaterStation.objects.select_related("geography").filter(pk=station_id).first()
        if station is None:
            continue
        top_geo, top_votes = votes.most_common(1)[0]
        total_votes = sum(votes.values())
        # Only auto-reassign on unanimous evidence to avoid accidental geo drift.
        if total_votes <= 0 or top_votes != total_votes:
            continue
        if station.geography.name == top_geo:
            continue
        plans.append(
            StationGeographyPlan(
                station_id=station_id,
                station_name=station.name,
                from_geography=station.geography.name,
                to_geography=top_geo,
                evidence_votes=top_votes,
                evidence_total=total_votes,
            )
        )
    return plans, stats


def collapse_target_hall_name(hall_name: str) -> str:
    base = normalize_label(hall_name.split(";", 1)[0])
    return base[:100]


def build_hall_collapse_plan() -> tuple[list[HallCollapsePlan], dict[str, int]]:
    semicolon_qs = Hall.objects.filter(name__contains=";")
    stats = {
        "hall_semicolon_total": semicolon_qs.count(),
        "hall_semicolon_empty_or_orphaned": 0,
        "hall_collapse_candidates": 0,
        "hall_collapse_candidate_containers": 0,
    }
    plans: list[HallCollapsePlan] = []
    qs = semicolon_qs.select_related("freshwater_station").order_by("id")
    for hall in qs.iterator():
        target_name = collapse_target_hall_name(hall.name)
        if not target_name or target_name == hall.name:
            continue
        container_count = hall.containers.count()
        has_feed = hall.feed_containers.exists()
        if container_count <= 0 and not has_feed:
            stats["hall_semicolon_empty_or_orphaned"] += 1
            continue
        stats["hall_collapse_candidates"] += 1
        stats["hall_collapse_candidate_containers"] += container_count
        plans.append(
            HallCollapsePlan(
                source_hall_id=int(hall.id),
                source_hall_name=hall.name,
                target_hall_name=target_name,
                station_id=int(hall.freshwater_station_id),
                station_name=hall.freshwater_station.name,
                container_count=container_count,
            )
        )
    return plans, stats


def ensure_pen_type(user, reason: str):
    existing = ContainerType.objects.filter(name="FishTalk Imported Pen").order_by("id")
    if existing.exists():
        pen_type = existing.first()
        created = False
    else:
        pen_type = ContainerType(
            name="FishTalk Imported Pen",
            category="PEN",
            max_volume_m3=Decimal("999999.99"),
            description="Auto-created for FishTalk migration",
        )
        save_with_history(pen_type, user=user, reason=reason)
        created = True
    if created:
        return pen_type
    # Normalize core fields for legacy duplicates so downstream migrations are stable.
    updates = []
    if pen_type.category != "PEN":
        pen_type.category = "PEN"
        updates.append("category")
    if pen_type.max_volume_m3 != Decimal("999999.99"):
        pen_type.max_volume_m3 = Decimal("999999.99")
        updates.append("max_volume_m3")
    if updates:
        save_with_history(pen_type, user=user, reason=reason)
    return pen_type


def apply_plan(plans: list[MovePlan], *, user, reason: str) -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    if not plans:
        return stats

    pen_type = ensure_pen_type(user, reason)
    hall_ids_affected: set[int] = set()
    station_ids_affected: set[int] = set()

    with transaction.atomic():
        for plan in plans:
            container = Container.objects.select_related("hall__freshwater_station").get(pk=plan.container_id)
            station = container.hall.freshwater_station if container.hall_id else None
            hall = container.hall
            if hall is not None:
                hall_ids_affected.add(int(hall.id))
            if station is not None:
                station_ids_affected.add(int(station.id))

            geography, _ = Geography.objects.get_or_create(
                name=plan.target_geography[:100],
                defaults={"description": "Imported placeholder from FishTalk"},
            )
            area, created = Area.objects.get_or_create(
                name=plan.target_area_name[:100],
                geography=geography,
                defaults={
                    "latitude": station.latitude if station else Decimal("0"),
                    "longitude": station.longitude if station else Decimal("0"),
                    "max_biomass": Decimal("0"),
                    "active": True,
                },
            )
            if created:
                stats["areas_created"] += 1

            # Re-home marine container from hall/station context to area context.
            container.hall = None
            container.area = area
            container.parent_container = None
            container.hierarchy_role = "HOLDING"
            container.container_type = pen_type
            if not container.active:
                container.active = True
            save_with_history(container, user=user, reason=reason)
            stats["containers_moved_to_area"] += 1

            ext = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="Containers",
                target_object_id=container.id,
            ).order_by("-updated_at").first()
            if ext is not None:
                metadata = dict(ext.metadata or {})
                metadata.update(
                    {
                        "site": plan.source_site,
                        "site_group": plan.source_site_group,
                        "prod_stage": plan.source_prod_stage,
                        "grouping_bucket": "sea",
                        "remediated_from_station_id": plan.from_station_id,
                        "remediated_from_station_name": plan.from_station_name,
                        "remediated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
                    }
                )
                ext.metadata = metadata
                ext.save(update_fields=["metadata", "updated_at"])

        for hall_id in sorted(hall_ids_affected):
            hall = Hall.objects.filter(pk=hall_id).first()
            if hall is None:
                continue
            if hall.containers.exists():
                continue
            if hall.feed_containers.exists():
                if hall.active:
                    hall.active = False
                    save_with_history(hall, user=user, reason=reason)
                    stats["halls_deactivated_with_feed_refs"] += 1
                continue
            hall.delete()
            stats["halls_deleted_empty"] += 1

        for station_id in sorted(station_ids_affected):
            station = FreshwaterStation.objects.filter(pk=station_id).first()
            if station is None:
                continue
            has_containers = Container.objects.filter(hall__freshwater_station=station).exists()
            has_halls = station.halls.exists()
            if not has_containers and not has_halls:
                station.delete()
                stats["stations_deleted_empty"] += 1
                continue
            if not has_containers and station.active:
                station.active = False
                save_with_history(station, user=user, reason=reason)
                stats["stations_deactivated"] += 1

    return dict(stats)


def apply_station_geography_plan(
    plans: list[StationGeographyPlan],
    *,
    user,
    reason: str,
) -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    if not plans:
        return dict(stats)
    with transaction.atomic():
        for plan in plans:
            station = FreshwaterStation.objects.select_related("geography").get(pk=plan.station_id)
            geography, _ = Geography.objects.get_or_create(
                name=plan.to_geography[:100],
                defaults={"description": "Imported placeholder from FishTalk"},
            )
            if station.geography_id == geography.id:
                continue
            station.geography = geography
            save_with_history(station, user=user, reason=reason)
            stats["stations_geography_reassigned"] += 1
    return dict(stats)


def apply_hall_collapse_plan(
    plans: list[HallCollapsePlan],
    *,
    user,
    reason: str,
) -> dict[str, int]:
    stats: dict[str, int] = defaultdict(int)
    with transaction.atomic():
        for plan in plans:
            source_hall = Hall.objects.select_related("freshwater_station").filter(pk=plan.source_hall_id).first()
            if source_hall is None:
                continue
            target_hall, created = Hall.objects.get_or_create(
                name=plan.target_hall_name,
                freshwater_station_id=plan.station_id,
                defaults={
                    "description": "Auto-normalized from semicolon hall labels during migration remediation",
                    "active": True,
                },
            )
            if created:
                save_with_history(target_hall, user=user, reason=reason)
                stats["hall_targets_created"] += 1

            structural = list(
                source_hall.containers.filter(hierarchy_role="STRUCTURAL").order_by("id")
            )
            holding = list(
                source_hall.containers.exclude(hierarchy_role="STRUCTURAL").order_by("id")
            )
            for container in structural + holding:
                container.hall = target_hall
                save_with_history(container, user=user, reason=reason)
                stats["hall_collapse_containers_rehomed"] += 1

            for feed_container in source_hall.feed_containers.all().iterator():
                feed_container.hall = target_hall
                save_with_history(feed_container, user=user, reason=reason)
                stats["hall_collapse_feed_containers_rehomed"] += 1

            if not source_hall.containers.exists() and not source_hall.feed_containers.exists():
                source_hall.delete()
                stats["hall_collapse_sources_deleted"] += 1

        # Sweep lingering semicolon halls that are already empty/no-op.
        for hall in Hall.objects.filter(name__contains=";").iterator():
            if hall.containers.exists() or hall.feed_containers.exists():
                continue
            hall.delete()
            stats["hall_collapse_empty_sources_deleted"] += 1
    return dict(stats)


def build_markdown(
    *,
    plans: list[MovePlan],
    hall_collapse_plans: list[HallCollapsePlan],
    station_geo_plans: list[StationGeographyPlan],
    pre_stats: dict[str, int],
    apply_stats: dict[str, int],
    executed: bool,
) -> str:
    by_station = Counter(plan.from_station_name for plan in plans)
    weird_station_names = sorted(
        {name for name in by_station if GUID_NAME_RE.match(name)}
    )
    lines: list[str] = []
    lines.append("# Marine Infrastructure Misclassification Remediation")
    lines.append("")
    lines.append(f"- Executed: `{executed}`")
    lines.append(f"- Candidate container moves (hall -> area): `{len(plans)}`")
    lines.append(f"- Scanned hall containers: `{pre_stats.get('hall_containers_scanned', 0)}`")
    lines.append(
        f"- Missing source linkage rows: `{pre_stats.get('without_external_map', 0)}`"
    )
    lines.append(
        f"- Missing grouped-organisation rows: `{pre_stats.get('without_grouped_org_row', 0)}`"
    )
    lines.append(
        f"- Station geography reassignment candidates: `{len(station_geo_plans)}`"
    )
    lines.append(f"- Hall normalization candidates: `{len(hall_collapse_plans)}`")
    lines.append("")
    lines.append("## Candidate Stations")
    lines.append("")
    lines.append(f"- Unique stations affected: `{len(by_station)}`")
    lines.append(f"- GUID-like station names: `{len(weird_station_names)}`")
    if weird_station_names:
        lines.append(f"- GUID examples: `{', '.join(weird_station_names[:10])}`")
    lines.append("")
    lines.append("| Station | Containers moved |")
    lines.append("| --- | ---: |")
    for station_name, count in by_station.most_common(30):
        lines.append(f"| {station_name} | {count} |")
    lines.append("")
    if hall_collapse_plans:
        lines.append("## Hall Label Normalization")
        lines.append("")
        lines.append("| Station | Source Hall | Target Hall | Containers |")
        lines.append("| --- | --- | --- | ---: |")
        for plan in sorted(hall_collapse_plans, key=lambda item: item.container_count, reverse=True)[:30]:
            lines.append(
                f"| {plan.station_name} | {plan.source_hall_name} | {plan.target_hall_name} | "
                f"{plan.container_count} |"
            )
        lines.append("")
    if station_geo_plans:
        lines.append("## Station Geography Corrections")
        lines.append("")
        lines.append("| Station | From | To | Votes |")
        lines.append("| --- | --- | --- | ---: |")
        for plan in sorted(station_geo_plans, key=lambda item: item.evidence_total, reverse=True)[:30]:
            lines.append(
                f"| {plan.station_name} | {plan.from_geography} | {plan.to_geography} | "
                f"{plan.evidence_votes}/{plan.evidence_total} |"
            )
        lines.append("")
    lines.append("## Apply Stats")
    lines.append("")
    if apply_stats:
        for key in sorted(apply_stats):
            lines.append(f"- `{key}`: {apply_stats[key]}")
    else:
        lines.append("- Dry-run only (no database writes).")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remediate marine containers misclassified under freshwater stations.",
    )
    parser.add_argument(
        "--csv-dir",
        default=str(PROJECT_ROOT / "scripts" / "migration" / "data" / "extract"),
        help="FishTalk extract CSV directory.",
    )
    parser.add_argument(
        "--report-md",
        default=str(
            PROJECT_ROOT
            / "aquamind"
            / "docs"
            / "progress"
            / "migration"
            / "analysis_reports"
            / datetime.utcnow().strftime("%Y-%m-%d")
            / "marine_infra_station_area_remediation_2026-02-19.md"
        ),
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--report-json",
        default=str(
            PROJECT_ROOT
            / "aquamind"
            / "docs"
            / "progress"
            / "migration"
            / "analysis_reports"
            / datetime.utcnow().strftime("%Y-%m-%d")
            / "marine_infra_station_area_remediation_2026-02-19.json"
        ),
        help="JSON report output path.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply remediation changes. Default is dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_dir = Path(args.csv_dir)
    report_md = Path(args.report_md)
    report_json = Path(args.report_json)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)

    plans, pre_stats = build_move_plan(csv_dir=csv_dir)
    hall_collapse_plans, hall_collapse_stats = build_hall_collapse_plan()
    station_geo_plans, station_geo_stats = build_station_geography_plan(csv_dir=csv_dir)
    pre_stats.update(hall_collapse_stats)
    pre_stats.update(station_geo_stats)
    apply_stats: dict[str, int] = {}
    if args.execute:
        user_model = get_user_model()
        user = user_model.objects.filter(is_superuser=True).first() or user_model.objects.first()
        reason = "FishTalk migration remediation: marine containers moved from station/hall to area"
        if plans:
            apply_stats = apply_plan(plans, user=user, reason=reason)

        hall_collapse_plans, hall_collapse_stats = build_hall_collapse_plan()
        pre_stats.update(hall_collapse_stats)
        collapse_apply = apply_hall_collapse_plan(hall_collapse_plans, user=user, reason=reason)
        apply_stats.update(collapse_apply)

        # Recompute after container moves, then reassign station geography if needed.
        station_geo_plans, station_geo_stats = build_station_geography_plan(csv_dir=csv_dir)
        pre_stats.update(station_geo_stats)
        geo_apply = apply_station_geography_plan(station_geo_plans, user=user, reason=reason)
        apply_stats.update(geo_apply)

    payload = {
        "generated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "executed": bool(args.execute),
        "pre_stats": pre_stats,
        "apply_stats": apply_stats,
        "candidate_move_count": len(plans),
        "candidate_station_count": len({plan.from_station_id for plan in plans}),
        "hall_collapse_candidate_count": len(hall_collapse_plans),
        "station_geography_candidate_count": len(station_geo_plans),
        "candidate_guid_station_names": sorted(
            {plan.from_station_name for plan in plans if GUID_NAME_RE.match(plan.from_station_name)}
        ),
    }
    report_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    report_md.write_text(
        build_markdown(
            plans=plans,
            hall_collapse_plans=hall_collapse_plans,
            station_geo_plans=station_geo_plans,
            pre_stats=pre_stats,
            apply_stats=apply_stats,
            executed=bool(args.execute),
        ),
        encoding="utf-8",
    )

    print(f"Candidate moves: {len(plans)}")
    print(f"Executed: {bool(args.execute)}")
    print(f"Report (md): {report_md}")
    print(f"Report (json): {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

