"""Accounting and cost-center models for finance core."""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class AccountType(models.TextChoices):
    ASSET = "ASSET", "Asset"
    LIABILITY = "LIABILITY", "Liability"
    EQUITY = "EQUITY", "Equity"
    REVENUE = "REVENUE", "Revenue"
    EXPENSE = "EXPENSE", "Expense"


class CostCenterType(models.TextChoices):
    SITE = "SITE", "Site"
    PROJECT = "PROJECT", "Project"
    DEPARTMENT = "DEPARTMENT", "Department"
    OTHER = "OTHER", "Other"


class AccountGroup(models.Model):
    """Hierarchical chart-of-account grouping with optional NAV cost group mapping."""

    group_id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    cost_group = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="External cost-group code used in NAV imports.",
    )
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_accountgroup"
        ordering = ("account_type", "display_order", "code")
        constraints = [
            models.UniqueConstraint(
                fields=["cost_group"],
                condition=models.Q(cost_group__isnull=False),
                name="finance_core_accountgroup_cost_group_uniq",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Account(models.Model):
    """Leaf chart-of-account entry."""

    account_id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    group = models.ForeignKey(
        AccountGroup,
        on_delete=models.PROTECT,
        related_name="accounts",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_account"
        ordering = ("account_type", "code")

    def __str__(self):
        return f"{self.code} - {self.name}"


class CostCenter(models.Model):
    """Hierarchical cost-center structure for stations, projects, and departments."""

    cost_center_id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(
        "finance.DimCompany",
        on_delete=models.PROTECT,
        related_name="finance_core_cost_centers",
    )
    site = models.ForeignKey(
        "finance.DimSite",
        on_delete=models.PROTECT,
        related_name="finance_core_cost_centers",
        null=True,
        blank=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=150)
    cost_center_type = models.CharField(
        max_length=20,
        choices=CostCenterType.choices,
        default=CostCenterType.OTHER,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_costcenter"
        ordering = ("company__display_name", "code")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="finance_core_costcenter_company_code_uniq",
            )
        ]

    def clean(self):
        super().clean()
        if self.parent and self.parent.company_id != self.company_id:
            raise ValidationError("Parent cost center must belong to the same company.")
        if self.site and self.site.company_id != self.company_id:
            raise ValidationError("Site must belong to the same company.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CostCenterBatchLink(models.Model):
    """Primary finance-core project link for a biological batch."""

    link_id = models.BigAutoField(primary_key=True)
    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.CASCADE,
        related_name="batch_links",
    )
    batch = models.OneToOneField(
        "batch.Batch",
        on_delete=models.CASCADE,
        related_name="finance_core_link",
    )
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_core_batch_links",
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_costcenterbatchlink"
        ordering = ("batch__batch_number",)

    def clean(self):
        super().clean()
        if self.batch_id and self.cost_center_id and self.cost_center.cost_center_type != CostCenterType.PROJECT:
            raise ValidationError("Batch links must point at PROJECT cost centers.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch.batch_number} -> {self.cost_center.code}"
