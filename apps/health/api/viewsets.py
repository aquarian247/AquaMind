from rest_framework import viewsets, permissions

from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType,
    HealthParameter
)
from apps.health.api.serializers import (
    JournalEntrySerializer, MortalityReasonSerializer,
    MortalityRecordSerializer, LiceCountSerializer,
    VaccinationTypeSerializer, TreatmentSerializer,
    SampleTypeSerializer,
    HealthParameterSerializer
)


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Automatically set the user to the logged-in user."""
        serializer.save(user=self.request.user)


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


class HealthParameterViewSet(viewsets.ModelViewSet):
    """API endpoint for managing Health Parameters."""
    # Allow seeing inactive ones, frontend can filter if needed
    queryset = HealthParameter.objects.all()
    serializer_class = HealthParameterSerializer
    permission_classes = [permissions.IsAuthenticated] # Adjust permissions as needed
