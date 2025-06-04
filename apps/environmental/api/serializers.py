"""
Serializers for the environmental app.

These serializers convert Django models to JSON and vice versa for the REST API.
Includes special handling for TimescaleDB hypertable models.
"""
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from apps.environmental.models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    WeatherData,
    StageTransitionEnvironmental
)


class EnvironmentalParameterSerializer(serializers.ModelSerializer):
    """Serializer for the EnvironmentalParameter model."""
    
    min_value = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)
    max_value = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)
    optimal_min = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)
    optimal_max = serializers.DecimalField(max_digits=10, decimal_places=4, required=False, allow_null=True)

    class Meta:
        model = EnvironmentalParameter
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """Validate min/max value relationships."""
        min_value = data.get('min_value')
        max_value = data.get('max_value')
        optimal_min = data.get('optimal_min')
        optimal_max = data.get('optimal_max')
        
        # Validate min/max values if both are provided
        if min_value is not None and max_value is not None:
            if min_value > max_value:
                raise serializers.ValidationError(
                    {"min_value": "Minimum value cannot be greater than maximum value."}
                )
        
        # Validate optimal ranges if both are provided
        if optimal_min is not None and optimal_max is not None:
            if optimal_min > optimal_max:
                raise serializers.ValidationError(
                    {"optimal_min": "Minimum optimal value cannot be greater than maximum optimal value."}
                )
        
        # Validate optimal range is within min/max range if all values are provided
        if (min_value is not None and max_value is not None and 
            optimal_min is not None and optimal_max is not None):
            if optimal_min < min_value or optimal_max > max_value:
                raise serializers.ValidationError(
                    {"optimal_range": "Optimal range must be within the min/max range."}
                )
        
        return data


class EnvironmentalReadingSerializer(serializers.ModelSerializer):
    """
    Serializer for the EnvironmentalReading model.
    
    Handles TimescaleDB hypertable data with special attention to the time column.
    """
    parameter_name = serializers.StringRelatedField(source='parameter', read_only=True)
    container_name = serializers.StringRelatedField(source='container', read_only=True)
    batch_name = serializers.StringRelatedField(source='batch', read_only=True)
    sensor_name = serializers.StringRelatedField(source='sensor', read_only=True)
    
    class Meta:
        model = EnvironmentalReading
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def validate(self, data):
        """
        Validate environmental reading values against parameter bounds.
        
        Checks if the reading value is within the acceptable range defined
        by the associated environmental parameter.
        """
        parameter = data.get('parameter')
        value = data.get('value')
        
        if parameter and value:
            # Check if value is within min/max bounds if they are defined
            if parameter.min_value is not None and value < parameter.min_value:
                raise serializers.ValidationError({
                    "value": f"Value cannot be less than the parameter minimum ({parameter.min_value})."
                })
            
            if parameter.max_value is not None and value > parameter.max_value:
                raise serializers.ValidationError({
                    "value": f"Value cannot be greater than the parameter maximum ({parameter.max_value})."
                })
        
        return data


class PhotoperiodDataSerializer(serializers.ModelSerializer):
    """Serializer for the PhotoperiodData model."""
    
    area_name = serializers.StringRelatedField(source='area', read_only=True)
    
    day_length_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('24'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('24'))],
        help_text="Day length in hours (0-24)"
    )

    class Meta:
        model = PhotoperiodData
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_day_length_hours(self, value):
        """Validate that day length is between 0 and 24 hours."""
        if value < 0 or value > 24:
            raise serializers.ValidationError("Day length must be between 0 and 24 hours.")
        return value


class WeatherDataSerializer(serializers.ModelSerializer):
    """
    Serializer for the WeatherData model.
    
    Handles TimescaleDB hypertable data with special attention to the time column.
    """
    area_name = serializers.StringRelatedField(source='area', read_only=True)
    
    class Meta:
        model = WeatherData
        fields = '__all__'
        read_only_fields = ('created_at',)
    
    def validate(self, data):
        """Validate weather data values."""
        # Validate wind_direction if provided
        wind_direction = data.get('wind_direction')
        if wind_direction is not None and (wind_direction < 0 or wind_direction > 360):
            raise serializers.ValidationError(
                {"wind_direction": "Wind direction must be between 0 and 360 degrees."}
            )
        
        # Validate wave_direction if provided
        wave_direction = data.get('wave_direction')
        if wave_direction is not None and (wave_direction < 0 or wave_direction > 360):
            raise serializers.ValidationError(
                {"wave_direction": "Wave direction must be between 0 and 360 degrees."}
            )
        
        # Validate cloud_cover if provided
        cloud_cover = data.get('cloud_cover')
        if cloud_cover is not None and (cloud_cover < 0 or cloud_cover > 100):
            raise serializers.ValidationError(
                {"cloud_cover": "Cloud cover must be between 0 and 100 percent."}
            )
        
        return data


class StageTransitionEnvironmentalSerializer(serializers.ModelSerializer):
    """Serializer for the StageTransitionEnvironmental model."""
    
    batch_transfer_id = serializers.ReadOnlyField(source='batch_transfer.id')
    
    class Meta:
        model = StageTransitionEnvironmental
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """Validate environmental values."""
        # Validate temperature if provided
        temperature = data.get('temperature')
        if temperature is not None and temperature < 0:
            raise serializers.ValidationError(
                {"temperature": "Temperature cannot be negative."}
            )
        
        # Validate oxygen if provided
        oxygen = data.get('oxygen')
        if oxygen is not None and oxygen < 0:
            raise serializers.ValidationError(
                {"oxygen": "Oxygen level cannot be negative."}
            )
        
        # Validate pH if provided
        ph = data.get('ph')
        if ph is not None and (ph < 0 or ph > 14):
            raise serializers.ValidationError(
                {"ph": "pH must be between 0 and 14."}
            )
        
        # Validate salinity if provided
        salinity = data.get('salinity')
        if salinity is not None and salinity < 0:
            raise serializers.ValidationError(
                {"salinity": "Salinity cannot be negative."}
            )
        
        return data
