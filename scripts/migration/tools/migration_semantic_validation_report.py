#!/usr/bin/env python3
# flake8: noqa
"""Compare FishTalk aggregates to AquaMind aggregates for a migrated component.

This is a semantic validation (not raw row counts) to verify that
domain totals and key metrics align after migration.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db.models import Sum
from django.utils import timezone

from apps.batch.models import Batch, MortalityEvent, GrowthSample
from apps.batch.models.assignment import BatchContainerAssignment
from apps.environmental.models import EnvironmentalReading
from apps.harvest.models import HarvestEvent, HarvestLot
from apps.health.models import JournalEntry, Treatment, LiceCount
from apps.inventory.models import FeedingEvent
from apps.migration_support.models import ExternalIdMap
from scripts.migration.tools.etl_loader import ETLDataLoader


REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    start_time: datetime
    end_time: datetime | None


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
                    start_time=start,
                    end_time=end,
                )
            )
    members.sort(key=lambda m: m.start_time)
    return members


def resolve_component_key(report_dir: Path, *, component_id: int | None, component_key: str | None) -> str:
    if component_key:
        return component_key
    if component_id is None:
        raise ValueError("Provide --component-id or --component-key")

    import csv

    path = report_dir / "population_members.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("component_id") == str(component_id) and row.get("component_key"):
                return row["component_key"]

    raise ValueError("Unable to resolve component_key from report")


def to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def fmt(value: object, *, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, Decimal):
        quant = Decimal(f"1.{'0'*decimals}")
        return f"{value.quantize(quant)}"
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def numeric_diff(left: object, right: object) -> str:
    if left is None or right is None:
        return "n/a"
    try:
        return fmt(to_decimal(left) - to_decimal(right))
    except Exception:
        return "n/a"


def harvest_sum(rows: list[dict], field: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        total += to_decimal(row.get(field) or 0)
    return total


def sum_int(rows: list[dict], field: str) -> int:
    total = 0
    for row in rows:
        raw = row.get(field)
        try:
            total += int(round(float(raw)))
        except Exception:
            continue
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic migration validation report")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--use-csv", type=str, metavar="CSV_DIR", required=True, help="CSV extract directory")
    parser.add_argument("--output", type=str, help="Optional output markdown path")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model="PopulationComponent", source_identifier=component_key
    ).first()
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.utcnow()) for m in members)

    loader = ETLDataLoader(args.use_csv)

    # FishTalk aggregates
    feeding_rows = loader.get_feeding_actions_for_populations(set(population_ids), window_start, window_end)
    ft_feed_events = len(feeding_rows)
    ft_feed_kg = sum(to_decimal(r.get("FeedAmountG") or 0) for r in feeding_rows) / Decimal("1000")

    mortality_rows = loader.get_mortality_actions_for_populations(set(population_ids), window_start, window_end)
    ft_mortality_events = len(mortality_rows)
    ft_mortality_count = sum_int(mortality_rows, "MortalityCount")
    ft_mortality_biomass = harvest_sum(mortality_rows, "MortalityBiomass")

    culling_rows = loader.get_culling_actions_for_populations(set(population_ids), window_start, window_end)
    ft_culling_events = len(culling_rows)
    ft_culling_count = sum_int(culling_rows, "CullingCount")
    ft_culling_biomass = harvest_sum(culling_rows, "CullingBiomass")

    escape_rows = loader.get_escape_actions_for_populations(set(population_ids), window_start, window_end)
    ft_escape_events = len(escape_rows)
    ft_escape_count = sum_int(escape_rows, "EscapeCount")
    ft_escape_biomass = harvest_sum(escape_rows, "EscapeBiomass")

    treatment_rows = loader.get_treatments_for_populations(set(population_ids), window_start, window_end)
    ft_treatment_events = len(treatment_rows)

    weight_rows = loader.get_weight_samples_for_populations(set(population_ids), window_start, window_end)
    ft_weight_samples = len(weight_rows)

    user_sample_rows = loader.get_user_sample_sessions(set(population_ids), window_start, window_end)
    ft_user_samples = len(user_sample_rows)

    lice_sample_rows, lice_data_rows, _ = loader.get_lice_samples_for_populations(
        set(population_ids), window_start, window_end
    )
    ft_lice_samples = len(lice_sample_rows)
    ft_lice_data_rows = len(lice_data_rows)
    ft_lice_fish_sampled = sum_int(lice_sample_rows, "NumberOfFish")
    ft_lice_total_count = sum_int(lice_data_rows, "LiceCount")

    harvest_rows = loader.get_harvest_results_for_populations(set(population_ids), window_start, window_end)
    ft_harvest_rows = len(harvest_rows)
    ft_harvest_count = sum_int(harvest_rows, "Count")
    ft_harvest_live = harvest_sum(harvest_rows, "GrossBiomass")
    ft_harvest_gutted = harvest_sum(harvest_rows, "NetBiomass")

    # AquaMind aggregates
    feeding_qs = FeedingEvent.objects.filter(batch=batch)
    am_feed_events = feeding_qs.count()
    am_feed_kg = feeding_qs.aggregate(total=Sum("amount_kg"))["total"] or Decimal("0")

    def mortality_by_source(source_model: str) -> tuple[int, Decimal, int]:
        ids = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model=source_model,
            target_app_label="batch",
            target_model="mortalityevent",
        ).values_list("target_object_id", flat=True)
        qs = MortalityEvent.objects.filter(batch=batch, pk__in=ids)
        return (
            qs.count(),
            qs.aggregate(total=Sum("biomass_kg"))["total"] or Decimal("0"),
            qs.aggregate(total=Sum("count"))["total"] or 0,
        )

    am_mortality_events, am_mortality_biomass, am_mortality_count = mortality_by_source("Mortality")
    am_culling_events, am_culling_biomass, am_culling_count = mortality_by_source("Culling")
    am_escape_events, am_escape_biomass, am_escape_count = mortality_by_source("Escapes")

    am_treatment_events = Treatment.objects.filter(batch=batch).count()
    am_weight_samples = GrowthSample.objects.filter(assignment__batch=batch).count()
    am_user_samples = JournalEntry.objects.filter(batch=batch).count()

    lice_qs = LiceCount.objects.filter(batch=batch)
    am_lice_rows = lice_qs.count()
    am_lice_total_count = lice_qs.aggregate(total=Sum("count_value"))["total"] or 0

    lice_maps = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PublicLiceSampleData",
        target_app_label="health",
        target_model="licecount",
        target_object_id__in=lice_qs.values_list("id", flat=True),
    )
    sample_ids = {m.metadata.get("sample_id") for m in lice_maps if m.metadata and m.metadata.get("sample_id")}
    am_lice_sample_count = len(sample_ids)
    sample_fish = {}
    for m in lice_maps:
        sample_id = m.metadata.get("sample_id") if m.metadata else None
        if not sample_id or sample_id in sample_fish:
            continue
        try:
            lice_obj = lice_qs.get(id=m.target_object_id)
        except LiceCount.DoesNotExist:
            continue
        sample_fish[sample_id] = lice_obj.fish_sampled
    am_lice_fish_sampled = sum(sample_fish.values())

    env_count = EnvironmentalReading.objects.filter(batch=batch).count()

    harvest_event_qs = HarvestEvent.objects.filter(batch=batch)
    harvest_lot_qs = HarvestLot.objects.filter(event__batch=batch)
    am_harvest_events = harvest_event_qs.count()
    am_harvest_lots = harvest_lot_qs.count()
    am_harvest_count = harvest_lot_qs.aggregate(total=Sum("unit_count"))["total"] or 0
    am_harvest_live = harvest_lot_qs.aggregate(total=Sum("live_weight_kg"))["total"] or Decimal("0")
    am_harvest_gutted = harvest_lot_qs.aggregate(total=Sum("gutted_weight_kg"))["total"] or Decimal("0")

    lines = []
    lines.append("# Semantic Migration Validation Report")
    lines.append("")
    lines.append(f"- Component key: `{component_key}`")
    lines.append(f"- Batch: `{batch.batch_number}` (id={batch.id})")
    lines.append(f"- Populations: {len(population_ids)}")
    lines.append(f"- Window: {window_start} → {window_end}")
    lines.append("")
    lines.append("| Metric | FishTalk | AquaMind | Diff (FT - AM) |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append(f"| Feeding events | {ft_feed_events} | {am_feed_events} | {numeric_diff(ft_feed_events, am_feed_events)} |")
    lines.append(f"| Feeding kg | {fmt(ft_feed_kg)} | {fmt(am_feed_kg)} | {numeric_diff(ft_feed_kg, am_feed_kg)} |")
    lines.append(f"| Mortality events | {ft_mortality_events} | {am_mortality_events} | {numeric_diff(ft_mortality_events, am_mortality_events)} |")
    lines.append(f"| Mortality count | {ft_mortality_count} | {am_mortality_count} | {numeric_diff(ft_mortality_count, am_mortality_count)} |")
    lines.append(f"| Mortality biomass kg | {fmt(ft_mortality_biomass)} | {fmt(am_mortality_biomass)} | {numeric_diff(ft_mortality_biomass, am_mortality_biomass)} |")
    lines.append(f"| Culling events | {ft_culling_events} | {am_culling_events} | {numeric_diff(ft_culling_events, am_culling_events)} |")
    lines.append(f"| Culling count | {ft_culling_count} | {am_culling_count} | {numeric_diff(ft_culling_count, am_culling_count)} |")
    lines.append(f"| Culling biomass kg | {fmt(ft_culling_biomass)} | {fmt(am_culling_biomass)} | {numeric_diff(ft_culling_biomass, am_culling_biomass)} |")
    lines.append(f"| Escape events | {ft_escape_events} | {am_escape_events} | {numeric_diff(ft_escape_events, am_escape_events)} |")
    lines.append(f"| Escape count | {ft_escape_count} | {am_escape_count} | {numeric_diff(ft_escape_count, am_escape_count)} |")
    lines.append(f"| Escape biomass kg | {fmt(ft_escape_biomass)} | {fmt(am_escape_biomass)} | {numeric_diff(ft_escape_biomass, am_escape_biomass)} |")
    lines.append(f"| Treatments | {ft_treatment_events} | {am_treatment_events} | {numeric_diff(ft_treatment_events, am_treatment_events)} |")
    lines.append(f"| Growth samples | {ft_weight_samples} | {am_weight_samples} | {numeric_diff(ft_weight_samples, am_weight_samples)} |")
    lines.append(f"| Health journal entries | {ft_user_samples} | {am_user_samples} | {numeric_diff(ft_user_samples, am_user_samples)} |")
    lines.append(f"| Lice samples | {ft_lice_samples} | {am_lice_sample_count} | {numeric_diff(ft_lice_samples, am_lice_sample_count)} |")
    lines.append(f"| Lice data rows | {ft_lice_data_rows} | {am_lice_rows} | {numeric_diff(ft_lice_data_rows, am_lice_rows)} |")
    lines.append(f"| Lice total count | {ft_lice_total_count} | {am_lice_total_count} | {numeric_diff(ft_lice_total_count, am_lice_total_count)} |")
    lines.append(f"| Fish sampled (lice) | {ft_lice_fish_sampled} | {am_lice_fish_sampled} | {numeric_diff(ft_lice_fish_sampled, am_lice_fish_sampled)} |")
    lines.append(f"| Environmental readings | n/a (sqlite) | {env_count} | n/a |")
    lines.append(f"| Harvest rows | {ft_harvest_rows} | {am_harvest_lots} | {numeric_diff(ft_harvest_rows, am_harvest_lots)} |")
    lines.append(f"| Harvest events | n/a | {am_harvest_events} | n/a |")
    lines.append(f"| Harvest count | {ft_harvest_count} | {am_harvest_count} | {numeric_diff(ft_harvest_count, am_harvest_count)} |")
    lines.append(f"| Harvest live kg | {fmt(ft_harvest_live)} | {fmt(am_harvest_live)} | {numeric_diff(ft_harvest_live, am_harvest_live)} |")
    lines.append(f"| Harvest gutted kg | {fmt(ft_harvest_gutted)} | {fmt(am_harvest_gutted)} | {numeric_diff(ft_harvest_gutted, am_harvest_gutted)} |")

    output = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
