"""
Serializers for the environmental app.

These serializers convert Django models to JSON and vice versa for the REST API.
Includes special handling for TimescaleDB hypertable models.
"""
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers
from apps.batch.models import Batch, BatchTransfer
from apps.environmental.models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    StageTransitionEnvironmental,
    WeatherData,
)
from apps.infrastructure.models import Area, Container, Sensor

class EnvironmentalParameterSerializer(serializers.ModelSerializer):
    """Serializer for the EnvironmentalParameter model.
    
    Handles environmental parameters that define acceptable ranges for various
    water quality and environmental metrics in aquaculture operations.
    """
    
    name = serializers.CharField(
        help_text="Name of the environmental parameter (e.g., 'Dissolved Oxygen', 'Temperature')."
    )
    unit = serializers.CharField(
        help_text="Unit of measurement for this parameter (e.g., 'mg/L', '°C')."
    )
    description = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Detailed description of the parameter and its importance in aquaculture."
    )
    min_value = serializers.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        required=False, 
        allow_null=True,
        help_text="Minimum acceptable value for this parameter. Values below this trigger alerts."
    )
    max_value = serializers.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        required=False, 
        allow_null=True,
        help_text="Maximum acceptable value for this parameter. Values above this trigger alerts."
    )
    optimal_min = serializers.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        required=False, 
        allow_null=True,
        help_text="Minimum optimal value for this parameter. Values in the optimal range are ideal for fish health."
    )
    optimal_max = serializers.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        required=False, 
        allow_null=True,
        help_text="Maximum optimal value for this parameter. Values in the optimal range are ideal for fish health."
    )

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
    This serializer manages time-series environmental readings from sensors and manual measurements.
    """
    parameter_name = serializers.StringRelatedField(
        source='parameter', 
        read_only=True,
        help_text="Name of the environmental parameter being measured."
    )
    container_name = serializers.StringRelatedField(
        source='container', 
        read_only=True,
        help_text="Name of the container where the reading was taken."
    )
    batch_name = serializers.StringRelatedField(
        source='batch', 
        read_only=True,
        help_text="Name/number of the batch associated with this reading."
    )
    sensor_name = serializers.StringRelatedField(
        source='sensor', 
        read_only=True,
        help_text="Name of the sensor that recorded this reading, if applicable."
    )
    
    # Additional fields with help_text
    parameter = serializers.PrimaryKeyRelatedField(
        queryset=EnvironmentalParameter.objects.all(),
        help_text="The environmental parameter being measured (references EnvironmentalParameter model)."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        help_text="The container where the reading was taken."
    )
    batch = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(),
        required=False,
        allow_null=True,
        help_text="Optional batch associated with this reading."
    )
    sensor = serializers.PrimaryKeyRelatedField(
        queryset=Sensor.objects.all(),
        required=False,
        allow_null=True,
        help_text="Optional sensor that recorded this reading. Required if is_manual is False."
    )
    reading_time = serializers.DateTimeField(
        help_text="Timestamp when the reading was taken. Used as the time dimension in TimescaleDB."
    )
    value = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="The measured value of the parameter."
    )
    is_manual = serializers.BooleanField(
        default=False,
        help_text="Whether this reading was taken manually (true) or by an automated sensor (false)."
    )
    
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
    """Serializer for the PhotoperiodData model.
    
    Handles photoperiod (day/night cycle) data for different areas,
    which is important for managing fish growth and maturation.
    """
    
    area_name = serializers.StringRelatedField(
        source='area', 
        read_only=True,
        help_text="Name of the area where this photoperiod data applies."
    )
    
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        help_text="The area where this photoperiod data applies."
    )
    
    date = serializers.DateField(
        help_text="Date for which this photoperiod data is recorded."
    )
    
    day_length_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('24'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('24'))],
        help_text="Natural day length in hours (0-24)."
    )
    
    artificial_light_start = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="Time when artificial lighting starts, if used."
    )
    
    artificial_light_end = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="Time when artificial lighting ends, if used."
    )
    
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Additional notes about the photoperiod conditions."
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
    Manages weather data recordings that may affect aquaculture operations.
    """
    area_name = serializers.StringRelatedField(
        source='area', 
        read_only=True,
        help_text="Name of the area where this weather data was recorded."
    )
    
    # Additional fields with help_text
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        help_text="The area where this weather data was recorded."
    )
    
    timestamp = serializers.DateTimeField(
        help_text="Timestamp when the weather data was recorded. Used as the time dimension in TimescaleDB."
    )
    
    temperature = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Air temperature in degrees Celsius."
    )
    
    wind_speed = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Wind speed in meters per second."
    )
    
    wind_direction = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Wind direction in degrees (0-360, where 0/360 is North)."
    )
    
    precipitation = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precipitation amount in millimeters."
    )
    
    wave_height = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Wave height in meters."
    )
    
    wave_direction = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Wave direction in degrees (0-360, where 0/360 is North)."
    )
    
    cloud_cover = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Cloud cover percentage (0-100)."
    )
    
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
    """Serializer for the StageTransitionEnvironmental model.
    
    Records environmental conditions during batch transfers between lifecycle stages,
    which is critical for tracking environmental factors during transitions.
    """
    
    batch_transfer_id = serializers.ReadOnlyField(
        source='batch_transfer.id',
        help_text="ID of the batch transfer this environmental record is associated with."
    )
    
    # Additional fields with help_text
    batch_transfer = serializers.PrimaryKeyRelatedField(
        queryset=BatchTransfer.objects.all(),
        help_text="The batch transfer this environmental record is associated with."
    )
    
    temperature = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Water temperature in degrees Celsius during the transfer."
    )
    
    oxygen = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Dissolved oxygen level in mg/L during the transfer."
    )
    
    ph = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        required=False,
        allow_null=True,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="pH level (0-14) during the transfer."
    )
    
    salinity = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Salinity level in ppt (parts per thousand) during the transfer."
    )
    
    notes = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Additional notes about environmental conditions during the transfer."
    )
    
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
