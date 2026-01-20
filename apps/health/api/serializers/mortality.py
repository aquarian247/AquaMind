"""
Mortality serializers for health monitoring.

This module defines serializers for mortality models, including
MortalityReason, MortalityRecord, and LiceCount.
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from typing import Optional

from apps.batch.models import Batch, BatchContainerAssignment
from apps.health.api.serializers.base import HealthBaseSerializer
from apps.health.models import (
    LiceCount, LiceType, MortalityReason, MortalityRecord
)
from apps.infrastructure.models import Container

class LiceTypeSerializer(HealthBaseSerializer):
    """Serializer for LiceType model.

    Provides read-only access to normalized lice type classifications.
    """
    species = serializers.CharField(
        read_only=True,
        help_text="Scientific name of the lice species."
    )
    gender = serializers.CharField(
        read_only=True,
        help_text="Gender classification (male, female, unknown)."
    )
    development_stage = serializers.CharField(
        read_only=True,
        help_text=(
            "Development stage "
            "(copepodid, chalimus, pre-adult, adult, juvenile)."
        )
    )
    description = serializers.CharField(
        read_only=True,
        help_text="Description of lice type and characteristics."
    )
    is_active = serializers.BooleanField(
        read_only=True,
        help_text="Whether this lice type is currently tracked."
    )

    class Meta:
        model = LiceType
        fields = [
            'id', 'species', 'gender',
            'development_stage', 'description', 'is_active'
        ]


class MortalityReasonSerializer(HealthBaseSerializer):
    """Serializer for hierarchical MortalityReason model."""
    name = serializers.CharField(
        help_text="Name of the mortality reason."
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Detailed description."
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=MortalityReason.objects.all(),
        required=False,
        allow_null=True,
        help_text="Parent reason ID for sub-reasons."
    )
    parent_name = serializers.SerializerMethodField(
        help_text="Name of parent reason (read-only)."
    )
    children = serializers.SerializerMethodField(
        help_text="Child reasons (read-only, only on detail view)."
    )

    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else None

    def get_children(self, obj):
        # Only include children on detail view to avoid N+1
        request = self.context.get('request')
        if request and hasattr(request, 'parser_context'):
            if request.parser_context.get('kwargs', {}).get('pk'):
                return MortalityReasonSerializer(
                    obj.children.all(),
                    many=True,
                    context={'request': request}
                ).data
        return None

    class Meta:
        model = MortalityReason
        fields = ['id', 'name', 'description', 'parent', 'parent_name', 'children']


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
        required=False,
        allow_null=True,
        help_text="The container where the mortality occurred (optional)."
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
    """Serializer for LiceCount model.

    Records sea lice counts for monitoring parasite loads.

    Supports legacy format (adult_female_count, adult_male_count,
    juvenile_count) and new normalized format (lice_type + count_value).
    """
    average_per_fish = serializers.FloatField(
        read_only=True,
        help_text=(
            "Calculated average number of lice per fish "
            "(total count / fish sampled)."
        )
    )
    total_count = serializers.IntegerField(
        read_only=True,
        help_text="Total lice count regardless of tracking format."
    )
    lice_type_details = LiceTypeSerializer(
        source='lice_type',
        read_only=True,
        help_text="Detailed lice type classification information."
    )
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        help_text="The batch for which lice were counted."
    )
    assignment = serializers.PrimaryKeyRelatedField(
        queryset=BatchContainerAssignment.objects.all(),
        required=False,
        allow_null=True,
        help_text="Container-specific assignment where lice count was recorded."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        required=False,
        allow_null=True,
        help_text="The container where fish were sampled (optional)."
    )
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        help_text="User who performed the lice count (auto-set from request)."
    )
    count_date = serializers.DateTimeField(
        read_only=True,
        help_text="Date and time when the lice count was performed (auto-set)."
    )
    
    # Legacy fields
    adult_female_count = serializers.IntegerField(
        required=False,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=(
            "[LEGACY] Adult female lice count. "
            "Use lice_type + count_value for new records."
        )
    )
    adult_male_count = serializers.IntegerField(
        required=False,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=(
            "[LEGACY] Adult male lice count. "
            "Use lice_type + count_value for new records."
        )
    )
    juvenile_count = serializers.IntegerField(
        required=False,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=(
            "[LEGACY] Juvenile lice count. "
            "Use lice_type + count_value for new records."
        )
    )
    
    # New normalized fields
    lice_type = serializers.PrimaryKeyRelatedField(
        queryset=LiceType.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text=(
            "Normalized lice type "
            "(species + gender + development stage)."
        )
    )
    count_value = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0)],
        help_text="Count for the specific lice type."
    )
    detection_method = serializers.ChoiceField(
        choices=[
            ('automated', 'Automated Detection'),
            ('manual', 'Manual Visual Count'),
            ('visual', 'Visual Estimation'),
            ('camera', 'Camera-based Detection')
        ],
        required=False,
        allow_null=True,
        help_text="Method used to detect and count lice."
    )
    confidence_level = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=(
            "Confidence level (0.00-1.00, "
            "where 1.00 is highest confidence)."
        )
    )
    
    fish_sampled = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of fish examined during this lice count."
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Additional notes about the lice count or observations."
    )

    class Meta:
        model = LiceCount
        fields = [
            'id', 'batch', 'assignment', 'container', 'user', 'count_date',
            # Legacy fields
            'adult_female_count', 'adult_male_count',
            'juvenile_count',
            # New normalized fields
            'lice_type', 'lice_type_details', 'count_value',
            'detection_method', 'confidence_level',
            # Common fields
            'fish_sampled', 'notes',
            # Calculated fields
            'average_per_fish', 'total_count'
        ]
        read_only_fields = [
            'count_date', 'average_per_fish',
            'total_count', 'user', 'lice_type_details'
        ]
    
    def validate(self, data):
        """Validate legacy OR new format used consistently."""
        # Check legacy format
        has_legacy = any([
            data.get('adult_female_count', 0) > 0,
            data.get('adult_male_count', 0) > 0,
            data.get('juvenile_count', 0) > 0
        ])

        # Check new format
        has_new = (
            data.get('lice_type') is not None and
            data.get('count_value') is not None
        )

        if has_legacy and has_new:
            raise serializers.ValidationError(
                "Cannot use both legacy counts and new "
                "normalized format in same record."
            )

        if not has_legacy and not has_new:
            raise serializers.ValidationError(
                "Must provide either legacy counts "
                "(adult_female_count, adult_male_count, "
                "juvenile_count) or new format "
                "(lice_type + count_value)."
            )

        # Validate new format completeness
        if (
            (data.get('lice_type') is not None) !=
            (data.get('count_value') is not None)
        ):
            raise serializers.ValidationError(
                "Both lice_type and count_value must be "
                "provided together."
            )

        return data
