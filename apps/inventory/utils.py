"""
Utility functions and mixins for the inventory app.

This module contains reusable components for models and serializers in the
inventory app.
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


def format_decimal(value, decimal_places=2):
    """
    Format a decimal value to a specified number of decimal places.

    Args:
        value: The decimal value to format
        decimal_places: Number of decimal places to round to

    Returns:
        Formatted Decimal value
    """
    if value is None:
        return None

    # Convert to Decimal if not already
    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    # Format with specified decimal places
    return value.quantize(Decimal(f'0.{"0" * decimal_places}'))


def calculate_feeding_percentage(amount_kg, biomass_kg):
    """
    Calculate feeding percentage based on amount and biomass.

    Args:
        amount_kg: Amount of feed in kg
        biomass_kg: Biomass in kg

    Returns:
        Feeding percentage as a Decimal
    """
    if not amount_kg or not biomass_kg or biomass_kg <= 0:
        return None

    # Convert to Decimal if not already
    if not isinstance(amount_kg, Decimal):
        amount_kg = Decimal(str(amount_kg))
    if not isinstance(biomass_kg, Decimal):
        biomass_kg = Decimal(str(biomass_kg))

    # Calculate percentage
    return format_decimal((amount_kg / biomass_kg) * Decimal('100.0'), 2)


def validate_stock_quantity(feed_stock, amount_kg):
    """
    Validate that there is enough stock for a feeding event.

    Args:
        feed_stock: FeedStock instance
        amount_kg: Amount of feed in kg to validate

    Returns:
        True if valid, False otherwise
    """
    if not feed_stock:
        return True

    # Convert to Decimal if not already
    if not isinstance(amount_kg, Decimal):
        amount_kg = Decimal(str(amount_kg))

    return feed_stock.current_quantity_kg >= amount_kg


class TimestampedModelMixin(models.Model):
    """
    Mixin for models with created_at and updated_at fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UpdatedModelMixin(models.Model):
    """
    Mixin for models that only need an updated_at field.
    Use this for models representing continuous state where creation time is not
    meaningful.
    """
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveModelMixin(models.Model):
    """
    Mixin for models with an is_active flag.
    """
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class DecimalFieldMixin:
    """
    Mixin for models with common decimal field definitions.
    """
    @staticmethod
    def percentage_field(max_digits=5, decimal_places=2, **kwargs):
        """Create a percentage field with validators."""
        return models.DecimalField(
            max_digits=max_digits,
            decimal_places=decimal_places,
            validators=[MinValueValidator(0), MaxValueValidator(100)],
            **kwargs
        )

    @staticmethod
    def positive_decimal_field(
            max_digits=10, decimal_places=2, min_value=0, **kwargs):
        """Create a positive decimal field with validators."""
        return models.DecimalField(
            max_digits=max_digits,
            decimal_places=decimal_places,
            validators=[MinValueValidator(min_value)],
            **kwargs
        )
