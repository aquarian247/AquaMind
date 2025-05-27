"""
Script to fix the health app serializers.py file
"""

content = '''"""
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
'''

# Write the content to the serializers.py file
with open('apps/health/api/serializers.py', 'w') as f:
    f.write(content)

print("Fixed serializers.py file successfully!")
