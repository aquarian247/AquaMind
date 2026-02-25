"""
Seed demo transport carrier data for station-to-sea workflow testing.

Creates:
- Truck and vessel transport carriers
- Carrier tank containers (linked via Container.carrier)
- Historian tag links per tank/parameter
- Baseline environmental readings used by snapshot capture

The command is idempotent and safe to run repeatedly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.historian.models import HistorianTag, HistorianTagLink
from apps.infrastructure.models import Container, ContainerType, Geography, TransportCarrier


@dataclass(frozen=True)
class CarrierSeedConfig:
    carrier_type: str
    count: int
    tanks_per_carrier: int
    capacity_m3: Decimal


PARAMETER_MATCHERS: list[tuple[str, list[str]]] = [
    ("Temperature", ["temperature", "temp"]),
    ("Dissolved Oxygen", ["dissolved oxygen", "oxygen", "o2"]),
    ("Salinity", ["salinity"]),
    ("pH", ["ph"]),
    ("Ammonia", ["ammonia"]),
    ("Nitrite", ["nitrite"]),
    ("Nitrate", ["nitrate"]),
]

READING_DEFAULTS = {
    "temperature": Decimal("9.80"),
    "dissolved oxygen": Decimal("8.40"),
    "salinity": Decimal("31.20"),
    "ph": Decimal("7.20"),
    "ammonia": Decimal("0.0300"),
    "nitrite": Decimal("0.0120"),
    "nitrate": Decimal("1.8000"),
}


class Command(BaseCommand):
    help = (
        "Seed transport demo carriers/tanks plus historian links and baseline readings "
        "for dynamic station-to-sea workflows."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--geography",
            type=str,
            default="",
            help="Geography name to attach carriers to (default: first available geography).",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="DEMO",
            help="Name prefix for seeded carriers/tanks (default: DEMO).",
        )
        parser.add_argument(
            "--trucks",
            type=int,
            default=15,
            help="Number of truck carriers to seed (default: 15).",
        )
        parser.add_argument(
            "--vessels",
            type=int,
            default=2,
            help="Number of vessel carriers to seed (default: 2).",
        )
        parser.add_argument(
            "--tanks-per-truck",
            type=int,
            default=10,
            help="Truck tanks per carrier (default: 10).",
        )
        parser.add_argument(
            "--tanks-per-vessel",
            type=int,
            default=10,
            help="Vessel tanks per carrier (default: 10).",
        )
        parser.add_argument(
            "--skip-tags",
            action="store_true",
            help="Skip historian tag and link creation.",
        )
        parser.add_argument(
            "--skip-readings",
            action="store_true",
            help="Skip baseline environmental reading creation.",
        )

    def handle(self, *args, **options):
        trucks = options["trucks"]
        vessels = options["vessels"]
        tanks_per_truck = options["tanks_per_truck"]
        tanks_per_vessel = options["tanks_per_vessel"]
        prefix = options["prefix"].strip().upper()
        skip_tags = options["skip_tags"]
        skip_readings = options["skip_readings"]

        for name, value in [
            ("--trucks", trucks),
            ("--vessels", vessels),
            ("--tanks-per-truck", tanks_per_truck),
            ("--tanks-per-vessel", tanks_per_vessel),
        ]:
            if value < 0:
                raise CommandError(f"{name} cannot be negative.")
        if not prefix:
            raise CommandError("--prefix cannot be empty.")

        geography = self._resolve_geography(options["geography"])
        tank_type = self._resolve_tank_type()
        parameters = self._resolve_parameters()

        if (not skip_tags or not skip_readings) and not parameters:
            raise CommandError(
                "No environmental parameters found (Temperature/Oxygen/pH/etc). "
                "Create parameters before seeding tags/readings."
            )

        configs = [
            CarrierSeedConfig(
                carrier_type="TRUCK",
                count=trucks,
                tanks_per_carrier=tanks_per_truck,
                capacity_m3=Decimal("120.00"),
            ),
            CarrierSeedConfig(
                carrier_type="VESSEL",
                count=vessels,
                tanks_per_carrier=tanks_per_vessel,
                capacity_m3=Decimal("2500.00"),
            ),
        ]

        stats = {
            "carriers_created": 0,
            "carriers_updated": 0,
            "tanks_created": 0,
            "tanks_updated": 0,
            "tags_created": 0,
            "tag_links_created": 0,
            "readings_created": 0,
            "readings_updated": 0,
        }

        self.stdout.write(
            f"Seeding transport demo data in geography '{geography.name}' using tank type '{tank_type.name}'."
        )

        with transaction.atomic():
            seeded_tanks: list[Container] = []
            for config in configs:
                if config.count == 0:
                    continue
                carriers, carrier_stats = self._seed_carriers_and_tanks(
                    geography=geography,
                    tank_type=tank_type,
                    config=config,
                    prefix=prefix,
                )
                stats["carriers_created"] += carrier_stats["carriers_created"]
                stats["carriers_updated"] += carrier_stats["carriers_updated"]
                stats["tanks_created"] += carrier_stats["tanks_created"]
                stats["tanks_updated"] += carrier_stats["tanks_updated"]
                for carrier in carriers:
                    seeded_tanks.extend(
                        Container.objects.filter(carrier=carrier, active=True).order_by("name")
                    )

            if seeded_tanks and not skip_tags:
                tags_created, links_created = self._seed_tag_links(
                    tanks=seeded_tanks,
                    parameters=parameters,
                    prefix=prefix,
                )
                stats["tags_created"] += tags_created
                stats["tag_links_created"] += links_created

            if seeded_tanks and not skip_readings:
                readings_created, readings_updated = self._seed_baseline_readings(
                    tanks=seeded_tanks,
                    parameters=parameters,
                )
                stats["readings_created"] += readings_created
                stats["readings_updated"] += readings_updated

        self.stdout.write(self.style.SUCCESS("Transport demo data seeded successfully."))
        for key, value in stats.items():
            self.stdout.write(f"- {key}: {value}")

    def _resolve_geography(self, geography_name: str) -> Geography:
        if geography_name:
            geography = Geography.objects.filter(name__iexact=geography_name.strip()).first()
            if not geography:
                raise CommandError(f"Geography '{geography_name}' not found.")
            return geography

        geography = Geography.objects.order_by("id").first()
        if not geography:
            raise CommandError("No geography records found. Seed infrastructure base data first.")
        return geography

    def _resolve_tank_type(self) -> ContainerType:
        preferred_names = [
            "Pre-Transfer Tanks - Post-Smolt",
            "Large Tanks - Smolt",
            "Medium Tanks - Parr",
        ]
        for name in preferred_names:
            candidate = ContainerType.objects.filter(name__iexact=name).first()
            if candidate:
                return candidate

        fallback = ContainerType.objects.filter(name__icontains="tank").order_by("id").first()
        if fallback:
            return fallback

        raise CommandError(
            "No suitable tank ContainerType found. Please create at least one tank type."
        )

    def _resolve_parameters(self) -> list[EnvironmentalParameter]:
        parameters: list[EnvironmentalParameter] = []
        for canonical_name, aliases in PARAMETER_MATCHERS:
            match = EnvironmentalParameter.objects.filter(name__iexact=canonical_name).first()
            if not match:
                name_query = Q()
                for alias in aliases:
                    name_query |= Q(name__icontains=alias)
                match = EnvironmentalParameter.objects.filter(name_query).order_by("id").first()
            if match and match not in parameters:
                parameters.append(match)
        return parameters

    def _seed_carriers_and_tanks(
        self,
        *,
        geography: Geography,
        tank_type: ContainerType,
        config: CarrierSeedConfig,
        prefix: str,
    ) -> tuple[list[TransportCarrier], dict[str, int]]:
        carriers: list[TransportCarrier] = []
        stats = {
            "carriers_created": 0,
            "carriers_updated": 0,
            "tanks_created": 0,
            "tanks_updated": 0,
        }

        for index in range(1, config.count + 1):
            carrier_name = f"{prefix}-{config.carrier_type}-{index:02d}"
            defaults = {
                "carrier_type": config.carrier_type,
                "geography": geography,
                "capacity_m3": config.capacity_m3,
                "active": True,
                "license_plate": (
                    f"{prefix[:3]}-{index:03d}" if config.carrier_type == "TRUCK" else ""
                ),
                "imo_number": (
                    f"{9700000 + index}" if config.carrier_type == "VESSEL" else ""
                ),
                "captain_contact": "",
            }
            carrier, created = TransportCarrier.objects.get_or_create(
                name=carrier_name,
                defaults=defaults,
            )
            if created:
                stats["carriers_created"] += 1
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(carrier, field) != value:
                        setattr(carrier, field, value)
                        changed = True
                if changed:
                    carrier.save()
                    stats["carriers_updated"] += 1
            carriers.append(carrier)

            if config.tanks_per_carrier == 0:
                continue

            volume_per_tank = (
                config.capacity_m3 / Decimal(config.tanks_per_carrier)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            max_allowed = tank_type.max_volume_m3
            if volume_per_tank > max_allowed:
                volume_per_tank = max_allowed
            if volume_per_tank <= 0:
                volume_per_tank = Decimal("1.00")

            max_biomass = (volume_per_tank * Decimal("70.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if max_biomass <= 0:
                max_biomass = Decimal("1.00")

            for tank_index in range(1, config.tanks_per_carrier + 1):
                tank_name = f"{carrier.name}-T{tank_index:02d}"
                container, tank_created = Container.objects.get_or_create(
                    name=tank_name,
                    carrier=carrier,
                    defaults={
                        "container_type": tank_type,
                        "volume_m3": volume_per_tank,
                        "max_biomass_kg": max_biomass,
                        "feed_recommendations_enabled": False,
                        "active": True,
                    },
                )
                if tank_created:
                    stats["tanks_created"] += 1
                else:
                    changed = False
                    updates = {
                        "container_type": tank_type,
                        "hall": None,
                        "area": None,
                        "volume_m3": volume_per_tank,
                        "max_biomass_kg": max_biomass,
                        "feed_recommendations_enabled": False,
                        "active": True,
                    }
                    for field, value in updates.items():
                        if getattr(container, field) != value:
                            setattr(container, field, value)
                            changed = True
                    if changed:
                        container.save()
                        stats["tanks_updated"] += 1

        return carriers, stats

    def _seed_tag_links(
        self,
        *,
        tanks: list[Container],
        parameters: list[EnvironmentalParameter],
        prefix: str,
    ) -> tuple[int, int]:
        tags_created = 0
        links_created = 0

        for tank in tanks:
            carrier = tank.carrier
            if not carrier:
                continue
            for parameter in parameters:
                token = self._slugify(parameter.name)
                tag_name = (
                    f"{prefix}.{carrier.carrier_type}.{self._slugify(carrier.name)}."
                    f"{self._slugify(tank.name)}.{token}"
                )
                tag, tag_created = HistorianTag.objects.get_or_create(
                    tag_name=tag_name,
                    defaults={
                        "description": (
                            f"Seeded {parameter.name} tag for {tank.name} ({carrier.name})"
                        ),
                        "unit": parameter.unit,
                        "source_system": "AVEVA",
                        "metadata": {"seed": "transport_demo"},
                    },
                )
                if tag_created:
                    tags_created += 1
                link, link_created = HistorianTagLink.objects.get_or_create(
                    tag=tag,
                    defaults={
                        "container": tank,
                        "parameter": parameter,
                        "notes": "[transport_demo_seed]",
                        "metadata": {"seed": "transport_demo"},
                    },
                )
                if link_created:
                    links_created += 1
                elif link.container_id != tank.id or link.parameter_id != parameter.id:
                    link.container = tank
                    link.parameter = parameter
                    if "[transport_demo_seed]" not in (link.notes or ""):
                        link.notes = f"{link.notes}\n[transport_demo_seed]".strip()
                    metadata = dict(link.metadata or {})
                    metadata["seed"] = "transport_demo"
                    link.metadata = metadata
                    link.save()

        return tags_created, links_created

    def _seed_baseline_readings(
        self,
        *,
        tanks: list[Container],
        parameters: list[EnvironmentalParameter],
    ) -> tuple[int, int]:
        readings_created = 0
        readings_updated = 0
        reading_time = timezone.now() - timedelta(minutes=5)

        for tank in tanks:
            for parameter in parameters:
                seed_note = (
                    f"[transport_demo_seed] container={tank.id};parameter={parameter.id}"
                )
                value = self._default_value_for_parameter(parameter.name)
                existing = (
                    EnvironmentalReading.objects.filter(
                        container=tank,
                        parameter=parameter,
                        notes=seed_note,
                    )
                    .order_by("id")
                    .first()
                )
                if existing:
                    existing.value = value
                    existing.reading_time = reading_time
                    existing.is_manual = True
                    existing.sensor = None
                    existing.batch = None
                    existing.batch_container_assignment = None
                    existing.recorded_by = None
                    existing.save()
                    readings_updated += 1
                else:
                    EnvironmentalReading.objects.create(
                        parameter=parameter,
                        container=tank,
                        value=value,
                        reading_time=reading_time,
                        is_manual=True,
                        notes=seed_note,
                    )
                    readings_created += 1

        return readings_created, readings_updated

    def _default_value_for_parameter(self, parameter_name: str) -> Decimal:
        lowered = parameter_name.strip().lower()
        if lowered in READING_DEFAULTS:
            return READING_DEFAULTS[lowered]
        for token, value in READING_DEFAULTS.items():
            if token in lowered:
                return value
        return Decimal("1.0000")

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().upper())
        return normalized.strip("_") or "UNKNOWN"
