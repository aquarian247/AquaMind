"""Historian snapshot helpers for transfer handoff compliance records."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.batch.access import can_override_transport_compliance
from apps.batch.models import TransferAction
from apps.environmental.models import EnvironmentalParameter, EnvironmentalReading
from apps.historian.models import HistorianTagLink

SNAPSHOT_NOTE_PREFIX = "[transfer_snapshot]"
SNAPSHOT_MOMENTS = {"start", "in_transit", "finish", "handoff"}

REQUIRED_START_PARAMETER_ALIASES = {
    "oxygen": ("oxygen", "o2", "dissolved oxygen"),
    "temperature": ("temperature", "temp"),
    "co2": ("co2", "carbon dioxide"),
}

MAPPING_POLICY_STRICT = "STRICT"
MAPPING_POLICY_OVERRIDE = "OVERRIDE"


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
    filters = Q(container_id=container_id)
    if sensor_id is not None:
        filters = filters | Q(sensor_id=sensor_id)
    query = EnvironmentalReading.objects.filter(parameter_id=parameter_id).filter(filters)
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
            notes=(f"{SNAPSHOT_NOTE_PREFIX} {marker};carrier_snapshot=true"),
        )
        created_count += 1

    return SnapshotResult(
        created_count=created_count,
        skipped_count=skipped_count,
        missing_value_count=missing_value_count,
    )


def _get_mapping_policy() -> str:
    policy = str(
        getattr(settings, "TRANSFER_START_MISSING_MAPPING_POLICY", MAPPING_POLICY_STRICT)
    ).upper()
    if policy not in {MAPPING_POLICY_STRICT, MAPPING_POLICY_OVERRIDE}:
        return MAPPING_POLICY_STRICT
    return policy


def _required_key_for_parameter(name: str) -> Optional[str]:
    lowered = (name or "").lower().strip()
    normalized = "".join(char for char in lowered if char.isalnum())

    # Order matters: detect CO2 before O2 to avoid "co2" matching oxygen aliases.
    if "co2" in normalized or "carbondioxide" in normalized:
        return "co2"
    if "temperature" in lowered or normalized.startswith("temp"):
        return "temperature"
    if "oxygen" in lowered or normalized in {"o2", "dissolvedoxygen"}:
        return "oxygen"

    for required_key, aliases in REQUIRED_START_PARAMETER_ALIASES.items():
        for alias in aliases:
            alias_norm = "".join(char for char in alias.lower() if char.isalnum())
            if alias_norm and alias_norm == normalized:
                return required_key
    return None


def _resolve_required_links(container_id: int) -> Tuple[Dict[str, HistorianTagLink], list]:
    links = (
        HistorianTagLink.objects.select_related("parameter", "sensor")
        .filter(container_id=container_id, parameter__isnull=False)
        .order_by("id")
    )
    found: Dict[str, HistorianTagLink] = {}
    for link in links:
        key = _required_key_for_parameter(link.parameter.name if link.parameter else "")
        if not key:
            continue
        if key not in found:
            found[key] = link

    missing = [key for key in REQUIRED_START_PARAMETER_ALIASES.keys() if key not in found]
    return found, missing


def _resolve_parameter_for_required_key(required_key: str) -> Optional[EnvironmentalParameter]:
    aliases = REQUIRED_START_PARAMETER_ALIASES.get(required_key, ())
    query = Q()
    for alias in aliases:
        query |= Q(name__iexact=alias)
    if not query:
        return None
    return EnvironmentalParameter.objects.filter(query).order_by("id").first()


def _normalize_manual_side_readings(values: Optional[Dict]) -> Dict[str, Optional[Decimal]]:
    normalized: Dict[str, Optional[Decimal]] = {
        "oxygen": None,
        "temperature": None,
        "co2": None,
    }
    if not isinstance(values, dict):
        return normalized

    for key in normalized.keys():
        raw = values.get(key)
        if raw in (None, ""):
            continue
        try:
            number = Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({f"manual_{key}": f"Invalid decimal value: {raw}"}) from exc
        normalized[key] = number
    return normalized


def _capture_required_value(
    *,
    action: TransferAction,
    side: str,
    parameter_id: int,
    sensor_id: Optional[int],
    container_id: int,
    assignment_id: Optional[int],
    reading_time,
    executed_by_id: Optional[int],
    required_key: str,
    override_applied: bool,
    manual_value: Optional[Decimal] = None,
):
    marker = (
        f"action={action.id};side={side};parameter={parameter_id};"
        f"moment=start;required_key={required_key}"
    )
    existing = EnvironmentalReading.objects.filter(
        container_id=container_id,
        parameter_id=parameter_id,
        reading_time=reading_time,
        notes__contains=marker,
    )
    if assignment_id:
        existing = existing.filter(batch_container_assignment_id=assignment_id)
    if existing.exists():
        return "skipped", False

    latest = None
    if manual_value is None:
        latest = _latest_value_for_link(
            container_id=container_id,
            parameter_id=parameter_id,
            sensor_id=sensor_id,
            reading_time=reading_time,
        )
        if not latest:
            return "missing_value", False

    value = manual_value if manual_value is not None else latest.value
    reading_sensor_id = None
    if latest is not None:
        reading_sensor_id = latest.sensor_id or sensor_id
    else:
        reading_sensor_id = sensor_id

    EnvironmentalReading.objects.create(
        parameter_id=parameter_id,
        container_id=container_id,
        batch_id=action.workflow.batch_id,
        sensor_id=reading_sensor_id,
        batch_container_assignment_id=assignment_id,
        value=value,
        reading_time=reading_time,
        is_manual=manual_value is not None,
        recorded_by_id=executed_by_id,
        notes=(
            f"{SNAPSHOT_NOTE_PREFIX} {marker};carrier_snapshot=true;"
            f"mandatory_start=true;override_applied={str(override_applied).lower()};"
            f"manual_input={str(manual_value is not None).lower()}"
        ),
    )
    return "created", manual_value is not None


def capture_mandatory_start_snapshot(
    *,
    action: TransferAction,
    source_assignment,
    dest_container,
    reading_time=None,
    executed_by_id: Optional[int] = None,
    allow_override: bool = False,
    compliance_override_note: str = "",
    override_user=None,
    source_manual_readings: Optional[Dict] = None,
    dest_manual_readings: Optional[Dict] = None,
) -> Dict:
    """
    Capture mandatory start-of-transfer compliance snapshot.

    Required mapping: source + destination must have AVEVA links for
    oxygen, temperature, and co2. Missing links are handled by policy:
    - STRICT: block handoff start
    - OVERRIDE: privileged users may override with explicit note
    """
    snapshot_time = reading_time or timezone.now()
    policy = _get_mapping_policy()
    source_manual = _normalize_manual_side_readings(source_manual_readings)
    dest_manual = _normalize_manual_side_readings(dest_manual_readings)

    source_links, source_missing = _resolve_required_links(source_assignment.container_id)
    dest_links, dest_missing = _resolve_required_links(dest_container.id)
    missing_mapping = {
        "source": source_missing,
        "destination": dest_missing,
    }
    has_missing_mapping = bool(source_missing or dest_missing)

    override_note = (compliance_override_note or "").strip()
    override_applied = False
    if has_missing_mapping:
        if policy == MAPPING_POLICY_STRICT:
            raise ValidationError(
                {
                    "missing_historian_mapping": [str(missing_mapping)],
                    "detail": (
                        "Mandatory AVEVA mapping missing for start snapshot. "
                        "Configure oxygen/temperature/co2 mapping for both source "
                        "and destination."
                    ),
                }
            )
        if not allow_override:
            raise ValidationError(
                {
                    "missing_historian_mapping": [str(missing_mapping)],
                    "detail": (
                        "Missing AVEVA mapping requires privileged override. "
                        "Set allow_compliance_override=true and include compliance_override_note."
                    ),
                }
            )
        if not override_note:
            raise ValidationError(
                {
                    "compliance_override_note": (
                        "Compliance override note is required when mapping is missing."
                    )
                }
            )
        if not can_override_transport_compliance(override_user):
            raise ValidationError(
                {
                    "detail": "You do not have permission to override compliance mapping checks."
                }
            )
        override_applied = True

    created_count = 0
    skipped_count = 0
    missing_value_count = 0
    manual_input_count = 0
    captured_parameters = {"source": [], "destination": []}

    for key in REQUIRED_START_PARAMETER_ALIASES.keys():
        source_link = source_links.get(key)
        source_parameter = source_link.parameter if source_link else _resolve_parameter_for_required_key(key)
        if source_parameter:
            source_status, source_used_manual = _capture_required_value(
                action=action,
                side="source",
                parameter_id=source_parameter.id,
                sensor_id=source_link.sensor_id if source_link else None,
                container_id=source_assignment.container_id,
                assignment_id=source_assignment.id,
                reading_time=snapshot_time,
                executed_by_id=executed_by_id,
                required_key=key,
                override_applied=override_applied,
                manual_value=source_manual.get(key),
            )
        else:
            source_status, source_used_manual = "missing_value", False

        status = source_status
        if status == "created":
            created_count += 1
            captured_parameters["source"].append(key)
            if source_used_manual:
                manual_input_count += 1
        elif status == "skipped":
            skipped_count += 1
        else:
            missing_value_count += 1

        dest_link = dest_links.get(key)
        dest_parameter = dest_link.parameter if dest_link else _resolve_parameter_for_required_key(key)
        if dest_parameter:
            dest_status, dest_used_manual = _capture_required_value(
                action=action,
                side="dest",
                parameter_id=dest_parameter.id,
                sensor_id=dest_link.sensor_id if dest_link else None,
                container_id=dest_container.id,
                assignment_id=action.dest_assignment_id,
                reading_time=snapshot_time,
                executed_by_id=executed_by_id,
                required_key=key,
                override_applied=override_applied,
                manual_value=dest_manual.get(key),
            )
        else:
            dest_status, dest_used_manual = "missing_value", False

        status = dest_status
        if status == "created":
            created_count += 1
            captured_parameters["destination"].append(key)
            if dest_used_manual:
                manual_input_count += 1
        elif status == "skipped":
            skipped_count += 1
        else:
            missing_value_count += 1

    if override_applied:
        action.notes = (
            f"{action.notes}\n[compliance_override] {override_note}"
        ).strip()
        action.save(update_fields=["notes", "updated_at"])

    return {
        "moment": "start",
        "policy": policy,
        "override_applied": override_applied,
        "override_note": override_note if override_applied else "",
        "missing_mapping": missing_mapping,
        "created_count": created_count,
        "skipped_count": skipped_count,
        "missing_value_count": missing_value_count,
        "manual_input_count": manual_input_count,
        "captured_parameters": captured_parameters,
        "status": "captured_with_override" if override_applied else "captured",
    }


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
