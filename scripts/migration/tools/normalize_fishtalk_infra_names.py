#!/usr/bin/env python3
"""Normalize FishTalk-migrated infrastructure names by removing FT/FW/Sea suffixes.

This is a one-off cleanup to improve GUI verification after pilot migrations.
It only updates names that start with "FT " and/or end with " FW"/" Sea".
"""

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

from django.db import transaction
from apps.infrastructure.models import Area, FreshwaterStation, Hall, Container


def normalize_name(name: str) -> str:
    raw = name.strip()
    if raw.startswith("FT "):
        raw = raw[3:].strip()
    if raw.endswith(" FW"):
        raw = raw[:-3].strip()
    if raw.endswith(" Sea"):
        raw = raw[:-4].strip()
    return raw


def maybe_rename(model, *, dry_run: bool) -> tuple[int, int]:
    renamed = 0
    skipped = 0
    for obj in model.objects.all():
        new_name = normalize_name(obj.name)
        if new_name == obj.name or not new_name:
            continue
        if model.objects.filter(name=new_name).exclude(pk=obj.pk).exists():
            skipped += 1
            continue
        if dry_run:
            renamed += 1
            continue
        obj.name = new_name
        obj.save(update_fields=["name"])
        renamed += 1
    return renamed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize FishTalk infra names (remove FT/FW/Sea tokens)")
    parser.add_argument("--dry-run", action="store_true", help="Show counts without writing")
    args = parser.parse_args()

    print("\nNormalizing FishTalk infra names...")
    if args.dry_run:
        print("[DRY RUN]")

    with transaction.atomic():
        station_renamed, station_skipped = maybe_rename(FreshwaterStation, dry_run=args.dry_run)
        area_renamed, area_skipped = maybe_rename(Area, dry_run=args.dry_run)
        hall_renamed, hall_skipped = maybe_rename(Hall, dry_run=args.dry_run)
        container_renamed, container_skipped = maybe_rename(Container, dry_run=args.dry_run)

    print("\nSummary")
    print(f"  FreshwaterStation: {station_renamed} renamed, {station_skipped} skipped (name collision)")
    print(f"  Area: {area_renamed} renamed, {area_skipped} skipped (name collision)")
    print(f"  Hall: {hall_renamed} renamed, {hall_skipped} skipped (name collision)")
    print(f"  Container: {container_renamed} renamed, {container_skipped} skipped (name collision)")

    if args.dry_run:
        print("\n[DRY RUN] No changes made")
    else:
        print("\n[SUCCESS] Names normalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
