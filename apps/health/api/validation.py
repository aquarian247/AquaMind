"""
Validation functions for the Health app.

This module provides reusable validation functions for health-related models,
focusing on common validation patterns like date validation, health parameter
validation, and sampling validation.
"""

from rest_framework import serializers
from decimal import Decimal, InvalidOperation as DecimalException
from datetime import date, timedelta


def validate_health_parameter_score(score, parameter=None):
    """
    Validate that a health parameter score is within the valid range (1-5).
    
    Args:
        score: The score to validate
        parameter: Optional parameter object for more specific validation
        
    Raises:
        serializers.ValidationError: If the score is invalid
    """
    if score is None:
        return
        
    try:
        score_int = int(score)
        if score_int < 1 or score_int > 5:
            raise serializers.ValidationError(
                "Health parameter score must be between 1 and 5."
            )
    except (ValueError, TypeError):
        raise serializers.ValidationError(
            "Health parameter score must be a valid integer."
        )
    
    # If parameter is provided, could add parameter-specific validation here
    return score_int


def validate_sample_size(sample_size, population_count=None):
    """
    Validate that a sample size is reasonable for the population.
    
    Args:
        sample_size: The sample size to validate
        population_count: Optional population count for validation against population
        
    Raises:
        serializers.ValidationError: If the sample size is invalid
    """
    if sample_size is None:
        return
        
    try:
        sample_size_int = int(sample_size)
        if sample_size_int <= 0:
            raise serializers.ValidationError(
                "Sample size must be greater than zero."
            )
            
        # If population count is provided, validate against it
        if population_count is not None:
            if sample_size_int > population_count:
                raise serializers.ValidationError(
                    f"Sample size ({sample_size_int}) cannot exceed "
                    f"the population count ({population_count})."
                )
    except (ValueError, TypeError):
        raise serializers.ValidationError(
            "Sample size must be a valid integer."
        )
    
    return sample_size_int


def validate_health_metrics(weight_g=None, length_cm=None):
    """
    Validate health metrics like weight and length.
    
    Args:
        weight_g: Optional weight in grams to validate
        length_cm: Optional length in centimeters to validate
        
    Raises:
        serializers.ValidationError: If the metrics are invalid
    """
    errors = {}
    
    # Validate weight if provided
    if weight_g is not None:
        try:
            weight_decimal = Decimal(str(weight_g))
            if weight_decimal <= 0:
                errors['weight_g'] = "Weight must be greater than zero."
        except (ValueError, TypeError, DecimalException):
            errors['weight_g'] = "Weight must be a valid number."
    
    # Validate length if provided
    if length_cm is not None:
        try:
            length_decimal = Decimal(str(length_cm))
            if length_decimal <= 0:
                errors['length_cm'] = "Length must be greater than zero."
        except (ValueError, TypeError, DecimalException):
            errors['length_cm'] = "Length must be a valid number."
    
    # Raise all errors at once
    if errors:
        raise serializers.ValidationError(errors)


def validate_treatment_dates(treatment_date, withholding_period_days=None):
    """
    Validate treatment dates and calculate withholding end date.
    
    Args:
        treatment_date: The treatment date
        withholding_period_days: Optional withholding period in days
        
    Returns:
        date: The calculated withholding end date, or None if not applicable
        
    Raises:
        serializers.ValidationError: If the dates are invalid
    """
    if not treatment_date:
        return None
        
    # Validate withholding period if provided
    if withholding_period_days is not None:
        try:
            withholding_days = int(withholding_period_days)
            if withholding_days < 0:
                raise serializers.ValidationError({
                    'withholding_period_days': "Withholding period days must be a non-negative integer."
                })
                
            # Calculate withholding end date
            if isinstance(treatment_date, date):
                return treatment_date + timedelta(days=withholding_days)
        except (ValueError, TypeError):
            raise serializers.ValidationError({
                'withholding_period_days': "Withholding period days must be a valid integer."
            })
    
    return None


def validate_lab_sample_dates(sample_date, date_sent_to_lab=None, date_results_received=None):
    """
    Validate that lab sample dates are in the correct order.
    
    Args:
        sample_date: The date the sample was taken
        date_sent_to_lab: Optional date the sample was sent to the lab
        date_results_received: Optional date the results were received
        
    Raises:
        serializers.ValidationError: If the dates are invalid
    """
    errors = {}
    
    # Validate date order
    if sample_date and date_sent_to_lab and date_sent_to_lab < sample_date:
        errors['date_sent_to_lab'] = "Date sent to lab cannot be before sample date."
    
    if date_sent_to_lab and date_results_received and date_results_received < date_sent_to_lab:
        errors['date_results_received'] = "Date results received cannot be before date sent to lab."
    
    # Raise all errors at once
    if errors:
        raise serializers.ValidationError(errors)
