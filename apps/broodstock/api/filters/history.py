"""
History filters for Broodstock models.

These filters provide date range, user, and change type filtering
for historical records across broodstock models with historical tracking.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.broodstock.models import (
    BroodstockFish,
    FishMovement,
    BreedingPair,
    EggProduction,
    BatchParentage
)


class BroodstockFishHistoryFilter(HistoryFilter):
    """Filter class for BroodstockFish historical records."""

    class Meta:
        model = BroodstockFish.history.model
        fields = ['container', 'health_status']


class FishMovementHistoryFilter(HistoryFilter):
    """Filter class for FishMovement historical records."""

    class Meta:
        model = FishMovement.history.model
        fields = ['fish', 'from_container', 'to_container', 'moved_by']


class BreedingPairHistoryFilter(HistoryFilter):
    """Filter class for BreedingPair historical records."""

    class Meta:
        model = BreedingPair.history.model
        fields = ['plan', 'male_fish', 'female_fish']


class EggProductionHistoryFilter(HistoryFilter):
    """Filter class for EggProduction historical records."""

    class Meta:
        model = EggProduction.history.model
        fields = ['source_type', 'pair', 'destination_station']


class BatchParentageHistoryFilter(HistoryFilter):
    """Filter class for BatchParentage historical records."""

    class Meta:
        model = BatchParentage.history.model
        fields = ['batch', 'egg_production']
