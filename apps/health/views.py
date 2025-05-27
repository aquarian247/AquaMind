from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime
from django.contrib.auth.decorators import login_required
from apps.batch.models import BatchContainerAssignment

# Import viewsets from the new modular structure
from .api.viewsets import (
    # Health observation viewsets
    HealthParameterViewSet,
    HealthSamplingEventViewSet,
    IndividualFishObservationViewSet,
    FishParameterScoreViewSet,
    
    # Journal entry viewsets
    JournalEntryViewSet,
    
    # Lab sample viewsets
    SampleTypeViewSet,
    HealthLabSampleViewSet,
    
    # Mortality viewsets
    MortalityReasonViewSet,
    MortalityRecordViewSet,
    LiceCountViewSet,
    
    # Treatment viewsets
    VaccinationTypeViewSet,
    TreatmentViewSet
)

# Note: HealthLabSampleViewSet is now imported from .api.viewsets


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

# Note: All viewsets are now imported from .api.viewsets
# The original viewset definitions have been moved to the appropriate files in the api/viewsets/ directory
