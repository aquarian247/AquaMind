"""
TransferAction model for the batch app.

This model represents individual container-to-container transfer actions within a workflow.
Each action represents ONE physical movement of fish and tracks its execution details.
"""
from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.batch.models.workflow import BatchTransferWorkflow
from apps.batch.models.assignment import BatchContainerAssignment
from django.contrib.auth.models import User


class TransferAction(models.Model):
    """
    Individual container-to-container transfer action within a workflow.
    Each action represents ONE physical movement of fish.
    
    State Machine: PENDING → IN_PROGRESS → COMPLETED / FAILED / SKIPPED
    """
    
    # Status Choices
    STATUS_CHOICES = [
        ('PENDING', 'Pending - Not Started'),
        ('IN_PROGRESS', 'In Progress - Being Executed'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed - Rolled Back'),
        ('SKIPPED', 'Skipped'),
    ]
    
    # Transfer Method Choices
    TRANSFER_METHOD_CHOICES = [
        ('NET', 'Net Transfer'),
        ('PUMP', 'Pump Transfer'),
        ('GRAVITY', 'Gravity Transfer'),
        ('MANUAL', 'Manual Bucket Transfer'),
    ]
    
    # Core Relationships
    workflow = models.ForeignKey(
        BatchTransferWorkflow,
        on_delete=models.CASCADE,
        related_name='actions',
        help_text="Parent workflow this action belongs to"
    )
    action_number = models.PositiveIntegerField(
        help_text="Sequence number within workflow (1, 2, 3...)"
    )
    
    # What's being moved
    source_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        related_name='transfer_actions_as_source',
        help_text="Source batch-container assignment"
    )
    dest_assignment = models.ForeignKey(
        BatchContainerAssignment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfer_actions_as_dest',
        help_text="Destination batch-container assignment (created during execution)"
    )
    
    # Counts & Biomass
    source_population_before = models.PositiveIntegerField(
        help_text="Population in source container before this action"
    )
    transferred_count = models.PositiveIntegerField(
        help_text="Number of fish to transfer"
    )
    mortality_during_transfer = models.PositiveIntegerField(
        default=0,
        help_text="Number of mortalities during transfer"
    )
    transferred_biomass_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Biomass transferred (kg)"
    )
    
    # Status & Timeline
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    planned_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned execution date"
    )
    actual_execution_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual execution date"
    )
    
    # Transfer Details
    transfer_method = models.CharField(
        max_length=20,
        choices=TRANSFER_METHOD_CHOICES,
        null=True,
        blank=True,
        help_text="Method used for transfer"
    )
    
    # Environmental Conditions During Transfer
    water_temp_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Water temperature during transfer (°C)"
    )
    oxygen_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Oxygen level during transfer (mg/L)"
    )
    
    # Measured Weight Data (for growth assimilation anchors)
    measured_avg_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Measured Average Weight (g)",
        help_text="Measured average weight during transfer (grams). Used as anchor for daily state calculations."
    )
    measured_std_dev_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Measured Std Dev Weight (g)",
        help_text="Standard deviation of measured weights (grams)."
    )
    measured_sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Measured Sample Size",
        help_text="Number of fish sampled for weight measurement."
    )
    measured_avg_length_cm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Measured Average Length (cm)",
        help_text="Measured average length during transfer (cm)."
    )
    measured_notes = models.TextField(
        blank=True,
        verbose_name="Measurement Notes",
        help_text="Notes about the weight measurements taken during transfer."
    )
    
    # Selection Method Choices
    SELECTION_METHOD_CHOICES = [
        ('AVERAGE', 'Average - Representative Sample'),
        ('LARGEST', 'Largest - Selection Bias Towards Larger Fish'),
        ('SMALLEST', 'Smallest - Selection Bias Towards Smaller Fish'),
    ]
    
    selection_method = models.CharField(
        max_length=16,
        choices=SELECTION_METHOD_CHOICES,
        default='AVERAGE',
        blank=True,
        verbose_name="Selection Method",
        help_text="Method used to select fish for transfer. Affects weight calculation bias."
    )
    
    # Execution Details
    executed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='executed_transfer_actions',
        help_text="User who executed this action"
    )
    execution_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of transfer in minutes"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about this specific action"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # History tracking
    history = HistoricalRecords()
    
    class Meta:
        unique_together = ['workflow', 'action_number']
        ordering = ['workflow', 'action_number']
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['actual_execution_date']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Transfer Action'
        verbose_name_plural = 'Transfer Actions'
    
    def __str__(self):
        source_container = self.source_assignment.container.name if self.source_assignment else "Unknown"
        dest_container = self.dest_assignment.container.name if self.dest_assignment else "TBD"
        return f"Action #{self.action_number}: {source_container} → {dest_container} ({self.get_status_display()})"
    
    def clean(self):
        """Validate the action before saving"""
        super().clean()
        
        # Validate workflow can accept actions
        if self.workflow and not self.workflow.can_add_actions():
            raise ValidationError(
                f"Cannot add actions to workflow in {self.workflow.status} status"
            )
        
        # Validate transfer count
        if self.transferred_count <= 0:
            raise ValidationError("Transferred count must be greater than zero")
        
        # Validate source has enough fish
        if self.source_assignment and self.transferred_count > self.source_assignment.population_count:
            raise ValidationError(
                f"Cannot transfer {self.transferred_count} fish from container "
                f"with only {self.source_assignment.population_count} fish"
            )
    
    def execute(self, executed_by, mortality_count=0, **execution_details):
        """
        Execute this transfer action.
        
        Args:
            executed_by: User executing the action
            mortality_count: Number of mortalities during transfer
            **execution_details: Additional details (transfer_method, water_temp_c, oxygen_level, 
                                 execution_duration_minutes, notes)
        
        Returns:
            dict: Execution result with status and updated workflow info
        
        Raises:
            ValidationError: If action cannot be executed
        """
        # Validate we can execute
        if self.status != 'PENDING':
            raise ValidationError(
                f"Cannot execute action in {self.status} status. "
                f"Action must be PENDING to execute."
            )
        
        if not self.workflow.can_execute_actions():
            raise ValidationError(
                f"Cannot execute actions on workflow in {self.workflow.status} status"
            )
        
        with transaction.atomic():
            # Lock source assignment to prevent race conditions
            source = BatchContainerAssignment.objects.select_for_update().get(
                pk=self.source_assignment_id
            )
            
            # Validate population
            total_reduction = self.transferred_count + mortality_count
            if total_reduction > source.population_count:
                raise ValidationError(
                    f"Cannot transfer {total_reduction} fish "
                    f"(including {mortality_count} mortalities) "
                    f"from container with {source.population_count} fish"
                )
            
            # Update source assignment
            source.population_count -= total_reduction
            if source.population_count == 0:
                source.is_active = False
                source.departure_date = timezone.now().date()
            source.save()
            
            # Create or update destination assignment if provided
            if self.dest_assignment:
                dest = self.dest_assignment
                dest.population_count += self.transferred_count
                # Update biomass
                if dest.avg_weight_g and self.transferred_count > 0:
                    dest.biomass_kg = (dest.population_count * dest.avg_weight_g) / 1000
                dest.save()
            
            # Update this action with execution details
            self.status = 'COMPLETED'
            self.actual_execution_date = timezone.now().date()
            self.executed_by = executed_by
            self.mortality_during_transfer = mortality_count
            
            # Apply optional execution details
            for key, value in execution_details.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.save()
            
            # Update workflow status and progress
            self.workflow.mark_in_progress()
            self.workflow.actions_completed += 1
            self.workflow.update_progress()
            self.workflow.check_completion()
            self.workflow.recalculate_totals()
            
            return {
                'action_id': self.id,
                'action_status': self.status,
                'workflow_status': self.workflow.status,
                'completion_percentage': float(self.workflow.completion_percentage),
                'actions_remaining': self.workflow.total_actions_planned - self.workflow.actions_completed
            }
    
    def skip(self, reason, skipped_by):
        """Skip this action with a reason"""
        if self.status != 'PENDING':
            raise ValidationError(f"Cannot skip action in {self.status} status")
        
        self.status = 'SKIPPED'
        self.notes = f"Skipped by {skipped_by.username}: {reason}\n\n{self.notes}"
        self.save(update_fields=['status', 'notes', 'updated_at'])
        
        # Update workflow progress
        self.workflow.actions_completed += 1
        self.workflow.update_progress()
        self.workflow.check_completion()
    
    def rollback(self, reason):
        """
        Mark action as failed and prepare for retry.
        Note: This doesn't reverse database changes - manual intervention required.
        """
        if self.status not in ['IN_PROGRESS', 'COMPLETED']:
            raise ValidationError(
                f"Cannot rollback action in {self.status} status"
            )
        
        self.status = 'FAILED'
        self.notes = f"FAILED: {reason}\n\n{self.notes}"
        self.save(update_fields=['status', 'notes', 'updated_at'])
        
        # Decrement workflow completion if was counted
        if self.workflow.actions_completed > 0:
            self.workflow.actions_completed -= 1
            self.workflow.update_progress()
            self.workflow.save(update_fields=['actions_completed', 'updated_at'])
    
    def retry(self):
        """Reset failed action to pending for retry"""
        if self.status != 'FAILED':
            raise ValidationError("Can only retry failed actions")
        
        self.status = 'PENDING'
        self.notes = f"[RETRY] {self.notes}"
        self.save(update_fields=['status', 'notes', 'updated_at'])
    
    def save(self, *args, **kwargs):
        """Override save to update workflow totals when action is created"""
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Update workflow total actions count when new action is created
        if is_new:
            self.workflow.total_actions_planned = self.workflow.actions.count()
            self.workflow.save(update_fields=['total_actions_planned', 'updated_at'])
