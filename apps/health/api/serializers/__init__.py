"""
Health app serializers package.

This package contains all serializers related to health monitoring in the AquaMind system.
"""

# Import base classes
from .base import (
    StandardErrorMixin,
    ReadWriteFieldsMixin,
    HealthBaseSerializer
)

# Import serializers from domain-specific modules
from .health_observation import (
    HealthParameterSerializer,
    HealthSamplingEventSerializer,
    IndividualFishObservationSerializer,
    FishParameterScoreSerializer
)
from .journal_entry import JournalEntrySerializer
from .lab_sample import SampleTypeSerializer, HealthLabSampleSerializer
from .mortality import MortalityReasonSerializer, MortalityRecordSerializer, LiceCountSerializer
from .vaccination import VaccinationTypeSerializer
from .treatment import TreatmentSerializer

# Import validation functions
from ..validation import (
    validate_health_parameter_score,
    validate_sample_size,
    validate_health_metrics,
    validate_treatment_dates,
    validate_lab_sample_dates
)

# For backward compatibility
# Note: The original serializers.py file has been split into multiple files
# and is no longer needed

# Export all classes and functions
__all__ = [
    # Base classes
    'StandardErrorMixin',
    'ReadWriteFieldsMixin',
    'HealthBaseSerializer',
    
    # Serializers
    'HealthParameterSerializer',
    'HealthSamplingEventSerializer',
    'IndividualFishObservationSerializer',
    'FishParameterScoreSerializer',
    'JournalEntrySerializer',
    'SampleTypeSerializer',
    'HealthLabSampleSerializer',
    'MortalityReasonSerializer',
    'MortalityRecordSerializer',
    'LiceCountSerializer',
    'VaccinationTypeSerializer',
    'TreatmentSerializer',
    
    # Validation functions
    'validate_health_parameter_score',
    'validate_sample_size',
    'validate_health_metrics',
    'validate_treatment_dates',
    'validate_lab_sample_dates'
]
