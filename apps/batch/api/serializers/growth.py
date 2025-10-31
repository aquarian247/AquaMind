"""
Serializer for the GrowthSample model.

This serializer handles the conversion between JSON and Django model instances
for growth sample data, including calculation of statistics from individual
measurements.
"""
import statistics
import decimal
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from django.db import transaction
from apps.batch.models import GrowthSample, IndividualGrowthObservation
from typing import Dict, Any, Optional
from apps.batch.api.serializers.utils import (
    NestedModelMixin, DecimalFieldsMixin, format_decimal
)
from apps.batch.api.serializers.validation import (
    validate_individual_measurements,
    validate_sample_size_against_population,
    validate_min_max_weight
)
from drf_spectacular.utils import extend_schema_field, extend_schema


class IndividualGrowthObservationInputSerializer(serializers.Serializer):
    """Input serializer for nested growth observations."""
    fish_identifier = serializers.CharField(max_length=50)
    weight_g = serializers.DecimalField(max_digits=10, decimal_places=2)
    length_cm = serializers.DecimalField(max_digits=10, decimal_places=2)


class IndividualGrowthObservationSerializer(serializers.ModelSerializer):
    """Serializer for displaying growth observations."""
    calculated_k_factor = serializers.SerializerMethodField()
    
    class Meta:
        model = IndividualGrowthObservation
        fields = ['id', 'fish_identifier', 'weight_g', 'length_cm', 'calculated_k_factor']
    
    def get_calculated_k_factor(self, obj):
        """Calculate K-factor if weight and length are provided."""
        if obj.weight_g and obj.length_cm and obj.length_cm > 0:
            return (obj.weight_g / (obj.length_cm ** 3)) * 100
        return None


class GrowthSampleSerializer(
    NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer
):
    """Serializer for GrowthSample model with calculated fields."""
    assignment_details = serializers.SerializerMethodField()
    
    # Legacy individual measurement lists (kept for backward compatibility)
    individual_lengths = serializers.ListField(
        child=serializers.DecimalField(
            max_digits=10, decimal_places=2, min_value=Decimal('0.01')
        ),
        write_only=True, required=False, allow_empty=True, max_length=1000
    )
    individual_weights = serializers.ListField(
        child=serializers.DecimalField(
            max_digits=10, decimal_places=2, min_value=Decimal('0.01')
        ),
        write_only=True, required=False, allow_empty=True, max_length=1000
    )
    
    # New nested observation handling
    individual_observations = IndividualGrowthObservationInputSerializer(
        many=True,
        required=False,
        write_only=True,
        help_text="Individual fish observations to create (write-only, for POST/PUT)."
    )
    
    # Read-only for displaying nested observations
    fish_observations = IndividualGrowthObservationSerializer(
        source='individual_observations',
        many=True,
        read_only=True,
        help_text="Individual fish observations with K-factors (read-only, for GET)."
    )

    # Override sample_date to explicitly handle date conversion
    # Mark as not required since we'll set it from journal_entry if needed
    sample_date = serializers.DateField(required=False)

    class Meta:
        model = GrowthSample
        fields = [
            'id', 'assignment', 'assignment_details', 'sample_date',
            'sample_size', 'avg_weight_g', 'avg_length_cm',
            'std_deviation_weight', 'std_deviation_length', 'min_weight_g',
            'max_weight_g', 'condition_factor', 'notes', 'created_at',
            'updated_at', 'individual_lengths', 'individual_weights',
            'individual_observations',  # write-only field for creating nested objects
            'fish_observations',  # read-only field for displaying nested objects
        ]
        read_only_fields = (
            'id',
            'assignment_details',  # Read-only representation
            'created_at',
            'updated_at',
            'fish_observations',  # Read-only nested observations
        )
        extra_kwargs = {
            'assignment': {'required': False},  # Set via JournalEntry context
            'sample_date': {'required': False},  # From journal_entry.entry_date
            'sample_size': {'required': False},  # Calc from individuals or manual
            'avg_weight_g': {'required': False},  # Calc if individuals given
            'avg_length_cm': {'required': False},  # Calc if individuals given
            'std_deviation_weight': {'required': False},  # Preserve if provided
            'std_deviation_length': {'required': False},  # Preserve if provided
            'condition_factor': {'required': False}  # Calculated if possible
        }

    def get_assignment_details(self, obj) -> Optional[Dict[str, Any]]:
        """Get detailed information about the batch container assignment."""
        if not obj.assignment:
            return None

        assignment = obj.assignment

        batch_info = self.get_nested_info(assignment, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number',
            'species_name': 'species.name'
        })

        container_info = self.get_nested_info(assignment, 'container', {
            'id': 'id',
            'name': 'name'
        })

        lifecycle_stage_info = self.get_nested_info(
            assignment, 'lifecycle_stage', {
                'id': 'id',
                'name': 'name'
            }
        )

        return {
            'id': assignment.id,
            'batch': batch_info,
            'container': container_info,
            'lifecycle_stage': lifecycle_stage_info,
            'population_count': assignment.population_count,
            'assignment_date': assignment.assignment_date
        }

    def validate(self, data):
        """Validate sample data, including individual measurements."""
        errors = {}

        try:
            validated_data = dict(data)  # Make a mutable copy

            assignment = validated_data.get(
                'assignment', getattr(self.instance, 'assignment', None)
            )
            if not assignment:
                if not self.instance:  # Create operation
                    errors['assignment'] = 'This field is required for new samples.'
                # For updates, assignment is usually fixed or not part of payload.
        except Exception as e:
            errors['general'] = f'Error processing request data: {str(e)}'
            return errors

        try:
            validate_individual_measurements(
                validated_data.get('sample_size'),
                validated_data.get('individual_lengths', []),
                validated_data.get('individual_weights', [])
            )
        except serializers.ValidationError as e:
            errors.update(e.detail)
        except Exception as e:
            errors['individual_measurements'] = f'Error validating individual measurements: {str(e)}'

        sample_size = validated_data.get('sample_size')
        if sample_size is not None and assignment:
            try:
                pop_errors = validate_sample_size_against_population(
                    sample_size, assignment
                )
                if pop_errors:
                    errors['sample_size'] = pop_errors
            except Exception as e:
                # Handle any unexpected errors in population validation
                errors['sample_size'] = f"Error validating sample size: {str(e)}"

        if not validated_data.get('individual_weights'):
            try:
                validate_min_max_weight(
                    validated_data.get('min_weight_g'),
                    validated_data.get('max_weight_g')
                )
            except serializers.ValidationError as e:
                errors.update(e.detail)
            except Exception as e:
                errors['weight_validation'] = f'Error validating weight ranges: {str(e)}'

        if errors:
            raise serializers.ValidationError(errors)

        # Process individual measurements after initial validation passes
        # This modifies validated_data in place with calculated stats
        try:
            if validated_data.get('individual_weights') or \
               validated_data.get('individual_lengths'):
                self._process_individual_measurements(validated_data)
        except Exception as e:
            errors['measurement_processing'] = f'Error processing individual measurements: {str(e)}'
            raise serializers.ValidationError(errors)

        return validated_data

    def _process_individual_measurements(self, validated_data):
        """Calculate stats from individual lists and update validated_data."""
        try:
            individual_weights = validated_data.get('individual_weights', [])
            individual_lengths = validated_data.get('individual_lengths', [])

            # Early return if no measurements provided
            if not individual_weights and not individual_lengths:
                return validated_data

            # Set sample size from measurements
            self._set_sample_size_from_measurements(validated_data, individual_weights, individual_lengths)

            # Process weight statistics
            if individual_weights:
                self._process_weight_statistics(validated_data, individual_weights)

            # Process length statistics
            if individual_lengths:
                self._process_length_statistics(validated_data, individual_lengths)

            # Process condition factor if both measurements available
            self._process_condition_factor(validated_data, individual_weights, individual_lengths)

        except serializers.ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise serializers.ValidationError({'measurement_processing': f'Unexpected error processing measurements: {str(e)}'})

        return validated_data

    def _set_sample_size_from_measurements(self, validated_data, weights, lengths):
        """Set sample size based on available measurements."""
        num_weights = len(weights) if weights else 0
        num_lengths = len(lengths) if lengths else 0

        if num_weights > 0 and num_lengths > 0 and num_weights != num_lengths:
            # This should be caught by validate_individual_measurements
            return
        elif num_weights > 0:
            validated_data['sample_size'] = num_weights
        elif num_lengths > 0:
            validated_data['sample_size'] = num_lengths

    def _process_weight_statistics(self, validated_data, individual_weights):
        """Process weight statistics and update validated_data."""
        try:
            avg_w, std_dev_w = self._calculate_stats(individual_weights, 'individual_weights')
            validated_data['avg_weight_g'] = avg_w
            validated_data['std_deviation_weight'] = std_dev_w
            validated_data['min_weight_g'] = min(individual_weights) if individual_weights else None
            validated_data['max_weight_g'] = max(individual_weights) if individual_weights else None
        except Exception as e:
            raise serializers.ValidationError({'individual_weights': f'Error calculating weight statistics: {str(e)}'})

    def _process_length_statistics(self, validated_data, individual_lengths):
        """Process length statistics and update validated_data."""
        try:
            avg_l, std_dev_l = self._calculate_stats(individual_lengths, 'individual_lengths')
            validated_data['avg_length_cm'] = avg_l
            validated_data['std_deviation_length'] = std_dev_l
        except Exception as e:
            raise serializers.ValidationError({'individual_lengths': f'Error calculating length statistics: {str(e)}'})

    def _process_condition_factor(self, validated_data, individual_weights, individual_lengths):
        """Process condition factor and update validated_data."""
        if (individual_weights and individual_lengths and
            len(individual_weights) == len(individual_lengths)):
            try:
                validated_data['condition_factor'] = (
                    self._calculate_condition_factor_from_individuals(
                        individual_weights, individual_lengths
                    )
                )
            except Exception as e:
                raise serializers.ValidationError({'condition_factor': f'Error calculating condition factor: {str(e)}'})
        elif individual_lengths or individual_weights:
            validated_data['condition_factor'] = None

    def _calculate_stats(self, numeric_data, field_name):
        """Calculate mean and std deviation for a list of numbers."""
        if not numeric_data:
            return None, None
        try:
            avg = statistics.mean(numeric_data)
            std_dev = (statistics.stdev(numeric_data)
                       if len(numeric_data) > 1 else Decimal('0.0'))
            return Decimal(format_decimal(avg)), Decimal(format_decimal(std_dev))
        except (ValueError, TypeError, InvalidOperation, statistics.StatisticsError):
            msg = f"Invalid numeric data for {field_name} statistics calculation."
            raise serializers.ValidationError({field_name: msg})

    def _calculate_condition_factor_from_individuals(self, weights, lengths):
        """Calculate K-factor from lists of weights (g) and lengths (cm)."""
        if not weights or not lengths or len(weights) != len(lengths):
            return None

        try:
            k_factors = []
            for w, l_val in zip(weights, lengths):
                if not isinstance(w, Decimal) or not isinstance(l_val, Decimal):
                    raise TypeError("Weights and lengths must be Decimal objects.")
                if l_val <= Decimal('0'):
                    continue  # Skip fish with zero or negative length
                k = (Decimal('100') * w) / (l_val ** 3)
                k_factors.append(k)

            if not k_factors:
                return None
            avg_k = statistics.mean(k_factors)
            return avg_k.quantize(Decimal('0.01'))
        except (ValueError, TypeError, InvalidOperation, statistics.StatisticsError):
            msg = "Invalid numeric data for K factor calculation."
            raise serializers.ValidationError({'individual_measurements': msg})

    @transaction.atomic
    def create(self, validated_data):
        """Create a new GrowthSample, processing individual measurements or observations."""
        if 'sample_date' not in validated_data:
            journal_entry = self.context.get('journal_entry')
            if journal_entry and hasattr(journal_entry, 'entry_date'):
                entry_date = journal_entry.entry_date
                validated_data['sample_date'] = (
                    entry_date.date() if hasattr(entry_date, 'date') else entry_date
                )

        # Extract nested individual observations
        individual_observations_data = validated_data.pop('individual_observations', [])
        
        # Legacy individual measurements (for backward compatibility)
        validated_data.pop('individual_weights', None)
        validated_data.pop('individual_lengths', None)

        if 'sample_date' in validated_data and \
           hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        # If creating with individual observations, set temporary sample_size
        # (will be recalculated by calculate_aggregates)
        if individual_observations_data and 'sample_size' not in validated_data:
            validated_data['sample_size'] = 0
            validated_data['avg_weight_g'] = Decimal('0.0')

        # Create the growth sample
        growth_sample = GrowthSample.objects.create(**validated_data)
        
        # Create individual observations if provided
        if individual_observations_data:
            for obs_data in individual_observations_data:
                IndividualGrowthObservation.objects.create(
                    growth_sample=growth_sample,
                    **obs_data
                )
            
            # Calculate aggregates from individual observations
            growth_sample.calculate_aggregates()
        
        return growth_sample

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an existing GrowthSample with nested individual observations."""
        # Extract nested individual observations
        individual_observations_data = validated_data.pop('individual_observations', None)
        
        # Legacy individual measurements (for backward compatibility)
        validated_data.pop('individual_lengths', None)
        validated_data.pop('individual_weights', None)

        if 'sample_date' in validated_data and \
           hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        # Update the growth sample fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update individual observations if provided
        if individual_observations_data is not None:
            # Replace strategy: Clear all existing observations and create new ones
            instance.individual_observations.all().delete()
            
            # Create new observations with the updated data
            for obs_data in individual_observations_data:
                IndividualGrowthObservation.objects.create(
                    growth_sample=instance,
                    **obs_data
                )
            
            # Recalculate aggregates from individual observations
            instance.calculate_aggregates()
        
        return instance
