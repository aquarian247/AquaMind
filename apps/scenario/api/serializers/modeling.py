"""Model-related serializers for Scenario API (TGC, FCR, Mortality)."""

from typing import Any, Dict, List

from rest_framework import serializers

from apps.batch.models import LifeCycleStage
from apps.scenario.models import (
    FCRModel,
    FCRModelStage,
    MortalityModel,
    MortalityModelStage,
    TGCModel,
    TGCModelStage,
)


class TGCModelStageSerializer(serializers.ModelSerializer):
    """Serializer for stage-specific TGC overrides."""

    stage_display = serializers.CharField(
        source="get_lifecycle_stage_display", read_only=True
    )

    class Meta:
        model = TGCModelStage
        fields = [
            "lifecycle_stage",
            "stage_display",
            "tgc_value",
            "temperature_exponent",
            "weight_exponent",
        ]

    def validate_tgc_value(self, value):
        """Validate TGC value is reasonable."""
        if value < 0.001 or value > 0.1:
            raise serializers.ValidationError(
                "TGC value must be between 0.001 and 0.1"
            )
        return value


class TGCModelSerializer(serializers.ModelSerializer):
    """Enhanced serializer for TGC models with validation."""

    profile_name = serializers.CharField(source="profile.name", read_only=True)
    stage_overrides = TGCModelStageSerializer(many=True, read_only=True)
    has_temperature_data = serializers.SerializerMethodField()

    class Meta:
        model = TGCModel
        fields = [
            "model_id",
            "name",
            "location",
            "release_period",
            "profile",
            "profile_name",
            "tgc_value",
            "exponent_n",
            "exponent_m",
            "stage_overrides",
            "has_temperature_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["model_id", "created_at", "updated_at"]

    def get_has_temperature_data(self, obj) -> bool:
        """Check if temperature profile has data."""
        return obj.profile.readings.exists()

    def validate_tgc_value(self, value):
        """Validate TGC coefficient."""
        if value <= 0:
            raise serializers.ValidationError("TGC value must be positive")
        if value > 0.1:
            raise serializers.ValidationError(
                "TGC value seems too high. Typical values are between 0.001 and 0.05"
            )
        return value

    def validate_exponent_n(self, value):
        """Validate temperature exponent."""
        if value < 0 or value > 2:
            raise serializers.ValidationError(
                "Temperature exponent should be between 0 and 2 (typically around 0.33)"
            )
        return value

    def validate_exponent_m(self, value):
        """Validate weight exponent."""
        if value < 0 or value > 1:
            raise serializers.ValidationError(
                "Weight exponent should be between 0 and 1 (typically around 0.66)"
            )
        return value

    def validate(self, data):
        """Cross-field validation."""
        profile = data.get("profile")
        if profile and not profile.readings.exists():
            raise serializers.ValidationError(
                {"profile": "Selected temperature profile has no temperature data"}
            )
        return data


class FCRModelStageSerializer(serializers.ModelSerializer):
    """Enhanced serializer for FCR model stages."""

    stage_name = serializers.CharField(source="stage.name", read_only=True)
    overrides = serializers.SerializerMethodField()

    class Meta:
        model = FCRModelStage
        fields = ["stage", "stage_name", "fcr_value", "duration_days", "overrides"]

    def get_overrides(self, obj) -> List[Dict[str, Any]]:
        """Get weight-based FCR overrides."""
        overrides = obj.overrides.all().order_by("min_weight_g")
        return [
            {
                "min_weight_g": float(o.min_weight_g),
                "max_weight_g": float(o.max_weight_g),
                "fcr_value": float(o.fcr_value),
            }
            for o in overrides
        ]

    def validate_fcr_value(self, value):
        """Validate FCR value."""
        if value <= 0:
            raise serializers.ValidationError("FCR value must be positive")
        if value > 5:
            raise serializers.ValidationError(
                "FCR value seems too high. Typical values are between 0.8 and 2.5"
            )
        return value

    def validate_duration_days(self, value):
        """Validate stage duration."""
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day")
        if value > 500:
            raise serializers.ValidationError(
                "Stage duration seems too long. Maximum expected is 500 days"
            )
        return value


class FCRModelSerializer(serializers.ModelSerializer):
    """Enhanced serializer for FCR models with validation."""

    stages = FCRModelStageSerializer(many=True, read_only=True)
    total_duration = serializers.SerializerMethodField()
    stage_coverage = serializers.SerializerMethodField()

    class Meta:
        model = FCRModel
        fields = [
            "model_id",
            "name",
            "stages",
            "total_duration",
            "stage_coverage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["model_id", "created_at", "updated_at"]

    def get_total_duration(self, obj) -> int:
        """Calculate total duration across all stages."""
        return sum(stage.duration_days for stage in obj.stages.all())

    def get_stage_coverage(self, obj) -> Dict[str, Any]:
        """Check which lifecycle stages are covered."""
        covered_stages = {stage.stage.name for stage in obj.stages.all()}
        all_stages = set(LifeCycleStage.objects.values_list("name", flat=True))
        return {
            "covered": list(covered_stages),
            "missing": list(all_stages - covered_stages),
            "coverage_percent": (
                len(covered_stages) / len(all_stages) * 100 if all_stages else 0
            ),
        }


class MortalityModelStageSerializer(serializers.ModelSerializer):
    """Serializer for stage-specific mortality rates."""

    stage_display = serializers.CharField(
        source="get_lifecycle_stage_display", read_only=True
    )

    class Meta:
        model = MortalityModelStage
        fields = [
            "lifecycle_stage",
            "stage_display",
            "daily_rate_percent",
            "weekly_rate_percent",
        ]


class MortalityModelSerializer(serializers.ModelSerializer):
    """Enhanced serializer for mortality models with validation."""

    stage_overrides = MortalityModelStageSerializer(many=True, read_only=True)
    effective_annual_rate = serializers.SerializerMethodField()

    class Meta:
        model = MortalityModel
        fields = [
            "model_id",
            "name",
            "frequency",
            "rate",
            "stage_overrides",
            "effective_annual_rate",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["model_id", "created_at", "updated_at"]

    def get_effective_annual_rate(self, obj) -> float:
        """Calculate effective annual mortality rate."""
        if obj.frequency == "daily":
            survival_rate = (1 - obj.rate / 100) ** 365
        else:
            survival_rate = (1 - obj.rate / 100) ** 52
        annual_mortality = (1 - survival_rate) * 100
        return round(annual_mortality, 2)

    def validate_rate(self, value):
        """Validate mortality rate."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Mortality rate must be between 0 and 100 percent"
            )

        frequency = self.initial_data.get(
            "frequency", self.instance.frequency if self.instance else "daily"
        )

        if frequency == "daily" and value > 5:
            raise serializers.ValidationError(
                "Daily mortality rate above 5% is unusually high. Please verify."
            )
        if frequency == "weekly" and value > 20:
            raise serializers.ValidationError(
                "Weekly mortality rate above 20% is unusually high. Please verify."
            )

        return value
