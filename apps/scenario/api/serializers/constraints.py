"""Serializers for biological constraints and scenario model changes."""

from typing import Any, Dict, List

from rest_framework import serializers

from apps.scenario.models import BiologicalConstraints, ScenarioModelChange


class ScenarioModelChangeSerializer(serializers.ModelSerializer):
    """Serializer for scenario model changes."""

    change_description = serializers.SerializerMethodField()

    class Meta:
        model = ScenarioModelChange
        fields = [
            "change_id",
            "change_day",
            "new_tgc_model",
            "new_fcr_model",
            "new_mortality_model",
            "change_description",
        ]
        read_only_fields = ["change_id"]

    def get_change_description(self, obj) -> str:
        """Generate human-readable change description."""
        changes: List[str] = []
        if obj.new_tgc_model:
            changes.append(f"TGC → {obj.new_tgc_model.name}")
        if obj.new_fcr_model:
            changes.append(f"FCR → {obj.new_fcr_model.name}")
        if obj.new_mortality_model:
            changes.append(f"Mortality → {obj.new_mortality_model.name}")

        joined = ', '.join(changes)
        return f"Day {obj.change_day}: {joined}" if changes else "No changes"

    def validate_change_day(self, value):
        """Validate change day is within valid range."""
        # Ensure change day is at least 1 (day 0 is before simulation starts)
        if value < 1:
            raise serializers.ValidationError(
                "Change day must be at least 1. Day 1 is the first "
                "simulation day; day 0 is before the simulation starts."
            )
        
        # Check against scenario duration if instance exists
        if self.instance and self.instance.scenario:
            if value > self.instance.scenario.duration_days:
                raise serializers.ValidationError(
                    f"Change day {value} exceeds scenario duration "
                    f"of {self.instance.scenario.duration_days} days"
                )
        
        return value

    def validate(self, data: Dict[str, Any]):
        """Ensure at least one model value is supplied."""
        if not any([
            data.get("new_tgc_model"),
            data.get("new_fcr_model"),
            data.get("new_mortality_model"),
        ]):
            raise serializers.ValidationError(
                "At least one model must be specified for a change"
            )
        return data


class BiologicalConstraintsSerializer(serializers.ModelSerializer):
    """Serializer for biological constraint sets."""

    stage_constraints = serializers.SerializerMethodField()

    class Meta:
        model = BiologicalConstraints
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "stage_constraints",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_stage_constraints(self, obj) -> List[Dict[str, Any]]:
        """Serialize stage constraints as dictionaries."""
        constraints = obj.stage_constraints.all().order_by("min_weight_g")
        return [
            {
                "stage": constraint.lifecycle_stage,
                "stage_display": constraint.get_lifecycle_stage_display(),
                "weight_range": {
                    "min": float(constraint.min_weight_g),
                    "max": float(constraint.max_weight_g),
                },
                "temperature_range": {
                    "min": float(constraint.min_temperature_c)
                    if constraint.min_temperature_c
                    else None,
                    "max": float(constraint.max_temperature_c)
                    if constraint.max_temperature_c
                    else None,
                },
                "freshwater_limit": (
                    float(constraint.max_freshwater_weight_g)
                    if constraint.max_freshwater_weight_g
                    else None
                ),
                "typical_duration": constraint.typical_duration_days,
            }
            for constraint in constraints
        ]
