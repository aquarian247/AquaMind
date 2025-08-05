"""
Router registration for the batch app API.

This module sets up the DRF router with all viewsets for the batch app.
"""
from rest_framework.routers import DefaultRouter

from apps.batch.api.viewsets import (
    SpeciesViewSet,
    LifeCycleStageViewSet,
    BatchViewSet,
    BatchContainerAssignmentViewSet,
    BatchCompositionViewSet,
    BatchTransferViewSet,
    MortalityEventViewSet,
    GrowthSampleViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'species', SpeciesViewSet, basename='species')
router.register(r'lifecycle-stages', LifeCycleStageViewSet, basename='lifecycle-stage')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'container-assignments', BatchContainerAssignmentViewSet, basename='batch-container-assignment')
router.register(r'batch-compositions', BatchCompositionViewSet, basename='batch-composition')
router.register(r'transfers', BatchTransferViewSet, basename='batch-transfer')
router.register(r'mortality-events', MortalityEventViewSet, basename='mortality-event')
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-sample')

# The API URLs are determined automatically by the router
urlpatterns = router.urls
