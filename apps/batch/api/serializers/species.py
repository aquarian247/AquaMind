"""
Serializers for Species and LifeCycleStage models.

These serializers handle the conversion between JSON and Django model instances
for species and lifecycle stage data.
"""
from rest_framework import serializers
from apps.batch.models import Species, LifeCycleStage


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
