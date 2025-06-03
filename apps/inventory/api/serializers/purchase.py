"""
Feed purchase serializer for the inventory app.
"""

from apps.inventory.models import FeedPurchase
from apps.inventory.api.serializers.base import (
    FeedRelatedSerializer, TimestampedModelSerializer
)
from apps.inventory.api.serializers.validation import validate_date_range


class FeedPurchaseSerializer(
    FeedRelatedSerializer, TimestampedModelSerializer
):
    """
    Serializer for the FeedPurchase model.

    Provides CRUD operations for feed purchase records.
    """
    # feed_name is already provided by FeedRelatedSerializer
    # from the parent class

    def validate(self, data):
        """
        Validate that the purchase date is before the expiry date if provided.
        """
        data = super().validate(data)

        if ('purchase_date' in data and 'expiry_date' in data and 
                data['expiry_date']):
            validate_date_range(data['purchase_date'], data['expiry_date'])

        return data

    class Meta:
        model = FeedPurchase
        fields = [
            'id', 'feed', 'feed_name', 'purchase_date', 'quantity_kg',
            'cost_per_kg', 'supplier', 'batch_number', 'expiry_date',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
