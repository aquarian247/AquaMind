"""
Utility functions and mixins for the infrastructure app.

This module contains reusable components for models and serializers.
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class TimestampedModel(models.Model):
    """Abstract model mixin that provides created_at and updated_at fields.

    This mixin should be used for all models that need to track when they were
    created and last updated.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveModel(models.Model):
    """Abstract model mixin that provides an active flag.

    This mixin should be used for all models that need to be marked as active
    or inactive.
    """

    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class LocationMixin(models.Model):
    """Abstract model mixin for models with latitude and longitude.

    This mixin provides standardized latitude and longitude fields with
    validation.
    """

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            models.validators.MinValueValidator(Decimal('-90')),
            models.validators.MaxValueValidator(Decimal('90'))
        ],
        help_text="Latitude (set when location is selected on map)"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            models.validators.MinValueValidator(Decimal('-180')),
            models.validators.MaxValueValidator(Decimal('180'))
        ],
        help_text="Longitude (set when location is selected on map)"
    )

    class Meta:
        abstract = True


class ExclusiveLocationMixin(models.Model):
    """Abstract model mixin for models that can be in either a hall or an area.

    This mixin provides the common validation logic and database constraints.
    """

    class Meta:
        abstract = True

    def validate_exclusive_location(self, hall_field='hall',
                                     area_field='area'):
        """Validate that the model is linked to either a hall or an area.

        Args:
            hall_field: The name of the hall field (default: 'hall')
            area_field: The name of the area field (default: 'area')

        Raises:
            ValidationError: If the model is linked to both or neither location.
        """
        hall = getattr(self, hall_field)
        area = getattr(self, area_field)

        if hall and area:
            raise ValidationError(
                _(
                    f"{self._meta.verbose_name.title()} cannot be linked to both "
                    f"a hall and a sea area"
                )
            )
        if not hall and not area:
            raise ValidationError(
                _(
                    f"{self._meta.verbose_name.title()} must be linked to either "
                    f"a hall or a sea area"
                )
            )


def get_location_name(obj, hall_field='hall',
                       area_field='area'):
    """Get the location name for an object that can be in either a hall or an area.

    Args:
        obj: The object with hall and area fields
        hall_field: The name of the hall field
        area_field: The name of the area field

    Returns:
        str: The name of the location (hall or area)
    """
    hall = getattr(obj, hall_field)
    area = getattr(obj, area_field)
    return hall.name if hall else area.name


def create_exclusive_location_constraint(model_name, hall_field='hall',
                                         area_field='area'):
    """Create a database constraint for models with exclusive location.

    Args:
        model_name: The name of the model for the constraint name
        hall_field: The name of the hall field
        area_field: The name of the area field

    Returns:
        models.CheckConstraint: A constraint for hall/area exclusivity
    """
    return models.CheckConstraint(
        check=(
            models.Q(**{
                f"{hall_field}__isnull": False,
                f"{area_field}__isnull": True
            }) |
            models.Q(**{
                f"{hall_field}__isnull": True,
                f"{area_field}__isnull": False
            })
        ),
        name=f"{model_name}_in_either_hall_or_area"
    )
