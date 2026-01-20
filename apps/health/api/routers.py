from rest_framework.routers import DefaultRouter

# Import viewsets from the new modular structure
from .viewsets import (
    # Health observation viewsets
    HealthParameterViewSet,
    ParameterScoreDefinitionViewSet,
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
    LiceTypeViewSet,
    
    # Treatment viewsets
    VaccinationTypeViewSet,
    TreatmentViewSet
)
from .viewsets.history import (
    JournalEntryHistoryViewSet,
    LiceCountHistoryViewSet,
    LiceTypeHistoryViewSet,
    MortalityRecordHistoryViewSet,
    TreatmentHistoryViewSet,
    HealthLabSampleHistoryViewSet
)

router = DefaultRouter()
router.register(r'journal-entries', JournalEntryViewSet, basename='journal-entry')
router.register(r'mortality-reasons', MortalityReasonViewSet, basename='mortality-reasons')
router.register(r'mortality-records', MortalityRecordViewSet, basename='mortality-record')
router.register(r'lice-counts', LiceCountViewSet, basename='lice-count')
router.register(r'lice-types', LiceTypeViewSet, basename='lice-type')
router.register(r'vaccination-types', VaccinationTypeViewSet, basename='vaccination-type')
router.register(r'treatments', TreatmentViewSet, basename='treatment')
router.register(r'sample-types', SampleTypeViewSet, basename='sample-type')
router.register(r'health-parameters', HealthParameterViewSet, basename='health-parameter')
router.register(r'parameter-score-definitions', ParameterScoreDefinitionViewSet, basename='parameter-score-definition')

# Register new health sampling viewsets
router.register(r'health-sampling-events', HealthSamplingEventViewSet, basename='health-sampling-event')
router.register(r'individual-fish-observations', IndividualFishObservationViewSet, basename='individual-fish-observation')
router.register(r'fish-parameter-scores', FishParameterScoreViewSet, basename='fish-parameter-score')
router.register(r'health-lab-samples', HealthLabSampleViewSet, basename='health-lab-sample')

# Register history endpoints
router.register(r'history/journal-entries', JournalEntryHistoryViewSet, basename='journal-entry-history')
router.register(r'history/mortality-records', MortalityRecordHistoryViewSet, basename='mortality-record-history')
router.register(r'history/lice-counts', LiceCountHistoryViewSet, basename='lice-count-history')
router.register(r'history/lice-types', LiceTypeHistoryViewSet, basename='lice-type-history')
router.register(r'history/treatments', TreatmentHistoryViewSet, basename='treatment-history')
router.register(r'history/health-lab-samples', HealthLabSampleHistoryViewSet, basename='health-lab-sample-history')
