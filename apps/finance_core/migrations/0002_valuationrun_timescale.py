"""Optional TimescaleDB setup for finance_core_valuationrun."""

from django.db import migrations


def setup_timescale(apps, schema_editor):
    try:
        from apps.environmental.migrations_helpers import (
            is_timescaledb_available,
            run_timescale_sql,
        )
    except ImportError:
        return

    if not is_timescaledb_available():
        return

    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE finance_core_valuationrun
        DROP CONSTRAINT IF EXISTS finance_core_valuationrun_pkey;
        """,
        description="Drop finance_core_valuationrun primary key",
    )
    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE finance_core_valuationrun
        ADD PRIMARY KEY (run_id, run_timestamp);
        """,
        description="Add composite primary key for finance_core_valuationrun",
    )
    run_timescale_sql(
        schema_editor,
        """
        SELECT create_hypertable(
            'finance_core_valuationrun',
            'run_timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
        """,
        description="Create valuation run hypertable",
    )
    run_timescale_sql(
        schema_editor,
        """
        ALTER TABLE finance_core_valuationrun SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'operating_unit_id',
            timescaledb.compress_orderby = 'run_timestamp'
        );
        """,
        description="Enable compression for valuation runs",
    )
    run_timescale_sql(
        schema_editor,
        """
        SELECT add_compression_policy(
            'finance_core_valuationrun',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );
        """,
        description="Add valuation run compression policy",
    )


def remove_timescale(apps, schema_editor):
    try:
        from apps.environmental.migrations_helpers import (
            is_timescaledb_available,
            run_timescale_sql,
        )
    except ImportError:
        return

    if not is_timescaledb_available():
        return

    run_timescale_sql(
        schema_editor,
        """
        SELECT remove_compression_policy(
            'finance_core_valuationrun',
            if_exists => TRUE
        );
        """,
        description="Remove valuation run compression policy",
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("finance_core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(setup_timescale, remove_timescale),
    ]
