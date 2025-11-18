"""
Serializer for the MortalityEvent model.

This serializer handles the conversion between JSON and Django model instances
for mortality event data, including validation of mortality counts and biomass.
"""
from rest_framework import serializers
from apps.batch.models import MortalityEvent
from apps.batch.api.serializers.utils import NestedModelMixin, DecimalFieldsMixin
from typing import Dict, Any, Optional


class MortalityEventSerializer(NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer):
    """Serializer for the MortalityEvent model."""
    
    batch_number = serializers.StringRelatedField(source='batch', read_only=True)
    cause_display = serializers.CharField(source='get_cause_display', read_only=True)
    batch_info = serializers.SerializerMethodField()
    assignment_info = serializers.SerializerMethodField()
    container_info = serializers.SerializerMethodField()
    reason_info = serializers.SerializerMethodField()

    class Meta:
        model = MortalityEvent
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_batch_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get basic batch information."""
        return self.get_nested_info(obj, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number'
        })
    
    def get_assignment_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get basic assignment information."""
        if obj.assignment:
            return {
                'id': obj.assignment.id,
                'container_id': obj.assignment.container_id,
                'container_name': obj.assignment.container.name,
                'lifecycle_stage': obj.assignment.lifecycle_stage.name if obj.assignment.lifecycle_stage else None
            }
        return None

    def get_container_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get basic container information."""
        return self.get_nested_info(obj, 'container', {
            'id': 'id',
            'name': 'name'
        })

    def get_reason_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get mortality reason information."""
        return self.get_nested_info(obj, 'reason', {
            'id': 'id',
            'name': 'name'
        })

    def validate(self, data):
        """
        Validate that mortality count doesn't exceed batch/assignment population
        and that assignment belongs to batch if both are provided.
        """
        errors = {}
        
        # Validate assignment belongs to batch if both provided
        assignment = data.get('assignment')
        batch = data.get('batch')
        
        if assignment and batch:
            if assignment.batch_id != batch.id:
                errors['assignment'] = (
                    f"Assignment {assignment.id} does not belong to "
                    f"batch {batch.batch_number}."
                )
        
        # Check if mortality count doesn't exceed assignment or batch population
        if 'count' in data:
            if assignment:
                # Validate against assignment population
                if data['count'] > assignment.population_count:
                    errors['count'] = (
                        f"Mortality count ({data['count']}) exceeds assignment "
                        f"population ({assignment.population_count})."
                    )
            elif batch:
                # Validate against batch population (legacy support)
                if data['count'] > batch.calculated_population_count:
                    errors['count'] = (
                        f"Mortality count ({data['count']}) exceeds batch "
                        f"population ({batch.calculated_population_count})."
                    )
            
            # Check if mortality biomass doesn't exceed assignment or batch biomass
            if 'biomass_kg' in data:
                if assignment:
                    if data['biomass_kg'] > assignment.biomass_kg:
                        errors['biomass_kg'] = (
                            f"Mortality biomass ({data['biomass_kg']} kg) exceeds assignment "
                            f"biomass ({assignment.biomass_kg} kg)."
                        )
                elif batch:
                    if data['biomass_kg'] > batch.calculated_biomass_kg:
                        errors['biomass_kg'] = (
                            f"Mortality biomass ({data['biomass_kg']} kg) exceeds batch "
                            f"biomass ({batch.calculated_biomass_kg} kg)."
                        )
        
        if errors:
            raise serializers.ValidationError(errors)

        return data
