"""Import models for finance core actual-cost intake."""

from django.db import models
from simple_history.models import HistoricalRecords


class CostImportBatch(models.Model):
    """Metadata container for idempotent NAV cost imports."""

    import_batch_id = models.BigAutoField(primary_key=True)
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    source_filename = models.CharField(max_length=255)
    checksum = models.CharField(max_length=64, blank=True)
    imported_row_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    uploaded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_core_cost_import_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_costimportbatch"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Import {self.year}-{self.month:02d} ({self.source_filename})"


class CostImportLine(models.Model):
    """Imported actual cost amount to be allocated during EoM."""

    line_id = models.BigAutoField(primary_key=True)
    import_batch = models.ForeignKey(
        CostImportBatch,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    company = models.ForeignKey(
        "finance.DimCompany",
        on_delete=models.PROTECT,
        related_name="finance_core_import_lines",
    )
    operating_unit = models.ForeignKey(
        "finance.DimSite",
        on_delete=models.PROTECT,
        related_name="finance_core_import_lines",
    )
    account_group = models.ForeignKey(
        "finance_core.AccountGroup",
        on_delete=models.PROTECT,
        related_name="import_lines",
    )
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    cost_group_code = models.CharField(max_length=64)
    operating_unit_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "finance_core_costimportline"
        ordering = ("year", "month", "operating_unit_name", "cost_group_code")
        indexes = [
            models.Index(
                fields=["year", "month", "operating_unit"],
                name="fc_imp_yr_mo_ou_idx",
            ),
            models.Index(
                fields=["year", "month", "account_group"],
                name="fc_imp_yr_mo_grp_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.year}-{self.month:02d} {self.operating_unit_name} "
            f"{self.cost_group_code} {self.amount}"
        )
