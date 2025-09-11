"""
Sensor model for the infrastructure app.

This module defines the Sensor model, which represents sensors installed in
containers for monitoring environmental conditions.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from apps.infrastructure.models.container import Container


class Sensor(models.Model):
    """
    Sensors installed in containers for monitoring environmental conditions.
    """
    SENSOR_TYPES = [
        ('TEMPERATURE', 'Temperature'),
        ('OXYGEN', 'Oxygen'),
        ('PH', 'pH'),
        ('SALINITY', 'Salinity'),
        ('CO2', 'CO2'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPES)
    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name='sensors')
    serial_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    last_calibration_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.get_sensor_type_display()} in {self.container.name})"
