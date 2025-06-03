"""
Feeding event serializer for the inventory app.
"""
from rest_framework import serializers
from django.db import transaction

from apps.inventory.models import FeedingEvent
from apps.inventory.api.serializers.base import (
    FeedingBaseSerializer, TimestampedModelSerializer
)
from apps.inventory.api.serializers.validation import (
    validate_batch_assignment_relationship, validate_feed_stock_quantity
)

class FeedingEventSerializer(
    FeedingBaseSerializer, TimestampedModelSerializer
):
    """
    Serializer for the FeedingEvent model.

    Provides CRUD operations for feeding events with validation and stock
    updates.
    """
    recorded_by_username = serializers.StringRelatedField(
        source='recorded_by', read_only=True
    )

    class Meta:
        model = FeedingEvent
        fields = [
            'id', 'batch', 'batch_name', 'batch_assignment',
            'container', 'container_name',
            'feed', 'feed_name', 'feed_stock', 'feeding_date',
            'feeding_time', 'amount_kg',
            'batch_biomass_kg', 'feeding_percentage',
            'feed_conversion_ratio', 'method',
            'notes', 'recorded_by', 'recorded_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'feeding_percentage']

    def validate(self, data):
        """
        Validate the feeding event data.

        Ensures:
        - The batch assignment belongs to the specified batch
        - There is enough feed in stock if feed_stock is provided
        - Sets container from batch_assignment if not provided
        - Gets batch biomass if not provided
        """
        data = super().validate(data)

        # Set the container from the batch_assignment if not explicitly
        # provided
        if ('batch_assignment' in data and
                'container' not in data):
            data['container'] = data['batch_assignment'].container

        # Get batch biomass if not explicitly provided
        if 'batch_biomass_kg' not in data and 'batch' in data:
            batch = data['batch']
            data['batch_biomass_kg'] = batch.calculated_biomass_kg

        # Validate batch assignment belongs to batch
        if ('batch' in data and 'batch_assignment' in data and
                data['batch_assignment']):
            validate_batch_assignment_relationship(
                data['batch'], data['batch_assignment']
            )

        # Validate feed stock quantity
        if ('feed_stock' in data and data['feed_stock'] and
                'amount_kg' in data):
            validate_feed_stock_quantity(data['feed_stock'], data['amount_kg'])

        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a FeedingEvent and handle related updates.
        """
        # Create the feeding event
        feeding_event = FeedingEvent.objects.create(**validated_data)

        # Update feed stock if provided
        feed_stock = validated_data.get('feed_stock')
        if feed_stock:
            feed_stock.current_quantity_kg -= validated_data['amount_kg']
            feed_stock.save()

        return feeding_event
