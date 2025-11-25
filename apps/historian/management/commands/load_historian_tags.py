from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Sequence

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.utils import timezone

try:
    import pyodbc  # type: ignore
except ImportError:  # pragma: no cover
    pyodbc = None

try:
    import pymssql  # type: ignore
except ImportError:  # pragma: no cover
    pymssql = None

if pyodbc is None and pymssql is None:  # pragma: no cover
    raise CommandError(
        "Either pyodbc or pymssql is required to run this command. Please install one of them."
    )

from apps.historian.models import HistorianTag, HistorianTagHistory
from scripts.migration.config import get_sqlserver_config

TAG_QUERY = "SELECT * FROM _Tag"
TAG_HISTORY_QUERY = "SELECT * FROM TagHistory"


class Command(BaseCommand):
    help = (
        "Loads historian tag metadata from the AVEVA SQL Server instance into "
        "historian_tag and historian_tag_history."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            default="aveva_readonly",
            help="Connection profile defined in scripts/migration/migration_config.json",
        )
        parser.add_argument(
            "--using",
            default="migr_dev",
            help="Django database alias to write to (default: migr_dev).",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=1000,
            help="Number of rows to batch per bulk insert.",
        )

    def handle(self, *args, **options):
        profile = options["profile"]
        using = options["using"]
        chunk_size = options["chunk_size"]

        if using not in connections:
            raise CommandError(f"Database alias '{using}' is not configured.")

        sql_config = get_sqlserver_config(profile)
        self.stdout.write(
            self.style.HTTP_INFO(
                f"Connecting to SQL Server profile '{profile}' ({sql_config.server}:{sql_config.port})"
            )
        )
        source_conn, cursor = self._connect(sql_config)
        try:
            with transaction.atomic(using=using):
                self._import_tags(cursor, using, chunk_size)
                tag_lookup = HistorianTag.objects.using(using).in_bulk(
                    field_name="tag_id"
                )
                cursor.execute(TAG_HISTORY_QUERY)
                history_columns = [col[0] for col in cursor.description]
                HistorianTagHistory.objects.using(using).all().delete()
                total_history = 0
                batch: List[HistorianTagHistory] = []
                while True:
                    rows = cursor.fetchmany(chunk_size)
                    if not rows:
                        break
                    for row in rows:
                        data = self._row_to_dict(history_columns, row)
                        batch.append(self._build_history_instance(data, tag_lookup))
                    HistorianTagHistory.objects.using(using).bulk_create(
                        batch, batch_size=chunk_size
                    )
                    total_history += len(batch)
                    batch = []

            self.stdout.write(
                self.style.SUCCESS(
                    f"Imported {HistorianTag.objects.using(using).count():,} tags "
                    f"and {total_history:,} tag history rows into '{using}'."
                )
            )
        finally:
            cursor.close()
            source_conn.close()

    def _connect(self, sql_config):
        if pyodbc is not None:
            try:
                conn = pyodbc.connect(sql_config.to_odbc_string())
                return conn, conn.cursor()
            except pyodbc.Error as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f"pyodbc connection failed ({exc}); attempting pymssql fallback."
                    )
                )
        if pymssql is not None:
            conn = pymssql.connect(
                server=sql_config.server,
                user=sql_config.uid,
                password=sql_config.pwd,
                database=sql_config.database,
                port=sql_config.port,
                tds_version="7.4",
            )
            return conn, conn.cursor()
        raise CommandError("Unable to establish SQL Server connection with available drivers.")

    def _import_tags(self, cursor, using: str, chunk_size: int) -> None:
        cursor.execute(TAG_QUERY)
        columns = [col[0] for col in cursor.description]
        HistorianTag.objects.using(using).all().delete()

        total = 0
        batch: List[HistorianTag] = []
        while True:
            rows = cursor.fetchmany(chunk_size)
            if not rows:
                break

            for row in rows:
                data = self._row_to_dict(columns, row)
                batch.append(self._build_tag_instance(data))

            HistorianTag.objects.using(using).bulk_create(batch, batch_size=chunk_size)
            total += len(batch)
            batch = []

        self.stdout.write(
            self.style.HTTP_SUCCESS(f"Imported {total:,} rows into historian_tag.")
        )

    def _build_tag_instance(self, data: Dict[str, Any]) -> HistorianTag:
        tag_id = self._as_uuid(data.get("TagId"))
        tag_name = (data.get("TagName") or "").strip()
        description = data.get("Description") or ""
        tag_type = self._as_int(data.get("TagType"))
        unit = (data.get("Unit") or "").strip()

        return HistorianTag(
            tag_id=tag_id or uuid.uuid4(),
            tag_name=tag_name,
            description=description,
            tag_type=tag_type,
            unit=unit,
            metadata=self._serialize_metadata(data),
        )

    def _build_history_instance(
        self, data: Dict[str, Any], tag_lookup: Dict[uuid.UUID, HistorianTag]
    ) -> HistorianTagHistory:
        tag_id = self._as_uuid(data.get("TagId"))
        tag = tag_lookup.get(tag_id) if tag_id else None
        recorded_at = self._as_datetime(data.get("DateCreated"))

        return HistorianTagHistory(
            tag=tag,
            recorded_at=recorded_at or timezone.now(),
            tag_name=(data.get("TagName") or "").strip(),
            tag_type=self._as_int(data.get("TagType")),
            unit=(data.get("Unit") or "").strip(),
            payload=self._serialize_metadata(data),
        )

    def _row_to_dict(
        self, columns: Sequence[str], row: Sequence[Any]
    ) -> Dict[str, Any]:
        return {columns[idx]: row[idx] for idx in range(len(columns))}

    def _serialize_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        serialized: Dict[str, Any] = {}
        for key, value in data.items():
            serialized[key] = self._serialize_value(value)
        return serialized

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone=timezone.utc)
            return value.isoformat()
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, (bytes, bytearray)):
            try:
                value = value.decode("utf-8")
            except Exception:  # pragma: no cover - fallback
                return value.hex()
        if isinstance(value, str):
            return value.replace("\x00", "")
        return value

    def _as_uuid(self, value: Any) -> uuid.UUID | None:
        if value in (None, ""):
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def _as_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    def _as_datetime(self, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return (
                timezone.make_aware(value, timezone=timezone.utc)
                if timezone.is_naive(value)
                else value.astimezone(timezone.utc)
            )
        return timezone.make_aware(datetime.fromisoformat(str(value)), timezone=timezone.utc)
