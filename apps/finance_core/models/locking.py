"""Period locking models for finance core."""

from django.db import models
from simple_history.models import HistoricalRecords


class PeriodLock(models.Model):
    """Hard lock that blocks finance-core and biology mutations for a period."""

    period_lock_id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(
        "finance.DimCompany",
        on_delete=models.PROTECT,
        related_name="finance_core_period_locks",
    )
    operating_unit = models.ForeignKey(
        "finance.DimSite",
        on_delete=models.PROTECT,
        related_name="finance_core_period_locks",
    )
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    is_locked = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    lock_reason = models.TextField(blank=True)
    locked_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_finance_core_periods",
    )
    locked_at = models.DateTimeField(auto_now_add=True)
    reopened_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reopened_finance_core_periods",
    )
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_periodlock"
        ordering = ("-year", "-month", "company__display_name", "operating_unit__site_name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "operating_unit", "year", "month"],
                name="finance_core_periodlock_company_operating_unit_year_month_uniq",
            )
        ]

    def __str__(self):
        return (
            f"{self.company.display_name} / {self.operating_unit.site_name} "
            f"{self.year}-{self.month:02d}"
        )
