"""Tests verifying BI views and supporting indexes for finance data."""

import unittest
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.utils import timezone

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.finance.models import (
    DimCompany,
    DimSite,
    FactHarvest,
    IntercompanyPolicy,
    IntercompanyTransaction,
)
from apps.harvest.models import HarvestEvent, HarvestLot, ProductGrade
from apps.infrastructure.models import Geography
from apps.infrastructure.models.container import Container
from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.station import FreshwaterStation
from apps.users.models import Subsidiary


@unittest.skipIf(connection.vendor == 'sqlite', 'BI views not created for SQLite')
class FinanceBIViewsTests(TestCase):
    """Integration tests for BI-facing database views."""

    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

        geography = Geography.objects.create(name="Faroe Islands")
        station = FreshwaterStation.objects.create(
            name="Glyvrar Hatchery",
            station_type="FRESHWATER",
            geography=geography,
            latitude=Decimal("62.000000"),
            longitude=Decimal("-6.800000"),
        )
        hall = Hall.objects.create(name="Hall A", freshwater_station=station)
        container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("100.00"),
        )
        container = Container.objects.create(
            name="Tank 1",
            container_type=container_type,
            hall=hall,
            volume_m3=Decimal("80.00"),
            max_biomass_kg=Decimal("5000.00"),
        )

        cls.company = DimCompany.objects.create(
            geography=geography,
            subsidiary=Subsidiary.FRESHWATER,
            display_name="FO Freshwater",
            currency="DKK",
        )
        cls.dest_company = DimCompany.objects.create(
            geography=geography,
            subsidiary=Subsidiary.FARMING,
            display_name="FO Farming",
            currency="DKK",
        )
        cls.site = DimSite.objects.create(
            source_model=DimSite.SourceModel.STATION,
            source_pk=station.pk,
            company=cls.company,
            site_name=station.name,
        )

        species = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
        )
        stage = LifeCycleStage.objects.create(
            name="Smolt",
            species=species,
            order=1,
        )
        batch = Batch.objects.create(
            batch_number="BATCH-001",
            species=species,
            lifecycle_stage=stage,
            start_date=now.date(),
        )
        cls.assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=container,
            lifecycle_stage=stage,
            population_count=1000,
            avg_weight_g=Decimal("450.00"),
            assignment_date=now.date(),
        )

        cls.grade = ProductGrade.objects.create(code="HOG", name="Head-on Gutted")
        cls.event = HarvestEvent.objects.create(
            event_date=now,
            batch=batch,
            assignment=cls.assignment,
            dest_geography=geography,
            dest_subsidiary=Subsidiary.FARMING,
        )
        cls.lot = HarvestLot.objects.create(
            event=cls.event,
            product_grade=cls.grade,
            live_weight_kg=Decimal("1200.500"),
            gutted_weight_kg=Decimal("900.250"),
            unit_count=500,
        )

        cls.fact = FactHarvest.objects.create(
            event=cls.event,
            lot=cls.lot,
            event_date=cls.event.event_date,
            quantity_kg=cls.lot.live_weight_kg,
            unit_count=cls.lot.unit_count,
            product_grade=cls.grade,
            dim_company=cls.company,
            dim_site=cls.site,
            dim_batch_id=batch.pk,
        )

        cls.policy = IntercompanyPolicy.objects.create(
            from_company=cls.company,
            to_company=cls.dest_company,
            product_grade=cls.grade,
        )
        cls.transaction = IntercompanyTransaction.objects.create(
            event=cls.event,
            policy=cls.policy,
            posting_date=now.date(),
            amount=Decimal("1500.00"),
            currency="DKK",
        )

    def test_fact_view_projects_expected_columns(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fact_id, event_date, quantity_kg, unit_count,
                       product_grade_code, company, site_name, batch_id
                FROM vw_fact_harvest
                """
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], self.fact.fact_id)
        self.assertEqual(row[1], self.event.event_date)
        self.assertEqual(row[2], self.lot.live_weight_kg)
        self.assertEqual(row[3], self.lot.unit_count)
        self.assertEqual(row[4], self.grade.code)
        self.assertEqual(row[5], self.company.display_name)
        self.assertEqual(row[6], self.site.site_name)
        self.assertEqual(row[7], self.fact.dim_batch_id)

    def test_intercompany_view_projects_expected_columns(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tx_id, posting_date, state, from_company,
                       to_company, product_grade_code, amount, currency
                FROM vw_intercompany_transactions
                """
            )
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], self.transaction.tx_id)
        self.assertEqual(row[1], self.transaction.posting_date)
        self.assertEqual(row[2], self.transaction.state)
        self.assertEqual(row[3], self.policy.from_company.display_name)
        self.assertEqual(row[4], self.policy.to_company.display_name)
        self.assertEqual(row[5], self.grade.code)
        self.assertEqual(row[6], self.transaction.amount)
        self.assertEqual(row[7], self.transaction.currency)

    def test_supporting_indexes_exist(self):
        index_names = [
            "ix_fact_harvest_event_date",
            "ix_fact_harvest_company_grade",
            "ix_intercompany_posting_date",
        ]

        with connection.cursor() as cursor:
            for index in index_names:
                cursor.execute("SELECT to_regclass(%s)", [f"public.{index}"])
                self.assertIsNotNone(cursor.fetchone()[0], index)
