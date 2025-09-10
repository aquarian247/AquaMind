"""
Router registration for the batch app API.

This module sets up the DRF router with all viewsets for the batch app.
"""
from rest_framework.routers import DefaultRouter

# Import main viewsets directly from the viewsets.py file
import importlib.util
import os

# Load the viewsets.py file directly
viewsets_path = os.path.join(os.path.dirname(__file__), 'viewsets.py')
spec = importlib.util.spec_from_file_location("viewsets_module", viewsets_path)
viewsets_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewsets_module)

SpeciesViewSet = viewsets_module.SpeciesViewSet
BatchViewSet = viewsets_module.BatchViewSet
BatchContainerAssignmentViewSet = viewsets_module.BatchContainerAssignmentViewSet
BatchCompositionViewSet = viewsets_module.BatchCompositionViewSet
BatchTransferViewSet = viewsets_module.BatchTransferViewSet
MortalityEventViewSet = viewsets_module.MortalityEventViewSet
GrowthSampleViewSet = viewsets_module.GrowthSampleViewSet
from .viewsets.history import (
    BatchHistoryViewSet,
    BatchContainerAssignmentHistoryViewSet,
    BatchTransferHistoryViewSet,
    MortalityEventHistoryViewSet,
    GrowthSampleHistoryViewSet
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'species', SpeciesViewSet, basename='species')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'container-assignments', BatchContainerAssignmentViewSet, basename='batch-container-assignment')
router.register(r'batch-compositions', BatchCompositionViewSet, basename='batch-composition')
router.register(r'transfers', BatchTransferViewSet, basename='batch-transfer')
router.register(r'mortality-events', MortalityEventViewSet, basename='mortality-event')
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-sample')

# Register history endpoints
router.register(r'history/batches', BatchHistoryViewSet, basename='batch-history')
router.register(r'history/container-assignments', BatchContainerAssignmentHistoryViewSet, basename='batch-container-assignment-history')
router.register(r'history/transfers', BatchTransferHistoryViewSet, basename='batch-transfer-history')
router.register(r'history/mortality-events', MortalityEventHistoryViewSet, basename='mortality-event-history')
router.register(r'history/growth-samples', GrowthSampleHistoryViewSet, basename='growth-sample-history')

# The API URLs are determined automatically by the router
urlpatterns = router.urls
