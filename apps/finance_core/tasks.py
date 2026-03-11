"""Celery tasks for finance core month-close flows."""

from celery import shared_task

from apps.finance_core.models import Budget
from apps.finance_core.services.valuation import (
    create_allocation_preview_run,
    finalize_valuation_run,
)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def build_allocation_preview_task(self, budget_id: int, month: int, operating_unit_id: int, user_id: int | None = None):
    """Build a persisted allocation preview for the requested period."""

    budget = Budget.objects.select_related("company").get(pk=budget_id)
    operating_unit = budget.company.sites.get(pk=operating_unit_id)
    user = None
    if user_id:
        from django.contrib.auth.models import User

        user = User.objects.filter(pk=user_id).first()
    run = create_allocation_preview_run(
        budget=budget,
        month=month,
        operating_unit=operating_unit,
        user=user,
    )
    return {"run_id": run.run_id, "status": run.status}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def finalize_valuation_run_task(
    self,
    budget_id: int,
    month: int,
    operating_unit_id: int,
    user_id: int | None = None,
    mortality_adjustments: dict | None = None,
):
    """Finalize a valuation run asynchronously."""

    budget = Budget.objects.select_related("company").get(pk=budget_id)
    operating_unit = budget.company.sites.get(pk=operating_unit_id)
    user = None
    if user_id:
        from django.contrib.auth.models import User

        user = User.objects.filter(pk=user_id).first()
    run = finalize_valuation_run(
        budget=budget,
        month=month,
        operating_unit=operating_unit,
        user=user,
        mortality_adjustments=mortality_adjustments,
    )
    return {"run_id": run.run_id, "status": run.status}
