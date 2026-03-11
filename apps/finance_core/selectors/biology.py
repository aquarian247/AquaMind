"""Biology selectors used by finance core valuation flows."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import OperationalError, ProgrammingError
from django.db.models import Q

from apps.batch.models import ActualDailyAssignmentState, BatchContainerAssignment
from apps.finance.services.dimension_mapping import DimensionMappingService


def _decimal_value(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _build_snapshot_row(source, *, population_attr: str, biomass_attr: str, weight_attr: str):
    batch = source.batch
    link = getattr(batch, "finance_core_link", None)
    cost_center = getattr(link, "cost_center", None)
    container = source.container
    site = DimensionMappingService.get_site_for_container(container)
    company = getattr(site, "company", None)

    return {
        "assignment_id": getattr(source, "assignment_id", getattr(source, "id", None)),
        "batch_id": batch.id,
        "batch_number": batch.batch_number,
        "container_id": container.id,
        "container_name": container.name,
        "lifecycle_stage": source.lifecycle_stage.name,
        "site_id": site.site_id if site else None,
        "site_name": site.site_name if site else None,
        "company_id": company.company_id if company else None,
        "company_name": company.display_name if company else None,
        "cost_center_id": cost_center.cost_center_id if cost_center else None,
        "cost_center_code": cost_center.code if cost_center else None,
        "cost_center_name": cost_center.name if cost_center else None,
        "population_count": _decimal_value(getattr(source, population_attr)),
        "biomass_kg": _decimal_value(getattr(source, biomass_attr)),
        "avg_weight_g": _decimal_value(getattr(source, weight_attr)),
    }


def get_opening_biology_snapshot_details(
    *,
    year: int,
    month: int,
    operating_unit_id: int,
    company_id: int | None = None,
):
    """Return opening-of-month headcount, biomass rows, and source metadata."""

    opening_date = date(year, month, 1)
    rows = []
    source = "assignment_fallback"
    latest_recorded_at = None

    try:
        daily_states = (
            ActualDailyAssignmentState.objects.select_related(
                "assignment",
                "batch",
                "container",
                "lifecycle_stage",
            )
            .filter(date=opening_date)
            .order_by("assignment_id")
        )

        for state in daily_states:
            row = _build_snapshot_row(
                state,
                population_attr="population",
                biomass_attr="biomass_kg",
                weight_attr="avg_weight_g",
            )
            if row["site_id"] != operating_unit_id:
                continue
            if company_id and row["company_id"] != company_id:
                continue
            rows.append(row)
            state_recorded_at = getattr(state, "last_computed_at", None)
            if state_recorded_at and (
                latest_recorded_at is None or state_recorded_at > latest_recorded_at
            ):
                latest_recorded_at = state_recorded_at
    except (ProgrammingError, OperationalError):
        rows = []

    if rows:
        return {
            "rows": rows,
            "source": "daily_state",
            "snapshot_date": opening_date.isoformat(),
            "latest_recorded_at": latest_recorded_at.isoformat()
            if latest_recorded_at
            else None,
        }

    assignments = (
        BatchContainerAssignment.objects.select_related(
            "batch",
            "container",
            "lifecycle_stage",
        )
        .filter(assignment_date__lte=opening_date)
        .filter(Q(departure_date__isnull=True) | Q(departure_date__gte=opening_date))
        .order_by("assignment_date", "id")
    )

    for assignment in assignments:
        row = _build_snapshot_row(
            assignment,
            population_attr="population_count",
            biomass_attr="biomass_kg",
            weight_attr="avg_weight_g",
        )
        if row["site_id"] != operating_unit_id:
            continue
        if company_id and row["company_id"] != company_id:
            continue
        rows.append(row)
        assignment_recorded_at = getattr(assignment, "updated_at", None)
        if assignment_recorded_at and (
            latest_recorded_at is None or assignment_recorded_at > latest_recorded_at
        ):
            latest_recorded_at = assignment_recorded_at

    return {
        "rows": rows,
        "source": source,
        "snapshot_date": opening_date.isoformat(),
        "latest_recorded_at": latest_recorded_at.isoformat()
        if latest_recorded_at
        else None,
    }


def get_opening_biology_snapshot(
    *,
    year: int,
    month: int,
    operating_unit_id: int,
    company_id: int | None = None,
):
    """Return opening-of-month headcount and biomass rows for a site."""

    return get_opening_biology_snapshot_details(
        year=year,
        month=month,
        operating_unit_id=operating_unit_id,
        company_id=company_id,
    )["rows"]
