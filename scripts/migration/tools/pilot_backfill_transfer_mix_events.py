#!/usr/bin/env python3
# flake8: noqa
"""Backfill container-scoped mix lineage from historical transfer actions.

This script is order-independent and idempotent at action scope:
- It scans completed `TransferAction` rows.
- It identifies physical co-location at destination container + transfer date.
- It materializes `BatchMixEvent` + `BatchMixEventComponent`.
- It rebuilds `BatchComposition` as batch-level fallback for the mixed batch.
- It updates `allow_mixed=True` for qualified actions.
- It can optionally rewrite destination assignment history to keep downstream state mixed.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timezone as dt_timezone
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
from django.db.models import Q
from django.utils import timezone

from apps.batch.models import (
    Batch,
    BatchComposition,
    BatchContainerAssignment,
    BatchMixEvent,
    BatchMixEventComponent,
    TransferAction,
)
from scripts.migration.history import save_with_history


User = get_user_model()


@dataclass
class BackfillStats:
    scanned_actions: int = 0
    skipped_missing_date: int = 0
    skipped_non_mix: int = 0
    skipped_zero_total: int = 0
    qualified_mix_actions: int = 0
    mixed_batches_created: int = 0
    mixed_batches_updated: int = 0
    mix_events_created: int = 0
    mix_events_updated: int = 0
    components_written: int = 0
    compositions_written: int = 0
    actions_allow_mixed_updated: int = 0
    actions_dest_repointed: int = 0
    assignments_created: int = 0
    assignments_updated: int = 0
    assignments_deactivated: int = 0


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def make_mix_datetime(transfer_date: date) -> datetime:
    naive = datetime.combine(transfer_date, time.min)
    return timezone.make_aware(naive, dt_timezone.utc)


def quantize_2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def get_history_user():
    return User.objects.filter(is_superuser=True).first() or User.objects.first()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill BatchMixEvent/BatchMixEventComponent from completed TransferAction history"
    )
    parser.add_argument(
        "--batch-number",
        help="Optional filter to actions where workflow batch matches this batch number",
    )
    parser.add_argument(
        "--since-date",
        help="Optional lower bound for action execution date (YYYY-MM-DD, inclusive)",
    )
    parser.add_argument(
        "--until-date",
        help="Optional upper bound for action execution date (YYYY-MM-DD, inclusive)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional cap for number of actions processed",
    )
    parser.add_argument(
        "--skip-assignment-rewrite",
        action="store_true",
        help=(
            "Only materialize mix lineage rows; do not create/refresh mixed destination "
            "assignment or deactivate contributing assignments."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate qualifying actions without writing changes",
    )
    return parser


def get_candidate_actions(args: argparse.Namespace):
    qs = (
        TransferAction.objects.select_related(
            "workflow__batch__species",
            "workflow__dest_lifecycle_stage",
            "source_assignment__batch",
            "source_assignment__lifecycle_stage",
            "dest_assignment__container",
            "dest_assignment__lifecycle_stage",
        )
        .filter(
            status="COMPLETED",
            dest_assignment__isnull=False,
        )
        .order_by("actual_execution_date", "planned_date", "id")
    )
    if args.batch_number:
        qs = qs.filter(workflow__batch__batch_number=args.batch_number)
    since = parse_date(args.since_date)
    if since:
        qs = qs.filter(
            Q(actual_execution_date__gte=since)
            | (Q(actual_execution_date__isnull=True) & Q(planned_date__gte=since))
        )
    until = parse_date(args.until_date)
    if until:
        qs = qs.filter(
            Q(actual_execution_date__lte=until)
            | (Q(actual_execution_date__isnull=True) & Q(planned_date__lte=until))
        )
    if args.limit is not None and args.limit > 0:
        qs = qs[: args.limit]
    return qs


def get_assignments_covering_date(
    *,
    container_id: int,
    transfer_date: date,
    source_assignment_id: int | None,
    mixed_batch_id: int | None,
) -> list[BatchContainerAssignment]:
    qs = (
        BatchContainerAssignment.objects.select_related("batch", "lifecycle_stage")
        .filter(
            container_id=container_id,
            assignment_date__lte=transfer_date,
        )
        .filter(
            Q(departure_date__isnull=True)
            | Q(departure_date__gt=transfer_date)
            | Q(departure_date=transfer_date, is_active=True)
        )
    )
    if source_assignment_id:
        qs = qs.exclude(pk=source_assignment_id)
    # Re-runs: avoid double-counting the mixed assignment produced by this action.
    if mixed_batch_id:
        qs = qs.exclude(batch_id=mixed_batch_id, assignment_date=transfer_date)
    return list(qs)


def build_contributions(
    *,
    overlapping_assignments: list[BatchContainerAssignment],
    source_assignment: BatchContainerAssignment,
    transferred_count: int,
    transferred_biomass_kg: Decimal,
):
    contributions: list[dict] = []
    total_population = 0
    total_biomass = Decimal("0.00")

    for assignment in overlapping_assignments:
        pop = int(assignment.population_count or 0)
        if pop <= 0:
            continue
        biomass = assignment.biomass_kg or Decimal("0.00")
        contributions.append(
            {
                "source_assignment": assignment,
                "source_batch": assignment.batch,
                "population_count": pop,
                "biomass_kg": biomass,
                "is_transferred_in": False,
            }
        )
        total_population += pop
        total_biomass += biomass

    if transferred_count > 0:
        contributions.append(
            {
                "source_assignment": source_assignment,
                "source_batch": source_assignment.batch,
                "population_count": transferred_count,
                "biomass_kg": transferred_biomass_kg,
                "is_transferred_in": True,
            }
        )
        total_population += transferred_count
        total_biomass += transferred_biomass_kg

    return contributions, total_population, total_biomass


def upsert_mix_lineage_for_action(
    *,
    action: TransferAction,
    transfer_date: date,
    history_user,
    history_reason: str,
    skip_assignment_rewrite: bool,
    stats: BackfillStats,
) -> None:
    workflow = action.workflow
    source_assignment = action.source_assignment
    dest_assignment = action.dest_assignment
    if source_assignment is None or dest_assignment is None:
        return

    mixed_batch_number = f"MIX-FTA-{action.id}"[:50]
    existing_mixed_batch = Batch.objects.filter(batch_number=mixed_batch_number).first()

    overlapping = get_assignments_covering_date(
        container_id=dest_assignment.container_id,
        transfer_date=transfer_date,
        source_assignment_id=source_assignment.id if source_assignment else None,
        mixed_batch_id=existing_mixed_batch.id if existing_mixed_batch else None,
    )

    # Must be true cross-batch co-location at destination.
    has_cross_batch = any(
        int(assignment.population_count or 0) > 0 and assignment.batch_id != workflow.batch_id
        for assignment in overlapping
    )
    if not has_cross_batch:
        stats.skipped_non_mix += 1
        return

    transferred_count = max(int(action.transferred_count or 0), 0)
    transferred_biomass = action.transferred_biomass_kg or Decimal("0.00")
    contributions, total_population, total_biomass = build_contributions(
        overlapping_assignments=overlapping,
        source_assignment=source_assignment,
        transferred_count=transferred_count,
        transferred_biomass_kg=transferred_biomass,
    )
    if total_population <= 0:
        stats.skipped_zero_total += 1
        return

    lifecycle_stage = (
        workflow.dest_lifecycle_stage
        or dest_assignment.lifecycle_stage
        or source_assignment.lifecycle_stage
    )
    if lifecycle_stage is None:
        return

    if total_biomass > 0:
        avg_weight_g = quantize_2((total_biomass * Decimal("1000")) / Decimal(total_population))
    else:
        avg_weight_g = source_assignment.avg_weight_g or dest_assignment.avg_weight_g or Decimal("0.00")

    mix_ts = make_mix_datetime(transfer_date)

    mixed_batch_created = False
    if existing_mixed_batch is None:
        mixed_batch = Batch(
            batch_number=mixed_batch_number,
            species=workflow.batch.species,
            lifecycle_stage=lifecycle_stage,
            status="ACTIVE",
            batch_type="MIXED",
            start_date=transfer_date,
            notes=(
                f"FishTalk migration mixed batch from action {action.id} "
                f"({workflow.workflow_number})"
            ),
        )
        save_with_history(mixed_batch, user=history_user, reason=history_reason)
        stats.mixed_batches_created += 1
        mixed_batch_created = True
    else:
        mixed_batch = existing_mixed_batch
        mixed_batch.species = workflow.batch.species
        mixed_batch.lifecycle_stage = lifecycle_stage
        mixed_batch.status = "ACTIVE"
        mixed_batch.batch_type = "MIXED"
        if not mixed_batch.start_date:
            mixed_batch.start_date = transfer_date
        if not mixed_batch.notes:
            mixed_batch.notes = (
                f"FishTalk migration mixed batch from action {action.id} "
                f"({workflow.workflow_number})"
            )
        save_with_history(mixed_batch, user=history_user, reason=history_reason)
        stats.mixed_batches_updated += 1

    mix_event = (
        BatchMixEvent.objects.filter(workflow_action=action)
        .order_by("-id")
        .first()
    )
    if mix_event is None:
        mix_event = BatchMixEvent(
            mixed_batch=mixed_batch,
            container=dest_assignment.container,
            workflow_action=action,
            mixed_at=mix_ts,
            notes=(
                f"Backfilled FishTalk container-scoped mixing from transfer action "
                f"{action.id} ({workflow.workflow_number})"
            ),
        )
        save_with_history(mix_event, user=history_user, reason=history_reason)
        stats.mix_events_created += 1
    else:
        mix_event.mixed_batch = mixed_batch
        mix_event.container = dest_assignment.container
        mix_event.mixed_at = mix_ts
        if not mix_event.notes:
            mix_event.notes = (
                f"Backfilled FishTalk container-scoped mixing from transfer action "
                f"{action.id} ({workflow.workflow_number})"
            )
        save_with_history(mix_event, user=history_user, reason=history_reason)
        stats.mix_events_updated += 1

    BatchMixEventComponent.objects.filter(mix_event=mix_event).delete()
    for contribution in contributions:
        pop = contribution["population_count"]
        percentage = quantize_2((Decimal(pop) / Decimal(total_population)) * Decimal("100"))
        BatchMixEventComponent.objects.create(
            mix_event=mix_event,
            source_assignment=contribution["source_assignment"],
            source_batch=contribution["source_batch"],
            population_count=pop,
            biomass_kg=contribution["biomass_kg"],
            percentage=percentage,
            is_transferred_in=contribution["is_transferred_in"],
        )
        stats.components_written += 1

    source_batch_aggregates: dict[int, dict] = defaultdict(
        lambda: {"source_batch": None, "population_count": 0, "biomass_kg": Decimal("0.00")}
    )
    for contribution in contributions:
        source_batch = contribution["source_batch"]
        aggregate = source_batch_aggregates[source_batch.id]
        aggregate["source_batch"] = source_batch
        aggregate["population_count"] += contribution["population_count"]
        aggregate["biomass_kg"] += contribution["biomass_kg"] or Decimal("0.00")

    BatchComposition.objects.filter(mixed_batch=mixed_batch).delete()
    for aggregate in source_batch_aggregates.values():
        percentage = quantize_2(
            (Decimal(aggregate["population_count"]) / Decimal(total_population)) * Decimal("100")
        )
        BatchComposition.objects.create(
            mixed_batch=mixed_batch,
            source_batch=aggregate["source_batch"],
            percentage=percentage,
            population_count=aggregate["population_count"],
            biomass_kg=aggregate["biomass_kg"],
        )
        stats.compositions_written += 1

    if not action.allow_mixed:
        action.allow_mixed = True
        save_with_history(action, user=history_user, reason=history_reason)
        stats.actions_allow_mixed_updated += 1

    if skip_assignment_rewrite:
        stats.qualified_mix_actions += 1
        return

    mixed_assignment = (
        BatchContainerAssignment.objects.filter(
            batch=mixed_batch,
            container=dest_assignment.container,
        )
        .order_by("assignment_date", "id")
        .first()
    )
    if mixed_assignment is None:
        mixed_assignment = BatchContainerAssignment(
            batch=mixed_batch,
            container=dest_assignment.container,
            lifecycle_stage=lifecycle_stage,
            population_count=total_population,
            avg_weight_g=avg_weight_g,
            biomass_kg=quantize_2(total_biomass),
            assignment_date=transfer_date,
            is_active=True,
            departure_date=None,
            notes=(
                f"Backfilled mixed assignment from transfer action {action.id} "
                f"({workflow.workflow_number})"
            ),
        )
        save_with_history(mixed_assignment, user=history_user, reason=history_reason)
        stats.assignments_created += 1
    else:
        mixed_assignment.lifecycle_stage = lifecycle_stage
        mixed_assignment.population_count = total_population
        mixed_assignment.avg_weight_g = avg_weight_g
        mixed_assignment.biomass_kg = quantize_2(total_biomass)
        mixed_assignment.assignment_date = transfer_date
        mixed_assignment.is_active = True
        mixed_assignment.departure_date = None
        if not mixed_assignment.notes:
            mixed_assignment.notes = (
                f"Backfilled mixed assignment from transfer action {action.id} "
                f"({workflow.workflow_number})"
            )
        save_with_history(mixed_assignment, user=history_user, reason=history_reason)
        stats.assignments_updated += 1

    for assignment in overlapping:
        if assignment.pk == mixed_assignment.pk:
            continue
        changed = False
        if assignment.is_active:
            assignment.is_active = False
            changed = True
        if assignment.departure_date is None or assignment.departure_date > transfer_date:
            assignment.departure_date = transfer_date
            changed = True
        if changed:
            save_with_history(assignment, user=history_user, reason=history_reason)
            stats.assignments_deactivated += 1

    if action.dest_assignment_id != mixed_assignment.id:
        action.dest_assignment = mixed_assignment
        save_with_history(action, user=history_user, reason=history_reason)
        stats.actions_dest_repointed += 1

    stats.qualified_mix_actions += 1

    # Ensure the very first creation path is counted as "created", not "updated".
    if mixed_batch_created and stats.mixed_batches_updated > 0:
        # no-op marker; keep branch explicit for readability
        pass


def main() -> int:
    args = build_parser().parse_args()

    history_user = get_history_user()
    if history_user is None:
        raise SystemExit("No users exist in AquaMind DB; cannot backfill mix lineage")
    history_reason = "FishTalk migration: backfill container-scoped mix lineage from transfer actions"

    stats = BackfillStats()
    actions = get_candidate_actions(args)

    for action in actions.iterator(chunk_size=500):
        stats.scanned_actions += 1
        transfer_date = action.actual_execution_date or action.planned_date
        if transfer_date is None:
            stats.skipped_missing_date += 1
            continue

        if args.dry_run:
            workflow = action.workflow
            mixed_batch_number = f"MIX-FTA-{action.id}"[:50]
            existing_mixed_batch = Batch.objects.filter(batch_number=mixed_batch_number).first()
            overlapping = get_assignments_covering_date(
                container_id=action.dest_assignment.container_id,
                transfer_date=transfer_date,
                source_assignment_id=action.source_assignment_id,
                mixed_batch_id=existing_mixed_batch.id if existing_mixed_batch else None,
            )
            has_cross_batch = any(
                int(assignment.population_count or 0) > 0 and assignment.batch_id != workflow.batch_id
                for assignment in overlapping
            )
            if has_cross_batch:
                stats.qualified_mix_actions += 1
            else:
                stats.skipped_non_mix += 1
            continue

        with transaction.atomic():
            upsert_mix_lineage_for_action(
                action=action,
                transfer_date=transfer_date,
                history_user=history_user,
                history_reason=history_reason,
                skip_assignment_rewrite=args.skip_assignment_rewrite,
                stats=stats,
            )

    print("Backfill transfer mix lineage summary")
    print("=" * 72)
    print(f"Scanned actions: {stats.scanned_actions}")
    print(f"Qualified mix actions: {stats.qualified_mix_actions}")
    print(f"Skipped (missing date): {stats.skipped_missing_date}")
    print(f"Skipped (non-mix co-location): {stats.skipped_non_mix}")
    print(f"Skipped (zero total population): {stats.skipped_zero_total}")
    print("-" * 72)
    print(f"Mixed batches created: {stats.mixed_batches_created}")
    print(f"Mixed batches updated: {stats.mixed_batches_updated}")
    print(f"Mix events created: {stats.mix_events_created}")
    print(f"Mix events updated: {stats.mix_events_updated}")
    print(f"Mix event components written: {stats.components_written}")
    print(f"Batch compositions written: {stats.compositions_written}")
    print(f"Actions updated allow_mixed=True: {stats.actions_allow_mixed_updated}")
    print(f"Actions repointed to mixed destination assignment: {stats.actions_dest_repointed}")
    print(f"Mixed assignments created: {stats.assignments_created}")
    print(f"Mixed assignments updated: {stats.assignments_updated}")
    print(f"Contributing assignments deactivated: {stats.assignments_deactivated}")
    print("=" * 72)
    if args.dry_run:
        print("Dry-run mode: no database changes were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
