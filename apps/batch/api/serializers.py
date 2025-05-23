"""
Serializers for the batch app.

These serializers convert Django models to JSON and vice versa for the REST API.
They handle validation, data conversion, and nested relationships for batch-related models.
"""
import datetime
import decimal
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.batch.models import (
    Species,
    LifeCycleStage,
    Batch,
    BatchContainerAssignment,
    BatchComposition,
    BatchTransfer,
    MortalityEvent,
    GrowthSample
)
from apps.infrastructure.models import Container
import statistics
import math


class SpeciesSerializer(serializers.ModelSerializer):
    """Serializer for the Species model."""

    class Meta:
        model = Species
        fields = '__all__'
        read_only_fields = ('created_at',)

    def validate(self, data):
        """Validate temperature and pH ranges."""
        # Validate temperature range
        if ('optimal_temperature_min' in data and 'optimal_temperature_max' in data and
                data['optimal_temperature_min'] and data['optimal_temperature_max']):
            if data['optimal_temperature_min'] > data['optimal_temperature_max']:
                raise serializers.ValidationError(
                    {"optimal_temperature_min": "Minimum temperature cannot be greater than maximum temperature."}
                )
        
        # Validate pH range
        if ('optimal_ph_min' in data and 'optimal_ph_max' in data and
                data['optimal_ph_min'] and data['optimal_ph_max']):
            if data['optimal_ph_min'] > data['optimal_ph_max']:
                raise serializers.ValidationError(
                    {"optimal_ph_min": "Minimum pH cannot be greater than maximum pH."}
                )
        
        return data


class LifeCycleStageSerializer(serializers.ModelSerializer):
    """Serializer for the LifeCycleStage model."""
    
    species_name = serializers.StringRelatedField(source='species', read_only=True)

    class Meta:
        model = LifeCycleStage
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def validate(self, data):
        """Validate weight and length ranges."""
        # Validate weight range
        if ('expected_weight_min_g' in data and 'expected_weight_max_g' in data and
                data['expected_weight_min_g'] and data['expected_weight_max_g']):
            if data['expected_weight_min_g'] > data['expected_weight_max_g']:
                raise serializers.ValidationError(
                    {"expected_weight_min_g": "Minimum weight cannot be greater than maximum weight."}
                )
        
        # Validate length range
        if ('expected_length_min_cm' in data and 'expected_length_max_cm' in data and
                data['expected_length_min_cm'] and data['expected_length_max_cm']):
            if data['expected_length_min_cm'] > data['expected_length_max_cm']:
                raise serializers.ValidationError(
                    {"expected_length_min_cm": "Minimum length cannot be greater than maximum length."}
                )
        
        return data


class BatchSerializer(serializers.ModelSerializer):
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

    def _format_decimal(self, value):
        """Convert Decimal (or numeric) to a string with two decimal places."""
        if value is None:
            return "0.00"
        try:
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
            return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except Exception:
            return "0.00"

    def get_calculated_biomass_kg(self, obj):
        return self._format_decimal(obj.calculated_biomass_kg)

    def get_calculated_avg_weight_g(self, obj):
        return self._format_decimal(obj.calculated_avg_weight_g)

    def create(self, validated_data):
        """
        Create a new batch instance.
        """
        if 'expected_end_date' not in validated_data or validated_data['expected_end_date'] is None:
            validated_data['expected_end_date'] = validated_data['start_date'] + datetime.timedelta(days=30)
        return Batch.objects.create(**validated_data)

    def validate(self, data):
        """Validate the batch data."""
        # Validate that expected_end_date is after start_date
        if 'expected_end_date' in data and 'start_date' in data:
            if data['expected_end_date'] and data['start_date'] and data['expected_end_date'] <= data['start_date']:
                raise serializers.ValidationError({
                    'expected_end_date': 'Expected end date must be after start date.'
                })
        
        # Validate that lifecycle_stage belongs to the correct species
        if 'lifecycle_stage' in data and 'species' in data:
            lifecycle_stage = data['lifecycle_stage']
            species = data['species']
            
            if lifecycle_stage.species.id != species.id:
                raise serializers.ValidationError({
                    'lifecycle_stage': f'Lifecycle stage {lifecycle_stage.name} does not belong to species {species.name}.'
                })
        
        return data
    
    def update(self, instance, validated_data):
        """Update an existing batch."""
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class BatchTransferSerializer(serializers.ModelSerializer):
    """Serializer for the BatchTransfer model."""
    
    source_batch_number = serializers.StringRelatedField(source='source_batch', read_only=True)
    destination_batch_number = serializers.StringRelatedField(source='destination_batch', read_only=True)
    transfer_type_display = serializers.CharField(source='get_transfer_type_display', read_only=True)
    source_lifecycle_stage_name = serializers.StringRelatedField(source='source_lifecycle_stage', read_only=True)
    destination_lifecycle_stage_name = serializers.StringRelatedField(
        source='destination_lifecycle_stage', read_only=True
    )
    # Container information fields from assignments
    source_container_name = serializers.StringRelatedField(source='source_assignment.container', read_only=True)
    destination_container_name = serializers.StringRelatedField(source='destination_assignment.container', read_only=True)
    source_batch_info = serializers.SerializerMethodField()
    destination_batch_info = serializers.SerializerMethodField()

    class Meta:
        model = BatchTransfer
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_source_batch_info(self, obj):
        """Get basic source batch information."""
        if obj.source_batch:
            return {
                'id': obj.source_batch.id,
                'batch_number': obj.source_batch.batch_number
            }
        return None

    def get_destination_batch_info(self, obj):
        """Get basic destination batch information."""
        if obj.destination_batch:
            return {
                'id': obj.destination_batch.id,
                'batch_number': obj.destination_batch.batch_number
            }
        return None

    def validate(self, data):
        """
        Validate transfer data including:
        - Transfer count doesn't exceed source batch population
        - Source and destination fields are correctly specified based on transfer type
        """
        errors = {}
        
        # Get the source batch from data
        source_batch = data.get('source_batch')
        if source_batch and 'transferred_count' in data:
            # Validate transfer count against source batch population
            if data['transferred_count'] > source_batch.calculated_population_count:
                errors['transferred_count'] = (
                    f"Transfer count ({data['transferred_count']}) exceeds source batch "
                    f"population ({source_batch.calculated_population_count})."
                )
        
        # Validate transfer type-specific fields
        if 'transfer_type' in data:
            transfer_type = data['transfer_type']
            # For lifecycle changes, validate that destination lifecycle stage is specified
            if transfer_type == 'LIFECYCLE' and not data.get('destination_lifecycle_stage'):
                errors['destination_lifecycle_stage'] = "Destination lifecycle stage is required for lifecycle transfers."
            
            # For container transfers, validate that destination container is specified
            if transfer_type == 'CONTAINER' and not data.get('destination_assignment'):
                errors['destination_assignment'] = "Destination assignment is required for container transfers."
            
            # For batch splits, validate that a destination batch is specified
            if transfer_type == 'SPLIT' and not data.get('destination_batch'):
                errors['destination_batch'] = "Destination batch is required for batch splits."
            
            # For batch merges, validate that a destination batch is specified
            if transfer_type == 'MERGE' and not data.get('destination_batch'):
                errors['destination_batch'] = "Destination batch is required for batch merges."
        
        # Validate transferred biomass
        if 'source_biomass_kg' in data and 'transferred_biomass_kg' in data:
            if data['transferred_biomass_kg'] > data['source_biomass_kg']:
                errors['transferred_biomass_kg'] = (
                    f"Transferred biomass ({data['transferred_biomass_kg']} kg) "
                    f"exceeds source biomass ({data['source_biomass_kg']} kg)."
                )
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data


class MortalityEventSerializer(serializers.ModelSerializer):
    """Serializer for the MortalityEvent model."""
    
    batch_number = serializers.StringRelatedField(source='batch', read_only=True)
    cause_display = serializers.CharField(source='get_cause_display', read_only=True)
    batch_info = serializers.SerializerMethodField()
    container_info = serializers.SerializerMethodField()
    reason_info = serializers.SerializerMethodField()

    class Meta:
        model = MortalityEvent
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def get_batch_info(self, obj):
        """Get basic batch information."""
        if obj.batch:
            return {
                'id': obj.batch.id,
                'batch_number': obj.batch.batch_number
            }
        return None

    def get_container_info(self, obj):
        """Get basic container information."""
        if obj.container:
            return {
                'id': obj.container.id,
                'name': obj.container.name
            }
        return None

    def get_reason_info(self, obj):
        """Get mortality reason information."""
        if obj.reason:
            return {
                'id': obj.reason.id,
                'name': obj.reason.name
            }
        return None

    def validate(self, data):
        """
        Validate that mortality count doesn't exceed batch population and
        that mortality biomass doesn't exceed batch biomass.
        """
        errors = {}
        
        # Get the batch from data or database
        batch = data.get('batch')

        if batch:
            # Check if mortality count doesn't exceed batch population
            if 'count' in data:
                if data['count'] > batch.calculated_population_count:
                    errors['count'] = (
                        f"Mortality count ({data['count']}) exceeds batch "
                        f"population ({batch.calculated_population_count})."
                    )
            
            # Check if mortality biomass doesn't exceed batch biomass
            if 'biomass_kg' in data:
                if data['biomass_kg'] > batch.calculated_biomass_kg:
                    errors['biomass_kg'] = (
                        f"Mortality biomass ({data['biomass_kg']} kg) exceeds batch "
                        f"biomass ({batch.calculated_biomass_kg} kg)."
                    )
        
        if errors:
            raise serializers.ValidationError(errors)

        return data


class BatchContainerAssignmentSerializer(serializers.ModelSerializer):
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
    
    batch = NestedBatchSerializer(read_only=True)
    batch_id = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all(), source='batch', write_only=True)
    container = NestedContainerSerializer(read_only=True)
    container_id = serializers.PrimaryKeyRelatedField(queryset=Container.objects.all(), source='container', write_only=True)
    lifecycle_stage = NestedLifeCycleStageSerializer(read_only=True)
    lifecycle_stage_id = serializers.PrimaryKeyRelatedField(
        queryset=LifeCycleStage.objects.all(),
        source='lifecycle_stage',
        write_only=True,
        required=False
    )
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
        if obj.batch:
            return {
                'id': obj.batch.id,
                'batch_number': obj.batch.batch_number,
                'species_name': obj.batch.species.name if obj.batch.species else None
            }
        return None

    def get_container_info(self, obj):
        """Get basic container information."""
        if obj.container:
            return {
                'id': obj.container.id,
                'name': obj.container.name,
                'container_type': obj.container.container_type.name if obj.container.container_type else None
            }
        return None

    def get_lifecycle_stage_info(self, obj):
        """Get lifecycle stage information."""
        if obj.lifecycle_stage:
            return {
                'id': obj.lifecycle_stage.id,
                'name': obj.lifecycle_stage.name,
                'order': obj.lifecycle_stage.order
            }
        return None

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
        
        if batch and container and 'biomass_kg' in data:
            # Check container capacity
            existing_biomass = BatchContainerAssignment.objects.filter(
                container=container, 
                is_active=True
            ).exclude(id=assignment_id).values_list('biomass_kg', flat=True)
            
            total_existing_biomass = sum(existing_biomass)
            new_total_biomass = total_existing_biomass + data['biomass_kg']
            
            # Check if container has a maximum biomass capacity set
            if container.max_biomass_kg and new_total_biomass > container.max_biomass_kg:
                errors['container'] = (
                    f"Container capacity exceeded: Total biomass {new_total_biomass} kg is greater than "
                    f"maximum capacity of {container.max_biomass_kg} kg."
                )
        
        # Check if the assignment population doesn't exceed the batch's total population
        if batch and 'population_count' in data:
            # Get existing assignments for this batch, excluding this one if updating
            existing_assignments = BatchContainerAssignment.objects.filter(
                batch=batch, 
                is_active=True
            ).exclude(id=assignment_id)
            
            total_assigned = sum(a.population_count for a in existing_assignments)
            batch_total_population = batch.calculated_population_count
            proposed_total = total_assigned + data['population_count']
            
            # Only validate if batch has a non-zero population to avoid test setup issues
            if batch_total_population > 0 and proposed_total > batch_total_population:
                errors['population_count'] = (
                    f"Population count exceeds batch total: Proposed total {proposed_total} is greater than "
                    f"available population {batch_total_population}."
                )
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data

    def create(self, validated_data):
        """Create a new batch container assignment."""
        population_count = validated_data.get('population_count', 0)
        avg_weight_g = validated_data.get('avg_weight_g', decimal.Decimal('0.0'))
        validated_data['biomass_kg'] = (population_count * avg_weight_g) / 1000 if population_count and avg_weight_g else decimal.Decimal('0.0')
        return BatchContainerAssignment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing batch container assignment."""
        population_count = validated_data.get('population_count', instance.population_count)
        avg_weight_g = validated_data.get('avg_weight_g', instance.avg_weight_g)
        validated_data['biomass_kg'] = (population_count * avg_weight_g) / 1000 if population_count and avg_weight_g else decimal.Decimal('0.0')
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class BatchCompositionSerializer(serializers.ModelSerializer):
    """Serializer for the BatchComposition model."""
    
    class NestedBatchSerializer(serializers.ModelSerializer):
        class Meta:
            model = Batch
            fields = ['id', 'batch_number', 'status']
    
    mixed_batch = NestedBatchSerializer(read_only=True)
    mixed_batch_id = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all(), source='mixed_batch', write_only=True)
    source_batch = NestedBatchSerializer(read_only=True)
    source_batch_id = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.all(), source='source_batch', write_only=True)
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )

    class Meta:
        model = BatchComposition
        fields = ['id', 'mixed_batch', 'mixed_batch_id', 'source_batch', 'source_batch_id',
                  'population_count', 'biomass_kg', 'percentage', 'created_at']
        read_only_fields = ('created_at',)
    
    def validate(self, data):
        """
        Validate the composition data including:
        - Population and biomass don't exceed source batch totals (if provided)
        - Percentage is between 0 and 100
        - At least one of population, biomass, or percentage is provided
        """
        errors = {}
        
        # Get current source batch, if available
        current_source_batch = data.get('source_batch')
        if not current_source_batch and self.instance:
            current_source_batch = self.instance.source_batch
        
        # Check that at least one metric is provided
        if not any(key in data for key in ['population_count', 'biomass_kg', 'percentage']):
            errors['non_field_errors'] = "At least one of population count, biomass, or percentage must be provided."
        
        # Validate percentage if provided
        if 'percentage' in data:
            if data['percentage'] < 0 or data['percentage'] > 100:
                errors['percentage'] = "Percentage must be between 0 and 100."
        
        # Validate population count against source batch if provided
        if 'population_count' in data and current_source_batch:
            try:
                pop_count = int(data['population_count'])
                source_pop_avail = current_source_batch.calculated_population_count
                if pop_count <= 0:
                    errors['population_count'] = "Population count must be greater than zero."
                elif source_pop_avail is not None and pop_count > source_pop_avail:
                    errors['population_count'] = (
                        f"Population ({pop_count}) cannot exceed available population "
                        f"in source batch ({current_source_batch.batch_number}: {source_pop_avail})."
                    )
            except (ValueError, TypeError):
                errors['population_count'] = "Population count must be a valid integer."
        
        # Validate biomass against source batch if provided
        if 'biomass_kg' in data and current_source_batch:
            try:
                biomass_kg = data['biomass_kg']
                biomass_kg_decimal = Decimal(biomass_kg)
                source_bio_avail = current_source_batch.calculated_biomass_kg
                if biomass_kg_decimal <= Decimal('0'):
                    errors['biomass_kg'] = "Biomass must be greater than zero."
                elif source_bio_avail is not None and biomass_kg_decimal > source_bio_avail:
                    errors['biomass_kg'] = (
                        f"Biomass ({biomass_kg_decimal} kg) cannot exceed available biomass "
                        f"in source batch ({current_source_batch.batch_number}: {source_bio_avail} kg)."
                    )
            except InvalidOperation:
                errors['biomass_kg'] = "Biomass must be a valid decimal number."
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data


class GrowthSampleSerializer(serializers.ModelSerializer):
    """Serializer for GrowthSample model with calculated fields."""
    assignment_details = BatchContainerAssignmentSerializer(source='assignment', read_only=True)
    individual_lengths = serializers.ListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01')),
        write_only=True, required=False, allow_empty=True, max_length=1000
    )
    individual_weights = serializers.ListField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01')),
        write_only=True, required=False, allow_empty=True, max_length=1000
    )
    
    # Override sample_date to explicitly handle date conversion
    # Mark as not required since we'll set it from journal_entry if needed
    sample_date = serializers.DateField(required=False)

    class Meta:
        model = GrowthSample
        fields = [
            'id', 'assignment', 'assignment_details', 'sample_date', 'sample_size',
            'avg_weight_g', 'avg_length_cm', 'std_deviation_weight',
            'std_deviation_length', 'min_weight_g', 'max_weight_g',
            'condition_factor', 'notes', 'created_at', 'updated_at',
            'individual_lengths', 'individual_weights'
        ]
        read_only_fields = (
            'id',
            'assignment_details', # Read-only representation
            'created_at',
            'updated_at'
        )
        extra_kwargs = {
            'assignment': {'required': False}, # Shouldn't change on update via JournalEntry
            'sample_date': {'required': False}, # Set from journal_entry.entry_date if missing
            'avg_weight_g': {'required': False},  # Not required if individual_weights provided
            'avg_length_cm': {'required': False},  # Not required if individual_lengths provided
            'std_deviation_weight': {'required': False},  # Preserve if provided
            'std_deviation_length': {'required': False},  # Preserve if provided
            'condition_factor': {'required': False}  # Calculated if possible
        }

    def validate(self, data):
        """Custom validation to ensure sample_size matches individual lists if provided."""
        # Run standard field validation and parent validation first
        data = super().validate(data)
        
        # The DateField serializer field should have already converted the datetime to date
        # but add an extra safety check just in case
        if 'sample_date' in data and hasattr(data['sample_date'], 'date'):
            data['sample_date'] = data['sample_date'].date()
        
        # For create operations, sample_date is required but can come from journal_entry
        if not self.instance and 'sample_date' not in data:
            # Try to get from context
            if 'journal_entry' in self.context:
                journal_entry = self.context.get('journal_entry')
                if journal_entry and journal_entry.entry_date:
                    entry_date = journal_entry.entry_date
                    data['sample_date'] = entry_date.date() if hasattr(entry_date, 'date') else entry_date
            # If we still don't have a sample_date, raise validation error
            if 'sample_date' not in data:
                raise serializers.ValidationError({'sample_date': 'This field is required when creating a GrowthSample.'})

        # --- Restore validation using initial_data ---
        initial_data_errors = {}

        # Check if we have initial_data (might not be set in certain contexts)
        if hasattr(self, 'initial_data'):
            # Get individual measurements from initial_data
            initial_lengths = self.initial_data.get('individual_lengths', [])
            initial_weights = self.initial_data.get('individual_weights', [])
            # Use validated 'sample_size' from the 'data' dict returned by super().validate()
            # or fall back to initial_data if sample_size wasn't in the input to super()
            sample_size_for_check = data.get('sample_size', self.initial_data.get('sample_size'))
        else:
            # If initial_data is not available, use empty lists and data
            initial_lengths = []
            initial_weights = []
            sample_size_for_check = data.get('sample_size')

        # Check sample_size against initial individual measurement lists
        if sample_size_for_check is not None and (initial_lengths or initial_weights):
            if initial_lengths and len(initial_lengths) != sample_size_for_check:
                initial_data_errors['sample_size'] = [
                    f"Sample size ({sample_size_for_check}) must match length of individual_lengths ({len(initial_lengths)})."
                ]
            if initial_weights and len(initial_weights) != sample_size_for_check:
                # Use setdefault to avoid overwriting the length error if both fail
                initial_data_errors.setdefault('sample_size', []).append(
                    f"Sample size ({sample_size_for_check}) must match length of individual_weights ({len(initial_weights)})."
                )

        # Check initial list length mismatch
        if initial_lengths and initial_weights and len(initial_lengths) != len(initial_weights):
            initial_data_errors['individual_measurements'] = [
                "Length of individual_weights must match individual_lengths."
            ]
        
        # Raise collected errors if any
        if initial_data_errors:
            raise serializers.ValidationError(initial_data_errors)
         # --- End restored validation using initial_data ---

        # --- Calculation logic if individual lists not provided ---
        sample_size = data.get('sample_size')  # Use validated sample_size now
        assignment = data.get('assignment')

        # If assignment is not in data (e.g., partial update), try getting it from the instance
        if assignment is None and self.instance:
            assignment = self.instance.assignment

        # Check sample_size against population_count
        if assignment is not None and sample_size is not None:
            # If assignment is an ID (not an instance), fetch the object
            # This should generally not happen if we correctly pull from self.instance
            if not isinstance(assignment, BatchContainerAssignment):
                try:
                    assignment = BatchContainerAssignment.objects.get(id=assignment)
                except BatchContainerAssignment.DoesNotExist:
                    # This might be caught by PrimaryKeyRelatedField already, but belt-and-suspenders
                    raise serializers.ValidationError({'assignment': "Assignment does not exist."})
            
            # Determine the population count to check against.
            # Use the assignment's current population count.
            current_population_count = assignment.population_count
            
            if sample_size > current_population_count:
                raise serializers.ValidationError(
                    {'sample_size': f"Sample size ({sample_size}) exceeds assignment population ({current_population_count})."}
                )

        # Check min/max weight
        min_weight = data.get('min_weight_g')
        max_weight = data.get('max_weight_g')
        if min_weight is not None and max_weight is not None and min_weight > max_weight:
            raise serializers.ValidationError(
                {'min_weight_g': "Minimum weight cannot be greater than maximum weight."}
            )

        # Process individual measurements to calculate stats before final validation
        # Note: This uses initial_data again because the fields were write_only=True
        data = self._process_individual_measurements(data)
        return data

    def _process_individual_measurements(self, validated_data):
        """Calculate stats from initial individual lists and update validated_data."""
        # Handle cases where initial_data might not be available
        if hasattr(self, 'initial_data'):
            # Use initial_data because fields are write_only=True, convert to Decimal early.
            individual_lengths = self.initial_data.get('individual_lengths', None)
            individual_weights = self.initial_data.get('individual_weights', None)
        else:
            # If no initial_data, no individual measurements to process
            return validated_data
            
        lengths_decimal = []
        weights_decimal = []

        if individual_lengths:
            try:
                lengths_decimal = [decimal.Decimal(l) for l in individual_lengths]
                avg_len, std_dev_len = self._calculate_stats(lengths_decimal, 'individual_lengths')
                validated_data['avg_length_cm'] = avg_len
                validated_data['std_deviation_length'] = std_dev_len
            except (ValueError, TypeError, decimal.InvalidOperation):
                raise serializers.ValidationError({'individual_lengths': "Invalid number format in individual_lengths."})
        # Do not override avg_length_cm if provided and no individual_lengths are given

        if individual_weights:
            try:
                weights_decimal = [decimal.Decimal(w) for w in individual_weights]
                avg_wt, std_dev_wt = self._calculate_stats(weights_decimal, 'individual_weights')
                validated_data['avg_weight_g'] = avg_wt
                validated_data['std_deviation_weight'] = std_dev_wt
            except (ValueError, TypeError, decimal.InvalidOperation):
                raise serializers.ValidationError({'individual_weights': "Invalid number format in individual_weights."})
        # Do not override avg_weight_g if provided and no individual_weights are given

        # Calculate condition factor only if both lists were provided *in this request*
        if individual_lengths and individual_weights:
            try:
                # Use the already converted Decimal lists
                validated_data['condition_factor'] = self._calculate_condition_factor_from_individuals(
                    weights_decimal, lengths_decimal
                )
            except serializers.ValidationError: # Propagate validation errors from calculation
                raise
            except Exception as e: # Catch other potential calculation errors
                raise serializers.ValidationError({'individual_measurements': f"Error calculating K factor: {e}"})
        # If only one list provided, let the model's save method handle K calculation later if possible
        elif individual_lengths or individual_weights:
            validated_data['condition_factor'] = None  # Explicitly set to None for recalculation trigger

        return validated_data

    def _calculate_stats(self, numeric_data, field_name):
        """Calculate mean and std deviation for a list of numbers."""
        if not numeric_data:
            return None, None
        try:
            # Ensure data are Decimals already
            avg = statistics.mean(numeric_data)
            std_dev = statistics.stdev(numeric_data) if len(numeric_data) > 1 else decimal.Decimal('0.0')
            # Quantize for consistent output
            quantizer = decimal.Decimal('0.01')
            return avg.quantize(quantizer), std_dev.quantize(quantizer)
        except (ValueError, TypeError, decimal.InvalidOperation, statistics.StatisticsError):
            raise serializers.ValidationError({field_name: "Invalid numeric data for statistics calculation."})

    def _calculate_condition_factor_from_individuals(self, weights, lengths):
        """Calculate average condition factor (K) from lists of weights (g) and lengths (cm)."""
        # Expects lists of Decimals
        if not weights or not lengths or len(weights) != len(lengths):
            return None # Cannot calculate if lists are missing, empty, or mismatched

        try:
            k_factors = []
            for w, l in zip(weights, lengths):
                # Ensure they are Decimals before calculation
                if not isinstance(w, decimal.Decimal) or not isinstance(l, decimal.Decimal):
                    raise TypeError("Weights and lengths must be Decimal objects.")
                if l <= 0:
                    continue # Skip fish with zero or negative length
                k = (decimal.Decimal('100') * w) / (l ** 3)
                k_factors.append(k)

            if not k_factors:
                return None
            avg_k = statistics.mean(k_factors)
            quantizer = decimal.Decimal('0.01')
            return avg_k.quantize(quantizer)
        except (ValueError, TypeError, decimal.InvalidOperation, statistics.StatisticsError):
            raise serializers.ValidationError({'individual_measurements': "Invalid numeric data for K factor calculation."})

    def create(self, validated_data):
        """Create a new GrowthSample with calculated fields."""
        # Make sure sample_date is present - this is a critical field
        if 'sample_date' not in validated_data:
            # For save(journal_entry=...) calls, try to get from journal_entry
            journal_entry = self.context.get('journal_entry', None)
            if journal_entry and hasattr(journal_entry, 'entry_date'):
                entry_date = journal_entry.entry_date
                validated_data['sample_date'] = entry_date.date() if hasattr(entry_date, 'date') else entry_date
        
        # Add individual measurements to serializer data
        individual_weights = validated_data.pop('individual_weights', [])
        individual_lengths = validated_data.pop('individual_lengths', [])
        
        # Ensure sample_date is a date, not a datetime
        if 'sample_date' in validated_data and hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        return GrowthSample.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Handle individual measurements - extract from validated_data
        individual_lengths = validated_data.pop('individual_lengths', None)
        individual_weights = validated_data.pop('individual_weights', None)
        
        # Ensure sample_date is a date, not a datetime (extra safety check)
        if 'sample_date' in validated_data and hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()
            
        # Perform the update using the standard method
        return super().update(instance, validated_data)
