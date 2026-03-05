"""
Serializer for the TransferAction model.

This serializer handles the conversion between JSON and Django model instances
for transfer actions within workflows, including execution validation.
"""
from rest_framework import serializers
from apps.batch.models import TransferAction
from apps.batch.api.serializers.utils import NestedModelMixin
from typing import Dict, Any, Optional
from decimal import Decimal
from apps.environmental.models import EnvironmentalReading

SNAPSHOT_NOTE_PREFIX = "[transfer_snapshot]"


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
    dest_container_name = serializers.SerializerMethodField()
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
            'dest_container',
            'dest_container_name',
            'transferred_count',
            'mortality_during_transfer',
            'transferred_biomass_kg',
            'allow_mixed',
            'status',
            'leg_type',
            'created_via',
            'status_display',
            'planned_date',
            'actual_execution_date',
            'executed_at',
            'transfer_method',
            'transfer_method_display',
            'executed_by',
            'executed_by_username',
        ]
        read_only_fields = [
            'actual_execution_date',
            'executed_by',
        ]

    def get_dest_container_name(self, obj):
        if obj.dest_assignment and obj.dest_assignment.container:
            return str(obj.dest_assignment.container)
        if obj.dest_container:
            return str(obj.dest_container)
        return None


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
    source_readings_snapshot = serializers.SerializerMethodField()
    dest_readings_snapshot = serializers.SerializerMethodField()
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
            'is_dynamic_execution': 'is_dynamic_execution',
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
            'carrier_type': (
                assignment.container.carrier.carrier_type
                if assignment.container and assignment.container.carrier
                else None
            ),
            'location_type': (
                'SEA'
                if assignment.container and assignment.container.area_id
                else 'STATION'
                if assignment.container and assignment.container.hall_id
                else 'CARRIER'
                if assignment.container and assignment.container.carrier_id
                else None
            ),
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
        """Get destination assignment/container information."""
        assignment = obj.dest_assignment
        container = assignment.container if assignment else obj.dest_container
        if not container:
            return None

        return {
            'id': assignment.id if assignment else None,
            'container_id': container.id,
            'container_name': str(container),
            'carrier_type': (
                container.carrier.carrier_type
                if container and container.carrier
                else None
            ),
            'location_type': (
                'SEA'
                if container and container.area_id
                else 'STATION'
                if container and container.hall_id
                else 'CARRIER'
                if container and container.carrier_id
                else None
            ),
            'population_count': assignment.population_count if assignment else None,
            'avg_weight_g': (
                float(assignment.avg_weight_g)
                if assignment and assignment.avg_weight_g else None
            ),
            'biomass_kg': (
                float(assignment.biomass_kg)
                if assignment and assignment.biomass_kg else None
            ),
        }

    def _get_snapshot(self, obj, side: str):
        assignment = obj.source_assignment if side == 'source' else obj.dest_assignment
        container_id = None
        container_name = None
        if assignment:
            container_id = assignment.container_id
            container_name = str(assignment.container)
        elif side == "dest" and obj.dest_container_id:
            container_id = obj.dest_container_id
            container_name = str(obj.dest_container)

        if not container_id:
            return None

        marker = f"{SNAPSHOT_NOTE_PREFIX} action={obj.id};side={side};"
        query = EnvironmentalReading.objects.filter(
            container_id=container_id,
            notes__contains=marker,
        )
        if assignment:
            query = query.filter(batch_container_assignment=assignment)
        readings = query.select_related("parameter").order_by("parameter__name", "-reading_time")
        if not readings:
            return None

        captured_at = max(reading.reading_time for reading in readings)
        return {
            'captured_at': captured_at,
            'container_id': container_id,
            'container_name': container_name,
            'readings': [
                {
                    'parameter_id': reading.parameter_id,
                    'parameter_name': reading.parameter.name,
                    'unit': reading.parameter.unit,
                    'value': float(reading.value),
                    'reading_time': reading.reading_time,
                }
                for reading in readings
            ],
        }

    def get_source_readings_snapshot(self, obj):
        return self._get_snapshot(obj, 'source')

    def get_dest_readings_snapshot(self, obj):
        return self._get_snapshot(obj, 'dest')

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
        if workflow and workflow.is_dynamic_execution:
            errors['workflow'] = (
                "Dynamic workflow action creation is deprecated. "
                "Use start/complete handoff endpoints."
            )
        elif workflow and not workflow.can_add_actions():
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

        if not data.get("dest_assignment") and not data.get("dest_container"):
            errors["dest_container"] = (
                "Destination assignment or destination container is required."
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


class TransferActionSnapshotSerializer(serializers.Serializer):
    """Serializer for capturing point-in-time transport snapshots."""

    moment = serializers.ChoiceField(
        choices=[
            ("start", "Start"),
            ("in_transit", "In Transit"),
            ("finish", "Finish"),
        ],
        required=True,
        help_text="Snapshot moment to capture for this transfer handoff.",
    )


class TransferStartManualReadingsSerializer(serializers.Serializer):
    """Optional manual env readings entered at transfer start."""

    oxygen = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
    )
    temperature = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
    )
    co2 = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
    )


class TransferHandoffStartSerializer(serializers.Serializer):
    """Serializer for dynamic handoff start requests."""

    leg_type = serializers.ChoiceField(
        choices=TransferAction.LEG_TYPE_CHOICES,
        required=True,
    )
    source_assignment_id = serializers.IntegerField(min_value=1, required=True)
    dest_container_id = serializers.IntegerField(min_value=1, required=True)
    planned_transferred_count = serializers.IntegerField(min_value=1, required=True)
    planned_transferred_biomass_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
    )
    transfer_method = serializers.ChoiceField(
        choices=TransferAction.TRANSFER_METHOD_CHOICES,
        required=False,
    )
    allow_mixed = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    allow_compliance_override = serializers.BooleanField(required=False, default=False)
    compliance_override_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    source_manual_readings = TransferStartManualReadingsSerializer(
        required=False,
        default=dict,
    )
    dest_manual_readings = TransferStartManualReadingsSerializer(
        required=False,
        default=dict,
    )

    def validate(self, attrs):
        if attrs.get("allow_compliance_override") and not (
            attrs.get("compliance_override_note") or ""
        ).strip():
            raise serializers.ValidationError(
                {
                    "compliance_override_note": (
                        "Compliance override note is required when override is enabled."
                    )
                }
            )
        return attrs


class TransferHandoffCompleteSerializer(serializers.Serializer):
    """Serializer for dynamic handoff completion payload."""

    transferred_count = serializers.IntegerField(min_value=1, required=True)
    transferred_biomass_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
    )
    mortality_during_transfer = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )
    transfer_method = serializers.ChoiceField(
        choices=TransferAction.TRANSFER_METHOD_CHOICES,
        required=False,
    )
    water_temp_c = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
    )
    oxygen_level = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
    )
    execution_duration_minutes = serializers.IntegerField(
        required=False,
        min_value=0,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


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
