"""Management command to project harvest facts and intercompany transactions."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Iterable, Optional, Set, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.finance.models import (
    FactHarvest,
    IntercompanyPolicy,
    IntercompanyTransaction,
)
from apps.finance.utils import FinanceDimensionResolver, FinanceMappingError
from apps.harvest.models import HarvestEvent, HarvestLot


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Project finance facts from harvest events and detect intercompany movements."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--from",
            dest="from_date",
            help="Inclusive start date (YYYY-MM-DD) for event projection.",
        )
        parser.add_argument(
            "--to",
            dest="to_date",
            help="Inclusive end date (YYYY-MM-DD) for event projection.",
        )

    def handle(self, *args, **options):
        start_dt = self._parse_boundary(options.get("from_date"), start_of_day=True)
        end_dt = self._parse_boundary(options.get("to_date"), start_of_day=False)

        events_qs = self._build_event_queryset(start_dt, end_dt)

        resolver = FinanceDimensionResolver.build()
        policy_cache = self._build_policy_cache()

        stats = {
            "events": 0,
            "lots": 0,
            "facts_created": 0,
            "facts_updated": 0,
            "tx_created": 0,
            "tx_updated": 0,
        }

        with transaction.atomic():
            for event in events_qs:
                stats["events"] += 1
                lots = list(event.lots.all())
                if not lots:
                    continue

                try:
                    source_company, source_site = resolver.resolve_source(event.assignment)
                except FinanceMappingError as exc:
                    raise CommandError(str(exc)) from exc

                dest_company = resolver.resolve_destination(
                    getattr(event.dest_geography, "pk", None),
                    event.dest_subsidiary,
                )

                lots_stats = self._project_lots(
                    event,
                    lots,
                    source_company,
                    source_site,
                )
                stats["lots"] += lots_stats.total
                stats["facts_created"] += lots_stats.created
                stats["facts_updated"] += lots_stats.updated

                if not dest_company or dest_company.pk == source_company.pk:
                    continue

                tx_stats = self._ensure_intercompany_transactions(
                    event,
                    lots,
                    source_company_id=source_company.pk,
                    dest_company_id=dest_company.pk,
                    policy_cache=policy_cache,
                )
                stats["tx_created"] += tx_stats.created
                stats["tx_updated"] += tx_stats.updated

        logger.info(
            {
                "event": "finance_projection_complete",
                **stats,
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Finance projection complete: "
                f"events={stats['events']} lots={stats['lots']} "
                f"facts(created={stats['facts_created']}, updated={stats['facts_updated']}) "
                f"tx(created={stats['tx_created']}, updated={stats['tx_updated']})"
            )
        )

    def _parse_boundary(self, value: Optional[str], *, start_of_day: bool) -> Optional[datetime]:
        if not value:
            return None

        parsed_date = parse_date(value)
        if not parsed_date:
            raise CommandError(f"Invalid date value '{value}'. Expected YYYY-MM-DD")

        current_tz = timezone.get_current_timezone()
        if start_of_day:
            dt = datetime.combine(parsed_date, time.min)
            return timezone.make_aware(dt, current_tz) if timezone.is_naive(dt) else dt

        # end of day inclusive: advance to next day midnight and use lt filter later
        dt = datetime.combine(parsed_date + timedelta(days=1), time.min)
        return timezone.make_aware(dt, current_tz) if timezone.is_naive(dt) else dt

    def _build_event_queryset(
        self, start_dt: Optional[datetime], end_dt: Optional[datetime]
    ) -> Iterable[HarvestEvent]:
        lots_qs = HarvestLot.objects.select_related("product_grade")

        qs = (
            HarvestEvent.objects.select_related(
                "assignment__container__hall__freshwater_station__geography",
                "assignment__container__area__geography",
                "dest_geography",
            )
            .prefetch_related(Prefetch("lots", queryset=lots_qs))
            .order_by("event_date", "id")
        )

        if start_dt:
            qs = qs.filter(event_date__gte=start_dt)
        if end_dt:
            qs = qs.filter(event_date__lt=end_dt)

        return qs

    def _project_lots(
        self,
        event: HarvestEvent,
        lots: Iterable[HarvestLot],
        source_company,
        source_site,
    ) -> "FactsStats":
        stats = FactsStats()

        for lot in lots:
            defaults = {
                "event": event,
                "event_date": event.event_date,
                "quantity_kg": lot.live_weight_kg,
                "unit_count": lot.unit_count,
                "product_grade": lot.product_grade,
                "dim_company": source_company,
                "dim_site": source_site,
                "dim_batch_id": event.batch_id,
            }
            fact, created = FactHarvest.objects.update_or_create(
                lot=lot,
                defaults=defaults,
            )
            stats.increment(created)

        return stats

    def _ensure_intercompany_transactions(
        self,
        event: HarvestEvent,
        lots: Iterable[HarvestLot],
        *,
        source_company_id: int,
        dest_company_id: int,
        policy_cache: Dict[Tuple[int, int, int], IntercompanyPolicy],
    ) -> "FactsStats":
        stats = FactsStats()
        posting_date = event.event_date.date()
        seen_policies: Set[int] = set()

        for lot in lots:
            policy = policy_cache.get(
                (source_company_id, dest_company_id, lot.product_grade_id)
            )
            if not policy or policy.pk in seen_policies:
                continue

            seen_policies.add(policy.pk)
            # Get the content type for HarvestEvent
            from django.contrib.contenttypes.models import ContentType
            harvest_event_ct = ContentType.objects.get(
                app_label='harvest', model='harvestevent'
            )

            tx, created = IntercompanyTransaction.objects.get_or_create(
                content_type=harvest_event_ct,
                object_id=event.id,
                policy=policy,
                defaults={
                    "posting_date": posting_date,
                    "state": IntercompanyTransaction.State.PENDING,
                },
            )

            if created:
                stats.increment(created=True)
                continue

            if tx.posting_date != posting_date:
                IntercompanyTransaction.objects.filter(pk=tx.pk).update(
                    posting_date=posting_date
                )
                stats.increment(created=False)

        return stats

    def _build_policy_cache(self) -> Dict[Tuple[int, int, int], IntercompanyPolicy]:
        cache: Dict[Tuple[int, int, int], IntercompanyPolicy] = {}
        for policy in IntercompanyPolicy.objects.select_related(
            "from_company", "to_company", "product_grade"
        ):
            cache[(policy.from_company_id, policy.to_company_id, policy.product_grade_id)] = policy
        return cache


class FactsStats:
    """Simple counter helper for created/updated stats."""

    def __init__(self) -> None:
        self.created = 0
        self.updated = 0

    def increment(self, created: bool) -> None:
        if created:
            self.created += 1
        else:
            self.updated += 1

    @property
    def total(self) -> int:
        return self.created + self.updated

    def __iter__(self):
        yield from (self.created, self.updated)
