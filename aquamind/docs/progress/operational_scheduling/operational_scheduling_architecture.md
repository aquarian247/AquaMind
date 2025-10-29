# Operational Scheduling Architecture

**Version**: 2.0  
**Last Updated**: October 28, 2025  
**Author**: Manus AI  
**Target Repository**: `aquarian247/AquaMind/aquamind/docs/progress/`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Context](#system-context)
3. [Data Model](#data-model)
4. [Integration Architecture](#integration-architecture)
5. [API Design](#api-design)
6. [Business Logic](#business-logic)
7. [Database Schema](#database-schema)
8. [Migration Strategy](#migration-strategy)

---

## Executive Summary

The **Operational Scheduling** feature introduces a scenario-aware planning layer to AquaMind, enabling farming managers to plan, track, and analyze operational activities across batch lifecycles. This feature complements the existing **Transfer Workflow** system by providing long-term visibility and variance tracking for all operational events, not just transfers.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Scenario Integration** | Plan activities within specific scenarios for what-if analysis |
| **Activity Templates** | Auto-generate lifecycle plans for new batches based on templates |
| **Variance Tracking** | Compare planned vs. actual execution dates and outcomes |
| **Cross-Batch Visibility** | View all planned activities across 50-60 active batches in a unified timeline |
| **Transfer Workflow Linking** | Spawn and track complex Transfer Workflows from planned transfer activities |
| **Mobile-Friendly** | Mark activities as completed from mobile devices in the field |

### Design Principles

1. **No Duplication**: Planned Activities do NOT replace Transfer Workflows; they complement them by providing a planning layer.
2. **Scenario-Centric**: All planning occurs within a scenario context, enabling multiple what-if analyses.
3. **Lightweight Planning**: Planned Activities are simple, single-event records (vaccination on Day 45), not complex multi-step workflows.
4. **Bidirectional Linking**: Planned Activities can spawn Transfer Workflows, and completed workflows update linked activities.
5. **Audit Trail**: All activity status changes are tracked via `django-simple-history`.

---

## System Context

### Relationship to Existing Apps

The Operational Scheduling feature is implemented as a new Django app named **`planning`**, which integrates with existing AquaMind apps:

```
┌─────────────────────────────────────────────────────────────┐
│                      AquaMind System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐ │
│  │   scenario   │────▶│   planning   │────▶│    batch    │ │
│  │              │     │              │     │             │ │
│  │ - Scenario   │     │ - Planned    │     │ - Transfer  │ │
│  │ - Projection │     │   Activity   │     │   Workflow  │ │
│  │              │     │ - Activity   │     │ - Transfer  │ │
│  │              │     │   Template   │     │   Action    │ │
│  └──────────────┘     └──────────────┘     └─────────────┘ │
│         │                     │                     │       │
│         │                     │                     │       │
│         ▼                     ▼                     ▼       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           infrastructure (Container, Area)           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

| Existing App | Integration Type | Purpose |
|--------------|------------------|---------|
| **scenario** | Foreign Key | All planned activities belong to a scenario |
| **batch** | Foreign Key | Activities are planned for specific batches |
| **batch** (Transfer Workflows) | Linking Field | Planned transfer activities can spawn workflows |
| **infrastructure** | Foreign Key (optional) | Activities can target specific containers |
| **operational** | Future Integration | Link actual operational events to planned activities |

---

## Data Model

### Core Models

#### 1. PlannedActivity

The **PlannedActivity** model represents a single planned operational event within a scenario.

**Purpose**: To provide a lightweight, scenario-aware planning record for all operational activities (vaccinations, treatments, culling, sales, feed changes, and transfers).

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto-incrementing primary key |
| `scenario` | ForeignKey | NOT NULL, ON DELETE CASCADE | Link to `scenario_scenario` |
| `batch` | ForeignKey | NOT NULL, ON DELETE CASCADE | Link to `batch_batch` |
| `activity_type` | CharField(50) | NOT NULL, CHOICES | Type of activity (see Activity Types below) |
| `due_date` | DateField | NOT NULL | Planned execution date |
| `status` | CharField(20) | NOT NULL, CHOICES, DEFAULT='PENDING' | Current status (PENDING, IN_PROGRESS, COMPLETED, OVERDUE, CANCELLED) |
| `container` | ForeignKey | NULL, ON DELETE SET NULL | Optional link to `infrastructure_container` |
| `notes` | TextField | NULL | Free-text notes for context |
| `created_by` | ForeignKey | NOT NULL, ON DELETE PROTECT | Link to `auth_user` |
| `created_at` | DateTimeField | AUTO_NOW_ADD | Timestamp of creation |
| `updated_at` | DateTimeField | AUTO_NOW | Timestamp of last update |
| `completed_at` | DateTimeField | NULL | Timestamp when status changed to COMPLETED |
| `completed_by` | ForeignKey | NULL, ON DELETE SET NULL | Link to `auth_user` who marked as completed |
| `transfer_workflow` | ForeignKey | NULL, ON DELETE SET NULL | Link to spawned `batch_batchtransferworkflow` (for TRANSFER activities only) |

**Activity Types** (Choices):

| Value | Display Name | Description |
|-------|--------------|-------------|
| `VACCINATION` | Vaccination | Administer vaccines to batch |
| `TREATMENT` | Treatment/Health Intervention | De-licing, disease treatment, parasite control |
| `CULL` | Culling | Remove weak or diseased fish |
| `SALE` | Sale/Harvest | Sell or harvest fish |
| `FEED_CHANGE` | Feed Strategy Change | Switch feed type or feeding schedule |
| `TRANSFER` | Transfer | Move fish between containers (links to Transfer Workflow) |
| `MAINTENANCE` | Maintenance | Tank cleaning, equipment checks |
| `SAMPLING` | Sampling | Growth sampling, health checks |
| `OTHER` | Other | Custom activity type |

**Status Choices**:

| Value | Description | Behavior |
|-------|-------------|----------|
| `PENDING` | Activity is planned but not started | Default status |
| `IN_PROGRESS` | Activity execution has begun | Set when linked Transfer Workflow status = IN_PROGRESS |
| `COMPLETED` | Activity has been executed | Set manually or when linked Transfer Workflow completes |
| `OVERDUE` | Activity is past due date and not completed | Auto-calculated (due_date < today AND status = PENDING) |
| `CANCELLED` | Activity was cancelled | Set manually |

**Model Methods**:

```python
class PlannedActivity(models.Model):
    # ... fields ...

    def is_overdue(self) -> bool:
        """Check if activity is overdue."""
        from django.utils import timezone
        return (
            self.status == 'PENDING' 
            and self.due_date < timezone.now().date()
        )

    def mark_completed(self, user):
        """Mark activity as completed."""
        from django.utils import timezone
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save()

    def spawn_transfer_workflow(self, workflow_type, source_lifecycle_stage, dest_lifecycle_stage):
        """Create a Transfer Workflow from this planned activity (TRANSFER type only)."""
        if self.activity_type != 'TRANSFER':
            raise ValueError("Can only spawn workflows from TRANSFER activities")
        
        from apps.batch.models import BatchTransferWorkflow
        
        workflow = BatchTransferWorkflow.objects.create(
            batch=self.batch,
            workflow_type=workflow_type,
            source_lifecycle_stage=source_lifecycle_stage,
            dest_lifecycle_stage=dest_lifecycle_stage,
            planned_start_date=self.due_date,
            planned_activity=self  # Link back to this activity
        )
        
        self.transfer_workflow = workflow
        self.status = 'IN_PROGRESS'
        self.save()
        
        return workflow

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
```

**Audit Trail**:

```python
# Register with django-simple-history
from simple_history.models import HistoricalRecords

class PlannedActivity(models.Model):
    # ... fields ...
    history = HistoricalRecords()
```

---

#### 2. ActivityTemplate

The **ActivityTemplate** model defines reusable templates for generating planned activities when a new batch is created.

**Purpose**: To automate the creation of standard lifecycle activities (e.g., "First vaccination at 50g", "Transfer to sea at 100g") for new batches, reducing manual planning effort.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto-incrementing primary key |
| `name` | CharField(200) | NOT NULL, UNIQUE | Template name (e.g., "Standard Atlantic Salmon Lifecycle") |
| `description` | TextField | NULL | Template description |
| `lifecycle_stage` | ForeignKey | NULL, ON DELETE SET NULL | Link to `batch_lifecyclestage` (optional filter) |
| `activity_type` | CharField(50) | NOT NULL, CHOICES | Type of activity (same choices as PlannedActivity) |
| `trigger_type` | CharField(20) | NOT NULL, CHOICES | When to create the activity (DAY_OFFSET, WEIGHT_THRESHOLD, STAGE_TRANSITION) |
| `day_offset` | IntegerField | NULL | Days after batch creation (for DAY_OFFSET trigger) |
| `weight_threshold_g` | DecimalField(10,2) | NULL | Average weight threshold (for WEIGHT_THRESHOLD trigger) |
| `target_lifecycle_stage` | ForeignKey | NULL, ON DELETE SET NULL | Target stage for STAGE_TRANSITION trigger |
| `notes_template` | TextField | NULL | Template for activity notes |
| `is_active` | BooleanField | DEFAULT=TRUE | Whether template is active |
| `created_at` | DateTimeField | AUTO_NOW_ADD | Timestamp of creation |
| `updated_at` | DateTimeField | AUTO_NOW | Timestamp of last update |

**Trigger Types**:

| Value | Description | Example |
|-------|-------------|---------|
| `DAY_OFFSET` | Create activity N days after batch creation | "First vaccination on Day 45" |
| `WEIGHT_THRESHOLD` | Create activity when batch reaches average weight | "Transfer to sea at 100g" |
| `STAGE_TRANSITION` | Create activity when batch transitions to a lifecycle stage | "Vaccination upon entering Smolt stage" |

**Model Methods**:

```python
class ActivityTemplate(models.Model):
    # ... fields ...

    def generate_activity(self, scenario, batch, override_due_date=None):
        """Generate a PlannedActivity from this template."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculate due date based on trigger type
        if override_due_date:
            due_date = override_due_date
        elif self.trigger_type == 'DAY_OFFSET':
            due_date = batch.created_at.date() + timedelta(days=self.day_offset)
        elif self.trigger_type == 'WEIGHT_THRESHOLD':
            # Placeholder: Would need growth projection logic
            due_date = timezone.now().date() + timedelta(days=30)  # Estimate
        elif self.trigger_type == 'STAGE_TRANSITION':
            # Placeholder: Would need lifecycle transition logic
            due_date = timezone.now().date() + timedelta(days=60)  # Estimate
        else:
            due_date = timezone.now().date()
        
        activity = PlannedActivity.objects.create(
            scenario=scenario,
            batch=batch,
            activity_type=self.activity_type,
            due_date=due_date,
            notes=self.notes_template,
            created_by=scenario.created_by  # Inherit from scenario creator
        )
        
        return activity

    class Meta:
        db_table = 'planning_activitytemplate'
        ordering = ['name']
        verbose_name = 'Activity Template'
        verbose_name_plural = 'Activity Templates'
```

---

## Integration Architecture

### 1. Scenario Integration

**Requirement**: All planned activities must belong to a scenario, enabling what-if analysis.

**Implementation**:

```python
# In planning/models.py
class PlannedActivity(models.Model):
    scenario = models.ForeignKey(
        'scenario.Scenario',
        on_delete=models.CASCADE,
        related_name='planned_activities',
        help_text="Scenario this activity belongs to"
    )
    # ... other fields
```

**API Behavior**:
- When a scenario is deleted, all its planned activities are cascade-deleted.
- The `ScenarioViewSet` gains a custom action: `GET /api/v1/scenario/scenarios/{id}/planned-activities/`
- This allows the frontend to fetch all activities for a scenario in one request.

**Custom Action**:

```python
# In apps/scenario/api/viewsets.py
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

---

### 2. Transfer Workflow Integration

**Requirement**: Planned activities with `activity_type=TRANSFER` can spawn Transfer Workflows, and completed workflows update the linked activity status.

**Implementation**:

#### A. Add Linking Field to TransferWorkflow

```python
# In apps/batch/models.py
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
```

#### B. Update Workflow Completion Logic

```python
# In apps/batch/models.py
class BatchTransferWorkflow(models.Model):
    # ... existing code ...

    def mark_completed(self):
        """Mark workflow as completed and update linked planned activity."""
        self.status = 'COMPLETED'
        self.actual_completion_date = timezone.now()
        self.save()
        
        # Update linked planned activity if exists
        if self.planned_activity:
            self.planned_activity.mark_completed(user=self.created_by)
```

#### C. API Endpoint for Spawning Workflows

```python
# In apps/planning/api/viewsets.py
class PlannedActivityViewSet(viewsets.ModelViewSet):
    # ... existing code ...

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
        
        # Spawn workflow
        workflow = activity.spawn_transfer_workflow(
            workflow_type=workflow_type,
            source_lifecycle_stage_id=source_stage_id,
            dest_lifecycle_stage_id=dest_stage_id
        )
        
        from apps.batch.api.serializers import BatchTransferWorkflowSerializer
        serializer = BatchTransferWorkflowSerializer(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

---

### 3. Batch Integration

**Requirement**: Planned activities are linked to batches, and the Batch Detail page displays a "Planned Activities" tab.

**Implementation**:

#### A. Add Related Name to PlannedActivity

```python
# In planning/models.py
class PlannedActivity(models.Model):
    batch = models.ForeignKey(
        'batch.Batch',
        on_delete=models.CASCADE,
        related_name='planned_activities',
        help_text="Batch this activity is planned for"
    )
    # ... other fields
```

#### B. Custom Action on BatchViewSet

```python
# In apps/batch/api/viewsets.py
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

---

## API Design

### REST Endpoints

#### 1. PlannedActivity CRUD

**Base URL**: `/api/v1/planning/planned-activities/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all planned activities (with filters) |
| POST | `/` | Create a new planned activity |
| GET | `/{id}/` | Retrieve a specific planned activity |
| PUT | `/{id}/` | Update a planned activity |
| PATCH | `/{id}/` | Partially update a planned activity |
| DELETE | `/{id}/` | Delete a planned activity |

**Query Parameters** (for GET `/`):

| Parameter | Type | Description |
|-----------|------|-------------|
| `scenario` | Integer | Filter by scenario ID |
| `batch` | Integer | Filter by batch ID |
| `activity_type` | String | Filter by activity type (VACCINATION, TREATMENT, etc.) |
| `status` | String | Filter by status (PENDING, COMPLETED, etc.) |
| `due_date_after` | Date | Filter activities due after this date |
| `due_date_before` | Date | Filter activities due before this date |
| `container` | Integer | Filter by container ID |
| `search` | String | Search in notes field |

**Example Request** (Create):

```http
POST /api/v1/planning/planned-activities/
Content-Type: application/json
Authorization: Bearer <token>

{
  "scenario": 42,
  "batch": 206,
  "activity_type": "VACCINATION",
  "due_date": "2024-12-15",
  "container": 977,
  "notes": "First vaccination - IPN vaccine, 0.1ml per fish"
}
```

**Example Response** (Create):

```json
{
  "id": 1523,
  "scenario": 42,
  "batch": 206,
  "activity_type": "VACCINATION",
  "activity_type_display": "Vaccination",
  "due_date": "2024-12-15",
  "status": "PENDING",
  "status_display": "Pending",
  "container": 977,
  "container_name": "Tank FRY-05",
  "notes": "First vaccination - IPN vaccine, 0.1ml per fish",
  "created_by": 5,
  "created_by_name": "John Doe",
  "created_at": "2024-10-28T10:30:00Z",
  "updated_at": "2024-10-28T10:30:00Z",
  "completed_at": null,
  "completed_by": null,
  "transfer_workflow": null,
  "is_overdue": false
}
```

#### 2. Custom Actions

**Mark as Completed**:

```http
POST /api/v1/planning/planned-activities/{id}/mark-completed/
Content-Type: application/json
Authorization: Bearer <token>

{}
```

**Response**:

```json
{
  "message": "Activity marked as completed",
  "activity": {
    "id": 1523,
    "status": "COMPLETED",
    "completed_at": "2024-12-15T14:30:00Z",
    "completed_by": 5,
    "completed_by_name": "John Doe"
  }
}
```

**Spawn Transfer Workflow** (for TRANSFER activities):

```http
POST /api/v1/planning/planned-activities/{id}/spawn-workflow/
Content-Type: application/json
Authorization: Bearer <token>

{
  "workflow_type": "LIFECYCLE_TRANSITION",
  "source_lifecycle_stage": 6,
  "dest_lifecycle_stage": 7
}
```

**Response**:

```json
{
  "id": 1042,
  "batch": 206,
  "workflow_type": "LIFECYCLE_TRANSITION",
  "status": "DRAFT",
  "planned_start_date": "2024-12-15",
  "planned_activity": 1523,
  "total_actions_planned": 0,
  "actions_completed": 0,
  "completion_percentage": 0
}
```

#### 3. ActivityTemplate CRUD

**Base URL**: `/api/v1/planning/activity-templates/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all activity templates |
| POST | `/` | Create a new template |
| GET | `/{id}/` | Retrieve a specific template |
| PUT | `/{id}/` | Update a template |
| DELETE | `/{id}/` | Delete a template |

**Custom Action** (Generate Activities from Template):

```http
POST /api/v1/planning/activity-templates/{id}/generate-for-batch/
Content-Type: application/json
Authorization: Bearer <token>

{
  "scenario": 42,
  "batch": 206
}
```

**Response**:

```json
{
  "message": "Generated 5 planned activities from template",
  "activities": [
    {
      "id": 1524,
      "activity_type": "VACCINATION",
      "due_date": "2024-11-15",
      "notes": "First vaccination - IPN vaccine"
    },
    {
      "id": 1525,
      "activity_type": "TRANSFER",
      "due_date": "2024-12-20",
      "notes": "Transfer to Parr stage"
    }
    // ... more activities
  ]
}
```

---

## Business Logic

### 1. Overdue Activity Detection

**Requirement**: Activities with `status=PENDING` and `due_date < today` should be automatically flagged as overdue.

**Implementation**:

#### A. Model Property

```python
# In planning/models.py
class PlannedActivity(models.Model):
    # ... fields ...

    @property
    def is_overdue(self):
        """Check if activity is overdue."""
        from django.utils import timezone
        return (
            self.status == 'PENDING' 
            and self.due_date < timezone.now().date()
        )
```

#### B. Serializer Field

```python
# In planning/api/serializers.py
class PlannedActivitySerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = PlannedActivity
        fields = '__all__'
```

#### C. API Filter

```python
# In planning/api/viewsets.py
class PlannedActivityViewSet(viewsets.ModelViewSet):
    queryset = PlannedActivity.objects.all()
    serializer_class = PlannedActivitySerializer
    filterset_fields = ['scenario', 'batch', 'activity_type', 'status', 'container']
    search_fields = ['notes']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Custom filter for overdue activities
        if self.request.query_params.get('overdue') == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                status='PENDING',
                due_date__lt=timezone.now().date()
            )
        
        return queryset
```

**Usage**:

```http
GET /api/v1/planning/planned-activities/?overdue=true
```

---

### 2. Activity Template Auto-Generation

**Requirement**: When a new batch is created, automatically generate planned activities from active templates.

**Implementation**:

#### A. Signal Handler

```python
# In planning/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.batch.models import Batch
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
```

#### B. Register Signal

```python
# In planning/apps.py
from django.apps import AppConfig

class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.planning'
    
    def ready(self):
        import apps.planning.signals  # noqa
```

---

### 3. Workflow Completion Sync

**Requirement**: When a Transfer Workflow completes, automatically update the linked Planned Activity status to COMPLETED.

**Implementation**:

#### A. Signal Handler

```python
# In planning/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.batch.models import BatchTransferWorkflow

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

---

## Database Schema

### DDL Statements

```sql
-- Create planning_plannedactivity table
CREATE TABLE planning_plannedactivity (
    id BIGSERIAL PRIMARY KEY,
    scenario_id BIGINT NOT NULL REFERENCES scenario_scenario(id) ON DELETE CASCADE,
    batch_id BIGINT NOT NULL REFERENCES batch_batch(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    container_id BIGINT NULL REFERENCES infrastructure_container(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_by_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE PROTECT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    completed_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL,
    transfer_workflow_id BIGINT NULL REFERENCES batch_batchtransferworkflow(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX idx_plannedactivity_scenario_due_date ON planning_plannedactivity(scenario_id, due_date);
CREATE INDEX idx_plannedactivity_batch_status ON planning_plannedactivity(batch_id, status);
CREATE INDEX idx_plannedactivity_activity_type_status ON planning_plannedactivity(activity_type, status);

-- Create planning_activitytemplate table
CREATE TABLE planning_activitytemplate (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT NULL,
    lifecycle_stage_id BIGINT NULL REFERENCES batch_lifecyclestage(id) ON DELETE SET NULL,
    activity_type VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL,
    day_offset INTEGER NULL,
    weight_threshold_g NUMERIC(10,2) NULL,
    target_lifecycle_stage_id BIGINT NULL REFERENCES batch_lifecyclestage(id) ON DELETE SET NULL,
    notes_template TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Add linking field to batch_batchtransferworkflow
ALTER TABLE batch_batchtransferworkflow
ADD COLUMN planned_activity_id BIGINT NULL REFERENCES planning_plannedactivity(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX idx_batchtransferworkflow_planned_activity ON batch_batchtransferworkflow(planned_activity_id)
WHERE planned_activity_id IS NOT NULL;
```

---

## Migration Strategy

### Phase 1: Create Planning App

**Migration File**: `apps/planning/migrations/0001_initial.py`

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('scenario', '0001_initial'),
        ('batch', '0001_initial'),
        ('infrastructure', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlannedActivity',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('activity_type', models.CharField(max_length=50, choices=[
                    ('VACCINATION', 'Vaccination'),
                    ('TREATMENT', 'Treatment/Health Intervention'),
                    ('CULL', 'Culling'),
                    ('SALE', 'Sale/Harvest'),
                    ('FEED_CHANGE', 'Feed Strategy Change'),
                    ('TRANSFER', 'Transfer'),
                    ('MAINTENANCE', 'Maintenance'),
                    ('SAMPLING', 'Sampling'),
                    ('OTHER', 'Other'),
                ])),
                ('due_date', models.DateField()),
                ('status', models.CharField(max_length=20, default='PENDING', choices=[
                    ('PENDING', 'Pending'),
                    ('IN_PROGRESS', 'In Progress'),
                    ('COMPLETED', 'Completed'),
                    ('OVERDUE', 'Overdue'),
                    ('CANCELLED', 'Cancelled'),
                ])),
                ('notes', models.TextField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(null=True, blank=True)),
                ('scenario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='planned_activities',
                    to='scenario.scenario'
                )),
                ('batch', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='planned_activities',
                    to='batch.batch'
                )),
                ('container', models.ForeignKey(
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='infrastructure.container'
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='auth.user'
                )),
                ('completed_by', models.ForeignKey(
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='completed_activities',
                    to='auth.user'
                )),
            ],
            options={
                'db_table': 'planning_plannedactivity',
                'ordering': ['due_date', 'created_at'],
                'verbose_name': 'Planned Activity',
                'verbose_name_plural': 'Planned Activities',
            },
        ),
        migrations.CreateModel(
            name='ActivityTemplate',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('activity_type', models.CharField(max_length=50, choices=[...])),  # Same as PlannedActivity
                ('trigger_type', models.CharField(max_length=20, choices=[
                    ('DAY_OFFSET', 'Day Offset'),
                    ('WEIGHT_THRESHOLD', 'Weight Threshold'),
                    ('STAGE_TRANSITION', 'Stage Transition'),
                ])),
                ('day_offset', models.IntegerField(null=True, blank=True)),
                ('weight_threshold_g', models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)),
                ('notes_template', models.TextField(null=True, blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('lifecycle_stage', models.ForeignKey(
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='batch.lifecyclestage'
                )),
                ('target_lifecycle_stage', models.ForeignKey(
                    null=True,
                    blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='target_templates',
                    to='batch.lifecyclestage'
                )),
            ],
            options={
                'db_table': 'planning_activitytemplate',
                'ordering': ['name'],
                'verbose_name': 'Activity Template',
                'verbose_name_plural': 'Activity Templates',
            },
        ),
        migrations.AddIndex(
            model_name='plannedactivity',
            index=models.Index(fields=['scenario', 'due_date'], name='idx_plannedactivity_scenario_due_date'),
        ),
        migrations.AddIndex(
            model_name='plannedactivity',
            index=models.Index(fields=['batch', 'status'], name='idx_plannedactivity_batch_status'),
        ),
        migrations.AddIndex(
            model_name='plannedactivity',
            index=models.Index(fields=['activity_type', 'status'], name='idx_plannedactivity_activity_type_status'),
        ),
    ]
```

### Phase 2: Add Linking Field to BatchTransferWorkflow

**Migration File**: `apps/batch/migrations/0002_add_planned_activity_link.py`

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

### Phase 3: Add Transfer Workflow Link to PlannedActivity

**Migration File**: `apps/planning/migrations/0002_add_transfer_workflow_link.py`

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('planning', '0001_initial'),
        ('batch', '0002_add_planned_activity_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='plannedactivity',
            name='transfer_workflow',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='batch.batchtransferworkflow'
            ),
        ),
    ]
```

---

## References

1. AquaMind PRD - Section 3.1.2.1 Transfer Workflow Architecture
2. AquaMind Data Model - `batch_batchtransferworkflow` and `batch_transferaction` tables
3. Django Simple History Documentation - https://django-simple-history.readthedocs.io/
4. Django REST Framework Custom Actions - https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing

---

**End of Document**
