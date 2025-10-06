"""Admin registrations for finance dimension models."""

from django.contrib import admin

from apps.finance.models import DimCompany, DimSite


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
