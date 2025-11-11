"""Finance models for dimensions and projections."""

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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
    """
    Policy enabling intercompany pricing between companies.
    
    Supports two pricing models:
    - Grade-based: For harvest transactions (uses product_grade)
    - Lifecycle-based: For transfer workflows (uses lifecycle_stage)
    """

    class Method(models.TextChoices):
        MARKET = "market", "Market"
        COST_PLUS = "cost_plus", "Cost Plus"
        STANDARD = "standard", "Standard"

    class PricingBasis(models.TextChoices):
        GRADE = "grade", "Product Grade (Harvest)"
        LIFECYCLE = "lifecycle", "Lifecycle Stage (Transfer)"
        EGG_DELIVERY = "egg_delivery", "Egg Delivery (Creation)"

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
    
    # Pricing Basis Selection
    pricing_basis = models.CharField(
        max_length=20,
        choices=PricingBasis.choices,
        default=PricingBasis.GRADE,
        help_text=(
            "Whether this policy is for harvest (grade) or "
            "transfer (lifecycle)"
        ),
    )
    
    # Grade-based pricing (for harvest transactions)
    product_grade = models.ForeignKey(
        "harvest.ProductGrade",
        on_delete=models.PROTECT,
        related_name="intercompany_policies",
        null=True,
        blank=True,
        help_text="Required if pricing_basis=GRADE",
    )
    
    # Lifecycle-based pricing (for transfer workflows)
    lifecycle_stage = models.ForeignKey(
        "batch.LifeCycleStage",
        on_delete=models.PROTECT,
        related_name="intercompany_policies",
        null=True,
        blank=True,
        help_text="Required if pricing_basis=LIFECYCLE",
    )
    
    # Pricing Method
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.STANDARD,
    )
    markup_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Markup percentage for COST_PLUS method",
    )
    
    # Standard pricing (fixed price per kg)
    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed price per kg for STANDARD method",
    )
    
    # Egg delivery pricing (for batch creation workflows)
    price_per_thousand_eggs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed price per 1000 eggs for EGG_DELIVERY pricing_basis",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # Grade-based policies: unique by companies + product_grade
            models.UniqueConstraint(
                fields=("from_company", "to_company", "product_grade"),
                name="intercompany_policy_company_grade_uniq",
                condition=models.Q(pricing_basis="grade", product_grade__isnull=False),
            ),
            # Lifecycle-based policies: unique by companies + lifecycle_stage
            models.UniqueConstraint(
                fields=("from_company", "to_company", "lifecycle_stage"),
                name="intercompany_policy_company_lifecycle_uniq",
                condition=models.Q(pricing_basis="lifecycle", lifecycle_stage__isnull=False),
            ),
        ]
        ordering = (
            "from_company__geography__name",
            "from_company__subsidiary",
            "pricing_basis",
        )

    def clean(self):
        """Validate that pricing_basis matches reference field."""
        super().clean()
        self._validate_pricing_basis()
        self._validate_pricing_method()

    def _validate_pricing_basis(self):
        """Validate pricing_basis field consistency."""
        is_grade_basis = self.pricing_basis == self.PricingBasis.GRADE
        is_lifecycle_basis = (
            self.pricing_basis == self.PricingBasis.LIFECYCLE
        )
        is_egg_delivery_basis = (
            self.pricing_basis == self.PricingBasis.EGG_DELIVERY
        )

        if is_grade_basis:
            self._validate_grade_pricing()
        elif is_lifecycle_basis:
            self._validate_lifecycle_pricing()
        elif is_egg_delivery_basis:
            self._validate_egg_delivery_pricing()

    def _validate_grade_pricing(self):
        """Validate grade-based pricing fields."""
        if not self.product_grade:
            raise ValidationError({
                'product_grade': (
                    'Product grade is required when pricing_basis '
                    'is GRADE'
                )
            })
        if self.lifecycle_stage:
            raise ValidationError({
                'lifecycle_stage': (
                    'Lifecycle stage should not be set when '
                    'pricing_basis is GRADE'
                )
            })

    def _validate_lifecycle_pricing(self):
        """Validate lifecycle-based pricing fields."""
        if not self.lifecycle_stage:
            raise ValidationError({
                'lifecycle_stage': (
                    'Lifecycle stage is required when pricing_basis '
                    'is LIFECYCLE'
                )
            })
        if self.product_grade:
            raise ValidationError({
                'product_grade': (
                    'Product grade should not be set when '
                    'pricing_basis is LIFECYCLE'
                )
            })
    
    def _validate_egg_delivery_pricing(self):
        """Validate egg delivery pricing fields."""
        if not self.price_per_thousand_eggs:
            raise ValidationError({
                'price_per_thousand_eggs': (
                    'Price per thousand eggs is required when '
                    'pricing_basis is EGG_DELIVERY'
                )
            })
        if self.product_grade:
            raise ValidationError({
                'product_grade': (
                    'Product grade should not be set when '
                    'pricing_basis is EGG_DELIVERY'
                )
            })
        if self.lifecycle_stage:
            raise ValidationError({
                'lifecycle_stage': (
                    'Lifecycle stage should not be set when '
                    'pricing_basis is EGG_DELIVERY'
                )
            })

    def _validate_pricing_method(self):
        """Validate pricing method requirements."""
        # STANDARD method requires price_per_kg for lifecycle pricing
        # Grade-based pricing can use MARKET/COST_PLUS methods
        if self.method == self.Method.STANDARD:
            if (self.pricing_basis == self.PricingBasis.LIFECYCLE and
                    not self.price_per_kg):
                raise ValidationError({
                    'price_per_kg': (
                        'Price per kg is required for STANDARD method '
                        'with lifecycle-based pricing'
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.pricing_basis == self.PricingBasis.GRADE:
            ref = f"grade={self.product_grade_id}"
        elif self.pricing_basis == self.PricingBasis.LIFECYCLE:
            ref = f"lifecycle={self.lifecycle_stage_id}"
        elif self.pricing_basis == self.PricingBasis.EGG_DELIVERY:
            ref = "egg_delivery"
        else:
            ref = "unknown"
        
        return (
            f"IntercompanyPolicy({self.from_company_id}->{self.to_company_id} "
            f"{ref})"
        )


class IntercompanyTransaction(models.Model):
    """
    Intercompany transaction with polymorphic source support.
    
    Can be triggered by:
    - HarvestEvent (Farming → Harvest) - grade-based pricing
    - BatchTransferWorkflow (Freshwater → Farming) - lifecycle-based pricing
    
    State flow: PENDING → POSTED → EXPORTED
    """

    class State(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        POSTED = "posted", "Posted (Approved)"
        EXPORTED = "exported", "Exported to NAV"

    tx_id = models.BigAutoField(primary_key=True)
    
    # Polymorphic source (HarvestEvent OR BatchTransferWorkflow)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=models.Q(
            app_label='harvest', model='harvestevent'
        ) | models.Q(
            app_label='batch', model='batchtransferworkflow'
        ),
        help_text=(
            "Source model type (HarvestEvent or BatchTransferWorkflow)"
        ),
    )
    object_id = models.PositiveIntegerField(
        help_text="Source object ID",
    )
    source = GenericForeignKey('content_type', 'object_id')
    
    # Legacy field for backward compatibility (will be removed after migration)
    event = models.ForeignKey(
        "harvest.HarvestEvent",
        on_delete=models.PROTECT,
        related_name="intercompany_transactions",
        null=True,
        blank=True,
        help_text="DEPRECATED: Use polymorphic source instead",
    )
    
    # Pricing policy
    policy = models.ForeignKey(
        IntercompanyPolicy,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    
    # Transaction details
    posting_date = models.DateField(db_index=True)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, null=True, blank=True)
    
    # State machine
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PENDING,
    )
    
    # Approval tracking
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_intercompany_transactions",
        help_text=(
            "Manager who approved this transaction (PENDING → POSTED)"
        ),
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the transaction was approved",
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            # Legacy constraint (will be removed)
            models.UniqueConstraint(
                fields=("event", "policy"),
                name="intercompany_transaction_event_policy_uniq",
                condition=models.Q(event__isnull=False),
            ),
            # New polymorphic constraint
            models.UniqueConstraint(
                fields=("content_type", "object_id", "policy"),
                name="intercompany_transaction_source_policy_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("state", "posting_date"),
                name="ix_interco_state_posting",
            ),
            models.Index(
                fields=("content_type", "object_id"),
                name="ix_interco_ct_objid",
            ),
        ]
        ordering = ("-posting_date", "tx_id")
    
    @property
    def source_type(self) -> str:
        """Return human-readable source type."""
        if self.content_type:
            return self.content_type.model
        elif self.event:
            return 'harvestevent'
        return 'unknown'
    
    @property
    def source_display(self) -> str:
        """Return human-readable source identifier."""
        if self.content_type and self.content_type.model == 'batchtransferworkflow':
            workflow = self.source
            if workflow:
                return f"Transfer {workflow.workflow_number}"
        elif self.event:
            return f"Harvest Event {self.event_id}"
        return f"Unknown source {self.object_id}"
    
    def approve(self, user: User) -> None:
        """
        Approve this transaction (PENDING → POSTED).

        Args:
            user: Manager approving the transaction

        Raises:
            ValidationError: If transaction is not in PENDING state
        """
        from django.utils import timezone

        if self.state != self.State.PENDING:
            raise ValidationError(
                f"Cannot approve transaction in {self.state} state. "
                "Only PENDING transactions can be approved."
            )

        self.state = self.State.POSTED
        self.approved_by = user
        self.approval_date = timezone.now()
        self.save(update_fields=[
            'state', 'approved_by', 'approval_date', 'updated_at'
        ])

    def __str__(self) -> str:
        return (
            f"IntercompanyTransaction(tx_id={self.tx_id}, "
            f"source={self.source_display})"
        )


class NavExportBatch(models.Model):
    """Container for NAV journal exports grouped by company and date range."""

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        EXPORTED = "exported", "Exported"

    batch_id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="nav_export_batches",
    )
    date_from = models.DateField()
    date_to = models.DateField()
    posting_date = models.DateField()
    currency = models.CharField(max_length=3, null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("company", "date_from", "date_to"),
                name="nav_export_batch_company_daterange_uniq",
            )
        ]
        ordering = ("-created_at", "-batch_id")

    def __str__(self) -> str:
        return f"NavExportBatch(id={self.batch_id}, company={self.company_id})"


class NavExportLine(models.Model):
    """Immutable NAV journal line linked to a specific intercompany transaction."""

    line_id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(
        NavExportBatch,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    transaction = models.ForeignKey(
        IntercompanyTransaction,
        on_delete=models.PROTECT,
        related_name="nav_export_lines",
    )
    document_no = models.CharField(max_length=32)
    account_no = models.CharField(max_length=50)
    balancing_account_no = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=255)
    dim_company = models.ForeignKey(
        DimCompany,
        on_delete=models.PROTECT,
        related_name="nav_export_lines",
    )
    dim_site = models.ForeignKey(
        DimSite,
        on_delete=models.PROTECT,
        related_name="nav_export_lines",
    )
    product_grade = models.ForeignKey(
        "harvest.ProductGrade",
        on_delete=models.PROTECT,
        related_name="nav_export_lines",
    )
    batch_id_int = models.PositiveIntegerField()

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "document_no"),
                name="nav_export_line_batch_document_no_uniq",
            )
        ]
        ordering = ("line_id",)

    def __str__(self) -> str:
        return f"NavExportLine(batch={self.batch_id}, document={self.document_no})"
