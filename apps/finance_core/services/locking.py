"""Period-lock enforcement and lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.finance.services.dimension_mapping import DimensionMappingService
from apps.finance_core.models import PeriodLock


@dataclass(frozen=True)
class PeriodContext:
    company_id: int
    operating_unit_id: int
    year: int
    month: int


class LockGuardService:
    """Centralized checks for finance-core period locks."""

    @staticmethod
    def _coerce_date(target_date):
        if hasattr(target_date, "year"):
            return target_date
        if isinstance(target_date, str):
            return date.fromisoformat(target_date)
        return timezone.now().date()

    @staticmethod
    def get_period_context(*, target_date: date, container) -> PeriodContext | None:
        target_date = LockGuardService._coerce_date(target_date)
        site = DimensionMappingService.get_site_for_container(container)
        if not site:
            return None
        return PeriodContext(
            company_id=site.company_id,
            operating_unit_id=site.site_id,
            year=target_date.year,
            month=target_date.month,
        )

    @staticmethod
    def is_locked(*, company_id: int, operating_unit_id: int, year: int, month: int) -> bool:
        return PeriodLock.objects.filter(
            company_id=company_id,
            operating_unit_id=operating_unit_id,
            year=year,
            month=month,
            is_locked=True,
        ).exists()

    @classmethod
    def assert_assignment_editable(cls, assignment, *, target_date: date | None = None):
        if assignment is None or not getattr(assignment, "container_id", None):
            return
        context = cls.get_period_context(
            target_date=target_date or getattr(assignment, "assignment_date", None) or timezone.now().date(),
            container=assignment.container,
        )
        if not context:
            return
        if cls.is_locked(
            company_id=context.company_id,
            operating_unit_id=context.operating_unit_id,
            year=context.year,
            month=context.month,
        ):
            raise ValidationError(
                "This biology change is blocked because the finance period is locked."
            )

    @classmethod
    def assert_container_editable(cls, container, *, target_date: date | None = None):
        if container is None:
            return
        context = cls.get_period_context(
            target_date=target_date or timezone.now().date(),
            container=container,
        )
        if not context:
            return
        if cls.is_locked(
            company_id=context.company_id,
            operating_unit_id=context.operating_unit_id,
            year=context.year,
            month=context.month,
        ):
            raise ValidationError(
                "This biology change is blocked because the finance period is locked."
            )


def lock_period(*, company, operating_unit, year: int, month: int, user=None, reason: str = ""):
    """Lock a period and return the resulting lock record."""

    lock, created = PeriodLock.objects.get_or_create(
        company=company,
        operating_unit=operating_unit,
        year=year,
        month=month,
        defaults={
            "locked_by": user,
            "lock_reason": reason,
            "is_locked": True,
        },
    )
    if not created:
        lock.is_locked = True
        lock.locked_by = user
        lock.lock_reason = reason
        lock.locked_at = timezone.now()
        lock.save(
            update_fields=[
                "is_locked",
                "locked_by",
                "lock_reason",
                "locked_at",
                "updated_at",
            ]
        )
    return lock


def reopen_period(*, period_lock: PeriodLock, user=None, reason: str = ""):
    """Reopen a period with mandatory reason and version bump."""

    if not reason:
        raise ValidationError("Reopen reason is required.")
    period_lock.is_locked = False
    period_lock.version += 1
    period_lock.reopened_by = user
    period_lock.reopened_at = timezone.now()
    period_lock.reopen_reason = reason
    period_lock.save(
        update_fields=[
            "is_locked",
            "version",
            "reopened_by",
            "reopened_at",
            "reopen_reason",
            "updated_at",
        ]
    )
    return period_lock
