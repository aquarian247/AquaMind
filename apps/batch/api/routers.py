"""
Router registration for the batch app API.

This module sets up the DRF router with all viewsets for the batch app.
"""
from rest_framework.routers import DefaultRouter

# Import viewsets from modular structure
from .viewsets import (
    SpeciesViewSet,
    LifeCycleStageViewSet,
    BatchViewSet,
    BatchContainerAssignmentViewSet,
    BatchCompositionViewSet,
    BatchTransferWorkflowViewSet,
    TransferActionViewSet,
    MortalityEventViewSet,
    GrowthSampleViewSet
)
from .viewsets.history import (
    BatchHistoryViewSet,
    BatchContainerAssignmentHistoryViewSet,
    MortalityEventHistoryViewSet,
    GrowthSampleHistoryViewSet
)
from .viewsets.container_availability import ContainerAvailabilityViewSet
from .viewsets.workflow_creation import BatchCreationWorkflowViewSet
from .viewsets.workflow_creation_action import CreationActionViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'species', SpeciesViewSet, basename='species')
router.register(r'lifecycle-stages', LifeCycleStageViewSet, basename='lifecycle-stage')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'container-assignments', BatchContainerAssignmentViewSet, basename='batch-container-assignment')
router.register(r'batch-compositions', BatchCompositionViewSet, basename='batch-composition')
router.register(r'transfer-workflows', BatchTransferWorkflowViewSet, basename='transfer-workflow')
router.register(r'transfer-actions', TransferActionViewSet, basename='transfer-action')
router.register(r'creation-workflows', BatchCreationWorkflowViewSet, basename='creation-workflow')
router.register(r'creation-actions', CreationActionViewSet, basename='creation-action')
router.register(r'mortality-events', MortalityEventViewSet, basename='mortality-event')
router.register(r'growth-samples', GrowthSampleViewSet, basename='growth-sample')

# Register container availability endpoint
router.register(r'containers/availability', ContainerAvailabilityViewSet, basename='container-availability')

# Register history endpoints
router.register(r'history/batches', BatchHistoryViewSet, basename='batch-history')
router.register(r'history/container-assignments', BatchContainerAssignmentHistoryViewSet, basename='batch-container-assignment-history')
router.register(r'history/mortality-events', MortalityEventHistoryViewSet, basename='mortality-event-history')
router.register(r'history/growth-samples', GrowthSampleHistoryViewSet, basename='growth-sample-history')

# The API URLs are determined automatically by the router
urlpatterns = router.urls
