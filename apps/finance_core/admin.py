"""Admin registrations for finance core."""

from django.contrib import admin

from apps.finance_core.models import (
    Account,
    AccountGroup,
    AllocationRule,
    Budget,
    BudgetEntry,
    CostCenter,
    CostCenterBatchLink,
    CostImportBatch,
    CostImportLine,
    PeriodLock,
    ValuationRun,
)


@admin.register(AccountGroup)
class AccountGroupAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "cost_group", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("code", "name", "cost_group")
    ordering = ("account_type", "code")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "group", "is_active")
    list_filter = ("account_type", "group", "is_active")
    search_fields = ("code", "name")
    ordering = ("account_type", "code")


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "site", "cost_center_type", "is_active")
    list_filter = ("company", "cost_center_type", "is_active")
    search_fields = ("code", "name", "site__site_name")
    ordering = ("company__display_name", "code")


@admin.register(CostCenterBatchLink)
class CostCenterBatchLinkAdmin(admin.ModelAdmin):
    list_display = ("batch", "cost_center", "created_by", "linked_at")
    list_filter = ("cost_center__company",)
    search_fields = ("batch__batch_number", "cost_center__code", "cost_center__name")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "fiscal_year", "status", "version")
    list_filter = ("company", "fiscal_year", "status")
    search_fields = ("name", "company__display_name")
    ordering = ("-fiscal_year", "company__display_name", "name")


@admin.register(BudgetEntry)
class BudgetEntryAdmin(admin.ModelAdmin):
    list_display = ("budget", "month", "account", "cost_center", "amount")
    list_filter = ("budget__company", "budget__fiscal_year", "month")
    search_fields = ("budget__name", "account__code", "cost_center__code")
    ordering = ("budget__fiscal_year", "month", "account__code")


@admin.register(CostImportBatch)
class CostImportBatchAdmin(admin.ModelAdmin):
    list_display = ("import_batch_id", "year", "month", "source_filename", "imported_row_count", "total_amount")
    list_filter = ("year", "month")
    search_fields = ("source_filename", "checksum")
    ordering = ("-created_at",)


@admin.register(CostImportLine)
class CostImportLineAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "operating_unit_name", "cost_group_code", "amount")
    list_filter = ("year", "month", "company", "operating_unit")
    search_fields = ("operating_unit_name", "cost_group_code")
    ordering = ("year", "month", "operating_unit_name")


@admin.register(PeriodLock)
class PeriodLockAdmin(admin.ModelAdmin):
    list_display = ("company", "operating_unit", "year", "month", "is_locked", "version")
    list_filter = ("company", "year", "month", "is_locked")
    search_fields = ("company__display_name", "operating_unit__site_name")
    ordering = ("-year", "-month")


@admin.register(AllocationRule)
class AllocationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "account_group", "cost_center", "effective_from", "effective_to", "is_active")
    list_filter = ("is_active", "effective_from")
    search_fields = ("name", "account_group__code", "cost_center__code")
    ordering = ("-effective_from", "name")


@admin.register(ValuationRun)
class ValuationRunAdmin(admin.ModelAdmin):
    list_display = ("run_id", "company", "operating_unit", "year", "month", "version", "status")
    list_filter = ("company", "year", "month", "status")
    search_fields = ("company__display_name", "operating_unit__site_name")
    ordering = ("-year", "-month", "-version")
