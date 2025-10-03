"""Temperature-related serializers for the Scenario API."""

from typing import Any, Dict, Optional

from rest_framework import serializers

from apps.scenario.models import TemperatureProfile, TemperatureReading


class TemperatureReadingSerializer(serializers.ModelSerializer):
    """Serializer for temperature readings with validation."""

    class Meta:
        model = TemperatureReading
        fields = ["reading_id", "reading_date", "temperature"]
        read_only_fields = ["reading_id"]

    def validate_temperature(self, value):
        """Validate temperature is within reasonable range."""
        if value < -5 or value > 35:
            raise serializers.ValidationError(
                "Temperature must be between -5°C and 35°C for aquaculture operations."
            )
        return value


class TemperatureProfileSerializer(serializers.ModelSerializer):
    """Serializer for temperature profiles with nested readings."""

    readings = TemperatureReadingSerializer(many=True, read_only=True)
    reading_count = serializers.IntegerField(read_only=True)
    date_range = serializers.SerializerMethodField()
    temperature_summary = serializers.SerializerMethodField()

    class Meta:
        model = TemperatureProfile
        fields = [
            "profile_id",
            "name",
            "readings",
            "reading_count",
            "date_range",
            "temperature_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["profile_id", "created_at", "updated_at"]

    def get_date_range(self, obj) -> Optional[Dict[str, Any]]:
        """Get the date range of readings."""
        readings = obj.readings.order_by("reading_date")
        if readings.exists():
            first = readings.first()
            last = readings.last()
            return {
                "start": first.reading_date,
                "end": last.reading_date,
                "days": (last.reading_date - first.reading_date).days + 1,
            }
        return None

    def get_temperature_summary(self, obj) -> Optional[Dict[str, Any]]:
        """Get temperature statistics."""
        readings = obj.readings.all()
        if not readings.exists():
            return None

        temps = [r.temperature for r in readings]
        return {
            "min": min(temps),
            "max": max(temps),
            "avg": sum(temps) / len(temps),
            "std_dev": self._calculate_std_dev(temps),
        }

    def _calculate_std_dev(self, values):
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
