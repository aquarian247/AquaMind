"""
Serializer for the BatchComposition model.

This serializer handles the conversion between JSON and Django model instances
for batch composition data, including validation of percentages and population counts.
"""
from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.batch.models import BatchComposition, Batch
from apps.batch.api.serializers.utils import NestedModelMixin, DecimalFieldsMixin


class BatchCompositionSerializer(
    NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer
):
    """Serializer for the BatchComposition model."""

    class NestedBatchSerializer(serializers.ModelSerializer):
        """Minimal serializer for nested Batch representation."""
        class Meta:
            model = Batch
            fields = ['id', 'batch_number', 'status']
            ref_name = 'CompositionNestedBatch'

    mixed_batch = NestedBatchSerializer(read_only=True)
    mixed_batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(), source='mixed_batch', write_only=True
    )
    source_batch = NestedBatchSerializer(read_only=True)
    source_batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(), source='source_batch', write_only=True
    )
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )

    class Meta:
        model = BatchComposition
        fields = [
            'id', 'mixed_batch', 'mixed_batch_id', 'source_batch',
            'source_batch_id', 'population_count', 'biomass_kg', 'percentage',
            'created_at'
        ]
        read_only_fields = ('created_at',)

    def validate(self, data):
        """Validate the composition data.

        Ensures:
        - Population/biomass don't exceed source batch totals.
        - Percentage is between 0 and 100.
        - At least one of population, biomass, or percentage is provided.
        """
        errors = {}
        source_batch = self._get_source_batch(data)

        # Validate required fields
        self._validate_required_fields(data, errors)

        # Validate percentage range
        if 'percentage' in data:
            self._validate_percentage(data, errors)

        # Validate population count
        if 'population_count' in data:
            self._validate_population_count(data, source_batch, errors)

        # Validate biomass
        if 'biomass_kg' in data:
            self._validate_biomass(data, source_batch, errors)

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def _get_source_batch(self, data):
        """Get the source batch from data or instance."""
        source_batch = data.get('source_batch')
        if not source_batch and self.instance:
            source_batch = self.instance.source_batch
        return source_batch

    def _validate_required_fields(self, data, errors):
        """Validate that at least one required field is provided."""
        if not any(key in data for key in ['population_count', 'biomass_kg', 'percentage']):
            errors['non_field_errors'] = (
                "At least one of population count, biomass, or percentage must be provided."
            )

    def _validate_percentage(self, data, errors):
        """Validate percentage is between 0 and 100."""
        if not (Decimal('0') <= data['percentage'] <= Decimal('100')):
            errors['percentage'] = "Percentage must be between 0 and 100."

    def _validate_population_count(self, data, source_batch, errors):
        """Validate population count against source batch."""
        if not source_batch:
            return

        try:
            pop_count = int(data['population_count'])
            if pop_count <= 0:
                errors['population_count'] = "Population count must be > 0."
                return

            source_pop = source_batch.calculated_population_count
            if source_pop is not None and pop_count > source_pop:
                msg = (
                    f"Population ({pop_count}) cannot exceed available "
                    f"({source_pop}) in source batch "
                    f"{source_batch.batch_number}."
                )
                errors['population_count'] = msg
        except (ValueError, TypeError):
            errors['population_count'] = "Population count must be an integer."

    def _validate_biomass(self, data, source_batch, errors):
        """Validate biomass against source batch."""
        if not source_batch:
            return

        try:
            biomass_kg = Decimal(data['biomass_kg'])
            if biomass_kg <= Decimal('0'):
                errors['biomass_kg'] = "Biomass must be > 0."
                return

            source_bio = source_batch.calculated_biomass_kg
            if source_bio is not None and biomass_kg > source_bio:
                msg = (
                    f"Biomass ({biomass_kg} kg) cannot exceed available "
                    f"({source_bio} kg) in source batch "
                    f"{source_batch.batch_number}."
                )
                errors['biomass_kg'] = msg
        except InvalidOperation:
            errors['biomass_kg'] = "Biomass must be a valid decimal."
