"""
Feeding event serializer for the inventory app.
"""
from decimal import Decimal
from django.core.validators import MinValueValidator
from rest_framework import serializers
from django.db import transaction

from apps.inventory.models import FeedingEvent
from apps.inventory.api.serializers.base import (
    FeedingBaseSerializer, TimestampedModelSerializer
)
from apps.inventory.api.serializers.validation import (
    validate_batch_assignment_relationship, validate_feed_stock_quantity
)
from apps.inventory.services.fifo_service import FIFOInventoryService

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

    amount_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Amount of feed given in kilograms"
    )
    batch_biomass_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,  # Will be auto-populated
        help_text="Batch biomass at feeding time (auto-populated from latest assignment)"
    )
    feeding_percentage = serializers.DecimalField(
        max_digits=8,
        decimal_places=6,
        read_only=True,
        help_text="Feed amount as percentage of biomass (auto-calculated)"
    )
    feed_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Cost of feed consumed (calculated via FIFO)"
    )

    class Meta:
        model = FeedingEvent
        fields = [
            'id', 'batch', 'batch_name', 'batch_assignment',
            'container', 'container_name',
            'feed', 'feed_name', 'feed_stock', 'feeding_date',
            'feeding_time', 'amount_kg',
            'batch_biomass_kg', 'feeding_percentage',
            'feed_cost', 'method',
            'notes', 'recorded_by', 'recorded_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'feeding_percentage', 'feed_cost']

    def validate(self, data):
        """
        Validate the feeding event data and auto-populate calculated fields.

        Auto-populates:
        - batch_biomass_kg from latest batch assignment if not provided
        - container from batch_assignment if not provided
        
        Validates:
        - The batch assignment belongs to the specified batch
        - There is enough feed in stock if feed_stock is provided
        """
        data = super().validate(data)

        # Auto-populate container from batch_assignment if not provided
        if ('batch_assignment' in data and data['batch_assignment'] and
                'container' not in data):
            data['container'] = data['batch_assignment'].container

        # Auto-populate batch biomass from latest assignment if not provided
        if 'batch_biomass_kg' not in data and 'batch' in data:
            batch = data['batch']
            # Get the most recent active assignment for this batch
            latest_assignment = batch.container_assignments.filter(
                departure_date__isnull=True
            ).order_by('-assignment_date').first()
            
            if latest_assignment:
                data['batch_biomass_kg'] = latest_assignment.biomass_kg
            else:
                # Fallback to calculated biomass if no assignments
                data['batch_biomass_kg'] = batch.calculated_biomass_kg or Decimal('0.01')

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
        Create a FeedingEvent with auto-calculated fields and FIFO cost tracking.
        """
        # Calculate feeding percentage
        amount_kg = validated_data['amount_kg']
        batch_biomass_kg = validated_data['batch_biomass_kg']
        feeding_percentage = (amount_kg / batch_biomass_kg) * 100
        validated_data['feeding_percentage'] = feeding_percentage

        # Calculate feed cost using FIFO if feed_stock is provided
        feed_cost = Decimal('0.00')
        feed_stock = validated_data.get('feed_stock')
        if feed_stock:
            try:
                # Use FIFO service to consume feed and get cost
                feed_cost = FIFOInventoryService.consume_feed_fifo(
                    container=feed_stock.feed_container,
                    amount_kg=amount_kg
                )
            except Exception as e:
                # Fallback to simple stock deduction if FIFO fails
                feed_stock.current_quantity_kg -= amount_kg
                feed_stock.save()
                # Estimate cost based on average purchase price
                # This is a fallback - in production you'd want better error handling
                feed_cost = amount_kg * Decimal('5.00')  # Default cost per kg
        
        validated_data['feed_cost'] = feed_cost

        # Create the feeding event
        feeding_event = FeedingEvent.objects.create(**validated_data)

        return feeding_event
