"""Django loader skeletons for infrastructure entities."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction

from apps.infrastructure import models as infra_models

from .service_helpers import (
    MIGRATION_SOURCE_SYSTEM,
    SOURCE_MODEL_AREA,
    SOURCE_MODEL_CONTAINER,
    SOURCE_MODEL_GEOGRAPHY,
    SOURCE_MODEL_HALL,
    SOURCE_MODEL_STATION,
    ensure_external_id_map,
    fetch_staging_rows,
    get_external_id_map,
    with_transaction,
)


def load_infra(*, connection_alias: str = "default") -> None:
    """Run all infra loaders in dependency order."""
    load_geography(connection_alias=connection_alias)
    load_freshwater_stations(connection_alias=connection_alias)
    load_halls(connection_alias=connection_alias)
    load_areas(connection_alias=connection_alias)
    load_containers(connection_alias=connection_alias)


@with_transaction
def load_geography(*, connection_alias: str = "default") -> None:
    """Load infrastructure_geography from staging derived data."""
    rows = fetch_staging_rows(
        "stg_infra_orgunit_geo",
        columns="DISTINCT DerivedGeo",
        where_sql="DerivedGeo IS NOT NULL",
        connection_alias=connection_alias,
    )

    for row in rows:
        derived_geo = row.get("DerivedGeo")
        if not derived_geo:
            continue

        existing = get_external_id_map(
            source_model=SOURCE_MODEL_GEOGRAPHY,
            source_identifier=derived_geo,
        )
        if existing and getattr(existing, "content_object", None):
            continue

        # TODO: Use domain service to create geography with audit user.
        geography = infra_models.Geography.objects.create(
            name=derived_geo,
            active=True,
        )

        ensure_external_id_map(
            source_model=SOURCE_MODEL_GEOGRAPHY,
            source_identifier=derived_geo,
            target_object=geography,
            metadata={"derived_geo": derived_geo},
        )


@with_transaction
def load_freshwater_stations(*, connection_alias: str = "default") -> None:
    """Load infrastructure_freshwaterstation from staging orgunit data."""
    rows = fetch_staging_rows(
        "stg_infra_orgunit_geo",
        columns="OrgUnitID, Site, SiteGroup, LocationID, DerivedGeo",
        connection_alias=connection_alias,
    )

    for row in rows:
        org_unit_id = row.get("OrgUnitID")
        if not org_unit_id:
            continue

        existing = get_external_id_map(
            source_model=SOURCE_MODEL_STATION,
            source_identifier=str(org_unit_id),
        )
        if existing and getattr(existing, "content_object", None):
            continue

        station_name = row.get("Site") or f"OrgUnit {org_unit_id}"
        derived_geo = row.get("DerivedGeo")
        geography = _resolve_geography_by_derived(derived_geo)

        # TODO: Load lat/long from Locations staging. Default to 0 if missing.
        # TODO: Use domain service to create/update station with audit user.
        station = infra_models.FreshwaterStation.objects.create(
            name=station_name[:100],
            latitude=0,
            longitude=0,
            station_type="FRESHWATER",
            geography=geography,
        )

        ensure_external_id_map(
            source_model=SOURCE_MODEL_STATION,
            source_identifier=str(org_unit_id),
            target_object=station,
            metadata={
                "org_unit_id": org_unit_id,
                "site": row.get("Site"),
                "site_group": row.get("SiteGroup"),
                "location_id": row.get("LocationID"),
                "derived_geo": derived_geo,
            },
        )


@with_transaction
def load_halls(*, connection_alias: str = "default") -> None:
    """Load infrastructure_hall from staging container hall mapping."""
    rows = fetch_staging_rows(
        "stg_infra_container_hall",
        columns=(
            "DISTINCT OrgUnitID, ContainerGroupID, ContainerGroup, "
            "HallNameCandidate"
        ),
        connection_alias=connection_alias,
    )

    for row in rows:
        org_unit_id = row.get("OrgUnitID")
        container_group_id = row.get("ContainerGroupID")
        if not org_unit_id or not container_group_id:
            continue

        source_identifier = f"{org_unit_id}:{container_group_id}"
        existing = get_external_id_map(
            source_model=SOURCE_MODEL_HALL,
            source_identifier=source_identifier,
        )
        if existing and getattr(existing, "content_object", None):
            continue

        station = _resolve_station_by_orgunit(org_unit_id)
        hall_name = row.get("HallNameCandidate") or row.get("ContainerGroup")
        if not hall_name:
            hall_name = f"Hall {container_group_id}"

        # TODO: Normalize hall naming rules (whitespace, Høll -> Hall, etc.).
        # TODO: Use domain service to create/update hall with audit user.
        hall = infra_models.Hall.objects.create(
            name=hall_name[:100],
            freshwater_station=station,
            active=True,
        )

        ensure_external_id_map(
            source_model=SOURCE_MODEL_HALL,
            source_identifier=source_identifier,
            target_object=hall,
            metadata={
                "org_unit_id": org_unit_id,
                "container_group_id": container_group_id,
                "container_group": row.get("ContainerGroup"),
                "hall_name_candidate": row.get("HallNameCandidate"),
            },
        )


@with_transaction
def load_areas(*, connection_alias: str = "default") -> None:
    """Load infrastructure_area (sea areas) from staging orgunit data."""
    rows = fetch_staging_rows(
        "stg_infra_orgunit_geo",
        columns="OrgUnitID, Site, SiteGroup, LocationID, DerivedGeo",
        connection_alias=connection_alias,
    )

    for row in rows:
        org_unit_id = row.get("OrgUnitID")
        if not org_unit_id:
            continue

        existing = get_external_id_map(
            source_model=SOURCE_MODEL_AREA,
            source_identifier=str(org_unit_id),
        )
        if existing and getattr(existing, "content_object", None):
            continue

        area_name = row.get("Site") or f"OrgUnit {org_unit_id}"
        derived_geo = row.get("DerivedGeo")
        geography = _resolve_geography_by_derived(derived_geo)

        # TODO: Load lat/long from Locations staging. Default to 0 if missing.
        # TODO: Use domain service to create/update area with audit user.
        area = infra_models.Area.objects.create(
            name=area_name[:100],
            latitude=0,
            longitude=0,
            max_biomass=0,
            active=True,
            geography=geography,
        )

        ensure_external_id_map(
            source_model=SOURCE_MODEL_AREA,
            source_identifier=str(org_unit_id),
            target_object=area,
            metadata={
                "org_unit_id": org_unit_id,
                "site": row.get("Site"),
                "site_group": row.get("SiteGroup"),
                "location_id": row.get("LocationID"),
                "derived_geo": derived_geo,
            },
        )


@with_transaction
def load_containers(*, connection_alias: str = "default") -> None:
    """Load infrastructure_container from staging container data."""
    hall_rows = fetch_staging_rows(
        "stg_infra_container_hall",
        columns=(
            "ContainerID, OrgUnitID, ContainerGroupID, ContainerGroup, "
            "HallNameCandidate"
        ),
        connection_alias=connection_alias,
    )
    hall_by_container_id = {
        row.get("ContainerID"): row for row in hall_rows if row.get("ContainerID")
    }

    rows = fetch_staging_rows(
        "stg_infra_container_geo",
        columns=(
            "ContainerID, OrgUnitID, Site, SiteGroup, LocationID, "
            "DerivedGeo, Confidence"
        ),
        connection_alias=connection_alias,
    )

    for row in rows:
        container_id = row.get("ContainerID")
        if not container_id:
            continue

        existing = get_external_id_map(
            source_model=SOURCE_MODEL_CONTAINER,
            source_identifier=str(container_id),
        )
        if existing and getattr(existing, "content_object", None):
            continue

        hall_row = hall_by_container_id.get(container_id)
        hall = None
        area = None

        # TODO: Determine FW vs Sea classification using ProdStage + hall presence.
        if hall_row:
            org_unit_id = hall_row.get("OrgUnitID")
            container_group_id = hall_row.get("ContainerGroupID")
            if org_unit_id and container_group_id:
                hall = _resolve_hall_by_orgunit_group(org_unit_id, container_group_id)
        else:
            org_unit_id = row.get("OrgUnitID")
            if org_unit_id:
                area = _resolve_area_by_orgunit(org_unit_id)

        # TODO: Map container types to FishTalk Imported Tank/Pen.
        # TODO: Use domain service to create/update container with audit user.
        container = infra_models.Container.objects.create(
            name=f"FT-{container_id}"[:100],
            container_type=_resolve_container_type(),
            hall=hall,
            area=area,
            active=True,
        )

        ensure_external_id_map(
            source_model=SOURCE_MODEL_CONTAINER,
            source_identifier=str(container_id),
            target_object=container,
            metadata={
                "container_id": container_id,
                "org_unit_id": row.get("OrgUnitID"),
                "site": row.get("Site"),
                "site_group": row.get("SiteGroup"),
                "location_id": row.get("LocationID"),
                "derived_geo": row.get("DerivedGeo"),
                "confidence": row.get("Confidence"),
            },
        )


def _resolve_geography_by_derived(derived_geo: Optional[str]) -> Optional[Any]:
    if not derived_geo:
        return None
    ext = get_external_id_map(
        source_model=SOURCE_MODEL_GEOGRAPHY,
        source_identifier=derived_geo,
    )
    return getattr(ext, "content_object", None) if ext else None


def _resolve_station_by_orgunit(org_unit_id: Any) -> Optional[Any]:
    ext = get_external_id_map(
        source_model=SOURCE_MODEL_STATION,
        source_identifier=str(org_unit_id),
    )
    return getattr(ext, "content_object", None) if ext else None


def _resolve_hall_by_orgunit_group(org_unit_id: Any, container_group_id: Any) -> Optional[Any]:
    source_identifier = f"{org_unit_id}:{container_group_id}"
    ext = get_external_id_map(
        source_model=SOURCE_MODEL_HALL,
        source_identifier=source_identifier,
    )
    return getattr(ext, "content_object", None) if ext else None


def _resolve_area_by_orgunit(org_unit_id: Any) -> Optional[Any]:
    ext = get_external_id_map(
        source_model=SOURCE_MODEL_AREA,
        source_identifier=str(org_unit_id),
    )
    return getattr(ext, "content_object", None) if ext else None


def _resolve_container_type() -> Optional[Any]:
    """Resolve container type for FishTalk imported containers.

    TODO: Implement mapping to FishTalk Imported Tank/Pen.
    """
    return None
