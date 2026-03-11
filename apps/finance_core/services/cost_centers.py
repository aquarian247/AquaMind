"""Cost-center lifecycle helpers for finance core."""

from __future__ import annotations

from datetime import date

from apps.finance.services.dimension_mapping import DimensionMappingService
from apps.finance_core.models import CostCenter, CostCenterBatchLink, CostCenterType


def ensure_cost_center_for_assignment(assignment, *, created_by=None):
    """
    Ensure a biological batch has a project cost center linked to its current site.

    The first assignment seen for a batch becomes the canonical finance-core project
    link. Additional assignments reuse the same project, supporting many batches to
    one cost project without disturbing existing operational finance behaviour.
    """

    if assignment is None or not getattr(assignment, "container_id", None):
        return None

    existing_link = getattr(assignment.batch, "finance_core_link", None)
    if existing_link:
        return existing_link.cost_center

    site = DimensionMappingService.get_site_for_container(assignment.container)
    if not site:
        return None

    company = site.company

    site_cost_center, _ = CostCenter.objects.get_or_create(
        company=company,
        code=f"SITE-{site.site_id}",
        defaults={
            "name": site.site_name,
            "site": site,
            "cost_center_type": CostCenterType.SITE,
            "description": "Auto-created site cost center from finance-core linkage.",
        },
    )

    assignment_date = assignment.assignment_date
    if isinstance(assignment_date, str):
        assignment_date = date.fromisoformat(assignment_date)
    month_token = assignment_date.strftime("%b").upper()
    project_cost_center, _ = CostCenter.objects.get_or_create(
        company=company,
        code=f"PRJ-{assignment.batch_id}",
        defaults={
            "site": site,
            "parent": site_cost_center,
            "name": f"{site.site_name}-{assignment.batch.batch_number}:{month_token}",
            "cost_center_type": CostCenterType.PROJECT,
            "description": "Auto-created batch project for finance-core allocation.",
        },
    )

    CostCenterBatchLink.objects.get_or_create(
        batch=assignment.batch,
        defaults={
            "cost_center": project_cost_center,
            "created_by": created_by,
        },
    )

    return project_cost_center
