"""
Health app viewsets package.

This package contains viewsets for the Health app, organized by domain.
"""

# Import all viewsets for easy access
from .health_observation import (
    HealthParameterViewSet,
    HealthSamplingEventViewSet,
    IndividualFishObservationViewSet,
    FishParameterScoreViewSet
)
from .journal_entry import JournalEntryViewSet
from .lab_sample import SampleTypeViewSet, HealthLabSampleViewSet
from .mortality import MortalityReasonViewSet, MortalityRecordViewSet, LiceCountViewSet
from .treatment import VaccinationTypeViewSet, TreatmentViewSet

# For backward compatibility
__all__ = [
    'HealthParameterViewSet',
    'HealthSamplingEventViewSet',
    'IndividualFishObservationViewSet',
    'FishParameterScoreViewSet',
    'JournalEntryViewSet',
    'SampleTypeViewSet',
    'HealthLabSampleViewSet',
    'MortalityReasonViewSet',
    'MortalityRecordViewSet',
    'LiceCountViewSet',
    'VaccinationTypeViewSet',
    'TreatmentViewSet'
]
