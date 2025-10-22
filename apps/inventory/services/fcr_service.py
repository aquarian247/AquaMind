"""
FCR Calculation Service

Handles Feed Conversion Ratio calculations at the batch level,
including support for mixed batches.
"""
from decimal import Decimal
from django.db import transaction, models
from django.db.models import Sum, Q, Avg
from typing import Optional, Dict, List, Tuple
from datetime import date

from apps.batch.models import Batch, BatchComposition, GrowthSample, BatchContainerAssignment
from apps.inventory.models import FeedingEvent, BatchFeedingSummary, ContainerFeedingSummary
from apps.infrastructure.models import Geography

class FCRCalculationError(ValueError):
    """Exception raised when FCR calculation fails."""
    pass

class FCRCalculationService:
    """Service for calculating Feed Conversion Ratios at batch level."""

    # ============================================================================
    # Pure Helper Functions (No Database Dependencies)
    # ============================================================================

    @staticmethod
    def _calculate_fcr_value(
        total_feed_consumed: Decimal,
        biomass_gain_kg: Decimal
    ) -> Decimal:
        """
        Calculate FCR value from feed consumed and biomass gain.

        Args:
            total_feed_consumed: Total feed consumed in kg
            biomass_gain_kg: Biomass gain in kg

        Returns:
            Decimal: FCR value (feed_consumed / biomass_gain)

        Raises:
            FCRCalculationError: If biomass_gain is zero or negative
        """
        if not biomass_gain_kg or biomass_gain_kg <= 0:
            raise FCRCalculationError("Cannot calculate FCR with zero or negative biomass gain")

        if not total_feed_consumed or total_feed_consumed <= 0:
            return Decimal('0')

        return total_feed_consumed / biomass_gain_kg

    @staticmethod
    def _calculate_confidence_level_from_days(days_since_weighing: int) -> str:
        """
        Calculate confidence level based on days since last weighing.

        Args:
            days_since_weighing: Number of days since last weighing event

        Returns:
            str: Confidence level ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')
        """
        if days_since_weighing < 0:
            return 'LOW'  # Future weighing date (data issue)

        if days_since_weighing < 10:
            return 'VERY_HIGH'
        elif days_since_weighing < 20:
            return 'HIGH'
        elif days_since_weighing < 40:
            return 'MEDIUM'
        else:
            return 'LOW'

    @staticmethod
    def _determine_estimation_method_from_data(
        biomass_gain_kg: Optional[Decimal],
        has_weighing_events: bool
    ) -> Optional[str]:
        """
        Determine estimation method based on available data.

        Args:
            biomass_gain_kg: The biomass gain value used
            has_weighing_events: Whether weighing events exist

        Returns:
            str or None: 'MEASURED', 'INTERPOLATED', or None
        """
        if not biomass_gain_kg:
            return None

        return 'MEASURED' if has_weighing_events else 'INTERPOLATED'

    @staticmethod
    def _prorate_feed_by_composition(
        feed_amount: Decimal,
        percentage: Decimal
    ) -> Decimal:
        """
        Calculate prorated feed amount based on composition percentage.

        Args:
            feed_amount: Original feed amount
            percentage: Composition percentage (0-100)

        Returns:
            Decimal: Prorated feed amount
        """
        return feed_amount * (percentage / Decimal('100'))

    @staticmethod
    def _calculate_weighted_average_fcr(
        fcr_contributions: List[Tuple[Decimal, Decimal]]
    ) -> Optional[Decimal]:
        """
        Calculate weighted average FCR from contributions.

        Args:
            fcr_contributions: List of (weight, fcr_value) tuples

        Returns:
            Decimal or None: Weighted average FCR, rounded to 3 decimal places
        """
        if not fcr_contributions:
            return None

        total_weight = Decimal('0')
        weighted_sum = Decimal('0')

        for weight, fcr_value in fcr_contributions:
            if weight > 0 and fcr_value > 0:
                weighted_sum += weight * fcr_value
                total_weight += weight

        if total_weight == 0:
            return None

        # Round to 3 decimal places for consistency
        return round(weighted_sum / total_weight, 3)

    @staticmethod
    def _aggregate_feeding_event_data(
        feeding_events: List[Dict]
    ) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Aggregate biomass and feeding percentage data from feeding events.

        Args:
            feeding_events: List of feeding event dictionaries

        Returns:
            Tuple of (avg_biomass, avg_feeding_pct)
        """
        if not feeding_events:
            return None, None

        total_biomass = Decimal('0')
        total_feeding_pct = Decimal('0')
        count = 0

        for event in feeding_events:
            biomass = event.get('batch_biomass_kg')
            feeding_pct = event.get('feeding_percentage')

            if biomass is not None:
                total_biomass += biomass
                count += 1

            if feeding_pct is not None:
                total_feeding_pct += feeding_pct

        avg_biomass = (total_biomass / count) if count > 0 else None
        avg_feeding_pct = (total_feeding_pct / len(feeding_events)) if feeding_events else None

        return avg_biomass, avg_feeding_pct

    @classmethod
    def calculate_batch_fcr(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date,
        biomass_gain_kg: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """
        Calculate FCR for a batch over a specific period.

        Args:
            batch: The batch to calculate FCR for
            period_start: Start date of the period
            period_end: End date of the period
            biomass_gain_kg: Biomass gain during period (from scenario modeling)

        Returns:
            Decimal: FCR value, or None if cannot be calculated
        """
        # Early return if no biomass gain provided
        if biomass_gain_kg is None:
            return None

        # Get total feed consumed by this batch
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )

        # Early return if no feed consumed
        if not total_feed_consumed or total_feed_consumed == 0:
            return None

        # Use pure helper function for FCR calculation
        return cls._calculate_fcr_value(total_feed_consumed, biomass_gain_kg)
    
    @classmethod
    def get_batch_feed_consumption(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Get total feed consumption for a batch, handling mixed batches.
        
        Args:
            batch: The batch to calculate for
            period_start: Start date of the period
            period_end: End date of the period
            
        Returns:
            Decimal: Total feed consumed in kg
        """
        if batch.batch_type == 'MIXED':
            return cls._get_mixed_batch_feed_consumption(
                batch, period_start, period_end
            )
        else:
            return cls._get_standard_batch_feed_consumption(
                batch, period_start, period_end
            )
    
    @classmethod
    def _get_standard_batch_feed_consumption(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """Get feed consumption for a standard (non-mixed) batch."""
        total_feed = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        ).aggregate(
            total=Sum('amount_kg')
        )['total'] or Decimal('0')
        
        return total_feed
    
    @classmethod
    def _get_mixed_batch_feed_consumption(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Get feed consumption for a mixed batch, prorated by composition.

        For mixed batches, we need to:
        1. Get all feeding events for containers with this mixed batch
        2. Prorate the feed consumption based on batch composition percentages
        """
        # Get all feeding events for containers where this mixed batch is present
        container_assignments = batch.batch_assignments.filter(
            is_active=True
        ).values_list('container_id', flat=True)

        feeding_events = FeedingEvent.objects.filter(
            container_id__in=container_assignments,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        )

        total_prorated_feed = Decimal('0')

        # For each feeding event, calculate this batch's share
        for event in feeding_events:
            # Get the composition percentage for this batch in the container
            composition = BatchComposition.objects.filter(
                mixed_batch=batch,
                source_batch=event.batch  # The original batch being fed
            ).first()

            if composition:
                # Use pure helper function for prorated calculation
                batch_share = cls._prorate_feed_by_composition(
                    event.amount_kg, composition.percentage
                )
                total_prorated_feed += batch_share
            elif event.batch == batch:
                # Direct feeding to this mixed batch
                total_prorated_feed += event.amount_kg

        return total_prorated_feed
    
    @classmethod
    def update_batch_feeding_summary(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date,
        biomass_gain_kg: Optional[Decimal] = None,
        starting_biomass_kg: Optional[Decimal] = None,
        ending_biomass_kg: Optional[Decimal] = None
    ) -> BatchFeedingSummary:
        """
        Update or create a BatchFeedingSummary with FCR calculation.

        Args:
            batch: The batch to update summary for
            period_start: Start date of the period
            period_end: End date of the period
            biomass_gain_kg: Biomass gain from scenario modeling
            starting_biomass_kg: Starting biomass for the period
            ending_biomass_kg: Ending biomass for the period

        Returns:
            BatchFeedingSummary: The updated summary
        """
        # Calculate total feed consumed and cost
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )

        total_feed_cost = cls.get_batch_feed_cost(
            batch, period_start, period_end
        )

        # Aggregate feeding event statistics using helper
        avg_biomass, avg_feeding_pct, has_weighing_events = cls._aggregate_feeding_event_statistics(
            batch, period_start, period_end
        )

        # Calculate confidence level and estimation method
        confidence_level = cls.calculate_confidence_level(batch, period_end)
        estimation_method = cls.determine_estimation_method(biomass_gain_kg, has_weighing_events)

        # Create summary data using helper
        summary_data = cls._create_batch_feeding_summary_data(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            total_feed_consumed=total_feed_consumed,
            total_feed_cost=total_feed_cost,
            biomass_gain_kg=biomass_gain_kg,
            avg_biomass=avg_biomass,
            avg_feeding_pct=avg_feeding_pct,
            has_weighing_events=has_weighing_events,
            confidence_level=confidence_level,
            estimation_method=estimation_method
        )

        # Update or create summary
        summary, created = BatchFeedingSummary.objects.update_or_create(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            defaults=summary_data
        )

        # Add custom attributes for test compatibility
        # (These aren't stored in the model but the tests expect them)
        summary.total_feed_cost = total_feed_cost
        summary.biomass_gain_kg = biomass_gain_kg
        summary.starting_biomass_kg = starting_biomass_kg
        summary.ending_biomass_kg = ending_biomass_kg

        return summary
    
    @classmethod
    def get_batch_feed_cost(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Get total feed cost for a batch over a period.
        
        Args:
            batch: The batch to calculate for
            period_start: Start date of the period
            period_end: End date of the period
            
        Returns:
            Decimal: Total feed cost
        """
        if batch.batch_type == 'MIXED':
            return cls._get_mixed_batch_feed_cost(
                batch, period_start, period_end
            )
        else:
            return cls._get_standard_batch_feed_cost(
                batch, period_start, period_end
            )
    
    @classmethod
    def _get_standard_batch_feed_cost(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """Get feed cost for a standard (non-mixed) batch."""
        total_cost = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end,
            feed_cost__isnull=False
        ).aggregate(
            total=Sum('feed_cost')
        )['total'] or Decimal('0')
        
        return total_cost
    
    @classmethod
    def _get_mixed_batch_feed_cost(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """Get feed cost for a mixed batch, prorated by composition."""
        # Get all feeding events for containers where this mixed batch is present
        container_assignments = batch.batch_assignments.filter(
            is_active=True
        ).values_list('container_id', flat=True)

        feeding_events = FeedingEvent.objects.filter(
            container_id__in=container_assignments,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end,
            feed_cost__isnull=False
        )

        total_prorated_cost = Decimal('0')

        # For each feeding event, calculate this batch's share
        for event in feeding_events:
            # Get the composition percentage for this batch in the container
            composition = BatchComposition.objects.filter(
                mixed_batch=batch,
                source_batch=event.batch
            ).first()

            if composition:
                # Use pure helper function for prorated calculation
                batch_share = cls._prorate_feed_by_composition(
                    event.feed_cost, composition.percentage
                )
                total_prorated_cost += batch_share
            elif event.batch == batch:
                # Direct feeding to this mixed batch
                total_prorated_cost += event.feed_cost

        return total_prorated_cost

    @classmethod
    def calculate_confidence_level(
        cls,
        batch: Batch,
        period_end: date,
        last_weighing_date: Optional[date] = None
    ) -> str:
        """
        Calculate confidence level based on time since last weighing.

        Args:
            batch: The batch to calculate confidence for
            period_end: End date of the period
            last_weighing_date: Date of last weighing (if known)

        Returns:
            str: Confidence level ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW')
        """
        # Determine the last weighing date
        weighing_date = last_weighing_date
        if not weighing_date:
            # Try to find the most recent weighing date for this batch
            latest_growth_sample = GrowthSample.objects.filter(
                assignment__batch=batch
            ).order_by('-sample_date').first()

            weighing_date = latest_growth_sample.sample_date if latest_growth_sample else None

        # Early return if no weighing data available
        if not weighing_date:
            return 'LOW'

        # Calculate days since last weighing and use pure helper
        days_since_weighing = (period_end - weighing_date).days
        return cls._calculate_confidence_level_from_days(days_since_weighing)

    @classmethod
    def determine_estimation_method(
        cls,
        biomass_gain_kg: Optional[Decimal],
        has_weighing_events: bool
    ) -> Optional[str]:
        """
        Determine how the FCR was calculated.

        Args:
            biomass_gain_kg: The biomass gain value used in FCR calculation
            has_weighing_events: Whether weighing events exist for the period

        Returns:
            str or None: 'MEASURED', 'INTERPOLATED', or None if no FCR
        """
        # Use pure helper function
        return cls._determine_estimation_method_from_data(
            biomass_gain_kg, has_weighing_events
        )

    @classmethod
    def update_batch_feeding_summary(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date,
        biomass_gain_kg: Optional[Decimal] = None,
        starting_biomass_kg: Optional[Decimal] = None,
        ending_biomass_kg: Optional[Decimal] = None,
        last_weighing_date: Optional[date] = None
    ) -> BatchFeedingSummary:
        """
        Update or create a BatchFeedingSummary with FCR calculation, confidence, and estimation method.

        Args:
            batch: The batch to update summary for
            period_start: Start date of the period
            period_end: End date of the period
            biomass_gain_kg: Biomass gain from scenario modeling
            starting_biomass_kg: Starting biomass for the period
            ending_biomass_kg: Ending biomass for the period
            last_weighing_date: Date of last weighing for confidence calculation

        Returns:
            BatchFeedingSummary: The updated summary
        """
        # Calculate total feed consumed and cost
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )

        total_feed_cost = cls.get_batch_feed_cost(
            batch, period_start, period_end
        )

        # Aggregate feeding event statistics using helper
        avg_biomass, avg_feeding_pct, has_weighing_events = cls._aggregate_feeding_event_statistics(
            batch, period_start, period_end
        )

        # Calculate confidence level (with optional last_weighing_date) and estimation method
        confidence_level = cls.calculate_confidence_level(
            batch, period_end, last_weighing_date
        )
        estimation_method = cls.determine_estimation_method(biomass_gain_kg, has_weighing_events)

        # Create summary data using helper
        summary_data = cls._create_batch_feeding_summary_data(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            total_feed_consumed=total_feed_consumed,
            total_feed_cost=total_feed_cost,
            biomass_gain_kg=biomass_gain_kg,
            avg_biomass=avg_biomass,
            avg_feeding_pct=avg_feeding_pct,
            has_weighing_events=has_weighing_events,
            confidence_level=confidence_level,
            estimation_method=estimation_method
        )

        # Update or create summary
        summary, created = BatchFeedingSummary.objects.update_or_create(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            defaults=summary_data
        )

        # Add custom attributes for test compatibility
        # (These aren't stored in the model but the tests expect them)
        summary.total_feed_cost = total_feed_cost
        summary.biomass_gain_kg = biomass_gain_kg
        summary.starting_biomass_kg = starting_biomass_kg
        summary.ending_biomass_kg = ending_biomass_kg

        return summary

    @classmethod
    def get_mixed_batch_composition_percentages(
        cls,
        batch: Batch,
        container_id: Optional[int] = None
    ) -> Dict[int, Decimal]:
        """
        Get composition percentages for a mixed batch.

        Args:
            batch: The batch to get composition for
            container_id: Optional container ID to filter by

        Returns:
            Dict[int, Decimal]: Mapping of source batch IDs to percentages
        """
        if batch.batch_type != 'MIXED':
            # For non-mixed batches, return 100% for the batch itself
            return {batch.id: Decimal('100.0')}

        compositions = BatchComposition.objects.filter(
            mixed_batch=batch
        )

        return {
            comp.source_batch.id: comp.percentage
            for comp in compositions
        }

    # ============================================================================
    # Data Aggregation Helpers
    # ============================================================================

    @classmethod
    def _aggregate_feeding_event_statistics(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Tuple[Optional[Decimal], Optional[Decimal], bool]:
        """
        Aggregate feeding event statistics for a batch.

        Args:
            batch: The batch to aggregate data for
            period_start: Start date of the period
            period_end: End date of the period

        Returns:
            Tuple of (avg_biomass, avg_feeding_pct, has_weighing_events)
        """
        # Get feeding events
        feeding_events = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        )

        # Early return if no feeding events
        if not feeding_events.exists():
            return None, None, False

        # Convert queryset to list of dicts for pure function
        event_data = list(feeding_events.values(
            'batch_biomass_kg', 'feeding_percentage'
        ))

        # Use pure helper for aggregation
        avg_biomass, avg_feeding_pct = cls._aggregate_feeding_event_data(event_data)

        # Check for weighing events in the period
        has_weighing_events = GrowthSample.objects.filter(
            assignment__batch=batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).exists()

        return avg_biomass, avg_feeding_pct, has_weighing_events

    @classmethod
    def _create_batch_feeding_summary_data(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date,
        total_feed_consumed: Decimal,
        total_feed_cost: Decimal,
        biomass_gain_kg: Optional[Decimal],
        avg_biomass: Optional[Decimal],
        avg_feeding_pct: Optional[Decimal],
        has_weighing_events: bool,
        confidence_level: str,
        estimation_method: Optional[str]
    ) -> Dict[str, any]:
        """
        Create the data dictionary for BatchFeedingSummary creation/update.

        Args:
            batch: The batch
            period_start/end: Period dates
            total_feed_consumed: Total feed consumed
            total_feed_cost: Total feed cost
            biomass_gain_kg: Biomass gain
            avg_biomass: Average biomass from feeding events
            avg_feeding_pct: Average feeding percentage
            has_weighing_events: Whether weighing events exist
            confidence_level: Calculated confidence level
            estimation_method: Estimation method

        Returns:
            Dict containing all fields for BatchFeedingSummary
        """
        # Calculate ending biomass
        ending_biomass = None
        if avg_biomass is not None and biomass_gain_kg is not None:
            ending_biomass = avg_biomass + biomass_gain_kg

        return {
            # Core feed and growth data
            'total_feed_kg': total_feed_consumed,
            'total_feed_consumed_kg': total_feed_consumed,
            'total_growth_kg': biomass_gain_kg,
            'total_biomass_gain_kg': biomass_gain_kg,
            'weighted_avg_fcr': cls._calculate_fcr_value(total_feed_consumed, biomass_gain_kg) if biomass_gain_kg else None,
            'fcr': cls._calculate_fcr_value(total_feed_consumed, biomass_gain_kg) if biomass_gain_kg else None,  # Legacy field

            # Biomass tracking
            'total_starting_biomass_kg': avg_biomass,
            'total_ending_biomass_kg': ending_biomass,

            # Quality indicators
            'overall_confidence_level': confidence_level,
            'estimation_method': estimation_method,

            # Legacy fields for backward compatibility
            'average_feeding_percentage': avg_feeding_pct,
            'container_count': 1,  # Default for legacy method
        }

    # ============================================================================
    # Container Aggregation Helpers
    # ============================================================================

    @staticmethod
    def _calculate_worst_confidence_level(confidence_levels: List[str]) -> str:
        """
        Calculate the worst (lowest) confidence level from a list.

        Args:
            confidence_levels: List of confidence level strings

        Returns:
            str: Worst confidence level
        """
        if not confidence_levels:
            return 'LOW'

        level_order = ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW']
        worst_level = 'VERY_HIGH'

        for level in confidence_levels:
            if level_order.index(level) > level_order.index(worst_level):
                worst_level = level

        return worst_level

    @staticmethod
    def _determine_overall_estimation_method(estimation_methods: List[str]) -> str:
        """
        Determine overall estimation method from container methods.

        Args:
            estimation_methods: List of estimation method strings

        Returns:
            str: Overall estimation method
        """
        unique_methods = set(method for method in estimation_methods if method)

        if len(unique_methods) == 1:
            return list(unique_methods)[0]
        elif 'INTERPOLATED' in unique_methods:
            return 'MIXED' if 'MEASURED' in unique_methods else 'INTERPOLATED'
        else:
            return 'MEASURED'

    @classmethod
    def _aggregate_container_summary_data(
        cls,
        container_summaries: models.QuerySet
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal, int, str, str, Optional[Decimal]]:
        """
        Aggregate data from container summaries.

        Args:
            container_summaries: QuerySet of ContainerFeedingSummary objects

        Returns:
            Tuple of aggregated data: (total_feed, total_growth, total_starting_biomass,
                                     total_ending_biomass, container_count, worst_confidence,
                                     overall_method, weighted_avg_fcr)
        """
        total_feed = Decimal('0')
        total_growth = Decimal('0')
        total_starting_biomass = Decimal('0')
        total_ending_biomass = Decimal('0')
        container_count = 0
        confidence_levels = []
        estimation_methods = []

        # Variables for weighted FCR calculation
        fcr_contributions = []

        for summary in container_summaries:
            # Accumulate totals for non-weighted metrics
            total_feed += summary.total_feed_kg or Decimal('0')
            total_growth += summary.growth_kg or Decimal('0')

            if summary.starting_biomass_kg:
                total_starting_biomass += summary.starting_biomass_kg
            if summary.ending_biomass_kg:
                total_ending_biomass += summary.ending_biomass_kg

            container_count += 1

            # Collect data for aggregation calculations
            if summary.confidence_level:
                confidence_levels.append(summary.confidence_level)
            if summary.estimation_method:
                estimation_methods.append(summary.estimation_method)

            # Prepare FCR contribution for weighted calculation
            weight = summary.total_feed_kg or summary.growth_kg
            if weight and weight > 0 and summary.fcr and summary.fcr > 0:
                fcr_contributions.append((weight, summary.fcr))

        # Calculate aggregations
        worst_confidence = cls._calculate_worst_confidence_level(confidence_levels)
        overall_method = cls._determine_overall_estimation_method(estimation_methods)
        weighted_avg_fcr = cls._calculate_weighted_average_fcr(fcr_contributions)

        return (
            total_feed, total_growth, total_starting_biomass, total_ending_biomass,
            container_count, worst_confidence, overall_method, weighted_avg_fcr
        )

    # ============================================================================
    # Container-Level FCR Calculations (Option B Implementation)
    # ============================================================================

    @classmethod
    def calculate_container_fcr(
        cls,
        container_assignment: BatchContainerAssignment,
        period_start: date,
        period_end: date
    ) -> Optional[Dict[str, any]]:
        """
        Calculate FCR for a specific container assignment.

        Args:
            container_assignment: The container assignment to calculate FCR for
            period_start: Start date of the period
            period_end: End date of the period

        Returns:
            Dict with FCR data or None if cannot be calculated
        """
        # Get feed consumption for this container
        total_feed = cls._get_container_feed_consumption(
            container_assignment, period_start, period_end
        )

        if not total_feed or total_feed == 0:
            return None

        # Get growth data for this container
        growth_data = cls._get_container_growth_data(
            container_assignment, period_start, period_end
        )

        if not growth_data or not growth_data.get('growth_kg'):
            return None

        # Calculate FCR
        fcr = total_feed / growth_data['growth_kg']

        # Determine confidence level
        confidence_level = cls.calculate_confidence_level(
            container_assignment.batch, period_end,
            container_assignment.last_weighing_date
        )

        # Determine estimation method
        has_weighing_events = growth_data.get('has_weighing_events', False)
        estimation_method = cls.determine_estimation_method(
            growth_data['growth_kg'], has_weighing_events
        )

        return {
            'total_feed_kg': total_feed,
            'starting_biomass_kg': growth_data.get('starting_biomass'),
            'ending_biomass_kg': growth_data.get('ending_biomass'),
            'growth_kg': growth_data['growth_kg'],
            'fcr': fcr,
            'confidence_level': confidence_level,
            'estimation_method': estimation_method,
            'data_points': growth_data.get('data_points', 0),
        }

    @classmethod
    def _get_container_feed_consumption(
        cls,
        container_assignment: BatchContainerAssignment,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Get total feed consumption for a specific container assignment.
        """
        # Get feeding events directly for this container
        feed_events = FeedingEvent.objects.filter(
            container=container_assignment.container,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        )

        # If this is a mixed batch, we need to prorate the feed
        if container_assignment.batch.batch_type == 'MIXED':
            return cls._get_mixed_container_feed_consumption(
                container_assignment, feed_events, period_start, period_end
            )
        else:
            # Standard batch - all feed goes to this assignment
            return feed_events.aggregate(
                total=Sum('amount_kg')
            )['total'] or Decimal('0')

    @classmethod
    def _get_mixed_container_feed_consumption(
        cls,
        container_assignment: BatchContainerAssignment,
        feed_events: models.QuerySet,
        period_start: date,
        period_end: date
    ) -> Decimal:
        """
        Calculate prorated feed consumption for mixed batches in containers.
        """
        total_prorated_feed = Decimal('0')

        for event in feed_events:
            # Find composition for this batch in this container
            composition = BatchComposition.objects.filter(
                mixed_batch=container_assignment.batch,
                source_batch=event.batch,
                container=container_assignment.container
            ).first()

            if composition:
                # Prorate feed by composition percentage
                batch_share = event.amount_kg * (composition.percentage / 100)
                total_prorated_feed += batch_share
            elif event.batch == container_assignment.batch:
                # Direct feeding to this mixed batch
                total_prorated_feed += event.amount_kg

        return total_prorated_feed

    @classmethod
    def _get_container_growth_data(
        cls,
        container_assignment: BatchContainerAssignment,
        period_start: date,
        period_end: date
    ) -> Optional[Dict[str, any]]:
        """
        Get growth data for a specific container assignment.

        Calculates container-specific biomass growth using:
        - Batch-level weight gain (from growth samples)
        - Container-specific population count
        """
        # Look for growth samples for this batch (samples are typically batch-level, not container-specific)
        growth_samples = GrowthSample.objects.filter(
            assignment__batch=container_assignment.batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).order_by('sample_date')

        if not growth_samples.exists():
            # No growth data available
            return None

        first_sample = growth_samples.first()
        last_sample = growth_samples.last()

        if first_sample == last_sample:
            # Only one sample - can't calculate growth
            return None

        # Calculate weight gain per fish (from batch-level samples)
        weight_gain_g = Decimal(str(last_sample.avg_weight_g)) - Decimal(str(first_sample.avg_weight_g))
        
        if weight_gain_g <= 0:
            # No growth or negative growth in this period
            return None
        
        # Use container-specific population for biomass calculation
        container_population = container_assignment.population_count
        
        if container_population == 0:
            return None
        
        # Calculate container-specific growth (weight gain × container population)
        growth_kg = (weight_gain_g / Decimal('1000')) * Decimal(str(container_population))
        
        # Calculate starting and ending biomass for this container
        starting_biomass = (Decimal(str(first_sample.avg_weight_g)) / Decimal('1000')) * Decimal(str(container_population))
        ending_biomass = (Decimal(str(last_sample.avg_weight_g)) / Decimal('1000')) * Decimal(str(container_population))

        return {
            'starting_biomass': starting_biomass,
            'ending_biomass': ending_biomass,
            'growth_kg': growth_kg,
            'has_weighing_events': True,
            'data_points': growth_samples.count(),
        }

    @classmethod
    def _estimate_container_growth_from_batch(
        cls,
        container_assignment: BatchContainerAssignment,
        period_start: date,
        period_end: date
    ) -> Optional[Dict[str, any]]:
        """
        Estimate container growth based on batch-level data and container proportion.
        """
        # Get batch-level growth data
        batch_growth_data = cls._get_batch_growth_data(
            container_assignment.batch, period_start, period_end
        )

        if not batch_growth_data or not batch_growth_data.get('growth_kg'):
            return None

        # Calculate this container's proportion of total batch
        total_batch_population = BatchContainerAssignment.objects.filter(
            batch=container_assignment.batch,
            is_active=True
        ).aggregate(
            total_pop=Sum('population_count')
        )['total_pop'] or 0

        if total_batch_population == 0:
            return None

        container_proportion = (
            container_assignment.population_count / total_batch_population
        )

        # Estimate container growth as proportion of batch growth
        container_growth = batch_growth_data['growth_kg'] * Decimal(str(container_proportion))

        # Estimate container biomass
        starting_biomass = None
        ending_biomass = None
        if container_assignment.avg_weight_g:
            # Estimate based on average weight
            avg_weight_kg = Decimal(str(container_assignment.avg_weight_g)) / 1000
            starting_biomass = avg_weight_kg * container_assignment.population_count
            ending_biomass = starting_biomass + container_growth

        return {
            'starting_biomass': starting_biomass,
            'ending_biomass': ending_biomass,
            'growth_kg': container_growth,
            'has_weighing_events': batch_growth_data.get('has_weighing_events', False),
            'data_points': batch_growth_data.get('data_points', 0),
        }

    @classmethod
    def _get_batch_growth_data(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Optional[Dict[str, any]]:
        """
        Get growth data for a batch (used as fallback for containers).
        
        Calculates biomass growth based on weight gain per fish multiplied by population.
        """
        growth_samples = GrowthSample.objects.filter(
            assignment__batch=batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).order_by('sample_date')

        if not growth_samples.exists():
            return None

        # Calculate batch-level growth
        first_sample = growth_samples.first()
        last_sample = growth_samples.last()

        if first_sample == last_sample:
            # Only one sample - can't calculate growth
            return None

        # Calculate weight gain per fish (in grams)
        weight_gain_g = Decimal(str(last_sample.avg_weight_g)) - Decimal(str(first_sample.avg_weight_g))
        
        if weight_gain_g <= 0:
            # No growth or negative growth in this period
            return None
        
        # Get current population from active assignments
        current_population = batch.batchcontainerassignment_set.filter(
            is_active=True
        ).aggregate(
            total_pop=Sum('population_count')
        )['total_pop'] or 0
        
        if current_population == 0:
            return None
        
        # Calculate total biomass growth (weight gain per fish × population)
        growth_kg = (weight_gain_g / Decimal('1000')) * Decimal(str(current_population))
        
        # Calculate starting and ending biomass estimates
        starting_biomass = (Decimal(str(first_sample.avg_weight_g)) / Decimal('1000')) * Decimal(str(current_population))
        ending_biomass = (Decimal(str(last_sample.avg_weight_g)) / Decimal('1000')) * Decimal(str(current_population))

        return {
            'starting_biomass': starting_biomass,
            'ending_biomass': ending_biomass,
            'growth_kg': growth_kg,
            'has_weighing_events': True,
            'data_points': growth_samples.count(),
        }

    @classmethod
    def create_container_feeding_summary(
        cls,
        container_assignment: BatchContainerAssignment,
        period_start: date,
        period_end: date
    ) -> Optional[ContainerFeedingSummary]:
        """
        Create or update a ContainerFeedingSummary for the given period.
        """
        # Calculate container FCR
        fcr_data = cls.calculate_container_fcr(
            container_assignment, period_start, period_end
        )

        if not fcr_data:
            return None

        # Create or update summary
        summary, created = ContainerFeedingSummary.objects.update_or_create(
            container_assignment=container_assignment,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'batch': container_assignment.batch,
                **fcr_data
            }
        )

        return summary

    @classmethod
    def aggregate_container_fcr_to_batch(
        cls,
        batch: Batch,
        period_start: date,
        period_end: date
    ) -> Optional[BatchFeedingSummary]:
        """
        Aggregate container-level FCRs into a batch-level summary.
        """
        # Get all container summaries for this batch and period
        container_summaries = ContainerFeedingSummary.objects.filter(
            batch=batch,
            period_start=period_start,
            period_end=period_end
        )

        # Early return if no container summaries exist
        if not container_summaries.exists():
            return None

        # Use helper method to aggregate all container data
        (
            total_feed, total_growth, total_starting_biomass, total_ending_biomass,
            container_count, worst_confidence, overall_method, weighted_avg_fcr
        ) = cls._aggregate_container_summary_data(container_summaries)

        # Create or update batch summary
        summary, created = BatchFeedingSummary.objects.update_or_create(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_feed_kg': total_feed,
                'total_growth_kg': total_growth,
                'total_starting_biomass_kg': total_starting_biomass if total_starting_biomass > 0 else None,
                'total_ending_biomass_kg': total_ending_biomass if total_ending_biomass > 0 else None,
                'weighted_avg_fcr': weighted_avg_fcr,
                'fcr': weighted_avg_fcr,  # Legacy field for backward compatibility
                'container_count': container_count,
                'total_feed_consumed_kg': total_feed,
                'total_biomass_gain_kg': total_growth,
                'overall_confidence_level': worst_confidence,
                'estimation_method': overall_method,
            }
        )

        return summary 