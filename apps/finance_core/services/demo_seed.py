"""Seed a reusable finance-core demo slice for the feature dev environment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction

from apps.batch.models import Batch, BatchContainerAssignment, LifeCycleStage, Species
from apps.finance.models import DimCompany, DimSite
from apps.finance_core.models import (
    Account,
    AccountGroup,
    AllocationRule,
    Budget,
    BudgetEntry,
    CostImportBatch,
    CostImportLine,
    PeriodLock,
    ValuationRun,
)
from apps.finance_core.services.cost_centers import ensure_cost_center_for_assignment
from apps.finance_core.services.imports import import_nav_costs
from apps.finance_core.services.locking import lock_period
from apps.finance_core.services.valuation import (
    create_allocation_preview_run,
    finalize_valuation_run,
)
from apps.infrastructure.models import Container, ContainerType, FreshwaterStation, Geography, Hall
from apps.users.models import Geography as UserGeography
from apps.users.models import Role, Subsidiary


@dataclass(frozen=True)
class DemoPeriod:
    year: int
    month: int

    @property
    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"


def _previous_month(today: date) -> DemoPeriod:
    if today.month == 1:
        return DemoPeriod(year=today.year - 1, month=12)
    return DemoPeriod(year=today.year, month=today.month - 1)


def _make_csv(filename: str, rows: list[tuple[str, str, str]]) -> SimpleUploadedFile:
    buffer = StringIO()
    buffer.write("CostGroup,OperatingUnit,Amount\n")
    for cost_group, operating_unit, amount in rows:
        buffer.write(f"{cost_group},{operating_unit},{amount}\n")
    return SimpleUploadedFile(filename, buffer.getvalue().encode("utf-8"), content_type="text/csv")


def _guard_environment(force: bool) -> None:
    db_name = str(settings.DATABASES["default"]["NAME"]).lower()
    if "migr" in db_name and not force:
        raise CommandError(
            "Refusing to seed finance-core demo data into a migration-preview style "
            "database. Re-run with --force if you really want that."
        )


def seed_finance_core_demo(*, prefix: str = "FC-DEMO", force: bool = False) -> dict:
    """Seed an idempotent finance-core demo slice for feature development."""

    _guard_environment(force)

    prefix = prefix.strip().upper()
    if not prefix:
        raise CommandError("prefix cannot be empty")

    today = date.today()
    current_period = DemoPeriod(year=today.year, month=today.month)
    previous_period = _previous_month(today)
    month_start = date(previous_period.year, previous_period.month, 1)

    with transaction.atomic():
        demo_user, _ = User.objects.get_or_create(
            username=f"{prefix.lower().replace('-', '_')}_finance",
            defaults={"email": f"{prefix.lower().replace('-', '_')}@example.com"},
        )
        demo_user.set_password("FinanceDemo123!")
        demo_user.save()
        profile = demo_user.profile
        profile.role = Role.FINANCE
        profile.geography = UserGeography.ALL
        profile.subsidiary = Subsidiary.ALL
        profile.save()

        geography, _ = Geography.objects.get_or_create(
            name=f"{prefix} Geography",
            defaults={"description": "Finance-core feature-dev demo geography"},
        )
        station, _ = FreshwaterStation.objects.get_or_create(
            name=f"{prefix} Station",
            defaults={
                "station_type": "FRESHWATER",
                "geography": geography,
                "latitude": Decimal("62.000000"),
                "longitude": Decimal("-6.800000"),
                "description": "Finance-core demo station",
            },
        )
        if station.geography_id != geography.id:
            station.geography = geography
            station.save(update_fields=["geography"])

        hall, _ = Hall.objects.get_or_create(
            name=f"{prefix} Hall",
            freshwater_station=station,
            defaults={
                "description": "Finance-core demo hall",
                "area_sqm": Decimal("200.00"),
            },
        )
        container_type, _ = ContainerType.objects.get_or_create(
            name=f"{prefix} Tank Type",
            defaults={
                "category": "TANK",
                "max_volume_m3": Decimal("120.00"),
                "description": "Finance-core demo tank type",
            },
        )
        container_a, _ = Container.objects.get_or_create(
            name=f"{prefix} Tank A",
            hall=hall,
            defaults={
                "container_type": container_type,
                "volume_m3": Decimal("80.00"),
                "max_biomass_kg": Decimal("5000.00"),
                "active": True,
            },
        )
        container_b, _ = Container.objects.get_or_create(
            name=f"{prefix} Tank B",
            hall=hall,
            defaults={
                "container_type": container_type,
                "volume_m3": Decimal("85.00"),
                "max_biomass_kg": Decimal("5000.00"),
                "active": True,
            },
        )

        call_command("finance_sync_dimensions")
        company = DimCompany.objects.get(
            geography=geography,
            subsidiary=Subsidiary.FRESHWATER,
        )
        company.display_name = f"{prefix} Freshwater"
        company.currency = "NOK"
        company.nav_company_code = f"{prefix.replace('-', '')}FW"
        company.save(update_fields=["display_name", "currency", "nav_company_code"])
        site = DimSite.objects.get(
            source_model=DimSite.SourceModel.STATION,
            source_pk=station.id,
        )

        species, _ = Species.objects.get_or_create(
            name=f"{prefix} Salmon",
            defaults={"scientific_name": f"Salmo {prefix.lower().replace('-', '_')}"},
        )
        stage, _ = LifeCycleStage.objects.get_or_create(
            name=f"{prefix} Smolt",
            species=species,
            defaults={"order": 1},
        )

        batch_a, _ = Batch.objects.update_or_create(
            batch_number=f"{prefix}-001",
            defaults={
                "species": species,
                "lifecycle_stage": stage,
                "status": "ACTIVE",
                "batch_type": "STANDARD",
                "start_date": month_start,
            },
        )
        batch_b, _ = Batch.objects.update_or_create(
            batch_number=f"{prefix}-002",
            defaults={
                "species": species,
                "lifecycle_stage": stage,
                "status": "ACTIVE",
                "batch_type": "STANDARD",
                "start_date": month_start,
            },
        )

        assignment_a, _ = BatchContainerAssignment.objects.update_or_create(
            batch=batch_a,
            container=container_a,
            defaults={
                "lifecycle_stage": stage,
                "population_count": 1200,
                "avg_weight_g": Decimal("125.00"),
                "assignment_date": month_start,
                "departure_date": None,
                "is_active": True,
                "notes": "Finance-core feature-dev demo assignment A",
            },
        )
        assignment_b, _ = BatchContainerAssignment.objects.update_or_create(
            batch=batch_b,
            container=container_b,
            defaults={
                "lifecycle_stage": stage,
                "population_count": 800,
                "avg_weight_g": Decimal("150.00"),
                "assignment_date": month_start,
                "departure_date": None,
                "is_active": True,
                "notes": "Finance-core feature-dev demo assignment B",
            },
        )

        cost_center_a = ensure_cost_center_for_assignment(assignment_a, created_by=demo_user)
        cost_center_b = ensure_cost_center_for_assignment(assignment_b, created_by=demo_user)

        opex_group, _ = AccountGroup.objects.update_or_create(
            code=f"{prefix}-OPEX",
            defaults={
                "name": f"{prefix} Operating Expenses",
                "account_type": "EXPENSE",
                "cost_group": f"{prefix}-OPEX",
                "is_active": True,
            },
        )
        feed_group, _ = AccountGroup.objects.update_or_create(
            code=f"{prefix}-FEED",
            defaults={
                "name": f"{prefix} Feed Costs",
                "account_type": "EXPENSE",
                "cost_group": f"{prefix}-FEED",
                "is_active": True,
            },
        )
        station_account, _ = Account.objects.update_or_create(
            code=f"{prefix}-5100",
            defaults={
                "name": f"{prefix} Station Costs",
                "account_type": "EXPENSE",
                "group": opex_group,
                "is_active": True,
            },
        )
        feed_account, _ = Account.objects.update_or_create(
            code=f"{prefix}-5200",
            defaults={
                "name": f"{prefix} Feed Costs",
                "account_type": "EXPENSE",
                "group": feed_group,
                "is_active": True,
            },
        )
        AllocationRule.objects.update_or_create(
            name=f"{prefix} Weighted OPEX",
            account_group=opex_group,
            cost_center=None,
            effective_from=month_start,
            defaults={
                "rule_definition": {
                    "mode": "weighted",
                    "weights": {"headcount": 0.7, "biomass": 0.3},
                    "fallback": "equal_split",
                },
                "is_active": True,
            },
        )

        budget, _ = Budget.objects.update_or_create(
            company=company,
            fiscal_year=current_period.year,
            name=f"{prefix} Budget {current_period.year}",
            version=1,
            defaults={
                "status": "ACTIVE",
                "created_by": demo_user,
                "notes": "Finance-core feature-dev demo budget",
            },
        )

        budget_entries = [
            (previous_period.month, station_account, cost_center_a, Decimal("450.00")),
            (previous_period.month, station_account, cost_center_b, Decimal("300.00")),
            (current_period.month, station_account, cost_center_a, Decimal("500.00")),
            (current_period.month, station_account, cost_center_b, Decimal("350.00")),
            (current_period.month, feed_account, cost_center_a, Decimal("250.00")),
            (current_period.month, feed_account, cost_center_b, Decimal("200.00")),
        ]
        for month_value, account, cost_center, amount in budget_entries:
            BudgetEntry.objects.update_or_create(
                budget=budget,
                account=account,
                cost_center=cost_center,
                month=month_value,
                defaults={
                    "amount": amount,
                    "notes": f"{prefix} demo seeded entry",
                },
            )

        ValuationRun.objects.filter(
            company=company,
            operating_unit=site,
            year__in=[previous_period.year, current_period.year],
            month__in=[previous_period.month, current_period.month],
        ).delete()
        PeriodLock.objects.filter(
            company=company,
            operating_unit=site,
            year__in=[previous_period.year, current_period.year],
            month__in=[previous_period.month, current_period.month],
        ).delete()
        CostImportBatch.objects.filter(source_filename__startswith=prefix).delete()
        previous_import = _make_csv(
            f"{prefix}_prev_import.csv",
            [
                (opex_group.cost_group, site.site_name, "1000.00"),
                (feed_group.cost_group, site.site_name, "700.00"),
            ],
        )
        current_import = _make_csv(
            f"{prefix}_curr_import.csv",
            [
                (opex_group.cost_group, site.site_name, "1200.00"),
                (feed_group.cost_group, site.site_name, "900.00"),
            ],
        )
        import_nav_costs(
            uploaded_file=previous_import,
            year=previous_period.year,
            month=previous_period.month,
            uploaded_by=demo_user,
        )
        import_nav_costs(
            uploaded_file=current_import,
            year=current_period.year,
            month=current_period.month,
            uploaded_by=demo_user,
        )

        finalize_valuation_run(
            budget=budget,
            month=previous_period.month,
            operating_unit=site,
            user=demo_user,
            notes=f"{prefix} previous-month approved run",
        )
        create_allocation_preview_run(
            budget=budget,
            month=current_period.month,
            operating_unit=site,
            user=demo_user,
            notes=f"{prefix} current-month preview run",
        )
        current_approved = finalize_valuation_run(
            budget=budget,
            month=current_period.month,
            operating_unit=site,
            user=demo_user,
            notes=f"{prefix} current-month approved run",
        )
        lock_period(
            company=company,
            operating_unit=site,
            year=previous_period.year,
            month=previous_period.month,
            user=demo_user,
            reason=f"{prefix} demo historical close",
        )

    return {
        "username": demo_user.username,
        "password": "FinanceDemo123!",
        "company": company.display_name,
        "operating_unit": site.site_name,
        "budget": budget.name,
        "current_period": current_period.label,
        "previous_period": previous_period.label,
        "current_approved_run_version": current_approved.version,
        "cost_centers": [cost_center_a.code, cost_center_b.code],
    }
