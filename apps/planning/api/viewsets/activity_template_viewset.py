from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.planning.models import ActivityTemplate
from apps.planning.api.serializers import (
    ActivityTemplateSerializer,
    PlannedActivitySerializer
)


class ActivityTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for ActivityTemplate model."""
    
    queryset = ActivityTemplate.objects.select_related('target_lifecycle_stage').all()
    serializer_class = ActivityTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['activity_type', 'trigger_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    @action(detail=True, methods=['post'], url_path='generate-for-batch')
    def generate_for_batch(self, request, pk=None):
        """Generate a PlannedActivity from this template for a specific batch."""
        template = self.get_object()
        
        scenario_id = request.data.get('scenario')
        batch_id = request.data.get('batch')
        override_due_date = request.data.get('override_due_date')
        
        if not scenario_id or not batch_id:
            return Response(
                {"error": "scenario and batch are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.scenario.models import Scenario
            from apps.batch.models import Batch
            
            scenario = Scenario.objects.get(scenario_id=scenario_id)
            batch = Batch.objects.get(id=batch_id)
            
            activity = template.generate_activity(
                scenario=scenario,
                batch=batch,
                override_due_date=override_due_date
            )
            
            serializer = PlannedActivitySerializer(activity)
            return Response({
                "message": "Activity generated from template",
                "activity": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Scenario.DoesNotExist:
            return Response(
                {"error": "Scenario not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Batch.DoesNotExist:
            return Response(
                {"error": "Batch not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

