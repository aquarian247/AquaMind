"""
Geography serializer for the infrastructure app.

This module defines the serializer for the Geography model.
"""

from apps.infrastructure.models.geography import Geography
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class GeographySerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Geography model."""

    class Meta:
        model = Geography
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
