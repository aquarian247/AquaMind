"""
Infrastructure viewsets package.

This package contains viewsets for the infrastructure app, organized into separate modules.
"""

from apps.infrastructure.api.viewsets.geography import GeographyViewSet
from apps.infrastructure.api.viewsets.area import AreaViewSet
from apps.infrastructure.api.viewsets.station import FreshwaterStationViewSet
from apps.infrastructure.api.viewsets.hall import HallViewSet
from apps.infrastructure.api.viewsets.container_type import ContainerTypeViewSet
from apps.infrastructure.api.viewsets.container import ContainerViewSet
from apps.infrastructure.api.viewsets.sensor import SensorViewSet
from apps.infrastructure.api.viewsets.feed_container import FeedContainerViewSet

__all__ = [
    'GeographyViewSet',
    'AreaViewSet',
    'FreshwaterStationViewSet',
    'HallViewSet',
    'ContainerTypeViewSet',
    'ContainerViewSet',
    'SensorViewSet',
    'FeedContainerViewSet',
]
