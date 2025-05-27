"""
Health app models - COMPATIBILITY LAYER.

IMPORTANT: This module is a compatibility layer that imports and re-exports 
all models from the modular structure. It exists only to maintain backward 
compatibility with existing code.

For new code, please import directly from the modular structure:
    from apps.health.models.health_observation import HealthParameter
    from apps.health.models.mortality import MortalityRecord
    etc.

This file may be removed in a future update once all imports have been migrated.
"""

# Import all models from the modular structure
from .models.journal_entry import JournalEntry
from .models.health_observation import (
    HealthParameter, HealthSamplingEvent, IndividualFishObservation, FishParameterScore
)
from .models.lab_sample import HealthLabSample, SampleType
from .models.treatment import Treatment
from .models.vaccination import VaccinationType
from .models.mortality import MortalityReason, MortalityRecord, LiceCount

# Re-export all models to maintain backward compatibility
__all__ = [
    'JournalEntry',
    'HealthParameter',
    'HealthSamplingEvent',
    'IndividualFishObservation',
    'FishParameterScore',
    'HealthLabSample',
    'SampleType',
    'Treatment',
    'VaccinationType',
    'MortalityReason',
    'MortalityRecord',
    'LiceCount',
]
