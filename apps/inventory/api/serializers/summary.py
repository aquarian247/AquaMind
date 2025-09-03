"""
Batch feeding summary serializer for the inventory app.
"""
from rest_framework import serializers

from apps.inventory.models import BatchFeedingSummary
from apps.inventory.api.serializers.base import (
    BatchRelatedSerializer, TimestampedModelSerializer
)
from apps.inventory.api.serializers.validation import (
    validate_date_range, validate_batch_and_date_range
)


class BatchFeedingSummarySerializer(
    BatchRelatedSerializer, TimestampedModelSerializer
):
    """
    Serializer for the BatchFeedingSummary model.

    Provides read operations for batch feeding summaries.
    """
    # batch_name is already provided by BatchRelatedSerializer

    class Meta:
        model = BatchFeedingSummary
        fields = [
            'id', 'batch', 'batch_name', 'period_start', 'period_end',
            'total_feed_kg', 'total_starting_biomass_kg', 'total_ending_biomass_kg',
            'total_growth_kg', 'weighted_avg_fcr', 'container_count',
            'overall_confidence_level', 'estimation_method', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """
        Validate that the period_start is before the period_end.
        """
        data = super().validate(data)

        if 'period_start' in data and 'period_end' in data:
            validate_date_range(data['period_start'], data['period_end'])

        return data


class BatchFeedingSummaryGenerateSerializer(serializers.Serializer):
    """
    Serializer for generating a BatchFeedingSummary on demand.
    """
    batch_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        """
        Validate that the batch exists and dates are valid.
        """
        # Use the extracted validation function
        data['batch'], data['start_date'], data['end_date'] = (
            validate_batch_and_date_range(
                data['batch_id'], data['start_date'], data['end_date']
            )
        )
        return data

    def create(self, validated_data):
        """
        Generate the BatchFeedingSummary.
        """
        batch = validated_data['batch']
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']

        # Generate the summary
        summary = BatchFeedingSummary.generate_for_batch(
            batch, start_date, end_date
        )
        if not summary:
            raise serializers.ValidationError(
                "No feeding events found in this period"
            )

        return summary
