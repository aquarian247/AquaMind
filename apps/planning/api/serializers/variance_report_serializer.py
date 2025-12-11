"""
Variance Report Serializers

Serializers for variance analysis and reporting of planned vs actual activity execution.
"""

from rest_framework import serializers


class ActivityVarianceItemSerializer(serializers.Serializer):
    """Serializer for individual activity variance data."""
    
    id = serializers.IntegerField()
    batch_number = serializers.CharField()
    batch_id = serializers.IntegerField()
    activity_type = serializers.CharField()
    activity_type_display = serializers.CharField()
    due_date = serializers.DateField()
    completed_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    variance_days = serializers.IntegerField(
        allow_null=True,
        help_text="Days between due_date and completion. Negative=early, 0=on-time, Positive=late"
    )
    is_on_time = serializers.BooleanField(
        allow_null=True,
        help_text="True if completed on or before due_date"
    )


class ActivityTypeStatsSerializer(serializers.Serializer):
    """Serializer for variance statistics grouped by activity type."""
    
    activity_type = serializers.CharField()
    activity_type_display = serializers.CharField()
    total_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    cancelled_count = serializers.IntegerField()
    completion_rate = serializers.FloatField(
        help_text="Percentage of activities completed (excluding cancelled)"
    )
    on_time_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    early_count = serializers.IntegerField()
    on_time_rate = serializers.FloatField(
        help_text="Percentage of completed activities that were on-time or early"
    )
    avg_variance_days = serializers.FloatField(
        allow_null=True,
        help_text="Average variance in days for completed activities"
    )
    min_variance_days = serializers.IntegerField(
        allow_null=True,
        help_text="Minimum variance (most early)"
    )
    max_variance_days = serializers.IntegerField(
        allow_null=True,
        help_text="Maximum variance (most late)"
    )


class VarianceReportSummarySerializer(serializers.Serializer):
    """Serializer for overall variance report summary."""
    
    total_activities = serializers.IntegerField()
    completed_activities = serializers.IntegerField()
    pending_activities = serializers.IntegerField()
    cancelled_activities = serializers.IntegerField()
    overdue_activities = serializers.IntegerField()
    overall_completion_rate = serializers.FloatField(
        help_text="Percentage of total activities completed"
    )
    on_time_activities = serializers.IntegerField()
    late_activities = serializers.IntegerField()
    early_activities = serializers.IntegerField()
    overall_on_time_rate = serializers.FloatField(
        help_text="Percentage of completed activities that were on-time or early"
    )
    avg_variance_days = serializers.FloatField(
        allow_null=True,
        help_text="Average variance in days across all completed activities"
    )


class VarianceTimeSeriesItemSerializer(serializers.Serializer):
    """Serializer for time series variance data point."""
    
    period = serializers.CharField(
        help_text="Period identifier (e.g., '2025-01' for month, '2025-W01' for week)"
    )
    total_due = serializers.IntegerField()
    completed = serializers.IntegerField()
    on_time = serializers.IntegerField()
    late = serializers.IntegerField()
    early = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    on_time_rate = serializers.FloatField()


class VarianceReportSerializer(serializers.Serializer):
    """
    Main serializer for the complete variance report response.
    
    Contains summary statistics, per-activity-type breakdown,
    time series data, and optionally individual activity details.
    """
    
    report_generated_at = serializers.DateTimeField()
    scenario_id = serializers.IntegerField(allow_null=True)
    scenario_name = serializers.CharField(allow_null=True)
    date_range_start = serializers.DateField(allow_null=True)
    date_range_end = serializers.DateField(allow_null=True)
    summary = VarianceReportSummarySerializer()
    by_activity_type = ActivityTypeStatsSerializer(many=True)
    time_series = VarianceTimeSeriesItemSerializer(many=True)
    activities = ActivityVarianceItemSerializer(
        many=True,
        required=False,
        help_text="Individual activity details (only included if include_details=true)"
    )





