"""
Growth Manager Module

This module handles growth sampling and metrics generation for the AquaMind test data.
It creates realistic growth curves with appropriate patterns for each lifecycle stage.
"""
import random
import datetime
import math
import logging
import traceback
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.batch.models import BatchContainerAssignment, GrowthSample

# Set up logging
logger = logging.getLogger('growth_manager')

class GrowthManager:
    """Manages growth-related data generation."""
    
    def __init__(self):
        """Initialize the growth manager."""
        logger.info("Initializing GrowthManager")
        # Growth parameters by lifecycle stage
        self.stage_growth_ranges = {
            "Egg&Alevin": {
                "weight_range": (0.1, 0.2),         # grams
                "length_range": (1.5, 2.5)          # cm
            },
            "Fry": {
                "weight_range": (0.2, 30.0),        # grams
                "length_range": (2.5, 10.0)         # cm
            },
            "Parr": {
                "weight_range": (30.0, 80.0),       # grams
                "length_range": (10.0, 15.0)        # cm
            },
            "Smolt": {
                "weight_range": (80.0, 120.0),      # grams
                "length_range": (15.0, 20.0)        # cm
            },
            "Post-Smolt": {
                "weight_range": (120.0, 500.0),     # grams
                "length_range": (20.0, 35.0)        # cm
            },
            "Adult": {
                "weight_range": (500.0, 5000.0),    # grams
                "length_range": (35.0, 70.0)        # cm
            }
        }
        
        # Growth patterns by lifecycle stage
        self.growth_patterns = {
            "Egg&Alevin": "minimal",    # Minimal growth
            "Fry": "linear",            # Linear growth
            "Parr": "linear",           # Linear growth
            "Smolt": "linear",          # Linear growth
            "Post-Smolt": "accelerating", # Accelerating growth
            "Adult": "sigmoid"          # Sigmoid growth curve
        }
        logger.info("GrowthManager initialized with growth patterns for all lifecycle stages")
    
    def get_growth_range(self, stage_name):
        """Get the growth ranges for a specific lifecycle stage."""
        growth_range = self.stage_growth_ranges.get(stage_name, {})
        if not growth_range:
            logger.warning(f"No growth range found for stage: {stage_name}")
        return growth_range
    
    def get_growth_pattern(self, stage_name):
        """Get the growth pattern for a specific lifecycle stage."""
        pattern = self.growth_patterns.get(stage_name, "linear")
        logger.debug(f"Growth pattern for {stage_name}: {pattern}")
        return pattern
    
    def _interpolate_growth(self, start_value, end_value, progress, pattern):
        """
        Interpolate growth based on the specified pattern.
        
        Args:
            start_value: Starting value
            end_value: Ending value
            progress: Progress as a fraction between 0 and 1
            pattern: Growth pattern ('minimal', 'linear', 'accelerating', 'sigmoid')
            
        Returns:
            Interpolated value
        """
        try:
            if pattern == "minimal":
                # Minimal growth with slight increase
                return start_value + (end_value - start_value) * (progress * 0.2)
            
            elif pattern == "linear":
                # Linear growth
                return start_value + (end_value - start_value) * progress
            
            elif pattern == "accelerating":
                # Accelerating growth (power curve)
                return start_value + (end_value - start_value) * (progress ** 1.5)
            
            elif pattern == "sigmoid":
                # Sigmoid growth curve
                if progress < 0.001:
                    progress = 0.001
                if progress > 0.999:
                    progress = 0.999
                    
                # Transform progress to -6 to 6 range for sigmoid function
                x = 12 * progress - 6
                sigmoid = 1 / (1 + math.exp(-x))
                
                # Scale sigmoid from 0-1 range
                scaled_sigmoid = (sigmoid - 0.002) / 0.996
                
                return start_value + (end_value - start_value) * scaled_sigmoid
            
            else:
                # Default to linear
                logger.warning(f"Unknown growth pattern '{pattern}', defaulting to linear")
                return start_value + (end_value - start_value) * progress
        except Exception as e:
            logger.error(f"Error in interpolate_growth: {str(e)}")
            logger.error(traceback.format_exc())
            # Return a safe value to avoid crashing
            return start_value + (end_value - start_value) * 0.5
    
    @transaction.atomic
    def generate_growth_samples(self, start_date, end_date=None, sample_interval_days=7):
        """
        Generate growth samples for all active batch container assignments.
        
        Args:
            start_date: The date to start generating samples from
            end_date: The end date (defaults to today)
            sample_interval_days: Interval between samples in days (default: 7)
            
        Returns:
            Total number of growth samples generated
        """
        logger.info(f"Generating growth samples from {start_date} to {end_date or 'today'}")
        try:
            if end_date is None:
                end_date = timezone.now().date()
            
            # Get all active assignments in this period
            logger.info("Querying for batch container assignments")
            try:
                assignments = BatchContainerAssignment.objects.filter(
                    assignment_date__lte=end_date
                ).select_related('batch', 'batch__lifecycle_stage', 'container')
                
                logger.info(f"Found {assignments.count()} batch container assignments")
                
                # Check if any assignments exist
                if assignments.count() == 0:
                    logger.warning("No batch container assignments found for the specified period")
                    print("WARNING: No batch container assignments found for growth samples")
                    return 0
            except Exception as e:
                logger.error(f"Error querying batch container assignments: {str(e)}")
                logger.error(traceback.format_exc())
                return 0
            
            # Process each assignment
            total_samples = 0
            for idx, assignment in enumerate(assignments):
                logger.info(f"Processing assignment {idx+1}/{assignments.count()}: Batch {assignment.batch.batch_number} in {assignment.container.name}")
                
                try:
                    # Check if assignment has the necessary fields
                    if not hasattr(assignment, 'batch') or not assignment.batch:
                        logger.error(f"Assignment {assignment.id} has no batch")
                        continue
                    
                    if not hasattr(assignment.batch, 'lifecycle_stage') or not assignment.batch.lifecycle_stage:
                        logger.error(f"Batch {assignment.batch.id} has no lifecycle_stage")
                        continue
                        
                    # Determine the date range for this assignment
                    assignment_start = max(assignment.assignment_date, start_date)
                    
                    # Handle the case where removal_date is None
                    if hasattr(assignment, 'removal_date'):
                        assignment_end = min(assignment.removal_date or end_date, end_date)
                    else:
                        logger.warning(f"Assignment {assignment.id} has no removal_date attribute, using end_date")
                        assignment_end = end_date
                    
                    # Skip if the assignment doesn't overlap with our target period
                    if assignment_start > assignment_end:
                        logger.warning(f"Assignment {assignment.id} dates don't overlap target period: {assignment_start} > {assignment_end}")
                        continue
                    
                    # Handle the case where is_active field is used instead of removal_date
                    is_active = True
                    if hasattr(assignment, 'is_active'):
                        is_active = assignment.is_active
                        logger.debug(f"Assignment {assignment.id} is_active: {is_active}")
                    
                    if not is_active and assignment_end >= end_date:
                        logger.warning(f"Assignment {assignment.id} is not active and extends to end date, skipping")
                        continue
                    
                    logger.info(f"Generating samples for assignment from {assignment_start} to {assignment_end}")
                    
                    # Generate samples at the specified interval
                    samples_generated = self._generate_assignment_samples(
                        assignment, 
                        assignment_start, 
                        assignment_end, 
                        sample_interval_days
                    )
                    
                    logger.info(f"Generated {samples_generated} samples for this assignment")
                    total_samples += samples_generated
                except Exception as e:
                    logger.error(f"Error processing assignment {assignment.id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    # Continue with next assignment instead of failing entire process
                    continue
            
            logger.info(f"Total growth samples generated: {total_samples}")
            print(f"Generated {total_samples:,} growth samples from {start_date} to {end_date}")
            return total_samples
            
        except Exception as e:
            logger.error(f"Error in generate_growth_samples: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"ERROR generating growth samples: {str(e)}")
            return 0
    
    def _generate_assignment_samples(self, assignment, start_date, end_date, interval_days):
        """Generate growth samples for a specific batch container assignment."""
        try:
            logger.debug(f"Generating assignment samples: Batch {assignment.batch.batch_number}, Container {assignment.container.name}")
            
            # Get stage information
            stage_name = assignment.batch.lifecycle_stage.name
            logger.debug(f"Lifecycle stage: {stage_name}")
            
            growth_range = self.get_growth_range(stage_name)
            growth_pattern = self.get_growth_pattern(stage_name)
            
            if not growth_range:
                logger.warning(f"No growth range found for stage {stage_name}")
                return 0
            
            # Extract weight and length ranges
            weight_start, weight_end = growth_range["weight_range"]
            length_start, length_end = growth_range["length_range"]
            logger.debug(f"Weight range: {weight_start}g to {weight_end}g, Length range: {length_start}cm to {length_end}cm")
            
            # Calculate assignment duration in days
            try:
                # Check if removal_date attribute exists and has value
                if hasattr(assignment, 'removal_date') and assignment.removal_date:
                    stage_duration = (assignment.removal_date - assignment.assignment_date).days
                else:
                    # Default to 90 days if ongoing or no removal_date
                    stage_duration = 90
                    logger.debug(f"Using default stage duration of {stage_duration} days (no removal_date)")
            except Exception as e:
                logger.warning(f"Error calculating stage duration: {str(e)}, using default 90 days")
                stage_duration = 90
            
            logger.debug(f"Stage duration: {stage_duration} days")
            
            # Generate samples on the appropriate days
            current_date = start_date
            samples_count = 0
            
            # Add some small random variation for realistic data
            base_variation = random.uniform(0.95, 1.05)
            logger.debug(f"Base variation factor: {base_variation}")
            
            while current_date <= end_date:
                # Only generate samples on Mondays (weekday=0)
                if current_date.weekday() == 0:
                    try:
                        # Calculate progress through this stage (0 to 1)
                        days_in_stage = (current_date - assignment.assignment_date).days
                        progress = min(1.0, days_in_stage / stage_duration) if stage_duration > 0 else 0.5
                        logger.debug(f"Day {days_in_stage} of stage, progress: {progress:.2f}")
                        
                        # Interpolate weight and length based on progress and pattern
                        avg_weight_g = self._interpolate_growth(
                            weight_start, weight_end, progress, growth_pattern
                        )
                        
                        avg_length_cm = self._interpolate_growth(
                            length_start, length_end, progress, growth_pattern
                        )
                        
                        # Apply small consistent variation for this batch
                        avg_weight_g *= base_variation
                        avg_length_cm *= base_variation
                        
                        # Add daily random noise (±2%)
                        daily_variation = random.uniform(0.98, 1.02)
                        avg_weight_g *= daily_variation
                        avg_length_cm *= daily_variation
                        
                        # Round to appropriate precision
                        avg_weight_g = round(avg_weight_g, 2)
                        avg_length_cm = round(avg_length_cm, 1)
                        
                        logger.debug(f"Sample for {current_date}: Weight={avg_weight_g}g, Length={avg_length_cm}cm")
                        
                        # Determine sample size (1% of population, min 10, max 100)
                        sample_size = min(100, max(10, int(assignment.batch.population_count * 0.01)))
                        
                        # Calculate condition factor
                        condition_factor = self._calculate_condition_factor(avg_weight_g, avg_length_cm)
                        
                        # Create the growth sample
                        try:
                            sample = GrowthSample.objects.create(
                                batch=assignment.batch,
                                sample_date=current_date,
                                avg_weight_g=avg_weight_g,
                                avg_length_cm=avg_length_cm,
                                sample_size=sample_size,
                                condition_factor=condition_factor,
                                std_deviation_weight=avg_weight_g * 0.05,  # Approx 5% std dev
                                std_deviation_length=avg_length_cm * 0.03,  # Approx 3% std dev
                                min_weight_g=avg_weight_g * 0.85,  # Approx min
                                max_weight_g=avg_weight_g * 1.15,  # Approx max
                                notes=f"Auto-generated growth sample for batch {assignment.batch.batch_number}"
                            )
                            logger.debug(f"Created growth sample: {sample}")
                            samples_count += 1
                        except Exception as e:
                            logger.error(f"Error creating growth sample: {str(e)}")
                            logger.error(traceback.format_exc())
                            # Continue trying to create other samples
                    except Exception as e:
                        logger.error(f"Error generating sample for date {current_date}: {str(e)}")
                        logger.error(traceback.format_exc())
                
                # Move to next day
                current_date += datetime.timedelta(days=1)
            
            logger.info(f"Generated {samples_count} growth samples for this assignment")
            return samples_count
            
        except Exception as e:
            logger.error(f"Error in _generate_assignment_samples: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    def _calculate_condition_factor(self, weight_g, length_cm):
        """
        Calculate Fulton's condition factor.
        
        K = (weight in g) * 100 / (length in cm)^3
        """
        try:
            if length_cm <= 0:
                return None
                
            k_factor = (weight_g * 100) / (length_cm ** 3)
            return round(k_factor, 2)
        except Exception as e:
            logger.error(f"Error calculating condition factor: {str(e)}")
            return None
