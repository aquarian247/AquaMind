"""
Utility functions and mixins for the Health app.

This module provides reusable functions and mixins for serializers and views
in the Health app, focusing on common patterns like decimal formatting,
date validation, and health score calculations.
"""

from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers


def format_decimal(value, precision=2):
    """
    Format a decimal value to the specified precision.
    
    Args:
        value: The value to format (can be float, int, or Decimal)
        precision: The number of decimal places to round to (default: 2)
        
    Returns:
        Decimal: The formatted value as a Decimal object
    """
    if value is None:
        return None
    
    # Convert to Decimal if not already
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    
    # Round to specified precision
    return value.quantize(Decimal(f'0.{"0" * precision}'), rounding=ROUND_HALF_UP)


def validate_date_order(start_date, end_date, start_field_name='start_date', end_field_name='end_date'):
    """
    Validate that start_date comes before end_date.
    
    Args:
        start_date: The start date
        end_date: The end date
        start_field_name: The name of the start date field for error messages
        end_field_name: The name of the end date field for error messages
        
    Raises:
        serializers.ValidationError: If end_date is before start_date
    """
    if start_date and end_date and end_date < start_date:
        raise serializers.ValidationError({
            end_field_name: f"{end_field_name} cannot be before {start_field_name}."
        })


def validate_assignment_date_range(assignment, sample_date, field_name='sample_date'):
    """
    Validate that a sample_date falls within a BatchContainerAssignment's active period.
    
    Args:
        assignment: The BatchContainerAssignment instance
        sample_date: The date to validate
        field_name: The name of the date field for error messages
        
    Raises:
        serializers.ValidationError: If sample_date is outside the assignment's active period
    """
    if sample_date and assignment:
        if sample_date < assignment.assignment_date:
            raise serializers.ValidationError({
                field_name: f"{field_name} ({sample_date}) cannot be before the assignment date ({assignment.assignment_date})."
            })
        if assignment.departure_date and sample_date > assignment.departure_date:
            raise serializers.ValidationError({
                field_name: f"{field_name} ({sample_date}) cannot be after the assignment departure date ({assignment.departure_date})."
            })


def calculate_k_factor(weight_g, length_cm):
    """
    Calculate the condition factor (K-factor) for a fish.
    
    K-factor = (weight in grams) * 100 / (length in cm)^3
    
    Args:
        weight_g: Weight in grams
        length_cm: Length in centimeters
        
    Returns:
        Decimal: The calculated K-factor, or None if inputs are invalid
    """
    if not weight_g or not length_cm or length_cm <= 0:
        return None
    
    # Convert to Decimal if not already
    if not isinstance(weight_g, Decimal):
        weight_g = Decimal(str(weight_g))
    if not isinstance(length_cm, Decimal):
        length_cm = Decimal(str(length_cm))
    
    # Calculate K-factor
    k_factor = (weight_g * Decimal('100')) / (length_cm ** Decimal('3'))
    
    # Round to 4 decimal places
    return format_decimal(k_factor, 4)


def calculate_uniformity(values):
    """
    Calculate the uniformity percentage based on coefficient of variation.
    
    Uniformity = 100 - (standard deviation / mean * 100)
    
    Args:
        values: List of values to calculate uniformity for
        
    Returns:
        Decimal: The calculated uniformity percentage, or None if inputs are invalid
    """
    if not values or len(values) < 2:
        return None
    
    # Convert all values to Decimal
    decimal_values = [Decimal(str(v)) for v in values if v is not None]
    
    if not decimal_values or len(decimal_values) < 2:
        return None
    
    # Calculate mean and standard deviation
    mean = sum(decimal_values) / len(decimal_values)
    
    if mean <= 0:
        return None
    
    # Use statistics module for standard deviation
    try:
        import statistics
        std_dev = Decimal(str(statistics.stdev(decimal_values)))
    except (statistics.StatisticsError, ValueError):
        return None
    
    # Calculate coefficient of variation and uniformity
    cv = (std_dev / mean) * Decimal('100')
    uniformity = Decimal('100') - cv
    
    # Round to 2 decimal places
    return format_decimal(uniformity, 2)


class HealthDecimalFieldsMixin:
    """
    Mixin for standardizing decimal field handling in health app serializers.
    
    This mixin provides methods for formatting decimal fields consistently
    and handling common validation patterns for decimal values.
    """
    
    def format_decimal_field(self, obj, field_name, precision=2):
        """
        Format a decimal field on an object to the specified precision.
        
        Args:
            obj: The object containing the field
            field_name: The name of the field to format
            precision: The number of decimal places to round to
            
        Returns:
            Decimal: The formatted value, or None if the field is None
        """
        value = getattr(obj, field_name, None)
        return format_decimal(value, precision) if value is not None else None
    
    def validate_positive_decimal(self, value, field_name):
        """
        Validate that a decimal value is positive.
        
        Args:
            value: The value to validate
            field_name: The name of the field for error messages
            
        Returns:
            Decimal: The validated value
            
        Raises:
            serializers.ValidationError: If the value is not positive
        """
        if value is not None:
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
            
            if value <= 0:
                raise serializers.ValidationError({
                    field_name: f"{field_name} must be greater than zero."
                })
        
        return value


class NestedHealthModelMixin:
    """
    Mixin for handling nested model serialization in health app serializers.
    
    This mixin provides methods for creating and updating nested models,
    handling common patterns for health-related nested data.
    """
    
    def create_nested_objects(self, validated_data, nested_field, nested_serializer_class):
        """
        Create nested objects from validated data.
        
        Args:
            validated_data: The validated data from the serializer
            nested_field: The name of the field containing nested data
            nested_serializer_class: The serializer class for the nested objects
            
        Returns:
            list: The created nested objects
        """
        nested_data = validated_data.pop(nested_field, [])
        nested_objects = []
        
        for item_data in nested_data:
            serializer = nested_serializer_class(data=item_data)
            serializer.is_valid(raise_exception=True)
            nested_objects.append(serializer)
        
        return nested_objects
    
    def save_nested_objects(self, parent_instance, nested_objects, parent_field_name):
        """
        Save nested objects with a reference to the parent instance.
        
        Args:
            parent_instance: The parent model instance
            nested_objects: List of serializers for the nested objects
            parent_field_name: The name of the field on the nested model that references the parent
            
        Returns:
            list: The saved nested model instances
        """
        saved_objects = []
        
        for serializer in nested_objects:
            # Set the parent reference
            serializer.validated_data[parent_field_name] = parent_instance
            # Save the nested object
            saved_objects.append(serializer.save())
        
        return saved_objects


class UserAssignmentMixin:
    """
    Mixin for handling user assignment in health app serializers.
    
    This mixin provides methods for automatically assigning the current user
    to a model instance during creation or update.
    """
    
    def assign_user(self, validated_data, request, user_field='user'):
        """
        Assign the current user to a model instance if not provided.
        
        Args:
            validated_data: The validated data from the serializer
            request: The request object containing the user
            user_field: The name of the user field on the model
            
        Returns:
            dict: The updated validated data with the user assigned
        """
        # Only assign user if not already provided
        if user_field not in validated_data and request and hasattr(request, 'user'):
            validated_data[user_field] = request.user
        
        return validated_data
