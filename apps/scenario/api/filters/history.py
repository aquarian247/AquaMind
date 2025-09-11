"""
History filters for Scenario models.

These filters provide date range, user, and change type filtering
for historical records across scenario models with historical tracking.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.scenario.models import (
    TGCModel,
    FCRModel,
    MortalityModel,
    Scenario,
    ScenarioModelChange
)


class TGCModelHistoryFilter(HistoryFilter):
    """Filter class for TGCModel historical records."""

    class Meta:
        model = TGCModel.history.model
        fields = ['name', 'location', 'release_period']


class FCRModelHistoryFilter(HistoryFilter):
    """Filter class for FCRModel historical records."""

    class Meta:
        model = FCRModel.history.model
        fields = ['name']


class MortalityModelHistoryFilter(HistoryFilter):
    """Filter class for MortalityModel historical records."""

    class Meta:
        model = MortalityModel.history.model
        fields = ['name', 'frequency']


class ScenarioHistoryFilter(HistoryFilter):
    """Filter class for Scenario historical records."""

    class Meta:
        model = Scenario.history.model
        fields = ['name', 'start_date', 'created_by']


class ScenarioModelChangeHistoryFilter(HistoryFilter):
    """Filter class for ScenarioModelChange historical records."""

    class Meta:
        model = ScenarioModelChange.history.model
        fields = ['scenario', 'change_day', 'new_tgc_model', 'new_fcr_model', 'new_mortality_model']
