"""
History viewsets for Broodstock models.

These viewsets provide read-only access to historical records
for broodstock models with historical tracking, filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.broodstock.models import (
    BroodstockFish,
    FishMovement,
    BreedingPair,
    EggProduction,
    BatchParentage
)
from apps.broodstock.api.serializers.history import (
    BroodstockFishHistorySerializer,
    FishMovementHistorySerializer,
    BreedingPairHistorySerializer,
    EggProductionHistorySerializer,
    BatchParentageHistorySerializer
)
from apps.broodstock.api.filters.history import (
    BroodstockFishHistoryFilter,
    FishMovementHistoryFilter,
    BreedingPairHistoryFilter,
    EggProductionHistoryFilter,
    BatchParentageHistoryFilter
)


class BroodstockFishHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BroodstockFish historical records."""
    queryset = BroodstockFish.history.all()
    serializer_class = BroodstockFishHistorySerializer
    filterset_class = BroodstockFishHistoryFilter


class FishMovementHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for FishMovement historical records."""
    queryset = FishMovement.history.all()
    serializer_class = FishMovementHistorySerializer
    filterset_class = FishMovementHistoryFilter


class BreedingPairHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BreedingPair historical records."""
    queryset = BreedingPair.history.all()
    serializer_class = BreedingPairHistorySerializer
    filterset_class = BreedingPairHistoryFilter


class EggProductionHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for EggProduction historical records."""
    queryset = EggProduction.history.all()
    serializer_class = EggProductionHistorySerializer
    filterset_class = EggProductionHistoryFilter


class BatchParentageHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for BatchParentage historical records."""
    queryset = BatchParentage.history.all()
    serializer_class = BatchParentageHistorySerializer
    filterset_class = BatchParentageHistoryFilter
