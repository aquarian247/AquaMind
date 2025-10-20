"""
BatchTransferWorkflow model for the batch app.

This model orchestrates batch transfer operations that may take days or weeks to complete.
It represents the LOGICAL transfer operation (e.g., "Fry → Parr transition") and manages
multiple TransferAction instances to track the execution of individual container movements.
"""
from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.batch.models.batch import Batch
from apps.batch.models.species import LifeCycleStage
from django.contrib.auth.models import User


class BatchTransferWorkflow(models.Model):
    """
    Orchestrates a batch transfer operation that may take days/weeks to complete.
    Represents the LOGICAL transfer operation (e.g., "Fry → Parr transition").
    
    State Machine: DRAFT → PLANNED → IN_PROGRESS → COMPLETED / CANCELLED
    """
    
    # Workflow Types
    WORKFLOW_TYPE_CHOICES = [
        ('LIFECYCLE_TRANSITION', 'Lifecycle Stage Transition'),
        ('CONTAINER_REDISTRIBUTION', 'Container Redistribution'),
        ('EMERGENCY_CASCADE', 'Emergency Cascading Transfer'),
        ('PARTIAL_HARVEST', 'Partial Harvest Preparation'),
    ]
    
    # Status Choices (State Machine)
    STATUS_CHOICES = [
        ('DRAFT', 'Draft - Planning'),
        ('PLANNED', 'Planned - Ready to Execute'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Identification
    workflow_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique workflow identifier (e.g., TRF-2024-001)"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        related_name='transfer_workflows',
        help_text="Batch being transferred"
    )
    
    # Transfer Type & Lifecycle Context
    workflow_type = models.CharField(
        max_length=30,
        choices=WORKFLOW_TYPE_CHOICES,
        default='LIFECYCLE_TRANSITION'
    )
    source_lifecycle_stage = models.ForeignKey(
        LifeCycleStage,
        on_delete=models.PROTECT,
        related_name='workflows_as_source',
        help_text="Source lifecycle stage"
    )
    dest_lifecycle_stage = models.ForeignKey(
        LifeCycleStage,
        on_delete=models.PROTECT,
        related_name='workflows_as_destination',
        null=True,
        blank=True,
        help_text="Destination lifecycle stage (if stage transition)"
    )
    
    # State Machine
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # Timeline
    planned_start_date = models.DateField(
        help_text="Planned start date for the workflow"
    )
    planned_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned completion date"
    )
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when first action was executed"
    )
    actual_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when last action was executed"
    )
    
    # Summary Metrics (Calculated from actions)
    total_source_count = models.PositiveIntegerField(
        default=0,
        help_text="Total fish in source containers"
    )
    total_transferred_count = models.PositiveIntegerField(
        default=0,
        help_text="Total fish transferred"
    )
    total_mortality_count = models.PositiveIntegerField(
        default=0,
        help_text="Total mortalities during transfer"
    )
    total_biomass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total biomass transferred (kg)"
    )
    
    # Progress Tracking
    total_actions_planned = models.PositiveIntegerField(
        default=0,
        help_text="Total number of actions planned"
    )
    actions_completed = models.PositiveIntegerField(
        default=0,
        help_text="Number of actions completed"
    )
    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Completion percentage (0-100)"
    )
    
    # Finance Integration
    is_intercompany = models.BooleanField(
        default=False,
        help_text="Whether this transfer crosses subsidiary boundaries"
    )
    source_subsidiary = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Source subsidiary (derived from containers)"
    )
    dest_subsidiary = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Destination subsidiary (derived from containers)"
    )
    finance_transaction = models.ForeignKey(
        'finance.IntercompanyTransaction',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfer_workflows',
        help_text="Associated intercompany transaction (if applicable)"
    )
    
    # Audit & Notes
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='initiated_transfer_workflows',
        help_text="User who created this workflow"
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='completed_transfer_workflows',
        help_text="User who completed this workflow"
    )
    notes = models.TextField(
        blank=True,
        help_text="General notes about the workflow"
    )
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation (if cancelled)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['planned_start_date']),
            models.Index(fields=['workflow_type']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Batch Transfer Workflow'
        verbose_name_plural = 'Batch Transfer Workflows'
    
    def __str__(self):
        return f"{self.workflow_number} - {self.batch.batch_number} ({self.get_status_display()})"
    
    def can_add_actions(self):
        """Can only add actions in DRAFT or PLANNED status"""
        return self.status in ['DRAFT', 'PLANNED']
    
    def can_execute_actions(self):
        """Can only execute in PLANNED or IN_PROGRESS status"""
        return self.status in ['PLANNED', 'IN_PROGRESS']
    
    def can_cancel(self):
        """Can cancel if not already completed or cancelled"""
        return self.status not in ['COMPLETED', 'CANCELLED']
    
    def mark_in_progress(self):
        """
        Auto-called when first action is executed.
        Transitions from PLANNED to IN_PROGRESS.
        """
        if self.status == 'PLANNED' and not self.actual_start_date:
            self.status = 'IN_PROGRESS'
            self.actual_start_date = timezone.now().date()
            self.save(update_fields=['status', 'actual_start_date', 'updated_at'])
    
    def check_completion(self):
        """
        Auto-called after each action completes.
        Transitions to COMPLETED when all actions are done.
        """
        if self.status == 'IN_PROGRESS':
            if self.actions_completed >= self.total_actions_planned:
                self.status = 'COMPLETED'
                self.actual_completion_date = timezone.now().date()
                self.save(update_fields=['status', 'actual_completion_date', 'updated_at'])
                
                # Trigger finance integration if intercompany
                if self.is_intercompany and not self.finance_transaction:
                    self._create_intercompany_transaction()
    
    def update_progress(self):
        """Recalculate completion percentage from actions"""
        if self.total_actions_planned > 0:
            self.completion_percentage = (
                Decimal(self.actions_completed) / 
                Decimal(self.total_actions_planned) * 100
            )
            self.save(update_fields=[
                'actions_completed',
                'completion_percentage',
                'updated_at'
            ])
    
    def recalculate_totals(self):
        """Recalculate summary metrics from all actions"""
        from apps.batch.models.workflow_action import TransferAction
        
        actions = self.actions.all()
        
        self.total_source_count = sum(a.source_population_before for a in actions)
        self.total_transferred_count = sum(a.transferred_count for a in actions if a.status == 'COMPLETED')
        self.total_mortality_count = sum(a.mortality_during_transfer for a in actions if a.status == 'COMPLETED')
        self.total_biomass_kg = sum(a.transferred_biomass_kg for a in actions if a.status == 'COMPLETED')
        
        self.save(update_fields=[
            'total_source_count',
            'total_transferred_count',
            'total_mortality_count',
            'total_biomass_kg',
            'updated_at'
        ])
    
    def plan_workflow(self):
        """
        Finalize the workflow to PLANNED status.
        Must have at least one action to plan.
        """
        if self.status != 'DRAFT':
            from django.core.exceptions import ValidationError
            raise ValidationError("Can only plan workflows in DRAFT status")
        
        if self.total_actions_planned == 0:
            from django.core.exceptions import ValidationError
            raise ValidationError("Cannot plan workflow with zero actions")
        
        self.status = 'PLANNED'
        self.save(update_fields=['status', 'updated_at'])
    
    def cancel_workflow(self, reason, cancelled_by):
        """Cancel the workflow with a reason"""
        if not self.can_cancel():
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Cannot cancel workflow in {self.status} status")
        
        self.status = 'CANCELLED'
        self.cancellation_reason = reason
        self.completed_by = cancelled_by
        self.save(update_fields=['status', 'cancellation_reason', 'completed_by', 'updated_at'])
    
    def detect_intercompany(self):
        """
        Determine if transfer crosses subsidiary boundaries.
        Called automatically when actions are added.
        """
        from apps.batch.models.workflow_action import TransferAction
        
        actions = self.actions.select_related(
            'source_assignment__container__hall__freshwater_station',
            'source_assignment__container__area',
            'dest_assignment__container__hall__freshwater_station',
            'dest_assignment__container__area'
        ).all()
        
        if not actions:
            return False
        
        source_subs = set()
        dest_subs = set()
        
        for action in actions:
            # Determine source subsidiary
            if action.source_assignment:
                container = action.source_assignment.container
                if container.hall:
                    source_subs.add('FRESHWATER')
                elif container.area:
                    source_subs.add('FARMING')
            
            # Determine destination subsidiary
            if action.dest_assignment:
                container = action.dest_assignment.container
                if container.hall:
                    dest_subs.add('FRESHWATER')
                elif container.area:
                    dest_subs.add('FARMING')
        
        # Intercompany if subsidiaries differ
        if source_subs and dest_subs and source_subs != dest_subs:
            self.is_intercompany = True
            self.source_subsidiary = list(source_subs)[0] if source_subs else None
            self.dest_subsidiary = list(dest_subs)[0] if dest_subs else None
            self.save(update_fields=['is_intercompany', 'source_subsidiary', 'dest_subsidiary', 'updated_at'])
            return True
        
        return False
    
    def _create_intercompany_transaction(self):
        """
        Create IntercompanyTransaction when transfer completes.
        Called automatically when workflow transitions to COMPLETED.
        
        Uses TransferFinanceService to:
        - Lookup pricing policy
        - Calculate transfer value
        - Create transaction in PENDING state
        """
        if not self.is_intercompany or self.finance_transaction:
            return
        
        # Import here to avoid circular dependency
        from apps.finance.services.transfer_finance import (
            TransferFinanceService,
            TransferFinanceError,
        )
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            service = TransferFinanceService(self)
            transaction = service.create_transaction()
            
            self.finance_transaction = transaction
            self.save(update_fields=['finance_transaction', 'updated_at'])
            
            logger.info(
                f"Created intercompany transaction {transaction.tx_id} "
                f"for workflow {self.workflow_number}"
            )
            
        except TransferFinanceError as e:
            logger.error(
                f"Failed to create intercompany transaction for workflow "
                f"{self.workflow_number}: {e}"
            )
            # Don't raise - workflow is still COMPLETED
            # Finance team can create transaction manually if needed
