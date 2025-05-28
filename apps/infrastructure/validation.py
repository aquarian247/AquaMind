"""
Validation functions for the infrastructure app.

This module contains validation functions that can be reused across models and
serializers in the infrastructure app.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_container_volume(container, container_type_field='container_type',
                              volume_field='volume_m3'):
    """Validate that a container's volume doesn't exceed the max volume.

    Args:
        container: The container object to validate
        container_type_field: The name of the container type field
        volume_field: The name of the volume field

    Raises:
        ValidationError: If the container's volume exceeds the maximum volume
    """
    container_type = getattr(container, container_type_field)
    volume = getattr(container, volume_field)

    if container_type and volume:
        max_volume = getattr(container_type, f'max_{volume_field}')
        if volume > max_volume:
            raise ValidationError({
                volume_field: _(
                    f'Container volume ({volume} m³) cannot exceed max '
                    f'volume for this container type ({max_volume} m³)'
                )
            })


def validate_unique_name_in_location(model_class, name, location_field, location_id,
                                     instance=None):
    """Validate that a name is unique within a specific location.

    Args:
        model_class: The model class to check against
        name: The name to validate
        location_field: The name of the location field (e.g., 'hall', 'area')
        location_id: The ID of the location
        instance: The current instance being validated (optional, for updates)

    Raises:
        ValidationError: If another object with the same name exists in the location
    """
    filter_kwargs = {
        'name': name,
        location_field: location_id
    }

    # Exclude the current instance when updating
    queryset = model_class.objects.filter(**filter_kwargs)
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    if queryset.exists():
        raise ValidationError({
            'name': _(
                f'An object with this name already exists in this '
                f'{location_field}'
            )
        })


def validate_coordinates(latitude, longitude):
    """Validate that latitude and longitude are within valid ranges.

    Args:
        latitude: The latitude value to validate
        longitude: The longitude value to validate

    Raises:
        ValidationError: If latitude or longitude are outside valid ranges
    """
    errors = {}

    if latitude is not None and (latitude < -90 or latitude > 90):
        errors['latitude'] = _('Latitude must be between -90 and 90 degrees')

    if longitude is not None and (longitude < -180 or longitude > 180):
        errors['longitude'] = _(
            'Longitude must be between -180 and 180 degrees'
        )

    if errors:
        raise ValidationError(errors)
