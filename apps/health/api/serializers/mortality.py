"""
Mortality serializers for health monitoring.

This module defines serializers for mortality models, including
MortalityReason, MortalityRecord, and LiceCount.
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator
from typing import Optional

from apps.batch.models import Batch
from apps.health.api.serializers.base import HealthBaseSerializer
from apps.health.models import LiceCount, MortalityReason, MortalityRecord
from apps.infrastructure.models import Container

class MortalityReasonSerializer(HealthBaseSerializer):
    """Serializer for the MortalityReason model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    name = serializers.CharField(
        help_text="Name of the mortality reason (e.g., 'Disease', 'Predation')."
    )
    description = serializers.CharField(
        help_text="Detailed description of the mortality reason."
    )
    
    class Meta:
        model = MortalityReason
        fields = ['id', 'name', 'description']


class MortalityRecordSerializer(HealthBaseSerializer):
    """Serializer for the MortalityRecord model.

    Uses HealthBaseSerializer for consistent error handling and field management.
    Records mortality events including count, reason, and associated batch/container.
    """
    container_name = serializers.SerializerMethodField(
        help_text="Name of the container where the mortality occurred."
    )
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        help_text="The batch associated with this mortality record."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        help_text="The container where the mortality occurred."
    )
    event_date = serializers.DateTimeField(
        read_only=True,
        help_text="Date and time when the mortality event was recorded (auto-set)."
    )
    count = serializers.IntegerField(
        help_text="Number of mortalities recorded in this event.",
        validators=[MinValueValidator(1)]
    )
    reason = serializers.PrimaryKeyRelatedField(
        queryset=MortalityReason.objects.all(),
        help_text="Reason for the mortality (references MortalityReason model)."
    )
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Additional notes about the mortality event."
    )

    def get_container_name(self, obj) -> Optional[str]:
        """Get the container name for the mortality record."""
        return obj.container.name if obj.container else None

    class Meta:
        model = MortalityRecord
        fields = [
            'id', 'batch', 'container', 'container_name', 'event_date',
            'count', 'reason', 'notes'
        ]
        read_only_fields = ['event_date']  # Event date is auto-set


class LiceCountSerializer(HealthBaseSerializer):
    """Serializer for the LiceCount model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Records sea lice counts for monitoring parasite loads in fish populations.
    """
    average_per_fish = serializers.FloatField(
        read_only=True,
        help_text="Calculated average number of lice per fish (total count / fish sampled)."
    )
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        help_text="The batch for which lice were counted."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        help_text="The container where the fish were sampled for lice counting."
    )
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        help_text="User who performed the lice count (auto-set from request)."
    )
    count_date = serializers.DateTimeField(
        read_only=True,
        help_text="Date and time when the lice count was performed (auto-set)."
    )
    adult_female_count = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Number of adult female lice counted across all sampled fish."
    )
    adult_male_count = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Number of adult male lice counted across all sampled fish."
    )
    juvenile_count = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Number of juvenile lice counted across all sampled fish."
    )
    fish_sampled = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of fish examined during this lice count."
    )
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Additional notes about the lice count or observations."
    )

    class Meta:
        model = LiceCount
        fields = [
            'id', 'batch', 'container', 'user', 'count_date',
            'adult_female_count', 'adult_male_count', 'juvenile_count',
            'fish_sampled', 'notes', 'average_per_fish'
        ]
        read_only_fields = ['count_date', 'average_per_fish', 'user']
        # User is typically set in viewset, count_date is auto_now_add
