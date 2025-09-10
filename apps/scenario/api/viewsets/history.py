"""
History viewsets for Scenario models.

These viewsets provide read-only access to historical records
for scenario models with historical tracking, filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from apps.scenario.models import (
    TGCModel,
    FCRModel,
    MortalityModel,
    Scenario,
    ScenarioModelChange
)
from apps.scenario.api.serializers.history import (
    TGCModelHistorySerializer,
    FCRModelHistorySerializer,
    MortalityModelHistorySerializer,
    ScenarioHistorySerializer,
    ScenarioModelChangeHistorySerializer
)
from apps.scenario.api.filters.history import (
    TGCModelHistoryFilter,
    FCRModelHistoryFilter,
    MortalityModelHistoryFilter,
    ScenarioHistoryFilter,
    ScenarioModelChangeHistoryFilter
)


class TGCModelHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for TGCModel historical records."""
    queryset = TGCModel.history.all()
    serializer_class = TGCModelHistorySerializer
    filterset_class = TGCModelHistoryFilter


class FCRModelHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for FCRModel historical records."""
    queryset = FCRModel.history.all()
    serializer_class = FCRModelHistorySerializer
    filterset_class = FCRModelHistoryFilter


class MortalityModelHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for MortalityModel historical records."""
    queryset = MortalityModel.history.all()
    serializer_class = MortalityModelHistorySerializer
    filterset_class = MortalityModelHistoryFilter


class ScenarioHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Scenario historical records."""
    queryset = Scenario.history.all()
    serializer_class = ScenarioHistorySerializer
    filterset_class = ScenarioHistoryFilter


class ScenarioModelChangeHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for ScenarioModelChange historical records."""
    queryset = ScenarioModelChange.history.all()
    serializer_class = ScenarioModelChangeHistorySerializer
    filterset_class = ScenarioModelChangeHistoryFilter
