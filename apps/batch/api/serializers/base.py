"""
Base serializer classes for batch app.

This module contains base serializer classes that standardize common patterns
across the batch app serializers, including:
- Error message formatting
- Read/write field pairs
- Calculated fields handling
"""
from rest_framework import serializers
from apps.batch.api.serializers.utils import DecimalFieldsMixin, NestedModelMixin


class StandardErrorMixin:
    """Mixin to standardize error message formatting across serializers.

    This mixin provides methods to format validation errors consistently
    and to collect errors during validation.
    """

    def format_error(self, message, **kwargs):
        """Format an error message with optional context variables.

        Args:
            message: The error message template
            **kwargs: Context variables to format into the message

        Returns:
            Formatted error message
        """
        return message.format(**kwargs) if kwargs else message

    def add_error(self, errors, field, message, **kwargs):
        """Add an error to the errors dictionary.

        Args:
            errors: Dictionary of errors to add to
            field: Field name to add error for
            message: Error message or template
            **kwargs: Context variables for message formatting

        Returns:
            Updated errors dictionary
        """
        errors[field] = self.format_error(message, **kwargs)
        return errors


class ReadWriteFieldsMixin:
    """Mixin to standardize handling of read/write field pairs.

    This mixin provides methods to create and manage field pairs where
    one field is used for reading (typically a nested representation)
    and another for writing (typically a primary key).
    """

    def create_field_pair(self, name, model_class, source=None, required=True,
                          **kwargs):
        """Create a read/write field pair.

        Args:
            name: Base name for the field (e.g., 'batch')
            model_class: Model class for the related field
            source: Source attribute (only if different from name)
            required: Whether the field is required
            **kwargs: Additional arguments for the fields

        Returns:
            Dictionary with read and write fields
        """
        # Only set source if it's different from the field name
        source_arg = {} if source is None or source == name else {'source': source}

        read_field = serializers.PrimaryKeyRelatedField(
            read_only=True,
            **source_arg
        )

        write_field = serializers.PrimaryKeyRelatedField(
            queryset=model_class.objects.all(),
            write_only=True,
            required=required,
            **source_arg,
            **kwargs
        )

        return {
            name: read_field,
            f"{name}_id": write_field
        }


class BatchBaseSerializer(
    StandardErrorMixin, ReadWriteFieldsMixin,
    NestedModelMixin, DecimalFieldsMixin,
    serializers.ModelSerializer
):
    """Base serializer class for batch app serializers.

    This class combines all the mixins to provide a standardized base
    for all batch app serializers.
    """

    def get_fields(self):
        """Get the fields for the serializer.

        This method is called by DRF to get the fields for the serializer.
        Override in subclasses to add custom field handling.
        """
        return super().get_fields()

    def validate(self, data):
        """Validate the serializer data.

        This method provides a standardized approach to validation
        with error collection.
        """
        errors = {}

        # Perform validation and collect errors
        # Override in subclasses to add custom validation

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(data)
