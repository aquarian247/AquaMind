"""
Base serializer classes for the inventory app.

This module contains base serializer classes that standardize patterns
across serializers in the inventory app.
"""
from rest_framework import serializers

from .utils import StandardErrorMixin, ReadWriteFieldsMixin


class InventoryBaseSerializer(
    StandardErrorMixin, ReadWriteFieldsMixin, serializers.ModelSerializer
):
    """
    Base serializer for inventory models.

    This serializer combines standard error handling and read/write field
    management.
    It provides a foundation for all inventory serializers to ensure consistent
    behavior and patterns.
    """


class TimestampedModelSerializer(InventoryBaseSerializer):
    """
    Base serializer for models with created_at and updated_at fields.
    """
    class Meta:
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UpdatedModelSerializer(InventoryBaseSerializer):
    """
    Base serializer for models with only an updated_at field.
    Use this for models representing continuous state where creation time is
    not meaningful.
    """
    class Meta:
        fields = ['updated_at']
        read_only_fields = ['updated_at']


class FeedRelatedSerializer(InventoryBaseSerializer):
    """
    Base serializer for models related to feeds.

    This serializer provides consistent handling of feed relationships,
    including string representations for read operations.
    """
    feed_name = serializers.StringRelatedField(
        source='feed', read_only=True)

    class Meta:
        fields = ['feed', 'feed_name']


class ContainerRelatedSerializer(InventoryBaseSerializer):
    """
    Base serializer for models related to containers.

    This serializer provides consistent handling of container relationships,
    including string representations for read operations.
    """
    container_name = serializers.StringRelatedField(
        source='container', read_only=True)

    class Meta:
        fields = ['container', 'container_name']


class BatchRelatedSerializer(InventoryBaseSerializer):
    """
    Base serializer for models related to batches.

    This serializer provides consistent handling of batch relationships,
    including string representations for read operations.
    """
    batch_name = serializers.StringRelatedField(
        source='batch', read_only=True)

    class Meta:
        fields = ['batch', 'batch_name']


class FeedingBaseSerializer(
    FeedRelatedSerializer, BatchRelatedSerializer, ContainerRelatedSerializer
):
    """
    Base serializer for feeding-related models.

    This serializer combines feed, batch, and container relationship handling
    for models related to feeding events.
    """
    class Meta:
        fields = FeedRelatedSerializer.Meta.fields + \
                 BatchRelatedSerializer.Meta.fields + \
                 ContainerRelatedSerializer.Meta.fields
