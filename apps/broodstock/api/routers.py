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

# Create router instance
router = DefaultRouter()

# Register ViewSets
router.register(r'maintenance-tasks', MaintenanceTaskViewSet, basename='maintenancetask')
router.register(r'fish', BroodstockFishViewSet, basename='broodstockfish')
router.register(r'fish-movements', FishMovementViewSet, basename='fishmovement')
router.register(r'breeding-plans', BreedingPlanViewSet, basename='breedingplan')
router.register(r'trait-priorities', BreedingTraitPriorityViewSet, basename='breedingtraitpriority')
router.register(r'breeding-pairs', BreedingPairViewSet, basename='breedingpair')
router.register(r'egg-suppliers', EggSupplierViewSet, basename='eggsupplier')
router.register(r'egg-productions', EggProductionViewSet, basename='eggproduction')
router.register(r'external-egg-batches', ExternalEggBatchViewSet, basename='externaleggbatch')
router.register(r'batch-parentages', BatchParentageViewSet, basename='batchparentage')

# Export router
__all__ = ['router'] 