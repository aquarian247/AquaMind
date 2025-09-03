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
    """
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    actual_fcr = serializers.DecimalField(
        max_digits=5,
        decimal_places=3,
        required=False,
        allow_null=True
    )
    confidence = serializers.CharField(required=False, allow_null=True)
    data_points = serializers.IntegerField(required=False, default=0)
    predicted_fcr = serializers.DecimalField(
        max_digits=5,
        decimal_places=3,
        required=False,
        allow_null=True
    )
    scenarios_used = serializers.IntegerField(required=False, default=0)
    deviation = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Percentage deviation of actual from predicted FCR"
    )
    # Container-specific metadata
    container_name = serializers.CharField(required=False, allow_null=True)
    assignment_id = serializers.IntegerField(required=False, allow_null=True)
    container_count = serializers.IntegerField(required=False, allow_null=True)
    total_containers = serializers.IntegerField(required=False, allow_null=True)


class FCRTrendsSerializer(serializers.Serializer):
    """
    Serializer for FCR trends API response.

    Provides comprehensive FCR trend data with actual and predicted values,
    confidence levels, and deviation analysis.
    """
    interval = serializers.ChoiceField(
        choices=['DAILY', 'WEEKLY', 'MONTHLY'],
        default='WEEKLY'
    )
    unit = serializers.CharField(default='ratio', read_only=True)
    aggregation_level = serializers.ChoiceField(
        choices=['batch', 'assignment', 'geography'],
        required=False,
        allow_null=True
    )
    series = FCRDataPointSerializer(many=True)

    def to_representation(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert the service response to API representation.

        Args:
            instance: Dictionary from FCRTrendsService.get_fcr_trends()

        Returns:
            Dict: Properly formatted API response
        """
        return {
            'interval': instance.get('interval', 'WEEKLY'),
            'unit': instance.get('unit', 'ratio'),
            'aggregation_level': instance.get('aggregation_level'),
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
