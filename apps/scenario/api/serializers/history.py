"""
History serializers for Scenario models.

These serializers provide read-only access to historical records
for scenario models with historical tracking, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.scenario.models import (
    TGCModel,
    FCRModel,
    MortalityModel,
    Scenario,
    ScenarioModelChange
)


class TGCModelHistorySerializer(HistorySerializer):
    """History serializer for TGCModel model."""

    class Meta:
        model = TGCModel.history.model
        fields = '__all__'


class FCRModelHistorySerializer(HistorySerializer):
    """History serializer for FCRModel model."""

    class Meta:
        model = FCRModel.history.model
        fields = '__all__'


class MortalityModelHistorySerializer(HistorySerializer):
    """History serializer for MortalityModel model."""

    class Meta:
        model = MortalityModel.history.model
        fields = '__all__'


class ScenarioHistorySerializer(HistorySerializer):
    """History serializer for Scenario model."""

    class Meta:
        model = Scenario.history.model
        fields = '__all__'


class ScenarioModelChangeHistorySerializer(HistorySerializer):
    """History serializer for ScenarioModelChange model."""

    class Meta:
        model = ScenarioModelChange.history.model
        fields = '__all__'
