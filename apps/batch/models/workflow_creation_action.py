"""
Creation Action model for batch creation workflows.

Tracks individual egg delivery actions to specific containers (trays/tanks).
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.batch.models.assignment import BatchContainerAssignment
from apps.batch.models.workflow_creation import BatchCreationWorkflow

User = get_user_model()


class CreationAction(models.Model):
    """
    Individual egg delivery/placement action within a batch creation workflow.
    
    Tracks delivery of eggs to destination container (tray/tank).
    NO source_assignment - eggs come from external source or broodstock facility.
    """
    
    # Action Status Choices
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('SKIPPED', 'Skipped'),
    ]
    
    # Delivery Method Choices
    DELIVERY_METHOD_CHOICES = [
        ('TRANSPORT', 'Ground Transport'),
        ('HELICOPTER', 'Helicopter'),
        ('BOAT', 'Boat'),
        ('INTERNAL_TRANSFER', 'Internal Facility Transfer'),
    ]
    
    # Identification
    workflow = models.ForeignKey(
        BatchCreationWorkflow,
        on_delete=models.CASCADE,
        related_name='actions',
        help_text="Parent batch creation workflow"
    )
    action_number = models.PositiveIntegerField(
        help_text="Sequential action number within workflow (1, 2, 3...)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Destination (only - no source for creation)
    dest_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        related_name='creation_actions_as_dest',
        help_text="Destination container assignment (tray/tank)"
    )
    
    # Delivery Details
    egg_count_planned = models.PositiveIntegerField(
        help_text="Number of eggs planned for this delivery"
    )
    egg_count_actual = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Actual number of eggs delivered (if different from planned)"
    )
    mortality_on_arrival = models.PositiveIntegerField(
        default=0,
        help_text="Number of eggs DOA (dead on arrival)"
    )
    
    # Timing
    expected_delivery_date = models.DateField(
        help_text="Expected delivery date for this action"
    )
    actual_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual delivery date (when executed)"
    )
    
    # Execution Details
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="Method of egg delivery"
    )
    water_temp_on_arrival = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Water temperature in destination container (°C)"
    )
    egg_quality_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Visual egg quality score on arrival (1=poor, 5=excellent)"
    )
    execution_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of delivery operation (minutes)"
    )
    
    # User Attribution
    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='executed_creation_actions',
        null=True,
        blank=True,
        help_text="User who executed this delivery"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Notes about this delivery (transport conditions, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'batch_creationaction'
        ordering = ['workflow', 'action_number']
        constraints = [
            models.UniqueConstraint(
                fields=['workflow', 'action_number'],
                name='creation_action_workflow_number_uniq'
            )
        ]
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['expected_delivery_date']),
        ]
    
    def __str__(self):
        return f"{self.workflow.workflow_number} - Action #{self.action_number}"
    
    @property
    def dest_container_name(self):
        """Helper to get destination container name."""
        return self.dest_assignment.container.name if self.dest_assignment else None
    
    def execute(self, **execution_data):
        """
        Execute this delivery action.
        
        Args:
            mortality_on_arrival: Number of eggs DOA
            delivery_method: How eggs were delivered
            water_temp_on_arrival: Water temperature (°C)
            egg_quality_score: Quality score (1-5)
            execution_duration_minutes: Duration of operation
            executed_by: User performing execution
            notes: Additional notes
            
        Updates:
            - Action status to COMPLETED
            - Destination assignment population
            - Workflow progress counters
            - Batch status (PLANNED → RECEIVING on first action)
        """
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            # Validate
            if self.status not in ['PENDING', 'FAILED']:
                raise ValidationError(
                    f"Cannot execute action in {self.status} status"
                )
            
            # Update action status
            self.status = 'IN_PROGRESS'
            self.actual_delivery_date = timezone.now().date()
            self.executed_by = execution_data.get('executed_by')
            
            # Record execution details
            self.mortality_on_arrival = execution_data.get('mortality_on_arrival', 0)
            self.delivery_method = execution_data.get('delivery_method')
            self.water_temp_on_arrival = execution_data.get('water_temp_on_arrival')
            self.egg_quality_score = execution_data.get('egg_quality_score')
            self.execution_duration_minutes = execution_data.get('execution_duration_minutes')
            self.notes = execution_data.get('notes', '')
            
            # Calculate actual eggs received
            planned_eggs = self.egg_count_planned
            doa = self.mortality_on_arrival
            actual_received = planned_eggs - doa
            self.egg_count_actual = actual_received
            
            # Update destination assignment population (use F() for atomic increment)
            from django.db.models import F
            
            BatchContainerAssignment.objects.filter(id=self.dest_assignment.id).update(
                population_count=F('population_count') + actual_received,
                is_active=True
            )
            # Refresh to get updated value
            self.dest_assignment.refresh_from_db()
            
            # Mark action completed
            self.status = 'COMPLETED'
            self.save()
            
            # Update workflow progress counters
            self.workflow.actions_completed += 1
            self.workflow.total_eggs_received += actual_received
            self.workflow.total_mortality_on_arrival += doa
            
            # Update batch status if first action
            if self.workflow.actions_completed == 1:
                self.workflow.status = 'IN_PROGRESS'
                self.workflow.actual_start_date = self.actual_delivery_date
                self.workflow.batch.status = 'RECEIVING'
                self.workflow.batch.save(update_fields=['status'])
                self.workflow.save()  # Save all fields after first action
            else:
                # Just save counter updates
                self.workflow.save(update_fields=[
                    'actions_completed',
                    'total_eggs_received', 
                    'total_mortality_on_arrival',
                ])
            
            # Update progress percentage (saves workflow again)
            self.workflow.update_progress()
            
            # Check if workflow complete
            self.workflow.check_completion()
    
    def skip(self, reason, user):
        """
        Skip this action (e.g. delivery cancelled).
        
        Args:
            reason: Why action was skipped
            user: User performing skip
        """
        if self.status not in ['PENDING']:
            raise ValidationError(
                f"Cannot skip action in {self.status} status"
            )
        
        self.status = 'SKIPPED'
        self.notes = f"Skipped: {reason}\n{self.notes}"
        self.executed_by = user
        self.save()
        
        # Skipped actions don't count toward completion
        # but should update total_actions if workflow logic requires it

