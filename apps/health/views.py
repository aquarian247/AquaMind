from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime
from django.contrib.auth.decorators import login_required
from apps.batch.models import BatchContainerAssignment # Assuming this is the correct path

from .models import (
    MortalityReason, MortalityRecord, LiceCount, VaccinationType, Treatment, 
    SampleType, JournalEntry, HealthParameter,
    HealthSamplingEvent, IndividualFishObservation, FishParameterScore,
    HealthLabSample
)
from .api.serializers import (
    MortalityReasonSerializer, MortalityRecordSerializer, LiceCountSerializer, 
    VaccinationTypeSerializer, TreatmentSerializer, SampleTypeSerializer, 
    JournalEntrySerializer, HealthParameterSerializer,
    HealthSamplingEventSerializer, IndividualFishObservationSerializer, FishParameterScoreSerializer,
    HealthLabSampleSerializer
)

class HealthLabSampleViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Health Lab Samples to be viewed or edited.
    Handles creation with historical BatchContainerAssignment linkage.
    """
    queryset = HealthLabSample.objects.all().order_by('-sample_date', '-created_at')
    serializer_class = HealthLabSampleSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser] # To support file uploads for attachments and JSON data

    def get_queryset(self):
        """Optionally restricts the returned samples to a given batch or container."""
        queryset = super().get_queryset()
        batch_id = self.request.query_params.get('batch_id')
        container_id = self.request.query_params.get('container_id')
        sample_type_id = self.request.query_params.get('sample_type_id')

        if batch_id:
            queryset = queryset.filter(batch_container_assignment__batch_id=batch_id)
        if container_id:
            queryset = queryset.filter(batch_container_assignment__container_id=container_id)
        if sample_type_id:
            queryset = queryset.filter(sample_type_id=sample_type_id)
            
        return queryset

    # perform_create and perform_update are handled by the serializer's create/update methods
    # which set 'recorded_by' and resolve 'batch_container_assignment'.


@login_required
def load_batch_assignments(request):
    """View to load batch container assignments for AJAX requests based on sample_date."""
    sample_date_str = request.GET.get('sample_date')
    assignments_data = []

    if sample_date_str:
        try:
            sample_date_obj = datetime.strptime(sample_date_str, '%Y-%m-%d').date()
            
            # Filter assignments: active on the given sample_date
            # assignment_date <= sample_date AND (departure_date >= sample_date OR departure_date IS NULL)
            # AND is_active = True
            valid_assignments = BatchContainerAssignment.objects.filter(
                Q(assignment_date__lte=sample_date_obj) &
                (Q(departure_date__gte=sample_date_obj) | Q(departure_date__isnull=True)) &
                Q(is_active=True)
            ).select_related('batch', 'container').order_by('batch__batch_number', 'container__name')

            for assignment in valid_assignments:
                assignments_data.append({'id': assignment.pk, 'text': str(assignment)})
        except ValueError:
            # Handle invalid date format if necessary, though client-side date picker should prevent this
            pass # Or return an error response

    return JsonResponse({'assignments': assignments_data})


# TODO: Add other viewsets for health models as needed.

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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class VaccinationTypeViewSet(viewsets.ModelViewSet):
    queryset = VaccinationType.objects.all()
    serializer_class = VaccinationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class TreatmentViewSet(viewsets.ModelViewSet):
    queryset = Treatment.objects.all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SampleTypeViewSet(viewsets.ModelViewSet):
    queryset = SampleType.objects.all()
    serializer_class = SampleTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

class HealthParameterViewSet(viewsets.ModelViewSet):
    queryset = HealthParameter.objects.all()
    serializer_class = HealthParameterSerializer
    permission_classes = [permissions.IsAuthenticated]

class HealthSamplingEventViewSet(viewsets.ModelViewSet):
    queryset = HealthSamplingEvent.objects.select_related(
        'assignment__batch', 
        'assignment__container', 
        'assignment__lifecycle_stage', 
        'sampled_by'
    ).prefetch_related(
        'individual_fish_observations__parameter_scores__parameter'
    ).all()
    serializer_class = HealthSamplingEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    # perform_create is handled by serializer to correctly create nested objects
    # and set sampled_by if not provided.

class IndividualFishObservationViewSet(viewsets.ModelViewSet):
    queryset = IndividualFishObservation.objects.all()
    serializer_class = IndividualFishObservationSerializer
    permission_classes = [permissions.IsAuthenticated]

class FishParameterScoreViewSet(viewsets.ModelViewSet):
    queryset = FishParameterScore.objects.all()
    serializer_class = FishParameterScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
