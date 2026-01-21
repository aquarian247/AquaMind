#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate a stitched FishTalk population component into AquaMind.

This is intentionally minimal: it creates required infrastructure (geography,
station/hall or sea area, containers) and then creates one AquaMind Batch with
one BatchContainerAssignment per FishTalk PopulationID in the stitched
component.

It is meant for a dry-run against aquamind_db_migr_dev only.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")

from scripts.migration.safety import (  # noqa: E402
    assert_default_db_is_migration_db,
    configure_migration_environment,
)

configure_migration_environment()

import django  # noqa: E402

django.setup()
assert_default_db_is_migration_db()

from django.db import transaction  # noqa: E402

from apps.batch.models import Batch, LifeCycleStage, Species, BatchCreationWorkflow, CreationAction  # noqa: E402
from apps.batch.models.assignment import BatchContainerAssignment  # noqa: E402
from apps.broodstock.models import EggSupplier  # noqa: E402
from apps.infrastructure.models import (  # noqa: E402
    Area,
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.migration_support.models import ExternalIdMap  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from scripts.migration.extractors.base import (  # noqa: E402
    BaseExtractor,
    ExtractionContext,
)
from scripts.migration.history import save_with_history, get_or_create_with_history  # noqa: E402

User = get_user_model()


REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


SEA_STAGE_MARKERS = ("ONGROW", "GROWER", "GRILSE")
FAROE_SITEGROUPS = {"WEST", "NORTH", "SOUTH"}
SCOTLAND_SITES_FRESHWATER_ARCHIVE = {
    "BRS1 LANGASS",
    "FW11 BARVAS",
    "FW12 AMHUINNSUIDHE",
    "FW14 HARRIS LOCHS",
    "FW22 RUSSEL BURN",
    "FW23 LOCH DAMPH SOUTH",
    "LANGASS OLD TO SUMMER 15",
    "LOCH GEIREAN",
    "LOCH TORMASAD",
    "TULLICH",
}
SCOTLAND_SITES_FRESHWATER = {
    "FW13 GEOCRAB",
    "FW21 COULDORAN",
    "FW22 APPLECROSS",
    "FW24 KINLOCHMOIDART",
}
SCOTLAND_SITES_BROODSTOCK = {
    "BRS2 LANGASS",
    "BRS3 GEOCRAB",
}
FAROE_SITES_LAND = {
    "S03 NORÐTOFTIR",
    "S04 HÚSAR",
    "S08 GJÓGV",
    "S10 SVÍNOY",
    "S16 GLYVRADALUR",
    "S21 VIÐAREIÐI",
    "S24 STROND",
}
FAROE_SITES_ROGNKELSI = {"H01 SVÍNOY"}
FAROE_SITES_LIVFISKUR = {
    "L01 VIÐ ÁIR",
    "L02 SKOPUN",
}
FAROE_SITES_OTHER = {"H125 GLYVRAR"}

def stage_bucket(stage_name: str) -> str | None:
    if not stage_name:
        return None
    upper = stage_name.upper()
    if any(marker in upper for marker in SEA_STAGE_MARKERS):
        return "sea"
    if "SMOLT" in upper or "PARR" in upper or "FRY" in upper or "ALEVIN" in upper or "EGG" in upper:
        return "freshwater"
    return None


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def normalize_key(value: str | None) -> str:
    return normalize_label(value).upper()


def resolve_site_grouping(site: str | None, site_group: str | None) -> tuple[str, str]:
    site_group_key = normalize_key(site_group)
    site_key = normalize_key(site)
    if site_group_key in FAROE_SITEGROUPS:
        return "Faroe Islands", f"SITEGROUP_{site_group_key}"
    if site_group_key:
        return "Scotland", f"SITEGROUP_{site_group_key}"
    if site_key in SCOTLAND_SITES_FRESHWATER_ARCHIVE:
        return "Scotland", "SCOTLAND_FRESHWATER_ARCHIVE"
    if site_key in SCOTLAND_SITES_FRESHWATER:
        return "Scotland", "SCOTLAND_FRESHWATER"
    if site_key in SCOTLAND_SITES_BROODSTOCK:
        return "Scotland", "SCOTLAND_BROODSTOCK"
    if site_key in FAROE_SITES_LAND:
        return "Faroe Islands", "FAROE_LAND"
    if site_key in FAROE_SITES_ROGNKELSI:
        return "Faroe Islands", "FAROE_ROGNKELSI"
    if site_key in FAROE_SITES_LIVFISKUR:
        return "Faroe Islands", "FAROE_LIVFISKUR"
    if site_key in FAROE_SITES_OTHER:
        return "Faroe Islands", "FAROE_OTHER"
    return "", ""


def hall_label_from_group(group_name: str | None) -> str:
    label = normalize_label(group_name)
    if not label:
        return ""
    if "Høll" in label:
        prefix, _, _ = label.partition("Høll")
        prefix = prefix.strip()
        return f"Hall {prefix}" if prefix else "Hall"
    if label.startswith("Hall ") or label.endswith(" Hall"):
        return label
    return label


def hall_label_from_official(official_id: str | None) -> str:
    if not official_id:
        return ""
    prefix = official_id.split(";")[0].strip()
    return hall_label_from_group(prefix)


def fishtalk_stage_to_aquamind(stage_name: str) -> str:
    upper = (stage_name or "").upper()
    if any(token in upper for token in ("EGG", "ALEVIN", "SAC")):
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
    return "Smolt"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


def get_or_create_egg_supplier(name: str, *, history_user: User | None, history_reason: str | None) -> EggSupplier:
    supplier = EggSupplier.objects.filter(name=name).first()
    if not supplier:
        supplier = EggSupplier(
            name=name,
            contact_details="Unknown (FishTalk migration)",
            certifications="",
        )
        save_with_history(supplier, user=history_user, reason=history_reason)
    ExternalIdMap.objects.update_or_create(
        source_system="FishTalk",
        source_model="EggSupplier",
        source_identifier=name,
        defaults={
            "target_app_label": supplier._meta.app_label,
            "target_model": supplier._meta.model_name,
            "target_object_id": supplier.pk,
        },
    )
    return supplier


def build_creation_workflow_number(batch_number: str, component_key: str) -> str:
    base = f"CRT-{batch_number}"
    if len(base) <= 50:
        return base
    suffix = (component_key or "")[:8]
    reserved = len("CRT-") + 1 + len(suffix)
    trimmed = batch_number[: max(0, 50 - reserved)]
    if suffix:
        return f"CRT-{trimmed}-{suffix}"
    return f"CRT-{trimmed}"[:50]


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    population_name: str
    container_id: str
    start_time: datetime
    end_time: datetime | None
    first_stage: str
    last_stage: str


def load_members_from_report(report_dir: Path, *, component_id: int | None, component_key: str | None) -> list[ComponentMember]:
    import csv

    path = report_dir / "population_members.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if component_id is not None and row.get("component_id") != str(component_id):
                continue
            if component_key is not None and row.get("component_key") != component_key:
                continue
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    population_name=row.get("population_name", ""),
                    container_id=row.get("container_id", ""),
                    start_time=start,
                    end_time=end,
                    first_stage=row.get("first_stage", ""),
                    last_stage=row.get("last_stage", ""),
                )
            )

    members.sort(key=lambda m: m.start_time)
    return members


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate one stitched FishTalk population component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--geography", default="Faroe Islands", help="Target geography name to use/create")
    parser.add_argument("--batch-number", help="Override batch_number")
    parser.add_argument(
        "--active-window-days",
        type=int,
        default=365,
        help="Days back from latest FishTalk status to consider active (default: 365)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.component_id is None and not args.component_key:
        raise SystemExit("Provide --component-id or --component-key")

    report_dir = Path(args.report_dir)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=args.component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    component_key = args.component_key
    if not component_key:
        # Derive component_key from the first matching row in the report.
        import csv

        with (report_dir / "population_members.csv").open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("component_id") == str(args.component_id):
                    component_key = row.get("component_key")
                    break
    if not component_key:
        raise SystemExit("Unable to resolve component_key from report")

    representative = next((m.population_name for m in members if "TRANSPORTPOP" not in m.population_name.upper()), members[0].population_name)
    batch_start = min(m.start_time for m in members).date()

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    population_ids = [m.population_id for m in members if m.population_id]
    latest_status_time_by_pop: dict[str, datetime] = {}
    component_status_time: datetime | None = None

    global_rows = extractor._run_sqlcmd(
        query="SELECT TOP 1 StatusTime FROM dbo.PublicStatusValues ORDER BY StatusTime DESC",
        headers=["StatusTime"],
    )
    global_status_time = parse_dt(global_rows[0].get("StatusTime", "")) if global_rows else None
    active_cutoff = (
        global_status_time - timedelta(days=args.active_window_days)
        if global_status_time
        else None
    )

    if population_ids:
        pop_clause = ",".join(f"'{pid}'" for pid in population_ids)
        status_rows = extractor._run_sqlcmd(
            query=(
                "SELECT PopulationID, MAX(StatusTime) AS MaxStatusTime "
                "FROM dbo.PublicStatusValues "
                f"WHERE PopulationID IN ({pop_clause}) "
                "GROUP BY PopulationID"
            ),
            headers=["PopulationID", "MaxStatusTime"],
        )
        for row in status_rows:
            latest = parse_dt(row.get("MaxStatusTime", ""))
            if latest:
                latest_status_time_by_pop[row["PopulationID"]] = latest
        component_status_time = max(latest_status_time_by_pop.values(), default=None)

    if component_status_time and active_cutoff:
        has_active_member = component_status_time >= active_cutoff
    else:
        has_active_member = any(m.end_time is None for m in members)

    active_population_by_container: dict[str, str] = {}
    container_latest: dict[str, tuple[datetime, str]] = {}
    for member in members:
        if not member.container_id:
            continue
        candidate_time = latest_status_time_by_pop.get(member.population_id) or member.end_time or member.start_time
        current = container_latest.get(member.container_id)
        if not current or candidate_time > current[0]:
            container_latest[member.container_id] = (candidate_time, member.population_id)
    for container_id, (_, population_id) in container_latest.items():
        active_population_by_container[container_id] = population_id

    batch_end = max((m.end_time for m in members if m.end_time), default=None)
    batch_end_date = batch_end.date() if batch_end else None
    batch_status = "ACTIVE" if has_active_member else "COMPLETED"
    batch_actual_end_date = None if has_active_member else (
        component_status_time.date() if component_status_time else batch_end_date
    )

    lifecycle_stage_name = fishtalk_stage_to_aquamind(members[0].first_stage or members[0].last_stage)

    # Resolve species / lifecycle stage.
    species = Species.objects.filter(name="Atlantic Salmon").first() or Species.objects.first()
    if species is None:
        raise SystemExit("Missing Species master data; run scripts/migration/setup_master_data.py")
    lifecycle_stage = LifeCycleStage.objects.filter(name=lifecycle_stage_name).first()
    if lifecycle_stage is None:
        raise SystemExit("Missing LifeCycleStage master data; run scripts/migration/setup_master_data.py")

    batch_number = args.batch_number
    if not batch_number:
        slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in representative).strip("-")
        batch_number = f"FT-{component_key[:8]}-{slug}"[:50]

    container_ids = sorted({m.container_id for m in members if m.container_id})
    if not container_ids:
        raise SystemExit("No container ids found in component members")

    in_clause = ",".join(f"'{cid}'" for cid in container_ids)
    containers = extractor._run_sqlcmd(
        query=(
            "SELECT c.ContainerID, c.ContainerName, c.OrgUnitID, c.OfficialID "
            "FROM dbo.Containers c "
            f"WHERE c.ContainerID IN ({in_clause})"
        ),
        headers=["ContainerID", "ContainerName", "OrgUnitID", "OfficialID"],
    )
    containers_by_id = {row["ContainerID"]: row for row in containers}

    grouping_rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), ContainerID) AS ContainerID, "
            "Site, SiteGroup, Company, ProdStage, ContainerGroup, ContainerGroupID, StandName, StandID "
            "FROM dbo.Ext_GroupedOrganisation_v2 "
            f"WHERE ContainerID IN ({in_clause})"
        ),
        headers=[
            "ContainerID",
            "Site",
            "SiteGroup",
            "Company",
            "ProdStage",
            "ContainerGroup",
            "ContainerGroupID",
            "StandName",
            "StandID",
        ],
    )

    container_grouping: dict[str, dict[str, str]] = {}
    for row in grouping_rows:
        container_id = row.get("ContainerID")
        if not container_id:
            continue
        site = normalize_label(row.get("Site"))
        site_group = normalize_label(row.get("SiteGroup"))
        company = normalize_label(row.get("Company"))
        prod_stage = normalize_label(row.get("ProdStage"))
        container_group = normalize_label(row.get("ContainerGroup"))
        container_group_id = normalize_label(row.get("ContainerGroupID"))
        stand_name = normalize_label(row.get("StandName"))
        stand_id = normalize_label(row.get("StandID"))
        geo_name, bucket = resolve_site_grouping(site, site_group)
        container_grouping[container_id] = {
            "site": site,
            "site_group": site_group,
            "company": company,
            "prod_stage": prod_stage,
            "container_group": container_group,
            "container_group_id": container_group_id,
            "stand_name": stand_name,
            "stand_id": stand_id,
            "geography": geo_name,
            "grouping_bucket": bucket,
        }

    org_unit_ids = sorted({row.get("OrgUnitID") for row in containers if row.get("OrgUnitID")})
    org_in_clause = ",".join(f"'{oid}'" for oid in org_unit_ids)
    org_units = extractor._run_sqlcmd(
        query=(
            "SELECT ou.OrgUnitID, ou.Name, l.Latitude, l.Longitude "
            "FROM dbo.OrganisationUnit ou "
            "LEFT JOIN dbo.Locations l ON l.LocationID = ou.LocationID "
            f"WHERE ou.OrgUnitID IN ({org_in_clause})"
        ),
        headers=["OrgUnitID", "Name", "Latitude", "Longitude"],
    )
    org_by_id = {row["OrgUnitID"]: row for row in org_units}

    containers_by_org: dict[str, list[str]] = {}
    for row in containers:
        org_id = row.get("OrgUnitID")
        container_id = row.get("ContainerID")
        if not org_id or not container_id:
            continue
        containers_by_org.setdefault(org_id, []).append(container_id)

    # Container classification: sea if any member population in that container has a sea stage.
    container_bucket: dict[str, str] = {}
    for member in members:
        bucket = stage_bucket(member.last_stage or member.first_stage or "")
        if not bucket:
            continue
        current = container_bucket.get(member.container_id)
        if current == "sea":
            continue
        if bucket == "sea":
            container_bucket[member.container_id] = "sea"
        else:
            container_bucket.setdefault(member.container_id, "freshwater")

    if args.dry_run:
        print(f"[dry-run] Would migrate component_key={component_key} into batch_number={batch_number}")
        print(f"[dry-run] Members: {len(members)} populations, containers: {len(container_ids)}")
        return 0

    with transaction.atomic():
        history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        history_reason = f"FishTalk migration: component {component_key}"
        def get_geography(name: str) -> Geography:
            if not name:
                name = args.geography
            if name not in geography_cache:
                geography_cache[name], _ = Geography.objects.get_or_create(
                    name=name,
                    defaults={"description": f"Imported placeholder for {name}"},
                )
            return geography_cache[name]

        geography_cache: dict[str, Geography] = {}

        tank_type, _ = get_or_create_with_history(
            ContainerType,
            lookup={"name": "FishTalk Imported Tank"},
            defaults={
                "category": "TANK",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
            user=history_user,
            reason=history_reason,
        )
        pen_type, _ = get_or_create_with_history(
            ContainerType,
            lookup={"name": "FishTalk Imported Pen"},
            defaults={
                "category": "PEN",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
            user=history_user,
            reason=history_reason,
        )

        # Lookup (or create) org-unit scoped holders
        # PREFER LOOKUP from pre-migrated infrastructure to avoid race conditions
        station_by_org: dict[str, FreshwaterStation] = {}
        hall_by_org_group: dict[tuple[str, str], Hall] = {}
        fallback_hall_by_org: dict[str, Hall] = {}
        area_by_org: dict[str, Area] = {}

        # Determine which org units have sea containers vs freshwater
        org_has_sea: dict[str, bool] = {}
        org_has_freshwater: dict[str, bool] = {}
        for org_id in org_unit_ids:
            org_containers = containers_by_org.get(org_id, [])
            org_has_sea[org_id] = any(
                container_bucket.get(cid) == "sea" for cid in org_containers
            )
            org_has_freshwater[org_id] = any(
                container_bucket.get(cid, "freshwater") != "sea" for cid in org_containers
            )

        for org_id in org_unit_ids:
            org = org_by_id.get(org_id) or {}
            org_name = (org.get("Name") or org_id)[:80]
            lat = Decimal(str(org.get("Latitude") or 0)).quantize(Decimal("0.000001"))
            lon = Decimal(str(org.get("Longitude") or 0)).quantize(Decimal("0.000001"))

            org_geo_candidates = [
                container_grouping.get(cid, {}).get("geography")
                for cid in containers_by_org.get(org_id, [])
                if container_grouping.get(cid, {}).get("geography")
            ]
            if org_geo_candidates:
                org_geo_name = Counter(org_geo_candidates).most_common(1)[0][0]
            else:
                org_geo_name = args.geography
            geography = get_geography(org_geo_name)

            # LOOKUP FreshwaterStation from pre-migration, fallback to create
            if org_has_freshwater.get(org_id, True):
                # Try to find pre-created station from ExternalIdMap
                station_map = get_external_map("OrgUnit_FW", org_id)
                if station_map:
                    station = FreshwaterStation.objects.get(pk=station_map.target_object_id)
                else:
                    # Fallback: try to find by name or create
                    station, _ = get_or_create_with_history(
                        FreshwaterStation,
                        lookup={"name": f"FT {org_name} FW"[:100]},
                        defaults={
                            "station_type": "FRESHWATER",
                            "geography": geography,
                            "latitude": lat,
                            "longitude": lon,
                            "description": "Imported placeholder from FishTalk",
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                    )
                station_by_org[org_id] = station

            # LOOKUP Area from pre-migration, fallback to create
            if org_has_sea.get(org_id, False):
                # Try to find pre-created area from ExternalIdMap
                area_map = get_external_map("OrgUnit_Sea", org_id)
                if area_map:
                    area = Area.objects.get(pk=area_map.target_object_id)
                else:
                    # Fallback: try to find by name or create
                    area, _ = get_or_create_with_history(
                        Area,
                        lookup={"name": f"FT {org_name} Sea"[:100], "geography": geography},
                        defaults={
                            "latitude": lat,
                            "longitude": lon,
                            "max_biomass": Decimal("0"),
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                    )
                area_by_org[org_id] = area

        # Create containers
        aquamind_container_by_source: dict[str, Container] = {}
        for cid in container_ids:
            mapped = get_external_map("Containers", cid)
            if mapped:
                aquamind_container_by_source[cid] = Container.objects.get(pk=mapped.target_object_id)
                continue

            src = containers_by_id.get(cid) or {}
            org_id = src.get("OrgUnitID") or org_unit_ids[0]
            bucket = container_bucket.get(cid, "freshwater")
            if bucket == "sea":
                container_type = pen_type
                area = area_by_org[org_id]
                hall = None
            else:
                container_type = tank_type
                area = None
                group_meta = container_grouping.get(cid, {})
                group_label = hall_label_from_group(group_meta.get("container_group"))
                if not group_label:
                    group_label = hall_label_from_official(src.get("OfficialID"))
                if group_label:
                    hall_key = (org_id, group_label)
                    hall = hall_by_org_group.get(hall_key)
                    if hall is None:
                        station = station_by_org[org_id]
                        group_description = (
                            "Imported placeholder from FishTalk "
                            f"({group_meta.get('container_group') or group_label})"
                        )
                        hall, _ = get_or_create_with_history(
                            Hall,
                            lookup={"name": group_label[:100], "freshwater_station": station},
                            defaults={
                                "description": group_description,
                                "active": True,
                            },
                            user=history_user,
                            reason=history_reason,
                        )
                        hall_by_org_group[hall_key] = hall
                else:
                    hall = fallback_hall_by_org.get(org_id)
                    if hall is None:
                        station = station_by_org[org_id]
                        org_name = (org_by_id.get(org_id, {}).get("Name") or org_id)[:80]
                        hall, _ = get_or_create_with_history(
                            Hall,
                            lookup={
                                "name": f"FT {org_name} Hall"[:100],
                                "freshwater_station": station,
                            },
                            defaults={
                                "description": "Imported placeholder from FishTalk",
                                "active": True,
                            },
                            user=history_user,
                            reason=history_reason,
                        )
                        fallback_hall_by_org[org_id] = hall

            container = Container(
                name=f"FT {src.get('ContainerName') or cid}"[:100],
                container_type=container_type,
                hall=hall,
                area=area,
                volume_m3=Decimal("0.00"),
                max_biomass_kg=Decimal("0.00"),
                feed_recommendations_enabled=True,
                active=True,
            )
            save_with_history(container, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="Containers",
                source_identifier=str(cid),
                defaults={
                    "target_app_label": container._meta.app_label,
                    "target_model": container._meta.model_name,
                    "target_object_id": container.pk,
                    "metadata": {
                        "container_name": src.get("ContainerName"),
                        "org_unit_id": src.get("OrgUnitID"),
                        "official_id": src.get("OfficialID"),
                        "site": container_grouping.get(cid, {}).get("site"),
                        "site_group": container_grouping.get(cid, {}).get("site_group"),
                        "company": container_grouping.get(cid, {}).get("company"),
                        "prod_stage": container_grouping.get(cid, {}).get("prod_stage"),
                        "container_group": container_grouping.get(cid, {}).get("container_group"),
                        "container_group_id": container_grouping.get(cid, {}).get("container_group_id"),
                        "stand_name": container_grouping.get(cid, {}).get("stand_name"),
                        "stand_id": container_grouping.get(cid, {}).get("stand_id"),
                        "grouping_bucket": container_grouping.get(cid, {}).get("grouping_bucket"),
                    },
                },
            )
            aquamind_container_by_source[cid] = container

        # Create / reuse batch via ExternalIdMap
        batch_map = get_external_map("PopulationComponent", component_key)
        if batch_map:
            batch = Batch.objects.get(pk=batch_map.target_object_id)
            batch.batch_number = batch_number
            batch.species = species
            batch.lifecycle_stage = lifecycle_stage
            batch.status = batch_status
            batch.start_date = batch_start
            batch.actual_end_date = batch_actual_end_date
            batch.notes = f"FishTalk stitched component {component_key}; representative='{representative}'"
            save_with_history(batch, user=history_user, reason=history_reason)
        else:
            batch = Batch(
                batch_number=batch_number,
                species=species,
                lifecycle_stage=lifecycle_stage,
                status=batch_status,
                start_date=batch_start,
                actual_end_date=batch_actual_end_date,
                notes=f"FishTalk stitched component {component_key}; representative='{representative}'",
            )
            save_with_history(batch, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationComponent",
                source_identifier=str(component_key),
                defaults={
                    "target_app_label": batch._meta.app_label,
                    "target_model": batch._meta.model_name,
                    "target_object_id": batch.pk,
                    "metadata": {"batch_number": batch.batch_number},
                },
            )

        assignment_by_population_id: dict[str, BatchContainerAssignment] = {}

        # Create assignments (1 per FishTalk PopulationID)
        for member in members:
            assignment_map = get_external_map("Populations", member.population_id)
            container = aquamind_container_by_source[member.container_id]

            lifecycle_name = fishtalk_stage_to_aquamind(member.last_stage or member.first_stage)
            stage = LifeCycleStage.objects.filter(name=lifecycle_name).first() or lifecycle_stage

            # Grab status snapshot near population start.
            status_rows = extractor._run_sqlcmd(
                query=(
                    "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                    "FROM dbo.PublicStatusValues "
                    f"WHERE PopulationID = '{member.population_id}' "
                    f"AND StatusTime >= '{member.start_time.strftime('%Y-%m-%d %H:%M:%S')}' "
                    "ORDER BY StatusTime ASC"
                ),
                headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
            )
            if not status_rows:
                status_rows = extractor._run_sqlcmd(
                    query=(
                        "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                        "FROM dbo.PublicStatusValues "
                        f"WHERE PopulationID = '{member.population_id}' "
                        f"AND StatusTime <= '{member.start_time.strftime('%Y-%m-%d %H:%M:%S')}' "
                        "ORDER BY StatusTime DESC"
                    ),
                    headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
                )

            count = 0
            biomass = Decimal("0.00")
            if status_rows:
                try:
                    count = int(round(float(status_rows[0].get("CurrentCount") or 0)))
                except ValueError:
                    count = 0
                try:
                    biomass = Decimal(str(status_rows[0].get("CurrentBiomassKg") or 0)).quantize(Decimal("0.01"))
                except Exception:
                    biomass = Decimal("0.00")

            latest_status_time = latest_status_time_by_pop.get(member.population_id)
            if latest_status_time and active_cutoff:
                assignment_active = latest_status_time >= active_cutoff
            else:
                assignment_active = member.end_time is None

            if assignment_active:
                assignment_departure = None
            elif latest_status_time:
                assignment_departure = latest_status_time.date()
            elif member.end_time:
                assignment_departure = member.end_time.date()
            else:
                assignment_departure = None

            active_population_id = active_population_by_container.get(member.container_id)
            if assignment_active and active_population_id and active_population_id != member.population_id:
                assignment_active = False
                if assignment_departure is None:
                    fallback_time = latest_status_time or member.end_time or member.start_time
                    assignment_departure = fallback_time.date()

            defaults = {
                "batch": batch,
                "container": container,
                "lifecycle_stage": stage,
                "population_count": max(count, 0),
                "biomass_kg": biomass,
                "avg_weight_g": None,
                "assignment_date": member.start_time.date(),
                "departure_date": assignment_departure,
                "is_active": assignment_active,
                "notes": f"FishTalk PopulationID={member.population_id}",
            }

            if assignment_map:
                assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)
                for key, value in defaults.items():
                    setattr(assignment, key, value)
                save_with_history(assignment, user=history_user, reason=history_reason)
            else:
                assignment = BatchContainerAssignment(**defaults)
                save_with_history(assignment, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="Populations",
                    source_identifier=str(member.population_id),
                    defaults={
                        "target_app_label": assignment._meta.app_label,
                        "target_model": assignment._meta.model_name,
                        "target_object_id": assignment.pk,
                        "metadata": {"component_key": component_key, "container_id": member.container_id},
                    },
                )

            assignment_by_population_id[member.population_id] = assignment

        initial_stage_name = lifecycle_stage.name if lifecycle_stage else lifecycle_stage_name
        initial_members = [
            member
            for member in members
            if member.start_time.date() == batch_start
            and fishtalk_stage_to_aquamind(member.first_stage or member.last_stage) == initial_stage_name
        ]
        if not initial_members:
            initial_members = [member for member in members if member.start_time.date() == batch_start]
        if not initial_members:
            initial_members = [members[0]]

        initial_members.sort(key=lambda member: (member.start_time, member.population_id))
        creation_assignments = [
            (member, assignment_by_population_id.get(member.population_id))
            for member in initial_members
            if assignment_by_population_id.get(member.population_id)
        ]

        if creation_assignments:
            workflow_number = build_creation_workflow_number(batch.batch_number, component_key)
            workflow_map = get_external_map("PopulationComponentCreationWorkflow", component_key)
            if workflow_map:
                creation_workflow = BatchCreationWorkflow.objects.get(pk=workflow_map.target_object_id)
            else:
                creation_workflow = BatchCreationWorkflow.objects.filter(workflow_number=workflow_number).first()

            supplier_name = "FishTalk Legacy Supplier"
            egg_supplier = get_or_create_egg_supplier(
                supplier_name,
                history_user=history_user,
                history_reason=history_reason,
            )

            total_eggs_planned = sum(int(assignment.population_count or 0) for _, assignment in creation_assignments)
            total_actions = len(creation_assignments)
            planned_start_date = min(member.start_time for member, _ in creation_assignments).date()
            planned_completion_date = max(member.start_time for member, _ in creation_assignments).date()
            progress_percentage = Decimal("100.00") if total_actions else Decimal("0.00")

            workflow_payload = {
                "workflow_number": workflow_number,
                "batch": batch,
                "status": "COMPLETED" if total_actions else "PLANNED",
                "egg_source_type": "EXTERNAL",
                "external_supplier": egg_supplier,
                "external_supplier_batch_number": str(component_key),
                "total_eggs_planned": total_eggs_planned,
                "total_eggs_received": total_eggs_planned,
                "total_mortality_on_arrival": 0,
                "planned_start_date": planned_start_date,
                "planned_completion_date": planned_completion_date,
                "actual_start_date": planned_start_date if total_actions else None,
                "actual_completion_date": planned_completion_date if total_actions else None,
                "total_actions": total_actions,
                "actions_completed": total_actions,
                "progress_percentage": progress_percentage,
                "created_by": history_user,
                "notes": f"Synthetic creation workflow from FishTalk component {component_key}",
            }

            if creation_workflow:
                for key, value in workflow_payload.items():
                    setattr(creation_workflow, key, value)
                save_with_history(creation_workflow, user=history_user, reason=history_reason)
            else:
                creation_workflow = BatchCreationWorkflow(**workflow_payload)
                save_with_history(creation_workflow, user=history_user, reason=history_reason)
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="PopulationComponentCreationWorkflow",
                source_identifier=str(component_key),
                defaults={
                    "target_app_label": creation_workflow._meta.app_label,
                    "target_model": creation_workflow._meta.model_name,
                    "target_object_id": creation_workflow.pk,
                    "metadata": {"batch_number": batch.batch_number},
                },
            )

            used_action_numbers = set(
                CreationAction.objects.filter(workflow=creation_workflow).values_list("action_number", flat=True)
            )
            next_action_number = 1

            def next_available_action_number() -> int:
                nonlocal next_action_number
                while next_action_number in used_action_numbers:
                    next_action_number += 1
                value = next_action_number
                used_action_numbers.add(value)
                next_action_number += 1
                return value

            for member, assignment in creation_assignments:
                action_map = get_external_map("PopulationCreationAction", member.population_id)
                if action_map:
                    creation_action = CreationAction.objects.get(pk=action_map.target_object_id)
                    action_number = creation_action.action_number or next_available_action_number()
                else:
                    creation_action = None
                    action_number = next_available_action_number()

                action_payload = {
                    "workflow": creation_workflow,
                    "action_number": action_number,
                    "status": "COMPLETED" if total_actions else "PENDING",
                    "dest_assignment": assignment,
                    "egg_count_planned": int(assignment.population_count or 0),
                    "egg_count_actual": int(assignment.population_count or 0),
                    "mortality_on_arrival": 0,
                    "expected_delivery_date": member.start_time.date(),
                    "actual_delivery_date": member.start_time.date(),
                    "executed_by": history_user,
                    "notes": f"FishTalk PopulationID={member.population_id}",
                }

                if creation_action:
                    for key, value in action_payload.items():
                        setattr(creation_action, key, value)
                    save_with_history(creation_action, user=history_user, reason=history_reason)
                else:
                    creation_action = CreationAction(**action_payload)
                    save_with_history(creation_action, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="PopulationCreationAction",
                    source_identifier=str(member.population_id),
                    defaults={
                        "target_app_label": creation_action._meta.app_label,
                        "target_model": creation_action._meta.model_name,
                        "target_object_id": creation_action.pk,
                        "metadata": {
                            "component_key": component_key,
                            "batch_number": batch.batch_number,
                        },
                    },
                )

        batch.status = batch_status
        batch.actual_end_date = batch_actual_end_date
        save_with_history(batch, user=history_user, reason=history_reason)

        print(f"Migrated component_key={component_key} into Batch(batch_number={batch.batch_number})")
        print(f"Assignments created/updated: {len(members)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
