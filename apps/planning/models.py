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
            models.Index(fields=['scenario', 'due_date'], name='idx_pa_scenario_due_date'),
            models.Index(fields=['batch', 'status'], name='idx_pa_batch_status'),
            models.Index(fields=['activity_type', 'status'], name='idx_pa_type_status'),
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
        if self.status == 'COMPLETED':
            raise ValueError("Activity is already completed")
        
        if self.status == 'CANCELLED':
            raise ValueError("Cannot complete a cancelled activity")
        
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
        
        if self.status not in ['PENDING', 'IN_PROGRESS']:
            raise ValueError(f"Cannot spawn workflow for activity with status {self.status}")
        
        from apps.batch.models import BatchTransferWorkflow
        
        # Generate workflow_number
        workflow_number = f"TRF-PA-{self.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        workflow = BatchTransferWorkflow.objects.create(
            workflow_number=workflow_number,
            batch=self.batch,
            workflow_type=workflow_type,
            source_lifecycle_stage=source_lifecycle_stage,
            dest_lifecycle_stage=dest_lifecycle_stage,
            planned_start_date=self.due_date,
            planned_activity=self,
            initiated_by=self.created_by
        )
        
        self.transfer_workflow = workflow
        self.status = 'IN_PROGRESS'
        self.save()
        
        return workflow


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
            if self.day_offset is None:
                raise ValueError("day_offset is required for DAY_OFFSET trigger type")
            due_date = batch.created_at.date() + timedelta(days=self.day_offset)
        elif self.trigger_type == 'WEIGHT_THRESHOLD':
            if self.weight_threshold_g is None:
                raise ValueError("weight_threshold_g is required for WEIGHT_THRESHOLD trigger type")
            # Placeholder: Would need growth projection logic
            due_date = timezone.now().date() + timedelta(days=30)
        elif self.trigger_type == 'STAGE_TRANSITION':
            if self.target_lifecycle_stage is None:
                raise ValueError("target_lifecycle_stage is required for STAGE_TRANSITION trigger type")
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

