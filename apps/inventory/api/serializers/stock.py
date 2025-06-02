"""
Feed stock serializer for the inventory app.
"""
from rest_framework import serializers

from apps.inventory.models import FeedStock
from apps.inventory.api.serializers.base import FeedRelatedSerializer, UpdatedModelSerializer


class FeedStockSerializer(FeedRelatedSerializer, UpdatedModelSerializer):
    """
    Serializer for the FeedStock model.
    
    Provides CRUD operations for feed stock levels in feed containers.
    """
    # feed_name is already provided by FeedRelatedSerializer
    feed_container_name = serializers.StringRelatedField(source='feed_container', read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model = FeedStock
        fields = [
            'id', 'feed', 'feed_name', 'feed_container', 'feed_container_name',
            'current_quantity_kg', 'reorder_threshold_kg', 'updated_at',
            'notes', 'needs_reorder'
        ]
        read_only_fields = ['updated_at']
