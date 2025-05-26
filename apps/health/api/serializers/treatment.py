"""
Treatment serializers for health monitoring.

This module defines serializers for treatment models, including
VaccinationType and Treatment.
"""

from rest_framework import serializers

from ...models import VaccinationType, Treatment


class VaccinationTypeSerializer(serializers.ModelSerializer):
    """Serializer for the VaccinationType model."""
    class Meta:
        model = VaccinationType
        fields = ['id', 'name', 'manufacturer', 'dosage', 'description']


class TreatmentSerializer(serializers.ModelSerializer):
    """Serializer for the Treatment model."""
    withholding_end_date = serializers.DateField(read_only=True)
    treatment_date = serializers.DateTimeField(read_only=True)
    
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
        """Check that vaccination_type is provided if treatment_type is 'vaccination'."""
        treatment_type = data.get('treatment_type')
        vaccination_type = data.get('vaccination_type')

        if treatment_type == 'vaccination' and not vaccination_type:
            raise serializers.ValidationError({
                'vaccination_type': 'This field is required when treatment_type is vaccination.'
            })
            
        # Add check to ensure non-vaccination treatments don't have a vaccination_type
        if treatment_type != 'vaccination' and vaccination_type:
             raise serializers.ValidationError({
                'vaccination_type': 'This field should only be set when treatment_type is vaccination.'
            })

        return data
