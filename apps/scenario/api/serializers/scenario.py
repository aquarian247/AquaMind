"""Scenario-focused serializers and helpers."""

from typing import Dict, Optional

from rest_framework import serializers

from apps.scenario.models import Scenario

from .constraints import (
    BiologicalConstraintsSerializer,
    ScenarioModelChangeSerializer,
)


DEFAULT_STAGE_BANDS = [
    (0.2, "egg", "Egg"),
    (1, "alevin", "Alevin"),
    (5, "fry", "Fry"),
    (50, "parr", "Parr"),
    (150, "smolt", "Smolt"),
    (1000, "post_smolt", "Post-Smolt"),
]


def _stage_payload(stage: str, display: str) -> Dict[str, str]:
    return {"stage": stage, "display": display}


def _stage_from_constraints(obj: Scenario) -> Optional[Dict[str, str]]:
    constraints = getattr(obj.biological_constraints, "stage_constraints", None)
    if not constraints:
        return None

    weight = obj.initial_weight
    for constraint in constraints.all():
        if constraint.min_weight_g <= weight <= constraint.max_weight_g:
            return _stage_payload(
                constraint.lifecycle_stage, constraint.get_lifecycle_stage_display()
            )
    return None


def _stage_from_weight(weight: float) -> Dict[str, str]:
    for threshold, stage, display in DEFAULT_STAGE_BANDS:
        if weight < threshold:
            return _stage_payload(stage, display)
    return _stage_payload("harvest", "Harvest")


class ScenarioSerializer(serializers.ModelSerializer):
    """Enhanced serializer for scenarios with comprehensive validation."""

    model_changes = ScenarioModelChangeSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    biological_constraints_info = BiologicalConstraintsSerializer(
        source="biological_constraints", read_only=True
    )
    initial_stage = serializers.SerializerMethodField()
    projected_harvest_day = serializers.SerializerMethodField()

    class Meta:
        model = Scenario
        fields = [
            "scenario_id",
            "name",
            "start_date",
            "duration_days",
            "initial_count",
            "initial_weight",
            "genotype",
            "supplier",
            "tgc_model",
            "fcr_model",
            "mortality_model",
            "batch",
            "biological_constraints",
            "biological_constraints_info",
            "model_changes",
            "created_by",
            "created_by_name",
            "initial_stage",
            "projected_harvest_day",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["scenario_id", "created_by", "created_at", "updated_at"]

    def get_initial_stage(self, obj) -> Optional[Dict[str, str]]:
        """Determine initial lifecycle stage based on weight."""
        weight = obj.initial_weight
        if weight is None:
            return None

        constrained_stage = _stage_from_constraints(obj)
        if constrained_stage:
            return constrained_stage

        return _stage_from_weight(weight)

    def get_projected_harvest_day(self, obj) -> Optional[int]:
        """Estimate harvest day based on growth model."""
        if obj.initial_weight and obj.tgc_model:
            # Placeholder until detailed growth calculations are implemented
            return None
        return None

    def validate_name(self, value):
        """Ensure unique naming within user's scenarios."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user:
            return value

        queryset = Scenario.objects.filter(name=value, created_by=user)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "You already have a scenario with this name"
            )
        return value

    def validate_duration_days(self, value):
        """Validate scenario duration."""
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day")
        if value > 1200:
            raise serializers.ValidationError(
                "Duration cannot exceed 1200 days (>3 years)"
            )
        return value

    def validate_initial_count(self, value):
        """Validate initial fish count."""
        if value < 1:
            raise serializers.ValidationError("Must have at least 1 fish")
        if value > 10_000_000:
            raise serializers.ValidationError(
                "Initial count seems too high (max 10 million)"
            )
        return value

    def validate_initial_weight(self, value):
        """Validate initial weight."""
        if value is None:
            return value
        if value < 0.01:
            raise serializers.ValidationError(
                "Initial weight too small (minimum 0.01g)"
            )
        if value > 10_000:
            raise serializers.ValidationError(
                "Initial weight too large (maximum 10kg)"
            )
        return value

    def validate(self, data):
        """Placeholder for cross-field validation hooks."""
        return data
