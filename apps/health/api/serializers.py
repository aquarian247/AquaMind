"""
Health app API serializers - COMPATIBILITY LAYER.

IMPORTANT: This module is a compatibility layer that imports and re-exports 
all serializers from the modular structure. It exists only to maintain backward 
compatibility with existing code.

For new code, please import directly from the modular structure:
    from apps.health.api.serializers.health_observation import HealthParameterSerializer
    from apps.health.api.serializers.mortality import MortalityRecordSerializer
    etc.

This file may be removed in a future update once all imports have been migrated.
"""

# Import all serializers from the modular structure
from .serializers.journal_entry import JournalEntrySerializer
from .serializers.health_observation import (
    HealthParameterSerializer, HealthSamplingEventSerializer,
    IndividualFishObservationSerializer, FishParameterScoreSerializer
)
from .serializers.lab_sample import HealthLabSampleSerializer, SampleTypeSerializer
from .serializers.treatment import TreatmentSerializer
from .serializers.vaccination import VaccinationTypeSerializer
from .serializers.mortality import MortalityReasonSerializer, MortalityRecordSerializer, LiceCountSerializer, LiceTypeSerializer

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
    'LiceTypeSerializer',
]
