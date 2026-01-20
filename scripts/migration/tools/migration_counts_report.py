#!/usr/bin/env python3
# flake8: noqa
"""Report core migration table counts and per-batch rollups."""

from __future__ import annotations

import argparse
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

from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchCreationWorkflow,
    CreationAction,
    BatchTransferWorkflow,
    TransferAction,
    MortalityEvent,
)
from apps.environmental.models import EnvironmentalReading
from apps.health.models import JournalEntry, Treatment, LiceCount
from apps.infrastructure.models import Container, Area, Hall, FreshwaterStation, Sensor
from apps.inventory.models import FeedingEvent, FeedPurchase, FeedContainerStock
from apps.migration_support.models import ExternalIdMap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report migration table counts and per-batch rollups")
    parser.add_argument(
        "--prefix",
        default="FT-",
        help="Batch number prefix to include (default: FT-)",
    )
    parser.add_argument(
        "--batch-number",
        action="append",
        default=[],
        help="Specific batch numbers to include (repeatable)",
    )
    return parser


def print_counts(section: str, rows: list[tuple[str, int]]) -> None:
    print(f"\n[{section}]")
    width = max(len(label) for label, _ in rows) if rows else 10
    for label, value in rows:
        print(f"{label.ljust(width)} : {value}")


def main() -> int:
    args = build_parser().parse_args()

    if args.batch_number:
        batch_qs = Batch.objects.filter(batch_number__in=args.batch_number)
    else:
        batch_qs = Batch.objects.filter(batch_number__startswith=args.prefix)

    batch_qs = batch_qs.order_by("batch_number")

    core_counts = [
        ("batch_batch", Batch.objects.count()),
        ("batch_batchcontainerassignment", BatchContainerAssignment.objects.count()),
        ("batch_creationworkflow", BatchCreationWorkflow.objects.count()),
        ("batch_creationaction", CreationAction.objects.count()),
        ("batch_batchtransferworkflow", BatchTransferWorkflow.objects.count()),
        ("batch_transferaction", TransferAction.objects.count()),
        ("batch_mortalityevent", MortalityEvent.objects.count()),
        ("inventory_feedingevent", FeedingEvent.objects.count()),
        ("health_treatment", Treatment.objects.count()),
        ("health_licecount", LiceCount.objects.count()),
        ("health_journalentry", JournalEntry.objects.count()),
        ("environmental_environmentalreading", EnvironmentalReading.objects.count()),
        ("infrastructure_sensor", Sensor.objects.count()),
        ("infrastructure_container", Container.objects.count()),
        ("infrastructure_area", Area.objects.count()),
        ("infrastructure_hall", Hall.objects.count()),
        ("infrastructure_freshwaterstation", FreshwaterStation.objects.count()),
        ("inventory_feedpurchase", FeedPurchase.objects.count()),
        ("inventory_feedcontainerstock", FeedContainerStock.objects.count()),
        ("migration_support_externalidmap", ExternalIdMap.objects.count()),
    ]

    print_counts("Core table counts", core_counts)

    print("\n[Per-batch counts]")
    if not batch_qs.exists():
        print("No batches matched the filter.")
        return 0

    header = (
        "batch_number",
        "assignments",
        "creation_workflows",
        "creation_actions",
        "workflows",
        "actions",
        "feeding",
        "feed_purchases",
        "feed_stock",
        "mortality",
        "treatments",
        "lice",
        "journal",
        "environmental",
    )
    print(" | ".join(header))
    print(" | ".join(["-" * len(col) for col in header]))

    for batch in batch_qs:
        batch_map = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="PopulationComponent",
            target_object_id=batch.pk,
        ).first()
        component_key = batch_map.source_identifier if batch_map else None
        purchase_ids = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="FeedReceptionBatches",
            metadata__component_key=component_key,
        ).values_list("target_object_id", flat=True)
        stock_ids = ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="FeedContainerStock",
            metadata__component_key=component_key,
        ).values_list("target_object_id", flat=True)

        row = (
            batch.batch_number,
            BatchContainerAssignment.objects.filter(batch=batch).count(),
            BatchCreationWorkflow.objects.filter(batch=batch).count(),
            CreationAction.objects.filter(workflow__batch=batch).count(),
            BatchTransferWorkflow.objects.filter(batch=batch).count(),
            TransferAction.objects.filter(workflow__batch=batch).count(),
            FeedingEvent.objects.filter(batch=batch).count(),
            FeedPurchase.objects.filter(pk__in=purchase_ids).count(),
            FeedContainerStock.objects.filter(pk__in=stock_ids).count(),
            MortalityEvent.objects.filter(batch=batch).count(),
            Treatment.objects.filter(batch=batch).count(),
            LiceCount.objects.filter(batch=batch).count(),
            JournalEntry.objects.filter(batch=batch).count(),
            EnvironmentalReading.objects.filter(batch=batch).count(),
        )
        print(" | ".join(str(value) for value in row))

    missing_creation = list(
        batch_qs.filter(creation_workflows__isnull=True)
        .values_list("batch_number", flat=True)
        .distinct()
    )
    if missing_creation:
        print("\n[Missing creation workflows]")
        for batch_number in missing_creation:
            print(f"- {batch_number}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
