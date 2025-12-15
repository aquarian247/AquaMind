"""
Migration to create LiveForwardProjection and ContainerForecastSummary models.

LiveForwardProjection is configured as a TimescaleDB hypertable with:
- Partitioning on computed_date (1-day chunks)
- 90-day retention policy
- Compression after 7 days (segment by assignment_id)

The migration uses the environmental app's migrations_helpers to gracefully
handle environments where TimescaleDB is not available (e.g., SQLite for CI).

Note: TimescaleDB hypertable creation requires the partition column to be
part of the primary key. We handle this by:
1. Creating the table normally
2. Attempting hypertable creation (may fail on primary key constraint)
3. If it fails, we modify the primary key to include computed_date
4. Then retry hypertable creation

In dev/test environments, the table works as a regular PostgreSQL table.
"""
from django.db import migrations, models
from django.conf import settings
from decimal import Decimal
import django.core.validators


def setup_timescale(apps, schema_editor):
    """
    Set up TimescaleDB hypertable, retention policy, and compression.

    Uses migration helpers from environmental app for graceful degradation
    when TimescaleDB is not available.
    """
    # Import helpers - gracefully skip if TimescaleDB not available
    try:
        from apps.environmental.migrations_helpers import (
            is_timescaledb_available,
            run_timescale_sql,
        )
    except ImportError:
        print("[INFO] TimescaleDB helpers not available - skipping setup")
        return

    if not is_timescaledb_available():
        print("[INFO] TimescaleDB not available - skipping hypertable setup")
        return

    # Get retention days from settings (default 90)
    retention_days = getattr(
        settings,
        'LIVE_FORWARD_PROJECTION_RETENTION_DAYS',
        90
    )

    # Get compression days from settings (default 7)
    compress_after_days = getattr(
        settings,
        'LIVE_FORWARD_PROJECTION_COMPRESS_AFTER_DAYS',
        7
    )

    # Step 1: Modify primary key to include computed_date for TimescaleDB
    # TimescaleDB requires the time dimension to be part of any unique index
    print("[INFO] Modifying primary key for TimescaleDB compatibility...")

    # Drop the default Django primary key constraint
    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE batch_liveforwardprojection
        DROP CONSTRAINT IF EXISTS batch_liveforwardprojection_pkey;
        """,
        description="Drop default primary key constraint"
    )

    # Create composite primary key including computed_date
    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE batch_liveforwardprojection
        ADD PRIMARY KEY (id, computed_date);
        """,
        description="Create composite primary key (id, computed_date)"
    )

    # Step 2: Create hypertable partitioned by computed_date
    run_timescale_sql(
        schema_editor,
        """
        SELECT create_hypertable(
            'batch_liveforwardprojection',
            'computed_date',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        """,
        description="Create hypertable for batch_liveforwardprojection"
    )

    # Step 3: Enable compression with segment by assignment
    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE batch_liveforwardprojection SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'assignment_id',
            timescaledb.compress_orderby = 'projection_date'
        );
        """,
        description="Enable compression for batch_liveforwardprojection"
    )

    # Step 4: Add compression policy
    run_timescale_sql(
        schema_editor,
        f"""
        SELECT add_compression_policy(
            'batch_liveforwardprojection',
            INTERVAL '{compress_after_days} days',
            if_not_exists => TRUE
        );
        """,
        description=(
            f"Add compression policy after {compress_after_days} days"
        )
    )

    # Step 5: Add retention policy
    run_timescale_sql(
        schema_editor,
        f"""
        SELECT add_retention_policy(
            'batch_liveforwardprojection',
            INTERVAL '{retention_days} days',
            if_not_exists => TRUE
        );
        """,
        description=f"Add {retention_days}-day retention policy"
    )


def remove_timescale(apps, schema_editor):
    """
    Remove TimescaleDB policies (reverse migration).

    Note: Removing hypertable requires dropping and recreating the table,
    which Django handles via the model deletion.
    """
    try:
        from apps.environmental.migrations_helpers import (
            is_timescaledb_available,
            run_timescale_sql,
        )
    except ImportError:
        return

    if not is_timescaledb_available():
        return

    # Remove policies (ignore errors if they don't exist)
    run_timescale_sql(
        schema_editor,
        """
        SELECT remove_retention_policy(
            'batch_liveforwardprojection',
            if_exists => TRUE
        );
        """,
        description="Remove retention policy"
    )

    run_timescale_sql(
        schema_editor,
        """
        SELECT remove_compression_policy(
            'batch_liveforwardprojection',
            if_exists => TRUE
        );
        """,
        description="Remove compression policy"
    )


class Migration(migrations.Migration):
    """
    Add LiveForwardProjection (hypertable) and ContainerForecastSummary models.
    """

    dependencies = [
        ('batch', '0043_add_planned_activity_to_daily_state'),
        ('infrastructure',
         '0008_alter_area_options_alter_containertype_options_and_more'),
    ]

    operations = [
        # Create LiveForwardProjection model
        migrations.CreateModel(
            name='LiveForwardProjection',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('computed_date', models.DateField(
                    db_index=True,
                    help_text='Date when projection was computed (partition key)'
                )),
                ('projection_date', models.DateField(
                    db_index=True,
                    help_text='Future date being projected'
                )),
                ('day_number', models.PositiveIntegerField(
                    help_text='Day number in batch lifecycle (1-based)'
                )),
                ('projected_weight_g', models.DecimalField(
                    decimal_places=2,
                    help_text='Projected average weight in grams',
                    max_digits=10,
                    validators=[
                        django.core.validators.MinValueValidator(
                            Decimal('0.00')
                        )
                    ]
                )),
                ('projected_population', models.PositiveIntegerField(
                    help_text='Projected population count',
                    validators=[
                        django.core.validators.MinValueValidator(0)
                    ]
                )),
                ('projected_biomass_kg', models.DecimalField(
                    decimal_places=2,
                    help_text='Projected biomass in kilograms',
                    max_digits=12,
                    validators=[
                        django.core.validators.MinValueValidator(
                            Decimal('0.00')
                        )
                    ]
                )),
                ('temperature_used_c', models.DecimalField(
                    decimal_places=2,
                    help_text='Temperature used for this day (profile + bias)',
                    max_digits=5
                )),
                ('tgc_value_used', models.DecimalField(
                    decimal_places=4,
                    help_text='TGC coefficient value used',
                    max_digits=8
                )),
                ('temp_profile_id', models.PositiveIntegerField(
                    blank=True,
                    help_text='ID of TemperatureProfile used as baseline',
                    null=True
                )),
                ('temp_profile_name', models.CharField(
                    blank=True,
                    default='',
                    help_text='Name of TemperatureProfile',
                    max_length=255
                )),
                ('temp_bias_c', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    help_text='Temperature bias (sensor vs profile delta)',
                    max_digits=5
                )),
                ('temp_bias_window_days', models.PositiveIntegerField(
                    default=14,
                    help_text='Number of recent days used to compute bias'
                )),
                ('temp_bias_clamp_min_c', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('-2.00'),
                    help_text='Minimum clamp for bias',
                    max_digits=5
                )),
                ('temp_bias_clamp_max_c', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('2.00'),
                    help_text='Maximum clamp for bias',
                    max_digits=5
                )),
                ('assignment', models.ForeignKey(
                    help_text='Container assignment being projected',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='live_projections',
                    to='batch.batchcontainerassignment'
                )),
                ('batch', models.ForeignKey(
                    help_text='Batch (denormalized)',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='live_projections',
                    to='batch.batch'
                )),
                ('container', models.ForeignKey(
                    help_text='Container (denormalized)',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='live_projections',
                    to='infrastructure.container'
                )),
            ],
            options={
                'verbose_name': 'Live Forward Projection',
                'verbose_name_plural': 'Live Forward Projections',
                'db_table': 'batch_liveforwardprojection',
                'ordering': ['projection_date'],
            },
        ),

        # Create ContainerForecastSummary model
        migrations.CreateModel(
            name='ContainerForecastSummary',
            fields=[
                ('assignment', models.OneToOneField(
                    help_text='Container assignment this summary belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True,
                    related_name='forecast_summary',
                    serialize=False,
                    to='batch.batchcontainerassignment'
                )),
                ('current_weight_g', models.DecimalField(
                    decimal_places=2,
                    help_text='Current average weight from latest actual state',
                    max_digits=10,
                    validators=[
                        django.core.validators.MinValueValidator(
                            Decimal('0.00')
                        )
                    ]
                )),
                ('current_population', models.PositiveIntegerField(
                    help_text='Current population from latest actual state',
                    validators=[
                        django.core.validators.MinValueValidator(0)
                    ]
                )),
                ('current_biomass_kg', models.DecimalField(
                    decimal_places=2,
                    help_text='Current biomass from latest actual state',
                    max_digits=12,
                    validators=[
                        django.core.validators.MinValueValidator(
                            Decimal('0.00')
                        )
                    ]
                )),
                ('state_date', models.DateField(
                    help_text='Date of actual state used as projection start'
                )),
                ('state_day_number', models.PositiveIntegerField(
                    help_text='Day number of the actual state'
                )),
                ('state_confidence', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    help_text='Overall confidence score from actual state (0-1)',
                    max_digits=3
                )),
                ('projected_harvest_date', models.DateField(
                    blank=True,
                    help_text='First date weight crosses harvest threshold',
                    null=True
                )),
                ('projected_harvest_weight_g', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Projected weight at harvest crossing date',
                    max_digits=10,
                    null=True
                )),
                ('days_to_harvest', models.PositiveIntegerField(
                    blank=True,
                    help_text='Days from state_date to projected harvest',
                    null=True
                )),
                ('harvest_threshold_g', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Harvest threshold used (from scenario)',
                    max_digits=10,
                    null=True
                )),
                ('projected_transfer_date', models.DateField(
                    blank=True,
                    help_text='First date weight crosses transfer threshold',
                    null=True
                )),
                ('projected_transfer_weight_g', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Projected weight at transfer crossing date',
                    max_digits=10,
                    null=True
                )),
                ('days_to_transfer', models.PositiveIntegerField(
                    blank=True,
                    help_text='Days from state_date to projected transfer',
                    null=True
                )),
                ('transfer_threshold_g', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Transfer threshold used (from scenario)',
                    max_digits=10,
                    null=True
                )),
                ('original_harvest_date', models.DateField(
                    blank=True,
                    help_text='Original harvest date from scenario',
                    null=True
                )),
                ('harvest_variance_days', models.IntegerField(
                    blank=True,
                    help_text='Days behind (+) or ahead (-) of plan',
                    null=True
                )),
                ('has_planned_harvest', models.BooleanField(
                    default=False,
                    help_text='PlannedActivity(HARVEST) exists'
                )),
                ('has_planned_transfer', models.BooleanField(
                    default=False,
                    help_text='PlannedActivity(TRANSFER) exists'
                )),
                ('needs_planning_attention', models.BooleanField(
                    default=False,
                    help_text='Approaching threshold without plan (TIER 3)'
                )),
                ('temp_profile_name', models.CharField(
                    blank=True,
                    default='',
                    help_text='Name of baseline TemperatureProfile used',
                    max_length=255
                )),
                ('temp_bias_c', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    help_text='Temperature bias applied to projections',
                    max_digits=5
                )),
                ('temp_bias_window_days', models.PositiveIntegerField(
                    default=14,
                    help_text='Days used to compute bias'
                )),
                ('last_computed', models.DateTimeField(
                    auto_now=True,
                    help_text='Timestamp when summary was last updated'
                )),
                ('computed_date', models.DateField(
                    blank=True,
                    help_text='Date of projection run',
                    null=True
                )),
            ],
            options={
                'verbose_name': 'Container Forecast Summary',
                'verbose_name_plural': 'Container Forecast Summaries',
                'db_table': 'batch_containerforecastsummary',
            },
        ),

        # Add indexes for LiveForwardProjection
        migrations.AddIndex(
            model_name='liveforwardprojection',
            index=models.Index(
                fields=['computed_date', 'assignment'],
                name='idx_lfp_computed_assignment'
            ),
        ),
        migrations.AddIndex(
            model_name='liveforwardprojection',
            index=models.Index(
                fields=['computed_date', 'batch'],
                name='idx_lfp_computed_batch'
            ),
        ),
        migrations.AddIndex(
            model_name='liveforwardprojection',
            index=models.Index(
                fields=['computed_date', 'assignment', 'projection_date'],
                name='idx_lfp_assignment_projdate'
            ),
        ),
        migrations.AddIndex(
            model_name='liveforwardprojection',
            index=models.Index(
                fields=['projection_date', 'projected_weight_g'],
                name='idx_lfp_projdate_weight'
            ),
        ),

        # Add indexes for ContainerForecastSummary
        migrations.AddIndex(
            model_name='containerforecastsummary',
            index=models.Index(
                fields=['needs_planning_attention'],
                name='idx_cfs_needs_attention'
            ),
        ),
        migrations.AddIndex(
            model_name='containerforecastsummary',
            index=models.Index(
                fields=['projected_harvest_date'],
                name='idx_cfs_harvest_date'
            ),
        ),
        migrations.AddIndex(
            model_name='containerforecastsummary',
            index=models.Index(
                fields=['projected_transfer_date'],
                name='idx_cfs_transfer_date'
            ),
        ),

        # Set up TimescaleDB hypertable and policies
        migrations.RunPython(
            setup_timescale,
            remove_timescale,
        ),
    ]
