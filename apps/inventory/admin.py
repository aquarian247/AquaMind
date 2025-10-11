from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from apps.inventory.models import (
    Feed, FeedPurchase, FeedingEvent, BatchFeedingSummary,
    ContainerFeedingSummary, FeedContainerStock
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
class FeedPurchaseAdmin(SimpleHistoryAdmin):
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


@admin.register(FeedingEvent)
class FeedingEventAdmin(SimpleHistoryAdmin):
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
class BatchFeedingSummaryAdmin(SimpleHistoryAdmin):
    list_display = [
        'batch', 'period_start', 'period_end', 'total_feed_kg',
        'fcr', 'average_feeding_percentage'
    ]
    list_filter = [
        'batch', 'period_start', 'period_end'
    ]
    search_fields = ['batch__name']


@admin.register(ContainerFeedingSummary)
class ContainerFeedingSummaryAdmin(SimpleHistoryAdmin):
    list_display = [
        'container_assignment', 'period_start', 'period_end', 'total_feed_kg',
        'fcr', 'growth_kg', 'confidence_level'
    ]
    list_filter = [
        'container_assignment', 'period_start', 'period_end', 'confidence_level'
    ]
    search_fields = ['container_assignment__container__name', 'batch__name']


@admin.register(FeedContainerStock)
class FeedContainerStockAdmin(SimpleHistoryAdmin):
    list_display = [
        'feed_container', 'feed_purchase', 'quantity_kg',
        'entry_date', 'created_at'
    ]
    list_filter = [
        'feed_container', 'feed_purchase', 'entry_date'
    ]
    search_fields = ['feed_container__name', 'feed_purchase__feed__name', 'feed_purchase__batch_number']
