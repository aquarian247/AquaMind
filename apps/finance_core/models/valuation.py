"""Allocation-rule and valuation-run models for finance core."""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class AllocationRule(models.Model):
    """Configurable allocation rule with JSON definition and effective dates."""

    rule_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150)
    account_group = models.ForeignKey(
        "finance_core.AccountGroup",
        on_delete=models.PROTECT,
        related_name="allocation_rules",
        null=True,
        blank=True,
    )
    cost_center = models.ForeignKey(
        "finance_core.CostCenter",
        on_delete=models.PROTECT,
        related_name="allocation_rules",
        null=True,
        blank=True,
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    rule_definition = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_allocationrule"
        ordering = ("-effective_from", "name")

    def clean(self):
        super().clean()
        if not self.account_group and not self.cost_center:
            raise ValidationError("AllocationRule requires an account group or cost center.")
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError("effective_to cannot be before effective_from.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ValuationRunStatus(models.TextChoices):
    PREVIEW = "PREVIEW", "Preview"
    APPROVED = "APPROVED", "Approved"
    EXPORTED = "EXPORTED", "Exported"
    FAILED = "FAILED", "Failed"


class ValuationRun(models.Model):
    """Versioned end-of-month valuation output with immutable snapshots."""

    run_id = models.BigAutoField(primary_key=True)
    run_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    company = models.ForeignKey(
        "finance.DimCompany",
        on_delete=models.PROTECT,
        related_name="finance_core_valuation_runs",
    )
    operating_unit = models.ForeignKey(
        "finance.DimSite",
        on_delete=models.PROTECT,
        related_name="finance_core_valuation_runs",
    )
    budget = models.ForeignKey(
        "finance_core.Budget",
        on_delete=models.SET_NULL,
        related_name="valuation_runs",
        null=True,
        blank=True,
    )
    import_batch = models.ForeignKey(
        "finance_core.CostImportBatch",
        on_delete=models.SET_NULL,
        related_name="valuation_runs",
        null=True,
        blank=True,
    )
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=ValuationRunStatus.choices,
        default=ValuationRunStatus.PREVIEW,
    )
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_finance_core_valuation_runs",
    )
    approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_finance_core_valuation_runs",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    biology_snapshot = models.JSONField(default=list, blank=True)
    allocation_snapshot = models.JSONField(default=list, blank=True)
    rule_snapshot = models.JSONField(default=list, blank=True)
    mortality_snapshot = models.JSONField(default=list, blank=True)
    totals_snapshot = models.JSONField(default=dict, blank=True)
    nav_posting = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_valuationrun"
        ordering = ("-year", "-month", "-version", "-run_timestamp")
        indexes = [
            models.Index(
                fields=["company", "year", "month"],
                name="fc_val_co_per_idx",
            ),
            models.Index(
                fields=["operating_unit", "year", "month"],
                name="fc_val_ou_per_idx",
            ),
            models.Index(
                fields=["company", "operating_unit", "year", "month", "version"],
                name="fc_val_per_ver_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.company.display_name} / {self.operating_unit.site_name} "
            f"{self.year}-{self.month:02d} v{self.version}"
        )
