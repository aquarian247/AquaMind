"""
Serializer for the TransferAction model.

This serializer handles the conversion between JSON and Django model instances
for transfer actions within workflows, including execution validation.
"""
from rest_framework import serializers
from apps.batch.models import TransferAction
from apps.batch.api.serializers.utils import NestedModelMixin
from typing import Dict, Any, Optional


class TransferActionListSerializer(
    NestedModelMixin,
    serializers.ModelSerializer
):
    """Lightweight serializer for action list views."""

    workflow_number = serializers.StringRelatedField(
        source='workflow', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    transfer_method_display = serializers.CharField(
        source='get_transfer_method_display', read_only=True
    )
    source_container_name = serializers.StringRelatedField(
        source='source_assignment.container', read_only=True
    )
    dest_container_name = serializers.StringRelatedField(
        source='dest_assignment.container', read_only=True
    )
    executed_by_username = serializers.StringRelatedField(
        source='executed_by', read_only=True
    )

    class Meta:
        model = TransferAction
        fields = [
            'id',
            'workflow',
            'workflow_number',
            'action_number',
            'source_assignment',
            'source_container_name',
            'dest_assignment',
            'dest_container_name',
            'transferred_count',
            'mortality_during_transfer',
            'transferred_biomass_kg',
            'status',
            'status_display',
            'planned_date',
            'actual_execution_date',
            'transfer_method',
            'transfer_method_display',
            'executed_by',
            'executed_by_username',
        ]
        read_only_fields = [
            'actual_execution_date',
            'executed_by',
        ]


class TransferActionDetailSerializer(
    NestedModelMixin,
    serializers.ModelSerializer
):
    """Full serializer for action detail views."""

    workflow_number = serializers.StringRelatedField(
        source='workflow', read_only=True
    )
    workflow_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    transfer_method_display = serializers.CharField(
        source='get_transfer_method_display', read_only=True
    )
    source_assignment_info = serializers.SerializerMethodField()
    dest_assignment_info = serializers.SerializerMethodField()
    executed_by_username = serializers.StringRelatedField(
        source='executed_by', read_only=True
    )

    class Meta:
        model = TransferAction
        fields = '__all__'
        read_only_fields = [
            'actual_execution_date',
            'executed_by',
            'created_at',
            'updated_at',
        ]

    def get_workflow_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get parent workflow information."""
        return self.get_nested_info(obj, 'workflow', {
            'id': 'id',
            'workflow_number': 'workflow_number',
            'status': 'status',
            'batch_number': 'batch.batch_number',
        })

    def get_source_assignment_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get source assignment information."""
        if not obj.source_assignment:
            return None
        
        assignment = obj.source_assignment
        return {
            'id': assignment.id,
            'container_id': assignment.container_id,
            'container_name': str(assignment.container),
            'population_count': assignment.population_count,
            'avg_weight_g': (
                float(assignment.avg_weight_g)
                if assignment.avg_weight_g else None
            ),
            'biomass_kg': (
                float(assignment.biomass_kg)
                if assignment.biomass_kg else None
            ),
        }

    def get_dest_assignment_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get destination assignment information."""
        if not obj.dest_assignment:
            return None
        
        assignment = obj.dest_assignment
        return {
            'id': assignment.id,
            'container_id': assignment.container_id,
            'container_name': str(assignment.container),
            'population_count': assignment.population_count,
            'avg_weight_g': (
                float(assignment.avg_weight_g)
                if assignment.avg_weight_g else None
            ),
            'biomass_kg': (
                float(assignment.biomass_kg)
                if assignment.biomass_kg else None
            ),
        }

    def validate(self, data):
        """
        Validate action data including:
        - Transfer count valid
        - Source has enough fish
        - Action can be added to workflow
        """
        errors = {}

        # Validate workflow allows action addition
        workflow = data.get('workflow')
        if workflow and not workflow.can_add_actions():
            errors['workflow'] = (
                f"Cannot add actions to workflow in {workflow.status} status"
            )

        # Validate transfer count
        if 'transferred_count' in data:
            transferred_count = data['transferred_count']
            if transferred_count <= 0:
                errors['transferred_count'] = (
                    "Transfer count must be greater than zero"
                )
            
            # Validate against source population
            source_assignment = data.get('source_assignment')
            if source_assignment:
                available = source_assignment.population_count
                if transferred_count > available:
                    errors['transferred_count'] = (
                        f"Transfer count ({transferred_count}) exceeds "
                        f"available population ({available})"
                    )

        # Validate biomass
        if 'transferred_biomass_kg' in data:
            if data['transferred_biomass_kg'] <= 0:
                errors['transferred_biomass_kg'] = (
                    "Transferred biomass must be greater than zero"
                )

        if errors:
            raise serializers.ValidationError(errors)

        return data


class TransferActionExecuteSerializer(serializers.Serializer):
    """Serializer for executing a transfer action."""

    mortality_during_transfer = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Number of mortalities during transfer"
    )
    transfer_method = serializers.ChoiceField(
        choices=TransferAction.TRANSFER_METHOD_CHOICES,
        required=False,
        help_text="Method used for transfer"
    )
    water_temp_c = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Water temperature during transfer (°C)"
    )
    oxygen_level = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text="Oxygen level during transfer (mg/L)"
    )
    execution_duration_minutes = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Duration of transfer in minutes"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes about the execution"
    )

    def validate_mortality_during_transfer(self, value):
        """Validate mortality doesn't exceed transfer count."""
        # Get action from context
        action = self.context.get('action')
        if action and value > action.transferred_count:
            raise serializers.ValidationError(
                f"Mortality ({value}) cannot exceed "
                f"transfer count ({action.transferred_count})"
            )
        return value


class TransferActionSkipSerializer(serializers.Serializer):
    """Serializer for skipping a transfer action."""

    reason = serializers.CharField(
        required=True,
        help_text="Reason for skipping this action"
    )


class TransferActionRollbackSerializer(serializers.Serializer):
    """Serializer for rolling back a transfer action."""

    reason = serializers.CharField(
        required=True,
        help_text="Reason for rollback"
    )
