"""
History serializers for Broodstock models.

These serializers provide read-only access to historical records
for broodstock models with historical tracking, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.broodstock.models import (
    BroodstockFish,
    FishMovement,
    BreedingPair,
    EggProduction,
    BatchParentage
)


class BroodstockFishHistorySerializer(HistorySerializer):
    """History serializer for BroodstockFish model."""

    class Meta:
        model = BroodstockFish.history.model
        fields = '__all__'


class FishMovementHistorySerializer(HistorySerializer):
    """History serializer for FishMovement model."""

    class Meta:
        model = FishMovement.history.model
        fields = '__all__'


class BreedingPairHistorySerializer(HistorySerializer):
    """History serializer for BreedingPair model."""

    class Meta:
        model = BreedingPair.history.model
        fields = '__all__'


class EggProductionHistorySerializer(HistorySerializer):
    """History serializer for EggProduction model."""

    class Meta:
        model = EggProduction.history.model
        fields = '__all__'


class BatchParentageHistorySerializer(HistorySerializer):
    """History serializer for BatchParentage model."""

    class Meta:
        model = BatchParentage.history.model
        fields = '__all__'
