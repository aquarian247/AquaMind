"""
Batch Creation Workflow models for the batch app.

This module defines models for managing batch creation workflows, which handle
the process of bringing new eggs into the system and distributing them across
containers (incubation trays).
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from simple_history.models import HistoricalRecords

User = get_user_model()


class BatchCreationWorkflow(models.Model):
    """
    Workflow for creating a new batch from eggs (external or internal broodstock).
    
    Unlike transfer workflows, creation workflows:
    - Create the batch when workflow is created (status: PLANNED)
    - Have no source containers (eggs from supplier/broodstock)
    - Track egg delivery to multiple destination containers over time
    - Can integrate with finance for internal egg transfers
    """
    
    # Workflow Status Choices
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Egg Source Type Choices
    EGG_SOURCE_TYPE_CHOICES = [
        ('INTERNAL', 'Internal Broodstock'),
        ('EXTERNAL', 'External Supplier'),
    ]
    
    # Identification
    workflow_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique workflow identifier (e.g. CRT-2025-001)"
    )
    
    # Linked Batch (created when workflow is created)
    batch = models.ForeignKey(
        'batch.Batch',
        on_delete=models.CASCADE,
        related_name='creation_workflows',
        help_text="Batch created by this workflow (status: PLANNED initially)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # Egg Source
    egg_source_type = models.CharField(
        max_length=20,
        choices=EGG_SOURCE_TYPE_CHOICES,
        help_text="Whether eggs are from internal broodstock or external supplier"
    )
    
    # Internal Source (if egg_source_type = 'INTERNAL')
    egg_production = models.ForeignKey(
        'broodstock.EggProduction',
        on_delete=models.PROTECT,
        related_name='creation_workflows',
        null=True,
        blank=True,
        help_text="Link to broodstock egg production event (if internal)"
    )
    
    # External Source (if egg_source_type = 'EXTERNAL')
    external_supplier = models.ForeignKey(
        'broodstock.EggSupplier',
        on_delete=models.PROTECT,
        related_name='creation_workflows',
        null=True,
        blank=True,
        help_text="External egg supplier (if not internal broodstock)"
    )
    external_supplier_batch_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Supplier's batch/lot number for traceability"
    )
    external_cost_per_thousand = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost per 1000 eggs (for external procurement)"
    )
    
    # Planned Quantities
    total_eggs_planned = models.PositiveIntegerField(
        help_text="Total eggs expected to be delivered across all actions"
    )
    
    # Actual Quantities (updated as actions execute)
    total_eggs_received = models.PositiveIntegerField(
        default=0,
        help_text="Actual eggs received (planned - mortality)"
    )
    total_mortality_on_arrival = models.PositiveIntegerField(
        default=0,
        help_text="Total DOA (dead on arrival) eggs"
    )
    
    # Timing
    planned_start_date = models.DateField(
        help_text="When first delivery is planned"
    )
    planned_completion_date = models.DateField(
        help_text="When all deliveries should be complete"
    )
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When first delivery actually occurred"
    )
    actual_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="When all deliveries were actually completed"
    )
    
    # Progress Tracking
    total_actions = models.PositiveIntegerField(
        default=0,
        help_text="Total number of delivery actions"
    )
    actions_completed = models.PositiveIntegerField(
        default=0,
        help_text="Number of actions completed"
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Percentage of actions completed"
    )
    
    # User Attribution
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='created_creation_workflows',
        null=True,
        help_text="User who created this workflow"
    )
    
    # Cancellation
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation (required if status = CANCELLED)"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When workflow was cancelled"
    )
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='cancelled_creation_workflows',
        null=True,
        blank=True,
        help_text="User who cancelled this workflow"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="General notes about this batch creation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'batch_creationworkflow'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['egg_source_type']),
            models.Index(fields=['planned_start_date']),
        ]
    
    def __str__(self):
        return f"{self.workflow_number} - {self.batch.batch_number}"
    
    def clean(self):
        """Validate egg source consistency."""
        if self.egg_source_type == 'INTERNAL':
            if not self.egg_production:
                raise ValidationError({
                    'egg_production': 'Internal egg source requires egg_production link'
                })
            if self.external_supplier:
                raise ValidationError({
                    'external_supplier': 'Internal egg source cannot have external_supplier'
                })
        elif self.egg_source_type == 'EXTERNAL':
            if not self.external_supplier:
                raise ValidationError({
                    'external_supplier': 'External egg source requires external_supplier'
                })
            if self.egg_production:
                raise ValidationError({
                    'egg_production': 'External egg source cannot have egg_production link'
                })
    
    def can_add_actions(self):
        """Check if actions can be added to this workflow."""
        return self.status in ['DRAFT', 'PLANNED']
    
    def can_plan(self):
        """Check if workflow can be planned (locked for execution)."""
        return self.status == 'DRAFT' and self.total_actions > 0
    
    def can_cancel(self):
        """
        Check if workflow can be cancelled.
        
        Rule: Can only cancel if NO actions have been executed.
        Once eggs physically arrive, they must be managed (cannot just "cancel" them).
        """
        return self.status in ['DRAFT', 'PLANNED'] and self.actions_completed == 0
    
    def update_progress(self):
        """Recalculate progress percentage."""
        if self.total_actions > 0:
            self.progress_percentage = Decimal(
                (self.actions_completed / self.total_actions) * 100
            ).quantize(Decimal('0.01'))
        else:
            self.progress_percentage = Decimal('0.00')
        self.save(update_fields=['progress_percentage'])
    
    def check_completion(self):
        """
        Check if workflow is complete and update status accordingly.
        
        Called after each action execution to see if all actions are done.
        """
        if self.actions_completed >= self.total_actions and self.total_actions > 0:
            self.status = 'COMPLETED'
            self.actual_completion_date = timezone.now().date()
            self.batch.status = 'ACTIVE'  # Batch becomes active when all eggs delivered
            self.batch.save(update_fields=['status'])
            self.save(update_fields=['status', 'actual_completion_date'])
            
            # Trigger finance integration if internal eggs
            if self.egg_source_type == 'INTERNAL':
                self._create_intercompany_transaction()
    
    def _create_intercompany_transaction(self):
        """
        Create intercompany transaction for internal egg transfer.
        
        Called automatically when workflow completes (all actions executed).
        Uses existing finance app infrastructure.
        """
        try:
            from apps.finance.services.transfer_finance import TransferFinanceService
            
            service = TransferFinanceService()
            service.create_egg_delivery_transaction(self)
        except Exception as e:
            # Log error but don't fail workflow completion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to create intercompany transaction for workflow {self.workflow_number}: {e}"
            )
    
    def cancel(self, reason, user):
        """
        Cancel this workflow.
        
        Args:
            reason: Cancellation reason
            user: User performing cancellation
            
        Raises:
            ValidationError: If workflow cannot be cancelled
        """
        if not self.can_cancel():
            raise ValidationError(
                "Cannot cancel workflow - eggs already delivered to containers. "
                "Once eggs physically arrive, they must be managed through normal batch operations."
            )
        
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            self.status = 'CANCELLED'
            self.cancellation_reason = reason
            self.cancelled_at = timezone.now()
            self.cancelled_by = user
            
            # Update batch status
            self.batch.status = 'CANCELLED'
            self.batch.save(update_fields=['status'])
            
            self.save(update_fields=[
                'status', 'cancellation_reason', 'cancelled_at', 'cancelled_by'
            ])
            
            # Broodstock linkage is preserved for audit trail
            # (don't delete broodstock_batchparentage records)

