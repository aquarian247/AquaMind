"""
Treatment serializers for health monitoring.

This module defines serializers for treatment models.
"""

from django.core.validators import MinValueValidator
from django.utils import timezone
from rest_framework import serializers

from apps.batch.models import Batch, BatchContainerAssignment
from apps.health.api.serializers.base import HealthBaseSerializer
from apps.health.api.utils import HealthDecimalFieldsMixin, UserAssignmentMixin
from apps.health.models import Treatment, VaccinationType
from apps.infrastructure.models import Container
from ..validation import validate_treatment_dates


class TreatmentSerializer(HealthDecimalFieldsMixin, UserAssignmentMixin,
                          HealthBaseSerializer):
    """Serializer for the Treatment model.

    Uses HealthBaseSerializer for consistent error handling and field management.
    Includes HealthDecimalFieldsMixin for decimal field validation and UserAssignmentMixin
    for automatic user assignment.
    
    This serializer handles treatment records for fish health management, including
    medications, vaccinations, and other therapeutic interventions.
    """
    withholding_end_date = serializers.DateField(
        read_only=True,
        help_text="Calculated end date of the withholding period based on treatment date and withholding period days."
    )
    treatment_date = serializers.DateTimeField(
        read_only=True,
        help_text="Date and time when the treatment was administered (auto-set)."
    )
    
    # Additional fields with help_text
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        help_text="The batch that received the treatment."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        help_text="The container where the treatment was administered."
    )
    batch_assignment = serializers.PrimaryKeyRelatedField(
        queryset=BatchContainerAssignment.objects.all(),
        required=False,
        allow_null=True,
        help_text="Optional specific batch-container assignment for this treatment."
    )
    treatment_type = serializers.ChoiceField(
        choices=Treatment.TREATMENT_TYPES,
        help_text="Type of treatment administered (e.g., 'medication', 'vaccination')."
    )
    vaccination_type = serializers.PrimaryKeyRelatedField(
        queryset=VaccinationType.objects.all(),
        required=False,
        allow_null=True,
        help_text="Specific vaccination type if treatment_type is 'vaccination'."
    )
    description = serializers.CharField(
        help_text="Detailed description of the treatment administered."
    )
    dosage = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Dosage amount of the treatment (with units specified in description)."
    )
    duration_days = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Duration of the treatment in days.",
        validators=[MinValueValidator(0)]
    )
    withholding_period_days = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Number of days fish must be withheld from harvest after treatment.",
        validators=[MinValueValidator(0)]
    )
    outcome = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Outcome or result of the treatment."
    )
    
    # We need to explicitly define the field to override the default DateField
    # that would be created for treatment_date based on the model

    class Meta:
        model = Treatment
        fields = [
            'id', 'batch', 'container', 'batch_assignment', 'user',
            'treatment_date', 'treatment_type', 'vaccination_type',
            'description', 'dosage', 'duration_days',
            'withholding_period_days', 'withholding_end_date', 'outcome'
        ]
        read_only_fields = ['treatment_date', 'withholding_end_date', 'user']
        # User set in viewset, date is auto_now_add, end_date is property

    def validate(self, data):
        """Validate treatment data.

        Uses validation functions from validation.py for consistent validation
        across the application. Ensures that 'vaccination_type' is provided if
        'treatment_type' is 'vaccination', and not provided otherwise.
        Validates 'treatment_date' and 'withholding_period_days' using
        `validate_treatment_dates`. Ensures 'duration_days' is a positive integer.

        Args:
            data (dict): The data to validate.

        Returns:
            dict: The validated data.

        Raises:
            serializers.ValidationError: If any validation checks fail.
        """
        treatment_type = data.get('treatment_type')
        vaccination_type = data.get('vaccination_type')
        treatment_date = data.get('treatment_date')
        withholding_period_days = data.get('withholding_period_days')

        # Validate vaccination type
        if treatment_type == 'vaccination' and not vaccination_type:
            raise serializers.ValidationError({
                'vaccination_type': ('This field is required when '
                                     'treatment_type is vaccination.')
            })

        # Add check to ensure non-vaccination treatments don't have a vaccination_type
        if treatment_type != 'vaccination' and vaccination_type:
            raise serializers.ValidationError({
                'vaccination_type': ('This field should only be set when '
                                     'treatment_type is vaccination.')
            })

        # Use the validate_treatment_dates function from validation.py
        if treatment_date and withholding_period_days:
            try:
                # Validate withholding_period_days and calculate end date
                validate_treatment_dates(
                    treatment_date, withholding_period_days)
            except serializers.ValidationError as e:
                # Pass through any validation errors
                raise e

        # Validate dosage using the HealthDecimalFieldsMixin
        # This is handled automatically by the mixin

        # Validate duration_days is a positive integer if provided
        duration_days = data.get('duration_days')
        if duration_days is not None:
            try:
                duration_days_int = int(duration_days)
                if duration_days_int < 0:
                    raise serializers.ValidationError({
                        'duration_days': 'Duration days must be a positive integer.'
                    })
                # Store the converted integer value
                data['duration_days'] = duration_days_int
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'duration_days': ('Duration days must be a valid integer.')
                })

        return data
