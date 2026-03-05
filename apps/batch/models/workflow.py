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
    ]

    DYNAMIC_ROUTE_MODE_CHOICES = [
        ("DIRECT_STATION_TO_VESSEL", "Direct Station to Vessel"),
        ("VIA_TRUCK_TO_VESSEL", "Via Truck to Vessel"),
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
    planned_activity = models.OneToOneField(
        'planning.PlannedActivity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='spawned_workflow',
        help_text="Planned activity that spawned this workflow (if any)"
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
    is_dynamic_execution = models.BooleanField(
        default=False,
        help_text=(
            "When true, actions are created during execution time by ship crew "
            "instead of pre-defined during planning."
        ),
    )
    dynamic_route_mode = models.CharField(
        max_length=32,
        choices=DYNAMIC_ROUTE_MODE_CHOICES,
        null=True,
        blank=True,
        help_text=(
            "Dynamic route pattern for station-to-sea workflows. "
            "Required when is_dynamic_execution is true."
        ),
    )
    estimated_total_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional operator estimate of total count to move.",
    )
    estimated_total_biomass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional operator estimate of total biomass to move.",
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
    dynamic_completed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dynamically_completed_transfer_workflows",
        help_text="User who explicitly completed a dynamic workflow.",
    )
    dynamic_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of explicit dynamic workflow completion.",
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

    def save(self, *args, **kwargs):
        """Auto-enable dynamic mode for station-to-sea lifecycle transitions."""
        if self._state.adding and not self.is_dynamic_execution:
            self.is_dynamic_execution = self.infer_dynamic_execution()
        super().save(*args, **kwargs)
    
    def can_add_actions(self):
        """Allow adding actions while executing only for dynamic workflows."""
        if self.is_dynamic_execution:
            return self.status == "IN_PROGRESS"
        return self.status in ["DRAFT", "PLANNED"]
    
    def can_execute_actions(self):
        """Can only execute in PLANNED or IN_PROGRESS status"""
        return self.status in ['PLANNED', 'IN_PROGRESS']
    
    def can_cancel(self):
        """Can cancel if not already completed or cancelled"""
        return self.status not in ['COMPLETED', 'CANCELLED']

    @property
    def is_vessel_transfer(self):
        """True if any action source/destination involves vessel carrier tanks."""
        actions = self.actions.select_related(
            'source_assignment__container__carrier',
            'dest_assignment__container__carrier',
        )
        for action in actions:
            source_carrier = (
                action.source_assignment.container.carrier
                if action.source_assignment and action.source_assignment.container
                else None
            )
            dest_carrier = (
                action.dest_assignment.container.carrier
                if action.dest_assignment and action.dest_assignment.container
                else None
            )
            if (source_carrier and source_carrier.carrier_type == 'VESSEL') or (
                dest_carrier and dest_carrier.carrier_type == 'VESSEL'
            ):
                return True
        return False

    def infer_dynamic_execution(self):
        """
        Heuristic default for station-to-sea planning when not explicitly set.

        Dynamic mode is enabled for common station-to-sea lifecycle transitions.
        """
        if self.workflow_type != 'LIFECYCLE_TRANSITION':
            return False
        if not self.source_lifecycle_stage or not self.dest_lifecycle_stage:
            return False

        source_name = (self.source_lifecycle_stage.name or '').strip().lower()
        dest_name = (self.dest_lifecycle_stage.name or '').strip().lower()

        station_like_sources = {'fry', 'parr', 'smolt', 'post-smolt'}
        sea_like_destinations = {'post-smolt', 'adult'}
        return source_name in station_like_sources and dest_name in sea_like_destinations

    def get_allowed_leg_types(self):
        """Allowed handoff leg types for the configured dynamic route mode."""
        if self.dynamic_route_mode == "DIRECT_STATION_TO_VESSEL":
            return ["STATION_TO_VESSEL", "VESSEL_TO_RING"]
        if self.dynamic_route_mode == "VIA_TRUCK_TO_VESSEL":
            return ["STATION_TO_TRUCK", "TRUCK_TO_VESSEL", "VESSEL_TO_RING"]
        return []
    
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
        if self.is_dynamic_execution:
            return
        if self.status == 'IN_PROGRESS':
            if self.actions_completed >= self.total_actions_planned:
                self.status = 'COMPLETED'
                self.actual_completion_date = timezone.now().date()
                self.save(update_fields=['status', 'actual_completion_date', 'updated_at'])
                
                # Update linked planned activity if exists
                if self.planned_activity and self.planned_activity.status != 'COMPLETED':
                    self.planned_activity.mark_completed(user=self.completed_by or self.initiated_by)
                
                # Trigger finance integration if intercompany
                if self.is_intercompany and not self.finance_transaction:
                    self._create_intercompany_transaction()
    
    def update_progress(self):
        """Recalculate completion percentage from actions"""
        if self.is_dynamic_execution:
            self.recalculate_totals()
            if self.estimated_total_count and self.estimated_total_count > 0:
                ratio = Decimal(self.total_transferred_count) / Decimal(self.estimated_total_count)
                self.completion_percentage = min(Decimal("100.00"), ratio * Decimal("100"))
            elif self.estimated_total_biomass_kg and self.estimated_total_biomass_kg > 0:
                ratio = Decimal(self.total_biomass_kg) / Decimal(self.estimated_total_biomass_kg)
                self.completion_percentage = min(Decimal("100.00"), ratio * Decimal("100"))
            else:
                self.completion_percentage = Decimal("0.00")

            self.save(update_fields=[
                "actions_completed",
                "completion_percentage",
                "updated_at",
            ])
            return

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
        
        if self.total_actions_planned == 0 and not self.is_dynamic_execution:
            from django.core.exceptions import ValidationError
            raise ValidationError("Cannot plan workflow with zero actions")

        if self.is_dynamic_execution:
            if self.actions.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Dynamic workflow planning is intent-only. "
                    "Remove pre-planned actions before planning."
                )
            if not self.dynamic_route_mode:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Dynamic route mode is required for dynamic workflows."
                )
        
        # Detect if this is an intercompany transfer
        self.detect_intercompany()
        
        self.status = 'PLANNED'
        self.save(update_fields=['status', 'updated_at'])

    def complete_dynamic(self, *, completed_by, completion_note: str = ""):
        """
        Explicit completion for dynamic workflows.

        Dynamic workflows never auto-complete by action count. Completion
        requires an operator action after all active handoffs are finalized.
        """
        from django.core.exceptions import ValidationError

        if not self.is_dynamic_execution:
            raise ValidationError("Use standard completion flow for non-dynamic workflows.")
        if self.status in ["COMPLETED", "CANCELLED"]:
            raise ValidationError(f"Workflow is already {self.status}.")

        in_progress_count = self.actions.filter(status="IN_PROGRESS").count()
        if in_progress_count > 0:
            raise ValidationError(
                "Cannot complete workflow while handoffs are still IN_PROGRESS."
            )

        completed_actions = self.actions.filter(status="COMPLETED")
        if not completed_actions.exists():
            raise ValidationError(
                "Dynamic workflow must contain at least one completed handoff."
            )

        self.actions_completed = completed_actions.count()
        self.recalculate_totals()
        self.update_progress()

        self.status = "COMPLETED"
        self.actual_completion_date = timezone.now().date()
        self.completed_by = completed_by
        self.dynamic_completed_by = completed_by
        self.dynamic_completed_at = timezone.now()
        if completion_note:
            prefix = "[dynamic_completion_note]"
            note_line = f"{prefix} {completion_note.strip()}"
            self.notes = f"{self.notes}\n{note_line}".strip()

        self.save(
            update_fields=[
                "status",
                "actual_completion_date",
                "completed_by",
                "dynamic_completed_by",
                "dynamic_completed_at",
                "actions_completed",
                "completion_percentage",
                "notes",
                "updated_at",
            ]
        )

        if self.planned_activity and self.planned_activity.status != "COMPLETED":
            self.planned_activity.mark_completed(user=completed_by)

        if self.is_intercompany and not self.finance_transaction:
            self._create_intercompany_transaction()
    
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
