"""
Serializers for the Scenario Planning API.

Handles serialization/deserialization of scenario data with
comprehensive validation for data entry operations.
"""
from rest_framework import serializers
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
import base64
import io
import csv
from datetime import datetime, date
from typing import Dict, Any, Optional, List  # added for explicit return typing

from ..models import (
    TemperatureProfile, TemperatureReading, TGCModel, FCRModel,
    FCRModelStage, MortalityModel, Scenario, ScenarioModelChange,
    ScenarioProjection, BiologicalConstraints, StageConstraint,
    TGCModelStage, FCRModelStageOverride, MortalityModelStage,
    LifecycleStageChoices
)
from ..services import BulkDataImportService, DateRangeInputService
from apps.batch.models import LifeCycleStage


class TemperatureReadingSerializer(serializers.ModelSerializer):
    """Serializer for temperature readings with validation."""
    
    class Meta:
        model = TemperatureReading
        fields = ['reading_id', 'reading_date', 'temperature']
        read_only_fields = ['reading_id']
    
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
            'profile_id', 'name', 'readings', 'reading_count',
            'date_range', 'temperature_summary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['profile_id', 'created_at', 'updated_at']
    
    def get_date_range(self, obj) -> Optional[Dict[str, Any]]:
        """Get the date range of readings."""
        readings = obj.readings.order_by('reading_date')
        if readings.exists():
            return {
                'start': readings.first().reading_date,
                'end': readings.last().reading_date,
                'days': (readings.last().reading_date - readings.first().reading_date).days + 1
            }
        return None
    
    def get_temperature_summary(self, obj) -> Optional[Dict[str, Any]]:
        """Get temperature statistics."""
        readings = obj.readings.all()
        if not readings.exists():
            return None
        
        temps = [r.temperature for r in readings]
        return {
            'min': min(temps),
            'max': max(temps),
            'avg': sum(temps) / len(temps),
            'std_dev': self._calculate_std_dev(temps)
        }
    
    def _calculate_std_dev(self, values):
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0
        avg = sum(values) / len(values)
        variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5


class TGCModelStageSerializer(serializers.ModelSerializer):
    """Serializer for stage-specific TGC overrides."""
    
    stage_display = serializers.CharField(
        source='get_lifecycle_stage_display', read_only=True
    )
    
    class Meta:
        model = TGCModelStage
        fields = [
            'lifecycle_stage', 'stage_display', 'tgc_value',
            'temperature_exponent', 'weight_exponent'
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
    
    profile_name = serializers.CharField(source='profile.name', read_only=True)
    stage_overrides = TGCModelStageSerializer(many=True, read_only=True)
    has_temperature_data = serializers.SerializerMethodField()
    
    class Meta:
        model = TGCModel
        fields = [
            'model_id', 'name', 'location', 'release_period',
            'profile', 'profile_name', 'tgc_value', 'exponent_n',
            'exponent_m', 'stage_overrides', 'has_temperature_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['model_id', 'created_at', 'updated_at']
    
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
        # Ensure temperature profile has data
        if 'profile' in data:
            profile = data['profile']
            if not profile.readings.exists():
                raise serializers.ValidationError({
                    'profile': 'Selected temperature profile has no temperature data'
                })
        
        return data


class FCRModelStageSerializer(serializers.ModelSerializer):
    """Enhanced serializer for FCR model stages."""
    
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    overrides = serializers.SerializerMethodField()
    
    class Meta:
        model = FCRModelStage
        fields = [
            'stage', 'stage_name', 'fcr_value', 'duration_days', 'overrides'
        ]
    
    def get_overrides(self, obj) -> List[Dict[str, Any]]:
        """Get weight-based FCR overrides."""
        overrides = obj.overrides.all().order_by('min_weight_g')
        return [
            {
                'min_weight_g': float(o.min_weight_g),
                'max_weight_g': float(o.max_weight_g),
                'fcr_value': float(o.fcr_value)
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
            'model_id', 'name', 'stages', 'total_duration',
            'stage_coverage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['model_id', 'created_at', 'updated_at']
    
    def get_total_duration(self, obj) -> int:
        """Calculate total duration across all stages."""
        return sum(stage.duration_days for stage in obj.stages.all())
    
    def get_stage_coverage(self, obj) -> Dict[str, Any]:
        """Check which lifecycle stages are covered."""
        covered_stages = set(stage.stage.name for stage in obj.stages.all())
        all_stages = set(LifeCycleStage.objects.values_list('name', flat=True))
        return {
            'covered': list(covered_stages),
            'missing': list(all_stages - covered_stages),
            'coverage_percent': (len(covered_stages) / len(all_stages) * 100) if all_stages else 0
        }


class MortalityModelStageSerializer(serializers.ModelSerializer):
    """Serializer for stage-specific mortality rates."""
    
    stage_display = serializers.CharField(
        source='get_lifecycle_stage_display', read_only=True
    )
    
    class Meta:
        model = MortalityModelStage
        fields = [
            'lifecycle_stage', 'stage_display',
            'daily_rate_percent', 'weekly_rate_percent'
        ]


class MortalityModelSerializer(serializers.ModelSerializer):
    """Enhanced serializer for mortality models with validation."""
    
    stage_overrides = MortalityModelStageSerializer(many=True, read_only=True)
    effective_annual_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = MortalityModel
        fields = [
            'model_id', 'name', 'frequency', 'rate',
            'stage_overrides', 'effective_annual_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['model_id', 'created_at', 'updated_at']
    
    def get_effective_annual_rate(self, obj) -> float:
        """Calculate effective annual mortality rate."""
        if obj.frequency == 'daily':
            # Convert daily rate to annual
            survival_rate = (1 - obj.rate / 100) ** 365
            annual_mortality = (1 - survival_rate) * 100
        else:  # weekly
            # Convert weekly rate to annual
            survival_rate = (1 - obj.rate / 100) ** 52
            annual_mortality = (1 - survival_rate) * 100
        
        return round(annual_mortality, 2)
    
    def validate_rate(self, value):
        """Validate mortality rate."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Mortality rate must be between 0 and 100 percent"
            )
        
        # Additional validation based on frequency
        frequency = self.initial_data.get('frequency', 
                                         self.instance.frequency if self.instance else 'daily')
        
        if frequency == 'daily' and value > 5:
            raise serializers.ValidationError(
                "Daily mortality rate above 5% is unusually high. Please verify."
            )
        elif frequency == 'weekly' and value > 20:
            raise serializers.ValidationError(
                "Weekly mortality rate above 20% is unusually high. Please verify."
            )
        
        return value


class ScenarioModelChangeSerializer(serializers.ModelSerializer):
    """Enhanced serializer for scenario model changes."""
    
    change_description = serializers.SerializerMethodField()
    
    class Meta:
        model = ScenarioModelChange
        fields = [
            'change_id', 'change_day', 'new_tgc_model',
            'new_fcr_model', 'new_mortality_model',
            'change_description'
        ]
        read_only_fields = ['change_id']
    
    def get_change_description(self, obj) -> str:
        """Generate human-readable change description."""
        changes = []
        if obj.new_tgc_model:
            changes.append(f"TGC → {obj.new_tgc_model.name}")
        if obj.new_fcr_model:
            changes.append(f"FCR → {obj.new_fcr_model.name}")
        if obj.new_mortality_model:
            changes.append(f"Mortality → {obj.new_mortality_model.name}")
        
        return f"Day {obj.change_day}: {', '.join(changes)}" if changes else "No changes"
    
    def validate_change_day(self, value):
        """Validate change day is within scenario duration."""
        if self.instance and self.instance.scenario:
            if value >= self.instance.scenario.duration_days:
                raise serializers.ValidationError(
                    f"Change day must be before scenario end (day {self.instance.scenario.duration_days})"
                )
        return value
    
    def validate(self, data):
        """Ensure at least one model is being changed."""
        if not any([data.get('new_tgc_model'), 
                   data.get('new_fcr_model'), 
                   data.get('new_mortality_model')]):
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
            'id', 'name', 'description', 'is_active',
            'stage_constraints', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_stage_constraints(self, obj) -> List[Dict[str, Any]]:
        """Get stage constraints in a structured format."""
        constraints = obj.stage_constraints.all().order_by('min_weight_g')
        return [
            {
                'stage': c.lifecycle_stage,
                'stage_display': c.get_lifecycle_stage_display(),
                'weight_range': {
                    'min': float(c.min_weight_g),
                    'max': float(c.max_weight_g)
                },
                'temperature_range': {
                    'min': float(c.min_temperature_c) if c.min_temperature_c else None,
                    'max': float(c.max_temperature_c) if c.max_temperature_c else None
                },
                'freshwater_limit': float(c.max_freshwater_weight_g) if c.max_freshwater_weight_g else None,
                'typical_duration': c.typical_duration_days
            }
            for c in constraints
        ]


class ScenarioSerializer(serializers.ModelSerializer):
    """Enhanced serializer for scenarios with comprehensive validation."""
    
    model_changes = ScenarioModelChangeSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    biological_constraints_info = BiologicalConstraintsSerializer(
        source='biological_constraints', read_only=True
    )
    initial_stage = serializers.SerializerMethodField()
    projected_harvest_day = serializers.SerializerMethodField()
    
    class Meta:
        model = Scenario
        fields = [
            'scenario_id', 'name', 'start_date', 'duration_days',
            'initial_count', 'initial_weight', 'genotype', 'supplier',
            'tgc_model', 'fcr_model', 'mortality_model', 'batch',
            'biological_constraints', 'biological_constraints_info',
            'model_changes', 'created_by', 'created_by_name',
            'initial_stage', 'projected_harvest_day',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'scenario_id', 'created_by', 'created_at', 'updated_at'
        ]
    
    def get_initial_stage(self, obj) -> Optional[Dict[str, str]]:
        """Determine initial lifecycle stage based on weight."""
        if not obj.initial_weight:
            return None
        
        # Use biological constraints if available
        if obj.biological_constraints:
            for constraint in obj.biological_constraints.stage_constraints.all():
                if constraint.min_weight_g <= obj.initial_weight <= constraint.max_weight_g:
                    return {
                        'stage': constraint.lifecycle_stage,
                        'display': constraint.get_lifecycle_stage_display()
                    }
        
        # Fallback to default stages
        weight = obj.initial_weight
        if weight < 0.2:
            return {'stage': 'egg', 'display': 'Egg'}
        elif weight < 1:
            return {'stage': 'alevin', 'display': 'Alevin'}
        elif weight < 5:
            return {'stage': 'fry', 'display': 'Fry'}
        elif weight < 50:
            return {'stage': 'parr', 'display': 'Parr'}
        elif weight < 150:
            return {'stage': 'smolt', 'display': 'Smolt'}
        elif weight < 1000:
            return {'stage': 'post_smolt', 'display': 'Post-Smolt'}
        else:
            return {'stage': 'harvest', 'display': 'Harvest'}
    
    def get_projected_harvest_day(self, obj) -> Optional[int]:
        """Estimate harvest day based on growth model."""
        # This is a simplified estimate
        if obj.initial_weight and obj.tgc_model:
            target_weight = 4500  # 4.5 kg typical harvest weight
            # Very rough estimate: days = (target/initial)^(1/0.66) / (TGC * avg_temp)
            # This would need the actual calculation engine for accuracy
            return None  # Placeholder
        return None
    
    def validate_name(self, value):
        """Ensure unique naming within user's scenarios."""
        user = self.context.get('request').user if self.context.get('request') else None
        if user and Scenario.objects.filter(
            name=value, 
            created_by=user
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
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
        if value > 10000000:
            raise serializers.ValidationError(
                "Initial count seems too high (max 10 million)"
            )
        return value
    
    def validate_initial_weight(self, value):
        """Validate initial weight."""
        if value is not None:
            if value < 0.01:
                raise serializers.ValidationError(
                    "Initial weight too small (minimum 0.01g)"
                )
            if value > 10000:
                raise serializers.ValidationError(
                    "Initial weight too large (maximum 10kg)"
                )
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        # Validate batch initialization if provided
        if data.get('batch'):
            batch = data['batch']
            # Could validate that batch has active assignments
            # and extract initial conditions from it
            
        # Validate model compatibility
        if data.get('tgc_model') and data.get('biological_constraints'):
            # Could check if TGC model location matches constraints
            pass
            
        return data


class ScenarioProjectionSerializer(serializers.ModelSerializer):
    """Enhanced serializer for scenario projections with chart formatting."""
    
    stage_name = serializers.CharField(
        source='current_stage.name', read_only=True
    )
    growth_rate = serializers.SerializerMethodField()
    fcr_actual = serializers.SerializerMethodField()
    
    class Meta:
        model = ScenarioProjection
        fields = [
            'projection_id', 'scenario', 'projection_date', 'day_number',
            'average_weight', 'population', 'biomass', 'daily_feed',
            'cumulative_feed', 'temperature', 'current_stage', 'stage_name',
            'growth_rate', 'fcr_actual'
        ]
        read_only_fields = ['projection_id']
    
    def get_growth_rate(self, obj) -> Optional[float]:
        """Calculate daily growth rate percentage."""
        if obj.day_number > 0:
            # Would need previous day's weight for accurate calculation
            # This is a placeholder
            return None
        return 0
    
    def get_fcr_actual(self, obj) -> Optional[float]:
        """Calculate actual FCR up to this point."""
        if obj.biomass > 0 and obj.cumulative_feed > 0:
            # Simplified calculation - would need initial biomass
            return round(obj.cumulative_feed / obj.biomass, 2)
        return None


class ProjectionChartSerializer(serializers.Serializer):
    """Serializer for formatting projection data for charts."""
    
    chart_type = serializers.ChoiceField(
        choices=['line', 'area', 'bar'],
        default='line'
    )
    metrics = serializers.MultipleChoiceField(
        choices=['weight', 'population', 'biomass', 'feed', 'temperature'],
        default=['weight', 'biomass']
    )
    aggregation = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly'],
        default='daily'
    )
    
    def to_representation(self, projections):
        """Format projections for chart display."""
        chart_data = {
            'labels': [],
            'datasets': []
        }
        
        # Group by aggregation period
        aggregated_data = self._aggregate_projections(
            projections, 
            self.validated_data['aggregation']
        )
        
        # Build datasets for each metric
        for metric in self.validated_data['metrics']:
            dataset = {
                'label': self._get_metric_label(metric),
                'data': [],
                'borderColor': self._get_metric_color(metric),
                'backgroundColor': self._get_metric_color(metric, alpha=0.2),
                'yAxisID': self._get_y_axis_id(metric)
            }
            
            for period_data in aggregated_data:
                if not chart_data['labels']:
                    chart_data['labels'].append(period_data['label'])
                dataset['data'].append(period_data.get(metric, 0))
            
            chart_data['datasets'].append(dataset)
        
        return chart_data
    
    def _aggregate_projections(self, projections, period):
        """Aggregate projections by time period."""
        # Implementation would group projections by period
        # This is a simplified version
        aggregated = []
        
        for proj in projections:
            aggregated.append({
                'label': proj.projection_date.strftime('%Y-%m-%d'),
                'weight': float(proj.average_weight),
                'population': float(proj.population),
                'biomass': float(proj.biomass),
                'feed': float(proj.daily_feed),
                'temperature': float(proj.temperature)
            })
        
        return aggregated
    
    def _get_metric_label(self, metric):
        """Get display label for metric."""
        labels = {
            'weight': 'Average Weight (g)',
            'population': 'Population',
            'biomass': 'Biomass (kg)',
            'feed': 'Daily Feed (kg)',
            'temperature': 'Temperature (°C)'
        }
        return labels.get(metric, metric)
    
    def _get_metric_color(self, metric, alpha=1):
        """Get color for metric."""
        colors = {
            'weight': f'rgba(75, 192, 192, {alpha})',
            'population': f'rgba(255, 99, 132, {alpha})',
            'biomass': f'rgba(54, 162, 235, {alpha})',
            'feed': f'rgba(255, 206, 86, {alpha})',
            'temperature': f'rgba(153, 102, 255, {alpha})'
        }
        return colors.get(metric, f'rgba(128, 128, 128, {alpha})')
    
    def _get_y_axis_id(self, metric):
        """Get Y-axis ID for metric."""
        if metric == 'temperature':
            return 'y-axis-2'
        return 'y-axis-1'


class ScenarioComparisonSerializer(serializers.Serializer):
    """Serializer for comparing multiple scenarios."""
    
    scenario_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=2,
        max_length=5
    )
    comparison_metrics = serializers.MultipleChoiceField(
        choices=[
            'final_weight', 'final_biomass', 'total_feed',
            'survival_rate', 'harvest_day', 'fcr_overall'
        ],
        default=['final_weight', 'final_biomass', 'fcr_overall']
    )
    
    def validate_scenario_ids(self, value):
        """Validate scenarios exist and belong to user."""
        user = self.context.get('request').user
        scenarios = Scenario.objects.filter(
            scenario_id__in=value,
            created_by=user
        )
        
        if scenarios.count() != len(value):
            raise serializers.ValidationError(
                "One or more scenarios not found or not accessible"
            )
        
        return value
    
    def to_representation(self, scenarios):
        """Generate comparison data."""
        comparison_data = {
            'scenarios': [],
            'metrics': {}
        }
        
        for scenario in scenarios:
            # Get latest projection for each scenario
            latest_projection = scenario.projections.order_by('-day_number').first()
            
            scenario_data = {
                'id': scenario.scenario_id,
                'name': scenario.name,
                'duration': scenario.duration_days,
                'models': {
                    'tgc': scenario.tgc_model.name,
                    'fcr': scenario.fcr_model.name,
                    'mortality': scenario.mortality_model.name
                }
            }
            
            if latest_projection:
                scenario_data['final_state'] = {
                    'weight': float(latest_projection.average_weight),
                    'population': float(latest_projection.population),
                    'biomass': float(latest_projection.biomass),
                    'total_feed': float(latest_projection.cumulative_feed),
                    'survival_rate': (latest_projection.population / scenario.initial_count * 100)
                }
            
            comparison_data['scenarios'].append(scenario_data)
        
        # Calculate comparison metrics
        for metric in self.validated_data['comparison_metrics']:
            comparison_data['metrics'][metric] = self._calculate_metric_comparison(
                comparison_data['scenarios'], 
                metric
            )
        
        return comparison_data
    
    def _calculate_metric_comparison(self, scenarios, metric):
        """Calculate comparison for specific metric."""
        values = []
        
        for scenario in scenarios:
            if 'final_state' in scenario:
                if metric == 'final_weight':
                    values.append({
                        'scenario': scenario['name'],
                        'value': scenario['final_state']['weight']
                    })
                elif metric == 'final_biomass':
                    values.append({
                        'scenario': scenario['name'],
                        'value': scenario['final_state']['biomass']
                    })
                elif metric == 'survival_rate':
                    values.append({
                        'scenario': scenario['name'],
                        'value': scenario['final_state']['survival_rate']
                    })
                # Add other metrics as needed
        
        return {
            'values': values,
            'best': max(values, key=lambda x: x['value']) if values else None,
            'worst': min(values, key=lambda x: x['value']) if values else None
        }


# Data Entry Serializers (keeping existing ones with minor enhancements)

class CSVUploadSerializer(serializers.Serializer):
    """Enhanced serializer for CSV file upload."""
    
    file = serializers.FileField()
    data_type = serializers.ChoiceField(
        choices=['temperature', 'fcr', 'mortality']
    )
    profile_name = serializers.CharField(max_length=255)
    validate_only = serializers.BooleanField(default=False)
    
    def validate_file(self, value):
        """Validate uploaded file is CSV."""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV")
        
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Try to decode and validate it's readable
        try:
            value.read().decode('utf-8')
            value.seek(0)  # Reset file pointer
        except Exception:
            raise serializers.ValidationError("File must be valid UTF-8 encoded CSV")
        
        return value
    
    def validate_profile_name(self, value):
        """Validate profile name uniqueness."""
        if TemperatureProfile.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                f"A temperature profile named '{value}' already exists"
            )
        return value


class DateRangeEntrySerializer(serializers.Serializer):
    """Serializer for date range entry."""
    
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    value = serializers.FloatField()
    
    def validate(self, data):
        """Validate date range."""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError(
                "Start date must be before end date"
            )
        
        # Check range isn't too long
        days = (data['end_date'] - data['start_date']).days
        if days > 365:
            raise serializers.ValidationError(
                "Date range cannot exceed 365 days"
            )
        
        return data


class BulkDateRangeSerializer(serializers.Serializer):
    """Serializer for bulk date range input."""
    
    profile_name = serializers.CharField(max_length=255)
    ranges = DateRangeEntrySerializer(many=True)
    merge_adjacent = serializers.BooleanField(default=True)
    fill_gaps = serializers.BooleanField(default=True)
    interpolation_method = serializers.ChoiceField(
        choices=['linear', 'previous', 'next', 'default'],
        default='linear'
    )
    default_value = serializers.FloatField(required=False, allow_null=True)
    
    def validate_ranges(self, value):
        """Validate ranges don't overlap."""
        if len(value) < 1:
            raise serializers.ValidationError(
                "At least one date range is required"
            )
        
        # Sort ranges by start date
        sorted_ranges = sorted(value, key=lambda x: x['start_date'])
        
        # Check for overlaps
        for i in range(1, len(sorted_ranges)):
            if sorted_ranges[i]['start_date'] <= sorted_ranges[i-1]['end_date']:
                raise serializers.ValidationError(
                    f"Date ranges overlap: {sorted_ranges[i-1]['end_date']} and {sorted_ranges[i]['start_date']}"
                )
        
        return value


class DataValidationResultSerializer(serializers.Serializer):
    """Serializer for data validation results."""
    
    success = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    preview_data = serializers.ListField()
    summary = serializers.DictField(required=False)


class CSVTemplateRequestSerializer(serializers.Serializer):
    """Serializer for CSV template download request."""
    
    data_type = serializers.ChoiceField(
        choices=['temperature', 'fcr', 'mortality']
    )
    include_sample_data = serializers.BooleanField(default=False)


# Scenario duplication and batch initialization serializers

class ScenarioDuplicateSerializer(serializers.Serializer):
    """Serializer for duplicating a scenario."""
    
    new_name = serializers.CharField(max_length=255)
    include_projections = serializers.BooleanField(default=False)
    include_model_changes = serializers.BooleanField(default=True)
    
    def validate_new_name(self, value):
        """Ensure new name is unique for user."""
        user = self.context.get('request').user
        if Scenario.objects.filter(name=value, created_by=user).exists():
            raise serializers.ValidationError(
                "You already have a scenario with this name"
            )
        return value


class BatchInitializationSerializer(serializers.Serializer):
    """Serializer for initializing scenario from batch."""
    
    batch_id = serializers.IntegerField()
    scenario_name = serializers.CharField(max_length=255)
    duration_days = serializers.IntegerField(min_value=1, max_value=1200)
    use_current_models = serializers.BooleanField(
        default=True,
        help_text="Use batch's current location and conditions for model selection"
    )
    
    def validate_batch_id(self, value):
        """Validate batch exists and is accessible."""
        from apps.batch.models import Batch
        
        try:
            batch = Batch.objects.get(pk=value)
            # Could add permission checks here
            return batch
        except Batch.DoesNotExist:
            raise serializers.ValidationError("Batch not found")
    
    def create_scenario_from_batch(self, validated_data):
        """Create scenario initialized from batch data."""
        batch = validated_data['batch_id']
        
        # Get current batch state
        current_assignment = batch.container_assignments.filter(
            is_active=True
        ).first()
        
        if not current_assignment:
            raise serializers.ValidationError(
                "Batch has no active container assignment"
            )
        
        # Extract initial conditions
        initial_data = {
            'name': validated_data['scenario_name'],
            'duration_days': validated_data['duration_days'],
            'initial_count': current_assignment.population_count,
            'initial_weight': float(current_assignment.avg_weight_g) if current_assignment.avg_weight_g else None,
            'batch': batch,
            'genotype': batch.species.name if hasattr(batch, 'species') else 'Unknown',
            'supplier': 'Internal',
            'start_date': date.today()
        }
        
        # Select appropriate models based on location
        if validated_data['use_current_models']:
            # Logic to select TGC model based on container location
            # This is simplified - would need actual location mapping
            initial_data['tgc_model'] = TGCModel.objects.first()  # Placeholder
            initial_data['fcr_model'] = FCRModel.objects.first()  # Placeholder
            initial_data['mortality_model'] = MortalityModel.objects.first()  # Placeholder
        
        return initial_data 
