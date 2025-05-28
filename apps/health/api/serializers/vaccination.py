"""
Vaccination serializers for health monitoring.

This module defines serializers for vaccination models.
"""


from ...models import VaccinationType
from .base import HealthBaseSerializer


class VaccinationTypeSerializer(HealthBaseSerializer):
    """Serializer for the VaccinationType model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    """
    class Meta:
        model = VaccinationType
        fields = ['id', 'name', 'manufacturer', 'dosage', 'description']
