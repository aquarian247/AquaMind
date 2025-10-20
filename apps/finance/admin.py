"""Admin registrations for finance models."""

from django.contrib import admin

from apps.finance.models import (
    DimCompany,
    DimSite,
    FactHarvest,
    IntercompanyPolicy,
    IntercompanyTransaction,
    NavExportBatch,
    NavExportLine,
)


@admin.register(DimCompany)
class DimCompanyAdmin(admin.ModelAdmin):
    list_display = (
        "company_id",
        "display_name",
        "geography",
        "subsidiary",
        "currency",
        "nav_company_code",
    )
    list_filter = ("geography", "subsidiary")
    search_fields = ("display_name", "nav_company_code")
    ordering = ("geography__name", "subsidiary")


@admin.register(DimSite)
class DimSiteAdmin(admin.ModelAdmin):
    list_display = (
        "site_id",
        "site_name",
        "company",
        "source_model",
        "source_pk",
    )
    list_filter = ("source_model", "company__geography", "company__subsidiary")
    search_fields = ("site_name",)
    ordering = ("site_name",)


@admin.register(FactHarvest)
class FactHarvestAdmin(admin.ModelAdmin):
    list_display = (
        "fact_id",
        "event",
        "lot",
        "event_date",
        "dim_company",
        "dim_site",
        "product_grade",
        "quantity_kg",
        "unit_count",
    )
    list_filter = (
        "dim_company__geography",
        "dim_company__subsidiary",
        "product_grade",
    )
    search_fields = ("lot__event__batch__batch_number", "dim_site__site_name")
    ordering = ("-event_date",)


@admin.register(IntercompanyPolicy)
class IntercompanyPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "policy_id",
        "pricing_basis",
        "from_company",
        "to_company",
        "product_grade",
        "lifecycle_stage",
        "method",
        "price_per_kg",
        "markup_percent",
    )
    list_filter = (
        "pricing_basis",
        "method",
        "from_company__geography",
        "to_company__geography",
    )
    search_fields = (
        "from_company__display_name",
        "to_company__display_name",
        "product_grade__code",
        "lifecycle_stage__stage_name",
    )
    ordering = ("from_company__geography__name", "pricing_basis")
    fieldsets = (
        (
            "Companies",
            {
                "fields": ("from_company", "to_company"),
            },
        ),
        (
            "Pricing Configuration",
            {
                "fields": (
                    "pricing_basis",
                    "product_grade",
                    "lifecycle_stage",
                    "method",
                    "price_per_kg",
                    "markup_percent",
                ),
                "description": (
                    "Use product_grade for harvest transactions "
                    "or lifecycle_stage for transfer workflows"
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(IntercompanyTransaction)
class IntercompanyTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "tx_id",
        "source_type",
        "posting_date",
        "state",
        "amount",
        "currency",
        "approved_by",
    )
    list_filter = ("state", "posting_date", "content_type")
    search_fields = (
        "policy__from_company__display_name",
        "policy__to_company__display_name",
        "approved_by__username",
    )
    ordering = ("-posting_date",)
    fieldsets = (
        (
            "Source",
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "source_display",
                    "event",
                ),
                "description": (
                    "Polymorphic source: HarvestEvent or "
                    "BatchTransferWorkflow. "
                    "Legacy event field kept for backward compatibility."
                ),
            },
        ),
        (
            "Transaction Details",
            {
                "fields": (
                    "policy",
                    "posting_date",
                    "amount",
                    "currency",
                ),
            },
        ),
        (
            "State & Approval",
            {
                "fields": (
                    "state",
                    "approved_by",
                    "approval_date",
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = (
        "source_display",
        "created_at",
        "updated_at",
    )


@admin.register(NavExportBatch)
class NavExportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "batch_id",
        "company",
        "date_from",
        "date_to",
        "posting_date",
        "currency",
        "state",
    )
    list_filter = ("state", "company__geography", "company__subsidiary")
    search_fields = ("company__display_name",)
    ordering = ("-created_at",)


@admin.register(NavExportLine)
class NavExportLineAdmin(admin.ModelAdmin):
    list_display = (
        "line_id",
        "batch",
        "transaction",
        "document_no",
        "account_no",
        "amount",
    )
    list_filter = ("batch__company__display_name", "product_grade")
    search_fields = ("document_no", "transaction__tx_id")
    ordering = ("line_id",)
