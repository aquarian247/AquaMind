#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk environmental readings for one stitched population component.

Source (FishTalk): dbo.Ext_SensorReadings_v2 and dbo.Ext_DailySensorReadings_v2
  - Ext_SensorReadings_v2: ContainerID, SensorID, ReadingTime, Reading
  - Ext_DailySensorReadings_v2: ContainerID, SensorID, Date, Reading

Target (AquaMind): apps.environmental.models.EnvironmentalReading

Notes:
  - FishTalk tables do not expose parameter type; we map SensorID -> EnvironmentalParameter
    using a deterministic heuristic and cache in ExternalIdMap.
  - We create Sensors per (ContainerID, SensorID) pairing, since FishTalk sensor metadata
    is sparse in this dataset. Sensor name is derived from SensorID.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone, timedelta
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

from apps.batch.models.assignment import BatchContainerAssignment
from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.infrastructure.models import Sensor, Container
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.history import save_with_history
from scripts.migration.tools.etl_loader import ETLDataLoader


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


def parse_date_or_dt(value: str, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if len(value) == 10:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            if end_of_day:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            return None
    return parse_dt(value)


def ensure_environmental_parameters(*, history_user, history_reason) -> None:
    """Seed core EnvironmentalParameter rows if missing."""
    defaults = [
        ("Temperature", "°C"),
        ("Dissolved Oxygen", "mg/L"),
        ("pH", "pH"),
        ("Salinity", "ppt"),
    ]
    existing = {p.name for p in EnvironmentalParameter.objects.all()}
    for name, unit in defaults:
        if name in existing:
            continue
        param = EnvironmentalParameter(name=name, unit=unit, description="Seeded for FishTalk migration")
        save_with_history(param, user=history_user, reason=history_reason)
        existing.add(name)


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


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    container_id: str
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
                    container_id=row.get("container_id", ""),
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


def sensor_parameter_for(sensor_id: str, *, history_user, history_reason) -> EnvironmentalParameter:
    mapped = get_external_map("SensorParameter", sensor_id)
    if mapped:
        return EnvironmentalParameter.objects.get(pk=mapped.target_object_id)

    # Heuristic mapping: hash to a deterministic parameter bucket, prefer common params.
    preferred = list(EnvironmentalParameter.objects.filter(name__in=["Temperature", "Dissolved Oxygen"]).order_by("id"))
    candidates = preferred or list(EnvironmentalParameter.objects.order_by("id"))
    if not candidates:
        raise SystemExit("Missing EnvironmentalParameter master data")

    idx = abs(hash(sensor_id)) % len(candidates)
    param = candidates[idx]

    ExternalIdMap.objects.update_or_create(
        source_system="FishTalk",
        source_model="SensorParameter",
        source_identifier=str(sensor_id),
        defaults={
            "target_app_label": param._meta.app_label,
            "target_model": param._meta.model_name,
            "target_object_id": param.pk,
            "metadata": {"method": "hash_bucket", "candidate_count": len(candidates)},
        },
    )

    return param


def get_or_create_sensor(container: Container, sensor_id: str, *, history_user, history_reason) -> Sensor:
    source_identifier = f"{container.id}:{sensor_id}"
    mapped = get_external_map("Sensors", source_identifier)
    if mapped:
        return Sensor.objects.get(pk=mapped.target_object_id)

    param = sensor_parameter_for(sensor_id, history_user=history_user, history_reason=history_reason)
    sensor_type = "OTHER"
    if param.name.upper().startswith("TEMP"):
        sensor_type = "TEMPERATURE"
    elif "OXY" in param.name.upper():
        sensor_type = "OXYGEN"
    elif param.name.upper() in {"PH", "SALINITY"}:
        sensor_type = param.name.upper()

    sensor = Sensor(
        name=f"FT Sensor {sensor_id[:8]}",
        sensor_type=sensor_type,
        container=container,
        serial_number=sensor_id,
        manufacturer="FishTalk",
        active=True,
    )
    save_with_history(sensor, user=history_user, reason=history_reason)
    ExternalIdMap.objects.update_or_create(
        source_system="FishTalk",
        source_model="Sensors",
        source_identifier=source_identifier,
        defaults={
            "target_app_label": sensor._meta.app_label,
            "target_model": sensor._meta.model_name,
            "target_object_id": sensor.pk,
            "metadata": {"container_id": str(container.pk), "sensor_id": sensor_id},
        },
    )
    return sensor


def load_environmental_rows(
    container_ids: list[str],
    window_start: datetime,
    window_end: datetime,
    *,
    daily_only: bool,
    limit: int,
    use_csv_dir: str | Path | None,
    sqlite_path: str | Path | None,
    loader: ETLDataLoader | None,
    extractor: BaseExtractor | None,
    sql_profile: str,
) -> tuple[list[dict], list[dict]]:
    use_loader = loader is not None or use_csv_dir is not None or sqlite_path is not None
    if use_loader:
        if loader is None:
            loader = ETLDataLoader(use_csv_dir, sqlite_path=sqlite_path)

        daily_rows = loader.get_daily_readings_for_containers(
            set(container_ids),
            start_date=window_start,
            end_date=window_end,
        )
        time_rows = []
        if not daily_only:
            time_rows = loader.get_time_readings_for_containers(
                set(container_ids),
                start_time=window_start,
                end_time=window_end,
            )
        if limit:
            daily_rows = daily_rows[:limit]
            time_rows = time_rows[:limit]
        return daily_rows, time_rows

    if extractor is None:
        extractor = BaseExtractor(ExtractionContext(profile=sql_profile))

    in_clause = ",".join(f"'{cid}'" for cid in container_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")
    date_start = window_start.strftime("%Y-%m-%d")
    date_end = window_end.strftime("%Y-%m-%d")

    daily_limit = f"TOP {limit} " if limit else ""
    daily_rows = extractor._run_sqlcmd(
        query=(
            f"SELECT {daily_limit}CONVERT(varchar(36), ContainerID) AS ContainerID, "
            "CONVERT(varchar(36), SensorID) AS SensorID, "
            "CONVERT(varchar(10), Date, 120) AS ReadingDate, "
            "CONVERT(varchar(32), Reading) AS Reading "
            "FROM dbo.Ext_DailySensorReadings_v2 "
            f"WHERE ContainerID IN ({in_clause}) AND Date >= '{date_start}' AND Date <= '{date_end}' "
            "ORDER BY Date ASC"
        ),
        headers=["ContainerID", "SensorID", "ReadingDate", "Reading"],
    )

    time_rows = []
    if not daily_only:
        time_limit = f"TOP {limit} " if limit else ""
        time_rows = extractor._run_sqlcmd(
            query=(
                f"SELECT {time_limit}CONVERT(varchar(36), ContainerID) AS ContainerID, "
                "CONVERT(varchar(36), SensorID) AS SensorID, "
                "CONVERT(varchar(19), ReadingTime, 120) AS ReadingTime, "
                "CONVERT(varchar(32), Reading) AS Reading "
                "FROM dbo.Ext_SensorReadings_v2 "
                f"WHERE ContainerID IN ({in_clause}) AND ReadingTime >= '{start_str}' AND ReadingTime <= '{end_str}' "
                "ORDER BY ReadingTime ASC"
            ),
            headers=["ContainerID", "SensorID", "ReadingTime", "Reading"],
        )

    return daily_rows, time_rows


def migrate_component_environmental(
    *,
    report_dir: Path,
    component_id: int | None = None,
    component_key: str | None = None,
    sql_profile: str = "fishtalk_readonly",
    daily_only: bool = False,
    limit: int = 0,
    dry_run: bool = False,
    use_csv_dir: str | Path | None = None,
    use_sqlite_path: str | Path | None = None,
    loader: ETLDataLoader | None = None,
    window_start_override: datetime | None = None,
    window_end_override: datetime | None = None,
) -> int:
    report_dir = Path(report_dir)
    component_key = resolve_component_key(report_dir, component_id=component_id, component_key=component_key)
    members = load_members_from_report(report_dir, component_id=component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )

    from apps.batch.models import Batch

    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot set EnvironmentalReading.recorded_by")

    ensure_environmental_parameters(
        history_user=user,
        history_reason=f"FishTalk migration: environmental master data for component {component_key}",
    )

    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)
    if window_start_override is not None:
        window_start = window_start_override
    if window_end_override is not None:
        window_end = window_end_override

    container_ids = sorted({m.container_id for m in members if m.container_id})
    population_by_container = {m.container_id: m.population_id for m in members if m.container_id and m.population_id}
    if not container_ids:
        raise SystemExit("No container ids found in report")

    if loader is None and (use_csv_dir is not None or use_sqlite_path is not None):
        loader = ETLDataLoader(use_csv_dir, sqlite_path=use_sqlite_path)

    daily_rows, time_rows = load_environmental_rows(
        container_ids,
        window_start,
        window_end,
        daily_only=daily_only,
        limit=limit,
        use_csv_dir=use_csv_dir,
        sqlite_path=use_sqlite_path,
        loader=loader,
        extractor=None,
        sql_profile=sql_profile,
    )

    if dry_run:
        print(
            f"[dry-run] Batch={batch.batch_number} daily_rows={len(daily_rows)} time_rows={len(time_rows)}"
        )
        return 0

    history_reason = f"FishTalk migration: environmental for component {component_key}"
    created = updated = skipped = 0

    with transaction.atomic():
        # Preload container mapping from ExternalIdMap (FishTalk Containers)
        container_by_source: dict[str, Container] = {}
        for cid in container_ids:
            mapped = get_external_map("Containers", cid)
            if mapped:
                container_by_source[cid] = Container.objects.get(pk=mapped.target_object_id)

        # Daily readings
        for row in daily_rows:
            container_id = (row.get("ContainerID") or "").strip()
            sensor_id = (row.get("SensorID") or "").strip()
            reading_date = (row.get("ReadingDate") or "").strip()
            value = to_decimal(row.get("Reading"), places="0.0001")
            if not container_id or not sensor_id or not reading_date or value is None:
                skipped += 1
                continue

            container = container_by_source.get(container_id)
            if not container:
                skipped += 1
                continue

            sensor = get_or_create_sensor(container, sensor_id, history_user=user, history_reason=history_reason)
            param = sensor_parameter_for(sensor_id, history_user=user, history_reason=history_reason)

            reading_dt = ensure_aware(parse_dt(f"{reading_date} 12:00:00"))
            assignment_map = get_external_map("Populations", population_by_container.get(container_id, ""))
            assignment = None
            if assignment_map:
                assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)

            source_id = f"Daily:{container_id}:{sensor_id}:{reading_date}"
            mapped = get_external_map("Ext_DailySensorReadings_v2", source_id)
            defaults = {
                "parameter": param,
                "container": container,
                "batch": batch,
                "sensor": sensor,
                "batch_container_assignment": assignment,
                "value": value,
                "reading_time": reading_dt,
                "is_manual": True,  # Daily aggregates are marked as manual readings
                "recorded_by": user,
                "notes": f"FishTalk Ext_DailySensorReadings_v2 {source_id}",
            }
            if mapped:
                obj = EnvironmentalReading.objects.get(pk=mapped.target_object_id)
                for k, v in defaults.items():
                    setattr(obj, k, v)
                save_with_history(obj, user=user, reason=history_reason)
                updated += 1
            else:
                obj = EnvironmentalReading(**defaults)
                save_with_history(obj, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="Ext_DailySensorReadings_v2",
                    source_identifier=source_id,
                    defaults={
                        "target_app_label": obj._meta.app_label,
                        "target_model": obj._meta.model_name,
                        "target_object_id": obj.pk,
                        "metadata": {"container_id": container_id, "sensor_id": sensor_id},
                    },
                )
                created += 1

        # Time readings
        for row in time_rows:
            container_id = (row.get("ContainerID") or "").strip()
            sensor_id = (row.get("SensorID") or "").strip()
            reading_time = parse_dt(row.get("ReadingTime") or "")
            value = to_decimal(row.get("Reading"), places="0.0001")
            if not container_id or not sensor_id or reading_time is None or value is None:
                skipped += 1
                continue

            container = container_by_source.get(container_id)
            if not container:
                skipped += 1
                continue

            sensor = get_or_create_sensor(container, sensor_id, history_user=user, history_reason=history_reason)
            param = sensor_parameter_for(sensor_id, history_user=user, history_reason=history_reason)
            reading_dt = ensure_aware(reading_time)
            assignment_map = get_external_map("Populations", population_by_container.get(container_id, ""))
            assignment = None
            if assignment_map:
                assignment = BatchContainerAssignment.objects.get(pk=assignment_map.target_object_id)

            source_id = f"Time:{container_id}:{sensor_id}:{reading_dt.isoformat()}"
            mapped = get_external_map("Ext_SensorReadings_v2", source_id)
            defaults = {
                "parameter": param,
                "container": container,
                "batch": batch,
                "sensor": sensor,
                "batch_container_assignment": assignment,
                "value": value,
                "reading_time": reading_dt,
                "is_manual": False,  # Time-series readings are automated sensor data
                "recorded_by": user,
                "notes": f"FishTalk Ext_SensorReadings_v2 {source_id}",
            }
            if mapped:
                obj = EnvironmentalReading.objects.get(pk=mapped.target_object_id)
                for k, v in defaults.items():
                    setattr(obj, k, v)
                save_with_history(obj, user=user, reason=history_reason)
                updated += 1
            else:
                obj = EnvironmentalReading(**defaults)
                save_with_history(obj, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="Ext_SensorReadings_v2",
                    source_identifier=source_id,
                    defaults={
                        "target_app_label": obj._meta.app_label,
                        "target_model": obj._meta.model_name,
                        "target_object_id": obj.pk,
                        "metadata": {"container_id": container_id, "sensor_id": sensor_id},
                    },
                )
                created += 1

    print(
        f"Migrated environmental readings for component_key={component_key} into batch={batch.batch_number} "
        f"(created={created}, updated={updated}, skipped={skipped}, daily_rows={len(daily_rows)}, time_rows={len(time_rows)})"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate environmental readings for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument("--daily-only", action="store_true", help="Use Ext_DailySensorReadings_v2 only")
    parser.add_argument("--limit", type=int, default=0, help="Limit readings per table (0 = no limit)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    parser.add_argument(
        "--use-csv",
        type=str,
        metavar="CSV_DIR",
        help="Use pre-extracted CSV files from this directory instead of live SQL",
    )
    parser.add_argument(
        "--use-sqlite",
        type=str,
        metavar="SQLITE_PATH",
        help="Use a SQLite index for environmental readings (faster than raw CSV)",
    )
    parser.add_argument(
        "--start-date",
        help="Override window start (YYYY-MM-DD or full datetime)",
    )
    parser.add_argument(
        "--end-date",
        help="Override window end (YYYY-MM-DD or full datetime)",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=0,
        help="Process environmental readings in N-day chunks (0 = no chunking)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    window_start_override = parse_date_or_dt(args.start_date) if args.start_date else None
    window_end_override = parse_date_or_dt(args.end_date, end_of_day=True) if args.end_date else None
    if args.chunk_days and args.chunk_days > 0:
        report_dir = Path(args.report_dir)
        component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
        members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
        if not members:
            raise SystemExit("No members found for the selected component")

        base_start = window_start_override or min(m.start_time for m in members)
        base_end = window_end_override or max((m.end_time or datetime.now()) for m in members)

        current = base_start
        while current <= base_end:
            chunk_end = min(base_end, current + timedelta(days=args.chunk_days) - timedelta(seconds=1))
            print(f"[chunk] {current} -> {chunk_end}")
            migrate_component_environmental(
                report_dir=report_dir,
                component_id=args.component_id,
                component_key=component_key,
                sql_profile=args.sql_profile,
                daily_only=args.daily_only,
                limit=args.limit,
                dry_run=args.dry_run,
                use_csv_dir=args.use_csv,
                use_sqlite_path=args.use_sqlite,
                window_start_override=current,
                window_end_override=chunk_end,
            )
            current = chunk_end + timedelta(seconds=1)
        return 0

    return migrate_component_environmental(
        report_dir=Path(args.report_dir),
        component_id=args.component_id,
        component_key=args.component_key,
        sql_profile=args.sql_profile,
        daily_only=args.daily_only,
        limit=args.limit,
        dry_run=args.dry_run,
        use_csv_dir=args.use_csv,
        use_sqlite_path=args.use_sqlite,
        window_start_override=window_start_override,
        window_end_override=window_end_override,
    )


if __name__ == "__main__":
    raise SystemExit(main())
