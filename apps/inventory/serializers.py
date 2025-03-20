from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from .models import Feed, FeedPurchase, FeedStock, FeedingEvent, BatchFeedingSummary
from apps.batch.models import Batch, BatchContainerAssignment
from apps.infrastructure.models import Container, FeedContainer


class FeedSerializer(serializers.ModelSerializer):
    """Serializer for the Feed model."""
    class Meta:
        model = Feed
        fields = [
            'id', 'name', 'brand', 'size_category', 'pellet_size_mm',
            'protein_percentage', 'fat_percentage', 'carbohydrate_percentage',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FeedPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for the FeedPurchase model."""
    feed_name = serializers.StringRelatedField(source='feed', read_only=True)

    class Meta:
        model = FeedPurchase
        fields = [
            'id', 'feed', 'feed_name', 'purchase_date', 'quantity_kg',
            'cost_per_kg', 'supplier', 'batch_number', 'expiry_date',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FeedStockSerializer(serializers.ModelSerializer):
    """Serializer for the FeedStock model."""
    feed_name = serializers.StringRelatedField(source='feed', read_only=True)
    feed_container_name = serializers.StringRelatedField(source='feed_container', read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model = FeedStock
        fields = [
            'id', 'feed', 'feed_name', 'feed_container', 'feed_container_name',
            'current_quantity_kg', 'reorder_threshold_kg', 'last_updated',
            'notes', 'needs_reorder'
        ]
        read_only_fields = ['last_updated']


class FeedingEventSerializer(serializers.ModelSerializer):
    """Serializer for the FeedingEvent model."""
    batch_name = serializers.StringRelatedField(source='batch', read_only=True)
    container_name = serializers.StringRelatedField(source='container', read_only=True)
    feed_name = serializers.StringRelatedField(source='feed', read_only=True)
    recorded_by_username = serializers.StringRelatedField(source='recorded_by', read_only=True)

    class Meta:
        model = FeedingEvent
        fields = [
            'id', 'batch', 'batch_name', 'batch_assignment', 'container', 'container_name',
            'feed', 'feed_name', 'feed_stock', 'feeding_date', 'feeding_time', 'amount_kg',
            'batch_biomass_kg', 'feeding_percentage', 'feed_conversion_ratio', 'method',
            'notes', 'recorded_by', 'recorded_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'feeding_percentage']

    def validate(self, data):
        """Validate the FeedingEvent data."""
        # Set the container from the batch_assignment if not explicitly provided
        if 'batch_assignment' in data and 'container' not in data:
            data['container'] = data['batch_assignment'].container

        # Get batch biomass if not explicitly provided
        if 'batch_biomass_kg' not in data and 'batch' in data:
            batch = data['batch']
            data['batch_biomass_kg'] = batch.biomass_kg

        # Check if the batch_assignment belongs to the batch
        if ('batch' in data and 'batch_assignment' in data and 
                data['batch_assignment'].batch.id != data['batch'].id):
            raise serializers.ValidationError(
                "The batch assignment must belong to the specified batch"
            )

        # Validate feed stock quantity if provided
        if 'feed_stock' in data and 'amount_kg' in data:
            if data['feed_stock'].current_quantity_kg < data['amount_kg']:
                raise serializers.ValidationError(
                    "Not enough feed in stock for this feeding event"
                )

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Create a FeedingEvent and handle related updates."""
        # Set current date/time if not provided
        if 'feeding_date' not in validated_data:
            validated_data['feeding_date'] = timezone.now().date()
        if 'feeding_time' not in validated_data:
            validated_data['feeding_time'] = timezone.now().time()

        # Create the feeding event
        feeding_event = super().create(validated_data)
        
        return feeding_event


class BatchFeedingSummarySerializer(serializers.ModelSerializer):
    """Serializer for the BatchFeedingSummary model."""
    batch_name = serializers.StringRelatedField(source='batch', read_only=True)

    class Meta:
        model = BatchFeedingSummary
        fields = [
            'id', 'batch', 'batch_name', 'period_start', 'period_end',
            'total_feed_kg', 'average_biomass_kg', 'average_feeding_percentage',
            'feed_conversion_ratio', 'growth_kg', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BatchFeedingSummaryGenerateSerializer(serializers.Serializer):
    """Serializer for generating a BatchFeedingSummary on demand."""
    batch_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        """Validate that the batch exists and dates are valid."""
        try:
            data['batch'] = Batch.objects.get(pk=data['batch_id'])
        except Batch.DoesNotExist:
            raise serializers.ValidationError("Batch does not exist")

        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")

        return data

    def create(self, validated_data):
        """Generate the BatchFeedingSummary."""
        batch = validated_data['batch']
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']

        # Generate the summary
        summary = BatchFeedingSummary.generate_for_batch(batch, start_date, end_date)
        if not summary:
            raise serializers.ValidationError("No feeding events found in this period")

        return summary