from rest_framework import serializers

from .models import (
    EnvironmentalParameter, 
    EnvironmentalReading, 
    PhotoperiodData, 
    WeatherData, 
    StageTransitionEnvironmental
)


class EnvironmentalParameterSerializer(serializers.ModelSerializer):
    """
    Serializer for environmental parameters that can be monitored.
    """
    class Meta:
        model = EnvironmentalParameter
        fields = [
            'id', 'name', 'unit', 'description', 'min_value', 'max_value',
            'optimal_min', 'optimal_max', 'created_at', 'updated_at'
        ]


class EnvironmentalReadingSerializer(serializers.ModelSerializer):
    """
    Serializer for environmental readings from sensors or manual input.
    Includes nested parameter details by default.
    """
    parameter_details = EnvironmentalParameterSerializer(source='parameter', read_only=True)
    
    class Meta:
        model = EnvironmentalReading
        fields = [
            'id', 'parameter', 'parameter_details', 'container', 'batch', 
            'sensor', 'value', 'reading_time', 'is_manual', 'recorded_by',
            'notes', 'created_at'
        ]


class EnvironmentalReadingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new environmental readings.
    Does not include nested objects for better performance during creation.
    """
    class Meta:
        model = EnvironmentalReading
        fields = [
            'id', 'parameter', 'container', 'batch', 'sensor', 'value',
            'reading_time', 'is_manual', 'recorded_by', 'notes'
        ]


class PhotoperiodDataSerializer(serializers.ModelSerializer):
    """
    Serializer for photoperiod data, which records day length for areas.
    """
    class Meta:
        model = PhotoperiodData
        fields = [
            'id', 'area', 'date', 'day_length_hours', 'light_intensity',
            'is_interpolated', 'created_at', 'updated_at'
        ]


class WeatherDataSerializer(serializers.ModelSerializer):
    """
    Serializer for weather data, which records weather conditions for areas.
    """
    class Meta:
        model = WeatherData
        fields = [
            'id', 'area', 'timestamp', 'temperature', 'wind_speed', 'wind_direction',
            'precipitation', 'wave_height', 'wave_period', 'wave_direction',
            'cloud_cover', 'created_at'
        ]


class WeatherDataCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new weather data records.
    """
    class Meta:
        model = WeatherData
        fields = [
            'id', 'area', 'timestamp', 'temperature', 'wind_speed', 'wind_direction',
            'precipitation', 'wave_height', 'wave_period', 'wave_direction', 'cloud_cover'
        ]


class StageTransitionEnvironmentalSerializer(serializers.ModelSerializer):
    """
    Serializer for environmental conditions during batch transfers.
    """
    class Meta:
        model = StageTransitionEnvironmental
        fields = [
            'id', 'batch_transfer', 'temperature', 'oxygen', 'salinity', 'ph',
            'additional_parameters', 'notes', 'created_at', 'updated_at'
        ]