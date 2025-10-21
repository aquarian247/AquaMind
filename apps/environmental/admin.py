from django.contrib import admin
from django import forms

from .models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    WeatherData,
    StageTransitionEnvironmental
)


@admin.register(EnvironmentalParameter)
class EnvironmentalParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'min_value_display', 'max_value_display', 'optimal_min_display', 'optimal_max_display')
    list_filter = ('unit',)
    search_fields = ('name', 'description')
    
    def min_value_display(self, obj):
        return f"{float(obj.min_value):,.2f} {obj.unit}" if obj.min_value is not None else "N/A"
    min_value_display.short_description = "Min Value"
    
    def max_value_display(self, obj):
        return f"{float(obj.max_value):,.2f} {obj.unit}" if obj.max_value is not None else "N/A"
    max_value_display.short_description = "Max Value"
    
    def optimal_min_display(self, obj):
        return f"{float(obj.optimal_min):,.2f} {obj.unit}" if obj.optimal_min is not None else "N/A"
    optimal_min_display.short_description = "Optimal Min"
    
    def optimal_max_display(self, obj):
        return f"{float(obj.optimal_max):,.2f} {obj.unit}" if obj.optimal_max is not None else "N/A"
    optimal_max_display.short_description = "Optimal Max"


@admin.register(EnvironmentalReading)
class EnvironmentalReadingAdmin(admin.ModelAdmin):
    list_display = ('parameter', 'value_display', 'container', 'batch', 'sensor', 'reading_time', 'is_manual')
    list_filter = ('parameter', 'container', 'batch', 'is_manual', 'reading_time')
    search_fields = ('parameter__name', 'container__name', 'batch__name', 'notes')
    date_hierarchy = 'reading_time'
    
    def value_display(self, obj):
        return f"{float(obj.value):,.2f} {obj.parameter.unit}" if obj.value is not None else "N/A"
    value_display.short_description = "Value"


@admin.register(PhotoperiodData)
class PhotoperiodDataAdmin(admin.ModelAdmin):
    list_display = ('area', 'date', 'day_length_hours_display', 'light_intensity_display', 'is_interpolated')
    list_filter = ('area', 'date', 'is_interpolated')
    search_fields = ('area__name',)
    date_hierarchy = 'date'
    
    def day_length_hours_display(self, obj):
        return f"{float(obj.day_length_hours):,.2f} hours" if obj.day_length_hours is not None else "N/A"
    day_length_hours_display.short_description = "Day Length"
    
    def light_intensity_display(self, obj):
        return f"{float(obj.light_intensity):,.2f} lux" if obj.light_intensity is not None else "N/A"
    light_intensity_display.short_description = "Light Intensity"


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ('area', 'timestamp', 'temperature_display', 'wind_speed_display', 'precipitation_display')
    list_filter = ('area', 'timestamp')
    search_fields = ('area__name',)
    date_hierarchy = 'timestamp'
    
    def temperature_display(self, obj):
        return f"{float(obj.temperature):,.1f} °C" if obj.temperature is not None else "N/A"
    temperature_display.short_description = "Temperature"
    
    def wind_speed_display(self, obj):
        return f"{float(obj.wind_speed):,.1f} m/s" if obj.wind_speed is not None else "N/A"
    wind_speed_display.short_description = "Wind Speed"
    
    def precipitation_display(self, obj):
        return f"{float(obj.precipitation):,.1f} mm" if obj.precipitation is not None else "N/A"
    precipitation_display.short_description = "Precipitation"


@admin.register(StageTransitionEnvironmental)
class StageTransitionEnvironmentalAdmin(admin.ModelAdmin):
    list_display = ('batch_transfer_workflow', 'temperature_display', 'oxygen_display', 'salinity_display', 'ph_display')
    list_filter = ('batch_transfer_workflow__planned_start_date',)
    search_fields = ('batch_transfer_workflow__workflow_number', 'batch_transfer_workflow__batch__batch_number', 'notes')
    
    def temperature_display(self, obj):
        return f"{float(obj.temperature):,.1f} °C" if obj.temperature is not None else "N/A"
    temperature_display.short_description = "Temperature"
    
    def oxygen_display(self, obj):
        return f"{float(obj.oxygen):,.1f} mg/L" if obj.oxygen is not None else "N/A"
    oxygen_display.short_description = "Oxygen"
    
    def salinity_display(self, obj):
        return f"{float(obj.salinity):,.1f} ppt" if obj.salinity is not None else "N/A"
    salinity_display.short_description = "Salinity"
    
    def ph_display(self, obj):
        return f"{float(obj.ph):,.1f}" if obj.ph is not None else "N/A"
    ph_display.short_description = "pH"