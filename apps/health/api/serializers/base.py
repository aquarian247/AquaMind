"""
Base serializer classes for the Health app.

This module provides standardized base serializer classes for health-related models,
focusing on consistent error handling, field definition, and validation patterns.
"""

from rest_framework import serializers


class StandardErrorMixin:
    """
    Mixin for standardizing error message formatting.
    
    This mixin provides methods for adding errors to a standardized error
    dictionary and raising validation errors with a consistent format.
    """
    
    def add_error(self, errors, field, message):
        """
        Add an error message to the error dictionary.
        
        Args:
            errors: The error dictionary to add to
            field: The field name to add the error for
            message: The error message
            
        Returns:
            dict: The updated error dictionary
        """
        if field not in errors:
            errors[field] = []
        
        if isinstance(message, list):
            errors[field].extend(message)
        else:
            errors[field].append(message)
        
        return errors
    
    def raise_errors(self, errors):
        """
        Raise validation errors if any exist.
        
        Args:
            errors: The error dictionary to check
            
        Raises:
            serializers.ValidationError: If errors exist
        """
        if errors:
            # Convert lists with single items to strings for cleaner output
            for field, messages in errors.items():
                if len(messages) == 1:
                    errors[field] = messages[0]
            
            raise serializers.ValidationError(errors)


class ReadWriteFieldsMixin:
    """
    Mixin for standardizing read/write field handling.
    
    This mixin provides methods for handling fields that have separate
    read-only and write-only representations, such as foreign keys that
    are represented as IDs for writing but nested objects for reading.
    """
    
    def get_fields(self):
        """
        Get the fields for this serializer, adding read-only fields for
        write-only fields that have a corresponding read-only representation.
        
        Returns:
            dict: The fields for this serializer
        """
        fields = super().get_fields()
        
        # Add read-only fields for write-only fields with a read-only representation
        for field_name, field in list(fields.items()):
            # Check if this is a write-only field with a _id suffix
            if field.write_only and field_name.endswith('_id'):
                # Get the base field name (without _id)
                base_name = field_name[:-3]
                
                # If a read-only field with this base name doesn't already exist,
                # add it as a SerializerMethodField
                if base_name not in fields:
                    fields[base_name] = serializers.SerializerMethodField(read_only=True)
                    
                    # Add a get_<field_name> method if it doesn't exist
                    method_name = f'get_{base_name}'
                    if not hasattr(self, method_name):
                        setattr(self, method_name, self._create_getter(base_name, field_name))
        
        return fields
    
    def _create_getter(self, base_name, field_name):
        """
        Create a getter method for a read-only field.
        
        Args:
            base_name: The base field name (without _id)
            field_name: The field name with _id
            
        Returns:
            function: A getter method for the field
        """
        def getter(obj):
            # Get the related object through the foreign key
            related_obj = getattr(obj, base_name, None)
            
            # If the related object exists, return a dict with its ID and str representation
            if related_obj:
                return {
                    'id': related_obj.id,
                    'name': str(related_obj)
                }
            
            return None
        
        return getter


class HealthBaseSerializer(StandardErrorMixin, ReadWriteFieldsMixin, serializers.ModelSerializer):
    """
    Base serializer for health-related models.
    
    This serializer combines the StandardErrorMixin and ReadWriteFieldsMixin
    to provide a consistent base for all health-related serializers.
    """
    
    def validate(self, data):
        """
        Validate the data for this serializer.
        
        This method provides a standardized approach to validation, collecting
        errors in a dictionary and raising them all at once.
        
        Args:
            data: The data to validate
            
        Returns:
            dict: The validated data
            
        Raises:
            serializers.ValidationError: If validation fails
        """
        errors = {}
        
        # Call the parent validate method if it exists
        try:
            data = super().validate(data)
        except serializers.ValidationError as e:
            # Add the errors from the parent validate method
            if hasattr(e, 'detail'):
                for field, messages in e.detail.items():
                    self.add_error(errors, field, messages)
        
        # Raise all errors at once
        self.raise_errors(errors)
        
        return data
