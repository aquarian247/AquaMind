"""
Feed Recommendation Service Module

This module provides services for calculating optimal feed recommendations
based on batch characteristics, environmental conditions, and lifecycle stage.
"""
import datetime
from decimal import Decimal
from typing import Optional, Dict, Tuple, List, Any

from django.db.models import Q, Avg
from django.utils import timezone

from apps.batch.models import BatchContainerAssignment, LifeCycleStage
from apps.environmental.models import EnvironmentalReading, EnvironmentalParameter
from apps.inventory.models import Feed, FeedRecommendation, FeedingEvent


class FeedRecommendationService:
    """
    Service for calculating and generating feed recommendations.
    
    This service analyzes batch, container, and environmental data to generate
    optimal feed recommendations tailored to specific containers and conditions.
    """
    
    # Optimal temperature ranges for feeding as percentage of optimal (1.0 = 100%)
    TEMP_EFFICIENCY_RANGES = {
        # temp_c: efficiency_factor (as decimal 0.0-1.0)
        # These are example values and should be adjusted based on species-specific data
        'cold': {'min': Decimal('0.0'), 'max': Decimal('8.0'), 'factor': Decimal('0.5')},
        'cool': {'min': Decimal('8.0'), 'max': Decimal('12.0'), 'factor': Decimal('0.7')},
        'optimal': {'min': Decimal('12.0'), 'max': Decimal('18.0'), 'factor': Decimal('1.0')},
        'warm': {'min': Decimal('18.0'), 'max': Decimal('22.0'), 'factor': Decimal('0.8')},
        'hot': {'min': Decimal('22.0'), 'max': Decimal('100.0'), 'factor': Decimal('0.6')}
    }
    
    # Optimal dissolved oxygen ranges (mg/L) and their efficiency factors
    DO_EFFICIENCY_RANGES = {
        'critical': {'min': Decimal('0.0'), 'max': Decimal('4.0'), 'factor': Decimal('0.3')},
        'poor': {'min': Decimal('4.0'), 'max': Decimal('6.0'), 'factor': Decimal('0.6')},
        'adequate': {'min': Decimal('6.0'), 'max': Decimal('8.0'), 'factor': Decimal('0.9')},
        'optimal': {'min': Decimal('8.0'), 'max': Decimal('12.0'), 'factor': Decimal('1.0')},
        'super_saturated': {'min': Decimal('12.0'), 'max': Decimal('100.0'), 'factor': Decimal('0.8')}
    }
    
    # Base feeding percentages by lifecycle stage (% of biomass)
    BASE_FEEDING_PERCENTAGES = {
        # stage_name: base_percentage (as decimal)
        'Egg & Alevin': Decimal('0'),  # No external feeding
        'Fry': Decimal('5.0'),         # 5% of biomass
        'Parr': Decimal('3.0'),        # 3% of biomass
        'Smolt': Decimal('2.0'),       # 2% of biomass
        'Post-Smolt': Decimal('1.5'),  # 1.5% of biomass
        'Adult': Decimal('1.0')        # 1% of biomass
    }
    
    # Recommended feedings per day by lifecycle stage
    FEEDINGS_PER_DAY = {
        'Egg & Alevin': 0,
        'Fry': 8,
        'Parr': 6,
        'Smolt': 4,
        'Post-Smolt': 3,
        'Adult': 2
    }
    
    @classmethod
    def get_temperature_efficiency(cls, temperature_c: Decimal) -> Decimal:
        """
        Calculate feeding efficiency factor based on water temperature.
        
        Args:
            temperature_c: Water temperature in Celsius
            
        Returns:
            Decimal: Efficiency factor (0.0-1.0) to apply to base feeding rate
        """
        if temperature_c is None:
            return Decimal('0.8')  # Default if no temperature data
            
        for range_name, range_data in cls.TEMP_EFFICIENCY_RANGES.items():
            if range_data['min'] <= temperature_c < range_data['max']:
                return range_data['factor']
                
        # Fallback to a reasonable default
        return Decimal('0.7')
    
    @classmethod
    def get_oxygen_efficiency(cls, dissolved_oxygen_mg_l: Decimal) -> Decimal:
        """
        Calculate feeding efficiency factor based on dissolved oxygen levels.
        
        Args:
            dissolved_oxygen_mg_l: Dissolved oxygen in mg/L
            
        Returns:
            Decimal: Efficiency factor (0.0-1.0) to apply to base feeding rate
        """
        if dissolved_oxygen_mg_l is None:
            return Decimal('0.8')  # Default if no DO data
            
        for range_name, range_data in cls.DO_EFFICIENCY_RANGES.items():
            if range_data['min'] <= dissolved_oxygen_mg_l < range_data['max']:
                return range_data['factor']
                
        # Fallback to a reasonable default
        return Decimal('0.7')
    
    @classmethod
    def get_recommended_feed_type(cls, lifecycle_stage: LifeCycleStage) -> Optional[Feed]:
        """
        Determine the most appropriate feed type based on lifecycle stage.
        
        Args:
            lifecycle_stage: The lifecycle stage of the batch
            
        Returns:
            Feed: The recommended feed object or None if no suitable feed found
        """
        # Map lifecycle stages to appropriate feed size categories
        stage_to_feed_size = {
            'Egg & Alevin': None,  # No feeding
            'Fry': 'MICRO',
            'Parr': 'SMALL',
            'Smolt': 'MEDIUM', 
            'Post-Smolt': 'MEDIUM',
            'Adult': 'LARGE'
        }
        
        stage_name = lifecycle_stage.name
        feed_size = stage_to_feed_size.get(stage_name)
        
        if not feed_size:
            return None
            
        # Find active feeds of the appropriate size
        recommended_feeds = Feed.objects.filter(
            size_category=feed_size,
            is_active=True
        ).order_by('-protein_percentage')  # Prefer higher protein content
        
        if recommended_feeds.exists():
            return recommended_feeds.first()
            
        return None
    
    @classmethod
    def get_recent_environmental_readings(
        cls, 
        assignment: BatchContainerAssignment,
        hours_lookback: int = 24
    ) -> Dict[str, Decimal]:
        """
        Retrieve recent environmental readings for a container.
        
        Args:
            assignment: The batch container assignment to check
            hours_lookback: How many hours back to consider for readings
            
        Returns:
            Dict: Dictionary of parameter names and their average values
        """
        lookback_time = timezone.now() - datetime.timedelta(hours=hours_lookback)
        
        # Try to get parameters we need
        try:
            temp_param = EnvironmentalParameter.objects.get(name__icontains='temperature')
            oxygen_param = EnvironmentalParameter.objects.get(name__icontains='oxygen')
        except EnvironmentalParameter.DoesNotExist:
            # If parameters don't exist, return empty values
            return {'water_temperature_c': None, 'dissolved_oxygen_mg_l': None}
        
        # Get recent readings
        temp_readings = EnvironmentalReading.objects.filter(
            container=assignment.container,
            parameter=temp_param,
            reading_time__gte=lookback_time
        ).aggregate(avg_value=Avg('value'))
        
        oxygen_readings = EnvironmentalReading.objects.filter(
            container=assignment.container,
            parameter=oxygen_param,
            reading_time__gte=lookback_time
        ).aggregate(avg_value=Avg('value'))
        
        return {
            'water_temperature_c': temp_readings.get('avg_value'),
            'dissolved_oxygen_mg_l': oxygen_readings.get('avg_value')
        }
    
    @classmethod
    def calculate_feed_recommendation(
        cls, 
        assignment: BatchContainerAssignment,
        target_date: Optional[datetime.date] = None
    ) -> Dict[str, Any]:
        """
        Calculate the recommended feed amount and type for a batch container assignment.
        
        Args:
            assignment: The batch container assignment to generate a recommendation for
            target_date: The date for which to generate the recommendation (defaults to today)
            
        Returns:
            Dict: Recommendation data including feed_type, amount_kg, and environmental factors
        """
        if target_date is None:
            target_date = timezone.now().date()
            
        # Get latest environment readings
        env_readings = cls.get_recent_environmental_readings(assignment)
        
        # Get lifecycle stage
        lifecycle_stage = assignment.lifecycle_stage
        
        # Determine base feeding percentage based on lifecycle stage
        base_feeding_pct = cls.BASE_FEEDING_PERCENTAGES.get(
            lifecycle_stage.name, 
            Decimal('1.0')  # Default to 1% if stage not found
        )
        
        # Apply temperature efficiency
        temp_efficiency = cls.get_temperature_efficiency(env_readings['water_temperature_c'])
        
        # Apply oxygen efficiency
        oxygen_efficiency = cls.get_oxygen_efficiency(env_readings['dissolved_oxygen_mg_l'])
        
        # Calculate combined efficiency factor
        combined_efficiency = min(temp_efficiency, oxygen_efficiency)
        
        # Calculate adjusted feeding percentage
        adjusted_feeding_pct = base_feeding_pct * combined_efficiency
        
        # Calculate recommended feed amount
        biomass_kg = assignment.biomass_kg
        recommended_kg = (biomass_kg * adjusted_feeding_pct) / Decimal('100.0')
        
        # Determine recommended feed type
        recommended_feed = cls.get_recommended_feed_type(lifecycle_stage)
        
        # Get recommended feedings per day
        feedings_per_day = cls.FEEDINGS_PER_DAY.get(lifecycle_stage.name, 2)
        
        # Build the recommendation explanation
        reason_parts = []
        reason_parts.append(f"Lifecycle stage '{lifecycle_stage.name}' base feeding: {base_feeding_pct}% of biomass.")
        
        if env_readings['water_temperature_c']:
            reason_parts.append(
                f"Temperature efficiency factor: {temp_efficiency} "
                f"(based on {env_readings['water_temperature_c']}°C)"
            )
            
        if env_readings['dissolved_oxygen_mg_l']:
            reason_parts.append(
                f"Oxygen efficiency factor: {oxygen_efficiency} "
                f"(based on {env_readings['dissolved_oxygen_mg_l']} mg/L DO)"
            )
            
        reason_parts.append(f"Combined efficiency factor: {combined_efficiency}")
        reason_parts.append(f"Adjusted feeding percentage: {adjusted_feeding_pct}% of biomass")
        reason_parts.append(f"Biomass: {biomass_kg} kg")
        reason_parts.append(f"Recommended feed amount: {recommended_kg} kg")
        
        if recommended_feed:
            reason_parts.append(f"Recommended feed type: {recommended_feed.name} ({recommended_feed.brand})")
        else:
            reason_parts.append("No suitable feed type found based on lifecycle stage.")
            
        reason_parts.append(f"Recommended feedings per day: {feedings_per_day}")
        
        recommendation_reason = "\n".join(reason_parts)
        
        # Estimate expected FCR
        # This is a simplification - a more sophisticated model would consider historical data
        expected_fcr = Decimal('1.2')  # Example default
        
        return {
            'batch_container_assignment': assignment,
            'recommended_date': target_date,
            'feed': recommended_feed,
            'recommended_feed_kg': recommended_kg.quantize(Decimal('0.001')),  
            'feeding_percentage': adjusted_feeding_pct.quantize(Decimal('0.01')),
            'feedings_per_day': feedings_per_day,
            'water_temperature_c': env_readings['water_temperature_c'],
            'dissolved_oxygen_mg_l': env_readings['dissolved_oxygen_mg_l'],
            'recommendation_reason': recommendation_reason,
            'expected_fcr': expected_fcr
        }
    
    @classmethod
    def create_recommendation(
        cls, 
        assignment: BatchContainerAssignment,
        target_date: Optional[datetime.date] = None,
        save: bool = True
    ) -> Tuple[Optional[FeedRecommendation], bool]:
        """
        Create a feed recommendation for a batch container assignment.
        
        Args:
            assignment: The batch container assignment to create a recommendation for
            target_date: The date for which to generate the recommendation (defaults to today)
            save: Whether to save the recommendation to the database
            
        Returns:
            Tuple[Optional[FeedRecommendation], bool]: The recommendation object (or None if no valid feed) and whether it was created
        """
        if target_date is None:
            target_date = timezone.now().date()
            
        # Check if a recommendation already exists for this assignment and date
        existing = FeedRecommendation.objects.filter(
            batch_container_assignment=assignment,
            recommended_date=target_date
        ).first()
        
        if existing:
            return existing, False
            
        # Calculate the recommendation
        recommendation_data = cls.calculate_feed_recommendation(assignment, target_date)
        
        # Skip if no valid feed was found
        if not recommendation_data['feed']:
            print(f"No valid feed found for assignment {assignment}. Skipping recommendation.")
            return None, False
            
        # Create the recommendation object
        recommendation = FeedRecommendation(
            batch_container_assignment=recommendation_data['batch_container_assignment'],
            recommended_date=recommendation_data['recommended_date'],
            feed=recommendation_data['feed'],
            recommended_feed_kg=recommendation_data['recommended_feed_kg'],
            feeding_percentage=recommendation_data['feeding_percentage'],
            feedings_per_day=recommendation_data['feedings_per_day'],
            water_temperature_c=recommendation_data['water_temperature_c'],
            dissolved_oxygen_mg_l=recommendation_data['dissolved_oxygen_mg_l'],
            recommendation_reason=recommendation_data['recommendation_reason'],
            expected_fcr=recommendation_data['expected_fcr']
        )
        
        if save:
            recommendation.save()
            
        return recommendation, True
    
    @classmethod
    def create_recommendations_for_container(
        cls,
        container_id: int,
        target_date: Optional[datetime.date] = None
    ) -> List[FeedRecommendation]:
        """
        Create feed recommendations for all active batch assignments in a container.
        
        Args:
            container_id: The ID of the container to create recommendations for
            target_date: The date for which to create recommendations (defaults to today)
            
        Returns:
            List[FeedRecommendation]: List of created recommendations
        """
        from apps.infrastructure.models import Container
        
        # Default to today if no date provided
        if target_date is None:
            target_date = timezone.now().date()
            
        try:
            container = Container.objects.get(id=container_id)
            # Skip if feed recommendations are disabled for this container
            if not container.feed_recommendations_enabled:
                return []
        except Container.DoesNotExist:
            return []
            
        # Get all active assignments for this container
        assignments = BatchContainerAssignment.objects.filter(
            container_id=container_id,
            is_active=True
        )
        
        recommendations = []
        for assignment in assignments:
            recommendation, created = cls.create_recommendation(assignment, target_date)
            if recommendation and created:  # Only include valid recommendations that were created
                recommendations.append(recommendation)
                
        return recommendations
    
    @classmethod
    def generate_all_recommendations(cls, target_date: Optional[datetime.date] = None) -> int:
        """
        Generate feed recommendations for all active batch container assignments.
        
        Args:
            target_date: The date for which to generate recommendations (defaults to today)
            
        Returns:
            int: Number of recommendations created
        """
        # Default to today if no date provided
        if target_date is None:
            target_date = timezone.now().date()
            
        # Get all active batch container assignments where container has recommendations enabled
        assignments = BatchContainerAssignment.objects.filter(
            is_active=True,
            container__feed_recommendations_enabled=True
        )
        
        count = 0
        for assignment in assignments:
            recommendation, created = cls.create_recommendation(assignment, target_date)
            if recommendation and created:
                count += 1
                
        return count


class FeedingEfficiencyService:
    """
    Service for analyzing and calculating feeding efficiency metrics.
    
    This service helps track and analyze the effectiveness of feeding strategies,
    including Feed Conversion Ratio (FCR) calculations and feeding efficiency.
    """
    
    @classmethod
    def calculate_fcr(
        cls,
        batch_id: int,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Optional[Decimal]:
        """
        Calculate the Feed Conversion Ratio for a batch over a specified period.
        
        FCR = Total Feed Given / Weight Gain
        
        Args:
            batch_id: The ID of the batch
            start_date: Start date for the calculation period
            end_date: End date for the calculation period
            
        Returns:
            Decimal: The FCR value or None if cannot be calculated
        """
        # Get total feed given
        feed_events = FeedingEvent.objects.filter(
            batch_id=batch_id,
            feeding_date__gte=start_date,
            feeding_date__lte=end_date
        )
        
        if not feed_events.exists():
            return None
            
        # Calculate total feed
        total_feed_kg = sum(event.amount_kg for event in feed_events)
        
        # Find weight at start and end
        start_event = feed_events.filter(feeding_date=start_date).first()
        end_event = feed_events.filter(feeding_date=end_date).first()
        
        if not (start_event and end_event):
            return None
            
        start_weight = start_event.batch_biomass_kg
        end_weight = end_event.batch_biomass_kg
        
        weight_gain = end_weight - start_weight
        
        if weight_gain <= 0:
            return None
            
        fcr = total_feed_kg / weight_gain
        return fcr.quantize(Decimal('0.01'))
    
    @classmethod
    def compare_recommendations_to_actual(
        cls,
        batch_id: int,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Compare recommended feed amounts to actual amounts used.
        
        Args:
            batch_id: The ID of the batch
            start_date: Start date for the comparison
            end_date: End date for the comparison
            
        Returns:
            Dict: Stats comparing recommendations vs. actual feeding
        """
        # Get all container assignments for this batch
        assignments = BatchContainerAssignment.objects.filter(
            batch_id=batch_id,
            assignment_date__lte=end_date,
            is_active=True
        )
        
        # Get all recommendations for these assignments
        recommendations = FeedRecommendation.objects.filter(
            batch_container_assignment__in=assignments,
            recommended_date__gte=start_date,
            recommended_date__lte=end_date
        )
        
        # Get actual feeding events
        feed_events = FeedingEvent.objects.filter(
            batch_id=batch_id,
            feeding_date__gte=start_date,
            feeding_date__lte=end_date
        )
        
        # Calculate totals
        total_recommended_kg = sum(rec.recommended_feed_kg for rec in recommendations)
        total_actual_kg = sum(event.amount_kg for event in feed_events)
        
        # Calculate difference
        difference_kg = total_actual_kg - total_recommended_kg
        
        # Calculate percent followed (if positive number is over-feeding)
        percent_difference = (difference_kg / total_recommended_kg * 100) if total_recommended_kg else None
        
        return {
            'total_recommended_kg': total_recommended_kg,
            'total_actual_kg': total_actual_kg,
            'difference_kg': difference_kg,
            'percent_difference': percent_difference,
            'num_recommendations': recommendations.count(),
            'num_feeding_events': feed_events.count()
        }
