"""
Vaccination serializers for health monitoring.

This module defines serializers for vaccination models.
"""


from ...models import VaccinationType
from rest_framework import serializers
from .base import HealthBaseSerializer


class VaccinationTypeSerializer(HealthBaseSerializer):
    """Serializer for the VaccinationType model.
    
    Uses HealthBaseSerializer for consistent error handling and field management.
    Handles information about different types of vaccines used in aquaculture.
    """
    name = serializers.CharField(
        help_text="Name of the vaccination type (e.g., 'PD Vaccine', 'IPN Vaccine')."
    )
    manufacturer = serializers.CharField(
        help_text="Manufacturer or supplier of the vaccine."
    )
    dosage = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Standard dosage information for this vaccine."
    )
    description = serializers.CharField(
        help_text="Detailed description of the vaccine, including diseases targeted and efficacy information."
    )
    
    class Meta:
        model = VaccinationType
        fields = ['id', 'name', 'manufacturer', 'dosage', 'description']
