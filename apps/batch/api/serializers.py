"""
Serializers for the batch app.

These serializers convert Django models to JSON and vice versa for the REST API.
They handle validation, data conversion, and nested relationships for batch-related models.
"""
from rest_framework import serializers
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
import decimal


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
    
    species_name = serializers.StringRelatedField(source='species', read_only=True)
    lifecycle_stage_name = serializers.StringRelatedField(source='lifecycle_stage', read_only=True)
    container_name = serializers.StringRelatedField(source='container', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'biomass_kg')
    
    def validate(self, data):
        """
        Validate that the batch doesn't exceed container capacity and
        that the lifecycle stage belongs to the specified species.
        """
        errors = {}
        
        # Check if the lifecycle stage belongs to the specified species
        if 'species' in data and 'lifecycle_stage' in data:
            if data['lifecycle_stage'].species != data['species']:
                errors['lifecycle_stage'] = f"This lifecycle stage does not belong to {data['species'].name}."
        
        # Check if the batch doesn't exceed container capacity
        if 'container' in data and 'biomass_kg' in data:
            # Get existing biomass in the container excluding this batch
            batch_id = self.instance.id if self.instance else None
            existing_biomass = Batch.objects.filter(
                container=data['container']
            ).exclude(id=batch_id).values_list('biomass_kg', flat=True)
            
            total_existing_biomass = sum(existing_biomass)
            new_total_biomass = total_existing_biomass + data['biomass_kg']
            
            # Check if container has a maximum biomass capacity set
            container = Container.objects.get(id=data['container'].id)
            if container.max_biomass_kg and new_total_biomass > container.max_biomass_kg:
                errors['biomass_kg'] = (
                    f"Total biomass ({new_total_biomass} kg) exceeds container capacity "
                    f"({container.max_biomass_kg} kg)."
                )
        
        # Check if end date is after start date
        if 'start_date' in data and 'expected_end_date' in data and data['expected_end_date']:
            if data['expected_end_date'] < data['start_date']:
                errors['expected_end_date'] = "Expected end date cannot be before start date."
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data
        
    def create(self, validated_data):
        """Create a new batch with calculated biomass."""
        # Calculate biomass from population count and average weight
        if 'population_count' in validated_data and 'avg_weight_g' in validated_data:
            biomass_kg = (validated_data['population_count'] * float(validated_data['avg_weight_g'])) / 1000
            validated_data['biomass_kg'] = biomass_kg
            
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update a batch with recalculated biomass if necessary."""
        # If population_count or avg_weight_g is updated, recalculate biomass
        population_count = validated_data.get('population_count', instance.population_count)
        avg_weight_g = validated_data.get('avg_weight_g', instance.avg_weight_g)
        
        if ('population_count' in validated_data or 'avg_weight_g' in validated_data):
            biomass_kg = (population_count * float(avg_weight_g)) / 1000
            instance.biomass_kg = biomass_kg
        
        # Update other fields
        for attr, value in validated_data.items():
            if attr not in ['biomass_kg']:
                setattr(instance, attr, value)
        
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

    class Meta:
        model = BatchTransfer
        fields = '__all__'
        read_only_fields = ('created_at',)
    
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
            if data['transferred_count'] > source_batch.population_count:
                errors['transferred_count'] = (
                    f"Transfer count ({data['transferred_count']}) exceeds source batch "
                    f"population ({source_batch.population_count})."
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

    class Meta:
        model = MortalityEvent
        fields = '__all__'
        read_only_fields = ('created_at',)
    
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
                if data['count'] > batch.population_count:
                    errors['count'] = (
                        f"Mortality count ({data['count']}) exceeds batch "
                        f"population ({batch.population_count})."
                    )
            
            # Check if mortality biomass doesn't exceed batch biomass
            if 'biomass_kg' in data:
                if data['biomass_kg'] > batch.biomass_kg:
                    errors['biomass_kg'] = (
                        f"Mortality biomass ({data['biomass_kg']} kg) exceeds batch "
                        f"biomass ({batch.biomass_kg} kg)."
                    )
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data


class BatchContainerAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for the BatchContainerAssignment model."""
    
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
    lifecycle_stage_id = serializers.PrimaryKeyRelatedField(queryset=LifeCycleStage.objects.all(), source='lifecycle_stage', write_only=True)
    
    class Meta:
        model = BatchContainerAssignment
        fields = ['id', 'batch', 'batch_id', 'container', 'container_id', 'lifecycle_stage', 'lifecycle_stage_id', 
                  'population_count', 'biomass_kg', 'assignment_date', 'is_active', 'notes', 'created_at', 'updated_at']
        read_only_fields = ('created_at',)
    
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
                errors['biomass_kg'] = (
                    f"Total biomass ({new_total_biomass} kg) exceeds container capacity "
                    f"({container.max_biomass_kg} kg)."
                )
        
        # Check if the assignment population doesn't exceed the batch's total population
        if batch and 'population_count' in data:
            # Get existing assignments for this batch, excluding this one if updating
            existing_assignments = BatchContainerAssignment.objects.filter(
                batch=batch, 
                is_active=True
            ).exclude(id=assignment_id)
            
            total_assigned = sum(a.population_count for a in existing_assignments)
            
            if total_assigned + data['population_count'] > batch.population_count:
                errors['population_count'] = (
                    f"Total assigned population ({total_assigned + data['population_count']}) "
                    f"exceeds batch population ({batch.population_count})."
                )
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data


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
    
    class Meta:
        model = BatchComposition
        fields = ['id', 'mixed_batch', 'mixed_batch_id', 'source_batch', 'source_batch_id', 
                  'population_count', 'biomass_kg', 'percentage', 'created_at']
        read_only_fields = ('created_at',)
    
    def validate(self, data):
        """
        Validate that:
        - The population count doesn't exceed the source batch's population
        - The percentage is between 0 and 100
        """
        errors = {}
        
        # Check if the population count doesn't exceed the source batch's population
        source_batch = data.get('source_batch')
        if source_batch and 'population_count' in data:
            if data['population_count'] > source_batch.population_count:
                errors['population_count'] = (
                    f"Population count ({data['population_count']}) exceeds source batch "
                    f"population ({source_batch.population_count})."
                )
        
        # Check if the percentage is between 0 and 100
        if 'percentage' in data:
            if data['percentage'] < 0 or data['percentage'] > 100:
                errors['percentage'] = "Percentage must be between 0 and 100."
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return data


class GrowthSampleSerializer(serializers.ModelSerializer):
    """
    Serializer for the GrowthSample model.
    Handles calculation of avg/std dev for weight/length and condition_factor from individual measurements if provided.
    """
    # Use PrimaryKeyRelatedField for writing the assignment relation
    assignment = serializers.PrimaryKeyRelatedField(
        queryset=BatchContainerAssignment.objects.all(),
        help_text="ID of the BatchContainerAssignment this sample belongs to."
    )
    # Add write-only fields to accept individual measurements
    individual_lengths = serializers.ListField(
        child=serializers.DecimalField(max_digits=6, decimal_places=2, coerce_to_string=False),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="Optional: List of individual fish lengths (cm). If provided, avg_length_cm and std_deviation_length will be calculated."
    )
    individual_weights = serializers.ListField(
        child=serializers.DecimalField(max_digits=8, decimal_places=2, coerce_to_string=False),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="Optional: List of individual fish weights (g). If provided, avg_weight_g and std_deviation_weight will be calculated."
    )

    # Add a read-only field to show assignment details (optional, can customize)
    assignment_details = serializers.StringRelatedField(source='assignment', read_only=True)

    class Meta:
        model = GrowthSample
        fields = [
            'id', 'assignment', 'assignment_details', 'sample_date', 'sample_size',
            'avg_weight_g', 'avg_length_cm', 'std_deviation_weight',
            'std_deviation_length', 'min_weight_g', 'max_weight_g',
            'condition_factor', 'notes', 'created_at', 'updated_at',
            'individual_lengths', 'individual_weights' # Include write-only fields
        ]
        read_only_fields = (
            'id',
            'assignment_details', # Read-only representation
            'avg_length_cm', # Calculated if individual_lengths provided
            'std_deviation_length', # Calculated if individual_lengths provided
            'avg_weight_g', # Calculated if individual_weights provided
            'std_deviation_weight', # Calculated if individual_weights provided
            'condition_factor', # Calculated if both lists provided
            'created_at',
            'updated_at'
        )

    def _calculate_stats(self, data_list, field_name):
        """Helper to calculate avg and std dev from a list of Decimal numbers."""
        avg = None
        std_dev = None
        if data_list:
            if not all(isinstance(item, decimal.Decimal) for item in data_list):
                 # Convert to Decimal for precision if not already
                 try:
                     data_list = [decimal.Decimal(str(item)) for item in data_list]
                 except (decimal.InvalidOperation, TypeError) as e:
                     raise serializers.ValidationError({field_name: f"Invalid numeric value found: {e}"})

            try:
                avg = statistics.mean(data_list)
                if len(data_list) > 1:
                    std_dev = statistics.stdev(data_list)
                else:
                    std_dev = decimal.Decimal(0) # Std dev is 0 for a single sample

                # Quantize results for consistency
                avg = avg.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
                if std_dev is not None:
                    std_dev = std_dev.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

            except (statistics.StatisticsError, decimal.InvalidOperation, TypeError) as e:
                raise serializers.ValidationError({field_name: f"Error calculating statistics: {e}"})
        return avg, std_dev

    def _calculate_condition_factor_from_individuals(self, weights, lengths):
        """Calculate the average condition factor from lists of weights and lengths."""
        if not weights or not lengths or len(weights) != len(lengths):
            return None # Cannot calculate if lists are missing, empty, or mismatched

        k_factors = []
        try:
            # Ensure Decimals
            weights_decimal = [decimal.Decimal(str(w)) for w in weights]
            lengths_decimal = [decimal.Decimal(str(l)) for l in lengths]

            for w, l in zip(weights_decimal, lengths_decimal):
                if l is not None and l > 0 and w is not None:
                    k = (100 * w / (l ** 3))
                    k_factors.append(k)
                # else: skip pair if length is zero/null or weight is null

            if not k_factors:
                return None # No valid pairs to calculate K

            avg_k = statistics.mean(k_factors)
            return avg_k.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

        except (decimal.InvalidOperation, decimal.DivisionByZero, statistics.StatisticsError, TypeError) as e:
             raise serializers.ValidationError({"condition_factor": f"Error calculating condition factor: {e}"})

    def validate(self, data):
        """
        Validate input data:
        - Sample size vs assignment population.
        - Sample size vs length of individual measurement lists.
        - Consistency between individual weights and lengths lists.
        - Min/Max weight consistency.
        """
        errors = {}
        assignment = data.get('assignment', getattr(self.instance, 'assignment', None))
        sample_size = data.get('sample_size', getattr(self.instance, 'sample_size', None))
        individual_lengths = data.get('individual_lengths')
        individual_weights = data.get('individual_weights')

        # Check sample size vs assignment population
        if assignment and sample_size is not None:
            if sample_size > assignment.population_count:
                errors['sample_size'] = (
                    f"Sample size ({sample_size}) exceeds assignment "
                    f"population ({assignment.population_count})."
                )

        # Check sample size vs individual measurement lists
        if individual_lengths is not None and sample_size != len(individual_lengths):
             errors['sample_size'] = (
                 f"Sample size ({sample_size}) does not match the number "
                 f"of individual lengths provided ({len(individual_lengths)})."
             )
        if individual_weights is not None and sample_size != len(individual_weights):
            errors['sample_size'] = (
                f"Sample size ({sample_size}) does not match the number "
                f"of individual weights provided ({len(individual_weights)})."
            )

        # Check consistency between measurement lists
        if individual_lengths is not None and individual_weights is not None:
            if len(individual_lengths) != len(individual_weights):
                errors['individual_measurements'] = (
                    f"Number of individual lengths ({len(individual_lengths)}) does not match "
                    f"number of individual weights ({len(individual_weights)})."
                )

        # Check min/max weight
        min_weight = data.get('min_weight_g', getattr(self.instance, 'min_weight_g', None))
        max_weight = data.get('max_weight_g', getattr(self.instance, 'max_weight_g', None))
        if min_weight is not None and max_weight is not None:
            if min_weight > max_weight:
                errors['min_weight_g'] = "Minimum weight cannot be greater than maximum weight."

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def _process_individual_measurements(self, validated_data):
        """Calculate stats from individual lists and update validated_data."""
        individual_lengths = validated_data.pop('individual_lengths', None)
        individual_weights = validated_data.pop('individual_weights', None)

        if individual_lengths:
            avg_len, std_dev_len = self._calculate_stats(individual_lengths, 'individual_lengths')
            validated_data['avg_length_cm'] = avg_len
            validated_data['std_deviation_length'] = std_dev_len

        if individual_weights:
            avg_wgt, std_dev_wgt = self._calculate_stats(individual_weights, 'individual_weights')
            validated_data['avg_weight_g'] = avg_wgt
            validated_data['std_deviation_weight'] = std_dev_wgt

        # Calculate condition factor only if both lists were provided *in this request*
        if individual_lengths and individual_weights:
            validated_data['condition_factor'] = self._calculate_condition_factor_from_individuals(
                individual_weights, individual_lengths
            )
        # If only one list provided, let the model's save method handle K calculation later if possible
        elif individual_lengths or individual_weights:
             validated_data['condition_factor'] = None # Explicitly set to None for recalculation trigger

        return validated_data

    def create(self, validated_data):
        """
        Create a GrowthSample instance, calculating stats if individual measurements provided.
        """
        validated_data = self._process_individual_measurements(validated_data)
        # Ensure condition factor is None if not calculated, allowing model's save to try
        if 'condition_factor' not in validated_data:
             validated_data['condition_factor'] = None

        # Remove calculated fields that are read-only from direct creation input
        # (They are set above based on calculations)
        read_only_calculated = ['avg_length_cm', 'std_deviation_length', 'avg_weight_g', 'std_deviation_weight', 'condition_factor']
        creation_data = {k: v for k, v in validated_data.items() if k not in read_only_calculated or v is not None}

        # Need to re-add calculated values if they exist
        for field in read_only_calculated:
            if field in validated_data and validated_data[field] is not None:
                creation_data[field] = validated_data[field]

        return super().create(creation_data)


    def update(self, instance, validated_data):
        """
        Update a GrowthSample instance, recalculating stats if individual measurements provided.
        """
        validated_data = self._process_individual_measurements(validated_data)

        # Update instance fields directly before calling super().update
        # This ensures the model's save method (called by super().update) has the latest calculated values
        instance.avg_length_cm = validated_data.get('avg_length_cm', instance.avg_length_cm)
        instance.std_deviation_length = validated_data.get('std_deviation_length', instance.std_deviation_length)
        instance.avg_weight_g = validated_data.get('avg_weight_g', instance.avg_weight_g)
        instance.std_deviation_weight = validated_data.get('std_deviation_weight', instance.std_deviation_weight)
        instance.condition_factor = validated_data.get('condition_factor', instance.condition_factor)

        # If condition_factor was set to None by _process_individual_measurements because only one list was provided,
        # ensure it's None on the instance so the model's save method attempts recalculation.
        if 'condition_factor' in validated_data and validated_data['condition_factor'] is None:
             instance.condition_factor = None

        # Remove lists and calculated fields from validated_data passed to super(), as they are handled above
        validated_data.pop('individual_lengths', None)
        validated_data.pop('individual_weights', None)
        calculated_fields = ['avg_length_cm', 'std_deviation_length', 'avg_weight_g', 'std_deviation_weight', 'condition_factor']
        for field in calculated_fields:
             validated_data.pop(field, None)

        return super().update(instance, validated_data)
