"""
Journal Entry serializers for health monitoring.

This module defines serializers for the JournalEntry model.
"""

from rest_framework import serializers

from apps.batch.models import Batch
from apps.infrastructure.models import Container
from ...models import JournalEntry
from .base import HealthBaseSerializer


class JournalEntrySerializer(HealthBaseSerializer):
    """Serializer for JournalEntry model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    batch = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all())
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'batch', 'container', 'entry_date', 
            'description', 'category', 'severity', 'resolution_status', 'resolution_notes',
            'created_at', 'updated_at', 'user', 
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')

    def create(self, validated_data):
        """Create a new journal entry.

        The 'user' field is automatically set from the request context.

        Args:
            validated_data (dict): The validated data for creating the entry.

        Returns:
            JournalEntry: The created journal entry instance.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update an existing journal entry.

        The 'user' field cannot be updated through this method.

        Args:
            instance (JournalEntry): The journal entry instance to update.
            validated_data (dict): The validated data for updating the entry.

        Returns:
            JournalEntry: The updated journal entry instance.
        """
        # Remove user from validated_data if present to prevent changing it
        validated_data.pop('user', None)
        return super().update(instance, validated_data)
