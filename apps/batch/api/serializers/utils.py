"""
Utility functions and mixins for batch serializers.

This module contains common functionality used across multiple serializers
in the batch app, including decimal formatting, nested serializer patterns,
and validation helpers.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from rest_framework import serializers


def format_decimal(value, decimal_places=2, default="0.00"):
    """
    Convert a value to a formatted decimal string with specified decimal places.
    
    Args:
        value: The value to format (can be Decimal, float, int, or string)
        decimal_places: Number of decimal places to round to
        default: Default value to return if conversion fails
        
    Returns:
        String representation of the decimal value
    """
    if value is None:
        return default
    
    try:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        quantize_string = f"0.{'0' * decimal_places}"
        return str(value.quantize(Decimal(quantize_string), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return default


def calculate_biomass_kg(population_count, avg_weight_g):
    """
    Calculate biomass in kg from population count and average weight in grams.
    
    Args:
        population_count: Number of fish
        avg_weight_g: Average weight per fish in grams
        
    Returns:
        Decimal representing biomass in kg
    """
    if not population_count or not avg_weight_g:
        return Decimal('0.0')
    
    try:
        if not isinstance(population_count, int):
            population_count = int(population_count)
        
        if not isinstance(avg_weight_g, Decimal):
            avg_weight_g = Decimal(str(avg_weight_g))
            
        return (population_count * avg_weight_g) / 1000
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0.0')


def validate_date_order(start_date, end_date, field_name='end_date', error_message=None):
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: The start date
        end_date: The end date to validate
        field_name: The name of the end date field for the error message
        error_message: Custom error message (optional)
        
    Returns:
        Dictionary with validation error or None if valid
    """
    if not start_date or not end_date:
        return None
        
    if end_date <= start_date:
        if not error_message:
            error_message = f"{field_name.replace('_', ' ').title()} must be after start date."
        return {field_name: error_message}
    
    return None


class DecimalFieldsMixin:
    """
    Mixin to add formatted decimal field getters to serializers.
    
    This mixin provides methods to format decimal fields with consistent
    decimal places and handling of None values.
    """
    
    def get_formatted_decimal(self, obj, field_name, decimal_places=2, default="0.00"):
        """
        Get a formatted decimal value from an object attribute.
        
        Args:
            obj: The model instance
            field_name: The name of the field to format
            decimal_places: Number of decimal places to round to
            default: Default value to return if the field is None
            
        Returns:
            String representation of the decimal value
        """
        value = getattr(obj, field_name, None)
        return format_decimal(value, decimal_places, default)


class NestedModelMixin:
    """
    Mixin to add consistent handling of nested model serializers.
    
    This mixin provides methods to create nested serializers with read/write
    field pairs (e.g., 'batch' and 'batch_id').
    """
    
    def get_nested_info(self, obj, related_obj, fields):
        """
        Get a dictionary with basic information about a related object.
        
        Args:
            obj: The parent model instance
            related_obj: The name of the related object attribute
            fields: Dictionary mapping output field names to attribute paths
            
        Returns:
            Dictionary with related object information or None
        """
        if not obj or not hasattr(obj, related_obj) or getattr(obj, related_obj) is None:
            return None
            
        related = getattr(obj, related_obj)
        result = {}
        
        for output_field, attr_path in fields.items():
            # Handle nested attributes with dot notation
            if '.' in attr_path:
                parts = attr_path.split('.')
                value = related
                for part in parts:
                    if value is None:
                        break
                    value = getattr(value, part, None)
                result[output_field] = value
            else:
                result[output_field] = getattr(related, attr_path, None)
                
        return result
