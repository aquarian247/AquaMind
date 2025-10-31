"""Tests for NAV export service routines."""

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.finance.models import (
    DimCompany,
    DimSite,
    FactHarvest,
    IntercompanyPolicy,
    IntercompanyTransaction,
    NavExportBatch,
    NavExportLine,
)
from apps.finance.services import (
    ExportAlreadyExists,
    NoPendingTransactions,
    create_export_batch,
    generate_csv,
)
from apps.harvest.models import HarvestEvent, HarvestLot, ProductGrade
from apps.infrastructure.models import Geography
from apps.infrastructure.models.container import Container
from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.station import FreshwaterStation
from apps.users.models import Subsidiary


class NavExportServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()

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
            max_volume_m3=Decimal("100.00"),
        )
        container = Container.objects.create(
            name="Tank 1",
            container_type=container_type,
            hall=hall,
            volume_m3=Decimal("80.00"),
            max_biomass_kg=Decimal("5000.00"),
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
            dest_geography=geo_dest,
            dest_subsidiary=Subsidiary.FARMING,
        )
        cls.lot = HarvestLot.objects.create(
            event=cls.event,
            product_grade=cls.grade,
            live_weight_kg=Decimal("1200.500"),
            gutted_weight_kg=Decimal("900.250"),
            unit_count=500,
        )

        FactHarvest.objects.create(
            event=cls.event,
            lot=cls.lot,
            event_date=cls.event.event_date,
            quantity_kg=cls.lot.live_weight_kg,
            unit_count=cls.lot.unit_count,
            product_grade=cls.grade,
            dim_company=cls.source_company,
            dim_site=cls.dim_site,
            dim_batch_id=batch.pk,
        )

        cls.policy = IntercompanyPolicy.objects.create(
            from_company=cls.source_company,
            to_company=cls.dest_company,
            product_grade=cls.grade,
        )
        # Get content type for HarvestEvent
        harvest_event_ct = ContentType.objects.get(
            app_label='harvest', model='harvestevent'
        )

        cls.transaction = IntercompanyTransaction.objects.create(
            content_type=harvest_event_ct,
            object_id=cls.event.id,
            policy=cls.policy,
            posting_date=now.date(),
            amount=Decimal("1500.00"),
            currency="DKK",
        )

    def tearDown(self):
        NavExportBatch.objects.all().delete()
        NavExportLine.objects.all().delete()

    def test_create_export_batch_creates_lines_and_marks_transactions(self):
        batch = create_export_batch(
            company_id=self.source_company.pk,
            date_from=self.transaction.posting_date,
            date_to=self.transaction.posting_date,
        )

        self.transaction.refresh_from_db()
        self.assertEqual(
            self.transaction.state,
            IntercompanyTransaction.State.EXPORTED,
        )
        self.assertEqual(batch.lines.count(), 1)

    def test_create_export_batch_rejects_duplicates_without_force(self):
        create_export_batch(
            company_id=self.source_company.pk,
            date_from=self.transaction.posting_date,
            date_to=self.transaction.posting_date,
        )

        with self.assertRaises(ExportAlreadyExists):
            create_export_batch(
                company_id=self.source_company.pk,
                date_from=self.transaction.posting_date,
                date_to=self.transaction.posting_date,
            )

    def test_create_export_batch_force_reprocesses_existing(self):
        batch = create_export_batch(
            company_id=self.source_company.pk,
            date_from=self.transaction.posting_date,
            date_to=self.transaction.posting_date,
        )

        self.transaction.refresh_from_db()
        self.transaction.amount = Decimal("2000.00")
        self.transaction.save(update_fields=["amount"])

        updated = create_export_batch(
            company_id=self.source_company.pk,
            date_from=self.transaction.posting_date,
            date_to=self.transaction.posting_date,
            force=True,
        )

        self.assertEqual(batch.pk, updated.pk)
        line = updated.lines.get()
        self.assertEqual(line.amount, Decimal("2000.00"))

    def test_create_export_batch_without_pending_transactions(self):
        self.transaction.state = IntercompanyTransaction.State.EXPORTED
        self.transaction.save(update_fields=["state"])

        with self.assertRaises(NoPendingTransactions):
            create_export_batch(
                company_id=self.source_company.pk,
                date_from=self.transaction.posting_date,
                date_to=self.transaction.posting_date,
            )

    def test_generate_csv_streams_rows(self):
        batch = create_export_batch(
            company_id=self.source_company.pk,
            date_from=self.transaction.posting_date,
            date_to=self.transaction.posting_date,
        )

        csv_content = b"".join(generate_csv(batch.batch_id)).decode("utf-8").splitlines()

        self.assertIn("export_id,created_at,company,posting_date,currency", csv_content[0])
        self.assertTrue(csv_content[1].startswith("IC"))
        self.assertIn("document_no,account_no,balancing_account_no,amount", csv_content[2])
