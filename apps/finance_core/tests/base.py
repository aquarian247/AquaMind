"""Shared finance-core test data helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.finance.models import DimCompany, DimSite
from apps.finance_core.models import Account, AccountGroup, Budget, BudgetEntry
from apps.infrastructure.models import Container, ContainerType, FreshwaterStation, Geography, Hall
from apps.users.models import Subsidiary


class FinanceCoreDomainMixin:
    """Build a consistent minimum dataset for finance-core tests."""

    def create_finance_core_domain(self, *, user):
        self.geo = Geography.objects.create(name="Finance Core Geo")
        self.company = DimCompany.objects.create(
            geography=self.geo,
            subsidiary=Subsidiary.FRESHWATER,
            display_name="Finance Core Freshwater",
            currency="NOK",
        )
        self.station = FreshwaterStation.objects.create(
            geography=self.geo,
            name="Finance Station",
            station_type="FRESHWATER",
            latitude=Decimal("60.000000"),
            longitude=Decimal("10.000000"),
            description="Finance test station",
        )
        self.site = DimSite.objects.create(
            source_model=DimSite.SourceModel.STATION,
            source_pk=self.station.id,
            company=self.company,
            site_name=self.station.name,
        )
        self.hall = Hall.objects.create(
            freshwater_station=self.station,
            name="Hall F1",
            description="Finance test hall",
            area_sqm=Decimal("100.00"),
        )
        self.container_type = ContainerType.objects.create(
            name="Finance Tank",
            category="TANK",
            max_volume_m3=Decimal("100.00"),
        )
        self.container = Container.objects.create(
            name="Tank FC-1",
            container_type=self.container_type,
            hall=self.hall,
            volume_m3=Decimal("80.00"),
            max_biomass_kg=Decimal("5000.00"),
        )
        self.species = Species.objects.create(
            name="Finance Salmon",
            scientific_name="Salmo finance",
        )
        self.stage = LifeCycleStage.objects.create(
            name="Finance Smolt",
            species=self.species,
            order=1,
        )
        self.batch = Batch.objects.create(
            batch_number="FIN-TEST-001",
            species=self.species,
            lifecycle_stage=self.stage,
            batch_type="STANDARD",
            status="ACTIVE",
            start_date=date(2026, 1, 1),
        )
        self.assignment = BatchContainerAssignment.objects.create(
            batch=self.batch,
            container=self.container,
            lifecycle_stage=self.stage,
            population_count=1000,
            avg_weight_g=Decimal("100.00"),
            assignment_date=date(2026, 1, 1),
            is_active=True,
        )
        self.cost_center = self.batch.finance_core_link.cost_center
        self.account_group = AccountGroup.objects.create(
            code="OPEX",
            name="Operating Expenses",
            account_type="EXPENSE",
            cost_group="OPEX",
        )
        self.account = Account.objects.create(
            code="5100",
            name="Station Costs",
            account_type="EXPENSE",
            group=self.account_group,
        )
        self.budget = Budget.objects.create(
            company=self.company,
            name="Base Budget",
            fiscal_year=2026,
            status="ACTIVE",
            created_by=user,
        )
        self.budget_entry = BudgetEntry.objects.create(
            budget=self.budget,
            account=self.account,
            cost_center=self.cost_center,
            month=3,
            amount=Decimal("500.00"),
            notes="Direct project cost",
        )

    def make_cost_import_file(self, *, amount: str = "1200.00", operating_unit_name: str | None = None):
        operating_unit_name = operating_unit_name or self.site.site_name
        content = f"CostGroup,OperatingUnit,Amount\nOPEX,{operating_unit_name},{amount}\n"
        return SimpleUploadedFile(
            "nav-import.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )
