"""
Health app API serializers.

This module imports and re-exports all serializers from the modular structure
to maintain backward compatibility.
"""

# Import all serializers from the modular structure
from .serializers.journal_entry import JournalEntrySerializer
from .serializers.health_observation import (
    HealthParameterSerializer, HealthSamplingEventSerializer,
    IndividualFishObservationSerializer, FishParameterScoreSerializer
)
from .serializers.lab_sample import HealthLabSampleSerializer, SampleTypeSerializer
from .serializers.treatment import TreatmentSerializer, VaccinationTypeSerializer
from .serializers.mortality import MortalityReasonSerializer, MortalityRecordSerializer, LiceCountSerializer

# Re-export all serializers to maintain backward compatibility
__all__ = [
    'JournalEntrySerializer',
    'HealthParameterSerializer',
    'HealthSamplingEventSerializer',
    'IndividualFishObservationSerializer',
    'FishParameterScoreSerializer',
    'HealthLabSampleSerializer',
    'SampleTypeSerializer',
    'TreatmentSerializer',
    'VaccinationTypeSerializer',
    'MortalityReasonSerializer',
    'MortalityRecordSerializer',
    'LiceCountSerializer',
]
