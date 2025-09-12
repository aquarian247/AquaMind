"""
FCR Trends Serializer for Operational API.

Handles serialization of FCR trends data with actual and predicted values.
"""
from rest_framework import serializers
from typing import Dict, Any


class FCRDataPointSerializer(serializers.Serializer):
    """
    Serializer for individual FCR data points in the trends series.

    Supports container-level granularity with operational metadata.
    FCR values represent feed conversion ratio (feed consumed / biomass gained).
    """
    period_start = serializers.DateField(
        help_text="Start date of the time period bucket (inclusive)"
    )
    period_end = serializers.DateField(
        help_text="End date of the time period bucket (inclusive)"
    )
    actual_fcr = serializers.DecimalField(
        max_digits=5,
        decimal_places=3,
        required=False,
        allow_null=True,
        help_text="Actual FCR ratio calculated from feeding and growth data (feed_kg / biomass_gain_kg)"
    )
    confidence = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Confidence level in the FCR calculation: VERY_HIGH, HIGH, MEDIUM, LOW. Based on data quality and sample size."
    )
    data_points = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Number of individual feeding/growth data points used to calculate this FCR value"
    )
    predicted_fcr = serializers.DecimalField(
        max_digits=5,
        decimal_places=3,
        required=False,
        allow_null=True,
        help_text="Predicted FCR ratio from scenario models (feed_kg / expected_biomass_gain_kg)"
    )
    scenarios_used = serializers.IntegerField(
        required=False,
        default=0,
        help_text="Number of scenario models that contributed to this prediction"
    )
    deviation = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Percentage deviation of actual from predicted FCR: ((actual - predicted) / predicted) * 100"
    )
    # Container-specific metadata
    container_name = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Name of the container for container-level aggregations"
    )
    assignment_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Container assignment ID for container-level aggregations"
    )
    container_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Number of containers included in this data point"
    )
    total_containers = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Total number of containers in the aggregation scope"
    )


class FCRTrendsSerializer(serializers.Serializer):
    """
    Serializer for FCR trends API response.

    Provides comprehensive FCR trend data with actual and predicted values,
    confidence levels, and deviation analysis.

    Time interval semantics:
    - DAILY: Single-day buckets
    - WEEKLY: Monday-Sunday inclusive buckets
    - MONTHLY: Calendar month buckets (1st to last day)

    Default behavior when filters omitted:
    - aggregation_level: 'geography' (system-wide aggregation)
    - interval: 'DAILY' (most granular view)
    """
    interval = serializers.ChoiceField(
        choices=['DAILY', 'WEEKLY', 'MONTHLY'],
        default='DAILY',
        help_text="Time interval for data aggregation. DAILY=calendar days, WEEKLY=Monday-Sunday, MONTHLY=calendar months."
    )
    unit = serializers.CharField(
        default='ratio',
        read_only=True,
        help_text="Units for FCR values: 'ratio' (feed consumed / biomass gained)"
    )
    aggregation_level = serializers.ChoiceField(
        choices=['batch', 'assignment', 'geography'],
        default='geography',
        help_text="Level of data aggregation. 'batch'=per batch, 'assignment'=per container, 'geography'=across all batches in geography."
    )
    series = FCRDataPointSerializer(
        many=True,
        help_text="Time-series data points, one per interval bucket"
    )
    # Optional metadata
    model_version = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Version of the FCR calculation model used"
    )

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert the service response to API representation.

        Ensures explicit defaults for interval ('DAILY') and aggregation_level ('geography')
        are always returned, even when service doesn't specify them.

        Args:
            instance: Dictionary from FCRTrendsService.get_fcr_trends()

        Returns:
            Dict: Properly formatted API response with explicit field defaults
        """
        return {
            'interval': instance.get('interval', 'DAILY'),  # Explicit default: DAILY
            'unit': instance.get('unit', 'ratio'),
            'aggregation_level': instance.get('aggregation_level', 'geography'),  # Explicit default: geography
            'model_version': instance.get('model_version'),  # Optional metadata
            'series': [
                {
                    'period_start': item['period_start'],
                    'period_end': item['period_end'],
                    'actual_fcr': item.get('actual_fcr'),
                    'confidence': item.get('confidence'),
                    'data_points': item.get('data_points', 0),
                    'predicted_fcr': item.get('predicted_fcr'),
                    'scenarios_used': item.get('scenarios_used', 0),
                    'deviation': item.get('deviation'),
                    # Include container metadata
                    'container_name': item.get('container_name'),
                    'assignment_id': item.get('assignment_id'),
                    'container_count': item.get('container_count'),
                    'total_containers': item.get('total_containers')
                }
                for item in instance.get('series', [])
            ]
        }
