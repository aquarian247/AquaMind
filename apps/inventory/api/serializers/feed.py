"""
Feed serializer for the inventory app.
"""

from apps.inventory.models import Feed
from apps.inventory.api.serializers.base import InventoryBaseSerializer


class FeedSerializer(InventoryBaseSerializer):
    """
    Serializer for the Feed model.

    Provides CRUD operations for feed types used in aquaculture operations.
    """
    class Meta:
        model = Feed
        fields = [
            'id', 'name', 'brand', 'size_category', 'pellet_size_mm',
            'protein_percentage', 'fat_percentage', 'carbohydrate_percentage',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
