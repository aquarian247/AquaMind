#!/usr/bin/env python
"""
Phase 1: Pre-create ALL infrastructure before parallel batch migration.

This script extracts all org units and containers from FishTalk and creates
the corresponding AquaMind infrastructure (Areas, FreshwaterStations, Halls,
Containers) in a SINGLE-THREADED pass to avoid race conditions.

Run this ONCE before running pilot_migrate_batch_parallel.py.

Usage:
    python scripts/migration/tools/pilot_migrate_infrastructure.py [--geography "Faroe Islands"]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

# Django setup
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from apps.infrastructure.models import (  # noqa: E402
    Area,
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.migration_support.models import ExternalIdMap  # noqa: E402
from scripts.migration.extractors.base import (  # noqa: E402
    BaseExtractor,
    ExtractionContext,
)

# Import from local migration module
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import get_or_create_with_history  # noqa: E402

# Database alias for migration
DB_ALIAS = "migr_dev"


def get_all_org_units(extractor: BaseExtractor) -> list[dict]:
    """Get all organizational units from FishTalk."""
    query = """
    SELECT ou.OrgUnitID, ou.Name, l.Latitude, l.Longitude
    FROM dbo.OrganisationUnit ou
    LEFT JOIN dbo.Locations l ON l.LocationID = ou.LocationID
    WHERE ou.Active = 1
    """
    return extractor._run_sqlcmd(query, ["OrgUnitID", "Name", "Latitude", "Longitude"])


def get_all_containers(extractor: BaseExtractor) -> list[dict]:
    """Get all containers from FishTalk with their org unit."""
    query = """
    SELECT c.ContainerID, c.OrgUnitID, c.ContainerName, c.OfficialID, c.ContainerType
    FROM dbo.Containers c
    """
    return extractor._run_sqlcmd(query, ["ContainerID", "OrgUnitID", "ContainerName", "OfficialID", 
                                          "ContainerType"])


def get_container_geography_mapping() -> dict[str, str]:
    """Get geography mapping for containers based on container grouping."""
    # Read from the grouping CSV if it exists
    grouping_csv = Path(__file__).parent.parent / "data" / "container_grouping.csv"
    mapping = {}
    if grouping_csv.exists():
        with open(grouping_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("geography"):
                    mapping[row["ContainerID"]] = row["geography"]
    return mapping


def determine_container_bucket(container_type: str, official_id: str) -> str:
    """Determine if container is sea or freshwater based on type and ID."""
    container_type = (container_type or "").lower()
    official_id = (official_id or "").upper()
    
    # Sea indicators
    if any(x in container_type for x in ["cage", "pen", "ring", "net"]):
        return "sea"
    if any(x in official_id for x in ["CAGE", "PEN", "RING", "M-"]):
        return "sea"
    
    # Default to freshwater
    return "freshwater"


def hall_label_from_group(group_name: str | None) -> str | None:
    """Extract hall label from container group name."""
    if not group_name:
        return None
    # Remove common prefixes/suffixes
    label = group_name.strip()
    for prefix in ["Tank ", "Hall "]:
        if label.startswith(prefix):
            label = label[len(prefix):]
    return label[:100] if label else None


def hall_label_from_official(official_id: str | None) -> str | None:
    """Extract hall label from official ID (e.g., 'T1-A' -> 'T1')."""
    if not official_id:
        return None
    parts = official_id.split("-")
    if len(parts) >= 1:
        return parts[0][:100]
    return None


def main():
    parser = argparse.ArgumentParser(description="Pre-create migration infrastructure")
    parser.add_argument("--geography", default="Faroe Islands",
                        help="Default geography for unmapped containers")
    parser.add_argument("--sql-profile", default="fishtalk",
                        help="SQL Server connection profile")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created without creating")
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("INFRASTRUCTURE PRE-MIGRATION")
    print("=" * 70)
    
    # Get history user
    User = get_user_model()
    try:
        history_user = User.objects.using(DB_ALIAS).get(username="system_admin")
    except User.DoesNotExist:
        history_user = User.objects.using(DB_ALIAS).first()
    history_reason = "FishTalk migration infrastructure"
    
    # Create extractor for FishTalk queries
    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))
    
    # Geography cache
    geography_cache: dict[str, Geography] = {}
    
    def get_geography(name: str) -> Geography:
        if name not in geography_cache:
            geo = Geography.objects.using(DB_ALIAS).filter(name__icontains=name).first()
            if not geo:
                geo = Geography.objects.using(DB_ALIAS).first()
            geography_cache[name] = geo
        return geography_cache[name]
    
    # Fetch FishTalk data
    print("\n--- Fetching FishTalk Data ---")
    org_units = get_all_org_units(extractor)
    print(f"  Org units: {len(org_units)}")
    
    containers = get_all_containers(extractor)
    print(f"  Containers: {len(containers)}")
    
    geo_mapping = get_container_geography_mapping()
    print(f"  Geography mappings: {len(geo_mapping)}")
    
    # Build lookup structures
    org_by_id = {o["OrgUnitID"]: o for o in org_units}
    containers_by_org: dict[str, list[dict]] = {}
    for c in containers:
        org_id = c["OrgUnitID"]
        if org_id not in containers_by_org:
            containers_by_org[org_id] = []
        containers_by_org[org_id].append(c)
    
    # Determine sea vs freshwater for each container
    container_bucket: dict[str, str] = {}
    for c in containers:
        cid = c["ContainerID"]
        container_bucket[cid] = determine_container_bucket(
            c.get("ContainerType"), c.get("OfficialID")
        )
    
    # Determine which org units have sea vs freshwater
    org_has_sea: dict[str, bool] = {}
    org_has_freshwater: dict[str, bool] = {}
    for org_id, org_containers in containers_by_org.items():
        org_has_sea[org_id] = any(
            container_bucket.get(c["ContainerID"]) == "sea" for c in org_containers
        )
        org_has_freshwater[org_id] = any(
            container_bucket.get(c["ContainerID"], "freshwater") != "sea" for c in org_containers
        )
    
    print(f"\n--- Analysis ---")
    print(f"  Org units with freshwater: {sum(org_has_freshwater.values())}")
    print(f"  Org units with sea: {sum(org_has_sea.values())}")
    print(f"  Freshwater containers: {sum(1 for b in container_bucket.values() if b == 'freshwater')}")
    print(f"  Sea containers: {sum(1 for b in container_bucket.values() if b == 'sea')}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would create infrastructure. Exiting.")
        return 0
    
    # Create container types
    print("\n--- Creating Container Types ---")
    tank_type, created = get_or_create_with_history(
        ContainerType,
        lookup={"name": "FishTalk Imported Tank"},
        defaults={
            "category": "TANK",
            "max_volume_m3": Decimal("999999.99"),
            "description": "Auto-created for FishTalk migration",
        },
        user=history_user,
        reason=history_reason,
        using=DB_ALIAS,
    )
    print(f"  Tank type: {'created' if created else 'exists'}")
    
    pen_type, created = get_or_create_with_history(
        ContainerType,
        lookup={"name": "FishTalk Imported Pen"},
        defaults={
            "category": "PEN",
            "max_volume_m3": Decimal("999999.99"),
            "description": "Auto-created for FishTalk migration",
        },
        user=history_user,
        reason=history_reason,
        using=DB_ALIAS,
    )
    print(f"  Pen type: {'created' if created else 'exists'}")
    
    # Create Areas and FreshwaterStations
    print("\n--- Creating Areas and FreshwaterStations ---")
    station_by_org: dict[str, FreshwaterStation] = {}
    area_by_org: dict[str, Area] = {}
    
    stations_created = 0
    stations_existed = 0
    areas_created = 0
    areas_existed = 0
    
    for org_id in sorted(containers_by_org.keys()):
        org = org_by_id.get(org_id, {})
        org_name = (org.get("Name") or org_id)[:80]
        lat = Decimal(str(org.get("Latitude") or 0)).quantize(Decimal("0.000001"))
        lon = Decimal(str(org.get("Longitude") or 0)).quantize(Decimal("0.000001"))
        
        # Determine geography from containers
        org_containers = containers_by_org.get(org_id, [])
        org_geo_candidates = [
            geo_mapping.get(c["ContainerID"])
            for c in org_containers
            if geo_mapping.get(c["ContainerID"])
        ]
        if org_geo_candidates:
            org_geo_name = Counter(org_geo_candidates).most_common(1)[0][0]
        else:
            org_geo_name = args.geography
        geography = get_geography(org_geo_name)
        
        # Create FreshwaterStation if org has freshwater containers
        if org_has_freshwater.get(org_id, False):
            station, created = get_or_create_with_history(
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
                using=DB_ALIAS,
            )
            station_by_org[org_id] = station
            if created:
                stations_created += 1
                # Store in ExternalIdMap
                ExternalIdMap.objects.using(DB_ALIAS).get_or_create(
                    source_system="FishTalk",
                    source_model="OrgUnit_FW",
                    source_identifier=org_id,
                    defaults={
                        "target_model": "FreshwaterStation",
                        "target_object_id": station.pk,
                    }
                )
            else:
                stations_existed += 1
        
        # Create Area if org has sea containers
        if org_has_sea.get(org_id, False):
            area, created = get_or_create_with_history(
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
                using=DB_ALIAS,
            )
            area_by_org[org_id] = area
            if created:
                areas_created += 1
                # Store in ExternalIdMap
                ExternalIdMap.objects.using(DB_ALIAS).get_or_create(
                    source_system="FishTalk",
                    source_model="OrgUnit_Sea",
                    source_identifier=org_id,
                    defaults={
                        "target_model": "Area",
                        "target_object_id": area.pk,
                    }
                )
            else:
                areas_existed += 1
    
    print(f"  FreshwaterStations: {stations_created} created, {stations_existed} existed")
    print(f"  Areas: {areas_created} created, {areas_existed} existed")
    
    # Create Halls
    print("\n--- Creating Halls ---")
    hall_by_org_group: dict[tuple[str, str], Hall] = {}
    fallback_hall_by_org: dict[str, Hall] = {}
    halls_created = 0
    halls_existed = 0
    
    for org_id, org_containers in containers_by_org.items():
        if org_id not in station_by_org:
            continue  # No freshwater station for this org
        
        station = station_by_org[org_id]
        org_name = (org_by_id.get(org_id, {}).get("Name") or org_id)[:80]
        
        # Group containers by hall label
        for c in org_containers:
            cid = c["ContainerID"]
            if container_bucket.get(cid) == "sea":
                continue  # Sea containers don't need halls
            
            # Use OfficialID to derive hall grouping (ContainerGroup not available)
            group_label = hall_label_from_official(c.get("OfficialID"))
            
            if group_label:
                hall_key = (org_id, group_label)
                if hall_key not in hall_by_org_group:
                    hall, created = get_or_create_with_history(
                        Hall,
                        lookup={"name": group_label[:100], "freshwater_station": station},
                        defaults={
                            "description": f"Imported from FishTalk ({group_label})",
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                        using=DB_ALIAS,
                    )
                    hall_by_org_group[hall_key] = hall
                    if created:
                        halls_created += 1
                    else:
                        halls_existed += 1
            else:
                # Fallback hall for containers without group
                if org_id not in fallback_hall_by_org:
                    hall, created = get_or_create_with_history(
                        Hall,
                        lookup={"name": f"FT {org_name} Hall"[:100], "freshwater_station": station},
                        defaults={
                            "description": "Fallback hall from FishTalk migration",
                            "active": True,
                        },
                        user=history_user,
                        reason=history_reason,
                        using=DB_ALIAS,
                    )
                    fallback_hall_by_org[org_id] = hall
                    if created:
                        halls_created += 1
                    else:
                        halls_existed += 1
    
    print(f"  Halls: {halls_created} created, {halls_existed} existed")
    
    # Create Containers
    print("\n--- Creating Containers ---")
    containers_created = 0
    containers_existed = 0
    
    for c in containers:
        cid = c["ContainerID"]
        org_id = c["OrgUnitID"]
        
        # Check if already migrated
        existing = ExternalIdMap.objects.using(DB_ALIAS).filter(
            source_system="FishTalk",
            source_model="Containers",
            source_identifier=cid
        ).first()
        if existing:
            containers_existed += 1
            continue
        
        bucket = container_bucket.get(cid, "freshwater")
        if bucket == "sea":
            container_type = pen_type
            area = area_by_org.get(org_id)
            hall = None
            if not area:
                # Skip if no area for this org
                continue
        else:
            container_type = tank_type
            area = None
            
            # Find hall - use OfficialID to derive grouping
            group_label = hall_label_from_official(c.get("OfficialID"))
            
            if group_label:
                hall_key = (org_id, group_label)
                hall = hall_by_org_group.get(hall_key)
            else:
                hall = fallback_hall_by_org.get(org_id)
            
            if not hall:
                # Skip if no hall for this container
                continue
        
        container_name = (c.get("ContainerName") or c.get("OfficialID") or cid)[:100]
        
        container_obj, created = get_or_create_with_history(
            Container,
            lookup={"name": container_name, "hall": hall, "area": area},
            defaults={
                "container_type": container_type,
                "volume_m3": Decimal("1000"),
                "max_biomass_kg": Decimal("100000"),
                "active": True,
            },
            user=history_user,
            reason=history_reason,
            using=DB_ALIAS,
        )
        
        if created:
            containers_created += 1
            ExternalIdMap.objects.using(DB_ALIAS).create(
                source_system="FishTalk",
                source_model="Containers",
                source_identifier=cid,
                target_model="Container",
                target_object_id=container_obj.pk,
            )
        else:
            containers_existed += 1
    
    print(f"  Containers: {containers_created} created, {containers_existed} existed")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  FreshwaterStations: {stations_created + stations_existed}")
    print(f"  Areas: {areas_created + areas_existed}")
    print(f"  Halls: {halls_created + halls_existed}")
    print(f"  Containers: {containers_created + containers_existed}")
    print("\n[SUCCESS] Infrastructure pre-migration complete")
    print("You can now run pilot_migrate_batch_parallel.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
