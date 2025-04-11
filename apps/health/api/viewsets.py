from rest_framework import viewsets, permissions

from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType
)
from apps.health.api.serializers import (
    JournalEntrySerializer, MortalityReasonSerializer,
    MortalityRecordSerializer, LiceCountSerializer,
    VaccinationTypeSerializer, TreatmentSerializer,
    SampleTypeSerializer
)


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class MortalityReasonViewSet(viewsets.ModelViewSet):
    queryset = MortalityReason.objects.all()
    serializer_class = MortalityReasonSerializer
    permission_classes = [permissions.IsAuthenticated]


class MortalityRecordViewSet(viewsets.ModelViewSet):
    queryset = MortalityRecord.objects.all()
    serializer_class = MortalityRecordSerializer
    permission_classes = [permissions.IsAuthenticated]


class LiceCountViewSet(viewsets.ModelViewSet):
    queryset = LiceCount.objects.all()
    serializer_class = LiceCountSerializer
    permission_classes = [permissions.IsAuthenticated]


class VaccinationTypeViewSet(viewsets.ModelViewSet):
    queryset = VaccinationType.objects.all()
    serializer_class = VaccinationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class TreatmentViewSet(viewsets.ModelViewSet):
    queryset = Treatment.objects.all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class SampleTypeViewSet(viewsets.ModelViewSet):
    queryset = SampleType.objects.all()
    serializer_class = SampleTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
