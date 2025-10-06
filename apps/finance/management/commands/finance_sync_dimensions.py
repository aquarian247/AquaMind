"""Management command to sync finance dimension tables from infrastructure data."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.finance.models import DimCompany, DimSite
from apps.infrastructure.models.geography import Geography
from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.models.area import Area
from apps.users.models import Subsidiary


class Command(BaseCommand):
    help = "Sync finance dimension tables for companies and sites."

    target_subsidiaries = (Subsidiary.FRESHWATER, Subsidiary.FARMING)

    def handle(self, *args, **options):
        with transaction.atomic():
            companies, company_stats = self._sync_companies()
            site_stats = self._sync_sites(companies)

        self.stdout.write(
            self.style.SUCCESS(
                "Finance dimensions synced: "
                f"companies created={company_stats['created']} updated={company_stats['updated']}, "
                f"sites created={site_stats['created']} updated={site_stats['updated']}"
            )
        )

    def _sync_companies(self):
        stats = {"created": 0, "updated": 0}
        companies = {}

        for geography in Geography.objects.all().order_by("name"):
            for subsidiary in self.target_subsidiaries:
                display_name = f"{subsidiary}-{geography.name}"
                company, created = DimCompany.objects.update_or_create(
                    geography=geography,
                    subsidiary=subsidiary,
                    defaults={"display_name": display_name},
                )
                companies[(geography.id, subsidiary)] = company
                key = "created" if created else "updated"
                stats[key] += 1

        return companies, stats

    def _sync_sites(self, companies):
        stats = {"created": 0, "updated": 0}

        for station in FreshwaterStation.objects.select_related("geography").all():
            company = companies.get((station.geography_id, Subsidiary.FRESHWATER))
            if not company:
                continue

            _, created = DimSite.objects.update_or_create(
                source_model=DimSite.SourceModel.STATION,
                source_pk=station.pk,
                defaults={
                    "company": company,
                    "site_name": station.name,
                },
            )
            key = "created" if created else "updated"
            stats[key] += 1

        for area in Area.objects.select_related("geography").all():
            company = companies.get((area.geography_id, Subsidiary.FARMING))
            if not company:
                continue

            _, created = DimSite.objects.update_or_create(
                source_model=DimSite.SourceModel.AREA,
                source_pk=area.pk,
                defaults={
                    "company": company,
                    "site_name": area.name,
                },
            )
            key = "created" if created else "updated"
            stats[key] += 1

        return stats
