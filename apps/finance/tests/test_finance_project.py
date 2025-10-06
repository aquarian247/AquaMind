"""Tests for the finance_project management command."""

from decimal import Decimal

from django.core.management import call_command
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
from apps.infrastructure.models.area import Area
from apps.infrastructure.models.container import Container
from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.geography import Geography
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.station import FreshwaterStation
from apps.users.models import Subsidiary


class FinanceProjectCommandTests(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_projection_creates_fact_and_intercompany_transaction(self):
        geo_source = Geography.objects.create(name="Faroe Islands", description="")
        geo_dest = Geography.objects.create(name="Scotland", description="")

        station = FreshwaterStation.objects.create(
            name="Glyvrar Hatchery",
            station_type="FRESHWATER",
            geography=geo_source,
            latitude=Decimal("62.000000"),
            longitude=Decimal("-6.800000"),
            description="",
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

        call_command("finance_sync_dimensions")

        salmon = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
        )
        lifecycle = LifeCycleStage.objects.create(
            name="Smolt",
            species=salmon,
            order=1,
        )
        batch = Batch.objects.create(
            batch_number="BATCH-001",
            species=salmon,
            lifecycle_stage=lifecycle,
            start_date=self.now.date(),
        )
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=container,
            lifecycle_stage=lifecycle,
            population_count=1000,
            avg_weight_g=Decimal("120.00"),
            biomass_kg=Decimal("0.00"),
            assignment_date=self.now.date(),
        )

        grade = ProductGrade.objects.create(code="HOG", name="Head-on Gutted")
        event = HarvestEvent.objects.create(
            event_date=self.now,
            batch=batch,
            assignment=assignment,
            dest_geography=geo_dest,
            dest_subsidiary=Subsidiary.FARMING,
        )
        lot = HarvestLot.objects.create(
            event=event,
            product_grade=grade,
            live_weight_kg=Decimal("1234.500"),
            gutted_weight_kg=Decimal("1100.000"),
            unit_count=600,
        )

        source_company = DimCompany.objects.get(
            geography=geo_source, subsidiary=Subsidiary.FRESHWATER
        )
        dest_company = DimCompany.objects.get(
            geography=geo_dest, subsidiary=Subsidiary.FARMING
        )
        IntercompanyPolicy.objects.create(
            from_company=source_company,
            to_company=dest_company,
            product_grade=grade,
        )

        call_command("finance_project")

        fact = FactHarvest.objects.get()
        self.assertEqual(fact.lot, lot)
        self.assertEqual(fact.event, event)
        self.assertEqual(fact.dim_company, source_company)
        self.assertEqual(fact.dim_site.source_model, DimSite.SourceModel.STATION)
        self.assertEqual(fact.dim_site.source_pk, station.pk)
        self.assertEqual(fact.quantity_kg, lot.live_weight_kg)
        self.assertEqual(fact.unit_count, lot.unit_count)
        self.assertEqual(fact.dim_batch_id, batch.pk)

        tx = IntercompanyTransaction.objects.get()
        self.assertEqual(tx.policy.from_company, source_company)
        self.assertEqual(tx.policy.to_company, dest_company)
        self.assertEqual(tx.event, event)
        self.assertEqual(tx.state, IntercompanyTransaction.State.PENDING)
        self.assertEqual(tx.posting_date, event.event_date.date())

        call_command("finance_project")

        self.assertEqual(FactHarvest.objects.count(), 1)
        self.assertEqual(IntercompanyTransaction.objects.count(), 1)
        fact.refresh_from_db()
        self.assertEqual(fact.quantity_kg, lot.live_weight_kg)
        tx.refresh_from_db()
        self.assertEqual(tx.state, IntercompanyTransaction.State.PENDING)

    def test_projection_skips_intercompany_when_destination_missing(self):
        geo = Geography.objects.create(name="Faroe Islands", description="")
        area = Area.objects.create(
            name="Farming Area",
            geography=geo,
            latitude=Decimal("62.100000"),
            longitude=Decimal("-6.700000"),
            max_biomass=Decimal("200000.00"),
        )
        container_type = ContainerType.objects.create(
            name="Sea Pen",
            category="PEN",
            max_volume_m3=Decimal("5000.00"),
        )
        container = Container.objects.create(
            name="Pen 1",
            container_type=container_type,
            area=area,
            volume_m3=Decimal("4500.00"),
            max_biomass_kg=Decimal("800000.00"),
        )

        call_command("finance_sync_dimensions")

        salmon = Species.objects.create(
            name="Atlantic Salmon",
            scientific_name="Salmo salar",
        )
        lifecycle = LifeCycleStage.objects.create(
            name="Grow-out",
            species=salmon,
            order=2,
        )
        batch = Batch.objects.create(
            batch_number="BATCH-AREA",
            species=salmon,
            lifecycle_stage=lifecycle,
            start_date=self.now.date(),
        )
        assignment = BatchContainerAssignment.objects.create(
            batch=batch,
            container=container,
            lifecycle_stage=lifecycle,
            population_count=5000,
            avg_weight_g=Decimal("2500.00"),
            biomass_kg=Decimal("0.00"),
            assignment_date=self.now.date(),
        )

        grade = ProductGrade.objects.create(code="FROZEN", name="Frozen Whole")
        event = HarvestEvent.objects.create(
            event_date=self.now,
            batch=batch,
            assignment=assignment,
        )
        lot = HarvestLot.objects.create(
            event=event,
            product_grade=grade,
            live_weight_kg=Decimal("8000.000"),
            gutted_weight_kg=Decimal("7600.000"),
            unit_count=4000,
        )

        call_command("finance_project")

        fact = FactHarvest.objects.get()
        self.assertEqual(fact.lot, lot)
        self.assertEqual(fact.dim_company.subsidiary, Subsidiary.FARMING)
        self.assertEqual(fact.dim_site.source_model, DimSite.SourceModel.AREA)
        self.assertEqual(fact.dim_site.source_pk, area.pk)

        self.assertFalse(IntercompanyTransaction.objects.exists())

        call_command("finance_project")
        self.assertEqual(FactHarvest.objects.count(), 1)
        self.assertFalse(IntercompanyTransaction.objects.exists())
