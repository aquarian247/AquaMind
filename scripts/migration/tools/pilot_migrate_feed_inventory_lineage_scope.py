#!/usr/bin/env python3
# flake8: noqa
"""Migrate feed inventory from a lineage-scoped extract package.

This script consumes the prebuilt lineage extract package (scope populations,
expanded descendant edges, feeding rows, feed-batch lineage, and dependent feed
entities) and writes feed/infrastructure inventory models idempotently.

Contract:
- Start from selected batch keys (scope subset).
- Expand populations through descendant edges.
- Collect consumed feed batches from feeding rows for expanded populations.
- Add upstream feed batches from FeedTransfer lineage.
- Hydrate purchases/stocks/stores/types/suppliers only for selected feed batches.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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

from apps.infrastructure.models import Area, Container, FeedContainer, FreshwaterStation, Geography, Hall
from apps.inventory.models import Feed, FeedContainerStock, FeedPurchase
from apps.migration_support.models import ExternalIdMap
from scripts.migration.history import save_with_history


User = get_user_model()


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


def normalize_container_type(name: str) -> str:
    upper = (name or "").upper()
    if "SILO" in upper:
        return "SILO"
    if "BARGE" in upper:
        return "BARGE"
    if "TANK" in upper:
        return "TANK"
    return "OTHER"


def infer_geography_name_from_org_unit(org_unit_name: str) -> str:
    upper = (org_unit_name or "").strip().upper()
    if upper.startswith(("FW", "BRS")):
        return "Scotland"
    if upper.startswith(("S", "L", "H", "A")):
        return "Faroe Islands"
    return ""


def infer_station_type_from_org_unit(org_unit_name: str) -> str:
    upper = (org_unit_name or "").strip().upper()
    if upper.startswith("BRS"):
        return "BROODSTOCK"
    return "FRESHWATER"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_required_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required lineage file: {path}")
    return read_csv_rows(path)


def load_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv_rows(path)


def first_present_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in fieldnames:
            return candidate
    return None


def load_batch_keys(path: Path) -> list[str]:
    rows = read_csv_rows(path)
    if not rows:
        return []
    fieldnames = list(rows[0].keys())
    key_col = first_present_column(fieldnames, ["batch_key", "BatchKey", "source_batch_key"])
    if not key_col:
        raise ValueError(f"Unable to resolve batch key column in {path}")
    ordered: list[str] = []
    seen: set[str] = set()
    for row in rows:
        key = (row.get(key_col) or "").strip()
        if not key or key in seen:
            continue
        ordered.append(key)
        seen.add(key)
    return ordered


def get_external_map(source_model: str, source_identifier: str) -> ExternalIdMap | None:
    return ExternalIdMap.objects.filter(
        source_system="FishTalk",
        source_model=source_model,
        source_identifier=str(source_identifier),
    ).first()


def choose_batch_keys_file(args: argparse.Namespace, lineage_dir: Path) -> Path:
    if args.scope_batch_keys_file:
        return Path(args.scope_batch_keys_file)
    replay_keys = lineage_dir / "scope_batch_keys_for_replay.csv"
    if replay_keys.exists():
        return replay_keys
    return lineage_dir / "scope_batch_keys.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate feed inventory from lineage extract package for selected scope keys"
    )
    parser.add_argument(
        "--lineage-extract-dir",
        required=True,
        help="Path to lineage extract directory (fw_scope60_feed_infra_extract_descendants_*)",
    )
    parser.add_argument(
        "--scope-batch-keys-file",
        help="Optional CSV containing scope batch keys (batch_key/BatchKey/source_batch_key)",
    )
    parser.add_argument(
        "--cutoff-end-date",
        help="Optional cutoff date (YYYY-MM-DD) applied to feeding/reception timestamps",
    )
    parser.add_argument(
        "--org-units-csv",
        default=str(PROJECT_ROOT / "scripts/migration/data/extract/org_units.csv"),
        help="Optional org_units.csv path for OrgUnit fallback anchoring",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute plan and counts without writing")
    parser.add_argument("--summary-json", help="Optional output path for JSON summary")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    lineage_dir = Path(args.lineage_extract_dir)
    if not lineage_dir.exists():
        raise SystemExit(f"Lineage extract directory not found: {lineage_dir}")

    batch_keys_file = choose_batch_keys_file(args, lineage_dir)
    if not batch_keys_file.exists():
        raise SystemExit(f"Scope batch keys file not found: {batch_keys_file}")

    selected_batch_keys = set(load_batch_keys(batch_keys_file))
    if not selected_batch_keys:
        raise SystemExit("No batch keys resolved for lineage scope")

    cutoff_str = None
    cutoff_dt = None
    if args.cutoff_end_date:
        cutoff_dt = datetime.strptime(args.cutoff_end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Load lineage package files.
    scope_seed_rows = load_required_csv(lineage_dir / "scope_seed_populations.csv")
    edge_rows = load_required_csv(lineage_dir / "scope_descendant_population_edges.csv")
    expanded_rows = load_required_csv(lineage_dir / "scope_expanded_populations.csv")
    feeding_rows_all = load_required_csv(lineage_dir / "feeding_events_scope_expanded.csv")

    feed_batch_rows = load_required_csv(lineage_dir / "feed_batches_scope_lineage.csv")
    feed_lineage_rows = load_required_csv(lineage_dir / "feed_batch_lineage_transfers_upstream.csv")
    reception_line_rows = load_required_csv(lineage_dir / "feed_reception_batches_scope_lineage.csv")
    reception_rows = load_required_csv(lineage_dir / "feed_receptions_scope_lineage.csv")
    store_rows = load_required_csv(lineage_dir / "feed_stores_scope_lineage.csv")
    store_assign_rows = load_optional_csv(lineage_dir / "feed_store_unit_assignments_scope_lineage.csv")
    ext_store_assign_rows = load_optional_csv(lineage_dir / "ext_feed_store_assignments_scope_lineage.csv")
    ext_feed_type_rows = load_optional_csv(lineage_dir / "ext_feed_types_scope_lineage.csv")
    feed_type_rows = load_optional_csv(lineage_dir / "feed_types_scope_lineage.csv")
    supplier_rows = load_optional_csv(lineage_dir / "ext_feed_suppliers_scope_lineage.csv")

    # Resolve seed populations for selected keys.
    seed_populations: set[str] = set()
    for row in scope_seed_rows:
        batch_key = (row.get("BatchKey") or "").strip()
        if batch_key not in selected_batch_keys:
            continue
        pop_id = (row.get("PopulationID") or "").strip()
        if pop_id:
            seed_populations.add(pop_id)
    if not seed_populations:
        raise SystemExit("Selected batch keys did not resolve to seed populations in lineage package")

    # Expand descendant populations.
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in edge_rows:
        src = (row.get("SourcePopBefore") or "").strip()
        if not src:
            continue
        for field in ("SourcePopAfter", "DestPopAfter"):
            dst = (row.get(field) or "").strip()
            if dst:
                adjacency[src].add(dst)

    expanded_populations: set[str] = set(seed_populations)
    queue: deque[str] = deque(seed_populations)
    while queue:
        src = queue.popleft()
        for dst in adjacency.get(src, set()):
            if dst in expanded_populations:
                continue
            expanded_populations.add(dst)
            queue.append(dst)

    # Lookup maps.
    feed_batches_by_id: dict[str, dict[str, str]] = {}
    for row in feed_batch_rows:
        feed_batch_id = (row.get("FeedBatchID") or "").strip()
        if feed_batch_id:
            feed_batches_by_id[feed_batch_id] = row

    receptions_by_id: dict[str, dict[str, str]] = {}
    for row in reception_rows:
        rid = (row.get("FeedReceptionID") or "").strip()
        if rid:
            receptions_by_id[rid] = row

    stores_by_id: dict[str, dict[str, str]] = {}
    for row in store_rows:
        sid = (row.get("FeedStoreID") or "").strip()
        if sid:
            stores_by_id[sid] = row

    feed_types_by_id: dict[str, dict[str, str]] = {}
    for row in feed_type_rows:
        fid = (row.get("FeedTypeID") or "").strip()
        if fid:
            feed_types_by_id[fid] = row
    for row in ext_feed_type_rows:
        fid = (row.get("FeedTypeID") or "").strip()
        if fid:
            feed_types_by_id[fid] = row

    supplier_name_by_id: dict[str, str] = {}
    for row in supplier_rows:
        supplier_id = (row.get("FeedSupplierID") or "").strip()
        supplier_name = (row.get("Name") or "").strip()
        if supplier_id and supplier_name:
            supplier_name_by_id[supplier_id] = supplier_name

    org_units_by_id: dict[str, dict[str, str]] = {}
    org_units_csv_path = Path(args.org_units_csv) if args.org_units_csv else None
    if org_units_csv_path:
        for row in load_optional_csv(org_units_csv_path):
            org_unit_id = (row.get("OrgUnitID") or "").strip()
            if org_unit_id:
                org_units_by_id[org_unit_id] = row

    # Feeding scope for selected populations.
    selected_feeding_rows: list[dict[str, str]] = []
    primary_feed_batches: set[str] = set()
    store_to_consumption_container_counts: dict[str, Counter[str]] = defaultdict(Counter)
    population_to_container: dict[str, str] = {}
    for row in expanded_rows:
        pid = (row.get("PopulationID") or "").strip()
        if not pid:
            continue
        population_to_container[pid] = (row.get("ContainerID") or "").strip()

    for row in feeding_rows_all:
        pop_id = (row.get("PopulationID") or "").strip()
        if pop_id not in expanded_populations:
            continue
        feed_time = (row.get("FeedingTime") or "").strip()
        if cutoff_str and feed_time and feed_time > cutoff_str:
            continue
        feed_batch_id = (row.get("FeedBatchID") or "").strip()
        if not feed_batch_id:
            continue
        selected_feeding_rows.append(row)
        primary_feed_batches.add(feed_batch_id)

        batch_row = feed_batches_by_id.get(feed_batch_id)
        store_id = (batch_row.get("FeedStoreID") or "").strip() if batch_row else ""
        source_container_id = population_to_container.get(pop_id, "")
        if store_id and source_container_id:
            store_to_consumption_container_counts[store_id][source_container_id] += 1

    # Expand upstream feed batches.
    feed_batch_ids: set[str] = set(primary_feed_batches)
    lineage_pairs: list[tuple[str, str]] = []
    for row in feed_lineage_rows:
        src = (row.get("SourceFeedBatchID") or "").strip()
        dst = (row.get("DestinationFeedBatchID") or "").strip()
        if src and dst:
            lineage_pairs.append((src, dst))

    changed = True
    while changed:
        changed = False
        for src, dst in lineage_pairs:
            if dst in feed_batch_ids and src not in feed_batch_ids:
                feed_batch_ids.add(src)
                changed = True

    # Filter reception lines to scoped feed batches.
    scoped_reception_lines: list[dict[str, str]] = []
    for row in reception_line_rows:
        feed_batch_id = (row.get("FeedBatchID") or "").strip()
        if feed_batch_id in feed_batch_ids:
            scoped_reception_lines.append(row)

    # Candidate store->container links from feed-store assignment datasets.
    store_to_assignment_containers: dict[str, list[str]] = defaultdict(list)

    def collect_assignment_rows(rows: list[dict[str, str]]) -> None:
        for row in rows:
            store_id = (row.get("FeedStoreID") or "").strip()
            container_id = (row.get("ContainerID") or "").strip()
            if not store_id or not container_id:
                continue
            if container_id not in store_to_assignment_containers[store_id]:
                store_to_assignment_containers[store_id].append(container_id)

    collect_assignment_rows(store_assign_rows)
    collect_assignment_rows(ext_store_assign_rows)

    # Resolve source container ids -> mapped target container with location.
    candidate_source_containers: set[str] = set()
    for containers in store_to_assignment_containers.values():
        candidate_source_containers.update(containers)
    for counter in store_to_consumption_container_counts.values():
        candidate_source_containers.update(counter.keys())

    source_to_target_container_id: dict[str, int] = {}
    if candidate_source_containers:
        for mapping in ExternalIdMap.objects.filter(
            source_system="FishTalk",
            source_model="Containers",
            source_identifier__in=candidate_source_containers,
        ):
            source_to_target_container_id[mapping.source_identifier] = mapping.target_object_id

    target_containers_by_id: dict[int, Container] = {}
    if source_to_target_container_id:
        for container in Container.objects.filter(pk__in=set(source_to_target_container_id.values())).select_related(
            "hall", "area"
        ):
            target_containers_by_id[container.pk] = container

    org_unit_anchor_cache: dict[str, tuple[Hall | None, Area | None, str]] = {}
    orgunit_station_created = 0
    orgunit_station_updated = 0
    orgunit_hall_created = 0
    orgunit_hall_reused = 0

    def _resolve_org_unit_anchor(org_unit_id: str) -> tuple[Hall | None, Area | None, str]:
        nonlocal orgunit_station_created, orgunit_station_updated, orgunit_hall_created, orgunit_hall_reused
        if not org_unit_id:
            return None, None, "orgunit-missing"
        cached = org_unit_anchor_cache.get(org_unit_id)
        if cached is not None:
            return cached

        org_row = org_units_by_id.get(org_unit_id, {})
        org_name = (org_row.get("Name") or "").strip()
        if not org_name:
            result = (None, None, "orgunit-missing-name")
            org_unit_anchor_cache[org_unit_id] = result
            return result

        station: FreshwaterStation | None = None
        org_map = get_external_map("OrgUnit_FW", org_unit_id)
        if org_map and org_map.target_model == "freshwaterstation":
            station = FreshwaterStation.objects.filter(pk=org_map.target_object_id).first()

        geography_name = infer_geography_name_from_org_unit(org_name)
        station_type = infer_station_type_from_org_unit(org_name)
        latitude = to_decimal(org_row.get("Latitude"), places="0.000001") or Decimal("0.000000")
        longitude = to_decimal(org_row.get("Longitude"), places="0.000001") or Decimal("0.000000")

        if station is None:
            if not geography_name:
                result = (None, None, "orgunit-unclassifiable")
                org_unit_anchor_cache[org_unit_id] = result
                return result
            if args.dry_run:
                geography = Geography(name=geography_name)
                station = FreshwaterStation(
                    name=org_name[:100],
                    station_type=station_type,
                    geography=geography,
                    latitude=latitude,
                    longitude=longitude,
                    description="FishTalk OrgUnit fallback station anchor",
                    active=True,
                )
            else:
                geography = Geography.objects.filter(name=geography_name).first()
                if geography is None:
                    result = (None, None, "orgunit-geography-missing")
                    org_unit_anchor_cache[org_unit_id] = result
                    return result
                station, station_created = FreshwaterStation.objects.get_or_create(
                    name=org_name[:100],
                    defaults={
                        "station_type": station_type,
                        "geography": geography,
                        "latitude": latitude,
                        "longitude": longitude,
                        "description": "FishTalk OrgUnit fallback station anchor",
                        "active": True,
                    },
                )
                if station_created:
                    orgunit_station_created += 1
                else:
                    station_updated = False
                    if station.station_type != station_type:
                        station.station_type = station_type
                        station_updated = True
                    if station.geography_id != geography.id:
                        station.geography = geography
                        station_updated = True
                    if station.latitude != latitude:
                        station.latitude = latitude
                        station_updated = True
                    if station.longitude != longitude:
                        station.longitude = longitude
                        station_updated = True
                    if station_updated:
                        save_with_history(station, user=user, reason=history_reason)
                        orgunit_station_updated += 1
                ExternalIdMap.objects.update_or_create(
                    source_system="FishTalk",
                    source_model="OrgUnit_FW",
                    source_identifier=org_unit_id,
                    defaults={
                        "target_app_label": station._meta.app_label,
                        "target_model": station._meta.model_name,
                        "target_object_id": station.pk,
                        "metadata": {"org_unit_name": org_name},
                    },
                )

        hall: Hall | None = None
        if not args.dry_run and station and station.pk:
            hall = Hall.objects.filter(freshwater_station=station).order_by("id").first()
            if hall:
                orgunit_hall_reused += 1
            else:
                hall_name = f"{org_name[:80]} Feed Hall"
                hall = Hall(
                    name=hall_name[:100],
                    freshwater_station=station,
                    description="Fallback hall anchor for lineage feed-store import",
                    active=True,
                )
                save_with_history(hall, user=user, reason=history_reason)
                orgunit_hall_created += 1
        elif station:
            hall = Hall(
                name=f"{org_name[:80]} Feed Hall"[:100],
                freshwater_station=station,
                description="Fallback hall anchor for lineage feed-store import",
                active=True,
            )

        result = (hall, None, "orgunit")
        org_unit_anchor_cache[org_unit_id] = result
        return result

    def resolve_store_anchor_container(store_id: str) -> tuple[Container | None, str]:
        # 1) Direct feed-store assignment containers first.
        for source_container_id in store_to_assignment_containers.get(store_id, []):
            target_id = source_to_target_container_id.get(source_container_id)
            if not target_id:
                continue
            target_container = target_containers_by_id.get(target_id)
            if target_container and (target_container.hall_id or target_container.area_id):
                return target_container, "assignment"
        # 2) Fallback: infer from populations that consumed feed from this store.
        for source_container_id, _count in store_to_consumption_container_counts.get(store_id, Counter()).most_common():
            target_id = source_to_target_container_id.get(source_container_id)
            if not target_id:
                continue
            target_container = target_containers_by_id.get(target_id)
            if target_container and (target_container.hall_id or target_container.area_id):
                return target_container, "consumption"
        # 3) Fallback: OrgUnit->station/hall anchor for scoped FW stores.
        store_row = stores_by_id.get(store_id, {})
        org_unit_id = (store_row.get("OrgUnitID") or "").strip()
        hall, area, method = _resolve_org_unit_anchor(org_unit_id)
        if hall or area:
            anchor = SimpleNamespace(
                hall=hall,
                area=area,
                hall_id=getattr(hall, "id", None) if hall else None,
                area_id=getattr(area, "id", None) if area else None,
                pk=getattr(hall, "id", None) if hall else getattr(area, "id", None),
                external_id=org_unit_id,
            )
            return anchor, method
        return None, "unresolved"

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if not user:
        raise SystemExit("No users exist in target DB; cannot write history entries")

    # Summary counters.
    stores_created = 0
    stores_updated = 0
    stores_unresolved_line_hits = 0
    stores_unresolved_primary_line_hits = 0
    stores_unresolved_upstream_only_line_hits = 0
    feed_created = 0
    feed_updated = 0
    purchases_created = 0
    purchases_updated = 0
    stock_created = 0
    stock_updated = 0
    skipped_lines = 0
    skipped_after_cutoff = 0

    unresolved_store_ids: set[str] = set()
    unresolved_store_ids_primary: set[str] = set()
    unresolved_store_ids_upstream_only: set[str] = set()
    unresolved_store_line_count = 0
    location_resolution_counts = Counter()

    primary_store_ids: set[str] = set()
    for primary_feed_batch_id in primary_feed_batches:
        primary_batch_row = feed_batches_by_id.get(primary_feed_batch_id)
        if not primary_batch_row:
            continue
        primary_store_id = (primary_batch_row.get("FeedStoreID") or "").strip()
        if primary_store_id:
            primary_store_ids.add(primary_store_id)

    feed_container_cache: dict[str, FeedContainer] = {}
    feed_cache: dict[str, Feed] = {}

    history_reason = (
        "FishTalk migration: lineage-scoped feed inventory "
        f"(batch_keys={len(selected_batch_keys)}, feed_batches={len(feed_batch_ids)})"
    )

    # Sort reception lines by header reception time for deterministic writes.
    def line_sort_key(row: dict[str, str]) -> tuple[str, str, str]:
        rid = (row.get("FeedReceptionID") or "").strip()
        hdr = receptions_by_id.get(rid, {})
        return (
            (hdr.get("ReceptionTime") or ""),
            (row.get("FeedBatchID") or ""),
            (row.get("FeedReceptionLineNumber") or ""),
        )

    scoped_reception_lines.sort(key=line_sort_key)

    with transaction.atomic():
        for row in scoped_reception_lines:
            feed_reception_id = (row.get("FeedReceptionID") or "").strip()
            feed_batch_id = (row.get("FeedBatchID") or "").strip()
            line_number = (row.get("FeedReceptionLineNumber") or "").strip()
            if not feed_reception_id or not feed_batch_id:
                skipped_lines += 1
                continue

            reception = receptions_by_id.get(feed_reception_id)
            if not reception:
                skipped_lines += 1
                continue

            reception_time_raw = (reception.get("ReceptionTime") or "").strip()
            reception_time = parse_dt(reception_time_raw)
            if not reception_time:
                skipped_lines += 1
                continue
            if cutoff_dt and reception_time > cutoff_dt:
                skipped_after_cutoff += 1
                continue
            reception_time_aware = ensure_aware(reception_time)

            feed_batch = feed_batches_by_id.get(feed_batch_id, {})
            feed_store_id = (feed_batch.get("FeedStoreID") or "").strip()
            if not feed_store_id:
                skipped_lines += 1
                continue

            # Ensure feed container for store.
            if feed_store_id in feed_container_cache:
                feed_container = feed_container_cache[feed_store_id]
            else:
                feed_container = None
                feed_store_map = get_external_map("FeedStore", feed_store_id)
                if feed_store_map:
                    feed_container = FeedContainer.objects.filter(pk=feed_store_map.target_object_id).first()

                if feed_container:
                    feed_container_cache[feed_store_id] = feed_container
                else:
                    anchor_container, resolution_method = resolve_store_anchor_container(feed_store_id)
                    if not anchor_container:
                        stores_unresolved_line_hits += 1
                        unresolved_store_ids.add(feed_store_id)
                        if feed_store_id in primary_store_ids:
                            unresolved_store_ids_primary.add(feed_store_id)
                            stores_unresolved_primary_line_hits += 1
                        else:
                            unresolved_store_ids_upstream_only.add(feed_store_id)
                            stores_unresolved_upstream_only_line_hits += 1
                        unresolved_store_line_count += 1
                        skipped_lines += 1
                        continue

                    location_resolution_counts[resolution_method] += 1
                    store_row = stores_by_id.get(feed_store_id, {})
                    store_name = (store_row.get("Name") or f"FeedStore {feed_store_id[:8]}").strip()[:100]
                    store_capacity = to_decimal(store_row.get("Capacity"), places="0.01") or Decimal("0.00")
                    store_active = (store_row.get("Active") or "1").strip() != "0"
                    store_type = normalize_container_type(store_name)

                    if args.dry_run:
                        stores_created += 1
                        # keep a placeholder to continue counting downstream rows
                        feed_container = FeedContainer(
                            name=store_name,
                            container_type=store_type,
                            hall=anchor_container.hall if anchor_container.hall_id else None,
                            area=anchor_container.area if anchor_container.area_id else None,
                            capacity_kg=store_capacity,
                            active=store_active,
                        )
                    else:
                        feed_container = FeedContainer(
                            name=store_name,
                            container_type=store_type,
                            hall=anchor_container.hall if anchor_container.hall_id else None,
                            area=anchor_container.area if anchor_container.area_id else None,
                            capacity_kg=store_capacity,
                            active=store_active,
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
                                    "resolution_method": resolution_method,
                                    "anchor_container_source_id": anchor_container.external_id
                                    if hasattr(anchor_container, "external_id")
                                    else None,
                                    "anchor_container_id": anchor_container.pk,
                                },
                            },
                        )
                        stores_created += 1

                    feed_container_cache[feed_store_id] = feed_container

            # Ensure feed type/feed mapping.
            feed_type_id = (feed_batch.get("FeedTypeID") or "").strip()
            feed_type_row = feed_types_by_id.get(feed_type_id, {})
            feed_type_name = (
                (feed_type_row.get("Name") or "").strip()
                or (row.get("FeedTypeName") or "").strip()
                or f"FeedType {feed_type_id}"
            )
            supplier_id = (
                (feed_type_row.get("FeedSupplierID") or "").strip()
                or (reception.get("SupplierID") or "").strip()
            )
            supplier_name = supplier_name_by_id.get(supplier_id, supplier_id or "FishTalk")

            feed_key = feed_type_id or feed_type_name
            if feed_key in feed_cache:
                feed = feed_cache[feed_key]
            else:
                feed_map = get_external_map("FeedType", feed_type_id) if feed_type_id else None
                if feed_map:
                    feed = Feed.objects.get(pk=feed_map.target_object_id)
                    feed.brand = supplier_name[:100]
                    if not args.dry_run:
                        save_with_history(feed, user=user, reason=history_reason)
                    feed_updated += 1
                else:
                    feed_name = (
                        f"FT-{feed_type_id} {feed_type_name}" if feed_type_id else f"FT-{feed_type_name}"
                    )[:100]
                    if args.dry_run:
                        feed = Feed(
                            name=feed_name,
                            brand=supplier_name[:100],
                            size_category="MEDIUM",
                            protein_percentage=Decimal("45.00"),
                            fat_percentage=Decimal("20.00"),
                            carbohydrate_percentage=Decimal("15.00"),
                            description="FishTalk lineage feed type import",
                            is_active=True,
                        )
                        feed_created += 1
                    else:
                        feed = Feed(
                            name=feed_name,
                            brand=supplier_name[:100],
                            size_category="MEDIUM",
                            protein_percentage=Decimal("45.00"),
                            fat_percentage=Decimal("20.00"),
                            carbohydrate_percentage=Decimal("15.00"),
                            description="FishTalk lineage feed type import",
                            is_active=True,
                        )
                        save_with_history(feed, user=user, reason=history_reason)
                        if feed_type_id:
                            ExternalIdMap.objects.update_or_create(
                                source_system="FishTalk",
                                source_model="FeedType",
                                source_identifier=feed_type_id,
                                defaults={
                                    "target_app_label": feed._meta.app_label,
                                    "target_model": feed._meta.model_name,
                                    "target_object_id": feed.pk,
                                    "metadata": {"feed_type_name": feed_type_name},
                                },
                            )
                        feed_created += 1
                feed_cache[feed_key] = feed

            amount_g = to_decimal(row.get("ReceptionAmount"), places="0.0001")
            if amount_g is None or amount_g <= 0:
                skipped_lines += 1
                continue
            quantity_kg = (amount_g / Decimal("1000")).quantize(Decimal("0.0001"))

            price_per_kg = to_decimal(row.get("PricePerKg"), places="0.0001") or Decimal("0.0100")
            if price_per_kg <= 0:
                price_per_kg = Decimal("0.0100")

            batch_number = (
                (row.get("SuppliersBatchNumber") or "").strip()
                or (row.get("ReceiptNumber") or "").strip()
                or (feed_batch.get("BatchNumber") or "").strip()
                or feed_batch_id
            )
            expiry_dt = parse_dt((row.get("OutOfDate") or "").strip())
            expiry_date = expiry_dt.date() if expiry_dt else None

            notes = (
                f"FishTalk FeedReception={feed_reception_id}; "
                f"FeedBatch={feed_batch_id}; "
                f"FeedStore={feed_store_id}; "
                f"Order={reception.get('OrderNumber') or 'n/a'}; "
                f"OurOrderNo={reception.get('OurOrderNo') or 'n/a'}; "
                f"OurRef={reception.get('OurReference') or 'n/a'}; "
                f"Comment={reception.get('Comment') or ''}"
            )

            source_identifier = f"{feed_reception_id}:{feed_batch_id}:{line_number or '0'}"

            purchase_map = get_external_map("FeedReceptionBatches", source_identifier)
            if purchase_map:
                purchase = FeedPurchase.objects.get(pk=purchase_map.target_object_id)
                purchase.feed = feed
                purchase.purchase_date = reception_time_aware.date()
                purchase.quantity_kg = quantity_kg
                purchase.cost_per_kg = price_per_kg
                purchase.supplier = supplier_name[:100]
                purchase.batch_number = batch_number[:100]
                purchase.expiry_date = expiry_date
                purchase.notes = notes
                if not args.dry_run:
                    save_with_history(purchase, user=user, reason=history_reason)
                purchases_updated += 1
            else:
                purchase = FeedPurchase(
                    feed=feed,
                    purchase_date=reception_time_aware.date(),
                    quantity_kg=quantity_kg,
                    cost_per_kg=price_per_kg,
                    supplier=supplier_name[:100],
                    batch_number=batch_number[:100],
                    expiry_date=expiry_date,
                    notes=notes,
                )
                if not args.dry_run:
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
                                "feed_reception_id": feed_reception_id,
                                "feed_batch_id": feed_batch_id,
                                "line_number": line_number or "0",
                                "feed_store_id": feed_store_id,
                                "scope_lineage": True,
                            },
                        },
                    )
                purchases_created += 1

            stock_map = get_external_map("FeedContainerStock", source_identifier)
            if stock_map:
                stock = FeedContainerStock.objects.get(pk=stock_map.target_object_id)
                stock.feed_container = feed_container
                stock.feed_purchase = purchase
                stock.quantity_kg = quantity_kg
                stock.entry_date = reception_time_aware
                if not args.dry_run:
                    save_with_history(stock, user=user, reason=history_reason)
                stock_updated += 1
            else:
                stock = FeedContainerStock(
                    feed_container=feed_container,
                    feed_purchase=purchase,
                    quantity_kg=quantity_kg,
                    entry_date=reception_time_aware,
                )
                if not args.dry_run:
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
                                "feed_store_id": feed_store_id,
                                "scope_lineage": True,
                            },
                        },
                    )
                stock_created += 1

    summary = {
        "lineage_extract_dir": str(lineage_dir),
        "scope_batch_keys_file": str(batch_keys_file),
        "selected_batch_keys": len(selected_batch_keys),
        "seed_populations": len(seed_populations),
        "expanded_populations": len(expanded_populations),
        "feeding_rows_selected": len(selected_feeding_rows),
        "primary_feed_batches": len(primary_feed_batches),
        "feed_batches_with_upstream": len(feed_batch_ids),
        "reception_lines_scoped": len(scoped_reception_lines),
        "cutoff_end_date": args.cutoff_end_date or "",
        "dry_run": bool(args.dry_run),
        "stores_created": stores_created,
        "stores_updated": stores_updated,
        "stores_unresolved": len(unresolved_store_ids),
        "stores_unresolved_line_hits": stores_unresolved_line_hits,
        "stores_unresolved_ids": sorted(unresolved_store_ids),
        "stores_unresolved_primary": len(unresolved_store_ids_primary),
        "stores_unresolved_primary_ids": sorted(unresolved_store_ids_primary),
        "stores_unresolved_upstream_only": len(unresolved_store_ids_upstream_only),
        "stores_unresolved_upstream_only_ids": sorted(unresolved_store_ids_upstream_only),
        "stores_unresolved_primary_line_hits": stores_unresolved_primary_line_hits,
        "stores_unresolved_upstream_only_line_hits": stores_unresolved_upstream_only_line_hits,
        "store_location_resolution": dict(location_resolution_counts),
        "orgunit_station_created": orgunit_station_created,
        "orgunit_station_updated": orgunit_station_updated,
        "orgunit_hall_created": orgunit_hall_created,
        "orgunit_hall_reused": orgunit_hall_reused,
        "feed_created": feed_created,
        "feed_updated": feed_updated,
        "purchases_created": purchases_created,
        "purchases_updated": purchases_updated,
        "stock_created": stock_created,
        "stock_updated": stock_updated,
        "skipped_lines": skipped_lines,
        "skipped_after_cutoff": skipped_after_cutoff,
        "unresolved_store_line_count": unresolved_store_line_count,
    }

    if args.summary_json:
        out_path = Path(args.summary_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        "Lineage feed inventory migration "
        f"(dry_run={args.dry_run}) "
        f"batch_keys={summary['selected_batch_keys']} "
        f"expanded_pops={summary['expanded_populations']} "
        f"feed_batches={summary['feed_batches_with_upstream']} "
        f"reception_lines={summary['reception_lines_scoped']} "
        f"purchases(created={purchases_created},updated={purchases_updated}) "
        f"stock(created={stock_created},updated={stock_updated}) "
        f"stores(created={stores_created},unresolved={len(unresolved_store_ids)}) "
        f"skipped={skipped_lines} cutoff_skipped={skipped_after_cutoff}"
    )
    if unresolved_store_ids:
        print(
            f"[WARN] Unresolved feed stores: {len(unresolved_store_ids)} "
            f"(line_rows={unresolved_store_line_count}, "
            f"primary_line_rows={stores_unresolved_primary_line_hits}, "
            f"upstream_only_line_rows={stores_unresolved_upstream_only_line_hits})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
