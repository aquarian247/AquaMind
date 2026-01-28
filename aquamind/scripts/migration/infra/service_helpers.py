"""Shared helpers for infrastructure migration loaders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from django.db import connections, transaction

from apps.migration_support.models import ExternalIdMap


MIGRATION_SOURCE_SYSTEM = "FishTalk"

SOURCE_MODEL_GEOGRAPHY = "GeographyDerived"
SOURCE_MODEL_STATION = "OrganisationUnitStation"
SOURCE_MODEL_HALL = "OrganisationUnitHall"
SOURCE_MODEL_AREA = "OrganisationUnitArea"
SOURCE_MODEL_CONTAINER = "Containers"


@dataclass(frozen=True)
class StagingRow:
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def fetch_staging_rows(
    table: str,
    *,
    columns: str = "*",
    where_sql: str | None = None,
    params: Iterable[Any] | None = None,
    connection_alias: str = "default",
) -> List[StagingRow]:
    """Fetch rows from staging tables in stg_migration schema.

    Note: This uses raw SQL only for staging reads. Target writes use ORM/domain.
    """
    sql = f"SELECT {columns} FROM stg_migration.{table}"
    if where_sql:
        sql = f"{sql} WHERE {where_sql}"

    rows: List[StagingRow] = []
    with connections[connection_alias].cursor() as cursor:
        cursor.execute(sql, list(params or []))
        column_names = [col[0] for col in cursor.description]
        for record in cursor.fetchall():
            rows.append(StagingRow(dict(zip(column_names, record))))
    return rows


def get_external_id_map(
    source_model: str,
    source_identifier: str,
    *,
    source_system: str = MIGRATION_SOURCE_SYSTEM,
) -> Optional[ExternalIdMap]:
    return ExternalIdMap.objects.filter(
        source_system=source_system,
        source_model=source_model,
        source_identifier=source_identifier,
    ).first()


def ensure_external_id_map(
    *,
    source_model: str,
    source_identifier: str,
    target_object: Any,
    metadata: Dict[str, Any],
    source_system: str = MIGRATION_SOURCE_SYSTEM,
) -> ExternalIdMap:
    """Create or update ExternalIdMap for idempotent loads.

    TODO: Confirm ExternalIdMap fields/relations and align metadata format.
    """
    existing = get_external_id_map(
        source_model=source_model,
        source_identifier=source_identifier,
        source_system=source_system,
    )
    if existing:
        if getattr(existing, "content_object", None) is None:
            existing.content_object = target_object
        existing.metadata = metadata
        existing.save(update_fields=["content_object", "metadata"])
        return existing

    return ExternalIdMap.objects.create(
        source_system=source_system,
        source_model=source_model,
        source_identifier=source_identifier,
        content_object=target_object,
        metadata=metadata,
    )


def with_transaction(func):
    """Decorator to wrap loader steps in an atomic transaction."""

    def _wrapped(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)

    return _wrapped
