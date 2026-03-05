"""
TransferAction model for the batch app.

This model represents individual container-to-container transfer actions within a workflow.
Each action represents ONE physical movement of fish and tracks its execution details.
"""
import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models, transaction
from django.db.models import Max
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.batch.models.workflow import BatchTransferWorkflow
from apps.batch.models.assignment import BatchContainerAssignment
from django.contrib.auth.models import User
from apps.batch.access import can_execute_transport_actions
from apps.infrastructure.models import Container


logger = logging.getLogger(__name__)


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

    LEG_TYPE_CHOICES = [
        ("STATION_TO_VESSEL", "Station to Vessel"),
        ("STATION_TO_TRUCK", "Station to Truck"),
        ("TRUCK_TO_VESSEL", "Truck to Vessel"),
        ("VESSEL_TO_RING", "Vessel to Ring"),
    ]

    CREATED_VIA_CHOICES = [
        ("PLANNED", "Planned"),
        ("DYNAMIC_LIVE", "Dynamic Live"),
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
    dest_container = models.ForeignKey(
        Container,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transfer_actions_as_dest_container",
        help_text="Destination container for dynamic live handoffs.",
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

    allow_mixed = models.BooleanField(
        default=False,
        help_text="Allow mixing with other batches if destination is occupied at execution"
    )
    
    # Status & Timeline
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    leg_type = models.CharField(
        max_length=32,
        choices=LEG_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Explicit transport leg type for dynamic handoffs.",
    )
    created_via = models.CharField(
        max_length=20,
        choices=CREATED_VIA_CHOICES,
        default="PLANNED",
        help_text="How this action was created (planned vs live dynamic start).",
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
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="High-resolution execution timestamp for operational ordering.",
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
        if self.dest_assignment and self.dest_assignment.container:
            dest_container = self.dest_assignment.container.name
        elif self.dest_container:
            dest_container = self.dest_container.name
        else:
            dest_container = "TBD"
        return f"Action #{self.action_number}: {source_container} → {dest_container} ({self.get_status_display()})"
    
    def clean(self):
        """Validate the action before saving"""
        super().clean()
        
        # Validate workflow can accept actions
        if (
            self.workflow
            and not self.workflow.can_add_actions()
            and not (
                self.workflow.is_dynamic_execution
                and self.status == "IN_PROGRESS"
                and self.created_via == "DYNAMIC_LIVE"
            )
        ):
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

        if not self.dest_assignment and not self.dest_container:
            raise ValidationError(
                "Destination assignment or destination container is required."
            )

        if self.dest_assignment and self.dest_container_id:
            if self.dest_assignment.container_id != self.dest_container_id:
                raise ValidationError(
                    "Destination assignment and destination container must match."
                )

    def has_transport_carrier_handoff(self):
        """True when either source or destination is linked to a transport carrier."""
        source_container = self.source_assignment.container if self.source_assignment else None
        dest_container = (
            self.dest_assignment.container
            if self.dest_assignment
            else self.dest_container
        )
        return bool(
            (source_container and source_container.carrier_id)
            or (dest_container and dest_container.carrier_id)
        )

    def requires_ship_crew_execution(self):
        """RBAC gate for vessel/dynamic transport actions."""
        return self.workflow.is_dynamic_execution or self.has_transport_carrier_handoff()

    @staticmethod
    def _build_mixed_batch_number():
        """Generate a short unique mixed batch identifier."""
        return (
            f"MIX-{timezone.now():%y%m%d%H%M%S}-"
            f"{uuid4().hex[:4].upper()}"
        )

    def _create_mixed_batch(self, lifecycle_stage, transfer_date):
        """Create a container-scoped mixed batch record."""
        from apps.batch.models.batch import Batch

        batch_number = self._build_mixed_batch_number()
        while Batch.objects.filter(batch_number=batch_number).exists():
            batch_number = self._build_mixed_batch_number()

        return Batch.objects.create(
            batch_number=batch_number,
            species=self.workflow.batch.species,
            lifecycle_stage=lifecycle_stage,
            status='ACTIVE',
            batch_type='MIXED',
            start_date=transfer_date,
            notes=(
                f"Auto-generated from transfer action {self.id} "
                f"in workflow {self.workflow.workflow_number}"
            ),
        )

    @staticmethod
    def _deactivate_assignment(assignment, departure_date):
        """Close an assignment after its fish are moved into a mixed assignment."""
        assignment.population_count = 0
        assignment.is_active = False
        if not assignment.departure_date:
            assignment.departure_date = departure_date
        assignment.save()

    def _execute_mixed_destination(self, source, execution_time):
        """
        Create a container-scoped mixed assignment and mix event.

        Mixing is local to the destination container. All currently active
        assignments in the destination container are merged with the incoming
        transferred fish into a new mixed batch assignment.
        """
        from apps.batch.models.batch import Batch
        from apps.batch.models.composition import BatchComposition
        from apps.batch.models.mix_event import BatchMixEvent, BatchMixEventComponent

        transfer_date = execution_time.date()
        dest_container = self.dest_assignment.container
        lifecycle_stage = (
            self.workflow.dest_lifecycle_stage
            or self.dest_assignment.lifecycle_stage
            or source.lifecycle_stage
        )

        existing_assignments = list(
            BatchContainerAssignment.objects.select_for_update().filter(
                container=dest_container,
                is_active=True,
            ).exclude(pk=source.pk)
        )

        contributions = []
        total_population = 0
        total_biomass = Decimal("0")

        for assignment in existing_assignments:
            if assignment.population_count <= 0:
                continue

            component_biomass = assignment.biomass_kg or Decimal("0")
            contributions.append(
                {
                    "source_assignment": assignment,
                    "source_batch": assignment.batch,
                    "population_count": assignment.population_count,
                    "biomass_kg": component_biomass,
                    "is_transferred_in": False,
                }
            )
            total_population += assignment.population_count
            total_biomass += component_biomass

        transferred_biomass = self.transferred_biomass_kg or Decimal("0")
        contributions.append(
            {
                "source_assignment": source,
                "source_batch": source.batch,
                "population_count": self.transferred_count,
                "biomass_kg": transferred_biomass,
                "is_transferred_in": True,
            }
        )
        total_population += self.transferred_count
        total_biomass += transferred_biomass

        if total_population <= 0:
            raise ValidationError(
                "Mixed transfer produced zero population for destination container."
            )

        if total_biomass > 0:
            avg_weight_g = (total_biomass * Decimal("1000")) / Decimal(total_population)
        else:
            avg_weight_g = source.avg_weight_g or Decimal("0")

        mixed_batch = self._create_mixed_batch(
            lifecycle_stage=lifecycle_stage,
            transfer_date=transfer_date,
        )
        mixed_assignment = BatchContainerAssignment.objects.create(
            batch=mixed_batch,
            container=dest_container,
            lifecycle_stage=lifecycle_stage,
            population_count=total_population,
            avg_weight_g=avg_weight_g,
            assignment_date=transfer_date,
            is_active=True,
            notes=(
                f"Created by transfer action {self.id} "
                f"from workflow {self.workflow.workflow_number}"
            ),
        )

        for assignment in existing_assignments:
            self._deactivate_assignment(assignment, transfer_date)

        mix_event = BatchMixEvent.objects.create(
            mixed_batch=mixed_batch,
            container=dest_container,
            workflow_action=self,
            mixed_at=execution_time,
            notes=(
                f"Container-scoped mixing triggered by action {self.action_number} "
                f"in workflow {self.workflow.workflow_number}"
            ),
        )

        source_batch_aggregates = {}
        for contribution in contributions:
            pop = contribution["population_count"]
            biomass = contribution["biomass_kg"] or Decimal("0")
            percentage = (Decimal(pop) / Decimal(total_population)) * Decimal("100")

            BatchMixEventComponent.objects.create(
                mix_event=mix_event,
                source_assignment=contribution["source_assignment"],
                source_batch=contribution["source_batch"],
                population_count=pop,
                biomass_kg=biomass,
                percentage=round(percentage, 2),
                is_transferred_in=contribution["is_transferred_in"],
            )

            batch_id = contribution["source_batch"].id
            aggregate = source_batch_aggregates.setdefault(
                batch_id,
                {
                    "source_batch": contribution["source_batch"],
                    "population_count": 0,
                    "biomass_kg": Decimal("0"),
                },
            )
            aggregate["population_count"] += pop
            aggregate["biomass_kg"] += biomass

        for aggregate in source_batch_aggregates.values():
            percentage = (
                Decimal(aggregate["population_count"]) / Decimal(total_population)
            ) * Decimal("100")
            BatchComposition.objects.create(
                mixed_batch=mixed_batch,
                source_batch=aggregate["source_batch"],
                percentage=round(percentage, 2),
                population_count=aggregate["population_count"],
                biomass_kg=aggregate["biomass_kg"],
            )

        return mixed_assignment
    
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

        if self.workflow.is_dynamic_execution:
            raise ValidationError(
                "Dynamic transport handoffs must use start/complete flow. "
                "Use /handoffs/start then /complete-handoff."
            )
        
        if not self.workflow.can_execute_actions():
            raise ValidationError(
                f"Cannot execute actions on workflow in {self.workflow.status} status"
            )

        if self.requires_ship_crew_execution() and not can_execute_transport_actions(executed_by):
            raise ValidationError(
                "Only SHIP_CREW or Logistics Operators can execute this transport action."
            )

        execution_time = timezone.now()
        
        # Map API field name to internal param when provided
        if 'mortality_during_transfer' in execution_details:
            mortality_count = execution_details.pop('mortality_during_transfer') or 0

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
                other_active = BatchContainerAssignment.objects.select_for_update().filter(
                    container=self.dest_assignment.container,
                    is_active=True,
                ).exclude(batch=self.workflow.batch)
                if other_active.exists() and not self.allow_mixed:
                    raise ValidationError(
                        "Destination container has another active batch. "
                        "Enable mixed batch to proceed."
                    )
                if other_active.exists() and self.allow_mixed:
                    dest = self._execute_mixed_destination(
                        source=source,
                        execution_time=execution_time,
                    )
                    self.dest_assignment = dest
                else:
                    dest = self.dest_assignment
                    if not dest.is_active:
                        dest.is_active = True
                        dest.assignment_date = timezone.now().date()
                    if self.workflow.dest_lifecycle_stage and dest.lifecycle_stage_id != self.workflow.dest_lifecycle_stage_id:
                        dest.lifecycle_stage = self.workflow.dest_lifecycle_stage
                    if (not dest.avg_weight_g or dest.avg_weight_g == 0) and source.avg_weight_g:
                        dest.avg_weight_g = source.avg_weight_g
                    dest.population_count += self.transferred_count
                    # Update biomass
                    if dest.avg_weight_g and self.transferred_count > 0:
                        dest.biomass_kg = (dest.population_count * dest.avg_weight_g) / 1000
                    dest.save()
            
            # Update this action with execution details
            self.status = 'COMPLETED'
            self.actual_execution_date = execution_time.date()
            self.executed_at = execution_time
            self.executed_by = executed_by
            self.mortality_during_transfer = mortality_count
            
            # Apply optional execution details
            for key, value in execution_details.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.save()

            # Record mortality event (if any)
            if mortality_count > 0:
                from apps.batch.models.mortality import MortalityEvent
                avg_weight_g = source.avg_weight_g or Decimal('0')
                biomass_kg = (Decimal(mortality_count) * avg_weight_g) / Decimal('1000')
                MortalityEvent.objects.create(
                    batch=self.workflow.batch,
                    assignment=source,
                    event_date=self.actual_execution_date,
                    count=mortality_count,
                    biomass_kg=biomass_kg,
                    cause='HANDLING',
                    description=(
                        f"Transfer mortality during {self.workflow.workflow_number} "
                        f"action {self.action_number}"
                    ),
                )
            
            # Update workflow status and progress
            self.workflow.mark_in_progress()
            self.workflow.actions_completed += 1
            self.workflow.update_progress()
            self.workflow.check_completion()
            self.workflow.recalculate_totals()

            action_id = self.id
            executed_by_id = executed_by.id if executed_by else None

            def _snapshot_after_commit():
                try:
                    from apps.environmental.services.historian_snapshot import (
                        snapshot_transfer_action_readings,
                    )

                    snapshot_transfer_action_readings(
                        action_id=action_id,
                        reading_time=execution_time,
                        executed_by_id=executed_by_id,
                        moment="finish",
                    )
                except Exception as exc:  # pragma: no cover - operational logging
                    logger.warning(
                        "Failed environmental snapshot for TransferAction %s: %s",
                        action_id,
                        exc,
                    )

            transaction.on_commit(_snapshot_after_commit)
            
            return {
                'action_id': self.id,
                'action_status': self.status,
                'workflow_status': self.workflow.status,
                'completion_percentage': float(self.workflow.completion_percentage),
                'actions_remaining': self.workflow.total_actions_planned - self.workflow.actions_completed
            }

    def _resolve_destination_assignment(self, *, source, execution_date):
        """Resolve or create destination assignment for dynamic completion."""
        dest_container = self.dest_container or (
            self.dest_assignment.container if self.dest_assignment else None
        )
        if not dest_container:
            raise ValidationError("Destination container is required to complete handoff.")

        if self.dest_assignment_id:
            return BatchContainerAssignment.objects.select_for_update().get(
                pk=self.dest_assignment_id
            )

        dest = (
            BatchContainerAssignment.objects.select_for_update()
            .filter(
                batch=self.workflow.batch,
                container=dest_container,
                is_active=True,
            )
            .first()
        )
        if dest:
            return dest

        latest = (
            BatchContainerAssignment.objects.select_for_update()
            .filter(batch=self.workflow.batch, container=dest_container)
            .order_by("-id")
            .first()
        )
        lifecycle_stage = self.workflow.dest_lifecycle_stage or source.lifecycle_stage
        if latest:
            latest.lifecycle_stage = lifecycle_stage
            latest.assignment_date = latest.assignment_date or execution_date
            latest.is_active = True
            latest.save(
                update_fields=[
                    "lifecycle_stage",
                    "assignment_date",
                    "is_active",
                    "updated_at",
                ]
            )
            return latest

        return BatchContainerAssignment.objects.create(
            batch=self.workflow.batch,
            container=dest_container,
            lifecycle_stage=lifecycle_stage,
            population_count=0,
            avg_weight_g=source.avg_weight_g or Decimal("0"),
            assignment_date=execution_date,
            is_active=True,
            notes=(
                f"Auto-created on dynamic handoff completion "
                f"for action {self.id} ({self.workflow.workflow_number})"
            ),
        )

    def complete_handoff(
        self,
        *,
        executed_by,
        transferred_count: int,
        transferred_biomass_kg: Decimal,
        mortality_count: int = 0,
        **execution_details,
    ):
        """
        Complete a previously started dynamic handoff.

        This endpoint applies source/destination mutations and marks the action
        as COMPLETED. It is valid only for IN_PROGRESS actions.
        """
        if self.status != "IN_PROGRESS":
            raise ValidationError("Only IN_PROGRESS handoffs can be completed.")
        if not self.workflow.is_dynamic_execution:
            raise ValidationError("complete_handoff is only valid for dynamic workflows.")
        if transferred_count <= 0:
            raise ValidationError("Transferred count must be greater than zero.")
        if transferred_biomass_kg is None or Decimal(transferred_biomass_kg) <= 0:
            raise ValidationError("Transferred biomass must be greater than zero.")
        if mortality_count < 0:
            raise ValidationError("Mortality cannot be negative.")

        if self.requires_ship_crew_execution() and not can_execute_transport_actions(executed_by):
            raise ValidationError(
                "Only SHIP_CREW or Logistics Operators can complete this transport action."
            )

        execution_time = timezone.now()
        transferred_biomass_kg = Decimal(transferred_biomass_kg)
        transferred_count = int(transferred_count)
        mortality_count = int(mortality_count)

        with transaction.atomic():
            source = BatchContainerAssignment.objects.select_for_update().get(
                pk=self.source_assignment_id
            )
            total_reduction = transferred_count + mortality_count
            if total_reduction > source.population_count:
                raise ValidationError(
                    f"Cannot move {total_reduction} fish (including mortality) from "
                    f"source with {source.population_count} fish."
                )

            source.population_count -= total_reduction
            if source.population_count == 0:
                source.is_active = False
                source.departure_date = execution_time.date()
            source.save()

            dest = self._resolve_destination_assignment(
                source=source,
                execution_date=execution_time.date(),
            )
            self.dest_assignment = dest
            if not self.dest_container_id:
                self.dest_container_id = dest.container_id

            other_active = BatchContainerAssignment.objects.select_for_update().filter(
                container=dest.container,
                is_active=True,
            ).exclude(batch=self.workflow.batch)
            if other_active.exists() and not self.allow_mixed:
                raise ValidationError(
                    "Destination container has another active batch. "
                    "Enable mixed batch to proceed."
                )
            if other_active.exists() and self.allow_mixed:
                mixed_dest = self._execute_mixed_destination(
                    source=source,
                    execution_time=execution_time,
                )
                self.dest_assignment = mixed_dest
            else:
                existing_population = dest.population_count
                existing_biomass = dest.biomass_kg or Decimal("0")

                if not dest.is_active:
                    dest.is_active = True
                    dest.assignment_date = execution_time.date()
                if (
                    self.workflow.dest_lifecycle_stage
                    and dest.lifecycle_stage_id != self.workflow.dest_lifecycle_stage_id
                ):
                    dest.lifecycle_stage = self.workflow.dest_lifecycle_stage

                dest.population_count = existing_population + transferred_count
                total_biomass = existing_biomass + transferred_biomass_kg
                if dest.population_count > 0:
                    dest.avg_weight_g = (
                        total_biomass * Decimal("1000")
                    ) / Decimal(dest.population_count)
                    dest.biomass_kg = total_biomass
                else:
                    dest.avg_weight_g = Decimal("0")
                    dest.biomass_kg = Decimal("0")
                dest.save()

            self.status = "COMPLETED"
            self.actual_execution_date = execution_time.date()
            self.executed_at = execution_time
            self.executed_by = executed_by
            self.mortality_during_transfer = mortality_count
            self.transferred_count = transferred_count
            self.transferred_biomass_kg = transferred_biomass_kg

            for key, value in execution_details.items():
                if hasattr(self, key):
                    setattr(self, key, value)

            self.save()

            if mortality_count > 0:
                from apps.batch.models.mortality import MortalityEvent
                avg_weight_g = source.avg_weight_g or Decimal("0")
                biomass_kg = (Decimal(mortality_count) * avg_weight_g) / Decimal("1000")
                MortalityEvent.objects.create(
                    batch=self.workflow.batch,
                    assignment=source,
                    event_date=self.actual_execution_date,
                    count=mortality_count,
                    biomass_kg=biomass_kg,
                    cause="HANDLING",
                    description=(
                        f"Transfer mortality during {self.workflow.workflow_number} "
                        f"action {self.action_number}"
                    ),
                )

            if self.workflow.status == "PLANNED":
                self.workflow.mark_in_progress()

            self.workflow.actions_completed = self.workflow.actions.filter(
                status="COMPLETED"
            ).count()
            self.workflow.update_progress()
            self.workflow.check_completion()
            self.workflow.recalculate_totals()

            action_id = self.id
            executed_by_id = executed_by.id if executed_by else None

            def _snapshot_after_commit():
                try:
                    from django.conf import settings
                    from apps.environmental.services.historian_snapshot import (
                        snapshot_transfer_action_readings,
                    )

                    if getattr(settings, "TRANSFER_CAPTURE_FINISH_SNAPSHOT", True):
                        snapshot_transfer_action_readings(
                            action_id=action_id,
                            reading_time=execution_time,
                            executed_by_id=executed_by_id,
                            moment="finish",
                        )
                except Exception as exc:  # pragma: no cover - operational logging
                    logger.warning(
                        "Failed finish snapshot for TransferAction %s: %s",
                        action_id,
                        exc,
                    )

            transaction.on_commit(_snapshot_after_commit)

            return {
                "action_id": self.id,
                "action_status": self.status,
                "workflow_status": self.workflow.status,
                "completion_percentage": float(self.workflow.completion_percentage),
                "actions_remaining": (
                    self.workflow.total_actions_planned - self.workflow.actions_completed
                ),
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

        if self.dest_assignment_id and not self.dest_container_id:
            self.dest_container_id = self.dest_assignment.container_id
        if self.workflow_id and self.workflow.is_dynamic_execution and self.created_via == "PLANNED":
            # Preserve backward compatibility for historical rows while defaulting
            # newly created dynamic handoffs to live mode unless explicitly set.
            if is_new and self.status == "IN_PROGRESS":
                self.created_via = "DYNAMIC_LIVE"

        if is_new:
            current_max = self.workflow.actions.aggregate(
                max_number=Max('action_number')
            )['max_number'] or 0

            if not self.action_number:
                self.action_number = current_max + 1
            elif (
                self.workflow.is_dynamic_execution
                and self.workflow.actions.filter(action_number=self.action_number).exists()
            ):
                self.action_number = current_max + 1
        
        super().save(*args, **kwargs)
        
        # Update workflow total actions count when new action is created
        if is_new:
            self.workflow.total_actions_planned = self.workflow.actions.count()
            self.workflow.save(update_fields=['total_actions_planned', 'updated_at'])
