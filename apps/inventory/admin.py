from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from apps.inventory.models import (
    Feed, FeedPurchase, FeedStock, FeedingEvent, BatchFeedingSummary
)


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'brand', 'size_category', 
        'protein_percentage', 'fat_percentage'
    ]
    list_filter = [
        'size_category', 'is_active', 'brand'
    ]
    search_fields = [
        'name', 'brand', 'description'
    ]


@admin.register(FeedPurchase)
class FeedPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'feed', 'quantity_kg', 'cost_per_kg', 
        'supplier', 'purchase_date', 'expiry_date'
    ]
    list_filter = [
        'feed', 'supplier', 'purchase_date'
    ]
    search_fields = [
        'supplier', 'batch_number', 'notes'
    ]


@admin.register(FeedStock)
class FeedStockAdmin(SimpleHistoryAdmin):
    list_display = [
        'feed', 'feed_container', 
        'current_quantity_kg', 'reorder_threshold_kg', 'updated_at'
    ]
    list_filter = [
        'feed', 'feed_container'
    ]
    search_fields = [
        'feed__name', 'feed_container__name'
    ]


@admin.register(FeedingEvent)
class FeedingEventAdmin(admin.ModelAdmin):
    list_display = [
        'batch', 'feed', 'feeding_date', 'feeding_time', 'amount_kg', 'method'
    ]
    list_filter = [
        'batch', 'feed', 'feeding_date', 'method'
    ]
    search_fields = [
        'batch__name', 'feed__name', 'notes'
    ]


@admin.register(BatchFeedingSummary)
class BatchFeedingSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'batch', 'period_start', 'period_end', 'total_feed_kg',
        'fcr', 'average_feeding_percentage'
    ]
    list_filter = [
        'batch', 'period_start', 'period_end'
    ]
    search_fields = ['batch__name']
