#!/usr/bin/env python3
"""Migrate exact FW->Sea transfer events from a persisted event ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from collections import defaultdict
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

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.batch.models import Batch, BatchTransferWorkflow, LifeCycleStage, TransferAction
from apps.batch.models.assignment import BatchContainerAssignment
from apps.migration_support.models import ExternalIdMap
from scripts.migration.history import save_with_history
from scripts.migration.tools.population_assignment_mapping import get_assignment_external_map


User = get_user_model()
MIGRATION_TRANSPORT_BYPASS_NOTE = (
    "[migration_transport_bypass] FishTalk source data lacks deterministic "
    "per-leg transport handoff metadata (truck/vessel/trip/compartment + "
    "mandatory start snapshot chain). Migration persists historical transfer "
    "edges as completed direct actions and forces workflows non-dynamic."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate exact InternalDelivery transfer events")
    parser.add_argument("--component-key", required=True)
    parser.add_argument("--events-csv", required=True)
    parser.add_argument(
        "--scoped-assignment-maps-only",
        action="store_true",
        help=(
            "Resolve FishTalk population assignments only via component-scoped "
            "external maps and never through legacy global Populations maps."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_dt(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, dt_timezone.utc)


def build_workflow_number(component_key: str, sales_op: str, input_op: str, op_date) -> str:
    seed = f"{component_key}|{sales_op}|{input_op}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10].upper()
    return f"FT-IDL-{op_date.strftime('%Y%m%d')}-{digest}"[:50]


def append_note_once(existing: str | None, note: str) -> str:
    current = (existing or "").strip()
    if note in current:
        return current
    return f"{current}\n{note}".strip()


def enforce_static_workflow_for_migration(
    workflow: BatchTransferWorkflow,
    *,
    history_user,
    history_reason: str,
) -> None:
    changed = False
    if workflow.is_dynamic_execution:
        workflow.is_dynamic_execution = False
        changed = True
    if workflow.dynamic_route_mode is not None:
        workflow.dynamic_route_mode = None
        changed = True
    if workflow.dynamic_completed_by_id is not None:
        workflow.dynamic_completed_by = None
        changed = True
    if workflow.dynamic_completed_at is not None:
        workflow.dynamic_completed_at = None
        changed = True
    updated_notes = append_note_once(workflow.notes, MIGRATION_TRANSPORT_BYPASS_NOTE)
    if updated_notes != (workflow.notes or "").strip():
        workflow.notes = updated_notes
        changed = True
    if changed:
        save_with_history(workflow, user=history_user, reason=history_reason)


def load_event_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    args = parse_args()

    component_key = args.component_key.strip()
    events_path = Path(args.events_csv).resolve()
    event_rows = load_event_rows(events_path)
    if not event_rows:
        raise SystemExit(f"No event rows found in {events_path}")

    batch_map = ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model="PopulationComponent",
        source_identifier=component_key,
    ).first()
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run pilot_migrate_component.py first."
        )
    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot create transfer workflows.")

    fallback_stage = LifeCycleStage.objects.first()
    if fallback_stage is None:
        raise SystemExit("Missing LifeCycleStage master data.")

    grouped_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    missing_assignments: list[str] = []
    resolved_rows: list[dict] = []
    for row in event_rows:
        event_id = (row.get("event_id") or "").strip()
        source_population_id = (row.get("source_population_id") or "").strip()
        destination_population_id = (row.get("destination_population_id") or "").strip()
        sales_operation_id = (row.get("sales_operation_id") or "").strip()
        input_operation_id = (row.get("input_operation_id") or "").strip()
        sale_dt = parse_dt(row.get("sale_timestamp") or "")
        if (
            not event_id
            or not source_population_id
            or not destination_population_id
            or not sales_operation_id
            or not input_operation_id
            or sale_dt is None
        ):
            raise SystemExit(f"Incomplete event row: {row}")

        source_map = get_assignment_external_map(
            source_population_id,
            component_key=component_key,
            allow_legacy_fallback=not args.scoped_assignment_maps_only,
        )
        dest_map = get_assignment_external_map(
            destination_population_id,
            component_key=component_key,
            allow_legacy_fallback=not args.scoped_assignment_maps_only,
        )
        if not source_map or not dest_map:
            missing_assignments.append(event_id)
            continue

        source_assignment = BatchContainerAssignment.objects.filter(
            pk=source_map.target_object_id
        ).select_related("lifecycle_stage").first()
        dest_assignment = BatchContainerAssignment.objects.filter(
            pk=dest_map.target_object_id
        ).select_related("lifecycle_stage").first()
        if source_assignment is None or dest_assignment is None:
            missing_assignments.append(event_id)
            continue

        sale_dt = ensure_aware(sale_dt)
        transferred_count = int(round(float(row.get("transferred_count") or 0)))
        avg_weight_g = Decimal(str(row.get("avg_weight_g") or 0)).quantize(Decimal("0.01"))
        transferred_biomass_kg = Decimal(str(row.get("transferred_biomass_kg") or 0)).quantize(
            Decimal("0.01")
        )
        if transferred_biomass_kg <= Decimal("0.00") and transferred_count > 0 and avg_weight_g > Decimal("0.00"):
            transferred_biomass_kg = ((Decimal(transferred_count) * avg_weight_g) / Decimal("1000")).quantize(
                Decimal("0.01")
            )

        resolved = dict(row)
        resolved.update(
            {
                "source_assignment": source_assignment,
                "dest_assignment": dest_assignment,
                "sale_dt": sale_dt,
                "transferred_count": transferred_count,
                "transferred_biomass_kg": transferred_biomass_kg,
            }
        )
        resolved_rows.append(resolved)
        grouped_rows[(sales_operation_id, input_operation_id)].append(resolved)

    if missing_assignments:
        raise SystemExit(
            "Missing component-scoped assignments for event rows: "
            + ", ".join(sorted(missing_assignments))
        )

    if args.dry_run:
        print(
            f"[dry-run] Would migrate exact transfer events into batch={batch.batch_number} "
            f"(workflows={len(grouped_rows)}, actions={len(resolved_rows)})"
        )
        return 0

    history_reason = f"FishTalk migration: exact transfer events for component {component_key}"
    created_wf = updated_wf = created_actions = updated_actions = 0

    with transaction.atomic():
        for (sales_operation_id, input_operation_id), rows in sorted(grouped_rows.items()):
            rows_sorted = sorted(rows, key=lambda item: (item["sale_dt"], item["event_id"]))
            first_row = rows_sorted[0]
            source_stage = (
                first_row["source_assignment"].lifecycle_stage
                or first_row["dest_assignment"].lifecycle_stage
                or fallback_stage
            )
            dest_stage = (
                first_row["dest_assignment"].lifecycle_stage
                or first_row["source_assignment"].lifecycle_stage
                or fallback_stage
            )
            workflow_type = (
                "LIFECYCLE_TRANSITION"
                if source_stage.id != dest_stage.id
                else "CONTAINER_REDISTRIBUTION"
            )
            start_date = min(row["sale_dt"].date() for row in rows_sorted)
            end_date = max(row["sale_dt"].date() for row in rows_sorted)
            workflow_identifier = f"{component_key}:{sales_operation_id}:{input_operation_id}"
            workflow_map = ExternalIdMap.objects.filter(
                source_system="FishTalk",
                source_model="InternalDeliveryOperationPair",
                source_identifier=workflow_identifier,
            ).first()
            workflow = None
            if workflow_map:
                workflow = BatchTransferWorkflow.objects.filter(pk=workflow_map.target_object_id).first()

            if workflow is None:
                workflow = BatchTransferWorkflow(
                    workflow_number=build_workflow_number(
                        component_key, sales_operation_id, input_operation_id, first_row["sale_dt"].date()
                    ),
                    batch=batch,
                    workflow_type=workflow_type,
                    source_lifecycle_stage=source_stage,
                    dest_lifecycle_stage=dest_stage,
                    status="COMPLETED",
                    planned_start_date=start_date,
                    planned_completion_date=end_date,
                    actual_start_date=start_date,
                    actual_completion_date=end_date,
                    initiated_by=user,
                    completed_by=user,
                    notes=(
                        f"FishTalk InternalDelivery; SalesOperationID={sales_operation_id}; "
                        f"InputOperationID={input_operation_id}; component={component_key}"
                    ),
                )
                save_with_history(workflow, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="InternalDeliveryOperationPair",
                    source_identifier=workflow_identifier,
                    defaults={
                        "target_app_label": workflow._meta.app_label,
                        "target_model": workflow._meta.model_name,
                        "target_object_id": workflow.pk,
                        "metadata": {
                            "component_key": component_key,
                            "sales_operation_id": sales_operation_id,
                            "input_operation_id": input_operation_id,
                        },
                    },
                )
                created_wf += 1
            else:
                workflow.workflow_type = workflow_type
                workflow.source_lifecycle_stage = source_stage
                workflow.dest_lifecycle_stage = dest_stage
                workflow.planned_start_date = start_date
                workflow.planned_completion_date = end_date
                workflow.actual_start_date = start_date
                workflow.actual_completion_date = end_date
                workflow.status = "COMPLETED"
                workflow.completed_by = user
                save_with_history(workflow, user=user, reason=history_reason)
                updated_wf += 1

            next_action_number = (
                workflow.actions.order_by("-action_number").values_list("action_number", flat=True).first() or 0
            ) + 1

            for row in rows_sorted:
                action_identifier = f"{component_key}:{row['event_id']}"
                action_map = ExternalIdMap.objects.filter(
                    source_system="FishTalk",
                    source_model="InternalDeliveryTransferEvent",
                    source_identifier=action_identifier,
                ).first()
                source_assignment = row["source_assignment"]
                dest_assignment = row["dest_assignment"]
                source_population_before = max(
                    int(source_assignment.population_count or 0),
                    int(row["transferred_count"] or 0),
                )
                defaults = {
                    "workflow": workflow,
                    "source_assignment": source_assignment,
                    "dest_assignment": dest_assignment,
                    "source_population_before": source_population_before,
                    "transferred_count": int(row["transferred_count"] or 0),
                    "mortality_during_transfer": 0,
                    "transferred_biomass_kg": row["transferred_biomass_kg"],
                    "allow_mixed": False,
                    "status": "COMPLETED",
                    "created_via": "PLANNED",
                    "leg_type": None,
                    "planned_date": row["sale_dt"].date(),
                    "actual_execution_date": row["sale_dt"].date(),
                    "executed_at": row["sale_dt"],
                    "transfer_method": None,
                    "notes": (
                        f"FishTalk exact transfer event {row['event_id']}; "
                        f"SalesOperationID={sales_operation_id}; InputOperationID={input_operation_id}; "
                        f"lineage={row.get('lineage_class') or ''}; "
                        f"destination_ring_text={row.get('destination_ring_text') or ''}"
                    ).strip(),
                }
                if action_map:
                    action = TransferAction.objects.filter(pk=action_map.target_object_id).first()
                    if action is None:
                        action_map = None
                if action_map:
                    action = TransferAction.objects.get(pk=action_map.target_object_id)
                    for key, value in defaults.items():
                        setattr(action, key, value)
                    if not action.action_number:
                        action.action_number = next_action_number
                        next_action_number += 1
                    save_with_history(action, user=user, reason=history_reason)
                    updated_actions += 1
                else:
                    while TransferAction.objects.filter(workflow=workflow, action_number=next_action_number).exists():
                        next_action_number += 1
                    action = TransferAction(action_number=next_action_number, **defaults)
                    next_action_number += 1
                    save_with_history(action, user=user, reason=history_reason)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="InternalDeliveryTransferEvent",
                        source_identifier=action_identifier,
                        defaults={
                            "target_app_label": action._meta.app_label,
                            "target_model": action._meta.model_name,
                            "target_object_id": action.pk,
                            "metadata": {
                                "component_key": component_key,
                                "event_id": row["event_id"],
                                "sales_operation_id": sales_operation_id,
                                "input_operation_id": input_operation_id,
                            },
                        },
                    )
                    created_actions += 1

            workflow.total_actions_planned = workflow.actions.count()
            workflow.actions_completed = workflow.actions.filter(status="COMPLETED").count()
            workflow.completion_percentage = Decimal("100.00") if workflow.total_actions_planned else Decimal("0.00")
            workflow.status = "COMPLETED" if workflow.total_actions_planned else workflow.status
            save_with_history(workflow, user=user, reason=history_reason)
            enforce_static_workflow_for_migration(
                workflow,
                history_user=user,
                history_reason=history_reason,
            )
            workflow.recalculate_totals()

    print(
        f"Migrated exact transfer events for component_key={component_key} into batch={batch.batch_number} "
        f"(workflows created={created_wf}, updated={updated_wf}; "
        f"actions created={created_actions}, updated={updated_actions})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
