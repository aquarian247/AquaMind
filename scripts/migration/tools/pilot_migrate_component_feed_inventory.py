#!/usr/bin/env python3
# flake8: noqa
"""Pilot migrate FishTalk feed purchases + container stock for one component.

Source (FishTalk):
  - FeedReceptions (header)
  - FeedReceptionBatches (lines)
  - FeedBatch (links lines to feed type + feed store)
  - FeedStore (feed storage locations)
  - FeedStoreUnitAssignment (links feed store to containers)
  - FeedTypes (feed type names)

Target (AquaMind):
  - inventory.FeedPurchase
  - infrastructure.FeedContainer
  - inventory.FeedContainerStock

Notes:
  - ReceptionAmount assumed to be grams; converted to kg.
  - FeedContainer is mapped per FeedStore, attached to hall/area via the
    first mapped container from FeedStoreUnitAssignment.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
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

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.inventory.models import Feed, FeedPurchase, FeedContainerStock
from apps.infrastructure.models import FeedContainer, Container
from apps.migration_support.models import ExternalIdMap
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
from scripts.migration.history import save_with_history, get_or_create_with_history


User = get_user_model()

REPORT_DIR_DEFAULT = PROJECT_ROOT / "scripts" / "migration" / "output" / "population_stitching"


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, dt_timezone.utc)


def to_decimal(value: object, *, places: str) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal(places))
    except Exception:
        return None


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk", source_model=source_model, source_identifier=str(source_identifier)
    ).first()


def normalize_container_type(name: str) -> str:
    upper = (name or "").upper()
    if "SILO" in upper:
        return "SILO"
    if "BARGE" in upper:
        return "BARGE"
    if "TANK" in upper:
        return "TANK"
    return "OTHER"


@dataclass(frozen=True)
class ComponentMember:
    population_id: str
    container_id: str
    start_time: datetime
    end_time: datetime | None


def load_members_from_report(report_dir: Path, *, component_id: int | None, component_key: str | None) -> list[ComponentMember]:
    import csv

    path = report_dir / "population_members.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing report file: {path}")

    members: list[ComponentMember] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if component_id is not None and row.get("component_id") != str(component_id):
                continue
            if component_key is not None and row.get("component_key") != component_key:
                continue
            start = parse_dt(row.get("start_time", ""))
            if start is None:
                continue
            end = parse_dt(row.get("end_time", ""))
            members.append(
                ComponentMember(
                    population_id=row.get("population_id", ""),
                    container_id=row.get("container_id", ""),
                    start_time=start,
                    end_time=end,
                )
            )

    members.sort(key=lambda m: m.start_time)
    return members


def resolve_component_key(report_dir: Path, *, component_id: int | None, component_key: str | None) -> str:
    if component_key:
        return component_key
    if component_id is None:
        raise ValueError("Provide --component-id or --component-key")

    import csv

    path = report_dir / "population_members.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("component_id") == str(component_id) and row.get("component_key"):
                return row["component_key"]

    raise ValueError("Unable to resolve component_key from report")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pilot migrate feed purchases/stock for a stitched FishTalk component")
    parser.add_argument("--component-id", type=int, help="Component id from components.csv")
    parser.add_argument("--component-key", help="Stable component_key from components.csv")
    parser.add_argument("--report-dir", default=str(REPORT_DIR_DEFAULT), help="Directory containing population_members.csv")
    parser.add_argument("--sql-profile", default="fishtalk_readonly", help="FishTalk SQL Server profile")
    parser.add_argument(
        "--include-all-receptions",
        action="store_true",
        help="Ignore component time window and pull all receptions for matching feed stores",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_dir = Path(args.report_dir)
    component_key = resolve_component_key(report_dir, component_id=args.component_id, component_key=args.component_key)
    members = load_members_from_report(report_dir, component_id=args.component_id, component_key=component_key)
    if not members:
        raise SystemExit("No members found for the selected component")

    batch_map = get_external_map("PopulationComponent", component_key)
    if not batch_map:
        raise SystemExit(
            f"Missing ExternalIdMap for PopulationComponent {component_key}. "
            "Run scripts/migration/tools/pilot_migrate_component.py first."
        )

    from apps.batch.models import Batch

    batch = Batch.objects.get(pk=batch_map.target_object_id)

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in AquaMind DB; cannot set history user")

    window_start = min(m.start_time for m in members)
    window_end = max((m.end_time or datetime.now()) for m in members)
    container_ids = sorted({m.container_id for m in members if m.container_id})
    if not container_ids:
        raise SystemExit("No container ids found in report")

    in_clause = ",".join(f"'{cid}'" for cid in container_ids)
    start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = window_end.strftime("%Y-%m-%d %H:%M:%S")

    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    reception_filter = ""
    if not args.include_all_receptions:
        reception_filter = (
            f"AND fr.ReceptionTime >= '{start_str}' AND fr.ReceptionTime <= '{end_str}' "
        )

    rows = extractor._run_sqlcmd(
        query=(
            "SELECT CONVERT(varchar(36), frb.FeedReceptionID) AS FeedReceptionID, "
            "CONVERT(varchar(36), frb.FeedBatchID) AS FeedBatchID, "
            "ISNULL(CONVERT(varchar(32), frb.PricePerKg), '') AS PricePerKg, "
            "ISNULL(CONVERT(varchar(32), frb.ReceptionAmount), '') AS ReceptionAmount, "
            "CONVERT(varchar(19), frb.ProductionDate, 120) AS ProductionDate, "
            "CONVERT(varchar(19), frb.OutOfDate, 120) AS OutOfDate, "
            "ISNULL(frb.ReceiptNumber, '') AS ReceiptNumber, "
            "ISNULL(frb.SuppliersBatchNumber, '') AS SuppliersBatchNumber, "
            "CONVERT(varchar(32), frb.FeedReceptionLineNumber) AS FeedReceptionLineNumber, "
            "CONVERT(varchar(19), fr.ReceptionTime, 120) AS ReceptionTime, "
            "ISNULL(fr.OrderNumber, '') AS OrderNumber, "
            "ISNULL(fr.OurOrderNo, '') AS OurOrderNo, "
            "ISNULL(fr.OurReference, '') AS OurReference, "
            "ISNULL(fr.GTIN, '') AS GTIN, "
            "CONVERT(varchar(36), fr.SupplierID) AS SupplierID, "
            "ISNULL(fr.Comment, '') AS ReceptionComment, "
            "CONVERT(varchar(36), fb.FeedStoreID) AS FeedStoreID, "
            "CONVERT(varchar(32), fb.FeedTypeID) AS FeedTypeID, "
            "ISNULL(fb.BatchNumber, '') AS FeedBatchNumber, "
            "CONVERT(varchar(19), fb.StartTime, 120) AS FeedBatchStartTime, "
            "CONVERT(varchar(19), fb.EndTime, 120) AS FeedBatchEndTime, "
            "ISNULL(fs.Name, '') AS FeedStoreName, "
            "ISNULL(CONVERT(varchar(32), fs.Capacity), '') AS FeedStoreCapacity, "
            "CONVERT(varchar(32), fs.FeedStoreTypeID) AS FeedStoreTypeID, "
            "CONVERT(varchar(36), fsa.ContainerID) AS ContainerID, "
            "ISNULL(ft.Name, '') AS FeedTypeName "
            "FROM dbo.FeedStoreUnitAssignment fsa "
            "JOIN dbo.FeedStore fs ON fs.FeedStoreID = fsa.FeedStoreID "
            "JOIN dbo.FeedBatch fb ON fb.FeedStoreID = fs.FeedStoreID "
            "JOIN dbo.FeedReceptionBatches frb ON frb.FeedBatchID = fb.FeedBatchID "
            "JOIN dbo.FeedReceptions fr ON fr.FeedReceptionID = frb.FeedReceptionID "
            "LEFT JOIN dbo.FeedTypes ft ON ft.FeedTypeID = fb.FeedTypeID "
            f"WHERE fsa.ContainerID IN ({in_clause}) "
            f"AND fsa.StartDate <= '{end_str}' AND (fsa.EndDate IS NULL OR fsa.EndDate >= '{start_str}') "
            f"{reception_filter}"
            "ORDER BY fr.ReceptionTime ASC"
        ),
        headers=[
            "FeedReceptionID",
            "FeedBatchID",
            "PricePerKg",
            "ReceptionAmount",
            "ProductionDate",
            "OutOfDate",
            "ReceiptNumber",
            "SuppliersBatchNumber",
            "FeedReceptionLineNumber",
            "ReceptionTime",
            "OrderNumber",
            "OurOrderNo",
            "OurReference",
            "GTIN",
            "SupplierID",
            "ReceptionComment",
            "FeedStoreID",
            "FeedTypeID",
            "FeedBatchNumber",
            "FeedBatchStartTime",
            "FeedBatchEndTime",
            "FeedStoreName",
            "FeedStoreCapacity",
            "FeedStoreTypeID",
            "ContainerID",
            "FeedTypeName",
        ],
    )

    if args.dry_run:
        print(f"[dry-run] Batch={batch.batch_number} FeedReceptionBatches={len(rows)}")
        return 0

    created_purchase = 0
    updated_purchase = 0
    created_stock = 0
    updated_stock = 0
    skipped = 0

    history_reason = f"FishTalk migration: feed inventory for component {component_key}"

    with transaction.atomic():
        container_cache: dict[str, Container] = {}
        feed_container_cache: dict[str, FeedContainer] = {}

        for row in rows:
            feed_reception_id = (row.get("FeedReceptionID") or "").strip()
            feed_batch_id = (row.get("FeedBatchID") or "").strip()
            line_number = (row.get("FeedReceptionLineNumber") or "").strip()
            feed_store_id = (row.get("FeedStoreID") or "").strip()
            container_id = (row.get("ContainerID") or "").strip()
            if not feed_reception_id or not feed_batch_id or not feed_store_id:
                skipped += 1
                continue

            container = None
            if container_id:
                if container_id in container_cache:
                    container = container_cache[container_id]
                else:
                    mapping = get_external_map("Containers", container_id)
                    if mapping:
                        container = Container.objects.get(pk=mapping.target_object_id)
                        container_cache[container_id] = container

            if not container:
                skipped += 1
                continue

            if feed_store_id in feed_container_cache:
                feed_container = feed_container_cache[feed_store_id]
            else:
                mapped = get_external_map("FeedStore", feed_store_id)
                if mapped:
                    feed_container = FeedContainer.objects.get(pk=mapped.target_object_id)
                else:
                    capacity = to_decimal(row.get("FeedStoreCapacity"), places="0.01") or Decimal("0.00")
                    name = (row.get("FeedStoreName") or f"FeedStore {feed_store_id[:8]}")[:100]
                    container_type = normalize_container_type(name)
                    hall = container.hall
                    area = container.area
                    if not hall and not area:
                        skipped += 1
                        continue
                    feed_container = FeedContainer(
                        name=name,
                        container_type=container_type,
                        hall=hall,
                        area=area,
                        capacity_kg=capacity,
                        active=True,
                    )
                    save_with_history(feed_container, user=user, reason=history_reason)
                    ExternalIdMap.objects.update_or_create(
                        source_system="FishTalk",
                        source_model="FeedStore",
                        source_identifier=feed_store_id,
                        defaults={
                            "target_app_label": feed_container._meta.app_label,
                            "target_model": feed_container._meta.model_name,
                            "target_object_id": feed_container.pk,
                            "metadata": {
                                "feed_store_name": row.get("FeedStoreName"),
                                "feed_store_type_id": row.get("FeedStoreTypeID"),
                                "container_id": container_id,
                            },
                        },
                    )
                feed_container_cache[feed_store_id] = feed_container

            feed_type_id = (row.get("FeedTypeID") or "").strip()
            feed_type_name = (row.get("FeedTypeName") or "").strip()
            feed_batch_number = (row.get("FeedBatchNumber") or "").strip()
            feed_display = feed_type_name or (f"FishTalk FeedType {feed_type_id}" if feed_type_id else "FishTalk Feed")
            if feed_batch_number:
                feed_display = f"{feed_display} ({feed_batch_number})"
            feed_name = f"FT-{feed_display}"[:100]

            feed, _ = Feed.objects.get_or_create(
                name=feed_name,
                defaults={
                    "brand": "FishTalk Import",
                    "size_category": "MEDIUM",
                    "protein_percentage": Decimal("45.0"),
                    "fat_percentage": Decimal("20.0"),
                    "carbohydrate_percentage": Decimal("15.0"),
                    "description": "Auto-created for FishTalk feed purchases",
                    "is_active": True,
                },
            )

            reception_time = parse_dt(row.get("ReceptionTime") or "")
            if not reception_time:
                skipped += 1
                continue
            reception_time = ensure_aware(reception_time)

            amount_g = to_decimal(row.get("ReceptionAmount"), places="0.0001")
            if amount_g is None or amount_g <= 0:
                skipped += 1
                continue
            quantity_kg = (amount_g / Decimal("1000")).quantize(Decimal("0.0001"))

            price_per_kg = to_decimal(row.get("PricePerKg"), places="0.0001") or Decimal("0.00")
            supplier_id = (row.get("SupplierID") or "").strip()
            supplier = supplier_id or "FishTalk"
            batch_number = (row.get("SuppliersBatchNumber") or "").strip() or (row.get("ReceiptNumber") or "").strip()
            if not batch_number:
                batch_number = feed_batch_number or feed_batch_id

            expiry_dt = parse_dt(row.get("OutOfDate") or "")
            expiry_date = expiry_dt.date() if expiry_dt else None

            notes = (
                f"FishTalk FeedReception={feed_reception_id}; FeedBatch={feed_batch_id}; "
                f"GTIN={row.get('GTIN') or 'n/a'}; Order={row.get('OrderNumber') or 'n/a'}; "
                f"OurOrderNo={row.get('OurOrderNo') or 'n/a'}; OurRef={row.get('OurReference') or 'n/a'}; "
                f"Comment={row.get('ReceptionComment') or ''}"
            ).strip()

            source_identifier = f"{feed_reception_id}:{feed_batch_id}:{line_number or '0'}"
            purchase_map = get_external_map("FeedReceptionBatches", source_identifier)
            if purchase_map:
                purchase = FeedPurchase.objects.get(pk=purchase_map.target_object_id)
                purchase.feed = feed
                purchase.purchase_date = reception_time.date()
                purchase.quantity_kg = quantity_kg
                purchase.cost_per_kg = price_per_kg
                purchase.supplier = supplier
                purchase.batch_number = batch_number
                purchase.expiry_date = expiry_date
                purchase.notes = notes
                save_with_history(purchase, user=user, reason=history_reason)
                updated_purchase += 1
            else:
                purchase = FeedPurchase(
                    feed=feed,
                    purchase_date=reception_time.date(),
                    quantity_kg=quantity_kg,
                    cost_per_kg=price_per_kg,
                    supplier=supplier,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    notes=notes,
                )
                save_with_history(purchase, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="FeedReceptionBatches",
                    source_identifier=source_identifier,
                    defaults={
                        "target_app_label": purchase._meta.app_label,
                        "target_model": purchase._meta.model_name,
                        "target_object_id": purchase.pk,
                        "metadata": {
                            "component_key": component_key,
                            "feed_reception_id": feed_reception_id,
                            "feed_batch_id": feed_batch_id,
                            "feed_batch_number": feed_batch_number,
                            "feed_type_id": feed_type_id,
                            "feed_type_name": feed_type_name,
                            "reception_time": row.get("ReceptionTime"),
                            "amount_g": str(amount_g),
                            "amount_kg": str(quantity_kg),
                        },
                    },
                )
                created_purchase += 1

            stock_map = get_external_map("FeedContainerStock", source_identifier)
            if stock_map:
                stock = FeedContainerStock.objects.get(pk=stock_map.target_object_id)
                stock.feed_container = feed_container
                stock.feed_purchase = purchase
                stock.quantity_kg = quantity_kg
                stock.entry_date = reception_time
                save_with_history(stock, user=user, reason=history_reason)
                updated_stock += 1
            else:
                stock = FeedContainerStock(
                    feed_container=feed_container,
                    feed_purchase=purchase,
                    quantity_kg=quantity_kg,
                    entry_date=reception_time,
                )
                save_with_history(stock, user=user, reason=history_reason)
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="FeedContainerStock",
                    source_identifier=source_identifier,
                    defaults={
                        "target_app_label": stock._meta.app_label,
                        "target_model": stock._meta.model_name,
                        "target_object_id": stock.pk,
                        "metadata": {
                            "component_key": component_key,
                            "feed_store_id": feed_store_id,
                            "container_id": container_id,
                        },
                    },
                )
                created_stock += 1

    print(
        f"Migrated feed inventory for component_key={component_key} into batch={batch.batch_number} "
        f"(purchases: created={created_purchase}, updated={updated_purchase}; "
        f"stock: created={created_stock}, updated={updated_stock}; skipped={skipped}; rows={len(rows)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
