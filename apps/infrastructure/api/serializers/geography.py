"""
Geography serializer for the infrastructure app.

This module defines the serializer for the Geography model.
"""

from rest_framework import serializers # Added for explicit field definition
from rest_framework.validators import UniqueValidator

from apps.infrastructure.models.geography import Geography
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class GeographySerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Geography model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the geographical region (e.g., 'Faroe Islands', 'Scotland West').",
        validators=[UniqueValidator(queryset=Geography.objects.all())]
    )
    description = serializers.CharField(
        allow_blank=True,
        required=False,
        style={'base_template': 'textarea.html'},
        help_text="Optional description of the geographical region, its boundaries, or specific characteristics."
    )

    class Meta:
        model = Geography
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at')
