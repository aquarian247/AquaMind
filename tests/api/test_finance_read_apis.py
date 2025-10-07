"""API tests for finance read-only endpoints."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

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
from apps.users.models import Role, Subsidiary
from tests.base import BaseAPITestCase


class FinanceAPITestDataMixin:
    """Creates shared finance fixtures for API tests."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.now = timezone.now()

        geo_source = Geography.objects.create(name="Faroe Islands")
        geo_dest = Geography.objects.create(name="Scotland")

        station = FreshwaterStation.objects.create(
            name="Glyvrar Hatchery",
            station_type="FRESHWATER",
            geography=geo_source,
            latitude=Decimal("62.000000"),
            longitude=Decimal("-6.800000"),
        )
        hall = Hall.objects.create(name="Hall A", freshwater_station=station)
        container_type = ContainerType.objects.create(
            name="Tank",
            category="TANK",
            max_volume_m3=Decimal("1000.00"),
        )
        container = Container.objects.create(
            name="Tank 1",
            container_type=container_type,
            hall=hall,
            volume_m3=Decimal("800.00"),
            max_biomass_kg=Decimal("50000.00"),
        )

        cls.source_company = DimCompany.objects.create(
            geography=geo_source,
            subsidiary=Subsidiary.FRESHWATER,
            display_name="FO Freshwater",
            currency="DKK",
        )
        cls.dest_company = DimCompany.objects.create(
            geography=geo_dest,
            subsidiary=Subsidiary.FARMING,
            display_name="SC Farming",
            currency="GBP",
        )
        cls.dim_site = DimSite.objects.create(
            source_model=DimSite.SourceModel.STATION,
            source_pk=station.pk,
            company=cls.source_company,
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
        cls.batch = Batch.objects.create(
            batch_number="BATCH-001",
            species=species,
            lifecycle_stage=stage,
            start_date=cls.now.date() - timedelta(days=30),
        )
        assignment = BatchContainerAssignment.objects.create(
            batch=cls.batch,
            container=container,
            lifecycle_stage=stage,
            population_count=1000,
            avg_weight_g=Decimal("450.00"),
            assignment_date=cls.now.date() - timedelta(days=7),
        )

        cls.grade_a = ProductGrade.objects.create(code="HOG", name="Head-on Gutted")
        cls.grade_b = ProductGrade.objects.create(code="TRIM", name="Trimmed")

        cls.event_recent = HarvestEvent.objects.create(
            event_date=cls.now,
            batch=cls.batch,
            assignment=assignment,
            dest_geography=geo_dest,
            dest_subsidiary=Subsidiary.FARMING,
            document_ref="DOC-RECENT",
        )
        cls.event_older = HarvestEvent.objects.create(
            event_date=cls.now - timedelta(days=2),
            batch=cls.batch,
            assignment=assignment,
            dest_geography=geo_dest,
            dest_subsidiary=Subsidiary.LOGISTICS,
            document_ref="DOC-OLDER",
        )

        cls.lot_recent = HarvestLot.objects.create(
            event=cls.event_recent,
            product_grade=cls.grade_a,
            live_weight_kg=Decimal("1200.500"),
            gutted_weight_kg=Decimal("900.250"),
            unit_count=500,
        )
        cls.lot_older = HarvestLot.objects.create(
            event=cls.event_older,
            product_grade=cls.grade_b,
            live_weight_kg=Decimal("800.000"),
            gutted_weight_kg=Decimal("600.000"),
            unit_count=320,
        )

        cls.fact_recent = FactHarvest.objects.create(
            event=cls.event_recent,
            lot=cls.lot_recent,
            event_date=cls.event_recent.event_date,
            quantity_kg=cls.lot_recent.live_weight_kg,
            unit_count=cls.lot_recent.unit_count,
            product_grade=cls.grade_a,
            dim_company=cls.source_company,
            dim_site=cls.dim_site,
            dim_batch_id=cls.batch.pk,
        )
        cls.fact_older = FactHarvest.objects.create(
            event=cls.event_older,
            lot=cls.lot_older,
            event_date=cls.event_older.event_date,
            quantity_kg=cls.lot_older.live_weight_kg,
            unit_count=cls.lot_older.unit_count,
            product_grade=cls.grade_b,
            dim_company=cls.source_company,
            dim_site=cls.dim_site,
            dim_batch_id=cls.batch.pk,
        )

        cls.policy = IntercompanyPolicy.objects.create(
            from_company=cls.source_company,
            to_company=cls.dest_company,
            product_grade=cls.grade_a,
        )
        cls.tx_pending = IntercompanyTransaction.objects.create(
            event=cls.event_recent,
            policy=cls.policy,
            posting_date=cls.event_recent.event_date.date(),
            amount=Decimal("1500.00"),
            currency="DKK",
            state=IntercompanyTransaction.State.PENDING,
        )
        cls.tx_exported = IntercompanyTransaction.objects.create(
            event=cls.event_older,
            policy=cls.policy,
            posting_date=cls.event_older.event_date.date(),
            amount=Decimal("800.00"),
            currency="DKK",
            state=IntercompanyTransaction.State.EXPORTED,
        )


class FinanceAPIPermissionTest(FinanceAPITestDataMixin, BaseAPITestCase):
    """Ensures finance endpoints enforce RBAC."""

    def setUp(self):
        super().setUp()
        self.facts_url = self.get_api_url("finance", "facts/harvests")
        self.tx_url = self.get_api_url("finance", "intercompany/transactions")

    def test_finance_facts_requires_finance_role(self):
        response = self.client.get(self.facts_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_finance_transactions_requires_finance_role(self):
        response = self.client.get(self.tx_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FinanceFactsAPITest(FinanceAPITestDataMixin, BaseAPITestCase):
    """Validates finance facts read API behaviour."""

    def setUp(self):
        super().setUp()
        self.user.profile.role = Role.FINANCE
        self.user.profile.save()
        self.facts_url = self.get_api_url("finance", "facts/harvests")

    def test_list_facts(self):
        response = self.client.get(self.facts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_filter_facts_by_company_and_grade(self):
        params = {
            "company": self.source_company.company_id,
            "grade": self.grade_a.code,
        }
        response = self.client.get(self.facts_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["lot"],
            self.fact_recent.lot_id,
        )

    def test_filter_facts_by_date_range(self):
        params = {
            "date_from": (self.fact_recent.event_date - timedelta(minutes=1)).isoformat(),
            "date_to": self.fact_recent.event_date.isoformat(),
        }
        response = self.client.get(self.facts_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["event"], self.event_recent.pk)

    def test_ordering_ascending(self):
        response = self.client.get(self.facts_url, {"ordering": "event_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["event"], self.event_older.pk)

    def test_pagination_override(self):
        response = self.client.get(self.facts_url, {"page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])

    def test_create_fact_disallowed(self):
        response = self.client.post(self.facts_url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class FinanceIntercompanyAPITest(FinanceAPITestDataMixin, BaseAPITestCase):
    """Validates intercompany transaction API behaviour."""

    def setUp(self):
        super().setUp()
        self.user.profile.role = Role.FINANCE
        self.user.profile.save()
        self.tx_url = self.get_api_url("finance", "intercompany/transactions")

    def test_list_transactions(self):
        response = self.client.get(self.tx_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_filter_transactions_by_state_and_company(self):
        params = {
            "state": IntercompanyTransaction.State.PENDING,
            "company": self.source_company.company_id,
        }
        response = self.client.get(self.tx_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["tx_id"], self.tx_pending.tx_id)

    def test_filter_transactions_by_date_range(self):
        params = {
            "date_to": self.tx_exported.posting_date.isoformat(),
        }
        response = self.client.get(self.tx_url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["tx_id"], self.tx_exported.tx_id)

    def test_ordering_ascending(self):
        response = self.client.get(self.tx_url, {"ordering": "posting_date"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["tx_id"], self.tx_exported.tx_id)

    def test_pagination_override(self):
        response = self.client.get(self.tx_url, {"page_size": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])

    def test_create_transaction_disallowed(self):
        response = self.client.post(self.tx_url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
