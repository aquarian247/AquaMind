from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.planning.models import PlannedActivity
from apps.planning.api.serializers import PlannedActivitySerializer


class PlannedActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for PlannedActivity model."""
    
    queryset = PlannedActivity.objects.select_related(
        'scenario',
        'batch',
        'container',
        'created_by',
        'completed_by',
        'transfer_workflow'
    ).all()
    serializer_class = PlannedActivitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scenario', 'batch', 'activity_type', 'status', 'container']
    search_fields = ['notes', 'batch__batch_number']
    ordering_fields = ['due_date', 'created_at', 'status']
    ordering = ['due_date', 'created_at']
    
    def get_queryset(self):
        """Apply custom filters."""
        queryset = super().get_queryset()
        
        # Filter by overdue status
        if self.request.query_params.get('overdue') == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                status='PENDING',
                due_date__lt=timezone.now().date()
            )
        
        # Filter by date range
        due_date_after = self.request.query_params.get('due_date_after')
        due_date_before = self.request.query_params.get('due_date_before')
        
        if due_date_after:
            queryset = queryset.filter(due_date__gte=due_date_after)
        if due_date_before:
            queryset = queryset.filter(due_date__lte=due_date_before)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        """Mark activity as completed."""
        activity = self.get_object()
        
        if activity.status == 'COMPLETED':
            return Response(
                {"error": "Activity is already completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activity.mark_completed(user=request.user)
        
        serializer = self.get_serializer(activity)
        return Response({
            "message": "Activity marked as completed",
            "activity": serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='spawn-workflow')
    def spawn_workflow(self, request, pk=None):
        """Spawn a Transfer Workflow from this planned activity."""
        activity = self.get_object()
        
        if activity.activity_type != 'TRANSFER':
            return Response(
                {"error": "Can only spawn workflows from TRANSFER activities"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if activity.transfer_workflow:
            return Response(
                {"error": "Workflow already spawned for this activity"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract parameters from request
        workflow_type = request.data.get('workflow_type', 'LIFECYCLE_TRANSITION')
        source_stage_id = request.data.get('source_lifecycle_stage')
        dest_stage_id = request.data.get('dest_lifecycle_stage')
        
        if not source_stage_id or not dest_stage_id:
            return Response(
                {"error": "source_lifecycle_stage and dest_lifecycle_stage are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.batch.models import LifeCycleStage
            
            # Validate lifecycle stages exist
            source_stage = LifeCycleStage.objects.get(id=source_stage_id)
            dest_stage = LifeCycleStage.objects.get(id=dest_stage_id)
            
            workflow = activity.spawn_transfer_workflow(
                workflow_type=workflow_type,
                source_lifecycle_stage=source_stage,
                dest_lifecycle_stage=dest_stage
            )
        except LifeCycleStage.DoesNotExist as e:
            return Response(
                {"error": "Lifecycle stage not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.batch.api.serializers import BatchTransferWorkflowDetailSerializer
        serializer = BatchTransferWorkflowDetailSerializer(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

