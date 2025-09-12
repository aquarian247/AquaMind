"""
FCR Calculation Service

Handles Feed Conversion Ratio calculations at the batch level,
including support for mixed batches.
"""
from decimal import Decimal
from django.db import transaction, models
from django.db.models import Sum, Q, Avg
from typing import Optional, Dict, List
from datetime import date

from apps.batch.models import Batch, BatchComposition, GrowthSample, BatchContainerAssignment
from apps.inventory.models import FeedingEvent, BatchFeedingSummary, ContainerFeedingSummary
from apps.infrastructure.models import Geography

class FCRCalculationError(ValueError):
    """Exception raised when FCR calculation fails."""
    pass

class FCRCalculationService:
    """Service for calculating Feed Conversion Ratios at batch level."""
    
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
        # Get total feed consumed by this batch
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )
        
        if not total_feed_consumed or total_feed_consumed == 0:
            return None
            
        if not biomass_gain_kg or biomass_gain_kg <= 0:
            raise FCRCalculationError("Cannot calculate FCR with zero or negative biomass gain")
            
        return total_feed_consumed / biomass_gain_kg
    
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
                # Prorate the feed amount by the composition percentage
                batch_share = event.amount_kg * (composition.percentage / 100)
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
        # Calculate total feed consumed
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )
        
        # Calculate total feed cost
        total_feed_cost = cls.get_batch_feed_cost(
            batch, period_start, period_end
        )
        
        # Calculate FCR
        fcr = None
        if biomass_gain_kg and biomass_gain_kg > 0:
            fcr = cls.calculate_batch_fcr(
                batch, period_start, period_end, biomass_gain_kg
            )
        
        # Get average biomass and feeding percentage from feeding events
        feeding_events = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        )
        
        avg_biomass = feeding_events.aggregate(
            avg=Avg('batch_biomass_kg')
        )['avg']
        
        avg_feeding_pct = feeding_events.aggregate(
            avg=Avg('feeding_percentage')
        )['avg']

        # Check for weighing events in the period
        has_weighing_events = GrowthSample.objects.filter(
            assignment__batch=batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).exists()

        # Calculate confidence level
        confidence_level = cls.calculate_confidence_level(
            batch, period_end
        )

        # Determine estimation method
        estimation_method = cls.determine_estimation_method(
            biomass_gain_kg, has_weighing_events
        )

        # Update or create summary
        summary, created = BatchFeedingSummary.objects.update_or_create(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_feed_consumed_kg': total_feed_consumed,
                # Core feed and growth data
                'total_feed_kg': total_feed_consumed,
                'total_feed_consumed_kg': total_feed_consumed,
                'total_growth_kg': biomass_gain_kg,
                'total_biomass_gain_kg': biomass_gain_kg,
                'weighted_avg_fcr': fcr,
                'fcr': fcr,  # Legacy field for backward compatibility

                # Biomass tracking
                'total_starting_biomass_kg': avg_biomass,
                'total_ending_biomass_kg': (avg_biomass + biomass_gain_kg) if avg_biomass and biomass_gain_kg else avg_biomass,

                # Quality indicators
                'overall_confidence_level': confidence_level,
                'estimation_method': estimation_method,

                # Legacy fields for backward compatibility
                'average_feeding_percentage': avg_feeding_pct,
                'container_count': 1,  # Default for legacy method
            }
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
                # Prorate the feed cost by the composition percentage
                batch_share = event.feed_cost * (composition.percentage / 100)
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
        if not last_weighing_date:
            # Try to find the most recent weighing date for this batch
            latest_growth_sample = GrowthSample.objects.filter(
                assignment__batch=batch
            ).order_by('-sample_date').first()

            if latest_growth_sample:
                last_weighing_date = latest_growth_sample.sample_date

        if not last_weighing_date:
            # No weighing data available
            return 'LOW'

        # Calculate days since last weighing
        days_since_weighing = (period_end - last_weighing_date).days

        if days_since_weighing < 0:
            # Future weighing date (data issue)
            return 'LOW'
        elif days_since_weighing < 10:
            return 'VERY_HIGH'
        elif days_since_weighing < 20:
            return 'HIGH'
        elif days_since_weighing < 40:
            return 'MEDIUM'
        else:
            return 'LOW'

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
        if not biomass_gain_kg:
            return None

        if has_weighing_events:
            return 'MEASURED'
        else:
            return 'INTERPOLATED'

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
        # Calculate total feed consumed
        total_feed_consumed = cls.get_batch_feed_consumption(
            batch, period_start, period_end
        )

        # Calculate total feed cost
        total_feed_cost = cls.get_batch_feed_cost(
            batch, period_start, period_end
        )

        # Calculate FCR
        fcr = None
        if biomass_gain_kg and biomass_gain_kg > 0:
            fcr = cls.calculate_batch_fcr(
                batch, period_start, period_end, biomass_gain_kg
            )

        # Check for weighing events in the period
        has_weighing_events = GrowthSample.objects.filter(
            assignment__batch=batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).exists()

        # Calculate confidence level
        confidence_level = cls.calculate_confidence_level(
            batch, period_end, last_weighing_date
        )

        # Determine estimation method
        estimation_method = cls.determine_estimation_method(
            biomass_gain_kg, has_weighing_events
        )

        # Get average biomass and feeding percentage from feeding events
        feeding_events = FeedingEvent.objects.filter(
            batch=batch,
            feeding_date__gte=period_start,
            feeding_date__lte=period_end
        )

        avg_biomass = feeding_events.aggregate(
            avg=Avg('batch_biomass_kg')
        )['avg']

        avg_feeding_pct = feeding_events.aggregate(
            avg=Avg('feeding_percentage')
        )['avg']

        # Update or create summary
        summary, created = BatchFeedingSummary.objects.update_or_create(
            batch=batch,
            period_start=period_start,
            period_end=period_end,
            defaults={
                # Core feed and growth data
                'total_feed_kg': total_feed_consumed,
                'total_feed_consumed_kg': total_feed_consumed,
                'total_growth_kg': biomass_gain_kg,
                'total_biomass_gain_kg': biomass_gain_kg,
                'weighted_avg_fcr': fcr,
                'fcr': fcr,  # Legacy field for backward compatibility

                # Biomass tracking
                'total_starting_biomass_kg': avg_biomass,
                'total_ending_biomass_kg': (avg_biomass + biomass_gain_kg) if avg_biomass and biomass_gain_kg else avg_biomass,

                # Quality indicators
                'overall_confidence_level': confidence_level,
                'estimation_method': estimation_method,

                # Legacy fields for backward compatibility
                'average_feeding_percentage': avg_feeding_pct,
                'container_count': 1,  # Default for legacy method
            }
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

        Returns container-specific growth data, falling back to batch-level
        if container-specific data is not available.
        """
        # Look for container-specific growth samples
        growth_samples = GrowthSample.objects.filter(
            assignment__batch=container_assignment.batch,
            sample_date__gte=period_start,
            sample_date__lte=period_end
        ).order_by('sample_date')

        if growth_samples.exists():
            # Calculate growth from container-specific samples
            # Note: In practice, growth samples might not be container-specific
            # This is a simplified implementation
            first_sample = growth_samples.first()
            last_sample = growth_samples.last()

            if first_sample and last_sample and first_sample != last_sample:
                # Estimate growth based on available data
                # This is a placeholder - actual implementation would need
                # more sophisticated biomass tracking per container
                growth_kg = Decimal('0')  # Placeholder for container-specific growth
                return {
                    'starting_biomass': None,  # Would need container-specific biomass
                    'ending_biomass': None,
                    'growth_kg': growth_kg,
                    'has_weighing_events': True,
                    'data_points': growth_samples.count(),
                }

        # Fallback: estimate growth based on batch-level data and container proportion
        return cls._estimate_container_growth_from_batch(
            container_assignment, period_start, period_end
        )

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

        # For now, use simple start/end calculation
        # In practice, this would be more sophisticated
        growth_kg = Decimal('0')  # Placeholder - would need proper biomass calculation

        return {
            'starting_biomass': None,  # Would need proper biomass tracking
            'ending_biomass': None,
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

        if not container_summaries.exists():
            return None

        # Calculate weighted averages
        total_feed = Decimal('0')
        total_growth = Decimal('0')
        total_starting_biomass = Decimal('0')
        total_ending_biomass = Decimal('0')
        container_count = 0
        worst_confidence = 'VERY_HIGH'
        estimation_methods = set()

        # Variables for weighted FCR calculation
        weighted_fcr_sum = Decimal('0')
        total_weight = Decimal('0')

        for summary in container_summaries:
            # Accumulate totals for non-weighted metrics
            total_feed += summary.total_feed_kg or 0
            total_growth += summary.growth_kg or 0
            if summary.starting_biomass_kg:
                total_starting_biomass += summary.starting_biomass_kg
            if summary.ending_biomass_kg:
                total_ending_biomass += summary.ending_biomass_kg

            container_count += 1
            estimation_methods.add(summary.estimation_method)

            # Track worst confidence level
            confidence_levels = ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW']
            if confidence_levels.index(summary.confidence_level) > confidence_levels.index(worst_confidence):
                worst_confidence = summary.confidence_level

            # Calculate weighted FCR contribution
            # Use total_feed_kg as primary weight, fallback to biomass_gain_kg if available
            weight = summary.total_feed_kg
            if weight is None or weight == 0:
                # Fallback to biomass gain if feed data unavailable
                weight = summary.growth_kg

            if weight and weight > 0 and summary.fcr and summary.fcr > 0:
                weighted_fcr_sum += Decimal(str(weight)) * Decimal(str(summary.fcr))
                total_weight += Decimal(str(weight))

        # Calculate weighted average FCR (rounded to 3 decimal places for consistency)
        weighted_avg_fcr = None
        if total_weight > 0 and weighted_fcr_sum > 0:
            weighted_avg_fcr = round(weighted_fcr_sum / total_weight, 3)

        # Determine overall estimation method
        if len(estimation_methods) == 1:
            overall_method = list(estimation_methods)[0]
        elif 'INTERPOLATED' in estimation_methods:
            overall_method = 'MIXED' if 'MEASURED' in estimation_methods else 'INTERPOLATED'
        else:
            overall_method = 'MEASURED'

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