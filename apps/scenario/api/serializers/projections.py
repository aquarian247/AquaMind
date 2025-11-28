"""Projection and comparison serializers for scenarios."""

from typing import Any, Dict, List, Optional

from rest_framework import serializers

from apps.scenario.models import Scenario, ScenarioProjection, ProjectionRun


class ProjectionRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing projection runs."""
    scenario_name = serializers.CharField(source='scenario.name', read_only=True)
    pinned_batch_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectionRun
        fields = [
            'run_id', 'scenario', 'scenario_name', 'run_number', 
            'label', 'run_date', 'total_projections',
            'final_weight_g', 'final_biomass_kg', 'pinned_batch_count',
            'created_by', 'created_at'
        ]
        read_only_fields = ['run_id', 'run_date', 'run_number', 'created_at']
    
    def get_pinned_batch_count(self, obj):
        return obj.pinned_batches.count()


class ProjectionRunDetailSerializer(ProjectionRunListSerializer):
    """Full serializer with parameters snapshot."""
    parameters_snapshot = serializers.JSONField(read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.username', 
        read_only=True,
        allow_null=True
    )
    
    class Meta(ProjectionRunListSerializer.Meta):
        fields = ProjectionRunListSerializer.Meta.fields + [
            'parameters_snapshot', 'notes', 'created_by_name', 'updated_at'
        ]


class ScenarioProjectionSerializer(serializers.ModelSerializer):
    """Serializer for scenario projection entries."""

    stage_name = serializers.CharField(source="current_stage.name", read_only=True)
    growth_rate = serializers.SerializerMethodField()
    fcr_actual = serializers.SerializerMethodField()

    class Meta:
        model = ScenarioProjection
        fields = [
            "projection_id",
            "scenario",
            "projection_date",
            "day_number",
            "average_weight",
            "population",
            "biomass",
            "daily_feed",
            "cumulative_feed",
            "temperature",
            "current_stage",
            "stage_name",
            "growth_rate",
            "fcr_actual",
        ]
        read_only_fields = ["projection_id"]

    def get_growth_rate(self, obj) -> Optional[float]:
        if obj.day_number > 0:
            return None
        return 0

    def get_fcr_actual(self, obj) -> Optional[float]:
        if obj.biomass > 0 and obj.cumulative_feed > 0:
            return round(obj.cumulative_feed / obj.biomass, 2)
        return None


class ProjectionChartSerializer(serializers.Serializer):
    """Serializer for formatting projection data for charts."""

    chart_type = serializers.ChoiceField(choices=["line", "area", "bar"], default="line")
    metrics = serializers.MultipleChoiceField(
        choices=["weight", "population", "biomass", "feed", "temperature"],
        default=["weight", "biomass"],
    )
    aggregation = serializers.ChoiceField(
        choices=["daily", "weekly", "monthly"],
        default="daily",
    )

    def to_representation(self, projections):
        chart_data = {"labels": [], "datasets": []}
        aggregated = self._aggregate_projections(
            projections, self.validated_data["aggregation"]
        )

        for metric in self.validated_data["metrics"]:
            dataset = {
                "label": self._get_metric_label(metric),
                "data": [],
                "borderColor": self._get_metric_color(metric),
                "backgroundColor": self._get_metric_color(metric, alpha=0.2),
                "yAxisID": self._get_y_axis_id(metric),
            }

            if not chart_data["labels"]:
                chart_data["labels"] = [row["label"] for row in aggregated]

            dataset["data"] = [row.get(metric, 0) for row in aggregated]
            chart_data["datasets"].append(dataset)

        return chart_data

    def _aggregate_projections(self, projections, period):
        aggregated: List[Dict[str, Any]] = []
        for projection in projections:
            aggregated.append(
                {
                    "label": projection.projection_date.strftime("%Y-%m-%d"),
                    "weight": float(projection.average_weight),
                    "population": float(projection.population),
                    "biomass": float(projection.biomass),
                    "feed": float(projection.daily_feed),
                    "temperature": float(projection.temperature),
                }
            )
        return aggregated

    def _get_metric_label(self, metric):
        labels = {
            "weight": "Average Weight (g)",
            "population": "Population",
            "biomass": "Biomass (kg)",
            "feed": "Daily Feed (kg)",
            "temperature": "Temperature (°C)",
        }
        return labels.get(metric, metric)

    def _get_metric_color(self, metric, alpha=1):
        colors = {
            "weight": f"rgba(75, 192, 192, {alpha})",
            "population": f"rgba(255, 99, 132, {alpha})",
            "biomass": f"rgba(54, 162, 235, {alpha})",
            "feed": f"rgba(255, 206, 86, {alpha})",
            "temperature": f"rgba(153, 102, 255, {alpha})",
        }
        return colors.get(metric, f"rgba(128, 128, 128, {alpha})")

    def _get_y_axis_id(self, metric):
        return "y-axis-2" if metric == "temperature" else "y-axis-1"


class ScenarioComparisonSerializer(serializers.Serializer):
    """Serializer for comparing multiple scenarios."""

    scenario_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=2, max_length=5
    )
    comparison_metrics = serializers.MultipleChoiceField(
        choices=[
            "final_weight",
            "final_biomass",
            "total_feed",
            "survival_rate",
            "harvest_day",
            "fcr_overall",
        ],
        default=["final_weight", "final_biomass", "fcr_overall"],
    )

    def validate_scenario_ids(self, value):
        user = self.context.get("request").user
        scenarios = Scenario.objects.filter(scenario_id__in=value, created_by=user)
        if scenarios.count() != len(value):
            raise serializers.ValidationError(
                "One or more scenarios not found or not accessible"
            )
        return value

    def to_representation(self, scenarios):
        data = {"scenarios": [], "metrics": {}}

        for scenario in scenarios:
            latest = scenario.projections.order_by("-day_number").first()
            scenario_entry: Dict[str, Any] = {
                "id": scenario.scenario_id,
                "name": scenario.name,
                "duration": scenario.duration_days,
                "models": {
                    "tgc": scenario.tgc_model.name,
                    "fcr": scenario.fcr_model.name,
                    "mortality": scenario.mortality_model.name,
                },
            }

            if latest:
                scenario_entry["final_state"] = {
                    "weight": float(latest.average_weight),
                    "population": float(latest.population),
                    "biomass": float(latest.biomass),
                    "total_feed": float(latest.cumulative_feed),
                    "survival_rate": latest.population / scenario.initial_count * 100,
                }

            data["scenarios"].append(scenario_entry)

        for metric in self.validated_data["comparison_metrics"]:
            data["metrics"][metric] = self._calculate_metric_comparison(
                data["scenarios"], metric
            )

        return data

    def _calculate_metric_comparison(self, scenarios, metric):
        values: List[Dict[str, Any]] = []
        for scenario in scenarios:
            final_state = scenario.get("final_state")
            if not final_state:
                continue

            if metric == "final_weight":
                values.append({"scenario": scenario["name"], "value": final_state["weight"]})
            elif metric == "final_biomass":
                values.append({"scenario": scenario["name"], "value": final_state["biomass"]})
            elif metric == "survival_rate":
                values.append({"scenario": scenario["name"], "value": final_state["survival_rate"]})

        return {
            "values": values,
            "best": max(values, key=lambda x: x["value"]) if values else None,
            "worst": min(values, key=lambda x: x["value"]) if values else None,
        }
