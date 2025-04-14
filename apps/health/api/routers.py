from rest_framework.routers import DefaultRouter

from apps.health.api.viewsets import (
    JournalEntryViewSet, MortalityReasonViewSet, MortalityRecordViewSet,
    LiceCountViewSet, VaccinationTypeViewSet, TreatmentViewSet,
    SampleTypeViewSet, HealthParameterViewSet
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
