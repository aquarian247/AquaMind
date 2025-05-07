# Test comment to verify editing capability after IDE reinstall

from rest_framework import serializers
from django.db import transaction
from datetime import datetime
from ..models import (
    JournalEntry, HealthParameter, 
    MortalityReason, MortalityRecord, LiceCount, VaccinationType, Treatment, SampleType,
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore
)
from apps.batch.models import BatchContainerAssignment, Batch, Container 

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

class JournalEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for JournalEntry model.
    """
    batch = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all())
    container = serializers.PrimaryKeyRelatedField(queryset=Container.objects.all(), allow_null=True, required=False)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'batch', 'container', 'entry_date', 
            'description', 'category', 'severity', 'resolution_status', 'resolution_notes',
            'created_at', 'updated_at', 'user', 
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'user')

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Serializer context must include request with user.")
        user = request.user

        if 'user' not in validated_data:
            validated_data['user'] = user

        with transaction.atomic():
            journal_entry = JournalEntry.objects.create(**validated_data)
        return journal_entry

    def update(self, instance, validated_data):
        with transaction.atomic():
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.save()

        return instance


# New Serializers for Health Sampling

class FishParameterScoreSerializer(serializers.ModelSerializer):
    """Serializer for FishParameterScore model."""
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    # parameter is still needed to choose which parameter is being scored.
    parameter = serializers.PrimaryKeyRelatedField(queryset=HealthParameter.objects.filter(is_active=True))

    class Meta:
        model = FishParameterScore
        # 'individual_fish_observation' is removed. It will be handled by the parent serializer.
        fields = ['id', 'parameter', 'parameter_name', 'score'] 
        read_only_fields = ['id', 'parameter_name']

class IndividualFishObservationSerializer(serializers.ModelSerializer):
    """Serializer for IndividualFishObservation model, with nested Parameter Scores."""
    parameter_scores = FishParameterScoreSerializer(many=True, required=False)

    class Meta:
        model = IndividualFishObservation
        fields = [
            'id', 'fish_identifier', 'length_cm', 'weight_g',
            'parameter_scores'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        scores_data = validated_data.pop('parameter_scores', [])
        sampling_event = self.context.get('sampling_event')
        if not sampling_event:
            # This case should ideally be prevented by how the view calls the serializer
            # or by a validator if sampling_event were part of the serializer fields.
            # For now, raising an error makes the requirement explicit.
            raise serializers.ValidationError({"sampling_event": "Sampling event must be provided in the context."}) 

        observation = IndividualFishObservation.objects.create(
            sampling_event=sampling_event, 
            **validated_data
        )
        for score_data in scores_data:
            FishParameterScore.objects.create(individual_fish_observation=observation, **score_data)
        return observation

    def update(self, instance, validated_data):
        scores_data = validated_data.pop('parameter_scores', None)

        instance.fish_identifier = validated_data.get('fish_identifier', instance.fish_identifier)
        instance.length_cm = validated_data.get('length_cm', instance.length_cm)
        instance.weight_g = validated_data.get('weight_g', instance.weight_g)
        instance.save()

        if scores_data is not None:
            instance.parameter_scores.all().delete()
            for score_data in scores_data:
                FishParameterScore.objects.create(individual_fish_observation=instance, **score_data)
        return instance

class HealthSamplingEventSerializer(serializers.ModelSerializer):
    """Serializer for HealthSamplingEvent, with nested Individual Fish Observations."""
    individual_fish_observations = IndividualFishObservationSerializer(many=True, required=False)
    assignment_details = serializers.StringRelatedField(source='assignment', read_only=True)
    sampled_by_username = serializers.CharField(source='sampled_by.username', read_only=True, allow_null=True)

    class Meta:
        model = HealthSamplingEvent
        fields = [
            'id', 'assignment', 'assignment_details', 'sampling_date', 'number_of_fish_sampled',
            'sampled_by', 'sampled_by_username', 'notes',
            'individual_fish_observations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'assignment_details', 'sampled_by_username']

    def create(self, validated_data):
        observations_data = validated_data.pop('individual_fish_observations', [])
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None
        
        # If sampled_by is not provided, default to the request user
        if 'sampled_by' not in validated_data or validated_data['sampled_by'] is None:
            validated_data['sampled_by'] = user
            
        sampling_event = HealthSamplingEvent.objects.create(**validated_data)
        for obs_data in observations_data:
            scores_data = obs_data.pop('parameter_scores', [])
            observation = IndividualFishObservation.objects.create(sampling_event=sampling_event, **obs_data)
            for score_data in scores_data:
                FishParameterScore.objects.create(individual_fish_observation=observation, **score_data)
        return sampling_event

    def update(self, instance, validated_data):
        observations_data = validated_data.pop('individual_fish_observations', None)

        # Update HealthSamplingEvent fields
        instance.assignment = validated_data.get('assignment', instance.assignment)
        instance.sampling_date = validated_data.get('sampling_date', instance.sampling_date)
        instance.number_of_fish_sampled = validated_data.get('number_of_fish_sampled', instance.number_of_fish_sampled)
        instance.sampled_by = validated_data.get('sampled_by', instance.sampled_by)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()

        if observations_data is not None:
            # Simple approach: delete existing and create new. More complex diffing could be implemented if needed.
            instance.individual_fish_observations.all().delete()
            for obs_data in observations_data:
                scores_data = obs_data.pop('parameter_scores', [])
                observation = IndividualFishObservation.objects.create(sampling_event=instance, **obs_data)
                for score_data in scores_data:
                    FishParameterScore.objects.create(individual_fish_observation=observation, **score_data)
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
