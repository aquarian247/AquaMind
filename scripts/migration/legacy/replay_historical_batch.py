#!/usr/bin/env python3
"""Wrapper that replays a historical batch through the EventEngine."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django
django.setup()
assert_default_db_is_migration_db()

from scripts.migration.replay.historical_feed import HistoricalEventFeed


def load_event_engine_class():
    engine_path = PROJECT_ROOT / 'scripts' / 'data_generation' / '03_event_engine_core.py'
    spec = importlib.util.spec_from_file_location('event_engine_core', engine_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Unable to import EventEngine from {engine_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.EventEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Replay a historical FishTalk batch inside AquaMind via EventEngine')
    parser.add_argument('replay_file', help='Path to the replay JSON file (docs/database/migration/replay_sets/*.json)')
    parser.add_argument('--duration', type=int, help='Override duration (days)')
    parser.add_argument('--geography', help='Override geography name')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    payload = json.loads(Path(args.replay_file).read_text(encoding='utf-8'))
    batch_meta = payload.get('batch', {})

    start_date = datetime.strptime(batch_meta['start_date'], '%Y-%m-%d').date()
    eggs = batch_meta.get('eggs', 100_000)
    geography = args.geography or batch_meta.get('geography', 'Faroe Islands')
    duration = args.duration or batch_meta.get('duration', 365)

    event_feed = HistoricalEventFeed(args.replay_file)
    EventEngine = load_event_engine_class()
    engine = EventEngine(start_date, eggs, geography, duration=duration, event_feed=event_feed)
    return engine.run()


if __name__ == '__main__':
    sys.exit(main())
