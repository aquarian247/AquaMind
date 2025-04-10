"""
Utility functions for formatting values in Django admin interfaces.
These functions provide consistent, safe formatting across all admin classes.
"""
from django.utils.html import format_html


def format_decimal(value, precision=2, include_units=None, use_commas=True):
    """
    Safely format decimal values for display in admin interfaces.
    
    Args:
        value: The numeric value to format
        precision: Number of decimal places to display
        include_units: Optional unit string to append (e.g., "kg", "m²")
        use_commas: Whether to include comma separators for thousands
        
    Returns:
        A safely formatted string or "N/A" if value is None
    """
    if value is None:
        return "N/A"
        
    try:
        # Convert to float to ensure consistent formatting
        value = float(value)
        
        # Create format string based on parameters
        format_str = "{:,.{}f}".format(value, precision) if use_commas else "{:.{}f}".format(value, precision)
        
        # Add units if specified
        if include_units:
            result = f"{format_str} {include_units}"
        else:
            result = format_str
            
        return result
    except (ValueError, TypeError):
        return "N/A"


def format_coordinates(value, precision=6):
    """
    Format coordinate values (latitude/longitude) with appropriate precision.
    
    Args:
        value: The coordinate value
        precision: Number of decimal places (default 6 for coordinates)
        
    Returns:
        A formatted coordinate string or "N/A" if value is None
    """
    if value is None:
        return "N/A"
        
    try:
        return "{:.{}f}".format(float(value), precision)
    except (ValueError, TypeError):
        return "N/A"


def format_area(value, precision=2):
    """Format area values with m² unit using HTML superscript."""
    if value is None:
        return "N/A"
        
    try:
        return format_html("{:.{}f} m<sup>2</sup>", float(value), precision)
    except (ValueError, TypeError):
        return "N/A"


def format_volume(value, precision=2):
    """Format volume values with m³ unit using HTML superscript."""
    if value is None:
        return "N/A"
        
    try:
        return format_html("{:.{}f} m<sup>3</sup>", float(value), precision)
    except (ValueError, TypeError):
        return "N/A"


def format_weight(value, precision=2):
    """Format weight values with kg unit."""
    if value is None:
        return "N/A"
        
    try:
        return format_html("{:,.{}f} kg", float(value), precision)
    except (ValueError, TypeError):
        return "N/A"
