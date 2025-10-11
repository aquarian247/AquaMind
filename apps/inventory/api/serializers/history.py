"""
History serializers for Inventory models.

These serializers provide read-only access to historical records
for inventory models with historical tracking, exposing change tracking information.
"""

from rest_framework import serializers
from aquamind.utils.history_utils import HistorySerializer
from apps.inventory.models import FeedingEvent


class FeedingEventHistorySerializer(HistorySerializer):
    """History serializer for FeedingEvent model."""

    class Meta:
        model = FeedingEvent.history.model
        fields = '__all__'
