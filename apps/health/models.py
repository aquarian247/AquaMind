"""
Health app models.

This module imports and re-exports all models from the modular structure
to maintain backward compatibility.
"""

# Import all models from the modular structure
from .models.journal_entry import JournalEntry
from .models.health_observation import (
    HealthParameter, HealthSamplingEvent, IndividualFishObservation, FishParameterScore
)
from .models.lab_sample import HealthLabSample, SampleType
from .models.treatment import Treatment, VaccinationType
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
