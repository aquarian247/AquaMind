from rest_framework.routers import DefaultRouter

# Import viewsets from the new modular structure
from .viewsets import (
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

router = DefaultRouter()
router.register(r'journal-entries', JournalEntryViewSet)
router.register(r'mortality-reasons', MortalityReasonViewSet)
router.register(r'mortality-records', MortalityRecordViewSet)
router.register(r'lice-counts', LiceCountViewSet)
router.register(r'vaccination-types', VaccinationTypeViewSet)
router.register(r'treatments', TreatmentViewSet)
router.register(r'sample-types', SampleTypeViewSet)
router.register(r'health-parameters', HealthParameterViewSet)

# Register new health sampling viewsets
router.register(r'health-sampling-events', HealthSamplingEventViewSet, basename='healthsamplingevent')
router.register(r'individual-fish-observations', IndividualFishObservationViewSet, basename='individualfishobservation')
router.register(r'fish-parameter-scores', FishParameterScoreViewSet, basename='fishparameterscore')
router.register(r'health-lab-samples', HealthLabSampleViewSet, basename='healthlabsample')
