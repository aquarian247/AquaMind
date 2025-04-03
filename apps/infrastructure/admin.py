from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .models import (
    Geography, 
    Area, 
    FreshwaterStation, 
    Hall, 
    ContainerType, 
    Container, 
    Sensor, 
    FeedContainer
)


@admin.register(Geography)
class GeographyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


class AreaAdminForm(forms.ModelForm):
    """Custom form for Area admin with map widget for coordinates."""
    
    class Meta:
        model = Area
        fields = '__all__'
    
    class Media:
        css = {
            'all': ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',)
        }
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'admin/js/leaflet_map_picker.js',
        )

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    form = AreaAdminForm
    list_display = ('name', 'geography', 'latitude_display', 'longitude_display', 'max_biomass_display', 'active')
    
    def latitude_display(self, obj):
        return f"{float(obj.latitude):.6f}" if obj.latitude is not None else "N/A"
    latitude_display.short_description = "Latitude"
    
    def longitude_display(self, obj):
        return f"{float(obj.longitude):.6f}" if obj.longitude is not None else "N/A"
    longitude_display.short_description = "Longitude"
    
    def max_biomass_display(self, obj):
        return f"{float(obj.max_biomass):,.2f} kg" if obj.max_biomass is not None else "N/A"
    max_biomass_display.short_description = "Max Biomass (kg)"
    list_filter = ('geography', 'active')
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'geography', 'max_biomass', 'active')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'description': format_html(
                '<div id="map-selector-container" data-lat-field="id_latitude" data-lng-field="id_longitude">' 
                '<p>Click on the map to set the location</p>'
                '<div id="location-map" style="width: 100%; height: 400px;"></div>'
                '</div>'
            )
        }),
    )


class FreshwaterStationAdminForm(forms.ModelForm):
    """Custom form for FreshwaterStation admin with map widget for coordinates."""
    
    class Meta:
        model = FreshwaterStation
        fields = '__all__'
    
    class Media:
        css = {
            'all': ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',)
        }
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'admin/js/leaflet_map_picker.js',
        )

@admin.register(FreshwaterStation)
class FreshwaterStationAdmin(admin.ModelAdmin):
    form = FreshwaterStationAdminForm
    list_display = ('name', 'station_type', 'geography', 'latitude_display', 'longitude_display', 'active')
    
    def latitude_display(self, obj):
        return f"{float(obj.latitude):.6f}" if obj.latitude is not None else "N/A"
    latitude_display.short_description = "Latitude"
    
    def longitude_display(self, obj):
        return f"{float(obj.longitude):.6f}" if obj.longitude is not None else "N/A"
    longitude_display.short_description = "Longitude"
    list_filter = ('station_type', 'geography', 'active')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'station_type', 'geography', 'description', 'active')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'description': format_html(
                '<div id="map-selector-container" data-lat-field="id_latitude" data-lng-field="id_longitude">' 
                '<p>Click on the map to set the location</p>'
                '<div id="location-map" style="width: 100%; height: 400px;"></div>'
                '</div>'
            )
        }),
    )


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'freshwater_station', 'area_sqm_display', 'active')
    
    def area_sqm_display(self, obj):
        return format_html("{:.2f} m<sup>2</sup>", float(obj.area_sqm)) if obj.area_sqm is not None else "N/A"
    area_sqm_display.short_description = format_html("Area (m<sup>2</sup>)")
    list_filter = ('freshwater_station', 'active')
    search_fields = ('name', 'description')


@admin.register(ContainerType)
class ContainerTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'max_volume_m3_display')
    
    def max_volume_m3_display(self, obj):
        return format_html("{:.2f} m<sup>3</sup>", float(obj.max_volume_m3)) if obj.max_volume_m3 is not None else "N/A"
    max_volume_m3_display.short_description = format_html("Max Volume (m<sup>3</sup>)")
    list_filter = ('category',)
    search_fields = ('name', 'description')


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'container_type', 'get_location', 'volume_m3_display', 'max_biomass_kg_display', 'active')
    
    def volume_m3_display(self, obj):
        return format_html("{:.2f} m<sup>3</sup>", float(obj.volume_m3)) if obj.volume_m3 is not None else "N/A"
    volume_m3_display.short_description = format_html("Volume (m<sup>3</sup>)")
    
    def max_biomass_kg_display(self, obj):
        return f"{float(obj.max_biomass_kg):,.2f} kg" if obj.max_biomass_kg is not None else "N/A"
    max_biomass_kg_display.short_description = "Max Biomass (kg)"
    list_filter = ('container_type', 'active')
    search_fields = ('name',)
    
    def get_location(self, obj):
        return obj.hall.name if obj.hall else obj.area.name
    get_location.short_description = 'Location'


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'sensor_type', 'container', 'installation_date', 'active')
    list_filter = ('sensor_type', 'active', 'installation_date')
    search_fields = ('name', 'serial_number', 'manufacturer')
    date_hierarchy = 'installation_date'


@admin.register(FeedContainer)
class FeedContainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'container_type', 'get_location', 'capacity_kg_display', 'active')
    
    def capacity_kg_display(self, obj):
        return f"{float(obj.capacity_kg):,.2f} kg" if obj.capacity_kg is not None else "N/A"
    capacity_kg_display.short_description = "Capacity (kg)"
    list_filter = ('container_type', 'active')
    search_fields = ('name',)
    
    def get_location(self, obj):
        return obj.hall.name if obj.hall else obj.area.name
    get_location.short_description = 'Location'
