"""
History filters for Infrastructure models.

These filters provide date range, user, and change type filtering
for historical records across all infrastructure models.
"""

import django_filters as filters
from aquamind.utils.history_utils import HistoryFilter
from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType,
    Container,
    Sensor,
    FeedContainer
)


class GeographyHistoryFilter(HistoryFilter):
    """Filter class for Geography historical records."""

    class Meta:
        model = Geography.history.model
        fields = ['name', 'description']


class AreaHistoryFilter(HistoryFilter):
    """Filter class for Area historical records."""

    class Meta:
        model = Area.history.model
        fields = ['name', 'geography', 'active']


class FreshwaterStationHistoryFilter(HistoryFilter):
    """Filter class for FreshwaterStation historical records."""

    class Meta:
        model = FreshwaterStation.history.model
        fields = ['name', 'station_type', 'geography', 'active']


class HallHistoryFilter(HistoryFilter):
    """Filter class for Hall historical records."""

    class Meta:
        model = Hall.history.model
        fields = ['name', 'freshwater_station', 'active']


class ContainerTypeHistoryFilter(HistoryFilter):
    """Filter class for ContainerType historical records."""

    class Meta:
        model = ContainerType.history.model
        fields = ['name', 'category']


class ContainerHistoryFilter(HistoryFilter):
    """Filter class for Container historical records."""

    class Meta:
        model = Container.history.model
        fields = ['name', 'container_type', 'hall', 'area', 'active']


class SensorHistoryFilter(HistoryFilter):
    """Filter class for Sensor historical records."""

    class Meta:
        model = Sensor.history.model
        fields = ['name', 'sensor_type', 'container', 'active']


class FeedContainerHistoryFilter(HistoryFilter):
    """Filter class for FeedContainer historical records."""

    class Meta:
        model = FeedContainer.history.model
        fields = ['name', 'container_type', 'hall', 'area', 'active']
