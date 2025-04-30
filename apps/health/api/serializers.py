# Test comment to verify editing capability after IDE reinstall

from rest_framework import serializers
from django.db import transaction
from datetime import datetime
from ..models import (
    JournalEntry, HealthParameter, HealthObservation,
    MortalityReason, MortalityRecord, LiceCount, VaccinationType, Treatment, SampleType, HealthParameter
)
from apps.batch.models import GrowthSample, BatchContainerAssignment, Batch, Container
from apps.batch.api.serializers import GrowthSampleSerializer

# HealthParameterSerializer is defined at the bottom of this file with more specific fields

class MortalityReasonSerializer(serializers.ModelSerializer):
    """Serializer for the MortalityReason model."""
    class Meta:
        model = MortalityReason
        fields = ['id', 'name', 'description']

class MortalityRecordSerializer(serializers.ModelSerializer):
    """Serializer for the MortalityRecord model."""
    class Meta:
        model = MortalityRecord
        fields = [
            'id', 'batch', 'container', 'event_date',
            'count', 'reason', 'notes'
        ]
        read_only_fields = ['event_date'] # Event date is auto-set

class LiceCountSerializer(serializers.ModelSerializer):
    """Serializer for the LiceCount model."""
    average_per_fish = serializers.FloatField(read_only=True)

    class Meta:
        model = LiceCount
        fields = [
            'id', 'batch', 'container', 'user', 'count_date',
            'adult_female_count', 'adult_male_count', 'juvenile_count',
            'fish_sampled', 'notes', 'average_per_fish'
        ]
        read_only_fields = ['count_date', 'average_per_fish', 'user'] 
        # User is typically set in viewset, count_date is auto_now_add

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

class SampleTypeSerializer(serializers.ModelSerializer):
    """Serializer for the SampleType model."""
    class Meta:
        model = SampleType
        fields = ['id', 'name', 'description']

class HealthObservationSerializer(serializers.ModelSerializer):
    """
    Serializer for HealthObservation model.
    Includes validation to ensure parameter is correctly specified.
    """
    # Add field for parameter name for read operations
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    
    # parameter field needs to be both readable and writable to work with nested serializers
    parameter = serializers.PrimaryKeyRelatedField(queryset=HealthParameter.objects.all())
    
    # journal_entry is set by the parent JournalEntrySerializer
    journal_entry = serializers.PrimaryKeyRelatedField(queryset=JournalEntry.objects.all(), required=False)

    class Meta:
        model = HealthObservation
        fields = ['id', 'journal_entry', 'parameter', 'parameter_name', 'score', 'fish_identifier', 'created_at', 'updated_at']
        read_only_fields = ('id', 'created_at', 'updated_at', 'parameter_name')
        
    # Removed custom parameter validation that was causing issues
    # DRF's default validation for PrimaryKeyRelatedField is sufficient

class JournalEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for JournalEntry model.
    Handles nested creation/update of HealthObservations and optionally GrowthSample.
    """
    # Read-only field for displaying existing observations
    health_observations = HealthObservationSerializer(many=True, required=False, read_only=True) # Renamed from 'observations'
    # Write-only field for creating/updating observations
    health_observations_write = HealthObservationSerializer(many=True, required=False, write_only=True)

    batch = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all())
    container = serializers.PrimaryKeyRelatedField(queryset=Container.objects.all(), allow_null=True, required=False)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'batch', 'container', 'entry_date', 
            'description', 'category', 'severity', 'resolution_status', 'resolution_notes',
            'health_observations', # Use renamed field
            'health_observations_write', # Write field
            'created_at', 'updated_at', 'user', # Include user if it should be set/shown
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'user') # Add sampling_event_id

    def create(self, validated_data):
        observations_data = validated_data.pop('health_observations_write', [])
        # growth_sample_data = validated_data.pop('growth_sample', None) # Ensure it's popped if passed, though it shouldn't be in validated_data now

        # Get user from context
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Serializer context must include request with user.")
        user = request.user

        # Ensure user is set in validated_data if not already present
        if 'user' not in validated_data:
            validated_data['user'] = user

        with transaction.atomic():
            # Create the journal entry
            journal_entry = JournalEntry.objects.create(**validated_data)

            # Create health observations
            for observation_data in observations_data:
                HealthObservation.objects.create(journal_entry=journal_entry, **observation_data)

        return journal_entry

    def update(self, instance, validated_data):
        observations_data = validated_data.pop('health_observations_write', None)

        with transaction.atomic():
            # Update JournalEntry fields (excluding nested ones handled below)
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.save()

            # Handle nested HealthObservations update/replace
            if observations_data is not None:
                # Clear existing observations before adding new ones
                instance.health_observations.all().delete()
                
                # Create new observations
                for observation_data in observations_data:
                    # Create observation directly with the journal_entry relationship
                    HealthObservation.objects.create(
                        journal_entry=instance,
                        **observation_data
                    )
                    

        return instance

class HealthParameterSerializer(serializers.ModelSerializer):
    """Serializer for the HealthParameter model."""
    class Meta:
        model = HealthParameter
        fields = [
            'id', 'name', 'description_score_1', 'description_score_2',
            'description_score_3', 'description_score_4', 'description_score_5',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
