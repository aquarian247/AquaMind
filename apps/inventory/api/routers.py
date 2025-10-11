"""
Router registration for the inventory app API.

This module sets up the DRF router with all viewsets for the inventory app.
"""
from rest_framework.routers import DefaultRouter

from apps.inventory.api.viewsets import (
    FeedViewSet,
    FeedPurchaseViewSet,
    FeedingEventViewSet,
    BatchFeedingSummaryViewSet,
    FeedContainerStockViewSet
)
from apps.inventory.api.viewsets.history import (
    FeedingEventHistoryViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'feeds', FeedViewSet, basename='feed')
router.register(r'feed-purchases', FeedPurchaseViewSet, basename='feed-purchase')
router.register(r'feeding-events', FeedingEventViewSet, basename='feeding-event')
router.register(r'batch-feeding-summaries', BatchFeedingSummaryViewSet, basename='batch-feeding-summary')
router.register(r'feed-container-stock', FeedContainerStockViewSet, basename='feed-container-stock')

# Register history endpoints
router.register(r'history/feeding-events', FeedingEventHistoryViewSet, basename='feeding-event-history')

# The API URLs are determined automatically by the router
urlpatterns = router.urls
