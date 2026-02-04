"""Historical replay helpers that drive the EventEngine from serialized data."""

from __future__ import annotations

import json
from datetime import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.inventory.models import FeedingEvent
from apps.batch.models import BatchContainerAssignment


class HistoricalEventFeed:
    """Injects deterministic events recorded from legacy systems."""

    def __init__(self, replay_path: str | Path):
        self.replay_path = Path(replay_path)
        payload = json.loads(self.replay_path.read_text(encoding='utf-8'))
        self.batch_meta = payload.get('batch', {})
        self.day_payloads: Dict[str, Dict[str, Any]] = payload.get('days', {})
        self.assignment_cache: Dict[str, BatchContainerAssignment] = {}

    def on_init(self, engine) -> None:
        print(f"🔁 Historical replay enabled ({self.replay_path.name})")

    def on_batch_created(self, batch, assignments: List[BatchContainerAssignment]) -> None:
        # Cache assignments by container name for quick lookup
        for assignment in assignments:
            self.assignment_cache[assignment.container.name] = assignment
        self.batch_id = batch.id

    def process_day(self, engine) -> bool:
        day_key = str(engine.stats['days'])
        payload = self.day_payloads.get(day_key)
        if not payload:
            return False

        for update in payload.get('assignments', []):
            container_name = update.get('container')
            assignment = self._get_assignment(container_name)
            if not assignment:
                continue
            if 'population_count' in update:
                assignment.population_count = update['population_count']
            if 'avg_weight_g' in update:
                assignment.avg_weight_g = update['avg_weight_g']
            if 'biomass_kg' in update:
                assignment.biomass_kg = update['biomass_kg']
            assignment.save(update_fields=['population_count', 'avg_weight_g', 'biomass_kg'])

        for event in payload.get('events', []):
            if event.get('type') == 'feed':
                self._record_feed_event(engine, event)

        return payload.get('replace_default_events', False)

    def after_day(self, engine) -> None:
        # Hook for future post-processing (e.g., metrics comparisons)
        pass

    def _record_feed_event(self, engine, event_payload: Dict[str, Any]) -> None:
        assignment = self._get_assignment(event_payload.get('container'))
        if not assignment:
            return
        feed = engine.get_feed(assignment.lifecycle_stage)
        if not feed:
            return
        amount = event_payload.get('amount_kg')
        hour = event_payload.get('hour', 8)
        FeedingEvent.objects.create(
            batch=engine.batch,
            container=assignment.container,
            batch_assignment=assignment,
            feed=feed,
            feeding_date=engine.current_date,
            feeding_time=time(hour=hour),
            amount_kg=amount,
            batch_biomass_kg=assignment.biomass_kg,
            feeding_percentage=None,
            feed_cost=None,
            method=event_payload.get('method', 'HISTORICAL'),
            notes=event_payload.get('note', 'Historical replay')
        )
        engine.stats['feed'] += 1

    def _get_assignment(self, container_name: Optional[str]) -> Optional[BatchContainerAssignment]:
        if not container_name:
            return None
        assignment = self.assignment_cache.get(container_name)
        if assignment:
            return assignment
        qs = BatchContainerAssignment.objects.filter(container__name=container_name, is_active=True)
        if hasattr(self, 'batch_id'):
            qs = qs.filter(batch_id=self.batch_id)
        assignment = qs.first()
        if assignment:
            self.assignment_cache[container_name] = assignment
        return assignment
