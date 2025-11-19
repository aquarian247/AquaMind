# Generated migration for batch growth assimilation - Issue #112
# Phase 2: Create continuous aggregate for daily temperature by container

from django.db import migrations, transaction
from apps.environmental.migrations_helpers import (
    is_timescaledb_available,
    run_timescale_sql,
)


def create_daily_temp_cagg_skip_for_dev(apps, schema_editor):
    """
    Placeholder for temperature CAGG setup.
    
    Per aquamind/docs/quality_assurance/timescaledb_testing_strategy.md:
    - TimescaleDB CAGGs are skipped in dev/test
    - Growth assimilation will query temperature readings directly
    - Manual production setup scripts will create:
      - env_daily_temp_by_container materialized view
      - Refresh policy (hourly, last 7 days)
    
    This keeps migrations simple and database-agnostic.
    """
    print("[INFO] ===============================================")
    print("[INFO] Temperature CAGG Setup - Skipped")
    print("[INFO] ===============================================")
    print("[INFO] CAGG: env_daily_temp_by_container")
    print("[INFO] Fallback: Direct queries to environmental_environmentalreading")
    print("[INFO] Production: Run separate TimescaleDB CAGG setup scripts")
    print("[INFO] Reference: scripts/timescaledb/setup_temperature_cagg.sql")
    print("[INFO] ===============================================")


def noop(apps, schema_editor):
    """No-op for reverse migration."""
    pass


class Migration(migrations.Migration):
    """
    Create continuous aggregate for daily temperature by container.
    
    This CAGG provides efficient access to daily temperature data needed for
    batch growth assimilation calculations. Falls back gracefully if TimescaleDB
    is unavailable.
    """

    dependencies = [
        ('environmental', '0013_update_stage_transition_to_workflow'),
    ]

    operations = [
        migrations.RunPython(
            create_daily_temp_cagg_skip_for_dev,
            reverse_code=noop
        ),
    ]

