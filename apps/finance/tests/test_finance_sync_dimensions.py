"""Tests for the finance_sync_dimensions management command."""

from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from apps.finance.models import DimCompany, DimSite
from apps.infrastructure.models.area import Area
from apps.infrastructure.models.geography import Geography
from apps.infrastructure.models.station import FreshwaterStation
from apps.users.models import Subsidiary


class FinanceSyncDimensionsCommandTests(TestCase):
    def setUp(self):
        self.geo_fo = Geography.objects.create(
            name="Faroe Islands",
            description="North Atlantic operations",
        )
        self.geo_sc = Geography.objects.create(
            name="Scotland",
            description="UK farming operations",
        )

    def test_initial_sync_creates_companies_and_sites(self):
        FreshwaterStation.objects.create(
            name="Glyvrar Hatchery",
            station_type="FRESHWATER",
            geography=self.geo_fo,
            latitude=Decimal("62.097000"),
            longitude=Decimal("-6.764000"),
            description="Primary freshwater station",
        )
        Area.objects.create(
            name="Vagar Sound",
            geography=self.geo_fo,
            latitude=Decimal("62.105000"),
            longitude=Decimal("-7.000000"),
            max_biomass=Decimal("150000.00"),
        )

        call_command("finance_sync_dimensions")

        self.assertEqual(DimCompany.objects.count(), 4)
        self.assertTrue(
            DimCompany.objects.filter(
                geography=self.geo_fo, subsidiary=Subsidiary.FRESHWATER
            ).exists()
        )
        self.assertTrue(
            DimCompany.objects.filter(
                geography=self.geo_sc, subsidiary=Subsidiary.FARMING
            ).exists()
        )

        self.assertEqual(DimSite.objects.count(), 2)
        station_site = DimSite.objects.get(source_model=DimSite.SourceModel.STATION)
        self.assertEqual(station_site.site_name, "Glyvrar Hatchery")
        self.assertEqual(station_site.company.subsidiary, Subsidiary.FRESHWATER)

    def test_sync_is_idempotent(self):
        station = FreshwaterStation.objects.create(
            name="Toftir Hatchery",
            station_type="FRESHWATER",
            geography=self.geo_fo,
            latitude=Decimal("62.000000"),
            longitude=Decimal("-6.800000"),
            description="",
        )
        area = Area.objects.create(
            name="Lerwick Sound",
            geography=self.geo_fo,
            latitude=Decimal("60.153300"),
            longitude=Decimal("-1.143000"),
            max_biomass=Decimal("175000.00"),
        )

        call_command("finance_sync_dimensions")

        company_ids = set(DimCompany.objects.values_list("company_id", flat=True))
        site_ids = set(DimSite.objects.values_list("site_id", flat=True))

        station.name = "Toftir Hatchery Updated"
        station.save(update_fields=["name"])
        area.name = "Lerwick Sound Updated"
        area.save(update_fields=["name"])

        call_command("finance_sync_dimensions")

        self.assertEqual(
            company_ids,
            set(DimCompany.objects.values_list("company_id", flat=True)),
        )
        self.assertEqual(
            site_ids,
            set(DimSite.objects.values_list("site_id", flat=True)),
        )

        station_site = DimSite.objects.get(
            source_model=DimSite.SourceModel.STATION, source_pk=station.pk
        )
        self.assertEqual(station_site.site_name, "Toftir Hatchery Updated")

        area_site = DimSite.objects.get(
            source_model=DimSite.SourceModel.AREA, source_pk=area.pk
        )
        self.assertEqual(area_site.site_name, "Lerwick Sound Updated")

    def test_sites_link_to_expected_companies(self):
        FreshwaterStation.objects.create(
            name="Klaksvik Hatchery",
            station_type="FRESHWATER",
            geography=self.geo_fo,
            latitude=Decimal("62.237000"),
            longitude=Decimal("-6.583000"),
            description="",
        )
        Area.objects.create(
            name="Oban Bay",
            geography=self.geo_sc,
            latitude=Decimal("56.415000"),
            longitude=Decimal("-5.471000"),
            max_biomass=Decimal("200000.00"),
        )

        call_command("finance_sync_dimensions")

        station_site = DimSite.objects.get(source_model=DimSite.SourceModel.STATION)
        self.assertEqual(station_site.company.geography, self.geo_fo)
        self.assertEqual(station_site.company.subsidiary, Subsidiary.FRESHWATER)

        area_site = DimSite.objects.get(source_model=DimSite.SourceModel.AREA)
        self.assertEqual(area_site.company.geography, self.geo_sc)
        self.assertEqual(area_site.company.subsidiary, Subsidiary.FARMING)
