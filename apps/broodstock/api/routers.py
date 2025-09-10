"""
Router configuration for the Broodstock Management API.

This module registers all broodstock-related ViewSets with the DRF router.
"""

from rest_framework.routers import DefaultRouter

from apps.broodstock.views import (
    MaintenanceTaskViewSet,
    BroodstockFishViewSet,
    FishMovementViewSet,
    BreedingPlanViewSet,
    BreedingTraitPriorityViewSet,
    BreedingPairViewSet,
    EggSupplierViewSet,
    EggProductionViewSet,
    ExternalEggBatchViewSet,
    BatchParentageViewSet
)
from .viewsets.history import (
    BroodstockFishHistoryViewSet,
    FishMovementHistoryViewSet,
    BreedingPairHistoryViewSet,
    EggProductionHistoryViewSet,
    BatchParentageHistoryViewSet
)

# Create router instance
router = DefaultRouter()

# Register ViewSets
router.register(r'maintenance-tasks', MaintenanceTaskViewSet, basename='maintenance-task')
router.register(r'fish', BroodstockFishViewSet, basename='broodstock-fish')
router.register(r'fish-movements', FishMovementViewSet, basename='fish-movement')
router.register(r'breeding-plans', BreedingPlanViewSet, basename='breeding-plan')
router.register(r'trait-priorities', BreedingTraitPriorityViewSet, basename='breeding-trait-priority')
router.register(r'breeding-pairs', BreedingPairViewSet, basename='breeding-pair')
router.register(r'egg-suppliers', EggSupplierViewSet, basename='egg-supplier')
router.register(r'egg-productions', EggProductionViewSet, basename='egg-production')
router.register(r'external-egg-batches', ExternalEggBatchViewSet, basename='external-egg-batch')
router.register(r'batch-parentages', BatchParentageViewSet, basename='batch-parentage')

# Register history endpoints
router.register(r'history/fish', BroodstockFishHistoryViewSet, basename='broodstock-fish-history')
router.register(r'history/fish-movements', FishMovementHistoryViewSet, basename='fish-movement-history')
router.register(r'history/breeding-pairs', BreedingPairHistoryViewSet, basename='breeding-pair-history')
router.register(r'history/egg-productions', EggProductionHistoryViewSet, basename='egg-production-history')
router.register(r'history/batch-parentages', BatchParentageHistoryViewSet, basename='batch-parentage-history')

# Export router
__all__ = ['router'] 