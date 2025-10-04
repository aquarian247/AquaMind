"""
Serializers for the Broodstock Management app.

This module contains serializers for all broodstock models with comprehensive
validation and nested representations where appropriate.
"""

from rest_framework import serializers
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.broodstock.models import (
    MaintenanceTask, BroodstockFish, FishMovement, BreedingPlan,
    BreedingTraitPriority, BreedingPair, EggProduction, EggSupplier,
    ExternalEggBatch, BatchParentage
)
from apps.infrastructure.api.serializers import ContainerSerializer
from apps.batch.api.serializers import BatchSerializer


class MaintenanceTaskSerializer(serializers.ModelSerializer):
    """Serializer for maintenance tasks."""
    
    container_name = serializers.CharField(source='container.name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = MaintenanceTask
        fields = [
            'id', 'container', 'container_name', 'task_type', 
            'scheduled_date', 'completed_date', 'notes', 
            'created_by', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure completed date is after scheduled date."""
        if data.get('completed_date') and data.get('scheduled_date'):
            if data['completed_date'] < data['scheduled_date']:
                raise serializers.ValidationError(
                    "Completed date cannot be before scheduled date."
                )
        return data


class BroodstockFishSerializer(serializers.ModelSerializer):
    """Serializer for broodstock fish."""
    
    container_name = serializers.CharField(source='container.name', read_only=True)
    movement_count = serializers.IntegerField(
        source='movements.count', read_only=True
    )
    
    class Meta:
        model = BroodstockFish
        fields = [
            'id', 'container', 'container_name', 'traits', 
            'health_status', 'movement_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_container(self, value):
        """
        Ensure container is suitable for broodstock.
        
        Broodstock fish should be kept in tank-type containers.
        Uses category check instead of fragile name substring matching.
        """
        if value.container_type.category != 'TANK':
            raise serializers.ValidationError(
                f"Broodstock fish can only be assigned to tank containers. "
                f"This container is a {value.container_type.get_category_display()}."
            )
        return value
    
    def validate_traits(self, value):
        """Validate traits JSON structure."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError(
                "Traits must be a JSON object."
            )
        return value


class FishMovementSerializer(serializers.ModelSerializer):
    """Serializer for fish movements."""
    
    fish_display = serializers.CharField(source='fish.__str__', read_only=True)
    from_container_name = serializers.CharField(
        source='from_container.name', read_only=True
    )
    to_container_name = serializers.CharField(
        source='to_container.name', read_only=True
    )
    
    class Meta:
        model = FishMovement
        fields = [
            'id', 'fish', 'fish_display', 'from_container', 
            'from_container_name', 'to_container', 'to_container_name',
            'movement_date', 'moved_by', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['moved_by', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate movement logic."""
        if data['from_container'] == data['to_container']:
            raise serializers.ValidationError(
                "Source and destination containers must be different."
            )
        
        # Ensure both containers are broodstock type
        for container in [data['from_container'], data['to_container']]:
            if 'broodstock' not in container.container_type.name.lower():
                raise serializers.ValidationError(
                    f"Container {container.name} is not a broodstock container."
                )
        
        # Verify fish is currently in the from_container
        if data['fish'].container != data['from_container']:
            raise serializers.ValidationError(
                "Fish is not currently in the specified source container."
            )
        
        return data


class BreedingTraitPrioritySerializer(serializers.ModelSerializer):
    """Serializer for breeding trait priorities."""
    
    trait_display = serializers.CharField(
        source='get_trait_name_display', read_only=True
    )
    
    class Meta:
        model = BreedingTraitPriority
        fields = [
            'id', 'plan', 'trait_name', 'trait_display', 
            'priority_weight', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BreedingPlanSerializer(serializers.ModelSerializer):
    """Serializer for breeding plans."""
    
    trait_priorities = BreedingTraitPrioritySerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    breeding_pair_count = serializers.IntegerField(
        source='breeding_pairs.count', read_only=True
    )
    
    class Meta:
        model = BreedingPlan
        fields = [
            'id', 'name', 'start_date', 'end_date', 'objectives',
            'geneticist_notes', 'breeder_instructions', 'is_active',
            'trait_priorities', 'breeding_pair_count', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure end date is after start date."""
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date."
                )
        return data


class BreedingPairSerializer(serializers.ModelSerializer):
    """Serializer for breeding pairs."""
    
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    male_fish_display = serializers.CharField(
        source='male_fish.__str__', read_only=True
    )
    female_fish_display = serializers.CharField(
        source='female_fish.__str__', read_only=True
    )
    egg_production_count = serializers.IntegerField(
        source='egg_productions.count', read_only=True
    )
    
    class Meta:
        model = BreedingPair
        fields = [
            'id', 'plan', 'plan_name', 'male_fish', 'male_fish_display',
            'female_fish', 'female_fish_display', 'pairing_date',
            'progeny_count', 'egg_production_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validate breeding pair logic."""
        if data['male_fish'] == data['female_fish']:
            raise serializers.ValidationError(
                "Male and female fish must be different."
            )
        
        # Ensure both fish are healthy
        for fish in [data['male_fish'], data['female_fish']]:
            if fish.health_status != 'healthy':
                raise serializers.ValidationError(
                    f"Fish #{fish.id} is not healthy and cannot be used for breeding."
                )
        
        return data


class EggSupplierSerializer(serializers.ModelSerializer):
    """Serializer for egg suppliers."""
    
    batch_count = serializers.IntegerField(
        source='egg_batches.count', read_only=True
    )
    
    class Meta:
        model = EggSupplier
        fields = [
            'id', 'name', 'contact_details', 'certifications',
            'batch_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ExternalEggBatchSerializer(serializers.ModelSerializer):
    """Serializer for external egg batches."""
    
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    egg_count = serializers.IntegerField(
        source='egg_production.egg_count', read_only=True
    )
    
    class Meta:
        model = ExternalEggBatch
        fields = [
            'id', 'egg_production', 'supplier', 'supplier_name',
            'batch_number', 'provenance_data', 'egg_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EggProductionSerializer(serializers.ModelSerializer):
    """Serializer for egg production."""
    
    pair_display = serializers.CharField(source='pair.__str__', read_only=True)
    external_batch = ExternalEggBatchSerializer(read_only=True)
    batch_assignment_count = serializers.IntegerField(
        source='batch_assignments.count', read_only=True
    )
    
    class Meta:
        model = EggProduction
        fields = [
            'id', 'pair', 'pair_display', 'egg_batch_id', 'egg_count',
            'production_date', 'destination_station', 'source_type',
            'external_batch', 'batch_assignment_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validate egg production logic."""
        # This validation is also in the model, but we check here for API clarity
        if data.get('source_type') == 'internal' and not data.get('pair'):
            raise serializers.ValidationError(
                "Internal egg production must have a breeding pair."
            )
        if data.get('source_type') == 'external' and data.get('pair'):
            raise serializers.ValidationError(
                "External egg production cannot have a breeding pair."
            )
        return data
    
    def create(self, validated_data):
        """Handle creation with potential external batch data."""
        # If this is an external egg production, we might need to create
        # the ExternalEggBatch in a separate step or via a custom view
        return super().create(validated_data)


class BatchParentageSerializer(serializers.ModelSerializer):
    """Serializer for batch parentage."""
    
    batch_number = serializers.CharField(
        source='batch.batch_number', read_only=True
    )
    egg_batch_id = serializers.CharField(
        source='egg_production.egg_batch_id', read_only=True
    )
    egg_source_type = serializers.CharField(
        source='egg_production.source_type', read_only=True
    )
    
    class Meta:
        model = BatchParentage
        fields = [
            'id', 'batch', 'batch_number', 'egg_production',
            'egg_batch_id', 'egg_source_type', 'assignment_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure batch is in egg or early stage."""
        batch = data['batch']
        if batch.lifecycle_stage.name.lower() not in ['egg', 'alevin', 'fry']:
            raise serializers.ValidationError(
                "Eggs can only be assigned to batches in egg, alevin, or fry stages."
            )
        return data


class EggProductionDetailSerializer(EggProductionSerializer):
    """Detailed serializer for egg production with nested data."""
    
    pair = BreedingPairSerializer(read_only=True)
    batch_assignments = BatchParentageSerializer(many=True, read_only=True)
    
    class Meta(EggProductionSerializer.Meta):
        # Extend parent fields with nested batch assignments
        fields = EggProductionSerializer.Meta.fields + ['batch_assignments']
