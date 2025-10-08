"""API tests for harvest events and lots."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status

from apps.harvest.models import HarvestEvent, HarvestLot
from apps.harvest.models import ProductGrade
from apps.infrastructure.models import Geography, ContainerType, FreshwaterStation, Hall, Container
from apps.batch.models import Species, LifeCycleStage, Batch, BatchContainerAssignment
from apps.users.models import Subsidiary
from tests.base import BaseAPITestCase


def _create_harvest_domain(seed_suffix: str = ""):
    """Create prerequisite domain objects for harvest tests."""

    geography = Geography.objects.create(name=f"Faroe Islands{seed_suffix}")

    species = Species.objects.create(
        name=f"Atlantic Salmon{seed_suffix}",
        scientific_name=f"Salmo salar {seed_suffix or 'test'}",
    )
    lifecycle_stage = LifeCycleStage.objects.create(
        name=f"Smolt{seed_suffix}",
        species=species,
        order=1,
    )

    station = FreshwaterStation.objects.create(
        name=f"Station{seed_suffix or '1'}",
        station_type="FRESHWATER",
        geography=geography,
        latitude=Decimal("62.000000"),
        longitude=Decimal("-6.783333"),
    )
    hall = Hall.objects.create(
        name=f"Hall{seed_suffix or 'A'}",
        freshwater_station=station,
    )
    container_type = ContainerType.objects.create(
        name=f"Tank{seed_suffix or '1'}",
        category="TANK",
        max_volume_m3=Decimal("500.00"),
    )
    container = Container.objects.create(
        name=f"Tank-{seed_suffix or 'A'}",
        container_type=container_type,
        hall=hall,
        volume_m3=Decimal("400.00"),
        max_biomass_kg=Decimal("1000.00"),
    )

    batch = Batch.objects.create(
        batch_number=f"BATCH-{seed_suffix or '001'}",
        species=species,
        lifecycle_stage=lifecycle_stage,
        start_date=timezone.now().date() - timedelta(days=30),
    )

    assignment = BatchContainerAssignment.objects.create(
        batch=batch,
        container=container,
        lifecycle_stage=lifecycle_stage,
        population_count=1000,
        avg_weight_g=Decimal("450.00"),
        biomass_kg=Decimal("450.00"),
        assignment_date=timezone.now().date() - timedelta(days=7),
    )

    grade_a = ProductGrade.objects.create(
        code=f"A{seed_suffix or '1'}",
        name=f"Grade A{seed_suffix}",
    )
    grade_b = ProductGrade.objects.create(
        code=f"B{seed_suffix or '1'}",
        name=f"Grade B{seed_suffix}",
    )

    now = timezone.now()
    event_recent = HarvestEvent.objects.create(
        event_date=now,
        batch=batch,
        assignment=assignment,
        dest_geography=geography,
        dest_subsidiary=Subsidiary.FARMING,
        document_ref=f"DOC-{seed_suffix or 'RECENT'}",
    )
    event_older = HarvestEvent.objects.create(
        event_date=now - timedelta(days=2),
        batch=batch,
        assignment=assignment,
        dest_geography=geography,
        dest_subsidiary=Subsidiary.LOGISTICS,
        document_ref=f"DOC-{seed_suffix or 'OLDER'}",
    )

    lot_recent = HarvestLot.objects.create(
        event=event_recent,
        product_grade=grade_a,
        live_weight_kg=Decimal("1200.500"),
        gutted_weight_kg=Decimal("900.250"),
        fillet_weight_kg=Decimal("650.750"),
        unit_count=500,
    )
    HarvestLot.objects.create(
        event=event_recent,
        product_grade=grade_b,
        live_weight_kg=Decimal("800.000"),
        gutted_weight_kg=Decimal("600.000"),
        fillet_weight_kg=Decimal("450.000"),
        unit_count=300,
    )

    return {
        "geography": geography,
        "species": species,
        "lifecycle_stage": lifecycle_stage,
        "batch": batch,
        "assignment": assignment,
        "grade_a": grade_a,
        "grade_b": grade_b,
        "event_recent": event_recent,
        "event_older": event_older,
        "lot_recent": lot_recent,
    }


class HarvestEventAPITest(BaseAPITestCase):
    """API tests for harvest event endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.domain = _create_harvest_domain()

    def setUp(self):
        super().setUp()
        self.events_url = self.get_api_url("operational", "harvest-events")

    def test_list_harvest_events(self):
        response = self.client.get(self.events_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 2)

    def test_filter_harvest_events_by_batch(self):
        response = self.client.get(self.events_url, {"batch": self.domain["batch"].id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_filter_harvest_events_by_date_range(self):
        cutoff = (self.domain["event_recent"].event_date - timedelta(hours=1)).isoformat()
        response = self.client.get(self.events_url, {"date_from": cutoff})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_harvest_events_by_document_ref(self):
        response = self.client.get(self.events_url, {"document_ref": "recent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["document_ref"],
            self.domain["event_recent"].document_ref,
        )

    def test_harvest_event_history_recorded(self):
        self.assertEqual(self.domain["event_recent"].history.count(), 1)

    def test_create_harvest_event_not_allowed(self):
        response = self.client.post(self.events_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class HarvestLotAPITest(BaseAPITestCase):
    """API tests for harvest lot endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.domain = _create_harvest_domain(seed_suffix="-LOTS")

    def setUp(self):
        super().setUp()
        self.lots_url = self.get_api_url("operational", "harvest-lots")

    def test_list_harvest_lots(self):
        response = self.client.get(self.lots_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 2)

    def test_filter_harvest_lots_by_event(self):
        response = self.client.get(self.lots_url, {"event": self.domain["event_recent"].id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_filter_harvest_lots_by_grade_code(self):
        response = self.client.get(self.lots_url, {"grade": self.domain["grade_a"].code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["product_grade"],
            self.domain["grade_a"].id,
        )

    def test_harvest_lot_history_recorded(self):
        self.assertEqual(self.domain["lot_recent"].history.count(), 1)

    def test_create_harvest_lot_not_allowed(self):
        response = self.client.post(self.lots_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
