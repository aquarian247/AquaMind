"""
Feed Container Stock serializers for inventory management.

This module defines serializers for FeedContainerStock model,
supporting FIFO inventory tracking operations.
"""

from rest_framework import serializers
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from typing import Optional

from apps.inventory.models import FeedContainerStock, FeedPurchase
from apps.infrastructure.models import FeedContainer


class FeedContainerStockSerializer(serializers.ModelSerializer):
    """
    Serializer for FeedContainerStock model.
    
    Handles FIFO inventory tracking for feed batches in containers.
    """
    feed_container_name = serializers.CharField(
        source='feed_container.name',
        read_only=True,
        help_text="Name of the feed container"
    )
    feed_purchase_batch = serializers.CharField(
        source='feed_purchase.batch_number',
        read_only=True,
        help_text="Feed purchase batch number"
    )
    feed_type = serializers.CharField(
        source='feed_purchase.feed.name',
        read_only=True,
        help_text="Type of feed"
    )
    cost_per_kg = serializers.DecimalField(
        source='feed_purchase.cost_per_kg',
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Cost per kg from the original purchase"
    )
    total_value = serializers.SerializerMethodField(
        help_text="Total value of remaining stock (quantity_kg * cost_per_kg)"
    )
    
    class Meta:
        model = FeedContainerStock
        fields = [
            'id', 'feed_container', 'feed_container_name',
            'feed_purchase', 'feed_purchase_batch', 'feed_type',
            'quantity_kg', 'entry_date', 'cost_per_kg', 'total_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_value']
    
    def get_total_value(self, obj) -> Optional[Decimal]:
        """Calculate total value of remaining stock."""
        return obj.quantity_kg * obj.feed_purchase.cost_per_kg
    
    def validate_quantity_kg(self, value):
        """Validate that quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class FeedContainerStockCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating FeedContainerStock entries.
    
    Used when adding feed batches to containers.
    """
    feed_container = serializers.PrimaryKeyRelatedField(
        queryset=FeedContainer.objects.all(),
        help_text="Feed container to add stock to"
    )
    feed_purchase = serializers.PrimaryKeyRelatedField(
        queryset=FeedPurchase.objects.all(),
        help_text="Feed purchase batch to add"
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity to add to container in kg"
    )
    
    class Meta:
        model = FeedContainerStock
        fields = ['feed_container', 'feed_purchase', 'quantity_kg', 'entry_date']
    
    def validate(self, data):
        """
        Validate that the feed purchase has sufficient stock.
        """
        feed_purchase = data['feed_purchase']
        requested_quantity = data['quantity_kg']
        
        # Check if feed purchase has enough remaining stock
        total_allocated = FeedContainerStock.objects.filter(
            feed_purchase=feed_purchase
        ).aggregate(
            total=models.Sum('quantity_kg')
        )['total'] or Decimal('0')
        
        available_quantity = feed_purchase.quantity_kg - total_allocated
        
        if requested_quantity > available_quantity:
            raise serializers.ValidationError(
                f"Insufficient stock. Available: {available_quantity}kg, "
                f"Requested: {requested_quantity}kg"
            )
        
        return data 