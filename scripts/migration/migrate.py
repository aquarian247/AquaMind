#!/usr/bin/env python3
"""High-level migration orchestrator (entry point for replay mode)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

import django
django.setup()

from scripts.migration.config import load_config
from scripts.migration.extractors.base import ExtractionContext
from scripts.migration.extractors.infrastructure import InfrastructureExtractor
from scripts.migration.loaders.infrastructure import InfrastructureLoader

LOGGER = logging.getLogger("migration")


def run_phase(name: str, config: dict, dry_run: bool) -> None:
    handler = PHASE_HANDLERS.get(name)
    if handler is None:
        LOGGER.warning("No handler registered for phase '%s'", name)
        return
    LOGGER.info("Starting phase: %s", name)
    handler(config=config, dry_run=dry_run)
    LOGGER.info("Completed phase: %s", name)


def infrastructure_phase(**kwargs):
    phase_config = kwargs.get('config', {}).get('phases', {}).get('infrastructure', {})
    context = ExtractionContext(
        profile=phase_config.get('source_profile', 'fishtalk_readonly'),
        database=phase_config.get('source_database'),
        container=phase_config.get('source_container'),
    )
    extractor = InfrastructureExtractor(context=context)
    loader = InfrastructureLoader(dry_run=kwargs.get('dry_run', False))
    geos = extractor.fetch_geographies()
    geo_stats = loader.load_geographies(geos)
    locations = extractor.fetch_locations()
    loc_stats = loader.load_locations(locations)
    LOGGER.info(
        "[infra] geographies total=%s created=%s updated=%s skipped=%s",
        len(geos),
        geo_stats.get('created'),
        geo_stats.get('updated'),
        geo_stats.get('skipped'),
    )
    LOGGER.info(
        "[infra] locations total=%s created=%s updated=%s skipped=%s",
        len(locations),
        loc_stats.get('created'),
        loc_stats.get('updated'),
        loc_stats.get('skipped'),
    )


def batches_phase(**kwargs):
    LOGGER.info("[batches] placeholder – load batches + assignments")


def inventory_phase(**kwargs):
    LOGGER.info("[inventory] placeholder – feed + stock data")


def health_phase(**kwargs):
    LOGGER.info("[health] placeholder – journal, treatments, mortality")


def environmental_phase(**kwargs):
    LOGGER.info("[environmental] placeholder – sensor + weather data")


def broodstock_phase(**kwargs):
    LOGGER.info("[broodstock] placeholder – broodstock lineage")


def financial_phase(**kwargs):
    LOGGER.info("[financial] placeholder – harvest + NAV exports")


PHASE_HANDLERS: Dict[str, Callable[..., None]] = {
    'infrastructure': infrastructure_phase,
    'batches': batches_phase,
    'inventory': inventory_phase,
    'health': health_phase,
    'environmental': environmental_phase,
    'broodstock': broodstock_phase,
    'financial': financial_phase,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='FishTalk → AquaMind migration orchestrator')
    parser.add_argument('--config', default='scripts/migration/migration_config.json', help='Path to migration_config.json')
    parser.add_argument('--phases', nargs='*', help='Subset of phases to run (defaults to all enabled phases)')
    parser.add_argument('--dry-run', action='store_true', help='Skip writes and only log actions')
    parser.add_argument('--log-level', default='INFO', help='Logging level (default: INFO)')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format='[%(levelname)s] %(message)s')

    config = load_config(args.config)
    enabled_phases = sorted(
        (name for name, meta in config.get('phases', {}).items() if meta.get('enabled', True)),
        key=lambda name: config['phases'][name].get('order', 0)
    )

    if args.phases:
        phases = [name for name in enabled_phases if name in args.phases]
    else:
        phases = enabled_phases

    LOGGER.info("Running phases: %s", ', '.join(phases) or 'none')
    for phase in phases:
        run_phase(phase, config, args.dry_run)

    return 0


if __name__ == '__main__':
    sys.exit(main())
