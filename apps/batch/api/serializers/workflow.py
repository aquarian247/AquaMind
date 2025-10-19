"""
Serializer for the BatchTransferWorkflow model.

This serializer handles the conversion between JSON and Django model instances
for batch transfer workflows, including nested action serialization.
"""
from rest_framework import serializers
from apps.batch.models import BatchTransferWorkflow
from apps.batch.api.serializers.utils import NestedModelMixin
from typing import Dict, Any, Optional


class BatchTransferWorkflowListSerializer(
    NestedModelMixin,
    serializers.ModelSerializer
):
    """Lightweight serializer for workflow list views."""

    batch_number = serializers.StringRelatedField(
        source='batch', read_only=True
    )
    workflow_type_display = serializers.CharField(
        source='get_workflow_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    source_stage_name = serializers.StringRelatedField(
        source='source_lifecycle_stage', read_only=True
    )
    dest_stage_name = serializers.StringRelatedField(
        source='dest_lifecycle_stage', read_only=True
    )
    initiated_by_username = serializers.StringRelatedField(
        source='initiated_by', read_only=True
    )

    class Meta:
        model = BatchTransferWorkflow
        fields = [
            'id',
            'workflow_number',
            'batch',
            'batch_number',
            'workflow_type',
            'workflow_type_display',
            'status',
            'status_display',
            'source_lifecycle_stage',
            'source_stage_name',
            'dest_lifecycle_stage',
            'dest_stage_name',
            'planned_start_date',
            'planned_completion_date',
            'actual_start_date',
            'actual_completion_date',
            'total_actions_planned',
            'actions_completed',
            'completion_percentage',
            'is_intercompany',
            'initiated_by',
            'initiated_by_username',
            'created_at',
        ]
        read_only_fields = [
            'workflow_number',
            'actual_start_date',
            'actual_completion_date',
            'total_actions_planned',
            'actions_completed',
            'completion_percentage',
            'created_at',
        ]


class BatchTransferWorkflowDetailSerializer(
    NestedModelMixin,
    serializers.ModelSerializer
):
    """Full serializer for workflow detail views with nested actions."""

    batch_number = serializers.StringRelatedField(
        source='batch', read_only=True
    )
    batch_info = serializers.SerializerMethodField()
    workflow_type_display = serializers.CharField(
        source='get_workflow_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    source_stage_name = serializers.StringRelatedField(
        source='source_lifecycle_stage', read_only=True
    )
    dest_stage_name = serializers.StringRelatedField(
        source='dest_lifecycle_stage', read_only=True
    )
    initiated_by_username = serializers.StringRelatedField(
        source='initiated_by', read_only=True
    )
    completed_by_username = serializers.StringRelatedField(
        source='completed_by', read_only=True
    )
    # Actions will be serialized via nested serializer
    actions = serializers.SerializerMethodField()

    class Meta:
        model = BatchTransferWorkflow
        fields = '__all__'
        read_only_fields = [
            'workflow_number',
            'actual_start_date',
            'actual_completion_date',
            'total_source_count',
            'total_transferred_count',
            'total_mortality_count',
            'total_biomass_kg',
            'total_actions_planned',
            'actions_completed',
            'completion_percentage',
            'created_at',
            'updated_at',
        ]

    def get_batch_info(self, obj) -> Optional[Dict[str, Any]]:
        """Get detailed batch information."""
        return self.get_nested_info(obj, 'batch', {
            'id': 'id',
            'batch_number': 'batch_number',
            'species_name': 'species.name',
            'lifecycle_stage': 'lifecycle_stage.name',
        })

    def get_actions(self, obj):
        """Get workflow actions with lightweight serialization."""
        from apps.batch.api.serializers.workflow_action import (
            TransferActionListSerializer
        )
        actions = obj.actions.all().order_by('action_number')
        return TransferActionListSerializer(actions, many=True).data

    def validate(self, data):
        """
        Validate workflow data including:
        - Batch exists
        - Lifecycle stages valid
        - Dates in order
        """
        errors = {}

        # Validate date order
        if 'planned_start_date' in data and 'planned_completion_date' in data:
            if data['planned_completion_date']:
                if (data['planned_completion_date'] <
                        data['planned_start_date']):
                    errors['planned_completion_date'] = (
                        "Completion date cannot be before start date"
                    )

        # Validate lifecycle stages for transition workflows
        if data.get('workflow_type') == 'LIFECYCLE_TRANSITION':
            if not data.get('dest_lifecycle_stage'):
                errors['dest_lifecycle_stage'] = (
                    "Destination lifecycle stage required for "
                    "lifecycle transitions"
                )

        if errors:
            raise serializers.ValidationError(errors)

        return data


class BatchTransferWorkflowCreateSerializer(
    BatchTransferWorkflowDetailSerializer
):
    """
    Serializer for creating workflows.
    Auto-generates workflow_number.
    """

    def create(self, validated_data):
        """Create workflow with auto-generated workflow number."""
        # Generate workflow number
        from django.utils import timezone
        year = timezone.now().year
        
        # Get next sequential number for this year
        last_workflow = (
            BatchTransferWorkflow.objects
            .filter(workflow_number__startswith=f'TRF-{year}-')
            .order_by('-workflow_number')
            .first()
        )
        
        if last_workflow:
            # Extract number and increment
            last_num = int(last_workflow.workflow_number.split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        workflow_number = f'TRF-{year}-{next_num:03d}'
        validated_data['workflow_number'] = workflow_number
        
        return super().create(validated_data)
