"""Load infrastructure master data into AquaMind."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import logging
from typing import Dict

from django.db import transaction

from apps.infrastructure.models import Area, Geography

from scripts.migration.loaders.base import BaseLoader

LOGGER = logging.getLogger("migration.infrastructure")


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
