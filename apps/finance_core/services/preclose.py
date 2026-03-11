"""Pre-close validation summary for finance core."""

from __future__ import annotations

from decimal import Decimal

from apps.finance_core.models import (
    Budget,
    CostImportLine,
    PeriodLock,
    ValuationRun,
    ValuationRunStatus,
)
from apps.finance_core.selectors.biology import get_opening_biology_snapshot_details


def _latest_import_summary(*, company_id: int, operating_unit_id: int, year: int, month: int):
    latest_line = (
        CostImportLine.objects.select_related("import_batch")
        .filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            year=year,
            month=month,
        )
        .order_by("-import_batch__created_at")
        .first()
    )
    if not latest_line:
        return None

    import_batch = latest_line.import_batch
    return {
        "import_batch_id": import_batch.import_batch_id,
        "source_filename": import_batch.source_filename,
        "imported_row_count": import_batch.imported_row_count,
        "total_amount": f"{import_batch.total_amount:.2f}",
        "created_at": import_batch.created_at.isoformat(),
        "uploaded_by_username": getattr(import_batch.uploaded_by, "username", None),
    }


def _valuation_run_summary(run):
    if not run:
        return None
    return {
        "run_id": run.run_id,
        "version": run.version,
        "status": run.status,
        "run_timestamp": run.run_timestamp.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "delta": run.totals_snapshot.get("delta"),
        "closing_value_total": run.totals_snapshot.get("closing_value_total"),
    }


def build_preclose_summary(
    *,
    company_id: int,
    operating_unit_id: int,
    year: int,
    month: int,
    budget_id: int | None = None,
):
    """Build a user-facing readiness summary for the EoM workflow."""

    budget = None
    if budget_id:
        budget = Budget.objects.filter(pk=budget_id).first()
    if budget is None:
        budget = (
            Budget.objects.filter(company_id=company_id, fiscal_year=year)
            .order_by("-version", "name")
            .first()
        )

    biology = get_opening_biology_snapshot_details(
        year=year,
        month=month,
        operating_unit_id=operating_unit_id,
        company_id=company_id,
    )
    biology_rows = biology["rows"]
    missing_cost_projects = [
        {
            "batch_id": row["batch_id"],
            "batch_number": row["batch_number"],
            "container_id": row["container_id"],
            "container_name": row["container_name"],
        }
        for row in biology_rows
        if not row["cost_center_id"]
    ]

    import_summary = _latest_import_summary(
        company_id=company_id,
        operating_unit_id=operating_unit_id,
        year=year,
        month=month,
    )

    valuation_runs = list(
        ValuationRun.objects.filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            year=year,
            month=month,
        )
        .order_by("-version")
    )
    latest_preview = next(
        (run for run in valuation_runs if run.status == ValuationRunStatus.PREVIEW),
        None,
    )
    latest_approved = next(
        (
            run
            for run in valuation_runs
            if run.status in [ValuationRunStatus.APPROVED, ValuationRunStatus.EXPORTED]
        ),
        None,
    )

    current_lock = (
        PeriodLock.objects.select_related("locked_by", "reopened_by")
        .filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            year=year,
            month=month,
        )
        .order_by("-version", "-updated_at")
        .first()
    )

    nav_ready = bool(latest_approved and latest_approved.nav_posting.get("lines"))
    lock_ready = bool(latest_approved and nav_ready)
    import_ready = import_summary is not None
    biology_ready = bool(biology_rows)
    project_links_ready = not missing_cost_projects
    allocation_ready = latest_preview is not None
    valuation_ready = latest_approved is not None
    locked = bool(current_lock and current_lock.is_locked)

    checks = [
        {
            "code": "import",
            "label": "Import",
            "status": "complete" if import_ready else "blocked",
            "blocking": not import_ready,
            "message": (
                f"Imported {import_summary['source_filename']} with {import_summary['total_amount']}"
                if import_ready
                else "No cost import found for the selected period."
            ),
        },
        {
            "code": "biology",
            "label": "Biology",
            "status": "warning" if biology_ready and biology["source"] != "daily_state" else ("complete" if biology_ready else "blocked"),
            "blocking": not biology_ready,
            "message": (
                f"{len(biology_rows)} biology rows from {biology['source']}"
                if biology_ready
                else "No biology rows found for the selected period."
            ),
        },
        {
            "code": "cost_projects",
            "label": "Cost Projects",
            "status": "complete" if project_links_ready else "blocked",
            "blocking": not project_links_ready,
            "message": (
                "All biology rows are linked to cost projects."
                if project_links_ready
                else f"{len(missing_cost_projects)} biology rows are missing cost projects."
            ),
        },
        {
            "code": "allocation",
            "label": "Allocation",
            "status": "complete" if allocation_ready else "pending",
            "blocking": False,
            "message": (
                f"Latest preview run: v{latest_preview.version}"
                if allocation_ready
                else "No allocation preview has been generated yet."
            ),
        },
        {
            "code": "valuation",
            "label": "Valuation",
            "status": "complete" if valuation_ready else "pending",
            "blocking": False,
            "message": (
                f"Latest approved run: v{latest_approved.version}"
                if valuation_ready
                else "No approved valuation run has been generated yet."
            ),
        },
        {
            "code": "nav_preview",
            "label": "NAV Preview",
            "status": "complete" if nav_ready else "pending",
            "blocking": False,
            "message": (
                f"Delta {latest_approved.totals_snapshot.get('delta')}"
                if nav_ready and latest_approved
                else "NAV preview is not ready yet."
            ),
        },
        {
            "code": "lock",
            "label": "Lock",
            "status": "complete" if locked else ("ready" if lock_ready else "pending"),
            "blocking": False,
            "message": (
                f"Locked at version {current_lock.version}"
                if locked and current_lock
                else "Period can be locked after valuation and NAV preview."
            ),
        },
    ]

    return {
        "period": f"{year}-{month:02d}",
        "budget": {
            "budget_id": budget.budget_id if budget else None,
            "name": budget.name if budget else None,
            "version": budget.version if budget else None,
            "status": budget.status if budget else None,
        },
        "biology": {
            "row_count": len(biology_rows),
            "source": biology["source"],
            "snapshot_date": biology["snapshot_date"],
            "latest_recorded_at": biology["latest_recorded_at"],
            "missing_cost_projects": missing_cost_projects,
        },
        "latest_import": import_summary,
        "latest_preview_run": _valuation_run_summary(latest_preview),
        "latest_approved_run": _valuation_run_summary(latest_approved),
        "current_lock": {
            "period_lock_id": current_lock.period_lock_id if current_lock else None,
            "is_locked": current_lock.is_locked if current_lock else False,
            "version": current_lock.version if current_lock else None,
            "locked_at": current_lock.locked_at.isoformat() if current_lock else None,
            "locked_by_username": getattr(current_lock.locked_by, "username", None)
            if current_lock
            else None,
            "reopened_at": current_lock.reopened_at.isoformat()
            if current_lock and current_lock.reopened_at
            else None,
            "reopened_by_username": getattr(current_lock.reopened_by, "username", None)
            if current_lock
            else None,
            "lock_reason": current_lock.lock_reason if current_lock else "",
            "reopen_reason": current_lock.reopen_reason if current_lock else "",
        },
        "checks": checks,
        "actions": {
            "can_import": not locked,
            "can_allocate": import_ready and biology_ready and project_links_ready and not locked and budget is not None,
            "can_valuate": allocation_ready and not locked and budget is not None,
            "can_lock": lock_ready and not locked,
            "can_unlock": locked,
        },
    }
