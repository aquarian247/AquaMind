"""
Journal Entry serializers for health monitoring.

This module defines serializers for the JournalEntry model.
"""

from rest_framework import serializers
from django.utils import timezone

from apps.batch.models import Batch
from apps.infrastructure.models import Container
from ...models import JournalEntry
from .base import HealthBaseSerializer


class JournalEntrySerializer(HealthBaseSerializer):
    """Serializer for JournalEntry model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Handles journal entries for health observations, incidents, and notes related to batches.
    """
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        help_text="The batch this journal entry is associated with."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(), 
        required=False, 
        allow_null=True,
        help_text="Optional container this journal entry is associated with. Can be null if the entry applies to the entire batch."
    )
    entry_date = serializers.DateTimeField(
        default=serializers.CreateOnlyDefault(timezone.now),
        help_text="Date and time when the observation or incident occurred. Defaults to the current datetime if not provided."
    )
    description = serializers.CharField(
        help_text="Detailed description of the health observation or incident."
    )
    category = serializers.CharField(
        help_text="Category of the journal entry (e.g., 'observation', 'incident', 'treatment')."
    )
    severity = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Optional severity level of the incident or observation (e.g., 'low', 'medium', 'high')."
    )
    resolution_status = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Current status of resolution for this entry (e.g., 'open', 'in progress', 'resolved')."
    )
    resolution_notes = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Notes on how the issue was resolved or is being addressed."
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
