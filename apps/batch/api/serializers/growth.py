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
from apps.batch.models import GrowthSample  # BatchContainerAssignment not directly used
from apps.batch.api.serializers.utils import (
    NestedModelMixin, DecimalFieldsMixin, format_decimal
)
from apps.batch.api.serializers.validation import (
    validate_individual_measurements,
    validate_sample_size_against_population,
    validate_min_max_weight
)


class GrowthSampleSerializer(
    NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer
):
    """Serializer for GrowthSample model with calculated fields."""
    assignment_details = serializers.SerializerMethodField()
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
            'updated_at', 'individual_lengths', 'individual_weights'
        ]
        read_only_fields = (
            'id',
            'assignment_details',  # Read-only representation
            'created_at',
            'updated_at'
        )
        extra_kwargs = {
            'assignment': {'required': False},  # Set via JournalEntry context
            'sample_date': {'required': False},  # From journal_entry.entry_date
            'avg_weight_g': {'required': False},  # Calc if individuals given
            'avg_length_cm': {'required': False},  # Calc if individuals given
            'std_deviation_weight': {'required': False},  # Preserve if provided
            'std_deviation_length': {'required': False},  # Preserve if provided
            'condition_factor': {'required': False}  # Calculated if possible
        }

    def get_assignment_details(self, obj):
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

        validated_data = dict(data)  # Make a mutable copy

        assignment = validated_data.get(
            'assignment', getattr(self.instance, 'assignment', None)
        )
        if not assignment:
            if not self.instance:  # Create operation
                errors['assignment'] = 'This field is required for new samples.'
            # For updates, assignment is usually fixed or not part of payload.

        measurement_errors = validate_individual_measurements(
            validated_data.get('individual_weights', []),
            validated_data.get('individual_lengths', [])
        )
        if measurement_errors:
            errors.update(measurement_errors)

        sample_size = validated_data.get('sample_size')
        if sample_size is not None and assignment:
            pop_errors = validate_sample_size_against_population(
                sample_size, assignment
            )
            if pop_errors:
                errors.update(pop_errors)

        if not validated_data.get('individual_weights'):
            min_max_errors = validate_min_max_weight(
                validated_data.get('min_weight_g'),
                validated_data.get('max_weight_g'),
                validated_data.get('avg_weight_g')
            )
            if min_max_errors:
                errors.update(min_max_errors)

        if errors:
            raise serializers.ValidationError(errors)

        # Process individual measurements after initial validation passes
        # This modifies validated_data in place with calculated stats
        if validated_data.get('individual_weights') or \
           validated_data.get('individual_lengths'):
            self._process_individual_measurements(validated_data)

        return validated_data

    def _process_individual_measurements(self, validated_data):
        """Calculate stats from individual lists and update validated_data."""
        individual_weights = validated_data.get('individual_weights', [])
        individual_lengths = validated_data.get('individual_lengths', [])

        if individual_weights or individual_lengths:
            num_weights = len(individual_weights) if individual_weights else 0
            num_lengths = len(individual_lengths) if individual_lengths else 0

            if num_weights > 0 and num_lengths > 0 and num_weights != num_lengths:
                # This should be caught by validate_individual_measurements
                pass
            elif num_weights > 0:
                validated_data['sample_size'] = num_weights
            elif num_lengths > 0:
                validated_data['sample_size'] = num_lengths

        if individual_weights:
            avg_w, std_dev_w = self._calculate_stats(
                individual_weights, 'individual_weights'
            )
            validated_data['avg_weight_g'] = avg_w
            validated_data['std_deviation_weight'] = std_dev_w
            validated_data['min_weight_g'] = (
                min(individual_weights) if individual_weights else None
            )
            validated_data['max_weight_g'] = (
                max(individual_weights) if individual_weights else None
            )

        if individual_lengths:
            avg_l, std_dev_l = self._calculate_stats(
                individual_lengths, 'individual_lengths'
            )
            validated_data['avg_length_cm'] = avg_l
            validated_data['std_deviation_length'] = std_dev_l

        if individual_weights and individual_lengths and \
           len(individual_weights) == len(individual_lengths):
            validated_data['condition_factor'] = (
                self._calculate_condition_factor_from_individuals(
                    individual_weights, individual_lengths
                )
            )
        elif individual_lengths or individual_weights:
            validated_data['condition_factor'] = None

        return validated_data

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

    def create(self, validated_data):
        """Create a new GrowthSample, processing individual measurements."""
        if 'sample_date' not in validated_data:
            journal_entry = self.context.get('journal_entry')
            if journal_entry and hasattr(journal_entry, 'entry_date'):
                entry_date = journal_entry.entry_date
                validated_data['sample_date'] = (
                    entry_date.date() if hasattr(entry_date, 'date') else entry_date
                )

        validated_data.pop('individual_weights', None)
        validated_data.pop('individual_lengths', None)

        if 'sample_date' in validated_data and \
           hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        return GrowthSample.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing GrowthSample."""
        validated_data.pop('individual_lengths', None)
        validated_data.pop('individual_weights', None)

        if 'sample_date' in validated_data and \
           hasattr(validated_data['sample_date'], 'date'):
            validated_data['sample_date'] = validated_data['sample_date'].date()

        return super().update(instance, validated_data)
