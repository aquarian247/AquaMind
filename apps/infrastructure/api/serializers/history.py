"""
History serializers for Infrastructure models.

These serializers provide read-only access to historical records
for all infrastructure models, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
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


class GeographyHistorySerializer(HistorySerializer):
    """History serializer for Geography model."""

    class Meta:
        model = Geography.history.model
        fields = '__all__'


class AreaHistorySerializer(HistorySerializer):
    """History serializer for Area model."""

    class Meta:
        model = Area.history.model
        fields = '__all__'


class FreshwaterStationHistorySerializer(HistorySerializer):
    """History serializer for FreshwaterStation model."""

    class Meta:
        model = FreshwaterStation.history.model
        fields = '__all__'


class HallHistorySerializer(HistorySerializer):
    """History serializer for Hall model."""

    class Meta:
        model = Hall.history.model
        fields = '__all__'


class ContainerTypeHistorySerializer(HistorySerializer):
    """History serializer for ContainerType model."""

    class Meta:
        model = ContainerType.history.model
        fields = '__all__'


class ContainerHistorySerializer(HistorySerializer):
    """History serializer for Container model."""

    class Meta:
        model = Container.history.model
        fields = '__all__'


class SensorHistorySerializer(HistorySerializer):
    """History serializer for Sensor model."""

    class Meta:
        model = Sensor.history.model
        fields = '__all__'


class FeedContainerHistorySerializer(HistorySerializer):
    """History serializer for FeedContainer model."""

    class Meta:
        model = FeedContainer.history.model
        fields = '__all__'
