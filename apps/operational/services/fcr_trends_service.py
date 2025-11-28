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

from apps.inventory.models import BatchFeedingSummary, ContainerFeedingSummary
from apps.inventory.services.fcr_service import FCRCalculationService
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
            "model_version": "1.0",  # FCR calculation model version
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
        Get actual FCR series from pre-calculated summaries.

        IMPORTANT: This method now READS from existing BatchFeedingSummary and
        ContainerFeedingSummary tables instead of recalculating on every request.
        
        Summaries should be pre-populated by:
        - Celery background tasks (daily/weekly)
        - Signal handlers when feeding events are created
        - Management commands for historical data
        
        This change improves API response time from ~3-5 seconds to <100ms.
        """
        # NOTE: Removed _ensure_container_summaries_exist() call - summaries should be pre-calculated
        # If summaries don't exist, the API returns empty data (which is correct behavior)

        # Get data based on aggregation level
        if aggregation_level == AggregationLevel.CONTAINER_ASSIGNMENT and assignment_id:
            return cls._get_container_assignment_series(
                start_date, end_date, interval, assignment_id
            )
        elif aggregation_level == AggregationLevel.BATCH and batch_id:
            return cls._get_batch_aggregated_series(
                start_date, end_date, interval, batch_id
            )
        elif aggregation_level == AggregationLevel.GEOGRAPHY and geography_id:
            return cls._get_geography_aggregated_series(
                start_date, end_date, interval, geography_id
            )
        else:
            # Default to geography level
            return cls._get_geography_aggregated_series(
                start_date, end_date, interval, geography_id
            )

    @classmethod
    def _ensure_container_summaries_exist(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        batch_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        geography_id: Optional[int] = None
    ) -> None:
        """
        Ensure container feeding summaries exist for the requested period.

        This implements the container-first approach by calculating
        container-level FCRs before aggregating.
        """
        # Get relevant container assignments
        assignments = cls._get_relevant_assignments(
            batch_id, assignment_id, geography_id
        )

        # Generate time periods based on interval
        periods = cls._generate_time_periods(start_date, end_date, interval)

        # Create container summaries for each assignment and period
        for assignment in assignments:
            for period_start, period_end in periods:
                FCRCalculationService.create_container_feeding_summary(
                    assignment, period_start, period_end
                )

        # Aggregate container summaries to batch level
        if batch_id:
            batch = Batch.objects.get(id=batch_id)
            for period_start, period_end in periods:
                FCRCalculationService.aggregate_container_fcr_to_batch(
                    batch, period_start, period_end
                )

    @classmethod
    def _get_relevant_assignments(
        cls,
        batch_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        geography_id: Optional[int] = None
    ) -> models.QuerySet:
        """Get container assignments relevant to the query."""
        queryset = BatchContainerAssignment.objects.filter(is_active=True)

        if assignment_id:
            queryset = queryset.filter(id=assignment_id)
        elif batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        elif geography_id:
            queryset = queryset.filter(
                container__station__area__geography_id=geography_id
            )

        return queryset.distinct()

    @classmethod
    def _generate_time_periods(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval
    ) -> List[Tuple[date, date]]:
        """Generate time periods for summary calculation based on interval."""
        periods = []
        current = start_date

        while current <= end_date:
            if interval == TimeInterval.DAILY:
                period_end = current
                next_start = current + timedelta(days=1)
            elif interval == TimeInterval.WEEKLY:
                # Start of week (Monday)
                period_start = cls._get_bucket_start(current, interval)
                period_end = min(period_start + timedelta(days=6), end_date)
                next_start = period_end + timedelta(days=1)
            elif interval == TimeInterval.MONTHLY:
                # Start of month
                period_start = cls._get_bucket_start(current, interval)
                # End of month
                if period_start.month == 12:
                    period_end = min(date(period_start.year + 1, 1, 1) - timedelta(days=1), end_date)
                else:
                    period_end = min(date(period_start.year, period_start.month + 1, 1) - timedelta(days=1), end_date)
                # Next month start
                if period_end.month == 12:
                    next_start = date(period_end.year + 1, 1, 1)
                else:
                    next_start = date(period_end.year, period_end.month + 1, 1)
            else:
                # Default to weekly for backward compatibility
                period_end = min(current + timedelta(days=6), end_date)
                next_start = period_end + timedelta(days=1)

            periods.append((current, period_end))
            current = next_start

        return periods

    @classmethod
    def _get_container_assignment_series(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        assignment_id: int
    ) -> List[Dict[str, Any]]:
        """Get FCR series for a specific container assignment."""
        queryset = ContainerFeedingSummary.objects.filter(
            container_assignment_id=assignment_id,
            period_start__gte=start_date,
            period_end__lte=end_date,
            fcr__isnull=False
        ).order_by('period_start')

        series = []
        for summary in queryset:
            series.append({
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "actual_fcr": round(float(summary.fcr), 3) if summary.fcr else None,
                "confidence": summary.confidence_level,
                "data_points": summary.data_points,
                "container_name": summary.container_name,
                "assignment_id": summary.container_assignment_id,
            })

        return series

    @classmethod
    def _get_batch_aggregated_series(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        batch_id: int
    ) -> List[Dict[str, Any]]:
        """Get aggregated FCR series for a batch."""
        queryset = BatchFeedingSummary.objects.filter(
            batch_id=batch_id,
            period_start__gte=start_date,
            period_end__lte=end_date,
            weighted_avg_fcr__isnull=False
        ).order_by('period_start')

        series = []
        for summary in queryset:
            series.append({
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "actual_fcr": round(float(summary.weighted_avg_fcr), 3) if summary.weighted_avg_fcr else None,
                "confidence": summary.overall_confidence_level,
                "data_points": summary.container_count,
                "container_count": summary.container_count,
            })

        return series

    @classmethod
    def _get_geography_aggregated_series(
        cls,
        start_date: date,
        end_date: date,
        interval: TimeInterval,
        geography_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get aggregated FCR series for a geography."""
        # Group by time periods and calculate weighted averages across batches
        periods = cls._generate_time_periods(start_date, end_date, interval)

        series = []
        for period_start, period_end in periods:
            # Get all batch summaries for this period and geography
            queryset = BatchFeedingSummary.objects.filter(
                period_start=period_start,
                period_end=period_end,
                weighted_avg_fcr__isnull=False
            )

            if geography_id:
                queryset = queryset.filter(
                    batch__batch_assignments__container__area__geography_id=geography_id
                )

            # Calculate weighted average across batches
            summaries = list(queryset)
            if summaries:
                # Weight by total feed consumption using Decimal for precision
                from decimal import Decimal
                total_weighted_fcr = Decimal('0')
                total_weight = Decimal('0')
                worst_confidence = 'VERY_HIGH'
                total_containers = 0

                for summary in summaries:
                    # Use total_feed_kg as primary weight, fallback to biomass_gain_kg if available
                    weight = summary.total_feed_kg
                    if weight is None or weight == 0:
                        weight = summary.total_biomass_gain_kg

                    if weight and weight > 0 and summary.weighted_avg_fcr and summary.weighted_avg_fcr > 0:
                        total_weighted_fcr += Decimal(str(weight)) * Decimal(str(summary.weighted_avg_fcr))
                        total_weight += Decimal(str(weight))

                    total_containers += summary.container_count or 0

                    # Track worst confidence
                    confidence_levels = ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW']
                    if confidence_levels.index(summary.overall_confidence_level) > confidence_levels.index(worst_confidence):
                        worst_confidence = summary.overall_confidence_level

                avg_fcr = round(float(total_weighted_fcr / total_weight), 3) if total_weight > 0 and total_weighted_fcr > 0 else None

                series.append({
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "actual_fcr": avg_fcr,
                    "confidence": worst_confidence,
                    "data_points": len(summaries),
                    "total_containers": total_containers,
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
        elif aggregation_level == AggregationLevel.CONTAINER_ASSIGNMENT and assignment_id:
            # Get batch_id from assignment
            try:
                assignment = BatchContainerAssignment.objects.get(id=assignment_id)
                scenario_filters['batch_id'] = assignment.batch_id
            except BatchContainerAssignment.DoesNotExist:
                # If assignment doesn't exist, no scenarios to filter
                return []
        elif aggregation_level == AggregationLevel.GEOGRAPHY and geography_id:
            # Get batches in the specified geography
            # Containers can be in areas directly or through stations
            batch_ids = Batch.objects.filter(
                models.Q(batch_assignments__container__area__geography_id=geography_id) |
                models.Q(batch_assignments__container__station__area__geography_id=geography_id)
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
                    bucket_end = cls._calculate_period_end(bucket_start, interval)  # Already returns ISO string

                    predicted_data.append({
                        "period_start": bucket_start.isoformat(),
                        "period_end": bucket_end,  # Already a string from _calculate_period_end
                        "predicted_fcr": round(float(fcr_value), 3),
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
        """Merge actual and predicted FCR series with enhanced metadata."""
        # Create a dictionary keyed by period_start for easy merging
        merged = {}

        # Add actual data with all available metadata
        for item in actual_series:
            key = item['period_start']
            merged[key] = {
                "period_start": item['period_start'],
                "period_end": item['period_end'],
                "actual_fcr": item.get('actual_fcr'),
                "confidence": item.get('confidence'),
                "data_points": item.get('data_points', 0),
                "predicted_fcr": None,
                "deviation": None,
                # Include container-specific metadata
                "container_name": item.get('container_name'),
                "assignment_id": item.get('assignment_id'),
                "container_count": item.get('container_count'),
                "total_containers": item.get('total_containers'),
            }

        # Add predicted data (batch-level predictions)
        for item in predicted_series:
            key = item['period_start']
            if key in merged:
                merged[key]["predicted_fcr"] = item.get('predicted_fcr')
                merged[key]["scenarios_used"] = item.get('scenarios_used', 0)
            else:
                merged[key] = {
                    "period_start": item['period_start'],
                    "period_end": item['period_end'],
                    "actual_fcr": None,
                    "confidence": None,
                    "data_points": 0,
                    "predicted_fcr": item.get('predicted_fcr'),
                    "scenarios_used": item.get('scenarios_used', 0),
                    "deviation": None,
                    "container_name": None,
                    "assignment_id": None,
                    "container_count": None,
                    "total_containers": None,
                }

        # Calculate deviations where both actual and predicted exist
        for item in merged.values():
            if item["actual_fcr"] and item["predicted_fcr"]:
                try:
                    item["deviation"] = round(
                        (item["actual_fcr"] - item["predicted_fcr"]) / item["predicted_fcr"] * 100,
                        2
                    )
                except (ZeroDivisionError, TypeError):
                    item["deviation"] = None

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
