#!/usr/bin/env python3
# flake8: noqa
"""Backfill zeroed egg-stage assignment counts from completed creation actions.

This repairs cohorts where:
- creation workflows/actions were migrated with positive egg counts, but
- the linked BatchContainerAssignment rows remained at population_count = 0.

The repair is deterministic and limited to destination assignments referenced
by completed CreationAction rows with positive egg_count_actual.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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
from django.db.models import Sum

from apps.batch.models import Batch
from apps.batch.models.workflow_creation_action import CreationAction
from apps.migration_support.models import ExternalIdMap
from scripts.migration.history import save_with_history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repair zeroed creation destination assignments from completed creation actions"
    )
    parser.add_argument(
        "--batch-id",
        action="append",
        type=int,
        default=[],
        help="Restrict repair to one or more batch IDs",
    )
    parser.add_argument(
        "--batch-number-contains",
        action="append",
        default=[],
        help="Restrict repair to batch numbers containing this substring (repeatable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report affected assignments without writing changes",
    )
    return parser


def iter_target_batches(args: argparse.Namespace):
    qs = Batch.objects.all().order_by("id")
    if args.batch_id:
        qs = qs.filter(id__in=args.batch_id)
    for token in args.batch_number_contains:
        qs = qs.filter(batch_number__icontains=token)
    return qs


def assignment_source_container_key(
    assignment_id: int,
    assignment_maps: dict[int, ExternalIdMap],
    fallback_name: str,
) -> str:
    ext_map = assignment_maps.get(assignment_id)
    metadata = dict(ext_map.metadata or {}) if ext_map else {}
    source_container_id = str(metadata.get("container_id") or "").strip()
    if source_container_id:
        return f"source:{source_container_id}"
    return f"name:{fallback_name.strip().upper()}"


def main() -> int:
    args = build_parser().parse_args()
    User = get_user_model()
    history_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    history_reason = "Repair creation assignment counts from creation actions"

    batch_summaries: list[dict] = []
    total_updates = 0

    for batch in iter_target_batches(args):
        creation_actions = list(
            CreationAction.objects.filter(
                workflow__batch=batch,
                egg_count_actual__gt=0,
                status="COMPLETED",
            ).select_related("dest_assignment", "dest_assignment__container")
        )
        if not creation_actions:
            continue

        egg_assignments = list(
            batch.batch_assignments.filter(lifecycle_stage__name="Egg&Alevin").select_related("container")
        )
        assignment_ids = [assignment.id for assignment in egg_assignments]
        assignment_maps = {
            ext_map.target_object_id: ext_map
            for ext_map in ExternalIdMap.objects.filter(
                target_app_label="batch",
                target_model="batchcontainerassignment",
                target_object_id__in=assignment_ids,
            )
        }
        positive_container_keys: set[str] = set()
        for assignment in egg_assignments:
            if int(assignment.population_count or 0) <= 0:
                continue
            positive_container_keys.add(
                assignment_source_container_key(
                    assignment.id,
                    assignment_maps,
                    assignment.container.name,
                )
            )

        affected = []
        for action in creation_actions:
            assignment = action.dest_assignment
            if assignment is None:
                continue
            egg_count = int(action.egg_count_actual or 0)
            if egg_count <= 0:
                continue
            if int(assignment.population_count or 0) > 0:
                continue
            source_container_key = assignment_source_container_key(
                assignment.id,
                assignment_maps,
                assignment.container.name,
            )
            if source_container_key in positive_container_keys:
                continue
            affected.append((action, assignment, egg_count))

        if not affected:
            continue

        egg_total_before = int(
            batch.batch_assignments.filter(lifecycle_stage__name="Egg&Alevin").aggregate(
                total=Sum("population_count")
            )["total"]
            or 0
        )

        if not args.dry_run:
            with transaction.atomic():
                for _, assignment, egg_count in affected:
                    assignment.population_count = egg_count
                    assignment.avg_weight_g = None
                    assignment.biomass_kg = 0
                    save_with_history(assignment, user=history_user, reason=history_reason)

                    ext_map = ExternalIdMap.objects.filter(
                        target_app_label="batch",
                        target_model="batchcontainerassignment",
                        target_object_id=assignment.id,
                    ).first()
                    if ext_map:
                        metadata = dict(ext_map.metadata or {})
                        metadata["baseline_population_count"] = egg_count
                        ext_map.metadata = metadata
                        ext_map.save(update_fields=["metadata"])

        egg_total_after = egg_total_before + sum(egg_count for _, _, egg_count in affected)
        if not args.dry_run:
            egg_total_after = int(
                batch.batch_assignments.filter(lifecycle_stage__name="Egg&Alevin").aggregate(
                    total=Sum("population_count")
                )["total"]
                or 0
            )
        batch_summaries.append(
            {
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "affected_assignments": len(affected),
                "egg_total_before": egg_total_before,
                "creation_total": int(
                    CreationAction.objects.filter(workflow__batch=batch).aggregate(
                        total=Sum("egg_count_actual")
                    )["total"]
                    or 0
                ),
                "egg_total_after": egg_total_after,
                "sample_containers": [
                    assignment.container.name
                    for _, assignment, _ in affected[:10]
                ],
            }
        )
        total_updates += len(affected)

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "batches_touched": len(batch_summaries),
                "assignments_updated": total_updates,
                "batches": batch_summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
