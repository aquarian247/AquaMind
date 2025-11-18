# Generated migration for batch growth assimilation - Issue #112
# Phase 2: TimescaleDB setup (skipped in dev/test per testing strategy)

from django.db import migrations


def skip_timescaledb_setup(apps, schema_editor):
    """
    Placeholder migration for TimescaleDB setup.
    
    Per aquamind/docs/quality_assurance/timescaledb_testing_strategy.md:
    - TimescaleDB operations are skipped in dev/test environments
    - The table works as a regular PostgreSQL table
    - TimescaleDB features (hypertable, compression, CAGGs) will be configured
      manually in production or via separate deployment scripts
    
    This keeps migrations database-agnostic and prevents transaction aborts
    during development.
    """
    print("[INFO] TimescaleDB setup skipped - batch_actualdailyassignmentstate works as regular table")
    print("[INFO] For production: manually run TimescaleDB configuration scripts")
    print("[INFO] Reference: aquamind/docs/quality_assurance/timescaledb_testing_strategy.md")


def noop(apps, schema_editor):
    """No-op for reverse migration."""
    pass


class Migration(migrations.Migration):
    """
    Placeholder migration for TimescaleDB setup.
    
    The ActualDailyAssignmentState table is created as a regular table in migration 0033.
    This migration documents that TimescaleDB configuration (hypertable, compression, CAGGs)
    is handled separately per the TimescaleDB testing strategy.
    
    In production, run separate scripts to:
    1. Update primary key to (id, date)
    2. Convert to hypertable with 14-day chunks
    3. Enable compression (segment by assignment_id, compress after 30 days)
    4. Create temperature CAGG (env_daily_temp_by_container)
    """

    dependencies = [
        ('batch', '0033_create_actual_daily_state_model'),
    ]

    operations = [
        migrations.RunPython(
            skip_timescaledb_setup,
            reverse_code=noop
        ),
    ]



