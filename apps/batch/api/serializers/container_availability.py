"""
Serializers for Container Availability API.

Provides response serialization for timeline-aware container selection.
"""
from rest_framework import serializers


class ContainerAssignmentSerializer(serializers.Serializer):
    """Current assignment in a container."""
    batch_id = serializers.IntegerField()
    batch_number = serializers.CharField()
    population_count = serializers.IntegerField()
    lifecycle_stage = serializers.CharField()
    assignment_date = serializers.DateField()
    expected_departure_date = serializers.DateField(allow_null=True)


class ContainerAvailabilitySerializer(serializers.Serializer):
    """
    Enriched container with availability forecast.
    
    Used by ContainerAvailabilityViewSet to return container data
    with timeline-aware availability status.
    """
    # Basic container info
    id = serializers.IntegerField()
    name = serializers.CharField()
    container_type = serializers.CharField()
    volume_m3 = serializers.FloatField()
    max_biomass_kg = serializers.FloatField()
    
    # Current occupancy
    current_status = serializers.ChoiceField(choices=['EMPTY', 'OCCUPIED'])
    current_assignments = ContainerAssignmentSerializer(many=True)
    
    # Availability forecast
    availability_status = serializers.ChoiceField(
        choices=['EMPTY', 'AVAILABLE', 'OCCUPIED_BUT_OK', 'CONFLICT']
    )
    days_until_available = serializers.IntegerField(allow_null=True)
    availability_message = serializers.CharField()
    
    # Capacity
    available_capacity_kg = serializers.FloatField()
    available_capacity_percent = serializers.FloatField()


class ContainerAvailabilityResponseSerializer(serializers.Serializer):
    """Response wrapper for container availability list."""
    count = serializers.IntegerField()
    results = ContainerAvailabilitySerializer(many=True)

