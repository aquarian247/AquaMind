"""
History viewsets for Infrastructure models.

These viewsets provide read-only access to historical records
for all infrastructure models with filtering and pagination.
"""

from aquamind.utils.history_utils import HistoryViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
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
from ..serializers.history import (
    GeographyHistorySerializer,
    AreaHistorySerializer,
    FreshwaterStationHistorySerializer,
    HallHistorySerializer,
    ContainerTypeHistorySerializer,
    ContainerHistorySerializer,
    SensorHistorySerializer,
    FeedContainerHistorySerializer
)
from ..filters.history import (
    GeographyHistoryFilter,
    AreaHistoryFilter,
    FreshwaterStationHistoryFilter,
    HallHistoryFilter,
    ContainerTypeHistoryFilter,
    ContainerHistoryFilter,
    SensorHistoryFilter,
    FeedContainerHistoryFilter
)


class GeographyHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Geography historical records."""
    queryset = Geography.history.all()
    serializer_class = GeographyHistorySerializer
    filterset_class = GeographyHistoryFilter


class AreaHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Area historical records."""
    queryset = Area.history.all()
    serializer_class = AreaHistorySerializer
    filterset_class = AreaHistoryFilter


class FreshwaterStationHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for FreshwaterStation historical records."""
    queryset = FreshwaterStation.history.all()
    serializer_class = FreshwaterStationHistorySerializer
    filterset_class = FreshwaterStationHistoryFilter


class HallHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Hall historical records."""
    queryset = Hall.history.all()
    serializer_class = HallHistorySerializer
    filterset_class = HallHistoryFilter


class ContainerTypeHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for ContainerType historical records."""
    queryset = ContainerType.history.all()
    serializer_class = ContainerTypeHistorySerializer
    filterset_class = ContainerTypeHistoryFilter


class ContainerHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Container historical records."""
    queryset = Container.history.all()
    serializer_class = ContainerHistorySerializer
    filterset_class = ContainerHistoryFilter


class SensorHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for Sensor historical records."""
    queryset = Sensor.history.all()
    serializer_class = SensorHistorySerializer
    filterset_class = SensorHistoryFilter


class FeedContainerHistoryViewSet(HistoryViewSet, ReadOnlyModelViewSet):
    """ViewSet for FeedContainer historical records."""
    queryset = FeedContainer.history.all()
    serializer_class = FeedContainerHistorySerializer
    filterset_class = FeedContainerHistoryFilter
