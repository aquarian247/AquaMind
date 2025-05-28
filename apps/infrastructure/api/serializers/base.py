"""
Base serializer classes for the infrastructure app.

This module defines base serializer classes to standardize serializer behavior.
"""

from rest_framework import serializers


class TimestampedModelSerializer(serializers.ModelSerializer):
    """Base serializer for models with created_at and updated_at fields."""

    class Meta:
        """Meta configuration for TimestampedModelSerializer."""
        abstract = True
        read_only_fields = ['created_at', 'updated_at']

    def get_fields(self):
        """Get serializer fields and ensure timestamps are read-only."""
        fields = super().get_fields()

        # Ensure created_at and updated_at are read-only
        if 'created_at' in fields:
            fields['created_at'].read_only = True

        if 'updated_at' in fields:
            fields['updated_at'].read_only = True

        return fields


class NamedModelSerializer(serializers.ModelSerializer):
    """Base serializer for models with a name field."""

    class Meta:
        abstract = True

    def validate_name(self, value):
        """Validate that the name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")

        return value.strip()


class LocationModelSerializer(serializers.ModelSerializer):
    """Base serializer for models with latitude and longitude fields."""

    class Meta:
        abstract = True

    def validate_latitude(self, value):
        """Validate that latitude is within range."""
        if value < -90 or value > 90:
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90 degrees."
            )

        return value

    def validate_longitude(self, value):
        """Validate that longitude is within range."""
        if value < -180 or value > 180:
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180 degrees."
            )

        return value


class ExclusiveLocationModelSerializer(serializers.ModelSerializer):
    """Base serializer for models that can be in either a hall or an area.

    This serializer provides validation for models like Container and
    FeedContainer.
    """

    class Meta:
        abstract = True

    def _get_model_name(self):
        """Get the verbose name of the model in title case.

        Returns:
            str: The model's verbose name in title case
        """
        return self.Meta.model._meta.verbose_name.title()

    def validate(self, data):
        """Validate that the model is linked to either a hall or an area.

        Args:
            data: The serializer data

        Returns:
            dict: The validated data

        Raises:
            ValidationError: If model is linked to both or neither location
        """
        hall = data.get('hall')
        area = data.get('area')

        # Check if we're doing a partial update
        if self.partial:
            # If fields aren't provided in the update, use the existing values
            if 'hall' not in data:
                hall = getattr(self.instance, 'hall', None)
            if 'area' not in data:
                area = getattr(self.instance, 'area', None)

        if hall and area:
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"{self._get_model_name()} cannot be linked to "
                    f"both a hall and a sea area"
                ]
            })

        if not hall and not area:
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"{self._get_model_name()} must be linked to "
                    f"either a hall or a sea area"
                ]
            })

        return data
