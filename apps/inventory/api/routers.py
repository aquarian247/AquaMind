"""
Router registration for the inventory app API.

This module sets up the DRF router with all viewsets for the inventory app.
"""
from rest_framework.routers import DefaultRouter

from apps.inventory.api.viewsets import (
    FeedViewSet,
    FeedPurchaseViewSet,
    FeedStockViewSet,
    FeedingEventViewSet,
    BatchFeedingSummaryViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'feeds', FeedViewSet)
router.register(r'feed-purchases', FeedPurchaseViewSet)
router.register(r'feed-stocks', FeedStockViewSet)
router.register(r'feeding-events', FeedingEventViewSet)
router.register(r'batch-feeding-summaries', BatchFeedingSummaryViewSet)

# The API URLs are determined automatically by the router
urlpatterns = router.urls
