"""
Serializers for ActualDailyAssignmentState (Growth Assimilation).

These serializers expose the computed daily states for the Growth Analysis page.

Issue: #112 - Phase 6 (API Endpoints)
"""
from rest_framework import serializers
from apps.batch.models import ActualDailyAssignmentState


class ActualDailyAssignmentStateSerializer(serializers.ModelSerializer):
    """
    Serializer for ActualDailyAssignmentState.
    
    Exposes daily computed states with full provenance tracking.
    Used for Growth Analysis chart (Actual series overlay).
    """
    # Add readable fields
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)
    container_name = serializers.CharField(source='assignment.container.name', read_only=True)
    
    class Meta:
        model = ActualDailyAssignmentState
        fields = [
            'id',
            'assignment_id',
            'container_name',
            'date',
            'day_number',
            'avg_weight_g',
            'population',
            'biomass_kg',
            'anchor_type',
            'sources',
            'confidence_scores',
            'lifecycle_stage',
            'observed_fcr',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # All fields are read-only (computed)


class ActualDailyAssignmentStateListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for lists (omits heavy JSON fields).
    
    Used for chart data where provenance details aren't needed.
    """
    assignment_id = serializers.IntegerField(source='assignment.id', read_only=True)
    container_name = serializers.CharField(source='assignment.container.name', read_only=True)
    
    class Meta:
        model = ActualDailyAssignmentState
        fields = [
            'date',
            'day_number',
            'avg_weight_g',
            'population',
            'biomass_kg',
            'anchor_type',
            'assignment_id',
            'container_name',
        ]
        read_only_fields = fields


class GrowthAnalysisCombinedSerializer(serializers.Serializer):
    """
    Combined response for Growth Analysis page.
    
    Returns all data needed to render the Growth Analysis chart:
    - Batch info
    - Growth samples (measured anchors)
    - Scenario projection (planned/modeled)
    - Actual daily states (assimilated reality)
    - Container assignments (for drilldown)
    
    This is a read-only response serializer (not bound to a model).
    """
    # Batch info
    batch_id = serializers.IntegerField()
    batch_number = serializers.CharField()
    species = serializers.CharField()
    lifecycle_stage = serializers.CharField()
    start_date = serializers.DateField()
    status = serializers.CharField()
    
    # Scenario info
    scenario = serializers.DictField(required=False, allow_null=True)
    projection_run = serializers.DictField(required=False, allow_null=True)
    
    # Time series data
    growth_samples = serializers.ListField(child=serializers.DictField())
    scenario_projection = serializers.ListField(child=serializers.DictField())
    actual_daily_states = serializers.ListField(child=serializers.DictField())
    
    # Container assignments (for drilldown)
    container_assignments = serializers.ListField(child=serializers.DictField())
    
    # Date range
    date_range = serializers.DictField()


class PinScenarioSerializer(serializers.Serializer):
    """
    Request serializer for pinning a scenario to a batch.
    
    POST /api/v1/batch/batches/{id}/pin-scenario/
    Body: {"scenario_id": 123}
    """
    scenario_id = serializers.IntegerField(required=True)
    
    def validate_scenario_id(self, value):
        """Validate scenario exists."""
        from apps.scenario.models import Scenario
        
        if not Scenario.objects.filter(scenario_id=value).exists():
            raise serializers.ValidationError(f"Scenario {value} does not exist")
        
        return value


class ManualRecomputeSerializer(serializers.Serializer):
    """
    Request serializer for manual recompute trigger (admin).
    
    POST /api/v1/batch/batches/{id}/recompute-daily-states/
    Body: {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "assignment_ids": [1, 2, 3]  // Optional
    }
    """
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    assignment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        help_text="Optional: Specific assignments to recompute. If not provided, all assignments recomputed."
    )
    
    def validate(self, data):
        """Validate date range."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date > end_date:
            raise serializers.ValidationError({
                'end_date': 'end_date must be after start_date'
            })
        
        return data

