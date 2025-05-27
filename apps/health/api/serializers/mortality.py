"""
Mortality serializers for health monitoring.

This module defines serializers for mortality models, including
MortalityReason, MortalityRecord, and LiceCount.
"""

from rest_framework import serializers

from ...models import MortalityReason, MortalityRecord, LiceCount
from .base import HealthBaseSerializer


class MortalityReasonSerializer(HealthBaseSerializer):
    """Serializer for the MortalityReason model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    class Meta:
        model = MortalityReason
        fields = ['id', 'name', 'description']


class MortalityRecordSerializer(HealthBaseSerializer):
    """Serializer for the MortalityRecord model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    class Meta:
        model = MortalityRecord
        fields = [
            'id', 'batch', 'container', 'event_date',
            'count', 'reason', 'notes'
        ]
        read_only_fields = ['event_date']  # Event date is auto-set


class LiceCountSerializer(HealthBaseSerializer):
    """Serializer for the LiceCount model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    average_per_fish = serializers.FloatField(read_only=True)

    class Meta:
        model = LiceCount
        fields = [
            'id', 'batch', 'container', 'user', 'count_date',
            'adult_female_count', 'adult_male_count', 'juvenile_count',
            'fish_sampled', 'notes', 'average_per_fish'
        ]
        read_only_fields = ['count_date', 'average_per_fish', 'user']
        # User is typically set in viewset, count_date is auto_now_add
