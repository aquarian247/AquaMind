"""
Health app viewsets package.

This package contains viewsets for the Health app, organized by domain.
"""

# Import all viewsets for easy access
from .health_observation import (
    HealthParameterViewSet,
    ParameterScoreDefinitionViewSet,
    HealthSamplingEventViewSet,
    IndividualFishObservationViewSet,
    FishParameterScoreViewSet
)
from .journal_entry import JournalEntryViewSet
from .lab_sample import SampleTypeViewSet, HealthLabSampleViewSet
from .mortality import MortalityReasonViewSet, MortalityRecordViewSet, LiceCountViewSet, LiceTypeViewSet
from .treatment import VaccinationTypeViewSet, TreatmentViewSet

# For backward compatibility
__all__ = [
    'HealthParameterViewSet',
    'ParameterScoreDefinitionViewSet',
    'HealthSamplingEventViewSet',
    'IndividualFishObservationViewSet',
    'FishParameterScoreViewSet',
    'JournalEntryViewSet',
    'SampleTypeViewSet',
    'HealthLabSampleViewSet',
    'MortalityReasonViewSet',
    'MortalityRecordViewSet',
    'LiceCountViewSet',
    'LiceTypeViewSet',
    'VaccinationTypeViewSet',
    'TreatmentViewSet'
]
