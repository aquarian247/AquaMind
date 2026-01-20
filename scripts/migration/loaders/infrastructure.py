"""Load infrastructure master data into AquaMind."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import logging
from typing import Dict

from django.db import transaction

from apps.infrastructure.models import Area, Container, ContainerType, FreshwaterStation, Geography, Hall

from scripts.migration.loaders.base import BaseLoader

LOGGER = logging.getLogger("migration.infrastructure")

FAROE_SITEGROUPS = {"WEST", "NORTH", "SOUTH"}
SCOTLAND_SITES_FRESHWATER_ARCHIVE = {
    "FW06 LOCH AILORT",
    "FW07 LOCHAILORT",
    "FW10 SALEN",
    "FW11 SALEN",
    "FW12 LOCH AILORT",
    "KYLEAKIN",
    "LOCH HOURN",
    "LOCH RO",
    "LOCH NEVIS",
    "LOCH RANZA",
    "LOCH ARKAIG",
    "LOCH LEVEN",
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


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).split()).strip()


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


def bucket_from_prod_stage(prod_stage: str | None) -> str | None:
    upper = normalize_key(prod_stage)
    if not upper:
        return None
    if "MARINE" in upper or "SEA" in upper:
        return "sea"
    if any(token in upper for token in ("HATCH", "FRESH", "SMOLT", "PARR", "FRY", "ALEVIN", "EGG", "BROOD")):
        return "freshwater"
    return None


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


class InfrastructureLoader(BaseLoader):
    @transaction.atomic
    def load_geographies(self, rows):
        stats = {"created": 0, "updated": 0, "skipped": 0}
        for row in rows:
            if self.dry_run:
                stats["skipped"] += 1
                continue

            name = (row.get("NationID") or "Unknown").strip()
            defaults = {"description": "Imported from FishTalk"}
            geography, created = Geography.objects.get_or_create(
                name=name[:100], defaults=defaults
            )

            if created:
                stats["created"] += 1
            elif self._update_fields(geography, defaults):
                stats["updated"] += 1

            if row.get("NationID"):
                self.record_external_id(
                    source_model="Locations",
                    source_identifier=row["NationID"],
                    instance=geography,
                    metadata={"kind": "geography", "name": geography.name},
                )
        return stats

    @transaction.atomic
    def load_locations(self, rows):
        stats = {"created": 0, "updated": 0, "skipped": 0}
        for row in rows:
            if self.dry_run:
                stats["skipped"] += 1
                continue

            geography = Geography.objects.filter(name=row.get("NationID") or "Unknown").first()
            if geography is None:
                geography, _ = Geography.objects.get_or_create(
                    name="Unknown", defaults={"description": "Imported placeholder"}
                )

            area_name = (row.get("Name") or row.get("LocationID") or "Unnamed")[:100]
            defaults = {
                "latitude": self._to_decimal(row.get("Latitude"), 0),
                "longitude": self._to_decimal(row.get("Longitude"), 0),
                "max_biomass": Decimal("0"),
                "active": True,
            }

            try:
                area, created = Area.objects.get_or_create(
                    name=area_name,
                    geography=geography,
                    defaults=defaults,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.warning("Skipping location %s due to %s", row.get("LocationID"), exc)
                continue

            if created:
                stats["created"] += 1
            elif self._update_fields(area, defaults):
                stats["updated"] += 1

            if row.get("LocationID"):
                self.record_external_id(
                    source_model="Locations",
                    source_identifier=row["LocationID"],
                    instance=area,
                    metadata={
                        "kind": "area",
                        "name": area.name,
                        "nation_id": row.get("NationID"),
                    },
                )
        return stats

    @transaction.atomic
    def load_sites_and_containers(self, site_rows, container_rows):
        stats = {
            "stations": {"created": 0, "updated": 0, "skipped": 0},
            "areas": {"created": 0, "updated": 0, "skipped": 0},
            "halls": {"created": 0, "updated": 0, "skipped": 0},
            "containers": {"created": 0, "updated": 0, "skipped": 0},
        }
        if not container_rows:
            return stats

        site_by_id = {
            row.get("OrgUnitID"): row
            for row in site_rows
            if row.get("OrgUnitID")
        }
        containers_by_org: dict[str, list[dict]] = {}
        for row in container_rows:
            org_id = row.get("OrgUnitID")
            if not org_id:
                stats["containers"]["skipped"] += 1
                continue
            containers_by_org.setdefault(org_id, []).append(row)

        if self.dry_run:
            stats["stations"]["skipped"] = len(containers_by_org)
            stats["areas"]["skipped"] = len(containers_by_org)
            stats["halls"]["skipped"] = len({
                (
                    org_id,
                    normalize_label(row.get("ContainerGroup"))
                    or hall_label_from_official(row.get("OfficialID")),
                )
                for org_id, rows in containers_by_org.items()
                for row in rows
                if normalize_label(row.get("ContainerGroup"))
                or hall_label_from_official(row.get("OfficialID"))
            })
            stats["containers"]["skipped"] += len(container_rows)
            return stats

        tank_type, _ = ContainerType.objects.get_or_create(
            name="FishTalk Imported Tank",
            defaults={
                "category": "TANK",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
        )
        pen_type, _ = ContainerType.objects.get_or_create(
            name="FishTalk Imported Pen",
            defaults={
                "category": "PEN",
                "max_volume_m3": Decimal("999999.99"),
                "description": "Auto-created for FishTalk migration",
            },
        )

        station_by_org: dict[str, FreshwaterStation] = {}
        area_by_org: dict[str, Area] = {}
        hall_by_group: dict[tuple[str, str], Hall] = {}

        for org_id, org_rows in containers_by_org.items():
            site_row = site_by_id.get(org_id, {})
            site_name_candidates = [
                normalize_label(row.get("Site") or row.get("OrgUnitName"))
                for row in org_rows
                if normalize_label(row.get("Site") or row.get("OrgUnitName"))
            ]
            if site_name_candidates:
                site_name = Counter(site_name_candidates).most_common(1)[0][0]
            else:
                site_name = normalize_label(site_row.get("Name") or org_id)

            site_group_candidates = [
                normalize_label(row.get("SiteGroup"))
                for row in org_rows
                if normalize_label(row.get("SiteGroup"))
            ]
            site_group = Counter(site_group_candidates).most_common(1)[0][0] if site_group_candidates else ""

            geo_name, _ = resolve_site_grouping(site_name, site_group)
            if not geo_name:
                geo_name = normalize_label(site_row.get("NationID")) or "Unknown"
            geography, geo_created = Geography.objects.get_or_create(
                name=geo_name[:100],
                defaults={"description": "Imported placeholder from FishTalk"},
            )
            if geo_created:
                LOGGER.info("[infra] created geography %s", geography.name)

            lat = self._to_decimal(site_row.get("Latitude"), 0)
            lon = self._to_decimal(site_row.get("Longitude"), 0)

            for row in org_rows:
                hall_label = hall_label_from_group(row.get("ContainerGroup"))
                if not hall_label:
                    hall_label = hall_label_from_official(row.get("OfficialID"))
                bucket = bucket_from_prod_stage(row.get("ProdStage"))
                if not bucket:
                    bucket = "freshwater" if hall_label else "sea"

                if bucket == "sea":
                    area = area_by_org.get(org_id)
                    if area is None:
                        defaults = {
                            "latitude": lat,
                            "longitude": lon,
                            "max_biomass": Decimal("0"),
                            "active": True,
                        }
                        area, created = Area.objects.get_or_create(
                            name=site_name[:100],
                            geography=geography,
                            defaults=defaults,
                        )
                        if created:
                            stats["areas"]["created"] += 1
                        elif self._update_fields(area, defaults):
                            stats["areas"]["updated"] += 1
                        area_by_org[org_id] = area
                        self.record_external_id(
                            source_model="OrganisationUnitArea",
                            source_identifier=org_id,
                            instance=area,
                            metadata={"site": site_name, "site_group": site_group},
                        )
                    container_type = pen_type
                    hall = None
                else:
                    station = station_by_org.get(org_id)
                    if station is None:
                        defaults = {
                            "station_type": "FRESHWATER",
                            "geography": geography,
                            "latitude": lat,
                            "longitude": lon,
                            "description": "Imported placeholder from FishTalk",
                            "active": True,
                        }
                        station, created = FreshwaterStation.objects.get_or_create(
                            name=site_name[:100],
                            defaults=defaults,
                        )
                        if created:
                            stats["stations"]["created"] += 1
                        elif self._update_fields(station, defaults):
                            stats["stations"]["updated"] += 1
                        station_by_org[org_id] = station
                        self.record_external_id(
                            source_model="OrganisationUnitStation",
                            source_identifier=org_id,
                            instance=station,
                            metadata={"site": site_name, "site_group": site_group},
                        )
                    if not hall_label:
                        hall_label = f"{site_name} Hall"
                    hall_key = (org_id, hall_label)
                    hall = hall_by_group.get(hall_key)
                    if hall is None:
                        defaults = {
                            "description": "Imported placeholder from FishTalk",
                            "active": True,
                        }
                        hall, created = Hall.objects.get_or_create(
                            name=hall_label[:100],
                            freshwater_station=station,
                            defaults=defaults,
                        )
                        if created:
                            stats["halls"]["created"] += 1
                        elif self._update_fields(hall, defaults):
                            stats["halls"]["updated"] += 1
                        hall_by_group[hall_key] = hall
                        hall_identifier = row.get("ContainerGroupID") or hall_label
                        self.record_external_id(
                            source_model="OrganisationUnitHall",
                            source_identifier=f"{org_id}:{hall_identifier}",
                            instance=hall,
                            metadata={
                                "site": site_name,
                                "site_group": site_group,
                                "container_group": row.get("ContainerGroup"),
                                "container_group_id": row.get("ContainerGroupID"),
                            },
                        )

                    container_type = tank_type
                    area = None

                container_id = row.get("ContainerID")
                if not container_id:
                    stats["containers"]["skipped"] += 1
                    continue
                container_name = normalize_label(row.get("ContainerName")) or container_id
                container_defaults = {
                    "name": f"FT {container_name}"[:100],
                    "container_type": container_type,
                    "hall": hall,
                    "area": area,
                    "volume_m3": Decimal("0.00"),
                    "max_biomass_kg": Decimal("0.00"),
                    "feed_recommendations_enabled": True,
                    "active": True,
                }

                container, created = Container.objects.get_or_create(
                    name=container_defaults["name"],
                    hall=hall,
                    area=area,
                    defaults=container_defaults,
                )
                if created:
                    stats["containers"]["created"] += 1
                elif self._update_fields(container, container_defaults):
                    stats["containers"]["updated"] += 1

                self.record_external_id(
                    source_model="Containers",
                    source_identifier=container_id,
                    instance=container,
                    metadata={
                        "container_name": row.get("ContainerName"),
                        "official_id": row.get("OfficialID"),
                        "org_unit_id": org_id,
                        "site": row.get("Site"),
                        "site_group": row.get("SiteGroup"),
                        "company": row.get("Company"),
                        "prod_stage": row.get("ProdStage"),
                        "container_group": row.get("ContainerGroup"),
                        "container_group_id": row.get("ContainerGroupID"),
                        "bucket": bucket,
                    },
                )
        return stats

    def _update_fields(self, instance, values: Dict[str, object]) -> bool:
        """Update provided fields when values differ."""
        dirty_fields = []
        for field_name, new_value in values.items():
            if new_value is None:
                continue
            if getattr(instance, field_name) != new_value:
                setattr(instance, field_name, new_value)
                dirty_fields.append(field_name)

        if dirty_fields:
            instance.save(update_fields=dirty_fields)
            return True
        return False

    def _to_decimal(self, value, default=0):
        try:
            return Decimal(str(value)).quantize(Decimal("0.000001"))
        except (InvalidOperation, TypeError):
            return Decimal(default)
