#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk mortality events for one stitched population component.

Source (FishTalk): dbo.Mortality keyed by ActionID.
  - Mortality.ActionID -> Action.PopulationID (+ OperationID -> Operations.StartTime)
  - Mortality.MortalityCauseID -> MortalityCauses.MortalityCausesID (DefaultText)

Target (AquaMind): apps.batch.models.MortalityEvent

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
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

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from scripts.migration.history import save_with_history

from apps.batch.models import Batch, MortalityEvent
from apps.batch.models.assignment import BatchContainerAssignment
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.tools.etl_loader import ETLDataLoader
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map

User = get_user_model()


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
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, dt_timezone.utc)


def to_decimal(value: object, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


def get_external_map(
    source_model: str,
    source_identifier: str,
    *,
    component_key: str | None = None,
) -> ExternalIdMap | None:
    if source_model == "Populations":
        return get_assignment_external_map(
            str(source_identifier),
            component_key=component_key,
        )
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


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


def map_cause(cause_text: str) -> str:
    upper = (cause_text or "").upper()
    if not upper:
        return "UNKNOWN"
    if any(token in upper for token in ("DISEASE", "IPN", "ISA", "VIBRIO", "PD ", "CMS", "BKD", "FUNG", "AMOEBA")):
        return "DISEASE"
    if any(token in upper for token in ("HANDLING", "TRANSPORT", "STUNNER", "TRANSFER")):
        return "HANDLING"
    if any(token in upper for token in ("PRED", "BIRD", "SEAL", "OTTER", "MINK", "CORMORANT", "HERON")):
        return "PREDATION"
    if any(token in upper for token in ("OXY", "WEATHER", "STORM", "PLANKTON", "ALGA", "JELLY", "ENVIRON")):
        return "ENVIRONMENTAL"
    if "UNKNOWN" in upper:
        return "UNKNOWN"
    return "OTHER"


def lookup_status_snapshot(
    *, population_id: str, at_time: datetime,
    extractor: BaseExtractor | None = None, loader: ETLDataLoader | None = None
) -> tuple[int, Decimal]:
    """Get population status snapshot near a given time using SQL or CSV."""
    if loader is not None:
        # Use CSV data
        status = loader.get_latest_status_for_population(population_id, before_time=at_time)
        count = 0
        biomass = Decimal("0.00")
        if status:
            try:
                count = int(round(float(status.get("CurrentCount") or 0)))
            except Exception:
                count = 0
            biomass = to_decimal(status.get("CurrentBiomassKg"), places="0.01") or Decimal("0.00")
        return max(count, 0), biomass
    
    # Use SQL
    ts = at_time.strftime("%Y-%m-%d %H:%M:%S")
    rows = extractor._run_sqlcmd(
        query=(
            "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
            "FROM dbo.PublicStatusValues "
            f"WHERE PopulationID = '{population_id}' AND StatusTime <= '{ts}' "
            "ORDER BY StatusTime DESC"
        ),
        headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
    )
    if not rows:
        rows = extractor._run_sqlcmd(
            query=(
                "SELECT TOP 1 StatusTime, CurrentCount, CurrentBiomassKg "
                "FROM dbo.PublicStatusValues "
                f"WHERE PopulationID = '{population_id}' AND StatusTime >= '{ts}' "
                "ORDER BY StatusTime ASC"
            ),
            headers=["StatusTime", "CurrentCount", "CurrentBiomassKg"],
        )

    count = 0
    biomass = Decimal("0.00")
    if rows:
        try:
            count = int(round(float(rows[0].get("CurrentCount") or 0)))
        except Exception:
            count = 0
        biomass = to_decimal(rows[0].get("CurrentBiomassKg"), places="0.01") or Decimal("0.00")

    return max(count, 0), biomass


def build_status_snapshot_index(csv_dir: Path, population_ids: set[str]) -> dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]]:
    import csv

    path = csv_dir / "status_values.csv"
    if not path.exists():
        return {}

    raw: dict[str, list[tuple[datetime, int, Decimal]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pop_id = (row.get("PopulationID") or "").strip()
            if not pop_id or pop_id not in population_ids:
                continue
            ts = parse_dt(row.get("StatusTime", ""))
            if ts is None:
                continue
            ts = ensure_aware(ts)
            try:
                count = int(float(row.get("CurrentCount") or 0)) if row.get("CurrentCount") not in (None, "") else 0
            except ValueError:
                count = 0
            try:
                biomass = Decimal(str(row.get("CurrentBiomassKg") or 0)) if row.get("CurrentBiomassKg") not in (None, "") else Decimal("0.00")
            except Exception:
                biomass = Decimal("0.00")
            raw.setdefault(pop_id, []).append((ts, count, biomass))

    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]] = {}
    for pop_id, items in raw.items():
        items.sort(key=lambda item: item[0])
        times = [item[0] for item in items]
        values = [(item[1], item[2]) for item in items]
        index[pop_id] = (times, values)

    return index


def lookup_status_snapshot_from_index(
    index: dict[str, tuple[list[datetime], list[tuple[int, Decimal]]]],
    population_id: str,
    at_time: datetime,
) -> tuple[int, Decimal]:
    if not index or population_id not in index:
        return 0, Decimal("0.00")
    times, values = index[population_id]
    if not times:
        return 0, Decimal("0.00")
    at_time = ensure_aware(at_time)
    pos = bisect_right(times, at_time)
    if pos > 0:
        return values[pos - 1]
    if pos < len(values):
        return values[pos]
    return 0, Decimal("0.00")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate mortality events for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    parser.add_argument(
        "--sync-assignment-counts",
        action="store_true",
        help=(
            "Apply baseline-minus-removals sync to assignment.population_count. "
            "Default is off to preserve stage-entry assignment semantics."
        ),
    )
    return parser


def collect_removal_totals_by_population(batch: Batch) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    event_ids = list(MortalityEvent.objects.filter(batch=batch).values_list("id", flat=True))
    if not event_ids:
        return totals

    event_count_by_id = {
        event.id: int(event.count or 0)
        for event in MortalityEvent.objects.filter(id__in=event_ids).only("id", "count")
    }
    mappings = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model__in=["Mortality", "Culling", "Escapes"],
        target_app_label="batch",
        target_model="mortalityevent",
        target_object_id__in=event_ids,
    )
    for mapping in mappings:
        pop_id = (mapping.metadata or {}).get("population_id")
        if not pop_id:
            continue
        totals[pop_id] += event_count_by_id.get(mapping.target_object_id, 0)
    return totals


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    population_ids = sorted({m.population_id for m in members if m.population_id})
    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)

    # Initialize data source
    use_csv = args.use_csv is not None
    loader = ETLDataLoader(args.use_csv) if use_csv else None
    extractor = None if use_csv else BaseExtractor(ExtractionContext(profile=args.sql_profile))

    status_index = {}
    if use_csv:
        # Load mortality data from CSV
        mortality_rows = loader.get_mortality_actions_for_populations(
            set(population_ids),
            start_time=window_start,
            end_time=window_end,
        )
        status_index = build_status_snapshot_index(Path(args.use_csv), set(population_ids))
    else:
        in_clause = ",".join(f"'{pid}'" for pid in population_ids)
        start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

        mortality_rows = extractor._run_sqlcmd(
            query=(
                "SELECT CONVERT(varchar(36), m.ActionID) AS ActionID, "
                "CONVERT(varchar(36), a.PopulationID) AS PopulationID, "
                "CONVERT(varchar(19), o.StartTime, 120) AS OperationStartTime, "
                "CONVERT(varchar(32), m.MortalityCount) AS MortalityCount, "
                "CONVERT(varchar(64), m.MortalityBiomass) AS MortalityBiomass, "
                "CONVERT(varchar(32), m.MortalityCauseID) AS MortalityCauseID, "
                "ISNULL(mc.DefaultText, '') AS CauseText, "
                "ISNULL(m.Comment, '') AS Comment "
                "FROM dbo.Mortality m "
                "JOIN dbo.Action a ON a.ActionID = m.ActionID "
                "JOIN dbo.Operations o ON o.OperationID = a.OperationID "
                "LEFT JOIN dbo.MortalityCauses mc ON mc.MortalityCausesID = m.MortalityCauseID "
                f"WHERE a.PopulationID IN ({in_clause}) "
                f"AND o.StartTime >= '{start_str}' AND o.StartTime <= '{end_str}' "
                "ORDER BY o.StartTime ASC"
            ),
            headers=[
                "ActionID",
                "PopulationID",
                "OperationStartTime",
                "MortalityCount",
                "MortalityBiomass",
                "MortalityCauseID",
                "CauseText",
                "Comment",
            ],
        )

    if args.dry_run:
        print(f"[dry-run] Would migrate {len(mortality_rows)} FishTalk mortality rows into batch={batch.batch_number}")
        return 0

    assignment_by_pop: dict[str, BatchContainerAssignment] = {}
    population_map_by_pop: dict[str, ExternalIdMap] = {}
    for pid in population_ids:
        mapped = get_external_map("Populations", pid, component_key=component_key)
        if mapped:
            assignment_by_pop[pid] = BatchContainerAssignment.objects.get(pk=mapped.target_object_id)
            population_map_by_pop[pid] = mapped

    baseline_count_by_pop: dict[str, int] = {}
    for pop_id, assignment in assignment_by_pop.items():
        baseline = None
        pop_map = population_map_by_pop.get(pop_id)
        if pop_map:
            raw = (pop_map.metadata or {}).get("baseline_population_count")
            if raw is not None:
                try:
                    baseline = int(round(float(raw)))
                except Exception:
                    baseline = None
        if baseline is None:
            baseline = int(assignment.population_count or 0)
        baseline_count_by_pop[pop_id] = max(baseline, 0)

    created = updated = skipped = 0
    adjusted_assignments = 0

    with transaction.atomic():
        history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        history_reason = f"FishTalk migration: mortality for component {component_key}"
        for row in mortality_rows:
            action_id = (row.get("ActionID") or "").strip()
            population_id = (row.get("PopulationID") or "").strip()
            if not action_id or not population_id:
                skipped += 1
                continue

            count_raw = row.get("MortalityCount")
            try:
                count = int(round(float(count_raw or 0)))
            except Exception:
                count = 0
            if count <= 0:
                skipped += 1
                continue

            op_time = parse_dt(row.get("OperationStartTime") or "")
            if op_time is None:
                skipped += 1
                continue
            op_time_aware = ensure_aware(op_time)

            biomass = to_decimal(row.get("MortalityBiomass"), places="0.01")
            if biomass is None or biomass <= 0:
                if use_csv and status_index:
                    snap_count, snap_biomass = lookup_status_snapshot_from_index(
                        status_index, population_id=population_id, at_time=op_time
                    )
                else:
                    snap_count, snap_biomass = lookup_status_snapshot(
                        population_id=population_id, at_time=op_time,
                        extractor=extractor, loader=loader
                    )
                if snap_count > 0 and snap_biomass > 0:
                    per_fish = (snap_biomass / Decimal(snap_count)).quantize(Decimal("0.000001"))
                    biomass = (per_fish * Decimal(count)).quantize(Decimal("0.01"))
                else:
                    biomass = Decimal("0.00")

            cause_text = (row.get("CauseText") or "").strip()
            cause_id = (row.get("MortalityCauseID") or "").strip()
            comment = (row.get("Comment") or "").strip()

            description_parts: list[str] = []
            if cause_text:
                description_parts.append(cause_text)
            if cause_id:
                description_parts.append(f"FishTalk MortalityCauseID={cause_id}")
            if comment:
                description_parts.append(comment)

            assignment = assignment_by_pop.get(population_id)

            defaults = {
                "batch": batch,
                "assignment": assignment,
                "event_date": op_time_aware.date(),
                "count": count,
                "biomass_kg": biomass,
                "cause": map_cause(cause_text),
                "description": "; ".join(description_parts)[:1000],
            }

            mapped = get_external_map("Mortality", action_id)
            if mapped:
                obj = MortalityEvent.objects.get(pk=mapped.target_object_id)
                for k, v in defaults.items():
                    setattr(obj, k, v)
                save_with_history(obj, user=history_user, reason=history_reason)
                updated += 1
            else:
                obj = MortalityEvent(**defaults)
                save_with_history(obj, user=history_user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="Mortality",
                    source_identifier=str(action_id),
                    defaults={
                        "target_app_label": obj._meta.app_label,
                        "target_model": obj._meta.model_name,
                        "target_object_id": obj.pk,
                        "metadata": {
                            "population_id": population_id,
                            "mortality_count": count,
                            "mortality_biomass_kg": str(biomass),
                        },
                    },
                )
                created += 1

        if args.sync_assignment_counts:
            removal_totals_by_pop = collect_removal_totals_by_population(batch)
            for pop_id, assignment in assignment_by_pop.items():
                baseline_count = baseline_count_by_pop.get(pop_id, int(assignment.population_count or 0))
                removed = max(removal_totals_by_pop.get(pop_id, 0), 0)
                resolved_count = max(baseline_count - removed, 0)
                if int(assignment.population_count or 0) == resolved_count:
                    continue
                assignment.population_count = resolved_count
                save_with_history(
                    assignment,
                    user=history_user,
                    reason=f"FishTalk mortality sync {component_key[:8]}",
                )
                adjusted_assignments += 1

    print(
        f"Migrated mortality for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, rows={len(mortality_rows)}, "
        f"assignments_adjusted={adjusted_assignments}, "
        f"assignment_sync={'on' if args.sync_assignment_counts else 'off'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
