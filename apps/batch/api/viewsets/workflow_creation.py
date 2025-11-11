"""
ViewSet for Batch Creation Workflows.

Provides CRUD operations and custom actions for managing batch creation workflows.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import BatchCreationWorkflow, CreationAction
from apps.batch.api.serializers.workflow_creation import (
    BatchCreationWorkflowListSerializer,
    BatchCreationWorkflowDetailSerializer,
    BatchCreationWorkflowCreateSerializer,
    BatchCreationWorkflowCancelSerializer,
)


@extend_schema_view(
    list=extend_schema(
        operation_id='listBatchCreationWorkflows',
        summary='List batch creation workflows',
        description='Get a list of all batch creation workflows with filtering options.',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by workflow status'),
            OpenApiParameter('egg_source_type', OpenApiTypes.STR, description='Filter by egg source type (INTERNAL/EXTERNAL)'),
            OpenApiParameter('batch', OpenApiTypes.INT, description='Filter by batch ID'),
        ],
        tags=['batch']
    ),
    retrieve=extend_schema(
        operation_id='retrieveBatchCreationWorkflow',
        summary='Get workflow details',
        description='Retrieve detailed information about a specific batch creation workflow.',
        tags=['batch']
    ),
    create=extend_schema(
        operation_id='createBatchCreationWorkflow',
        summary='Create new batch creation workflow',
        description='Create a new workflow and automatically create the associated batch with PLANNED status.',
        tags=['batch']
    ),
)
class BatchCreationWorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing batch creation workflows.
    
    Supports:
    - List/retrieve workflows
    - Create workflow (auto-creates batch)
    - Plan workflow (lock for execution)
    - Cancel workflow (if no actions executed)
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get workflows with filtering and optimization."""
        queryset = BatchCreationWorkflow.objects.select_related(
            'batch',
            'batch__species',
            'batch__lifecycle_stage',
            'egg_production',
            'external_supplier',
            'created_by',
            'cancelled_by',
        ).prefetch_related(
            Prefetch(
                'actions',
                queryset=CreationAction.objects.select_related(
                    'dest_assignment__container'
                ).order_by('action_number')
            )
        )
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        egg_source_filter = self.request.query_params.get('egg_source_type')
        if egg_source_filter:
            queryset = queryset.filter(egg_source_type=egg_source_filter)
        
        batch_filter = self.request.query_params.get('batch')
        if batch_filter:
            queryset = queryset.filter(batch_id=batch_filter)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BatchCreationWorkflowListSerializer
        elif self.action == 'create':
            return BatchCreationWorkflowCreateSerializer
        elif self.action == 'cancel':
            return BatchCreationWorkflowCancelSerializer
        return BatchCreationWorkflowDetailSerializer
    
    def perform_create(self, serializer):
        """Set created_by user on workflow creation."""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        operation_id='planBatchCreationWorkflow',
        summary='Plan workflow',
        description=(
            'Lock workflow for execution by changing status from DRAFT to PLANNED. '
            'Requires at least one action to be added first.'
        ),
        request=None,
        responses={
            200: BatchCreationWorkflowDetailSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=['batch']
    )
    @action(detail=True, methods=['post'])
    def plan(self, request, pk=None):
        """
        Plan the workflow (transition from DRAFT to PLANNED).
        
        Validates that workflow has actions before planning.
        """
        workflow = self.get_object()
        
        if not workflow.can_plan():
            return Response(
                {
                    'error': 'Cannot plan workflow',
                    'details': (
                        f'Workflow must be in DRAFT status and have at least one action. '
                        f'Current status: {workflow.status}, Actions: {workflow.total_actions}'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow.status = 'PLANNED'
        workflow.save(update_fields=['status'])
        
        serializer = BatchCreationWorkflowDetailSerializer(workflow)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='cancelBatchCreationWorkflow',
        summary='Cancel workflow',
        description=(
            'Cancel a workflow if no actions have been executed. '
            'Once eggs are delivered, workflow cannot be cancelled '
            '(physical eggs must be managed through normal batch operations).'
        ),
        request=BatchCreationWorkflowCancelSerializer,
        responses={
            200: BatchCreationWorkflowDetailSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=['batch']
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel the workflow.
        
        Can only cancel if no actions have been executed.
        Requires a cancellation reason.
        """
        workflow = self.get_object()
        serializer = BatchCreationWorkflowCancelSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            workflow.cancel(
                reason=serializer.validated_data['reason'],
                user=request.user
            )
            
            response_serializer = BatchCreationWorkflowDetailSerializer(workflow)
            return Response(response_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

