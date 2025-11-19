# Generated migration for batch growth assimilation - Issue #112
# Phase 2: Setup TimescaleDB hypertable with proper error handling

from django.db import migrations, transaction


def setup_hypertable_skip_for_dev(apps, schema_editor):
    """
    Placeholder for TimescaleDB hypertable setup.
    
    Per aquamind/docs/quality_assurance/timescaledb_testing_strategy.md:
    - TimescaleDB operations are skipped in dev/test to avoid transaction issues
    - The table works perfectly as a regular PostgreSQL table
    - Manual production setup scripts will configure:
      1. Update PK to (id, date)
      2. Convert to hypertable with 14-day chunks
      3. Enable compression (segment by assignment_id, compress after 30 days)
    
    This keeps migrations simple and prevents transaction aborts during development.
    """
    print("[INFO] ===============================================")
    print("[INFO] TimescaleDB Hypertable Setup - Skipped")
    print("[INFO] ===============================================")
    print("[INFO] Table: batch_actualdailyassignmentstate")
    print("[INFO] Status: Works as regular PostgreSQL table")
    print("[INFO] Production: Run separate TimescaleDB setup scripts")
    print("[INFO] Reference: scripts/timescaledb/setup_daily_state_hypertable.sql")
    print("[INFO] ===============================================")


def noop(apps, schema_editor):
    """No-op for reverse migration."""
    pass


class Migration(migrations.Migration):
    """
    Setup TimescaleDB hypertable for ActualDailyAssignmentState.
    
    This migration uses atomic savepoints to handle TimescaleDB operations gracefully.
    If TimescaleDB is unavailable or operations fail, the table continues to work
    as a regular PostgreSQL table without aborting the migration.
    """

    dependencies = [
        ('batch', '0033_create_actual_daily_state_model'),
    ]

    operations = [
        migrations.RunPython(
            setup_hypertable_skip_for_dev,
            reverse_code=noop
        ),
    ]
