"""
Health app models package.

This package contains all models related to health monitoring in the AquaMind system.
"""

from .journal_entry import JournalEntry
from .health_observation import (
    HealthParameter, HealthSamplingEvent, IndividualFishObservation, FishParameterScore
)
from .lab_sample import HealthLabSample, SampleType
from .treatment import Treatment, VaccinationType
from .mortality import MortalityReason, MortalityRecord, LiceCount
