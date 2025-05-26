"""
Health app serializers package.

This package contains all serializers related to health monitoring in the AquaMind system.
"""

from .journal_entry import JournalEntrySerializer
from .health_observation import (
    HealthParameterSerializer, HealthSamplingEventSerializer,
    IndividualFishObservationSerializer, FishParameterScoreSerializer
)
from .lab_sample import HealthLabSampleSerializer, SampleTypeSerializer
from .treatment import TreatmentSerializer, VaccinationTypeSerializer
from .mortality import MortalityReasonSerializer, MortalityRecordSerializer, LiceCountSerializer
