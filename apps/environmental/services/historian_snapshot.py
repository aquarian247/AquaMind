"""Historian snapshot helper for transfer handoff compliance records."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, Optional

from django.db.models import Q
from django.utils import timezone

from apps.batch.models import TransferAction
from apps.environmental.models import EnvironmentalReading
from apps.historian.models import HistorianTagLink

SNAPSHOT_NOTE_PREFIX = "[transfer_snapshot]"
SNAPSHOT_MOMENTS = {"start", "in_transit", "finish", "handoff"}


@dataclass
class SnapshotResult:
    """Simple snapshot result payload."""

    created_count: int
    skipped_count: int
    missing_value_count: int


def _fallback_value(parameter_name: str, action: TransferAction) -> Optional[Decimal]:
    """Use execution payload values when historian data is unavailable."""
    lowered = (parameter_name or "").lower()
    if "temp" in lowered and action.water_temp_c is not None:
        return action.water_temp_c
    if ("oxygen" in lowered or "o2" in lowered) and action.oxygen_level is not None:
        return action.oxygen_level
    return None


def _latest_value_for_link(
    *,
    container_id: int,
    parameter_id: int,
    sensor_id: Optional[int],
    reading_time,
):
    """Find latest ingested reading up to execution time for the mapping link."""
    query = EnvironmentalReading.objects.filter(parameter_id=parameter_id).filter(
        Q(container_id=container_id) | Q(sensor_id=sensor_id)
    )
    if reading_time:
        query = query.filter(reading_time__lte=reading_time)
    return query.order_by("-reading_time").first()


def _snapshot_for_assignment(
    *,
    action: TransferAction,
    assignment,
    side: str,
    reading_time,
    executed_by_id: Optional[int],
    moment: str,
) -> SnapshotResult:
    created_count = 0
    skipped_count = 0
    missing_value_count = 0

    if not assignment or not assignment.container_id:
        return SnapshotResult(0, 0, 0)

    container_id = assignment.container_id
    links = (
        HistorianTagLink.objects.select_related("parameter", "sensor")
        .filter(container_id=container_id, parameter__isnull=False)
        .order_by("id")
    )

    seen_parameters = set()
    for link in links:
        if link.parameter_id in seen_parameters:
            continue
        seen_parameters.add(link.parameter_id)

        marker = (
            f"action={action.id};side={side};parameter={link.parameter_id};"
            f"moment={moment}"
        )
        existing = EnvironmentalReading.objects.filter(
            batch_container_assignment_id=assignment.id,
            parameter_id=link.parameter_id,
            reading_time=reading_time,
            notes__contains=marker,
        ).exists()
        if existing:
            skipped_count += 1
            continue

        latest = _latest_value_for_link(
            container_id=container_id,
            parameter_id=link.parameter_id,
            sensor_id=link.sensor_id,
            reading_time=reading_time,
        )
        value = latest.value if latest else _fallback_value(link.parameter.name, action)
        if value is None:
            missing_value_count += 1
            continue

        EnvironmentalReading.objects.create(
            parameter_id=link.parameter_id,
            container_id=container_id,
            batch_id=action.workflow.batch_id,
            sensor_id=(latest.sensor_id if latest else link.sensor_id),
            batch_container_assignment_id=assignment.id,
            value=value,
            reading_time=reading_time,
            is_manual=latest is None,
            recorded_by_id=executed_by_id,
            notes=(
                f"{SNAPSHOT_NOTE_PREFIX} {marker};carrier_snapshot=true"
            ),
        )
        created_count += 1

    return SnapshotResult(
        created_count=created_count,
        skipped_count=skipped_count,
        missing_value_count=missing_value_count,
    )


def snapshot_transfer_action_readings(
    *,
    action_id: int,
    reading_time=None,
    executed_by_id: Optional[int] = None,
    moment: str = "handoff",
) -> Dict[str, int]:
    """
    Snapshot container readings for source/destination assignments.

    This function relies on existing ingested readings mapped through
    ``historian_tag_link`` and duplicates them at execution timestamp for
    assignment-level compliance traceability.
    """
    action = TransferAction.objects.select_related(
        "workflow__batch",
        "source_assignment",
        "dest_assignment",
    ).get(pk=action_id)
    snapshot_moment = (moment or "handoff").strip().lower()
    if snapshot_moment not in SNAPSHOT_MOMENTS:
        snapshot_moment = "handoff"
    snapshot_time = reading_time or timezone.now()

    source_result = _snapshot_for_assignment(
        action=action,
        assignment=action.source_assignment,
        side="source",
        reading_time=snapshot_time,
        executed_by_id=executed_by_id,
        moment=snapshot_moment,
    )
    dest_result = _snapshot_for_assignment(
        action=action,
        assignment=action.dest_assignment,
        side="dest",
        reading_time=snapshot_time,
        executed_by_id=executed_by_id,
        moment=snapshot_moment,
    )

    return {
        "moment": snapshot_moment,
        "created_count": source_result.created_count + dest_result.created_count,
        "skipped_count": source_result.skipped_count + dest_result.skipped_count,
        "missing_value_count": (
            source_result.missing_value_count + dest_result.missing_value_count
        ),
    }
