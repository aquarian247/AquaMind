"""
Journal Entry serializers for health monitoring.

This module defines serializers for the JournalEntry model.
"""

from rest_framework import serializers
from django.db import transaction

from apps.batch.models import Batch
from apps.infrastructure.models import Container
from ...models import JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    """Serializer for JournalEntry model."""
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
        """
        Create a new journal entry.
        User is set from the request.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update a journal entry.
        User is not updated.
        """
        # Remove user from validated_data if present to prevent changing it
        validated_data.pop('user', None)
        return super().update(instance, validated_data)
