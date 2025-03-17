"""
Router registration for the batch app API.

This module sets up the DRF router with all viewsets for the batch app.
"""
from rest_framework.routers import DefaultRouter

from apps.batch.api.viewsets import (
    SpeciesViewSet,
    LifeCycleStageViewSet,
    BatchViewSet,
    BatchTransferViewSet,
    MortalityEventViewSet,
    GrowthSampleViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'species', SpeciesViewSet)
router.register(r'lifecycle-stages', LifeCycleStageViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'transfers', BatchTransferViewSet)
router.register(r'mortality-events', MortalityEventViewSet)
router.register(r'growth-samples', GrowthSampleViewSet)

# The API URLs are determined automatically by the router
urlpatterns = router.urls
