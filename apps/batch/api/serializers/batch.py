"""
Serializer for the Batch model.

This serializer handles the conversion between JSON and Django model instances
for batch data, including calculated fields for population, biomass, and average weight.
"""
import datetime
from rest_framework import serializers
from apps.batch.models import Batch
from apps.batch.api.serializers.utils import format_decimal, validate_date_order
from apps.batch.api.serializers.base import BatchBaseSerializer


class BatchSerializer(BatchBaseSerializer):
    """Serializer for the Batch model."""
    
    species_name = serializers.CharField(source='species.name', read_only=True)
    calculated_population_count = serializers.IntegerField(read_only=True)
    calculated_biomass_kg = serializers.SerializerMethodField()
    calculated_avg_weight_g = serializers.SerializerMethodField()
    current_lifecycle_stage = serializers.SerializerMethodField()
    days_in_production = serializers.SerializerMethodField()
    active_containers = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = (
            'id', 'batch_number', 'species', 'species_name', 'lifecycle_stage', 
            'status', 'batch_type', 'start_date', 'expected_end_date', 'notes', 
            'created_at', 'updated_at', 'calculated_population_count', 
            'calculated_biomass_kg', 'calculated_avg_weight_g',
            'current_lifecycle_stage', 'days_in_production', 'active_containers'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'calculated_population_count',
            'calculated_biomass_kg', 'calculated_avg_weight_g',
            'current_lifecycle_stage', 'days_in_production', 'active_containers'
        )

    def get_current_lifecycle_stage(self, obj):
        """Get the current lifecycle stage of the batch based on active assignments."""
        latest_assignment = obj.batch_assignments.filter(is_active=True).order_by('-assignment_date').first()
        if latest_assignment and latest_assignment.lifecycle_stage:
            return {
                'id': latest_assignment.lifecycle_stage.id,
                'name': latest_assignment.lifecycle_stage.name,
                'order': latest_assignment.lifecycle_stage.order
            }
        return None

    def get_days_in_production(self, obj):
        """Calculate the number of days since the batch started."""
        if obj.start_date:
            from datetime import date
            return (date.today() - obj.start_date).days
        return 0

    def get_active_containers(self, obj):
        """Get a list of active container IDs for this batch."""
        active_assignments = obj.batch_assignments.filter(is_active=True)
        return [assignment.container.id for assignment in active_assignments if assignment.container]

    def get_calculated_biomass_kg(self, obj):
        return format_decimal(obj.calculated_biomass_kg)

    def get_calculated_avg_weight_g(self, obj):
        return format_decimal(obj.calculated_avg_weight_g)

    def create(self, validated_data):
        """
        Create a new batch instance.
        """
        if 'expected_end_date' not in validated_data or validated_data['expected_end_date'] is None:
            validated_data['expected_end_date'] = validated_data['start_date'] + datetime.timedelta(days=30)
        return Batch.objects.create(**validated_data)

    def validate(self, data):
        """Validate the batch data."""
        errors = {}
        
        # Validate that expected_end_date is after start_date
        if 'expected_end_date' in data and 'start_date' in data:
            date_error = validate_date_order(
                data['start_date'], 
                data['expected_end_date'], 
                'expected_end_date', 
                'Expected end date must be after start date.'
            )
            if date_error:
                errors.update(date_error)
        
        # Validate that lifecycle_stage belongs to the correct species
        if 'lifecycle_stage' in data and 'species' in data:
            lifecycle_stage = data['lifecycle_stage']
            species = data['species']
            
            if lifecycle_stage.species.id != species.id:
                self.add_error(
                    errors,
                    'lifecycle_stage',
                    'Lifecycle stage {stage_name} does not belong to species {species_name}.',
                    stage_name=lifecycle_stage.name,
                    species_name=species.name
                )
        
        if errors:
            raise serializers.ValidationError(errors)
            
        return super().validate(data)
    
    def update(self, instance, validated_data):
        """Update an existing batch."""
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
