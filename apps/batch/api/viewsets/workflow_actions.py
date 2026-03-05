"""
Transfer action viewsets.

These viewsets provide CRUD operations and execution actions for individual
transfer actions within workflows.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.batch.models import TransferAction
from apps.batch.access import can_execute_transport_actions
from apps.batch.api.serializers import (
    TransferActionListSerializer,
    TransferActionDetailSerializer,
    TransferActionExecuteSerializer,
    TransferActionSnapshotSerializer,
    TransferHandoffCompleteSerializer,
    TransferActionSkipSerializer,
    TransferActionRollbackSerializer,
)
from apps.batch.api.filters.workflow_actions import TransferActionFilter


def _validation_error_payload(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "messages"):
        return {"error": exc.messages}
    return {"error": str(exc)}


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
        elif self.action == 'snapshot':
            return TransferActionSnapshotSerializer
        elif self.action == "complete_handoff":
            return TransferHandoffCompleteSerializer
        elif self.action == 'skip':
            return TransferActionSkipSerializer
        elif self.action == 'rollback':
            return TransferActionRollbackSerializer
        return TransferActionDetailSerializer

    def perform_create(self, serializer):
        """Block deprecated dynamic creation path; allow standard planned creation."""
        workflow = serializer.validated_data.get("workflow")
        if workflow and workflow.is_dynamic_execution:
            raise ValidationError(
                {
                    "workflow": (
                        "Dynamic workflow action creation is deprecated. "
                        "Use /transfer-workflows/{id}/handoffs/start/ and "
                        "/transfer-actions/{id}/complete-handoff/."
                    )
                }
            )
        serializer.save()

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

        if action_obj.requires_ship_crew_execution() and not can_execute_transport_actions(request.user):
            raise PermissionDenied(
                "Only SHIP_CREW or Logistics Operators can execute this transport action."
            )
        if action_obj.workflow.is_dynamic_execution:
            raise ValidationError(
                {
                    "detail": (
                        "Dynamic execute-handoff path is deprecated. "
                        "Use start/complete handoff endpoints."
                    )
                }
            )

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
        summary="Complete transfer handoff",
        description=(
            "Completes an IN_PROGRESS dynamic handoff by applying actual "
            "counts/biomass/mortality and marking action COMPLETED."
        ),
        request=TransferHandoffCompleteSerializer,
        responses={
            200: {"type": "object"},
            400: {"description": "Validation error"},
        },
    )
    @action(detail=True, methods=["post"], url_path="complete-handoff")
    def complete_handoff(self, request, pk=None):
        action_obj = self.get_object()

        if action_obj.requires_ship_crew_execution() and not can_execute_transport_actions(request.user):
            raise PermissionDenied(
                "Only SHIP_CREW or Logistics Operators can complete this transport action."
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = serializer.validated_data.copy()
            mortality = payload.pop("mortality_during_transfer", 0)
            result = action_obj.complete_handoff(
                executed_by=request.user,
                mortality_count=mortality,
                **payload,
            )
            return Response(result)
        except DjangoValidationError as exc:
            return Response(
                _validation_error_payload(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Capture transport snapshot readings",
        description=(
            "Capture mapped AVEVA historian readings for this transfer action "
            "at a specific moment (start, in_transit, finish)."
        ),
        request=TransferActionSnapshotSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'action_id': {'type': 'integer'},
                    'moment': {'type': 'string'},
                    'created_count': {'type': 'integer'},
                    'skipped_count': {'type': 'integer'},
                    'missing_value_count': {'type': 'integer'},
                },
            },
            400: {'description': 'Invalid action state or payload'},
            403: {'description': 'Forbidden'},
        },
    )
    @action(detail=True, methods=['post'])
    def snapshot(self, request, pk=None):
        """Capture historian snapshot readings for an in-progress transport handoff."""
        action_obj = self.get_object()

        if action_obj.requires_ship_crew_execution() and not can_execute_transport_actions(request.user):
            raise PermissionDenied(
                "Only SHIP_CREW or Logistics Operators can capture transport snapshots."
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from django.utils import timezone
            from apps.environmental.services.historian_snapshot import (
                snapshot_transfer_action_readings,
            )

            result = snapshot_transfer_action_readings(
                action_id=action_obj.id,
                reading_time=timezone.now(),
                executed_by_id=request.user.id,
                moment=serializer.validated_data['moment'],
            )
            return Response({
                'action_id': action_obj.id,
                **result,
            })
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
    permission_classes = [IsAuthenticated]
