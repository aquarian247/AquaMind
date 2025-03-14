from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

from apps.infrastructure.models import Container, Area, Sensor
from apps.batch.models import Batch


class EnvironmentalParameter(models.Model):
    """
    Defines environmental parameters that can be monitored and recorded.
    Examples: temperature, oxygen, pH, salinity, etc.
    """
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum acceptable value for this parameter"
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum acceptable value for this parameter"
    )
    optimal_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum optimal value for this parameter"
    )
    optimal_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum optimal value for this parameter"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.unit})"


class EnvironmentalReading(models.Model):
    """
    Time-series data of environmental parameters recorded either by sensors or manually.
    This model is configured as a TimescaleDB hypertable for efficient time-series data handling.
    
    For TimescaleDB compatibility, we use a migration to modify the primary key constraint to include
    the partitioning column (reading_time) at the database level, allowing for proper hypertable creation.
    """
    # In Django model we keep id as primary_key, but in the migration we'll create a composite primary key
    id = models.BigAutoField(primary_key=True)
    parameter = models.ForeignKey(EnvironmentalParameter, on_delete=models.PROTECT)
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='environmental_readings')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='environmental_readings')
    sensor = models.ForeignKey(Sensor, on_delete=models.SET_NULL, null=True, blank=True, related_name='readings')
    value = models.DecimalField(max_digits=10, decimal_places=4)
    # TimescaleDB partitioning column - must be part of the primary key
    reading_time = models.DateTimeField()  
    is_manual = models.BooleanField(default=False, help_text="Whether this reading was entered manually")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # When the record was created in the system
    
    class Meta:
        indexes = [
            models.Index(fields=['container', 'parameter', 'reading_time']),
            models.Index(fields=['batch', 'parameter', 'reading_time']),
        ]
        # TimescaleDB requires the partitioning column (reading_time) to be part of the primary key
        # This is handled via a migration to maintain both Django and TimescaleDB compatibility
    
    def __str__(self):
        return f"{self.parameter.name}: {self.value} {self.parameter.unit} at {self.reading_time}"


class PhotoperiodData(models.Model):
    """
    Records photoperiod data (day length) for areas, important for fish growth and maturation.
    """
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='photoperiod_data')
    date = models.DateField()
    day_length_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Day length in hours (0-24)"
    )
    light_intensity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Light intensity in lux"
    )
    is_interpolated = models.BooleanField(
        default=False,
        help_text="Whether this data point was interpolated rather than measured"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('area', 'date')
        indexes = [
            models.Index(fields=['area', 'date']),
        ]
    
    def __str__(self):
        return f"{self.area.name}: {self.day_length_hours}h on {self.date}"


class WeatherData(models.Model):
    """
    Weather conditions by area, stored as a TimescaleDB hypertable for efficient time-series data handling.
    
    For TimescaleDB compatibility, we use a migration to modify the primary key constraint to include
    the partitioning column (timestamp) at the database level, allowing for proper hypertable creation.
    """
    # In Django model we keep id as primary_key, but in the migration we'll create a composite primary key
    id = models.BigAutoField(primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='weather_data')
    # TimescaleDB partitioning column - must be part of the primary key
    timestamp = models.DateTimeField()  
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Air temperature in °C")
    wind_speed = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Wind speed in m/s")
    wind_direction = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Wind direction in degrees (0-360)"
    )
    precipitation = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Precipitation in mm")
    wave_height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Wave height in meters")
    wave_period = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Wave period in seconds")
    wave_direction = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Wave direction in degrees (0-360)"
    )
    cloud_cover = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Cloud cover percentage (0-100)"
    )
    created_at = models.DateTimeField(auto_now_add=True)  # When the record was created in the system
    
    class Meta:
        indexes = [
            models.Index(fields=['area', 'timestamp']),
        ]
        # TimescaleDB requires the partitioning column (timestamp) to be part of the primary key
        # This is handled via a migration to maintain both Django and TimescaleDB compatibility
    
    def __str__(self):
        return f"Weather for {self.area.name} at {self.timestamp}"


class StageTransitionEnvironmental(models.Model):
    """
    Records environmental conditions during stage transitions of batches.
    Links to batch transfers to record conditions when fish are moved.
    """
    batch_transfer = models.OneToOneField('batch.BatchTransfer', on_delete=models.CASCADE, related_name='environmental_conditions')
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Water temperature in °C")
    oxygen = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Dissolved oxygen in mg/L")
    salinity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Salinity in ppt")
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="pH level")
    additional_parameters = models.JSONField(null=True, blank=True, help_text="Additional environmental parameters")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Environmental conditions for transfer {self.batch_transfer.id} at {self.batch_transfer.transfer_date}"