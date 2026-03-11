"""Valuation and reporting services for finance core."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import csv
import io

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.finance_core.models import BudgetEntry, CostImportLine, ValuationRun, ValuationRunStatus
from apps.finance_core.services.allocation import build_allocation_preview, summarize_allocations_by_cost_center

TWOPLACES = Decimal("0.01")


def _round_currency(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _latest_previous_run(*, company_id: int, operating_unit_id: int, year: int, month: int):
    return (
        ValuationRun.objects.filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            status__in=[ValuationRunStatus.PREVIEW, ValuationRunStatus.APPROVED, ValuationRunStatus.EXPORTED],
        )
        .filter(Q(year__lt=year) | Q(year=year, month__lt=month))
        .order_by("-year", "-month", "-version")
        .first()
    )


def _next_version(*, company_id: int, operating_unit_id: int, year: int, month: int) -> int:
    last = (
        ValuationRun.objects.filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            year=year,
            month=month,
        )
        .order_by("-version")
        .first()
    )
    return (last.version if last else 0) + 1


def create_allocation_preview_run(*, budget, month: int, operating_unit, user=None, notes: str = ""):
    """Persist an immutable preview allocation snapshot for a month-close."""

    preview = build_allocation_preview(
        year=budget.fiscal_year,
        month=month,
        operating_unit_id=operating_unit.site_id,
        company_id=budget.company_id,
    )
    import_batch = (
        CostImportLine.objects.filter(
            year=budget.fiscal_year,
            month=month,
            operating_unit=operating_unit,
        )
        .select_related("import_batch")
        .order_by("-import_batch__created_at")
        .first()
    )
    version = _next_version(
        company_id=budget.company_id,
        operating_unit_id=operating_unit.site_id,
        year=budget.fiscal_year,
        month=month,
    )

    valuation_run = ValuationRun.objects.create(
        company=budget.company,
        operating_unit=operating_unit,
        budget=budget,
        import_batch=import_batch.import_batch if import_batch else None,
        year=budget.fiscal_year,
        month=month,
        version=version,
        status=ValuationRunStatus.PREVIEW,
        created_by=user,
        notes=notes,
        biology_snapshot=preview["biology_snapshot"],
        allocation_snapshot=preview["allocations"],
        rule_snapshot=preview["rule_snapshots"],
        totals_snapshot=preview["totals"],
    )
    return valuation_run


def finalize_valuation_run(
    *,
    budget,
    month: int,
    operating_unit,
    user=None,
    mortality_adjustments: dict | None = None,
    notes: str = "",
):
    """Create an approved valuation run from current biology, imports, and budgets."""

    preview = build_allocation_preview(
        year=budget.fiscal_year,
        month=month,
        operating_unit_id=operating_unit.site_id,
        company_id=budget.company_id,
    )

    prior_run = _latest_previous_run(
        company_id=budget.company_id,
        operating_unit_id=operating_unit.site_id,
        year=budget.fiscal_year,
        month=month,
    )
    prior_totals_by_code = {
        row["cost_center_code"]: Decimal(str(row.get("closing_value", "0.00")))
        for row in (prior_run.totals_snapshot.get("cost_centers", []) if prior_run else [])
    }

    direct_budget_rows = list(
        BudgetEntry.objects.select_related("cost_center")
        .filter(
            budget=budget,
            month=month,
            cost_center__site=operating_unit,
        )
    )
    direct_budget_by_code = defaultdict(lambda: Decimal("0.00"))
    for entry in direct_budget_rows:
        direct_budget_by_code[entry.cost_center.code] += entry.amount

    allocation_summary = summarize_allocations_by_cost_center(preview["allocations"])
    biology_by_code = {
        row["cost_center_code"]: row
        for row in preview["biology_snapshot"]
    }
    mortality_adjustments = mortality_adjustments or {}

    cost_center_totals = []
    site_total_opening = Decimal("0.00")
    site_total_closing = Decimal("0.00")
    site_total_allocated = Decimal("0.00")
    site_total_direct = Decimal("0.00")
    site_total_impairment = Decimal("0.00")

    for row in allocation_summary:
        code = row["cost_center_code"]
        opening_value = prior_totals_by_code.get(code, Decimal("0.00"))
        allocated_amount = Decimal(row["allocated_amount"])
        direct_cost = _round_currency(direct_budget_by_code.get(code, Decimal("0.00")))
        biology_row = biology_by_code.get(code, {})
        biomass_kg = Decimal(str(biology_row.get("biomass_kg", "0.00")))

        adjustment_value = mortality_adjustments.get(str(row["cost_center_id"]))
        if adjustment_value is None:
            adjustment_value = mortality_adjustments.get(code, "0")
        impairment_pct = Decimal(str(adjustment_value or "0"))
        pre_impairment_value = opening_value + allocated_amount + direct_cost
        impairment_amount = _round_currency(pre_impairment_value * (impairment_pct / Decimal("100")))
        closing_value = _round_currency(pre_impairment_value - impairment_amount)
        wac_per_kg = _round_currency(closing_value / biomass_kg) if biomass_kg > 0 else Decimal("0.00")

        cost_center_totals.append(
            {
                "cost_center_id": row["cost_center_id"],
                "cost_center_code": code,
                "cost_center_name": row["cost_center_name"],
                "opening_value": f"{opening_value:.2f}",
                "allocated_amount": f"{allocated_amount:.2f}",
                "direct_cost": f"{direct_cost:.2f}",
                "impairment_pct": f"{impairment_pct:.2f}",
                "impairment_amount": f"{impairment_amount:.2f}",
                "closing_value": f"{closing_value:.2f}",
                "closing_biomass_kg": f"{biomass_kg:.2f}",
                "wac_per_kg": f"{wac_per_kg:.2f}",
            }
        )

        site_total_opening += opening_value
        site_total_allocated += allocated_amount
        site_total_direct += direct_cost
        site_total_impairment += impairment_amount
        site_total_closing += closing_value

    delta = _round_currency(site_total_closing - site_total_opening)
    inventory_account = "8313" if operating_unit.source_model == "station" else "8310"
    psg = "SMOLT" if operating_unit.source_model == "station" else "FISKUR"
    debit_account = inventory_account if delta >= 0 else "2211"
    credit_account = "2211" if delta >= 0 else inventory_account
    nav_preview = {
        "delta": f"{delta:.2f}",
        "psg": psg,
        "lines": [
            {
                "account_no": debit_account,
                "balancing_account_no": credit_account,
                "amount": f"{abs(delta):.2f}",
                "entry_type": "DEBIT",
                "operating_unit": operating_unit.site_name,
                "psg": psg,
            },
            {
                "account_no": credit_account,
                "balancing_account_no": debit_account,
                "amount": f"{abs(delta):.2f}",
                "entry_type": "CREDIT",
                "operating_unit": operating_unit.site_name,
                "psg": psg,
            },
        ],
    }

    version = _next_version(
        company_id=budget.company_id,
        operating_unit_id=operating_unit.site_id,
        year=budget.fiscal_year,
        month=month,
    )
    valuation_run = ValuationRun.objects.create(
        company=budget.company,
        operating_unit=operating_unit,
        budget=budget,
        year=budget.fiscal_year,
        month=month,
        version=version,
        status=ValuationRunStatus.APPROVED,
        created_by=user,
        approved_by=user,
        completed_at=timezone.now(),
        notes=notes,
        biology_snapshot=preview["biology_snapshot"],
        allocation_snapshot=preview["allocations"],
        rule_snapshot=preview["rule_snapshots"],
        mortality_snapshot=[
            {"cost_center": key, "impairment_pct": str(value)}
            for key, value in mortality_adjustments.items()
        ],
        totals_snapshot={
            "cost_centers": cost_center_totals,
            "opening_value_total": f"{site_total_opening:.2f}",
            "allocated_total": f"{site_total_allocated:.2f}",
            "direct_total": f"{site_total_direct:.2f}",
            "impairment_total": f"{site_total_impairment:.2f}",
            "closing_value_total": f"{site_total_closing:.2f}",
            "delta": f"{delta:.2f}",
        },
        nav_posting=nav_preview,
    )
    return valuation_run


def build_ring_valuation_report(*, valuation_run: ValuationRun):
    """Return ring/container valuation rows from a run's biology snapshot."""

    totals_by_center = {
        row["cost_center_code"]: Decimal(str(row.get("wac_per_kg", "0.00")))
        for row in valuation_run.totals_snapshot.get("cost_centers", [])
    }
    rows = []
    for biology_row in valuation_run.biology_snapshot:
        wac_per_kg = totals_by_center.get(biology_row["cost_center_code"], Decimal("0.00"))
        biomass_kg = Decimal(str(biology_row.get("biomass_kg", "0.00")))
        rows.append(
            {
                "cost_center_code": biology_row["cost_center_code"],
                "cost_center_name": biology_row["cost_center_name"],
                "batch_numbers": biology_row.get("batch_numbers", []),
                "biomass_kg": f"{biomass_kg:.2f}",
                "wac_per_kg": f"{wac_per_kg:.2f}",
                "estimated_value": f"{_round_currency(biomass_kg * wac_per_kg):.2f}",
            }
        )
    return rows


def build_movement_report(
    *,
    company_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    run_id: int | None = None,
):
    """Aggregate imported, allocated, and closing movements for reporting."""

    queryset = ValuationRun.objects.filter(status__in=[ValuationRunStatus.APPROVED, ValuationRunStatus.EXPORTED])
    if run_id:
        queryset = queryset.filter(run_id=run_id)
    if company_id:
        queryset = queryset.filter(company_id=company_id)
    if year:
        queryset = queryset.filter(year=year)
    if month:
        queryset = queryset.filter(month=month)

    return [
        {
            "run_id": run.run_id,
            "company": run.company.display_name,
            "operating_unit": run.operating_unit.site_name,
            "period": f"{run.year}-{run.month:02d}",
            "allocated_total": run.totals_snapshot.get("allocated_total", "0.00"),
            "closing_value_total": run.totals_snapshot.get("closing_value_total", "0.00"),
            "delta": run.totals_snapshot.get("delta", "0.00"),
        }
        for run in queryset.select_related("company", "operating_unit").order_by("-year", "-month", "-version")
    ]


def build_nav_export_preview(*, valuation_run: ValuationRun, as_csv: bool = False):
    """Return JSON or CSV preview for the valuation run's NAV posting."""

    payload = valuation_run.nav_posting or {}
    if not as_csv:
        return payload

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["operating_unit", "psg", "entry_type", "account_no", "balancing_account_no", "amount"],
    )
    writer.writeheader()
    for row in payload.get("lines", []):
        writer.writerow(row)
    return buffer.getvalue()
