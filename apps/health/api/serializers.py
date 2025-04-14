from rest_framework import serializers

from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType, HealthParameter, HealthObservation
)


class HealthParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthParameter
        fields = ('id', 'name', 'description_score_1', 'description_score_2',
                  'description_score_3', 'description_score_4', 'is_active')
        read_only_fields = ('id',)


class HealthObservationWriteSerializer(serializers.Serializer):
    parameter_id = serializers.PrimaryKeyRelatedField(
        queryset=HealthParameter.objects.all(), source='parameter'
    )
    score = serializers.IntegerField(min_value=1, max_value=4)

    class Meta:
        fields = ('parameter_id', 'score')


class HealthObservationReadSerializer(serializers.ModelSerializer):
    parameter = HealthParameterSerializer(read_only=True)

    class Meta:
        model = HealthObservation
        fields = ('id', 'parameter', 'score', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class JournalEntrySerializer(serializers.ModelSerializer):
    health_observations = HealthObservationReadSerializer(many=True, read_only=True)
    health_observations_write = HealthObservationWriteSerializer(
        many=True, write_only=True, required=False, source='health_observations'
    )

    class Meta:
        model = JournalEntry
        fields = (
            'id', 'batch', 'container', 'user', 'entry_date', 'category',
            'severity', 'description', 'resolution_status', 'resolution_notes',
            'health_observations', 'health_observations_write', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def create(self, validated_data):
        """Handle creation including nested HealthObservations."""
        # Pop observations data before creating the JournalEntry instance
        observations_data = validated_data.pop('health_observations', [])
        # The 'user' is automatically added to validated_data by perform_create
        journal_entry = JournalEntry.objects.create(**validated_data)
        # Create HealthObservation instances
        for obs_data in observations_data:
            HealthObservation.objects.create(journal_entry=journal_entry, **obs_data)
        return journal_entry

    def update(self, instance, validated_data):
        """Handle update including nested HealthObservations."""
        # Pop observations data before calling super().update
        # Use None as default to distinguish between empty list [] and not provided
        observations_data = validated_data.pop('health_observations', None)

        # Update the JournalEntry instance itself (excluding observations for now)
        instance = super().update(instance, validated_data)

        # Handle nested observations if data was provided
        if observations_data is not None:
            # Delete existing observations for this entry
            instance.health_observations.all().delete()
            # Create new observations from the provided data
            for obs_data in observations_data:
                HealthObservation.objects.create(journal_entry=instance, **obs_data)

        return instance


class MortalityReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = MortalityReason
        fields = '__all__'


class MortalityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MortalityRecord
        fields = '__all__'


class LiceCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiceCount
        fields = '__all__'
        read_only_fields = ('average_per_fish',)


class VaccinationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccinationType
        fields = '__all__'


class TreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Treatment
        fields = '__all__'
        read_only_fields = ('withholding_end_date',)


class SampleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleType
        fields = '__all__'
