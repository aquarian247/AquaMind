"""Regression tests for finance-core period locks in batch workflows."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.batch.models import (
    Batch,
    BatchContainerAssignment,
    BatchTransferWorkflow,
    LifeCycleStage,
    Species,
    TransferAction,
)
from apps.finance.models import DimCompany, DimSite
from apps.finance_core.services.locking import lock_period
from apps.infrastructure.models import (
    Container,
    ContainerType,
    FreshwaterStation,
    Geography,
    Hall,
)
from apps.users.models import Subsidiary

User = get_user_model()


class FinanceCorePeriodLockRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lock-test",
            email="lock-test@example.com",
            password="testpass123",
        )
        self.geo = Geography.objects.create(name="Lock Geo")
        self.company = DimCompany.objects.create(
            geography=self.geo,
            subsidiary=Subsidiary.FRESHWATER,
            display_name="Locked Freshwater",
            currency="NOK",
        )
        self.station = FreshwaterStation.objects.create(
            geography=self.geo,
            name="Lock Station",
            station_type="FRESHWATER",
            latitude=Decimal("61.000000"),
            longitude=Decimal("11.000000"),
        )
        self.site = DimSite.objects.create(
            source_model=DimSite.SourceModel.STATION,
            source_pk=self.station.id,
            company=self.company,
            site_name=self.station.name,
        )
        self.hall = Hall.objects.create(
            freshwater_station=self.station,
            name="Lock Hall",
            description="Lock hall",
            area_sqm=Decimal("100.00"),
        )
        self.container_type = ContainerType.objects.create(
            name="Lock Tank",
            category="TANK",
            max_volume_m3=Decimal("50.00"),
        )
        self.source_container = Container.objects.create(
            name="Source Lock Tank",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("40.00"),
            max_biomass_kg=Decimal("2000.00"),
        )
        self.dest_container = Container.objects.create(
            name="Dest Lock Tank",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("40.00"),
            max_biomass_kg=Decimal("2000.00"),
        )
        self.species = Species.objects.create(
            name="Lock Salmon",
            scientific_name="Salmo lock",
        )
        self.source_stage = LifeCycleStage.objects.create(
            name="Lock Stage 1",
            species=self.species,
            order=1,
        )
        self.dest_stage = LifeCycleStage.objects.create(
            name="Lock Stage 2",
            species=self.species,
            order=2,
        )
        self.batch = Batch.objects.create(
            batch_number="LOCK-001",
            species=self.species,
            lifecycle_stage=self.source_stage,
            batch_type="STANDARD",
            status="ACTIVE",
            start_date="2026-01-01",
        )
        self.source_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.source_container,
            lifecycle_stage=self.source_stage,
            population_count=100,
            avg_weight_g=Decimal("100.00"),
            assignment_date="2026-01-01",
            is_active=True,
        )
        self.dest_assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.dest_container,
            lifecycle_stage=self.dest_stage,
            population_count=0,
            avg_weight_g=Decimal("0.00"),
            assignment_date="2026-01-01",
            is_active=True,
        )
        self.workflow = BatchTransferWorkflow.objects.create(
            workflow_number="LOCK-WF-001",
            batch=self.batch,
            workflow_type="LIFECYCLE_TRANSITION",
            source_lifecycle_stage=self.source_stage,
            dest_lifecycle_stage=self.dest_stage,
            planned_start_date="2026-03-10",
            initiated_by=self.user,
            status="PLANNED",
            total_actions_planned=1,
        )
        self.action = TransferAction.objects.create(
            workflow=self.workflow,
            action_number=1,
            source_assignment=self.source_assignment,
            dest_assignment=self.dest_assignment,
            source_population_before=100,
            transferred_count=100,
            transferred_biomass_kg=Decimal("10.00"),
            status="PENDING",
        )

    def test_execute_transfer_is_blocked_when_period_locked(self):
        lock_period(
            company=self.company,
            operating_unit=self.site,
            year=2026,
            month=3,
            user=self.user,
            reason="Month close",
        )

        with self.assertRaises(ValidationError):
            self.action.execute(executed_by=self.user)
