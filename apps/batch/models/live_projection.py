"""
Live Forward Projection models for batch growth forecasting.

This module implements the data models for live forward projections that
predict future growth trajectories based on current ActualDailyAssignmentState
data, applying temperature bias adjustments from recent sensor readings.

Architecture:
- LiveForwardProjection: TimescaleDB hypertable storing daily projected values
  per container assignment, partitioned by computed_date for 90-day backtesting
- ContainerForecastSummary: Regular table with denormalized summary for fast
  dashboard queries

Key design decisions:
- Container-level projections (containers grow at different rates)
- 90-day retention for backtesting and accuracy validation
- Temperature bias computed from recent sensor data vs profile
- Model inputs persisted for full transparency and debugging

Related:
- ActualDailyAssignmentState (source of truth for current state)
- TGCCalculator (growth math)
- TemperatureProfile (baseline future temperatures)
- PlannedActivity (Tier 1 authoritative plans)

Issue: Live Forward Projection Feature
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


class LiveForwardProjection(models.Model):
    """
    Forward projection of growth from latest actual state to scenario end.

    TimescaleDB hypertable partitioned by computed_date. Stores one row per
    (computed_date, assignment, projection_date) for the full projection
    horizon.

    Retention: 90 days (via LIVE_FORWARD_PROJECTION_RETENTION_DAYS)
    Compression: After 7 days (segment by assignment_id)

    The projection starts from the latest ActualDailyAssignmentState and uses:
    - Pinned scenario's TGC model for growth
    - Temperature profile + bias for future temperatures
    - Scenario mortality model for population decay

    Temperature bias is computed from recent days where sensor-derived temps
    were available, comparing to profile temps for those same day numbers.
    """

    # =========================================================================
    # Partition Key (TimescaleDB)
    # =========================================================================
    computed_date = models.DateField(
        db_index=True,
        help_text="Date when projection was computed (partition key)"
    )

    # =========================================================================
    # Relationships (Container-Level Projection)
    # =========================================================================
    assignment = models.ForeignKey(
        'batch.BatchContainerAssignment',
        on_delete=models.CASCADE,
        related_name='live_projections',
        help_text="Container assignment being projected"
    )

    # Denormalized for efficient querying without joins
    batch = models.ForeignKey(
        'batch.Batch',
        on_delete=models.CASCADE,
        related_name='live_projections',
        help_text="Batch (denormalized from assignment)"
    )
    container = models.ForeignKey(
        'infrastructure.Container',
        on_delete=models.CASCADE,
        related_name='live_projections',
        help_text="Container (denormalized from assignment)"
    )

    # =========================================================================
    # Projection Point
    # =========================================================================
    projection_date = models.DateField(
        db_index=True,
        help_text="Future date being projected"
    )
    day_number = models.PositiveIntegerField(
        help_text="Day number in batch lifecycle (1-based from start_date)"
    )

    # =========================================================================
    # Projected Values
    # =========================================================================
    projected_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Projected average weight in grams"
    )
    projected_population = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Projected population count"
    )
    projected_biomass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Projected biomass in kilograms"
    )

    # =========================================================================
    # Model Inputs (Transparency/Debugging)
    # =========================================================================
    temperature_used_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Temperature used for this day (profile + bias)"
    )
    tgc_value_used = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="TGC coefficient value used"
    )

    # Temperature bias provenance (constant for entire projection run)
    temp_profile_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the TemperatureProfile used as baseline"
    )
    temp_profile_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Name of TemperatureProfile (denormalized for display)"
    )
    temp_bias_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Temperature bias (sensor vs profile delta)"
    )
    temp_bias_window_days = models.PositiveIntegerField(
        default=14,
        help_text="Number of recent days used to compute bias"
    )
    temp_bias_clamp_min_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('-2.00'),
        help_text="Minimum clamp for bias"
    )
    temp_bias_clamp_max_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        help_text="Maximum clamp for bias"
    )

    class Meta:
        db_table = 'batch_liveforwardprojection'
        indexes = [
            # Primary query: latest projections for an assignment
            models.Index(
                fields=['computed_date', 'assignment'],
                name='idx_lfp_computed_assignment'
            ),
            # Batch-level rollups
            models.Index(
                fields=['computed_date', 'batch'],
                name='idx_lfp_computed_batch'
            ),
            # Finding crossing dates (weight threshold queries)
            models.Index(
                fields=['computed_date', 'assignment', 'projection_date'],
                name='idx_lfp_assignment_projdate'
            ),
            models.Index(
                fields=['projection_date', 'projected_weight_g'],
                name='idx_lfp_projdate_weight'
            ),
        ]
        # Note: TimescaleDB hypertable + retention policy set in migration
        ordering = ['projection_date']
        verbose_name = 'Live Forward Projection'
        verbose_name_plural = 'Live Forward Projections'

    def __str__(self):
        return (
            f"{self.batch.batch_number} - {self.container.name} "
            f"Day {self.day_number} ({self.projection_date}) "
            f"[computed {self.computed_date}]"
        )


class ContainerForecastSummary(models.Model):
    """
    Denormalized summary of live projection results for fast dashboard queries.

    One row per active assignment, updated after each projection run.
    Contains current state snapshot and key crossing dates (harvest, transfer).

    Used by:
    - Executive Dashboard (Strategic tab)
    - Batch Details forecast panels
    - Contract matching queries

    Flags indicate planning status:
    - has_planned_harvest: PlannedActivity exists for HARVEST
    - has_planned_transfer: PlannedActivity exists for TRANSFER
    - needs_planning_attention: Approaching threshold without a plan
    """

    # =========================================================================
    # Primary Key (One-to-One with Assignment)
    # =========================================================================
    assignment = models.OneToOneField(
        'batch.BatchContainerAssignment',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='forecast_summary',
        help_text="Container assignment this summary belongs to"
    )

    # =========================================================================
    # Current State Snapshot (from latest ActualDailyAssignmentState)
    # =========================================================================
    current_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current average weight from latest actual state"
    )
    current_population = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Current population from latest actual state"
    )
    current_biomass_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current biomass from latest actual state"
    )
    state_date = models.DateField(
        help_text="Date of actual state used as projection start"
    )
    state_day_number = models.PositiveIntegerField(
        help_text="Day number of the actual state"
    )
    state_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Overall confidence score from actual state (0-1)"
    )

    # =========================================================================
    # Harvest Projection
    # =========================================================================
    projected_harvest_date = models.DateField(
        null=True,
        blank=True,
        help_text="First date projected weight crosses harvest threshold"
    )
    projected_harvest_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Projected weight at harvest crossing date"
    )
    days_to_harvest = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Days from state_date to projected harvest"
    )
    harvest_threshold_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Harvest threshold used (from scenario)"
    )

    # =========================================================================
    # Transfer Projection
    # =========================================================================
    projected_transfer_date = models.DateField(
        null=True,
        blank=True,
        help_text="First date projected weight crosses transfer threshold"
    )
    projected_transfer_weight_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Projected weight at transfer crossing date"
    )
    days_to_transfer = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Days from state_date to projected transfer"
    )
    transfer_threshold_g = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Transfer threshold used (from scenario)"
    )

    # =========================================================================
    # Variance from Original Plan
    # =========================================================================
    original_harvest_date = models.DateField(
        null=True,
        blank=True,
        help_text="Original harvest date from scenario ProjectionDay"
    )
    harvest_variance_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Days behind (+) or ahead (-) of original plan"
    )

    # =========================================================================
    # Planning Flags (for 3-tier Dashboard)
    # =========================================================================
    has_planned_harvest = models.BooleanField(
        default=False,
        help_text="PlannedActivity(HARVEST) exists for batch/container"
    )
    has_planned_transfer = models.BooleanField(
        default=False,
        help_text="PlannedActivity(TRANSFER) exists for batch/container"
    )
    needs_planning_attention = models.BooleanField(
        default=False,
        help_text="Approaching threshold without a plan (TIER 3)"
    )

    # =========================================================================
    # Temperature Bias Provenance (for UI display)
    # =========================================================================
    temp_profile_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Name of baseline TemperatureProfile used"
    )
    temp_bias_c = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Temperature bias applied to projections"
    )
    temp_bias_window_days = models.PositiveIntegerField(
        default=14,
        help_text="Days used to compute bias"
    )

    # =========================================================================
    # Metadata
    # =========================================================================
    last_computed = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this summary was last updated"
    )
    computed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of projection run that generated this summary"
    )

    class Meta:
        db_table = 'batch_containerforecastsummary'
        indexes = [
            # Dashboard queries by batch
            models.Index(
                fields=['needs_planning_attention'],
                name='idx_cfs_needs_attention'
            ),
            # Finding containers approaching harvest
            models.Index(
                fields=['projected_harvest_date'],
                name='idx_cfs_harvest_date'
            ),
            # Finding containers approaching transfer
            models.Index(
                fields=['projected_transfer_date'],
                name='idx_cfs_transfer_date'
            ),
        ]
        verbose_name = 'Container Forecast Summary'
        verbose_name_plural = 'Container Forecast Summaries'

    def __str__(self):
        return (
            f"{self.assignment.batch.batch_number} - "
            f"{self.assignment.container.name} Forecast Summary"
        )

    @property
    def tier(self) -> str:
        """
        Determine the forecast tier for dashboard display.

        Returns:
            'PLANNED': Has a confirmed PlannedActivity
            'PROJECTED': Has projection but no plan
            'NEEDS_PLANNING': Approaching threshold without plan
        """
        if self.has_planned_harvest or self.has_planned_transfer:
            return 'PLANNED'
        elif self.needs_planning_attention:
            return 'NEEDS_PLANNING'
        else:
            return 'PROJECTED'
