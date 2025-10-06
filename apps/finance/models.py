"""Finance models for dimensions and projections."""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.geography import Geography
from apps.users.models import Subsidiary


class DimCompany(models.Model):
    """Finance dimension for legal entities by geography and subsidiary."""

    company_id = models.BigAutoField(primary_key=True)
    geography = models.ForeignKey(
        Geography,
        on_delete=models.PROTECT,
        related_name="finance_companies",
    )
    subsidiary = models.CharField(max_length=3, choices=Subsidiary.choices)
    display_name = models.CharField(max_length=150)
    currency = models.CharField(max_length=3, blank=True, null=True)
    nav_company_code = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["geography", "subsidiary"],
                name="dim_company_geography_subsidiary_uniq",
            )
        ]
        ordering = ("geography__name", "subsidiary")
        verbose_name = "Finance Company"
        verbose_name_plural = "Finance Companies"

    def __str__(self) -> str:
        return self.display_name


class DimSite(models.Model):
    """Finance dimension for operational sites mapped to companies."""

    class SourceModel(models.TextChoices):
        STATION = "station", "Freshwater Station"
        AREA = "area", "Area"

    site_id = models.BigAutoField(primary_key=True)
    source_model = models.CharField(max_length=16, choices=SourceModel.choices)
    source_pk = models.PositiveIntegerField()
    company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="sites",
    )
    site_name = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_model", "source_pk"],
                name="dim_site_source_model_pk_uniq",
            )
        ]
        ordering = ("site_name",)
        verbose_name = "Finance Site"
        verbose_name_plural = "Finance Sites"

    def __str__(self) -> str:
        return self.site_name


class FactHarvest(models.Model):
    """Projected harvest facts derived from operational lots."""

    fact_id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        "harvest.HarvestEvent",
        on_delete=models.PROTECT,
        related_name="finance_facts",
    )
    lot = models.OneToOneField(
        "harvest.HarvestLot",
        on_delete=models.PROTECT,
        related_name="finance_fact",
    )
    event_date = models.DateTimeField(db_index=True)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=3)
    unit_count = models.PositiveIntegerField()
    product_grade = models.ForeignKey(
        "harvest.ProductGrade",
        on_delete=models.PROTECT,
        related_name="finance_facts",
    )
    dim_company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="fact_harvests",
    )
    dim_site = models.ForeignKey(
        DimSite,
        on_delete=models.PROTECT,
        related_name="fact_harvests",
    )
    dim_batch_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("-event_date", "fact_id")
        indexes = [
            models.Index(fields=("event_date",), name="ix_fact_harvest_event_date"),
            models.Index(
                fields=("dim_company", "product_grade"),
                name="ix_fact_harvest_company_grade",
            ),
        ]

    def __str__(self) -> str:
        return f"FactHarvest(lot={self.lot_id}, event={self.event_id})"


class IntercompanyPolicy(models.Model):
    """Policy enabling intercompany pricing between companies for a grade."""

    class Method(models.TextChoices):
        MARKET = "market", "Market"
        COST_PLUS = "cost_plus", "Cost Plus"
        STANDARD = "standard", "Standard"

    policy_id = models.BigAutoField(primary_key=True)
    from_company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="policies_outbound",
    )
    to_company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="policies_inbound",
    )
    product_grade = models.ForeignKey(
        "harvest.ProductGrade",
        on_delete=models.PROTECT,
        related_name="intercompany_policies",
    )
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.MARKET,
    )
    markup_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("from_company", "to_company", "product_grade"),
                name="intercompany_policy_company_grade_uniq",
            )
        ]
        ordering = (
            "from_company__geography__name",
            "from_company__subsidiary",
            "product_grade__code",
        )

    def __str__(self) -> str:
        return (
            f"IntercompanyPolicy({self.from_company_id}->{self.to_company_id} "
            f"grade={self.product_grade_id})"
        )


class IntercompanyTransaction(models.Model):
    """Pending intercompany transaction detected during projection."""

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        EXPORTED = "exported", "Exported"
        POSTED = "posted", "Posted"

    tx_id = models.BigAutoField(primary_key=True)
    event = models.ForeignKey(
        "harvest.HarvestEvent",
        on_delete=models.PROTECT,
        related_name="intercompany_transactions",
    )
    policy = models.ForeignKey(
        IntercompanyPolicy,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    posting_date = models.DateField(db_index=True)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event", "policy"),
                name="intercompany_transaction_event_policy_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=("state", "posting_date"),
                name="ix_interco_state_posting",
            )
        ]
        ordering = ("-posting_date", "tx_id")

    def __str__(self) -> str:
        return f"IntercompanyTransaction(event={self.event_id}, policy={self.policy_id})"
