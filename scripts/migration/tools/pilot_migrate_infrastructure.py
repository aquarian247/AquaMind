#!/usr/bin/env python3
"""Canonical infrastructure pre-migration runner.

This delegates to the shared extractor/loader pipeline so that all
infrastructure migrations consistently support:
- area-group hierarchy (`Geography -> AreaGroup -> Area`)
- nested container hierarchy (`Hall -> STRUCTURAL rack -> HOLDING tray`)
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

from scripts.migration.safety import (  # noqa: E402
    assert_default_db_is_migration_db,
    configure_migration_environment,
)

configure_migration_environment()

import django  # noqa: E402

django.setup()
assert_default_db_is_migration_db()

from scripts.migration.extractors.base import (  # noqa: E402
    ExtractionContext,
)
from scripts.migration.extractors.infrastructure import (  # noqa: E402
    InfrastructureExtractor,
)
from scripts.migration.loaders.infrastructure import (  # noqa: E402
    InfrastructureLoader,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pre-create migration infrastructure via shared loader.",
    )
    parser.add_argument(
        "--sql-profile",
        default="fishtalk",
        help="SQL Server connection profile.",
    )
    parser.add_argument(
        "--source-database",
        default=None,
        help="Optional source database override.",
    )
    parser.add_argument(
        "--source-container",
        default=None,
        help="Optional sqlcmd container override.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing.",
    )
    parser.add_argument(
        "--geography",
        default=None,
        help="Legacy no-op flag retained for compatibility.",
    )
    return parser


def _print_header() -> None:
    print("\n" + "=" * 70)
    print("INFRASTRUCTURE PRE-MIGRATION")
    print("=" * 70)


def _print_loader_summary(
    *,
    geographies: int,
    locations: int,
    sites: int,
    containers: int,
    geo_stats: dict,
    location_stats: dict,
    infra_stats: dict,
) -> None:
    print("\n--- Extracted source rows ---")
    print(f"  Geographies: {geographies}")
    print(f"  Locations: {locations}")
    print(f"  Sites: {sites}")
    print(f"  Containers: {containers}")

    print("\n--- Loader results ---")
    print(
        "  Geographies: "
        f"created={geo_stats.get('created', 0)} "
        f"updated={geo_stats.get('updated', 0)} "
        f"skipped={geo_stats.get('skipped', 0)}"
    )
    print(
        "  Locations->Areas: "
        f"created={location_stats.get('created', 0)} "
        f"updated={location_stats.get('updated', 0)} "
        f"skipped={location_stats.get('skipped', 0)}"
    )
    print(
        "  AreaGroups: "
        f"created={infra_stats['area_groups'].get('created', 0)} "
        f"updated={infra_stats['area_groups'].get('updated', 0)} "
        f"skipped={infra_stats['area_groups'].get('skipped', 0)}"
    )
    print(
        "  Stations: "
        f"created={infra_stats['stations'].get('created', 0)} "
        f"updated={infra_stats['stations'].get('updated', 0)} "
        f"skipped={infra_stats['stations'].get('skipped', 0)}"
    )
    print(
        "  Areas: "
        f"created={infra_stats['areas'].get('created', 0)} "
        f"updated={infra_stats['areas'].get('updated', 0)} "
        f"skipped={infra_stats['areas'].get('skipped', 0)}"
    )
    print(
        "  Halls: "
        f"created={infra_stats['halls'].get('created', 0)} "
        f"updated={infra_stats['halls'].get('updated', 0)} "
        f"skipped={infra_stats['halls'].get('skipped', 0)}"
    )
    print(
        "  Rack containers: "
        f"created={infra_stats['racks'].get('created', 0)} "
        f"updated={infra_stats['racks'].get('updated', 0)} "
        f"skipped={infra_stats['racks'].get('skipped', 0)}"
    )
    print(
        "  Holding containers: "
        f"created={infra_stats['containers'].get('created', 0)} "
        f"updated={infra_stats['containers'].get('updated', 0)} "
        f"skipped={infra_stats['containers'].get('skipped', 0)}"
    )

    print("\n[SUCCESS] Infrastructure pre-migration complete")
    print("Next: run pilot_migrate_input_batch.py for batch migration")


def main() -> int:
    args = build_parser().parse_args()
    _print_header()

    if args.geography:
        print(
            "[note] --geography is no longer used. "
            "Geography is derived from grouped site data."
        )

    context = ExtractionContext(
        profile=args.sql_profile,
        database=args.source_database,
        container=args.source_container,
    )
    extractor = InfrastructureExtractor(context=context)
    loader = InfrastructureLoader(dry_run=args.dry_run)

    geographies = extractor.fetch_geographies()
    locations = extractor.fetch_locations()
    sites = extractor.fetch_sites()
    containers = extractor.fetch_containers()

    geo_stats = loader.load_geographies(geographies)
    location_stats = loader.load_locations(locations)
    infra_stats = loader.load_sites_and_containers(sites, containers)

    _print_loader_summary(
        geographies=len(geographies),
        locations=len(locations),
        sites=len(sites),
        containers=len(containers),
        geo_stats=geo_stats,
        location_stats=location_stats,
        infra_stats=infra_stats,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
