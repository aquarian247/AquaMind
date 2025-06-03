"""
Validation functions for the inventory app.

This module contains reusable validation functions for serializers in the
inventory app.
"""
from decimal import Decimal
from rest_framework import serializers

from apps.batch.models import Batch


def validate_feed_stock_quantity(feed_stock, amount_kg):
    """
    Validate that there is enough stock for a feeding event.

    Args:
        feed_stock: FeedStock instance
        amount_kg: Amount of feed in kg to validate

    Raises:
        serializers.ValidationError: If there is not enough feed in stock
    """
    if not feed_stock:
        return

    # Convert to Decimal if not already
    if not isinstance(amount_kg, Decimal):
        amount_kg = Decimal(str(amount_kg))

    if feed_stock.current_quantity_kg < amount_kg:
        raise serializers.ValidationError(
            "Not enough feed in stock for this feeding event"
        )


def validate_batch_assignment_relationship(batch, batch_assignment):
    """
    Validate that a batch assignment belongs to the specified batch.

    Args:
        batch: Batch instance
        batch_assignment: BatchContainerAssignment instance

    Raises:
        serializers.ValidationError: If the batch assignment doesn't belong to the
            batch
    """
    if not batch or not batch_assignment:
        return

    if batch_assignment.batch.id != batch.id:
        raise serializers.ValidationError(
            "The batch assignment must belong to the specified batch"
        )


def validate_date_range(start_date, end_date):
    """
    Validate that a start date is before an end date.

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        serializers.ValidationError: If the start date is after the end date
    """
    if start_date and end_date and start_date > end_date:
        raise serializers.ValidationError(
            "Start date must be before end date"
        )


def validate_batch_exists(batch_id):
    """
    Validate that a batch exists.

    Args:
        batch_id: Batch ID

    Returns:
        Batch instance if it exists

    Raises:
        serializers.ValidationError: If the batch doesn't exist
    """
    try:
        return Batch.objects.get(pk=batch_id)
    except Batch.DoesNotExist:
        raise serializers.ValidationError("Batch does not exist")


def validate_batch_and_date_range(batch_id, start_date, end_date):
    """
    Validate that a batch exists and date range is valid.

    Args:
        batch_id: Batch ID
        start_date: Start date
        end_date: End date

    Returns:
        Tuple of (batch, start_date, end_date) if validation passes

    Raises:
        serializers.ValidationError: If the batch doesn't exist or date range is
            invalid
    """
    # Validate batch exists
    batch = validate_batch_exists(batch_id)

    # Validate date range
    validate_date_range(start_date, end_date)

    return batch, start_date, end_date
