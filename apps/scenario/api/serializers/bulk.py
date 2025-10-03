"""Serializers supporting CSV import/export and scenario duplication."""

from datetime import date
from typing import Any, Dict

from rest_framework import serializers

from apps.scenario.models import (
    BiologicalConstraints,
    FCRModel,
    MortalityModel,
    Scenario,
    TGCModel,
    TemperatureProfile,
)


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    data_type = serializers.ChoiceField(choices=["temperature", "fcr", "mortality"])
    profile_name = serializers.CharField(max_length=255)
    validate_only = serializers.BooleanField(default=False)

    def validate_file(self, value):
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        try:
            value.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - defensive check
            raise serializers.ValidationError("File must be valid UTF-8 encoded CSV") from exc
        finally:
            value.seek(0)
        return value

    def validate_profile_name(self, value):
        if TemperatureProfile.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"A temperature profile named '{value}' already exists"
            )
        return value


class DateRangeEntrySerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    value = serializers.FloatField()

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError("Start date must be before end date")
        days = (data["end_date"] - data["start_date"]).days
        if days > 365:
            raise serializers.ValidationError("Date range cannot exceed 365 days")
        return data


class BulkDateRangeSerializer(serializers.Serializer):
    profile_name = serializers.CharField(max_length=255)
    ranges = DateRangeEntrySerializer(many=True)
    merge_adjacent = serializers.BooleanField(default=True)
    fill_gaps = serializers.BooleanField(default=True)
    interpolation_method = serializers.ChoiceField(
        choices=["linear", "previous", "next", "default"], default="linear"
    )
    default_value = serializers.FloatField(required=False, allow_null=True)

    def validate_ranges(self, value):
        if not value:
            raise serializers.ValidationError("At least one date range is required")
        sorted_ranges = sorted(value, key=lambda entry: entry["start_date"])
        for prev, current in zip(sorted_ranges, sorted_ranges[1:]):
            if current["start_date"] <= prev["end_date"]:
                raise serializers.ValidationError(
                    "Date ranges overlap: "
                    f"{prev['end_date']} and {current['start_date']}"
                )
        return value


class DataValidationResultSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    preview_data = serializers.ListField()
    summary = serializers.DictField(required=False)


class CSVTemplateRequestSerializer(serializers.Serializer):
    data_type = serializers.ChoiceField(choices=["temperature", "fcr", "mortality"])
    include_sample_data = serializers.BooleanField(default=False)


class ScenarioDuplicateSerializer(serializers.Serializer):
    new_name = serializers.CharField(max_length=255)
    include_projections = serializers.BooleanField(default=False)
    include_model_changes = serializers.BooleanField(default=True)

    def validate_new_name(self, value):
        user = self.context.get("request").user
        if Scenario.objects.filter(name=value, created_by=user).exists():
            raise serializers.ValidationError("You already have a scenario with this name")
        return value


class BatchInitializationSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField()
    scenario_name = serializers.CharField(max_length=255)
    duration_days = serializers.IntegerField(min_value=1, max_value=1200)
    use_current_models = serializers.BooleanField(
        default=True,
        help_text="Use batch's current location and conditions for model selection",
    )

    def validate_batch_id(self, value):
        from apps.batch.models import Batch

        try:
            batch = Batch.objects.get(pk=value)
        except Batch.DoesNotExist as exc:
            raise serializers.ValidationError("Batch not found") from exc
        return batch

    def create_scenario_from_batch(self, validated_data):
        batch = validated_data["batch_id"]
        current_assignment = batch.container_assignments.filter(is_active=True).first()
        if not current_assignment:
            raise serializers.ValidationError("Batch has no active container assignment")

        initial_data: Dict[str, Any] = {
            "name": validated_data["scenario_name"],
            "duration_days": validated_data["duration_days"],
            "initial_count": current_assignment.population_count,
            "initial_weight": float(current_assignment.avg_weight_g)
            if current_assignment.avg_weight_g
            else None,
            "batch": batch,
            "genotype": batch.species.name if hasattr(batch, "species") else "Unknown",
            "supplier": "Internal",
            "start_date": date.today(),
        }

        if validated_data.get("use_current_models"):
            initial_data["tgc_model"] = TGCModel.objects.first()
            initial_data["fcr_model"] = FCRModel.objects.first()
            initial_data["mortality_model"] = MortalityModel.objects.first()

        return initial_data
