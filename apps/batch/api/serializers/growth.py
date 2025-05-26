"""
Serializer for the GrowthSample model.

This serializer handles the conversion between JSON and Django model instances
for growth sample data, including calculation of statistics from individual measurements.
"""
import statistics
import decimal
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from apps.batch.models import GrowthSample, BatchContainerAssignment
from apps.batch.api.serializers.utils import NestedModelMixin, DecimalFieldsMixin, format_decimal
from apps.batch.api.serializers.validation import (
    validate_individual_measurements,
    validate_sample_size_against_population,
    validate_min_max_weight
)


class GrowthSampleSerializer(NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer):
    """Serializer for GrowthSample model with calculated fields."""
    assignment_details = serializers.SerializerMethodField()
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
    
    def get_assignment_details(self, obj):
        """Get detailed information about the batch container assignment."""
        if not obj.assignment:
            return None
            
        assignment = obj.assignment
        
        # Use nested_info for batch, container, and lifecycle_stage
        batch_info = self.get_nested_info(assignment, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number',
            'species_name': 'species.name'
        })
        
        container_info = self.get_nested_info(assignment, 'container', {
            'id': 'id',
            'name': 'name'
        })
        
        lifecycle_stage_info = self.get_nested_info(assignment, 'lifecycle_stage', {
            'id': 'id',
            'name': 'name'
        })
        
        return {
            'id': assignment.id,
            'batch': batch_info,
            'container': container_info,
            'lifecycle_stage': lifecycle_stage_info,
            'population_count': assignment.population_count,
            'assignment_date': assignment.assignment_date
        }

    def validate(self, data):
        """Custom validation to ensure sample_size matches individual lists if provided."""
        # Run standard field validation and parent validation first
        data = super().validate(data)
        errors = {}
        
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
                errors['sample_date'] = 'This field is required when creating a GrowthSample.'

        # --- Validate individual measurements ---
        # Get individual measurements from initial_data if available
        if hasattr(self, 'initial_data'):
            initial_lengths = self.initial_data.get('individual_lengths', [])
            initial_weights = self.initial_data.get('individual_weights', [])
            sample_size_for_check = data.get('sample_size', self.initial_data.get('sample_size'))
        else:
            initial_lengths = []
            initial_weights = []
            sample_size_for_check = data.get('sample_size')

        # Validate individual measurements
        measurement_errors = validate_individual_measurements(
            sample_size_for_check, 
            initial_lengths, 
            initial_weights
        )
        if measurement_errors:
            errors.update(measurement_errors)

        # --- Validate sample size against assignment population ---
        sample_size = data.get('sample_size')  # Use validated sample_size now
        assignment = data.get('assignment')

        # If assignment is not in data (e.g., partial update), try getting it from the instance
        if assignment is None and self.instance:
            assignment = self.instance.assignment

        # Check sample_size against population_count
        if assignment is not None and sample_size is not None:
            population_error = validate_sample_size_against_population(sample_size, assignment)
            if population_error:
                errors['sample_size'] = population_error

        # --- Validate min/max weight ---
        min_weight = data.get('min_weight_g')
        max_weight = data.get('max_weight_g')
        weight_error = validate_min_max_weight(min_weight, max_weight)
        if weight_error:
            errors['min_weight_g'] = weight_error

        # Raise all collected errors
        if errors:
            raise serializers.ValidationError(errors)

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
            # Format with consistent decimal places
            return Decimal(format_decimal(avg)), Decimal(format_decimal(std_dev))
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
        
        # Remove individual measurements from serializer data
        validated_data.pop('individual_weights', [])
        validated_data.pop('individual_lengths', [])
        
        # Ensure sample_date is a date, not a datetime
        if 'sample_date' in validated_data and hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        return GrowthSample.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Handle individual measurements - extract from validated_data
        validated_data.pop('individual_lengths', None)
        validated_data.pop('individual_weights', None)
        
        # Ensure sample_date is a date, not a datetime (extra safety check)
        if 'sample_date' in validated_data and hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()
            
        # Perform the update using the standard method
        return super().update(instance, validated_data)
