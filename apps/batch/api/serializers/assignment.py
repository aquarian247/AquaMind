"""
Serializer for the BatchContainerAssignment model.

This serializer handles the conversion between JSON and Django model instances
for batch container assignment data, including validation of capacity and population.
"""
from decimal import Decimal
from rest_framework import serializers
from django.core.validators import MinValueValidator
from apps.batch.models import BatchContainerAssignment, Batch, LifeCycleStage
from apps.infrastructure.models import Container
from apps.batch.api.serializers.utils import calculate_biomass_kg
from apps.batch.api.serializers.validation import validate_container_capacity, validate_batch_population
from apps.batch.api.serializers.base import BatchBaseSerializer


class BatchContainerAssignmentSerializer(BatchBaseSerializer):
    """Serializer for BatchContainerAssignment model."""
    
    class NestedBatchSerializer(serializers.ModelSerializer):
        class Meta:
            model = Batch
            fields = ['id', 'batch_number', 'status']
    
    class NestedContainerSerializer(serializers.ModelSerializer):
        class Meta:
            model = Container
            fields = ['id', 'name', 'active']
    
    class NestedLifeCycleStageSerializer(serializers.ModelSerializer):
        class Meta:
            model = LifeCycleStage
            fields = ['id', 'name']
    
    # Define write-only fields for foreign keys
    batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        source='batch',
        write_only=True
    )
    container_id = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        source='container',
        write_only=True
    )
    lifecycle_stage_id = serializers.PrimaryKeyRelatedField(
        queryset=LifeCycleStage.objects.all(),
        source='lifecycle_stage',
        write_only=True,
        required=False
    )
    
    # Define nested serializers for read-only representation
    batch = NestedBatchSerializer(read_only=True)
    container = NestedContainerSerializer(read_only=True)
    lifecycle_stage = NestedLifeCycleStageSerializer(read_only=True)
    avg_weight_g = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.0'))],
        required=False
    )
    assignment_date = serializers.DateField(required=False)
    batch_info = serializers.SerializerMethodField()
    container_info = serializers.SerializerMethodField()
    lifecycle_stage_info = serializers.SerializerMethodField()
    biomass_kg = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = BatchContainerAssignment
        fields = (
            'id', 'batch', 'batch_id', 'container', 'container_id', 'lifecycle_stage', 'lifecycle_stage_id', 'assignment_date', 
            'population_count', 'avg_weight_g', 'biomass_kg', 'is_active', 'notes',
            'created_at', 'updated_at', 'batch_info', 'container_info', 'lifecycle_stage_info'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'biomass_kg', 'batch_info', 
            'container_info', 'lifecycle_stage_info'
        )
        extra_kwargs = {
            'lifecycle_stage_id': {'required': False},
            'assignment_date': {'required': False},
            'population_count': {'required': False},
            'avg_weight_g': {'required': False},
            'is_active': {'required': False},
            'notes': {'required': False},
        }
    
    def get_batch_info(self, obj):
        """Get basic batch information."""
        return self.get_nested_info(obj, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number',
            'species_name': 'species.name'
        })

    def get_container_info(self, obj):
        """Get basic container information."""
        return self.get_nested_info(obj, 'container', {
            'id': 'id',
            'name': 'name',
            'container_type': 'container_type.name'
        })

    def get_lifecycle_stage_info(self, obj):
        """Get lifecycle stage information."""
        return self.get_nested_info(obj, 'lifecycle_stage', {
            'id': 'id',
            'name': 'name',
            'order': 'order'
        })

    def validate(self, data):
        """
        Validate that:
        - The container has sufficient capacity for the assigned biomass
        - The batch population count assigned doesn't exceed the batch's total population
        """
        errors = {}
        
        # Get the batch and container from data
        batch = data.get('batch')
        container = data.get('container')
        assignment_id = self.instance.id if self.instance else None
        
        # Validate container capacity
        if batch and container and 'biomass_kg' in data:
            capacity_error = validate_container_capacity(
                container, 
                data['biomass_kg'], 
                assignment_id
            )
            if capacity_error:
                errors['container'] = capacity_error
        
        # Validate batch population
        if batch and 'population_count' in data:
            population_error = validate_batch_population(
                batch, 
                data['population_count'], 
                assignment_id
            )
            if population_error:
                errors['population_count'] = population_error
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return super().validate(data)

    def create(self, validated_data):
        """Create a new batch container assignment."""
        population_count = validated_data.get('population_count', 0)
        avg_weight_g = validated_data.get('avg_weight_g', Decimal('0.0'))
        validated_data['biomass_kg'] = calculate_biomass_kg(population_count, avg_weight_g)
        return BatchContainerAssignment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing batch container assignment."""
        population_count = validated_data.get('population_count', instance.population_count)
        avg_weight_g = validated_data.get('avg_weight_g', instance.avg_weight_g)
        validated_data['biomass_kg'] = calculate_biomass_kg(population_count, avg_weight_g)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
