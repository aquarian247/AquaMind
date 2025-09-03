"""
FCR Trends Service for Operational App

Provides comprehensive FCR trend analysis with actual and predicted FCR calculations,
supporting batch, container assignment, and geography level aggregations.
"""
from decimal import Decimal
from django.db import models
from django.db.models import Avg, Sum, F, Case, When, Value
from django.db.models.functions import TruncWeek, TruncMonth, TruncDay
from typing import List, Dict, Optional, Tuple, Any
from datetime import date, timedelta
from enum import Enum

from apps.inventory.models import BatchFeedingSummary
from apps.batch.models import Batch, BatchContainerAssignment
from apps.scenario.models import Scenario, FCRModelStage
from apps.infrastructure.models import Geography


class AggregationLevel(Enum):
    """Supported aggregation levels for FCR trends."""
    BATCH = "batch"
    CONTAINER_ASSIGNMENT = "assignment"
    GEOGRAPHY = "geography"


class TimeInterval(Enum):
    """Supported time intervals for FCR trends."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class FCRTrendsService:
    """Service for generating FCR trends with actual and predicted data."""

    @classmethod
    def get_fcr_trends(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval = TimeInterval.WEEKLY,
        batch_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        geography_id: Optional[int] = None,
        include_predicted: bool = True
    ) -> Dict[str, Any]:
        """
        Generate FCR trends for the specified parameters.

        Args:
            start_date: Start date for the trend period
            end_date: End date for the trend period
            interval: Time interval for bucketing (DAILY, WEEKLY, MONTHLY)
            batch_id: Optional batch ID for batch-level aggregation
            assignment_id: Optional assignment ID for container-level aggregation
            geography_id: Optional geography ID for geography-level aggregation
            include_predicted: Whether to include predicted FCR from scenarios

        Returns:
            Dict with interval, unit, and series data
        """
        # Determine aggregation level
        aggregation_level = cls._determine_aggregation_level(
            batch_id, assignment_id, geography_id
        )

        # Get actual FCR data
        actual_series = cls._get_actual_fcr_series(
            start_date, end_date, interval, aggregation_level,
            batch_id, assignment_id, geography_id
        )

        # Get predicted FCR data if requested
        predicted_series = []
        if include_predicted:
            predicted_series = cls._get_predicted_fcr_series(
                start_date, end_date, interval, aggregation_level,
                batch_id, assignment_id, geography_id
            )

        # Merge actual and predicted series
        merged_series = cls._merge_series(actual_series, predicted_series)

        return {
            "interval": interval.value,
            "unit": "ratio",
            "aggregation_level": aggregation_level.value,
            "series": merged_series
        }

    @classmethod
    def _determine_aggregation_level(
        cls,
        batch_id: Optional[int],
        assignment_id: Optional[int],
        geography_id: Optional[int]
    ) -> AggregationLevel:
        """Determine the aggregation level based on provided filters."""
        if assignment_id:
            return AggregationLevel.CONTAINER_ASSIGNMENT
        elif batch_id:
            return AggregationLevel.BATCH
        elif geography_id:
            return AggregationLevel.GEOGRAPHY
        else:
            return AggregationLevel.GEOGRAPHY  # Default to geography level

    @classmethod
    def _get_actual_fcr_series(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        aggregation_level: AggregationLevel,
        batch_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        geography_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get actual FCR series from BatchFeedingSummary data.

        Uses TimescaleDB time_bucket function for efficient aggregation.
        """
        # Base queryset
        queryset = BatchFeedingSummary.objects.filter(
            period_start__gte=start_date,
            period_end__lte=end_date,
            fcr__isnull=False
        )

        # Apply filters based on aggregation level
        if aggregation_level == AggregationLevel.CONTAINER_ASSIGNMENT and assignment_id:
            # Filter by specific container assignment
            queryset = queryset.filter(batch__batch_assignments__id=assignment_id)
        elif aggregation_level == AggregationLevel.BATCH and batch_id:
            # Filter by specific batch
            queryset = queryset.filter(batch_id=batch_id)
        elif aggregation_level == AggregationLevel.GEOGRAPHY and geography_id:
            # Filter by geography through container assignments
            queryset = queryset.filter(
                batch__batch_assignments__container__station__area__geography_id=geography_id
            )

        # Apply time bucketing based on interval
        if interval == TimeInterval.WEEKLY:
            bucket_func = TruncWeek('period_start')
            bucket_format = 'period_start'
        elif interval == TimeInterval.MONTHLY:
            bucket_func = TruncMonth('period_start')
            bucket_format = 'period_start'
        else:  # DAILY
            bucket_func = TruncDay('period_start')
            bucket_format = 'period_start'

        # Aggregate by time bucket
        aggregated = queryset.annotate(
            bucket=bucket_func
        ).values('bucket').annotate(
            avg_fcr=Avg('fcr'),
            avg_confidence=Avg(
                Case(
                    When(confidence_level='VERY_HIGH', then=Value(4)),
                    When(confidence_level='HIGH', then=Value(3)),
                    When(confidence_level='MEDIUM', then=Value(2)),
                    When(confidence_level='LOW', then=Value(1)),
                    default=Value(2)
                )
            ),
            count=Sum(1)
        ).order_by('bucket')

        # Convert to series format
        series = []
        for item in aggregated:
            confidence_level = cls._numeric_to_confidence_level(item['avg_confidence'])

            series.append({
                "period_start": item['bucket'].isoformat(),
                "period_end": cls._calculate_period_end(item['bucket'], interval),
                "actual_fcr": float(item['avg_fcr']) if item['avg_fcr'] else None,
                "confidence": confidence_level,
                "data_points": item['count']
            })

        return series

    @classmethod
    def _get_predicted_fcr_series(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        aggregation_level: AggregationLevel,
        batch_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        geography_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get predicted FCR series from scenario data.

        For predicted FCR, we use the FCR values from scenario projections.
        """
        # Find relevant scenarios
        scenario_filters = {}

        if aggregation_level == AggregationLevel.BATCH and batch_id:
            scenario_filters['batch_id'] = batch_id
        elif aggregation_level == AggregationLevel.GEOGRAPHY and geography_id:
            # Get batches in the specified geography
            batch_ids = Batch.objects.filter(
                batch_assignments__container__station__area__geography_id=geography_id
            ).values_list('id', flat=True).distinct()
            scenario_filters['batch_id__in'] = list(batch_ids)

        if not scenario_filters:
            # No specific filters, get all active scenarios
            scenarios = Scenario.objects.filter(
                start_date__lte=end_date,
                duration_days__gt=0
            )
        else:
            scenarios = Scenario.objects.filter(**scenario_filters)

        if not scenarios.exists():
            return []

        # For each scenario, get predicted FCR values
        predicted_data = []

        for scenario in scenarios:
            # Get FCR model stages for this scenario
            fcr_stages = FCRModelStage.objects.filter(
                model=scenario.fcr_model
            ).order_by('stage__order')

            # Generate predicted FCR for each time bucket
            current_date = scenario.start_date

            while current_date <= end_date:
                # Find appropriate FCR stage for current date
                days_elapsed = (current_date - scenario.start_date).days
                fcr_value = cls._get_fcr_for_date(fcr_stages, days_elapsed)

                if fcr_value:
                    bucket_start = cls._get_bucket_start(current_date, interval)
                    bucket_end = cls._calculate_period_end(bucket_start, interval)

                    predicted_data.append({
                        "period_start": bucket_start.isoformat(),
                        "period_end": bucket_end.isoformat(),
                        "predicted_fcr": float(fcr_value),
                        "scenario_name": scenario.name
                    })

                # Move to next interval
                current_date = cls._get_next_bucket_date(current_date, interval)

        # Aggregate predicted data by bucket
        bucketed_predictions = {}
        for item in predicted_data:
            bucket_key = item['period_start']
            if bucket_key not in bucketed_predictions:
                bucketed_predictions[bucket_key] = {
                    "period_start": item['period_start'],
                    "period_end": item['period_end'],
                    "predicted_fcr_values": [],
                    "scenario_count": 0
                }

            bucketed_predictions[bucket_key]["predicted_fcr_values"].append(item["predicted_fcr"])
            bucketed_predictions[bucket_key]["scenario_count"] += 1

        # Calculate averages for each bucket
        series = []
        for bucket_data in bucketed_predictions.values():
            if bucket_data["predicted_fcr_values"]:
                avg_predicted = sum(bucket_data["predicted_fcr_values"]) / len(bucket_data["predicted_fcr_values"])
                series.append({
                    "period_start": bucket_data["period_start"],
                    "period_end": bucket_data["period_end"],
                    "predicted_fcr": round(avg_predicted, 3),
                    "scenarios_used": bucket_data["scenario_count"]
                })

        return sorted(series, key=lambda x: x['period_start'])

    @classmethod
    def _get_fcr_for_date(
        cls,
        fcr_stages: models.QuerySet,
        days_elapsed: int
    ) -> Optional[Decimal]:
        """Get the appropriate FCR value for a given day in the scenario."""
        total_days = 0

        for stage in fcr_stages:
            stage_end = total_days + stage.duration_days

            if total_days <= days_elapsed < stage_end:
                return stage.fcr_value

            total_days = stage_end

        # If we've exceeded all stages, use the last stage's FCR
        if fcr_stages.exists():
            return fcr_stages.last().fcr_value

        return None

    @classmethod
    def _merge_series(
        cls,
        actual_series: List[Dict[str, Any]],
        predicted_series: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge actual and predicted FCR series."""
        # Create a dictionary keyed by period_start for easy merging
        merged = {}

        # Add actual data
        for item in actual_series:
            key = item['period_start']
            merged[key] = {
                "period_start": item['period_start'],
                "period_end": item['period_end'],
                "actual_fcr": item.get('actual_fcr'),
                "confidence": item.get('confidence'),
                "data_points": item.get('data_points', 0),
                "predicted_fcr": None,
                "deviation": None
            }

        # Add predicted data
        for item in predicted_series:
            key = item['period_start']
            if key in merged:
                merged[key]["predicted_fcr"] = item.get('predicted_fcr')
            else:
                merged[key] = {
                    "period_start": item['period_start'],
                    "period_end": item['period_end'],
                    "actual_fcr": None,
                    "confidence": None,
                    "data_points": 0,
                    "predicted_fcr": item.get('predicted_fcr'),
                    "deviation": None
                }

        # Calculate deviations where both actual and predicted exist
        for item in merged.values():
            if item["actual_fcr"] and item["predicted_fcr"]:
                item["deviation"] = round(
                    (item["actual_fcr"] - item["predicted_fcr"]) / item["predicted_fcr"] * 100,
                    2
                )

        # Convert back to list and sort
        return sorted(merged.values(), key=lambda x: x['period_start'])

    @classmethod
    def _numeric_to_confidence_level(cls, avg_confidence: float) -> str:
        """Convert numeric confidence average to text level."""
        if avg_confidence >= 3.5:
            return "VERY_HIGH"
        elif avg_confidence >= 2.5:
            return "HIGH"
        elif avg_confidence >= 1.5:
            return "MEDIUM"
        else:
            return "LOW"

    @classmethod
    def _calculate_period_end(cls, bucket_start: date, interval: TimeInterval) -> str:
        """Calculate the end date for a time bucket."""
        if interval == TimeInterval.WEEKLY:
            end_date = bucket_start + timedelta(days=6)
        elif interval == TimeInterval.MONTHLY:
            # Calculate last day of month
            if bucket_start.month == 12:
                end_date = date(bucket_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(bucket_start.year, bucket_start.month + 1, 1) - timedelta(days=1)
        else:  # DAILY
            end_date = bucket_start

        return end_date.isoformat()

    @classmethod
    def _get_bucket_start(cls, date_val: date, interval: TimeInterval) -> date:
        """Get the start of the time bucket for a given date."""
        if interval == TimeInterval.WEEKLY:
            # Start of week (Monday)
            days_since_monday = date_val.weekday()
            return date_val - timedelta(days=days_since_monday)
        elif interval == TimeInterval.MONTHLY:
            # Start of month
            return date_val.replace(day=1)
        else:  # DAILY
            return date_val

    @classmethod
    def _get_next_bucket_date(cls, current_date: date, interval: TimeInterval) -> date:
        """Get the next bucket date."""
        if interval == TimeInterval.WEEKLY:
            return current_date + timedelta(days=7)
        elif interval == TimeInterval.MONTHLY:
            if current_date.month == 12:
                return date(current_date.year + 1, 1, 1)
            else:
                return date(current_date.year, current_date.month + 1, 1)
        else:  # DAILY
            return current_date + timedelta(days=1)
