from rest_framework import serializers
from django.db import transaction
from django.db import models
from decimal import Decimal

from apps.infrastructure.models import Container
from apps.infrastructure.serializers import ContainerSerializer
from .models import (
    Species, 
    LifeCycleStage, 
    Batch, 
    BatchContainerAssignment,
    BatchComposition,
    BatchTransfer, 
    MortalityEvent, 
    GrowthSample
)


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = '__all__'


class LifeCycleStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifeCycleStage
        fields = '__all__'


class BatchCompositionSerializer(serializers.ModelSerializer):
    source_batch_number = serializers.CharField(source='source_batch.batch_number', read_only=True)
    mixed_batch_number = serializers.CharField(source='mixed_batch.batch_number', read_only=True)
    
    class Meta:
        model = BatchComposition
        fields = [
            'id', 'mixed_batch', 'mixed_batch_number', 'source_batch', 
            'source_batch_number', 'percentage', 'population_count', 
            'biomass_kg', 'created_at'
        ]
        read_only_fields = ['created_at']


class BatchContainerAssignmentSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    container_name = serializers.CharField(source='container.name', read_only=True)
    container_detail = ContainerSerializer(source='container', read_only=True)
    
    class Meta:
        model = BatchContainerAssignment
        fields = [
            'id', 'batch', 'batch_number', 'container', 'container_name', 
            'container_detail', 'population_count', 'biomass_kg', 
            'assignment_date', 'is_active', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        # Check that the container has enough capacity for this assignment
        container = data.get('container')
        if not container:
            return data
            
        biomass_kg = data.get('biomass_kg', 0)
        
        # Get all active assignments for this container excluding the current one if updating
        current_assignment_id = self.instance.id if self.instance else None
        current_biomass = BatchContainerAssignment.objects.filter(
            container=container, 
            is_active=True
        ).exclude(id=current_assignment_id).aggregate(
            total_biomass=models.Sum('biomass_kg')
        )['total_biomass'] or 0
        
        # Check if adding this batch would exceed container capacity
        if current_biomass + Decimal(str(biomass_kg)) > container.max_biomass_kg:
            raise serializers.ValidationError({
                'biomass_kg': f'Adding this batch would exceed container capacity of {container.max_biomass_kg} kg. '
                            f'Current biomass: {current_biomass} kg.'
            })
        
        return data


class BatchSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(source='species.name', read_only=True)
    lifecycle_stage_name = serializers.CharField(source='lifecycle_stage.name', read_only=True)
    container_assignments = BatchContainerAssignmentSerializer(many=True, read_only=True)
    components = BatchCompositionSerializer(many=True, read_only=True)
    batch_type_display = serializers.CharField(source='get_batch_type_display', read_only=True)
    
    class Meta:
        model = Batch
        fields = [
            'id', 'batch_number', 'species', 'species_name', 'lifecycle_stage', 
            'lifecycle_stage_name', 'status', 'batch_type', 'batch_type_display',
            'population_count', 'biomass_kg', 'avg_weight_g',
            'start_date', 'expected_end_date', 'actual_end_date', 
            'notes', 'created_at', 'updated_at', 'container_assignments', 'components'
        ]
        read_only_fields = ['created_at', 'updated_at', 'biomass_kg']
        
    def create(self, validated_data):
        # Always set batch_type to STANDARD for new batches created directly
        validated_data['batch_type'] = 'STANDARD'
        
        # Calculate biomass from population count and average weight if not provided
        if 'biomass_kg' not in validated_data and 'population_count' in validated_data and 'avg_weight_g' in validated_data:
            validated_data['biomass_kg'] = (validated_data['population_count'] * validated_data['avg_weight_g']) / 1000
            
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Calculate biomass from population count and average weight if both are provided
        if 'population_count' in validated_data and 'avg_weight_g' in validated_data:
            validated_data['biomass_kg'] = (validated_data['population_count'] * validated_data['avg_weight_g']) / 1000
            
        return super().update(instance, validated_data)


class BatchTransferSerializer(serializers.ModelSerializer):
    source_batch_number = serializers.CharField(source='source_batch.batch_number', read_only=True)
    destination_batch_number = serializers.CharField(source='destination_batch.batch_number', read_only=True, allow_null=True)
    source_container_name = serializers.CharField(source='source_assignment.container.name', read_only=True)
    destination_container_name = serializers.CharField(source='destination_assignment.container.name', read_only=True, allow_null=True)
    transfer_type_display = serializers.CharField(source='get_transfer_type_display', read_only=True)
    
    class Meta:
        model = BatchTransfer
        fields = [
            'id', 'source_batch', 'source_batch_number', 
            'destination_batch', 'destination_batch_number',
            'transfer_type', 'transfer_type_display', 'transfer_date',
            'source_assignment', 'destination_assignment',
            'source_count', 'transferred_count', 'mortality_count',
            'source_biomass_kg', 'transferred_biomass_kg',
            'source_lifecycle_stage', 'destination_lifecycle_stage',
            'source_container_name', 'destination_container_name',
            'is_emergency_mixing', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class MortalityEventSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    cause_display = serializers.CharField(source='get_cause_display', read_only=True)
    
    class Meta:
        model = MortalityEvent
        fields = [
            'id', 'batch', 'batch_number', 'event_date', 'count', 
            'biomass_kg', 'cause', 'cause_display', 'description', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class GrowthSampleSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    
    class Meta:
        model = GrowthSample
        fields = [
            'id', 'batch', 'batch_number', 'sample_date', 'sample_size', 
            'avg_weight_g', 'avg_length_cm', 'std_dev_weight', 
            'std_dev_length', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
