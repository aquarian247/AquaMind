"""Admin registrations for harvest models."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.harvest.models import HarvestEvent, HarvestLot, HarvestWaste, ProductGrade


@admin.register(ProductGrade)
class ProductGradeAdmin(admin.ModelAdmin):
    """Admin configuration for product grades."""

    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(HarvestEvent)
class HarvestEventAdmin(SimpleHistoryAdmin):
    """Admin configuration for harvest events."""

    list_display = (
        "event_date",
        "batch",
        "assignment",
        "dest_geography",
        "dest_subsidiary",
        "document_ref",
    )
    list_filter = ("event_date", "batch", "dest_geography", "dest_subsidiary")
    search_fields = ("document_ref", "batch__batch_number", "assignment__id")
    date_hierarchy = "event_date"
    readonly_fields = ("created_at", "updated_at")


@admin.register(HarvestLot)
class HarvestLotAdmin(SimpleHistoryAdmin):
    """Admin configuration for harvest lots."""

    list_display = (
        "event",
        "product_grade",
        "live_weight_kg",
        "gutted_weight_kg",
        "fillet_weight_kg",
        "unit_count",
    )
    list_filter = ("product_grade",)
    search_fields = ("event__document_ref", "product_grade__code")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HarvestWaste)
class HarvestWasteAdmin(SimpleHistoryAdmin):
    """Admin configuration for harvest waste entries."""

    list_display = ("event", "category", "weight_kg")
    list_filter = ("category",)
    search_fields = ("event__document_ref", "category")
    readonly_fields = ("created_at", "updated_at")
