"""
Transfer action viewsets.

These viewsets provide CRUD operations and execution actions for individual
transfer actions within workflows.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.batch.models import TransferAction
from apps.batch.api.serializers import (
    TransferActionListSerializer,
    TransferActionDetailSerializer,
    TransferActionExecuteSerializer,
    TransferActionSkipSerializer,
    TransferActionRollbackSerializer,
)
from apps.batch.api.filters.workflow_actions import TransferActionFilter


class TransferActionViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Transfer Actions.

    Transfer actions represent individual container-to-container fish
    movements within a workflow. Each action can be executed independently,
    tracking mortality, environmental conditions, and execution details.

    **State Machine:**
    - PENDING: Created, not yet executed
    - IN_PROGRESS: Currently being executed
    - COMPLETED: Successfully executed
    - FAILED: Execution failed, can be retried
    - SKIPPED: Manually skipped

    **Filtering:**
    - `workflow`: ID of parent workflow
    - `status`: Action status
    - `source_assignment`: Source container assignment
    - `dest_assignment`: Destination container assignment
    - `planned_date`: Filter by planned date

    **Searching:**
    - `workflow__workflow_number`: Workflow identifier
    - `notes`: Action notes

    **Ordering:**
    - `action_number` (default: ascending within workflow)
    - `planned_date`
    - `actual_execution_date`
    - `status`
    """

    queryset = TransferAction.objects.select_related(
        'workflow',
        'workflow__batch',
        'source_assignment',
        'source_assignment__container',
        'dest_assignment',
        'dest_assignment__container',
        'executed_by',
    )
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = TransferActionFilter
    filterset_fields = [
        'workflow',
        'status',
        'source_assignment',
        'dest_assignment',
    ]
    search_fields = [
        'workflow__workflow_number',
        'notes',
    ]
    ordering_fields = [
        'action_number',
        'planned_date',
        'actual_execution_date',
        'status',
    ]
    ordering = ['workflow', 'action_number']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TransferActionListSerializer
        elif self.action == 'execute':
            return TransferActionExecuteSerializer
        elif self.action == 'skip':
            return TransferActionSkipSerializer
        elif self.action == 'rollback':
            return TransferActionRollbackSerializer
        return TransferActionDetailSerializer

    @extend_schema(
        summary="Execute transfer action",
        description=(
            "Executes this transfer action, moving fish from source to "
            "destination container. Updates populations, marks action "
            "complete, and updates workflow progress."
        ),
        request=TransferActionExecuteSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'action_id': {'type': 'integer'},
                    'action_status': {'type': 'string'},
                    'workflow_status': {'type': 'string'},
                    'completion_percentage': {'type': 'number'},
                    'actions_remaining': {'type': 'integer'},
                }
            },
            400: {'description': 'Invalid state or validation error'},
        }
    )
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Execute this transfer action.

        Request body:
        {
            "mortality_during_transfer": 0,  # Optional, default 0
            "transfer_method": "NET",  # Optional
            "water_temp_c": 12.5,  # Optional
            "oxygen_level": 9.2,  # Optional
            "execution_duration_minutes": 45,  # Optional
            "notes": "Smooth transfer"  # Optional
        }

        Response includes action and workflow status updates.
        """
        action_obj = self.get_object()

        # Validate request data
        serializer = self.get_serializer(
            data=request.data,
            context={'action': action_obj}
        )
        serializer.is_valid(raise_exception=True)

        try:
            # Execute the action
            result = action_obj.execute(
                executed_by=request.user,
                **serializer.validated_data
            )
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Skip transfer action",
        description=(
            "Skips this transfer action with a reason. "
            "Action is marked as completed but not executed."
        ),
        request=TransferActionSkipSerializer,
        responses={
            200: TransferActionDetailSerializer,
            400: {'description': 'Invalid state or missing reason'},
        }
    )
    @action(detail=True, methods=['post'])
    def skip(self, request, pk=None):
        """
        Skip this transfer action.

        Request body:
        {
            "reason": "Reason for skipping"
        }
        """
        action_obj = self.get_object()

        # Validate request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            action_obj.skip(
                reason=serializer.validated_data['reason'],
                skipped_by=request.user
            )
            detail_serializer = TransferActionDetailSerializer(action_obj)
            return Response(detail_serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Rollback transfer action",
        description=(
            "Marks action as failed. Does NOT reverse database changes - "
            "manual intervention required."
        ),
        request=TransferActionRollbackSerializer,
        responses={
            200: TransferActionDetailSerializer,
            400: {'description': 'Invalid state or missing reason'},
        }
    )
    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """
        Rollback transfer action (mark as failed).

        Note: This does NOT reverse database changes.
        Manual intervention required to fix populations.

        Request body:
        {
            "reason": "Reason for rollback"
        }
        """
        action_obj = self.get_object()

        # Validate request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            action_obj.rollback(reason=serializer.validated_data['reason'])
            detail_serializer = TransferActionDetailSerializer(action_obj)
            return Response(detail_serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Retry failed action",
        description="Resets failed action to PENDING for retry.",
        request=None,
        responses={
            200: TransferActionDetailSerializer,
            400: {'description': 'Action not in FAILED state'},
        }
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """
        Retry failed action.

        Resets action from FAILED to PENDING.
        """
        action_obj = self.get_object()

        try:
            action_obj.retry()
            serializer = self.get_serializer(action_obj)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
