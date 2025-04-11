from rest_framework import serializers

from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType
)


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = '__all__'


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
