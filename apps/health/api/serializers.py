from rest_framework import serializers
from django.db import transaction

from ..models import JournalEntry, HealthParameter, HealthObservation
from apps.batch.models import GrowthSample, BatchContainerAssignment
from apps.batch.api.serializers import GrowthSampleSerializer

class HealthParameterSerializer(serializers.ModelSerializer):
    """Serializer for HealthParameter model."""
    class Meta:
        model = HealthParameter
        fields = '__all__'

class HealthObservationSerializer(serializers.ModelSerializer):
    """Serializer for HealthObservation model."""
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)

    class Meta:
        model = HealthObservation
        fields = [
            'id',
            'journal_entry', 
            'parameter', 
            'parameter_name', 
            'score', 
            'fish_identifier' 
        ]
        read_only_fields = ('id', 'parameter_name')
        extra_kwargs = {
            'journal_entry': {'read_only': True, 'required': False}
        }


class JournalEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for JournalEntry model.
    Handles nested creation/update of HealthObservations and optionally GrowthSample.
    """
    observations = HealthObservationSerializer(many=True, required=False)
    growth_sample = GrowthSampleSerializer(required=False, allow_null=True)
    assignment_details = serializers.StringRelatedField(source='assignment', read_only=True)
    created_by_details = serializers.StringRelatedField(source='created_by', read_only=True)

    assignment = serializers.PrimaryKeyRelatedField(
        queryset=BatchContainerAssignment.objects.all(),
        help_text="ID of the BatchContainerAssignment this journal entry belongs to."
    )

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'assignment', 'assignment_details', 'entry_type', 'entry_date',
            'description', 'created_by', 'created_by_details',
            'observations', 'growth_sample', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_by', 'created_by_details', 'created_at', 'updated_at')

    def create(self, validated_data):
        observations_data = validated_data.pop('observations', [])
        growth_sample_data = validated_data.pop('growth_sample', None)

        with transaction.atomic():
            validated_data['created_by'] = self.context['request'].user
            journal_entry = JournalEntry.objects.create(**validated_data)

            for observation_data in observations_data:
                HealthObservation.objects.create(journal_entry=journal_entry, **observation_data)

            if growth_sample_data:
                growth_sample_data['assignment'] = journal_entry.assignment
                if 'sample_date' not in growth_sample_data:
                    growth_sample_data['sample_date'] = journal_entry.entry_date

                growth_serializer = GrowthSampleSerializer(data=growth_sample_data, context=self.context)
                growth_serializer.is_valid(raise_exception=True)
                growth_serializer.save()

        return journal_entry

    def update(self, instance, validated_data):
        observations_data = validated_data.pop('observations', None)
        growth_sample_data = validated_data.pop('growth_sample', None)

        with transaction.atomic():
            instance = super().update(instance, validated_data)

            if observations_data is not None:
                instance.observations.all().delete()
                for observation_data in observations_data:
                    HealthObservation.objects.create(journal_entry=instance, **observation_data)

            existing_growth_sample = GrowthSample.objects.filter(assignment=instance.assignment, sample_date=instance.entry_date).first()

            if growth_sample_data is not None:
                growth_sample_data['assignment'] = instance.assignment
                growth_sample_data['sample_date'] = instance.entry_date

                if existing_growth_sample:
                    growth_serializer = GrowthSampleSerializer(existing_growth_sample, data=growth_sample_data, partial=True, context=self.context)
                else:
                    growth_serializer = GrowthSampleSerializer(data=growth_sample_data, context=self.context)

                growth_serializer.is_valid(raise_exception=True)
                growth_serializer.save()
            elif growth_sample_data is None and existing_growth_sample:
                 pass 

        return instance
