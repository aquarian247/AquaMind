"""Dynamic transfer workflow execution helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.batch.models import BatchContainerAssignment, BatchTransferWorkflow, TransferAction
from apps.environmental.services.historian_snapshot import (
    capture_mandatory_start_snapshot,
)
from apps.infrastructure.models import Container


LEG_TO_SOURCE_CATEGORY = {
    "STATION_TO_VESSEL": "station",
    "STATION_TO_TRUCK": "station",
    "TRUCK_TO_VESSEL": "truck",
    "VESSEL_TO_RING": "vessel",
}

LEG_TO_DEST_CATEGORY = {
    "STATION_TO_VESSEL": "vessel",
    "STATION_TO_TRUCK": "truck",
    "TRUCK_TO_VESSEL": "vessel",
    "VESSEL_TO_RING": "ring",
}


def get_container_category(container: Container | None) -> str:
    """Map infrastructure containers into transport execution categories."""
    if not container:
        return "unknown"
    if container.carrier_id and container.carrier and container.carrier.carrier_type == "TRUCK":
        return "truck"
    if container.carrier_id and container.carrier and container.carrier.carrier_type == "VESSEL":
        return "vessel"
    if container.area_id:
        return "ring"
    if container.hall_id:
        return "station"
    return "unknown"


def _validate_leg_allowed(workflow: BatchTransferWorkflow, leg_type: str) -> None:
    allowed = workflow.get_allowed_leg_types()
    if not allowed:
        raise ValidationError("Dynamic route mode is not configured for this workflow.")
    if leg_type not in allowed:
        raise ValidationError(
            f"Leg type {leg_type} is not allowed for route mode {workflow.dynamic_route_mode}."
        )


def _serialize_container(container: Container) -> Dict:
    return {
        "id": container.id,
        "name": container.name,
        "category": get_container_category(container),
        "carrier_type": container.carrier.carrier_type if container.carrier_id and container.carrier else None,
        "carrier_name": container.carrier.name if container.carrier_id and container.carrier else None,
        "station_name": (
            container.hall.freshwater_station.name
            if container.hall_id and container.hall and container.hall.freshwater_station_id
            else None
        ),
        "hall_name": container.hall.name if container.hall_id and container.hall else None,
        "area_name": container.area.name if container.area_id and container.area else None,
    }


def _serialize_assignment(assignment: BatchContainerAssignment) -> Dict:
    return {
        "id": assignment.id,
        "population_count": assignment.population_count,
        "biomass_kg": str(assignment.biomass_kg),
        "avg_weight_g": str(assignment.avg_weight_g) if assignment.avg_weight_g is not None else None,
        "lifecycle_stage_id": assignment.lifecycle_stage_id,
        "lifecycle_stage_name": assignment.lifecycle_stage.name if assignment.lifecycle_stage_id else None,
        "container": _serialize_container(assignment.container),
    }


def _serialize_action(action: TransferAction) -> Dict:
    source_container = action.source_assignment.container if action.source_assignment_id else None
    dest_container = (
        action.dest_assignment.container
        if action.dest_assignment_id
        else action.dest_container
    )
    return {
        "id": action.id,
        "action_number": action.action_number,
        "status": action.status,
        "leg_type": action.leg_type,
        "source_assignment_id": action.source_assignment_id,
        "source_container": _serialize_container(source_container) if source_container else None,
        "dest_assignment_id": action.dest_assignment_id,
        "dest_container": _serialize_container(dest_container) if dest_container else None,
        "transferred_count": action.transferred_count,
        "transferred_biomass_kg": str(action.transferred_biomass_kg),
        "mortality_during_transfer": action.mortality_during_transfer,
        "created_via": action.created_via,
        "actual_execution_date": action.actual_execution_date,
        "executed_at": action.executed_at,
        "started_at": action.created_at,
        "executed_by": action.executed_by.username if action.executed_by_id else None,
        "notes": action.notes,
    }


def build_execution_context(workflow: BatchTransferWorkflow) -> Dict:
    """Build page payload for dynamic workflow execution."""
    if not workflow.is_dynamic_execution:
        raise ValidationError("Execution context is only available for dynamic workflows.")

    source_assignments = (
        BatchContainerAssignment.objects.select_related(
            "container__carrier",
            "container__hall__freshwater_station",
            "container__area",
            "lifecycle_stage",
        )
        .filter(batch=workflow.batch, is_active=True, population_count__gt=0)
        .order_by("container__name", "id")
    )

    sources = {"station": [], "truck": [], "vessel": []}
    for assignment in source_assignments:
        category = get_container_category(assignment.container)
        if category in sources:
            sources[category].append(_serialize_assignment(assignment))

    destinations = {
        "truck": [],
        "vessel": [],
        "ring": [],
    }
    destination_queryset = (
        Container.objects.select_related(
            "carrier",
            "hall__freshwater_station",
            "area",
        )
        .filter(active=True)
        .order_by("name")
    )
    for container in destination_queryset:
        category = get_container_category(container)
        if category in destinations:
            destinations[category].append(_serialize_container(container))

    in_progress_actions = list(
        workflow.actions.select_related(
            "source_assignment__container__carrier",
            "source_assignment__container__hall__freshwater_station",
            "source_assignment__container__area",
            "dest_assignment__container__carrier",
            "dest_assignment__container__hall__freshwater_station",
            "dest_assignment__container__area",
            "dest_container__carrier",
            "dest_container__hall__freshwater_station",
            "dest_container__area",
            "executed_by",
        )
        .filter(status="IN_PROGRESS")
        .order_by("action_number")
    )
    recent_actions = list(
        workflow.actions.select_related(
            "source_assignment__container__carrier",
            "source_assignment__container__hall__freshwater_station",
            "source_assignment__container__area",
            "dest_assignment__container__carrier",
            "dest_assignment__container__hall__freshwater_station",
            "dest_assignment__container__area",
            "dest_container__carrier",
            "dest_container__hall__freshwater_station",
            "dest_container__area",
            "executed_by",
        )
        .order_by("-executed_at", "-id")[:20]
    )

    return {
        "workflow_id": workflow.id,
        "workflow_number": workflow.workflow_number,
        "status": workflow.status,
        "dynamic_route_mode": workflow.dynamic_route_mode,
        "allowed_leg_types": workflow.get_allowed_leg_types(),
        "sources": sources,
        "destinations": destinations,
        "in_progress_actions": [_serialize_action(action) for action in in_progress_actions],
        "recent_actions": [_serialize_action(action) for action in recent_actions],
        "progress": {
            "actions_completed": workflow.actions_completed,
            "total_actions_planned": workflow.total_actions_planned,
            "completion_percentage": str(workflow.completion_percentage),
            "total_transferred_count": workflow.total_transferred_count,
            "total_biomass_kg": str(workflow.total_biomass_kg),
            "total_mortality_count": workflow.total_mortality_count,
            "estimated_total_count": workflow.estimated_total_count,
            "estimated_total_biomass_kg": (
                str(workflow.estimated_total_biomass_kg)
                if workflow.estimated_total_biomass_kg is not None
                else None
            ),
        },
    }


def start_dynamic_handoff(
    *,
    workflow: BatchTransferWorkflow,
    started_by,
    leg_type: str,
    source_assignment_id: int,
    dest_container_id: int,
    planned_transferred_count: int,
    planned_transferred_biomass_kg,
    transfer_method: str | None = None,
    allow_mixed: bool = False,
    notes: str = "",
    allow_compliance_override: bool = False,
    compliance_override_note: str = "",
    source_manual_readings: Dict | None = None,
    dest_manual_readings: Dict | None = None,
) -> Dict:
    """
    Start a dynamic handoff by creating an IN_PROGRESS action + start snapshot.
    """
    if not workflow.is_dynamic_execution:
        raise ValidationError("Start handoff is only valid for dynamic workflows.")
    if workflow.status not in {"PLANNED", "IN_PROGRESS"}:
        raise ValidationError(
            f"Cannot start handoff when workflow status is {workflow.status}."
        )

    with transaction.atomic():
        if workflow.status == "PLANNED":
            workflow.mark_in_progress()
            workflow.refresh_from_db(fields=["status", "actual_start_date", "updated_at"])

        _validate_leg_allowed(workflow, leg_type)

        source_assignment = BatchContainerAssignment.objects.select_for_update().get(
            pk=source_assignment_id,
            batch=workflow.batch,
        )
        if not source_assignment.is_active or source_assignment.population_count <= 0:
            raise ValidationError("Source assignment is not active or has no available fish.")

        dest_container = Container.objects.get(pk=dest_container_id, active=True)

        expected_source = LEG_TO_SOURCE_CATEGORY.get(leg_type)
        expected_dest = LEG_TO_DEST_CATEGORY.get(leg_type)
        actual_source = get_container_category(source_assignment.container)
        actual_dest = get_container_category(dest_container)
        if expected_source != actual_source:
            raise ValidationError(
                f"Invalid source category {actual_source}; expected {expected_source}."
            )
        if expected_dest != actual_dest:
            raise ValidationError(
                f"Invalid destination category {actual_dest}; expected {expected_dest}."
            )

        if planned_transferred_count > source_assignment.population_count:
            raise ValidationError(
                "Planned transfer count cannot exceed available source population."
            )

        in_progress_for_source = TransferAction.objects.select_for_update().filter(
            workflow=workflow,
            source_assignment=source_assignment,
            status="IN_PROGRESS",
        )
        if in_progress_for_source.exists():
            raise ValidationError(
                "Source assignment already has an IN_PROGRESS handoff."
            )

        next_action_number = (
            workflow.actions.aggregate(max_number=Max("action_number")).get("max_number") or 0
        ) + 1
        action = TransferAction.objects.create(
            workflow=workflow,
            action_number=next_action_number,
            status="IN_PROGRESS",
            created_via="DYNAMIC_LIVE",
            leg_type=leg_type,
            source_assignment=source_assignment,
            source_population_before=source_assignment.population_count,
            dest_container=dest_container,
            transferred_count=planned_transferred_count,
            transferred_biomass_kg=Decimal(planned_transferred_biomass_kg),
            planned_date=timezone.now().date(),
            transfer_method=transfer_method,
            allow_mixed=allow_mixed,
            notes=notes or "",
        )

        snapshot_summary = capture_mandatory_start_snapshot(
            action=action,
            source_assignment=source_assignment,
            dest_container=dest_container,
            reading_time=timezone.now(),
            executed_by_id=getattr(started_by, "id", None),
            allow_override=allow_compliance_override,
            compliance_override_note=compliance_override_note,
            override_user=started_by,
            source_manual_readings=source_manual_readings,
            dest_manual_readings=dest_manual_readings,
        )

    return {
        "action": action,
        "snapshot_summary": snapshot_summary,
    }
