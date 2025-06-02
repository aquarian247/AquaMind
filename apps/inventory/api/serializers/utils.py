"""
Utility functions and mixins for serializers in the inventory app.

This module contains reusable components for serializers in the inventory app.
"""
from rest_framework import serializers


class ReadWriteFieldsMixin:
    """
    Mixin for serializers with separate read and write fields.
    
    This mixin helps manage fields that have different representations for
    read and write operations, such as foreign keys that are represented
    by IDs for write operations but by string representations for read operations.
    """
    def get_fields(self):
        """
        Override get_fields to handle read/write field pairs.
        """
        fields = super().get_fields()
        
        # Process fields with _id suffix for write operations
        for field_name, field in list(fields.items()):
            # Skip fields that don't end with _id
            if not field_name.endswith('_id'):
                continue
            
            # Get the base name (without _id)
            base_name = field_name[:-3]
            
            # If there's already a field with the base name, make the _id field write-only
            if base_name in fields:
                field.write_only = True
                # Make the base field read-only if it's a RelatedField
                if isinstance(fields[base_name], serializers.RelatedField):
                    fields[base_name].read_only = True
        
        return fields


class StandardErrorMixin:
    """
    Mixin for standardized error handling in serializers.
    """
    def add_error(self, field, error_message):
        """
        Add a standardized error for a field.
        
        Args:
            field: The field name to add the error to
            error_message: The error message
        """
        if not hasattr(self, '_errors'):
            self._errors = {}
        
        if field not in self._errors:
            self._errors[field] = []
        
        self._errors[field].append(error_message)
    
    def validate(self, attrs):
        """
        Override validate to use standardized error handling.
        """
        # Initialize errors
        self._errors = {}
        
        # Call the parent validate method
        try:
            attrs = super().validate(attrs)
        except serializers.ValidationError as e:
            # Convert DRF validation errors to our format
            if hasattr(e, 'detail'):
                for field, errors in e.detail.items():
                    for error in errors:
                        self.add_error(field, str(error))
        
        # If there are errors, raise a ValidationError
        if hasattr(self, '_errors') and self._errors:
            raise serializers.ValidationError(self._errors)
        
        return attrs


class NestedModelMixin:
    """
    Mixin for serializers that handle nested models.
    
    This mixin provides methods for handling nested serializers and
    creating or updating related objects.
    """
    def create_or_update_related(self, related_data, serializer_class, instance=None):
        """
        Create or update a related object using its serializer.
        
        Args:
            related_data: Data for the related object
            serializer_class: Serializer class for the related object
            instance: Existing instance to update (if any)
            
        Returns:
            The created or updated instance
        """
        if not related_data:
            return None
        
        serializer = serializer_class(instance=instance, data=related_data)
        serializer.is_valid(raise_exception=True)
        return serializer.save()


class InventoryBaseSerializer(StandardErrorMixin, ReadWriteFieldsMixin, serializers.ModelSerializer):
    """
    Base serializer for inventory models.
    
    This serializer combines standard error handling and read/write field management.
    """
    pass
