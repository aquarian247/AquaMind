#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk environmental readings for one stitched population component.

Source (FishTalk): dbo.Ext_SensorReadings_v2 and dbo.Ext_DailySensorReadings_v2
  - Ext_SensorReadings_v2: ContainerID, SensorID, ReadingTime, Reading
  - Ext_DailySensorReadings_v2: ContainerID, SensorID, Date, Reading

Target (AquaMind): apps.environmental.models.EnvironmentalReading

Notes:
  - Sensor metadata is resolved from FishTalk sensor catalogs (`Ext_Sensors_v2`,
    `Ext_SensorTypes_v2`, `Ext_MeasuringUnits_v2`) when available so SensorID maps
    to the correct environmental parameter (e.g. Oxygen Saturation vs Temperature).
  - If metadata is unavailable, we fall back to deterministic mapping and cache
    SensorID -> EnvironmentalParameter in ExternalIdMap.
  - Sensors are created per (ContainerID, SensorID) pairing.

Writes only to aquamind_db_migr_dev.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable

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
        ("Oxygen Saturation", "%"),
        ("CO2", "mg/L"),
        ("pH", "pH"),
        ("Salinity", "ppt"),
        ("Ammonia", "mg/L"),
        ("Nitrite", "mg/L"),
        ("Nitrate", "mg/L"),
        ("Alkalinity", "mg/L"),
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


def normalize_environmental_value(
    *,
    value: Decimal,
    parameter: EnvironmentalParameter,
) -> Decimal:
    """Apply deterministic value normalization for known FishTalk quirks."""
    if (
        parameter.name == "Oxygen Saturation"
        and value > Decimal("200")
        and value <= Decimal("2000")
    ):
        # Some sensors encode saturation as 10x percentage points (e.g. 1003.1 -> 100.31%).
        return (value / Decimal("10")).quantize(Decimal("0.0001"))
    return value


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


@dataclass(frozen=True)
class SensorMetadata:
    sensor_id: str
    sensor_name: str
    sensor_type_name: str
    unit_text: str


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


def build_assignment_index_for_containers(
    container_ids: list[int],
) -> dict[int, list[BatchContainerAssignment]]:
    """Preload assignment history for containers touched by the component."""
    index: dict[int, list[BatchContainerAssignment]] = {}
    if not container_ids:
        return index

    assignments = (
        BatchContainerAssignment.objects.filter(container_id__in=container_ids)
        .select_related("batch")
        .order_by("container_id", "assignment_date", "id")
    )
    for assignment in assignments:
        index.setdefault(assignment.container_id, []).append(assignment)
    return index


def resolve_assignment_for_container_date(
    assignments_by_container: dict[int, list[BatchContainerAssignment]],
    *,
    container_id: int,
    reading_date: date,
) -> BatchContainerAssignment | None:
    """Resolve the best assignment for a container on a given reading date.

    Preference order:
    1) assignment windows that cover reading_date (assignment_date..departure_date)
    2) latest assignment that started on/before reading_date
    3) earliest assignment after reading_date
    """
    candidates = assignments_by_container.get(container_id) or []
    if not candidates:
        return None

    in_window: list[BatchContainerAssignment] = []
    started_before_or_on: list[BatchContainerAssignment] = []
    starts_after: list[BatchContainerAssignment] = []
    for assignment in candidates:
        start = assignment.assignment_date
        end = assignment.departure_date
        if start and start <= reading_date and (end is None or end >= reading_date):
            in_window.append(assignment)
        if start and start <= reading_date:
            started_before_or_on.append(assignment)
        elif start and start > reading_date:
            starts_after.append(assignment)

    def _rank_desc(a: BatchContainerAssignment) -> tuple[date, int, int]:
        return (a.assignment_date or date.min, int(a.population_count or 0), a.id)

    if in_window:
        return max(in_window, key=_rank_desc)
    if started_before_or_on:
        return max(started_before_or_on, key=_rank_desc)
    if starts_after:
        return min(starts_after, key=lambda a: ((a.assignment_date or date.max), a.id))
    return None


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


def _chunked(values: Iterable[str], chunk_size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) >= chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _normalize_unit(unit_text: str) -> str:
    normalized = (unit_text or "").strip().lower()
    if not normalized:
        return ""
    aliases = {
        "°c": "°C",
        "c": "°C",
        "mg/l": "mg/L",
        "mg\\l": "mg/L",
        "µg/l": "µg/L",
        "ug/l": "µg/L",
        "%": "%",
        "ph": "pH",
        "‰": "ppt",
        "ppt": "ppt",
        "unknown": "",
    }
    return aliases.get(normalized, unit_text.strip())


def _parameter_identity_from_sensor_metadata(
    sensor_metadata: SensorMetadata | None,
    *,
    value_hint_max: Decimal | None = None,
) -> tuple[str, str] | None:
    if sensor_metadata is None:
        return None
    sensor_type = (sensor_metadata.sensor_type_name or "").strip().lower()
    unit = _normalize_unit(sensor_metadata.unit_text)
    sensor_name = (sensor_metadata.sensor_name or "").strip().lower()
    combined = f"{sensor_type} {sensor_name}".strip()

    if "oxygen" in combined and "saturation" in combined:
        return ("Oxygen Saturation", "%")
    if "oxygen" in combined and unit == "mg/L":
        if value_hint_max is not None and value_hint_max > Decimal("30"):
            # mg/L metadata is occasionally mislabeled for percentage-like oxygen streams.
            return ("Oxygen Saturation", "%")
        return ("Dissolved Oxygen", "mg/L")
    if "temperature" in combined or unit == "°C":
        return ("Temperature", "°C")
    if sensor_type == "ph" or unit == "pH":
        return ("pH", "pH")
    if "salinit" in combined or unit == "ppt":
        return ("Salinity", "ppt")
    if "co2" in combined or "carbon dioxide" in combined:
        return ("CO2", unit or "mg/L")
    if "nitrit" in combined or "no2" in combined:
        return ("Nitrite", unit or "mg/L")
    if "nitrat" in combined or "no3" in combined:
        return ("Nitrate", unit or "mg/L")
    if "ammon" in combined or "tan" in combined:
        return ("Ammonia", unit or "mg/L")
    if "alkalinity" in combined:
        return ("Alkalinity", unit or "mg/L")
    if sensor_metadata.sensor_type_name:
        fallback_unit = unit
        if not fallback_unit and "kg" in sensor_type:
            fallback_unit = "kg"
        return (sensor_metadata.sensor_type_name.strip(), fallback_unit)
    return None


def _get_or_create_parameter(
    *,
    name: str,
    unit: str,
    history_user,
    history_reason,
) -> EnvironmentalParameter:
    existing = EnvironmentalParameter.objects.filter(name=name).first()
    if existing:
        return existing
    param = EnvironmentalParameter(
        name=name,
        unit=unit,
        description="Seeded from FishTalk sensor metadata",
    )
    save_with_history(param, user=history_user, reason=history_reason)
    return param


def _load_sensor_metadata_from_csv(
    sensor_ids: set[str],
    *,
    use_csv_dir: str | Path | None,
) -> dict[str, SensorMetadata]:
    if not sensor_ids or use_csv_dir is None:
        return {}

    csv_dir = Path(use_csv_dir)
    sensors_path = csv_dir / "ext_sensors_v2.csv"
    sensor_types_path = csv_dir / "ext_sensor_types_v2.csv"
    units_path = csv_dir / "ext_measuring_units_v2.csv"
    if not (sensors_path.exists() and sensor_types_path.exists() and units_path.exists()):
        return {}

    sensor_types_by_id: dict[str, dict[str, str]] = {}
    with sensor_types_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sensor_type_id = (row.get("SensorTypeID") or "").strip()
            if sensor_type_id:
                sensor_types_by_id[sensor_type_id] = row

    units_by_id: dict[str, str] = {}
    with units_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            unit_id = (row.get("MeasuringUnitID") or "").strip()
            if unit_id:
                units_by_id[unit_id] = (row.get("MeasuringUnitText") or "").strip()

    metadata_by_sensor_id: dict[str, SensorMetadata] = {}
    with sensors_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sensor_id = (row.get("SensorID") or "").strip()
            if not sensor_id or sensor_id not in sensor_ids:
                continue
            sensor_type_id = (row.get("SensorTypeID") or "").strip()
            sensor_type = sensor_types_by_id.get(sensor_type_id, {})
            unit_id = (sensor_type.get("MeasuringUnitID") or "").strip()
            metadata_by_sensor_id[sensor_id] = SensorMetadata(
                sensor_id=sensor_id,
                sensor_name=(row.get("SensorName") or "").strip(),
                sensor_type_name=(sensor_type.get("SensorTypeName") or "").strip(),
                unit_text=units_by_id.get(unit_id, ""),
            )
    return metadata_by_sensor_id


def _load_sensor_metadata_from_sql(
    sensor_ids: set[str],
    *,
    sql_profile: str,
) -> dict[str, SensorMetadata]:
    if not sensor_ids:
        return {}

    extractor = BaseExtractor(ExtractionContext(profile=sql_profile))
    metadata_by_sensor_id: dict[str, SensorMetadata] = {}

    def _query_metadata(
        *,
        table_sensors: str,
        table_sensor_types: str,
        table_units: str,
        query_sensor_ids: list[str],
    ) -> None:
        in_clause = ",".join(f"'{sensor_id}'" for sensor_id in query_sensor_ids)
        rows = extractor._run_sqlcmd(
            query=(
                "SELECT "
                "CONVERT(varchar(36), s.SensorID) AS SensorID, "
                "ISNULL(s.SensorName, '') AS SensorName, "
                "ISNULL(st.SensorTypeName, '') AS SensorTypeName, "
                "ISNULL(mu.MeasuringUnitText, '') AS MeasuringUnitText "
                f"FROM dbo.{table_sensors} s "
                f"LEFT JOIN dbo.{table_sensor_types} st ON st.SensorTypeID = s.SensorTypeID "
                f"LEFT JOIN dbo.{table_units} mu ON mu.MeasuringUnitID = st.MeasuringUnitID "
                f"WHERE s.SensorID IN ({in_clause})"
            ),
            headers=["SensorID", "SensorName", "SensorTypeName", "MeasuringUnitText"],
        )
        for row in rows:
            sensor_id = (row.get("SensorID") or "").strip()
            if not sensor_id:
                continue
            metadata_by_sensor_id[sensor_id] = SensorMetadata(
                sensor_id=sensor_id,
                sensor_name=(row.get("SensorName") or "").strip(),
                sensor_type_name=(row.get("SensorTypeName") or "").strip(),
                unit_text=(row.get("MeasuringUnitText") or "").strip(),
            )

    for chunk in _chunked(sorted(sensor_ids), 100):
        _query_metadata(
            table_sensors="Ext_Sensors_v2",
            table_sensor_types="Ext_SensorTypes_v2",
            table_units="Ext_MeasuringUnits_v2",
            query_sensor_ids=chunk,
        )

    missing = sorted(sensor_ids - set(metadata_by_sensor_id.keys()))
    for chunk in _chunked(missing, 100):
        _query_metadata(
            table_sensors="Sensors",
            table_sensor_types="SensorTypes",
            table_units="MeasuringUnits",
            query_sensor_ids=chunk,
        )

    return metadata_by_sensor_id


def load_sensor_metadata(
    sensor_ids: set[str],
    *,
    use_csv_dir: str | Path | None,
    sql_profile: str,
) -> dict[str, SensorMetadata]:
    if not sensor_ids:
        return {}

    metadata_by_sensor_id = _load_sensor_metadata_from_csv(
        sensor_ids,
        use_csv_dir=use_csv_dir,
    )
    missing = sensor_ids - set(metadata_by_sensor_id.keys())
    if not missing:
        return metadata_by_sensor_id

    try:
        metadata_by_sensor_id.update(
            _load_sensor_metadata_from_sql(
                missing,
                sql_profile=sql_profile,
            )
        )
    except Exception as exc:
        print(f"[WARN] Sensor metadata SQL lookup failed; using fallback mapping. reason={exc}")

    return metadata_by_sensor_id


def sensor_parameter_for(
    sensor_id: str,
    *,
    history_user,
    history_reason,
    sensor_metadata: SensorMetadata | None = None,
    value_hint_max: Decimal | None = None,
) -> EnvironmentalParameter:
    mapped = get_external_map("SensorParameter", sensor_id)
    existing_param = None
    if mapped:
        existing_param = EnvironmentalParameter.objects.filter(pk=mapped.target_object_id).first()

    inferred_identity = _parameter_identity_from_sensor_metadata(
        sensor_metadata,
        value_hint_max=value_hint_max,
    )
    if inferred_identity:
        param_name, param_unit = inferred_identity
        param = _get_or_create_parameter(
            name=param_name,
            unit=param_unit,
            history_user=history_user,
            history_reason=history_reason,
        )
        if existing_param is None or existing_param.pk != param.pk:
            ExternalIdMap.objects.update_or_create(
                source_system="FishTalk",
                source_model="SensorParameter",
                source_identifier=str(sensor_id),
                defaults={
                    "target_app_label": param._meta.app_label,
                    "target_model": param._meta.model_name,
                    "target_object_id": param.pk,
                    "metadata": {
                        "method": "sensor_type_metadata",
                        "sensor_type_name": sensor_metadata.sensor_type_name if sensor_metadata else "",
                        "unit_text": sensor_metadata.unit_text if sensor_metadata else "",
                        "value_hint_max": str(value_hint_max) if value_hint_max is not None else "",
                    },
                },
            )
        return param

    if existing_param:
        return existing_param

    # Fallback mapping: hash to a deterministic parameter bucket.
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


def _sensor_type_from_parameter(param: EnvironmentalParameter) -> str:
    name_upper = param.name.upper()
    if name_upper.startswith("TEMP"):
        return "TEMPERATURE"
    if "OXY" in name_upper:
        return "OXYGEN"
    if name_upper in {"PH", "SALINITY"}:
        return name_upper
    return "OTHER"


def get_or_create_sensor(
    container: Container,
    sensor_id: str,
    *,
    history_user,
    history_reason,
    parameter: EnvironmentalParameter,
    sensor_metadata: SensorMetadata | None = None,
) -> Sensor:
    source_identifier = f"{container.id}:{sensor_id}"
    mapped = get_external_map("Sensors", source_identifier)
    desired_name = (
        (sensor_metadata.sensor_name or "").strip() if sensor_metadata else ""
    ) or f"FT Sensor {sensor_id[:8]}"
    desired_type = _sensor_type_from_parameter(parameter)

    if mapped:
        sensor = Sensor.objects.get(pk=mapped.target_object_id)
        changed = False
        if desired_name and sensor.name != desired_name:
            sensor.name = desired_name
            changed = True
        if desired_type and sensor.sensor_type != desired_type:
            sensor.sensor_type = desired_type
            changed = True
        if changed:
            save_with_history(sensor, user=history_user, reason=history_reason)
        return sensor

    sensor = Sensor(
        name=desired_name,
        sensor_type=desired_type,
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

    all_sensor_ids = {
        (row.get("SensorID") or "").strip()
        for row in (daily_rows + time_rows)
        if (row.get("SensorID") or "").strip()
    }
    sensor_value_max: dict[str, Decimal] = {}
    for row in (daily_rows + time_rows):
        sensor_id = (row.get("SensorID") or "").strip()
        if not sensor_id:
            continue
        reading_value = to_decimal(row.get("Reading"), places="0.0001")
        if reading_value is None:
            continue
        current = sensor_value_max.get(sensor_id)
        if current is None or reading_value > current:
            sensor_value_max[sensor_id] = reading_value

    sensor_metadata_by_id = load_sensor_metadata(
        all_sensor_ids,
        use_csv_dir=use_csv_dir,
        sql_profile=sql_profile,
    )
    if all_sensor_ids:
        print(
            "[INFO] Sensor metadata coverage: "
            f"{len(sensor_metadata_by_id)}/{len(all_sensor_ids)} sensor ids"
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

        assignments_by_container = build_assignment_index_for_containers(
            [container.pk for container in container_by_source.values()]
        )
        assignment_resolution_cache: dict[tuple[int, date], BatchContainerAssignment | None] = {}
        parameter_cache: dict[str, EnvironmentalParameter] = {}

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

            sensor_metadata = sensor_metadata_by_id.get(sensor_id)
            param = parameter_cache.get(sensor_id)
            if param is None:
                param = sensor_parameter_for(
                    sensor_id,
                    history_user=user,
                    history_reason=history_reason,
                    sensor_metadata=sensor_metadata,
                    value_hint_max=sensor_value_max.get(sensor_id),
                )
                parameter_cache[sensor_id] = param
            sensor = get_or_create_sensor(
                container,
                sensor_id,
                history_user=user,
                history_reason=history_reason,
                parameter=param,
                sensor_metadata=sensor_metadata,
            )
            normalized_value = normalize_environmental_value(value=value, parameter=param)

            reading_dt = ensure_aware(parse_dt(f"{reading_date} 12:00:00"))
            cache_key = (container.pk, reading_dt.date())
            if cache_key not in assignment_resolution_cache:
                assignment_resolution_cache[cache_key] = resolve_assignment_for_container_date(
                    assignments_by_container,
                    container_id=container.pk,
                    reading_date=reading_dt.date(),
                )
            resolved_assignment = assignment_resolution_cache[cache_key]
            resolved_batch = resolved_assignment.batch if resolved_assignment else None
            source_id = f"Daily:{container_id}:{sensor_id}:{reading_date}"
            mapped = get_external_map("Ext_DailySensorReadings_v2", source_id)

            existing_obj = None
            if mapped:
                existing_obj = EnvironmentalReading.objects.get(pk=mapped.target_object_id)
                if resolved_assignment is None:
                    resolved_assignment = existing_obj.batch_container_assignment
                    resolved_batch = existing_obj.batch
            if resolved_batch is None:
                resolved_batch = batch

            defaults = {
                "parameter": param,
                "container": container,
                "batch": resolved_batch,
                "sensor": sensor,
                "batch_container_assignment": resolved_assignment,
                "value": normalized_value,
                "reading_time": reading_dt,
                "is_manual": True,  # Daily aggregates are marked as manual readings
                "recorded_by": user,
                "notes": f"FishTalk Ext_DailySensorReadings_v2 {source_id}",
            }
            if mapped:
                obj = existing_obj
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

            sensor_metadata = sensor_metadata_by_id.get(sensor_id)
            param = parameter_cache.get(sensor_id)
            if param is None:
                param = sensor_parameter_for(
                    sensor_id,
                    history_user=user,
                    history_reason=history_reason,
                    sensor_metadata=sensor_metadata,
                    value_hint_max=sensor_value_max.get(sensor_id),
                )
                parameter_cache[sensor_id] = param
            sensor = get_or_create_sensor(
                container,
                sensor_id,
                history_user=user,
                history_reason=history_reason,
                parameter=param,
                sensor_metadata=sensor_metadata,
            )
            normalized_value = normalize_environmental_value(value=value, parameter=param)
            reading_dt = ensure_aware(reading_time)
            cache_key = (container.pk, reading_dt.date())
            if cache_key not in assignment_resolution_cache:
                assignment_resolution_cache[cache_key] = resolve_assignment_for_container_date(
                    assignments_by_container,
                    container_id=container.pk,
                    reading_date=reading_dt.date(),
                )
            resolved_assignment = assignment_resolution_cache[cache_key]
            resolved_batch = resolved_assignment.batch if resolved_assignment else None
            source_id = f"Time:{container_id}:{sensor_id}:{reading_dt.isoformat()}"
            mapped = get_external_map("Ext_SensorReadings_v2", source_id)

            existing_obj = None
            if mapped:
                existing_obj = EnvironmentalReading.objects.get(pk=mapped.target_object_id)
                if resolved_assignment is None:
                    resolved_assignment = existing_obj.batch_container_assignment
                    resolved_batch = existing_obj.batch
            if resolved_batch is None:
                resolved_batch = batch

            defaults = {
                "parameter": param,
                "container": container,
                "batch": resolved_batch,
                "sensor": sensor,
                "batch_container_assignment": resolved_assignment,
                "value": normalized_value,
                "reading_time": reading_dt,
                "is_manual": False,  # Time-series readings are automated sensor data
                "recorded_by": user,
                "notes": f"FishTalk Ext_SensorReadings_v2 {source_id}",
            }
            if mapped:
                obj = existing_obj
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
