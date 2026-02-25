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
    """Base serializer for models that can be in hall/area/(optionally carrier).

    This serializer provides validation for models like Container and FeedContainer.
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
        """Validate that the model is linked to one location context.

        Args:
            data: The serializer data

        Returns:
            dict: The validated data

        Raises:
            ValidationError: If model is linked to none or multiple locations
        """
        hall = data.get('hall')
        area = data.get('area')
        has_carrier_field = 'carrier' in self.fields
        carrier = data.get('carrier') if has_carrier_field else None

        # Check if we're doing a partial update
        if self.partial:
            # If fields aren't provided in the update, use the existing values
            if 'hall' not in data:
                hall = getattr(self.instance, 'hall', None)
            if 'area' not in data:
                area = getattr(self.instance, 'area', None)
            if has_carrier_field and 'carrier' not in data:
                carrier = getattr(self.instance, 'carrier', None)

        locations = [hall, area]
        labels = ['hall', 'area']
        if has_carrier_field:
            locations.append(carrier)
            labels.append('carrier')

        provided = [label for label, value in zip(labels, locations) if value]
        if len(provided) != 1:
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"{self._get_model_name()} must be linked to exactly one of "
                    f"{', '.join(labels)}"
                ]
            })

        return data
