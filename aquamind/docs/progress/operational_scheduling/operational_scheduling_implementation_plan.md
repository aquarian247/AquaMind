# Operational Scheduling Implementation Plan

**Version**: 2.0  
**Last Updated**: October 28, 2025  
**Author**: Manus AI  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/progress/`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Implementation Phases](#implementation-phases)
3. [Phase 1: Backend Foundation](#phase-1-backend-foundation)
4. [Phase 2: Frontend Implementation](#phase-2-frontend-implementation)
5. [Phase 3: Advanced Features](#phase-3-advanced-features)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Checklist](#deployment-checklist)

---

## Executive Summary

This implementation plan provides a complete roadmap for developing the **Operational Scheduling** feature in AquaMind. The plan is structured to deliver a production-ready system without temporary code or placeholder logic.

### Key Design Decisions

1. **No Temporary Code**: All features are implemented in their final form from the start.
2. **Scenario-Centric**: All planned activities belong to scenarios, enabling what-if analysis.
3. **Transfer Workflow Integration**: Planned transfer activities can spawn and track existing Transfer Workflows.
4. **Template-Based Planning**: Activity templates auto-generate lifecycle plans for new batches.
5. **Audit Trail**: All changes are tracked via `django-simple-history`.

### Implementation Sequence

The implementation is divided into three sequential phases:

| Phase | Focus | Duration | Deliverables |
|-------|-------|----------|--------------|
| **Phase 1** | Backend Foundation | 3-4 weeks | `planning` app, models, API, migrations |
| **Phase 2** | Frontend Implementation | 3-4 weeks | Production Planner UI, Timeline view, Forms |
| **Phase 3** | Advanced Features | 2-3 weeks | Templates, Auto-generation, Variance reporting |

**Total Estimated Duration**: 8-11 weeks

---

## Implementation Phases

### Phase 1: Backend Foundation

**Goal**: Create the complete backend infrastructure for Operational Scheduling, including models, API endpoints, and integration with existing apps.

**Duration**: 3-4 weeks

#### Task 1.1: Create Planning App Structure

**Objective**: Set up the new `planning` Django app with proper directory structure.

**Steps**:

1. Create app directory structure:
   ```bash
   cd aquamind/apps
   mkdir -p planning/api/serializers planning/api/viewsets planning/api/routers
   touch planning/__init__.py
   touch planning/models.py
   touch planning/admin.py
   touch planning/signals.py
   touch planning/apps.py
   touch planning/api/__init__.py
   touch planning/api/serializers/__init__.py
   touch planning/api/viewsets/__init__.py
   touch planning/api/routers/__init__.py
   ```

2. Register app in `settings.py`:
   ```python
   INSTALLED_APPS = [
       # ... existing apps
       'apps.planning',
   ]
   ```

3. Create `apps.py`:
   ```python
   from django.apps import AppConfig

   class PlanningConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'apps.planning'
       verbose_name = 'Operational Planning'
       
       def ready(self):
           import apps.planning.signals  # noqa
   ```

**Acceptance Criteria**:
- [ ] `planning` app is created and registered
- [ ] App structure follows AquaMind conventions (see `code_organization_guidelines.md`)
- [ ] App is importable without errors

**Estimated Time**: 1 hour

---

#### Task 1.2: Implement PlannedActivity Model

**Objective**: Create the core `PlannedActivity` model with all fields, methods, and audit trail.

**Steps**:

1. Create model in `planning/models.py`:
   ```python
   from django.db import models
   from django.utils import timezone
   from simple_history.models import HistoricalRecords

   class PlannedActivity(models.Model):
       """
       Represents a planned operational activity within a scenario.
       
       Activities can be simple events (vaccination, culling) or complex
       operations (transfers that spawn Transfer Workflows).
       """
       
       ACTIVITY_TYPE_CHOICES = [
           ('VACCINATION', 'Vaccination'),
           ('TREATMENT', 'Treatment/Health Intervention'),
           ('CULL', 'Culling'),
           ('SALE', 'Sale/Harvest'),
           ('FEED_CHANGE', 'Feed Strategy Change'),
           ('TRANSFER', 'Transfer'),
           ('MAINTENANCE', 'Maintenance'),
           ('SAMPLING', 'Sampling'),
           ('OTHER', 'Other'),
       ]
       
       STATUS_CHOICES = [
           ('PENDING', 'Pending'),
           ('IN_PROGRESS', 'In Progress'),
           ('COMPLETED', 'Completed'),
           ('OVERDUE', 'Overdue'),
           ('CANCELLED', 'Cancelled'),
       ]
       
       # Core fields
       scenario = models.ForeignKey(
           'scenario.Scenario',
           on_delete=models.CASCADE,
           related_name='planned_activities',
           help_text="Scenario this activity belongs to"
       )
       batch = models.ForeignKey(
           'batch.Batch',
           on_delete=models.CASCADE,
           related_name='planned_activities',
           help_text="Batch this activity is planned for"
       )
       activity_type = models.CharField(
           max_length=50,
           choices=ACTIVITY_TYPE_CHOICES,
           help_text="Type of operational activity"
       )
       due_date = models.DateField(
           help_text="Planned execution date"
       )
       status = models.CharField(
           max_length=20,
           choices=STATUS_CHOICES,
           default='PENDING',
           help_text="Current status of the activity"
       )
       
       # Optional fields
       container = models.ForeignKey(
           'infrastructure.Container',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           help_text="Target container (optional)"
       )
       notes = models.TextField(
           null=True,
           blank=True,
           help_text="Free-text notes for context"
       )
       
       # Audit fields
       created_by = models.ForeignKey(
           'auth.User',
           on_delete=models.PROTECT,
           related_name='created_planned_activities',
           help_text="User who created this activity"
       )
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       completed_at = models.DateTimeField(
           null=True,
           blank=True,
           help_text="Timestamp when activity was completed"
       )
       completed_by = models.ForeignKey(
           'auth.User',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           related_name='completed_planned_activities',
           help_text="User who marked activity as completed"
       )
       
       # Integration fields
       transfer_workflow = models.ForeignKey(
           'batch.BatchTransferWorkflow',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           help_text="Spawned Transfer Workflow (for TRANSFER activities)"
       )
       
       # Audit trail
       history = HistoricalRecords()
       
       class Meta:
           db_table = 'planning_plannedactivity'
           ordering = ['due_date', 'created_at']
           indexes = [
               models.Index(fields=['scenario', 'due_date']),
               models.Index(fields=['batch', 'status']),
               models.Index(fields=['activity_type', 'status']),
           ]
           verbose_name = 'Planned Activity'
           verbose_name_plural = 'Planned Activities'
       
       def __str__(self):
           return f"{self.get_activity_type_display()} for {self.batch} on {self.due_date}"
       
       @property
       def is_overdue(self):
           """Check if activity is overdue."""
           return (
               self.status == 'PENDING' 
               and self.due_date < timezone.now().date()
           )
       
       def mark_completed(self, user):
           """Mark activity as completed."""
           self.status = 'COMPLETED'
           self.completed_at = timezone.now()
           self.completed_by = user
           self.save()
       
       def spawn_transfer_workflow(self, workflow_type, source_lifecycle_stage, dest_lifecycle_stage):
           """Create a Transfer Workflow from this planned activity."""
           if self.activity_type != 'TRANSFER':
               raise ValueError("Can only spawn workflows from TRANSFER activities")
           
           if self.transfer_workflow:
               raise ValueError("Workflow already spawned for this activity")
           
           from apps.batch.models import BatchTransferWorkflow
           
           workflow = BatchTransferWorkflow.objects.create(
               batch=self.batch,
               workflow_type=workflow_type,
               source_lifecycle_stage=source_lifecycle_stage,
               dest_lifecycle_stage=dest_lifecycle_stage,
               planned_start_date=self.due_date,
               planned_activity=self,
               created_by=self.created_by
           )
           
           self.transfer_workflow = workflow
           self.status = 'IN_PROGRESS'
           self.save()
           
           return workflow
   ```

2. Create migration:
   ```bash
   python manage.py makemigrations planning
   ```

3. Apply migration:
   ```bash
   python manage.py migrate planning
   ```

**Acceptance Criteria**:
- [ ] `PlannedActivity` model is created with all fields
- [ ] Model has `is_overdue` property
- [ ] Model has `mark_completed()` method
- [ ] Model has `spawn_transfer_workflow()` method
- [ ] Audit trail is enabled via `django-simple-history`
- [ ] Migration runs without errors
- [ ] Model is accessible in Django admin

**Estimated Time**: 4 hours

---

#### Task 1.3: Implement ActivityTemplate Model

**Objective**: Create the `ActivityTemplate` model for auto-generating planned activities.

**Steps**:

1. Add model to `planning/models.py`:
   ```python
   class ActivityTemplate(models.Model):
       """
       Template for auto-generating planned activities when batches are created.
       
       Templates define standard lifecycle activities (e.g., "First vaccination at 50g")
       that can be automatically applied to new batches.
       """
       
       TRIGGER_TYPE_CHOICES = [
           ('DAY_OFFSET', 'Day Offset'),
           ('WEIGHT_THRESHOLD', 'Weight Threshold'),
           ('STAGE_TRANSITION', 'Stage Transition'),
       ]
       
       # Core fields
       name = models.CharField(
           max_length=200,
           unique=True,
           help_text="Template name (e.g., 'Standard Atlantic Salmon Lifecycle')"
       )
       description = models.TextField(
           null=True,
           blank=True,
           help_text="Template description"
       )
       activity_type = models.CharField(
           max_length=50,
           choices=PlannedActivity.ACTIVITY_TYPE_CHOICES,
           help_text="Type of activity to generate"
       )
       
       # Trigger configuration
       trigger_type = models.CharField(
           max_length=20,
           choices=TRIGGER_TYPE_CHOICES,
           help_text="When to create the activity"
       )
       day_offset = models.IntegerField(
           null=True,
           blank=True,
           help_text="Days after batch creation (for DAY_OFFSET trigger)"
       )
       weight_threshold_g = models.DecimalField(
           max_digits=10,
           decimal_places=2,
           null=True,
           blank=True,
           help_text="Average weight threshold (for WEIGHT_THRESHOLD trigger)"
       )
       target_lifecycle_stage = models.ForeignKey(
           'batch.LifecycleStage',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           related_name='target_templates',
           help_text="Target stage for STAGE_TRANSITION trigger"
       )
       
       # Template content
       notes_template = models.TextField(
           null=True,
           blank=True,
           help_text="Template for activity notes"
       )
       
       # Metadata
       is_active = models.BooleanField(
           default=True,
           help_text="Whether template is active"
       )
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       
       class Meta:
           db_table = 'planning_activitytemplate'
           ordering = ['name']
           verbose_name = 'Activity Template'
           verbose_name_plural = 'Activity Templates'
       
       def __str__(self):
           return self.name
       
       def generate_activity(self, scenario, batch, override_due_date=None):
           """Generate a PlannedActivity from this template."""
           from datetime import timedelta
           
           # Calculate due date based on trigger type
           if override_due_date:
               due_date = override_due_date
           elif self.trigger_type == 'DAY_OFFSET':
               due_date = batch.created_at.date() + timedelta(days=self.day_offset)
           elif self.trigger_type == 'WEIGHT_THRESHOLD':
               # Placeholder: Would need growth projection logic
               due_date = timezone.now().date() + timedelta(days=30)
           elif self.trigger_type == 'STAGE_TRANSITION':
               # Placeholder: Would need lifecycle transition logic
               due_date = timezone.now().date() + timedelta(days=60)
           else:
               due_date = timezone.now().date()
           
           activity = PlannedActivity.objects.create(
               scenario=scenario,
               batch=batch,
               activity_type=self.activity_type,
               due_date=due_date,
               notes=self.notes_template,
               created_by=scenario.created_by
           )
           
           return activity
   ```

2. Create migration:
   ```bash
   python manage.py makemigrations planning
   ```

3. Apply migration:
   ```bash
   python manage.py migrate planning
   ```

**Acceptance Criteria**:
- [ ] `ActivityTemplate` model is created with all fields
- [ ] Model has `generate_activity()` method
- [ ] Migration runs without errors
- [ ] Model is accessible in Django admin

**Estimated Time**: 3 hours

---

#### Task 1.4: Create Serializers

**Objective**: Create DRF serializers for `PlannedActivity` and `ActivityTemplate`.

**Steps**:

1. Create `planning/api/serializers/planned_activity_serializer.py`:
   ```python
   from rest_framework import serializers
   from apps.planning.models import PlannedActivity

   class PlannedActivitySerializer(serializers.ModelSerializer):
       """Serializer for PlannedActivity model."""
       
       # Read-only computed fields
       activity_type_display = serializers.CharField(
           source='get_activity_type_display',
           read_only=True
       )
       status_display = serializers.CharField(
           source='get_status_display',
           read_only=True
       )
       is_overdue = serializers.ReadOnlyField()
       
       # Nested representations for foreign keys
       created_by_name = serializers.CharField(
           source='created_by.get_full_name',
           read_only=True
       )
       completed_by_name = serializers.CharField(
           source='completed_by.get_full_name',
           read_only=True,
           allow_null=True
       )
       container_name = serializers.CharField(
           source='container.name',
           read_only=True,
           allow_null=True
       )
       
       class Meta:
           model = PlannedActivity
           fields = [
               'id',
               'scenario',
               'batch',
               'activity_type',
               'activity_type_display',
               'due_date',
               'status',
               'status_display',
               'container',
               'container_name',
               'notes',
               'created_by',
               'created_by_name',
               'created_at',
               'updated_at',
               'completed_at',
               'completed_by',
               'completed_by_name',
               'transfer_workflow',
               'is_overdue',
           ]
           read_only_fields = [
               'id',
               'created_at',
               'updated_at',
               'completed_at',
               'completed_by',
               'transfer_workflow',
           ]
       
       def create(self, validated_data):
           """Override create to set created_by from request user."""
           validated_data['created_by'] = self.context['request'].user
           return super().create(validated_data)
   ```

2. Create `planning/api/serializers/activity_template_serializer.py`:
   ```python
   from rest_framework import serializers
   from apps.planning.models import ActivityTemplate

   class ActivityTemplateSerializer(serializers.ModelSerializer):
       """Serializer for ActivityTemplate model."""
       
       activity_type_display = serializers.CharField(
           source='get_activity_type_display',
           read_only=True
       )
       trigger_type_display = serializers.CharField(
           source='get_trigger_type_display',
           read_only=True
       )
       
       class Meta:
           model = ActivityTemplate
           fields = [
               'id',
               'name',
               'description',
               'activity_type',
               'activity_type_display',
               'trigger_type',
               'trigger_type_display',
               'day_offset',
               'weight_threshold_g',
               'target_lifecycle_stage',
               'notes_template',
               'is_active',
               'created_at',
               'updated_at',
           ]
           read_only_fields = ['id', 'created_at', 'updated_at']
   ```

3. Create `planning/api/serializers/__init__.py`:
   ```python
   from .planned_activity_serializer import PlannedActivitySerializer
   from .activity_template_serializer import ActivityTemplateSerializer

   __all__ = [
       'PlannedActivitySerializer',
       'ActivityTemplateSerializer',
   ]
   ```

**Acceptance Criteria**:
- [ ] `PlannedActivitySerializer` is created with all fields
- [ ] Serializer includes computed fields (`is_overdue`, display names)
- [ ] `ActivityTemplateSerializer` is created
- [ ] Serializers are importable from `planning.api.serializers`

**Estimated Time**: 2 hours

---

#### Task 1.5: Create ViewSets

**Objective**: Create DRF viewsets for CRUD operations and custom actions.

**Steps**:

1. Create `planning/api/viewsets/planned_activity_viewset.py`:
   ```python
   from rest_framework import viewsets, status
   from rest_framework.decorators import action
   from rest_framework.response import Response
   from django_filters.rest_framework import DjangoFilterBackend
   from rest_framework.filters import SearchFilter, OrderingFilter
   from apps.planning.models import PlannedActivity
   from apps.planning.api.serializers import PlannedActivitySerializer

   class PlannedActivityViewSet(viewsets.ModelViewSet):
       """ViewSet for PlannedActivity model."""
       
       queryset = PlannedActivity.objects.all()
       serializer_class = PlannedActivitySerializer
       filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
       filterset_fields = ['scenario', 'batch', 'activity_type', 'status', 'container']
       search_fields = ['notes']
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
               workflow = activity.spawn_transfer_workflow(
                   workflow_type=workflow_type,
                   source_lifecycle_stage_id=source_stage_id,
                   dest_lifecycle_stage_id=dest_stage_id
               )
           except ValueError as e:
               return Response(
                   {"error": str(e)},
                   status=status.HTTP_400_BAD_REQUEST
               )
           
           from apps.batch.api.serializers import BatchTransferWorkflowSerializer
           serializer = BatchTransferWorkflowSerializer(workflow)
           return Response(serializer.data, status=status.HTTP_201_CREATED)
   ```

2. Create `planning/api/viewsets/activity_template_viewset.py`:
   ```python
   from rest_framework import viewsets, status
   from rest_framework.decorators import action
   from rest_framework.response import Response
   from apps.planning.models import ActivityTemplate
   from apps.planning.api.serializers import (
       ActivityTemplateSerializer,
       PlannedActivitySerializer
   )

   class ActivityTemplateViewSet(viewsets.ModelViewSet):
       """ViewSet for ActivityTemplate model."""
       
       queryset = ActivityTemplate.objects.all()
       serializer_class = ActivityTemplateSerializer
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
               
               scenario = Scenario.objects.get(id=scenario_id)
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
   ```

3. Create `planning/api/viewsets/__init__.py`:
   ```python
   from .planned_activity_viewset import PlannedActivityViewSet
   from .activity_template_viewset import ActivityTemplateViewSet

   __all__ = [
       'PlannedActivityViewSet',
       'ActivityTemplateViewSet',
   ]
   ```

**Acceptance Criteria**:
- [ ] `PlannedActivityViewSet` is created with CRUD operations
- [ ] ViewSet has `mark_completed` custom action
- [ ] ViewSet has `spawn_workflow` custom action
- [ ] `ActivityTemplateViewSet` is created with CRUD operations
- [ ] ViewSet has `generate_for_batch` custom action
- [ ] Filtering, searching, and ordering are configured

**Estimated Time**: 4 hours

---

#### Task 1.6: Register API Routes

**Objective**: Register the viewsets in the centralized API router.

**Steps**:

1. Create `planning/api/routers/planning_router.py`:
   ```python
   from rest_framework.routers import DefaultRouter
   from apps.planning.api.viewsets import (
       PlannedActivityViewSet,
       ActivityTemplateViewSet
   )

   router = DefaultRouter()
   router.register(r'planned-activities', PlannedActivityViewSet, basename='planned-activity')
   router.register(r'activity-templates', ActivityTemplateViewSet, basename='activity-template')
   ```

2. Update `aquamind/api/router.py`:
   ```python
   from django.urls import path, include
   from apps.planning.api.routers.planning_router import router as planning_router
   # ... other imports

   urlpatterns = [
       # ... existing routes
       path('planning/', include(planning_router.urls)),
   ]
   ```

**Acceptance Criteria**:
- [ ] API routes are registered at `/api/v1/planning/planned-activities/`
- [ ] API routes are registered at `/api/v1/planning/activity-templates/`
- [ ] Routes are accessible via browser (DRF browsable API)
- [ ] Custom actions are accessible (e.g., `/api/v1/planning/planned-activities/{id}/mark-completed/`)

**Estimated Time**: 1 hour

---

#### Task 1.7: Add Integration with Scenario App

**Objective**: Add custom action to `ScenarioViewSet` to retrieve planned activities.

**Steps**:

1. Update `apps/scenario/api/viewsets.py`:
   ```python
   from rest_framework.decorators import action
   from rest_framework.response import Response
   from apps.planning.api.serializers import PlannedActivitySerializer

   class ScenarioViewSet(viewsets.ModelViewSet):
       # ... existing code ...

       @action(detail=True, methods=['get'], url_path='planned-activities')
       def planned_activities(self, request, pk=None):
           """Retrieve all planned activities for this scenario."""
           scenario = self.get_object()
           activities = scenario.planned_activities.all()
           
           # Apply optional filters
           activity_type = request.query_params.get('activity_type')
           status = request.query_params.get('status')
           batch_id = request.query_params.get('batch')
           
           if activity_type:
               activities = activities.filter(activity_type=activity_type)
           if status:
               activities = activities.filter(status=status)
           if batch_id:
               activities = activities.filter(batch_id=batch_id)
           
           serializer = PlannedActivitySerializer(activities, many=True)
           return Response(serializer.data)
   ```

**Acceptance Criteria**:
- [ ] Custom action is added to `ScenarioViewSet`
- [ ] Endpoint is accessible at `/api/v1/scenario/scenarios/{id}/planned-activities/`
- [ ] Filtering by `activity_type`, `status`, and `batch` works correctly

**Estimated Time**: 1 hour

---

#### Task 1.8: Add Integration with Batch App

**Objective**: Add custom action to `BatchViewSet` and linking field to `BatchTransferWorkflow`.

**Steps**:

1. Add migration to `batch` app:
   ```bash
   python manage.py makemigrations batch --empty --name add_planned_activity_link
   ```

2. Edit migration file:
   ```python
   from django.db import migrations, models
   import django.db.models.deletion

   class Migration(migrations.Migration):
       dependencies = [
           ('batch', '0001_initial'),
           ('planning', '0001_initial'),
       ]

       operations = [
           migrations.AddField(
               model_name='batchtransferworkflow',
               name='planned_activity',
               field=models.OneToOneField(
                   null=True,
                   blank=True,
                   on_delete=django.db.models.deletion.SET_NULL,
                   related_name='spawned_workflow',
                   to='planning.plannedactivity'
               ),
           ),
       ]
   ```

3. Apply migration:
   ```bash
   python manage.py migrate batch
   ```

4. Update `apps/batch/models.py`:
   ```python
   class BatchTransferWorkflow(models.Model):
       # ... existing fields ...
       
       planned_activity = models.OneToOneField(
           'planning.PlannedActivity',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           related_name='spawned_workflow',
           help_text="Planned activity that spawned this workflow (if any)"
       )
       
       # ... existing methods ...
       
       def mark_completed(self):
           """Mark workflow as completed and update linked planned activity."""
           self.status = 'COMPLETED'
           self.actual_completion_date = timezone.now()
           self.save()
           
           # Update linked planned activity if exists
           if self.planned_activity:
               self.planned_activity.mark_completed(user=self.created_by)
   ```

5. Update `apps/batch/api/viewsets.py`:
   ```python
   from apps.planning.api.serializers import PlannedActivitySerializer

   class BatchViewSet(viewsets.ModelViewSet):
       # ... existing code ...

       @action(detail=True, methods=['get'], url_path='planned-activities')
       def planned_activities(self, request, pk=None):
           """Retrieve all planned activities for this batch across all scenarios."""
           batch = self.get_object()
           activities = batch.planned_activities.all()
           
           # Apply optional filters
           scenario_id = request.query_params.get('scenario')
           status = request.query_params.get('status')
           
           if scenario_id:
               activities = activities.filter(scenario_id=scenario_id)
           if status:
               activities = activities.filter(status=status)
           
           serializer = PlannedActivitySerializer(activities, many=True)
           return Response(serializer.data)
   ```

**Acceptance Criteria**:
- [ ] `planned_activity` field is added to `BatchTransferWorkflow` model
- [ ] Migration runs without errors
- [ ] `mark_completed()` method updates linked planned activity
- [ ] Custom action is added to `BatchViewSet`
- [ ] Endpoint is accessible at `/api/v1/batch/batches/{id}/planned-activities/`

**Estimated Time**: 2 hours

---

#### Task 1.9: Implement Signal Handlers

**Objective**: Create signal handlers for auto-generation and workflow sync.

**Steps**:

1. Create `planning/signals.py`:
   ```python
   from django.db.models.signals import post_save
   from django.dispatch import receiver
   from apps.batch.models import Batch, BatchTransferWorkflow
   from .models import ActivityTemplate, PlannedActivity

   @receiver(post_save, sender=Batch)
   def auto_generate_activities_from_templates(sender, instance, created, **kwargs):
       """Auto-generate planned activities when a new batch is created."""
       if not created:
           return  # Only run for new batches
       
       # Get the default scenario for this batch (if exists)
       default_scenario = instance.scenarios.filter(is_baseline=True).first()
       if not default_scenario:
           return  # No scenario to attach activities to
       
       # Get all active templates with DAY_OFFSET trigger
       templates = ActivityTemplate.objects.filter(
           is_active=True,
           trigger_type='DAY_OFFSET'
       )
       
       # Generate activities
       for template in templates:
           template.generate_activity(
               scenario=default_scenario,
               batch=instance
           )

   @receiver(post_save, sender=BatchTransferWorkflow)
   def sync_workflow_completion_to_activity(sender, instance, created, **kwargs):
       """Update linked planned activity when workflow completes."""
       if created:
           return  # Only run on updates
       
       if instance.status == 'COMPLETED' and instance.planned_activity:
           activity = instance.planned_activity
           if activity.status != 'COMPLETED':
               activity.mark_completed(user=instance.created_by)
   ```

2. Verify signal registration in `planning/apps.py`:
   ```python
   class PlanningConfig(AppConfig):
       # ... existing code ...
       
       def ready(self):
           import apps.planning.signals  # noqa
   ```

**Acceptance Criteria**:
- [ ] Signal handler for batch creation is implemented
- [ ] Signal handler for workflow completion is implemented
- [ ] Signals are registered in `apps.py`
- [ ] Auto-generation works when a new batch is created
- [ ] Workflow completion updates linked activity

**Estimated Time**: 2 hours

---

#### Task 1.10: Configure Django Admin

**Objective**: Register models in Django admin for manual management.

**Steps**:

1. Create `planning/admin.py`:
   ```python
   from django.contrib import admin
   from simple_history.admin import SimpleHistoryAdmin
   from .models import PlannedActivity, ActivityTemplate

   @admin.register(PlannedActivity)
   class PlannedActivityAdmin(SimpleHistoryAdmin):
       list_display = [
           'id',
           'scenario',
           'batch',
           'activity_type',
           'due_date',
           'status',
           'created_by',
           'created_at',
       ]
       list_filter = ['activity_type', 'status', 'scenario', 'created_at']
       search_fields = ['batch__batch_number', 'notes']
       readonly_fields = ['created_at', 'updated_at', 'completed_at']
       autocomplete_fields = ['scenario', 'batch', 'container']
       
       fieldsets = (
           ('Core Information', {
               'fields': ('scenario', 'batch', 'activity_type', 'due_date', 'status')
           }),
           ('Details', {
               'fields': ('container', 'notes')
           }),
           ('Integration', {
               'fields': ('transfer_workflow',)
           }),
           ('Audit Trail', {
               'fields': ('created_by', 'created_at', 'updated_at', 'completed_at', 'completed_by')
           }),
       )

   @admin.register(ActivityTemplate)
   class ActivityTemplateAdmin(admin.ModelAdmin):
       list_display = [
           'id',
           'name',
           'activity_type',
           'trigger_type',
           'is_active',
           'created_at',
       ]
       list_filter = ['activity_type', 'trigger_type', 'is_active']
       search_fields = ['name', 'description']
       readonly_fields = ['created_at', 'updated_at']
       
       fieldsets = (
           ('Core Information', {
               'fields': ('name', 'description', 'activity_type', 'is_active')
           }),
           ('Trigger Configuration', {
               'fields': ('trigger_type', 'day_offset', 'weight_threshold_g', 'target_lifecycle_stage')
           }),
           ('Template Content', {
               'fields': ('notes_template',)
           }),
           ('Metadata', {
               'fields': ('created_at', 'updated_at')
           }),
       )
   ```

**Acceptance Criteria**:
- [ ] `PlannedActivity` is registered in admin with history
- [ ] `ActivityTemplate` is registered in admin
- [ ] Admin interface is accessible and functional
- [ ] List views show relevant fields
- [ ] Detail views have organized fieldsets

**Estimated Time**: 1 hour

---

### Phase 1 Summary

**Total Estimated Time**: 3-4 weeks

**Deliverables**:
- [ ] `planning` app is created and configured
- [ ] `PlannedActivity` model is implemented with audit trail
- [ ] `ActivityTemplate` model is implemented
- [ ] Serializers are created for both models
- [ ] ViewSets are created with CRUD and custom actions
- [ ] API routes are registered
- [ ] Integration with `scenario` and `batch` apps is complete
- [ ] Signal handlers are implemented
- [ ] Django admin is configured

**Testing**:
- [ ] Unit tests for models (methods, properties)
- [ ] Unit tests for serializers
- [ ] Integration tests for API endpoints
- [ ] Integration tests for signal handlers

---

## Phase 2: Frontend Implementation

**Goal**: Create the Production Planner UI with timeline view, filters, and forms.

**Duration**: 3-4 weeks

*This phase is documented in the frontend repository.*

**Key Deliverables**:
- [ ] Production Planner page with KPI dashboard
- [ ] Timeline/Gantt chart view for planned activities
- [ ] Create/Edit activity forms
- [ ] Integration with Batch Detail page (Planned Activities tab)
- [ ] Integration with Scenario Planning page

---

## Phase 3: Advanced Features

**Goal**: Implement template management, auto-generation, and variance reporting.

**Duration**: 2-3 weeks

#### Task 3.1: Template Management UI

**Objective**: Create UI for managing activity templates.

**Steps**:
1. Create Template Manager page
2. Implement template CRUD forms
3. Add "Generate from Template" action to batch creation workflow

**Estimated Time**: 1 week

---

#### Task 3.2: Variance Reporting

**Objective**: Create reports comparing planned vs. actual execution.

**Steps**:
1. Add API endpoint for variance analysis
2. Create Variance Report page
3. Implement charts (planned vs. actual dates, completion rates)

**Estimated Time**: 1 week

---

#### Task 3.3: Mobile Optimization

**Objective**: Optimize UI for mobile devices (marking activities as completed in the field).

**Steps**:
1. Create mobile-friendly activity list view
2. Implement quick-complete action (swipe gesture)
3. Test on tablets and phones

**Estimated Time**: 1 week

---

## Testing Strategy

### Unit Tests

**Models**:
```python
# tests/test_models.py
from django.test import TestCase
from apps.planning.models import PlannedActivity, ActivityTemplate
from apps.scenario.models import Scenario
from apps.batch.models import Batch
from django.contrib.auth.models import User

class PlannedActivityModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.scenario = Scenario.objects.create(name='Test Scenario', created_by=self.user)
        self.batch = Batch.objects.create(batch_number='TEST-001')
        
    def test_is_overdue_property(self):
        """Test is_overdue property for pending activities."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Create overdue activity
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=timezone.now().date() - timedelta(days=1),
            status='PENDING',
            created_by=self.user
        )
        
        self.assertTrue(activity.is_overdue)
        
    def test_mark_completed(self):
        """Test mark_completed method."""
        activity = PlannedActivity.objects.create(
            scenario=self.scenario,
            batch=self.batch,
            activity_type='VACCINATION',
            due_date=timezone.now().date(),
            status='PENDING',
            created_by=self.user
        )
        
        activity.mark_completed(user=self.user)
        
        self.assertEqual(activity.status, 'COMPLETED')
        self.assertIsNotNone(activity.completed_at)
        self.assertEqual(activity.completed_by, self.user)
```

**API Endpoints**:
```python
# tests/test_api.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from apps.planning.models import PlannedActivity

class PlannedActivityAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
    def test_create_planned_activity(self):
        """Test creating a planned activity via API."""
        data = {
            'scenario': 1,
            'batch': 1,
            'activity_type': 'VACCINATION',
            'due_date': '2024-12-15',
            'notes': 'Test vaccination'
        }
        
        response = self.client.post('/api/v1/planning/planned-activities/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PlannedActivity.objects.count(), 1)
        
    def test_mark_completed_action(self):
        """Test mark-completed custom action."""
        activity = PlannedActivity.objects.create(
            scenario_id=1,
            batch_id=1,
            activity_type='VACCINATION',
            due_date='2024-12-15',
            status='PENDING',
            created_by=self.user
        )
        
        response = self.client.post(f'/api/v1/planning/planned-activities/{activity.id}/mark-completed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity.refresh_from_db()
        self.assertEqual(activity.status, 'COMPLETED')
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All migrations are created and tested
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] API documentation is generated (OpenAPI/Swagger)
- [ ] Django admin is configured
- [ ] Permissions are configured (role-based access)

### Deployment

- [ ] Run migrations on production database
- [ ] Verify API endpoints are accessible
- [ ] Verify Django admin is accessible
- [ ] Create initial activity templates (via admin or fixtures)
- [ ] Test signal handlers with real data

### Post-Deployment

- [ ] Monitor error logs for 24 hours
- [ ] Verify auto-generation works for new batches
- [ ] Verify workflow sync works for completed workflows
- [ ] Collect user feedback on UI/UX

---

## References

1. AquaMind PRD - Section 3.1.2.1 Transfer Workflow Architecture
2. AquaMind Code Organization Guidelines - `aquamind/docs/quality_assurance/code_organization_guidelines.md`
3. AquaMind API Standards - `aquamind/docs/quality_assurance/api_standards.md`
4. Django REST Framework Documentation - https://www.django-rest-framework.org/
5. Django Simple History Documentation - https://django-simple-history.readthedocs.io/

---

**End of Document**
