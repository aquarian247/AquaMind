"""
Serializers for the infrastructure app.

These serializers convert Django models to JSON and vice versa for the REST API.
"""
from rest_framework import serializers
from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType,
    Container,
    Sensor,
    FeedContainer
)


class GeographySerializer(serializers.ModelSerializer):
    """Serializer for the Geography model."""

    class Meta:
        model = Geography
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class AreaSerializer(serializers.ModelSerializer):
    """Serializer for the Area model."""
    
    geography_name = serializers.StringRelatedField(source='geography', read_only=True)

    class Meta:
        model = Area
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """Validate the latitude and longitude values."""
        if 'latitude' in data:
            if data['latitude'] < -90 or data['latitude'] > 90:
                raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        
        if 'longitude' in data:
            if data['longitude'] < -180 or data['longitude'] > 180:
                raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        
        return data


class FreshwaterStationSerializer(serializers.ModelSerializer):
    """Serializer for the FreshwaterStation model."""
    
    geography_name = serializers.StringRelatedField(source='geography', read_only=True)
    station_type_display = serializers.CharField(source='get_station_type_display', read_only=True)

    class Meta:
        model = FreshwaterStation
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class HallSerializer(serializers.ModelSerializer):
    """Serializer for the Hall model."""
    
    freshwater_station_name = serializers.StringRelatedField(
        source='freshwater_station', read_only=True
    )

    class Meta:
        model = Hall
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ContainerTypeSerializer(serializers.ModelSerializer):
    """Serializer for the ContainerType model."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = ContainerType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ContainerSerializer(serializers.ModelSerializer):
    """Serializer for the Container model."""
    
    container_type_name = serializers.StringRelatedField(source='container_type', read_only=True)
    hall_name = serializers.StringRelatedField(source='hall', read_only=True)
    area_name = serializers.StringRelatedField(source='area', read_only=True)

    class Meta:
        model = Container
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """
        Validate that the container is in either a hall or area, not both.
        Also validates that volume doesn't exceed container type max volume.
        """
        hall = data.get('hall')
        area = data.get('area')
        
        # Check if container is in both hall and area
        if hall and area:
            raise serializers.ValidationError(
                {"location": "Container must be in either a hall or an area, not both."}
            )
        
        # Check if container is neither in hall nor in area
        if not hall and not area:
            raise serializers.ValidationError(
                {"location": "Container must be in either a hall or an area."}
            )
        
        # Validate volume against container type max volume
        container_type = data.get('container_type')
        volume = data.get('volume_m3')
        
        if container_type and volume and volume > container_type.max_volume_m3:
            raise serializers.ValidationError({
                "volume_m3": f"Volume cannot exceed container type maximum volume of {container_type.max_volume_m3} m³."
            })
        
        return data


class SensorSerializer(serializers.ModelSerializer):
    """Serializer for the Sensor model."""
    
    container_name = serializers.StringRelatedField(source='container', read_only=True)
    sensor_type_display = serializers.CharField(source='get_sensor_type_display', read_only=True)

    class Meta:
        model = Sensor
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class FeedContainerSerializer(serializers.ModelSerializer):
    """Serializer for the FeedContainer model."""
    
    container_type_display = serializers.CharField(source='get_container_type_display', read_only=True)
    hall_name = serializers.StringRelatedField(source='hall', read_only=True)
    area_name = serializers.StringRelatedField(source='area', read_only=True)

    class Meta:
        model = FeedContainer
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """Validate that the feed container is in either a hall or area, not both."""
        hall = data.get('hall')
        area = data.get('area')
        
        # Check if container is in both hall and area
        if hall and area:
            raise serializers.ValidationError(
                {"location": "Feed container must be in either a hall or an area, not both."}
            )
        
        # Check if container is neither in hall nor in area
        if not hall and not area:
            raise serializers.ValidationError(
                {"location": "Feed container must be in either a hall or an area."}
            )
        
        return data
