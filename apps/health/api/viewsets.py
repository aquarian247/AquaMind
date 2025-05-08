from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.health.models import (
    JournalEntry, MortalityReason, MortalityRecord, LiceCount,
    VaccinationType, Treatment, SampleType,
    HealthParameter,
    HealthSamplingEvent,
    IndividualFishObservation,
    FishParameterScore,
    HealthLabSample
)
from apps.health.api.serializers import (
    JournalEntrySerializer, MortalityReasonSerializer,
    MortalityRecordSerializer, LiceCountSerializer,
    VaccinationTypeSerializer, TreatmentSerializer,
    SampleTypeSerializer,
    HealthParameterSerializer,
    HealthSamplingEventSerializer,
    IndividualFishObservationSerializer,
    FishParameterScoreSerializer,
    HealthLabSampleSerializer
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


# New ViewSets for Health Sampling

class HealthSamplingEventViewSet(viewsets.ModelViewSet):
    """API endpoint for managing Health Sampling Events."""
    queryset = HealthSamplingEvent.objects.select_related('assignment', 'sampled_by').prefetch_related('individual_fish_observations__parameter_scores__parameter').all()
    serializer_class = HealthSamplingEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Automatically set the sampled_by user to the logged-in user if not provided."""
        if not serializer.validated_data.get('sampled_by') and self.request.user.is_authenticated:
            serializer.save(sampled_by=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], url_path='calculate-aggregates')
    def calculate_aggregates(self, request, pk=None):
        """Triggers the calculation of aggregate metrics for the sampling event."""
        sampling_event = self.get_object()
        sampling_event.calculate_aggregate_metrics() # This method now saves the instance
        serializer = self.get_serializer(sampling_event)
        return Response(serializer.data)

class IndividualFishObservationViewSet(viewsets.ModelViewSet):
    """API endpoint for managing Individual Fish Observations."""
    queryset = IndividualFishObservation.objects.select_related('sampling_event').prefetch_related('parameter_scores__parameter').all()
    serializer_class = IndividualFishObservationSerializer
    permission_classes = [permissions.IsAuthenticated]

class FishParameterScoreViewSet(viewsets.ModelViewSet):
    """API endpoint for managing Fish Parameter Scores."""
    queryset = FishParameterScore.objects.select_related('individual_fish_observation__sampling_event', 'parameter').all()
    serializer_class = FishParameterScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

class HealthLabSampleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Health Lab Samples.
    Provides CRUD operations and filtering.
    """
    queryset = HealthLabSample.objects.select_related(
        'batch_container_assignment__batch',
        'batch_container_assignment__container',
        'sample_type',
        'recorded_by'
    ).all()
    serializer_class = HealthLabSampleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'batch_container_assignment__batch__id': ['exact'],
        'batch_container_assignment__container__id': ['exact'],
        'sample_type__id': ['exact'],
        'sample_date': ['exact', 'gte', 'lte'], # Allows for exact date, date_after (gte), date_before (lte)
        'lab_reference_id': ['exact', 'icontains'],
        'recorded_by__id': ['exact']
    }

    # The serializer already handles setting 'recorded_by' and resolving 'batch_container_assignment'
    # during creation, so perform_create might not be needed unless for other side effects.

    # Default ModelViewSet methods (list, create, retrieve, update, partial_update, destroy)
    # will be used.
