"""
ViewSet for Creation Actions (egg delivery actions).

Provides CRUD operations and execution functionality for individual delivery actions.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import CreationAction
from apps.batch.api.serializers.workflow_creation_action import (
    CreationActionSerializer,
    CreationActionCreateSerializer,
    CreationActionExecuteSerializer,
    CreationActionSkipSerializer,
)


@extend_schema_view(
    list=extend_schema(
        operation_id='listCreationActions',
        summary='List creation actions',
        description='Get a list of egg delivery actions with filtering options.',
        parameters=[
            OpenApiParameter('workflow', OpenApiTypes.INT, description='Filter by workflow ID'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by action status'),
        ],
        tags=['batch']
    ),
    retrieve=extend_schema(
        operation_id='retrieveCreationAction',
        summary='Get action details',
        description='Retrieve detailed information about a specific creation action.',
        tags=['batch']
    ),
    create=extend_schema(
        operation_id='createCreationAction',
        summary='Create new creation action',
        description='Add a new egg delivery action to a workflow. Creates placeholder container assignment.',
        tags=['batch']
    ),
)
class CreationActionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing creation actions (egg deliveries).
    
    Supports:
    - List/retrieve actions
    - Create action (with mixed batch validation)
    - Execute action (record delivery)
    - Skip action (if delivery cancelled)
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']  # No PUT
    
    def get_queryset(self):
        """Get actions with filtering and optimization."""
        queryset = CreationAction.objects.select_related(
            'workflow',
            'workflow__batch',
            'dest_assignment',
            'dest_assignment__container',
            'dest_assignment__container__container_type',
            'executed_by',
        )
        
        # Apply filters
        workflow_filter = self.request.query_params.get('workflow')
        if workflow_filter:
            queryset = queryset.filter(workflow_id=workflow_filter)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('workflow', 'action_number')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CreationActionCreateSerializer
        elif self.action == 'execute':
            return CreationActionExecuteSerializer
        elif self.action == 'skip':
            return CreationActionSkipSerializer
        return CreationActionSerializer
    
    def get_serializer_context(self):
        """Add action instance to context for validation."""
        context = super().get_serializer_context()
        if self.action == 'execute' and hasattr(self, 'get_object'):
            try:
                context['action'] = self.get_object()
            except:
                pass
        return context
    
    @extend_schema(
        operation_id='executeCreationAction',
        summary='Execute delivery action',
        description=(
            'Record the actual delivery of eggs to a container. '
            'Updates destination assignment population, tracks mortality, '
            'and progresses workflow status.'
        ),
        request=CreationActionExecuteSerializer,
        responses={
            200: CreationActionSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=['batch']
    )
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Execute this delivery action.
        
        Records:
        - Mortality on arrival
        - Delivery method and conditions
        - Water temperature and egg quality
        - Actual delivery date
        
        Updates:
        - Destination container population
        - Workflow progress
        - Batch status (PLANNED → RECEIVING on first action)
        """
        action_instance = self.get_object()
        serializer = CreationActionExecuteSerializer(
            data=request.data,
            context={'action': action_instance}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Execute the action
            execution_data = {
                **serializer.validated_data,
                'executed_by': request.user,
            }
            action_instance.execute(**execution_data)
            
            # Return updated action
            response_serializer = CreationActionSerializer(action_instance)
            return Response(response_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        operation_id='skipCreationAction',
        summary='Skip delivery action',
        description=(
            'Skip a delivery action (e.g. if delivery was cancelled). '
            'Action must be in PENDING status. Requires a reason.'
        ),
        request=CreationActionSkipSerializer,
        responses={
            200: CreationActionSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=['batch']
    )
    @action(detail=True, methods=['post'])
    def skip(self, request, pk=None):
        """
        Skip this action (e.g. delivery cancelled).
        
        Action must be PENDING.
        Requires a reason for audit trail.
        """
        action_instance = self.get_object()
        serializer = CreationActionSkipSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            action_instance.skip(
                reason=serializer.validated_data['reason'],
                user=request.user
            )
            
            response_serializer = CreationActionSerializer(action_instance)
            return Response(response_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

