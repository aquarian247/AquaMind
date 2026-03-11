"""Budgeting models for finance core."""

from django.db import models
from simple_history.models import HistoricalRecords


class BudgetStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class Budget(models.Model):
    """Annual budget container for company-level financial planning."""

    budget_id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(
        "finance.DimCompany",
        on_delete=models.PROTECT,
        related_name="finance_core_budgets",
    )
    name = models.CharField(max_length=150)
    fiscal_year = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=BudgetStatus.choices,
        default=BudgetStatus.DRAFT,
    )
    version = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_core_budgets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_budget"
        ordering = ("-fiscal_year", "company__display_name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "fiscal_year", "name", "version"],
                name="finance_core_budget_company_year_name_version_uniq",
            )
        ]

    def __str__(self):
        return f"{self.company.display_name} {self.fiscal_year} {self.name} v{self.version}"


class BudgetEntry(models.Model):
    """Monthly budget amount for an account and cost center."""

    entry_id = models.BigAutoField(primary_key=True)
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    account = models.ForeignKey(
        "finance_core.Account",
        on_delete=models.PROTECT,
        related_name="budget_entries",
    )
    cost_center = models.ForeignKey(
        "finance_core.CostCenter",
        on_delete=models.PROTECT,
        related_name="budget_entries",
    )
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    allocated_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="allocations",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_budgetentry"
        ordering = ("budget__fiscal_year", "month", "account__code", "cost_center__code")
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "account", "cost_center", "month"],
                name="finance_core_budgetentry_budget_account_costcenter_month_uniq",
            )
        ]

    def __str__(self):
        return (
            f"{self.budget.company.display_name} "
            f"{self.budget.fiscal_year}-{self.month:02d} "
            f"{self.account.code}/{self.cost_center.code}"
        )
