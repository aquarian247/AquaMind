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


class BatchCompositionSerializer(NestedModelMixin, DecimalFieldsMixin, serializers.ModelSerializer):
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
