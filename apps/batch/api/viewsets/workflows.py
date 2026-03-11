"""
Batch transfer workflow viewsets.

These viewsets provide CRUD operations and custom actions for batch transfer
workflow management with state machine transitions.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.batch.models import BatchTransferWorkflow
from apps.batch.api.serializers import (
    BatchTransferWorkflowListSerializer,
    BatchTransferWorkflowDetailSerializer,
    BatchTransferWorkflowCreateSerializer,
    TransferActionDetailSerializer,
    TransferHandoffStartSerializer,
)
from apps.batch.api.filters.workflows import BatchTransferWorkflowFilter
from apps.batch.services.dynamic_execution import (
    build_execution_context,
    start_dynamic_handoff,
)


def _validation_error_payload(exc: DjangoValidationError):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "messages"):
        return {"error": exc.messages}
    return {"error": str(exc)}


class BatchTransferWorkflowViewSet(
    HistoryReasonMixin,
    viewsets.ModelViewSet
):
    """
    API endpoint for managing Batch Transfer Workflows.

    Batch transfer workflows orchestrate multi-step transfer operations that
    may take days or weeks to complete. They manage multiple TransferAction
    instances and track progress, completion, and finance integration.

    **State Machine:**
    - DRAFT: Initial creation, can add/modify actions
    - PLANNED: Finalized, ready to execute actions
    - IN_PROGRESS: At least one action executed
    - COMPLETED: All actions completed
    - CANCELLED: Workflow cancelled

    **Filtering:**
    - `batch`: ID of the batch being transferred
    - `workflow_type`: Type (LIFECYCLE_TRANSITION, CONTAINER_REDISTRIBUTION,
      etc.)
    - `status`: Workflow status
    - `is_intercompany`: Whether crosses subsidiary boundaries
    - `is_dynamic_execution`: Whether actions are created during execution
    - `planned_start_date`: Filter by planned start date

    **Searching:**
    - `workflow_number`: Workflow identifier
    - `batch__batch_number`: Batch number
    - `notes`: Workflow notes

    **Ordering:**
    - `planned_start_date` (default: descending)
    - `created_at`
    - `workflow_number`
    - `status`
    """

    queryset = BatchTransferWorkflow.objects.select_related(
        'batch',
        'source_lifecycle_stage',
        'dest_lifecycle_stage',
        'initiated_by',
        'completed_by',
    ).prefetch_related('actions')
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = BatchTransferWorkflowFilter
    filterset_fields = [
        'batch',
        'workflow_type',
        'status',
        'is_intercompany',
        'is_dynamic_execution',
        'dynamic_route_mode',
    ]
    search_fields = [
        'workflow_number',
        'batch__batch_number',
        'notes',
    ]
    ordering_fields = [
        'planned_start_date',
        'created_at',
        'workflow_number',
        'status',
        'completion_percentage',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BatchTransferWorkflowListSerializer
        elif self.action == 'create':
            return BatchTransferWorkflowCreateSerializer
        return BatchTransferWorkflowDetailSerializer

    def perform_create(self, serializer):
        """Auto-set initiated_by to current user."""
        serializer.save(initiated_by=self.request.user)

    @extend_schema(
        summary="Finalize workflow to PLANNED status",
        description=(
            "Transitions workflow from DRAFT to PLANNED status. "
            "Workflow must have at least one action. "
            "After planning, actions can be executed."
        ),
        request=None,
        responses={
            200: BatchTransferWorkflowDetailSerializer,
            400: {'description': 'Invalid state or no actions'},
        }
    )
    @action(detail=True, methods=['post'])
    def plan(self, request, pk=None):
        """
        Finalize workflow to PLANNED status.

        Validates that workflow has actions and transitions to PLANNED.
        """
        workflow = self.get_object()

        try:
            workflow.plan_workflow()
            serializer = self.get_serializer(workflow)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Cancel workflow",
        description=(
            "Cancels workflow with reason. "
            "Cannot cancel if already completed or cancelled."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'reason': {
                        'type': 'string',
                        'description': 'Reason for cancellation'
                    }
                },
                'required': ['reason']
            }
        },
        responses={
            200: BatchTransferWorkflowDetailSerializer,
            400: {'description': 'Invalid state or missing reason'},
        }
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel workflow with reason.

        Request body:
        {
            "reason": "Reason for cancellation"
        }
        """
        workflow = self.get_object()
        reason = request.data.get('reason')

        if not reason:
            return Response(
                {'error': 'Cancellation reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            workflow.cancel_workflow(reason, request.user)
            serializer = self.get_serializer(workflow)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Force complete workflow",
        description=(
            "Manually marks workflow as completed. "
            "Use only if all actions are done manually."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "completion_note": {"type": "string"},
                },
            }
        },
        responses={
            200: BatchTransferWorkflowDetailSerializer,
            400: {'description': 'Invalid state'},
        }
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Force complete workflow.

        Only use if all actions are completed and workflow
        didn't auto-complete.
        """
        workflow = self.get_object()

        try:
            completion_note = (request.data.get("completion_note") or "").strip()
            if workflow.is_dynamic_execution:
                workflow.complete_dynamic(
                    completed_by=request.user,
                    completion_note=completion_note,
                )
            else:
                if workflow.status == 'COMPLETED':
                    return Response(
                        {'error': 'Workflow already completed'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                workflow.status = 'COMPLETED'
                workflow.completed_by = request.user
                workflow.save()
            serializer = self.get_serializer(workflow)
            return Response(serializer.data)
        except DjangoValidationError as exc:
            return Response(
                _validation_error_payload(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Complete dynamic workflow explicitly",
        description=(
            "Explicit completion endpoint for dynamic transfer workflows. "
            "Blocks completion while handoffs remain IN_PROGRESS and requires "
            "at least one completed handoff."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "completion_note": {"type": "string"},
                },
            }
        },
        responses={
            200: BatchTransferWorkflowDetailSerializer,
            400: {"description": "Validation error"},
        },
    )
    @action(detail=True, methods=["post"], url_path="complete-dynamic")
    def complete_dynamic(self, request, pk=None):
        workflow = self.get_object()
        try:
            completion_note = (request.data.get("completion_note") or "").strip()
            workflow.complete_dynamic(
                completed_by=request.user,
                completion_note=completion_note,
            )
            serializer = self.get_serializer(workflow)
            return Response(serializer.data)
        except DjangoValidationError as exc:
            return Response(
                _validation_error_payload(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Dynamic handoff start",
        description=(
            "Start a dynamic handoff in a dedicated two-step flow. Creates "
            "an IN_PROGRESS TransferAction and captures mandatory start "
            "compliance snapshots."
        ),
        request=TransferHandoffStartSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "action": {"type": "object"},
                    "snapshot_summary": {"type": "object"},
                },
            },
            400: {"description": "Validation error"},
        },
    )
    @action(detail=True, methods=["post"], url_path="handoffs/start")
    def handoffs_start(self, request, pk=None):
        workflow = self.get_object()
        serializer = TransferHandoffStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = start_dynamic_handoff(
                workflow=workflow,
                started_by=request.user,
                **serializer.validated_data,
            )
            return Response(
                {
                    "action": TransferActionDetailSerializer(result["action"]).data,
                    "snapshot_summary": result["snapshot_summary"],
                }
            )
        except DjangoValidationError as exc:
            return Response(
                _validation_error_payload(exc),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Dynamic execution context",
        description=(
            "Returns live sources, destination candidates, allowed legs, "
            "in-progress handoffs and progress details for the execution page."
        ),
        request=None,
        responses={
            200: {"type": "object"},
            400: {"description": "Validation error"},
        },
    )
    @action(detail=True, methods=["get"], url_path="execution-context")
    def execution_context(self, request, pk=None):
        workflow = self.get_object()
        try:
            return Response(build_execution_context(workflow))
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Detect intercompany transfer",
        description=(
            "Analyzes workflow actions to determine if transfer "
            "crosses subsidiary boundaries."
        ),
        request=None,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'is_intercompany': {'type': 'boolean'},
                    'source_subsidiary': {'type': 'string'},
                    'dest_subsidiary': {'type': 'string'},
                }
            },
        }
    )
    @action(detail=True, methods=['post'])
    def detect_intercompany(self, request, pk=None):
        """
        Detect if workflow crosses subsidiary boundaries.

        Analyzes container locations to determine if transfer
        is between FRESHWATER and FARMING subsidiaries.
        """
        workflow = self.get_object()

        is_intercompany = workflow.detect_intercompany()

        return Response({
            'is_intercompany': workflow.is_intercompany,
            'source_subsidiary': workflow.source_subsidiary,
            'dest_subsidiary': workflow.dest_subsidiary,
        })
