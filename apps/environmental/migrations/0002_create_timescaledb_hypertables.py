from django.db import migrations, connection

# Import our custom helper functions for TimescaleDB operations
from apps.environmental.migrations_helpers import (
    run_timescale_sql,
    create_hypertable,
    set_compression,
    is_timescaledb_available
)


def update_primary_keys(apps, schema_editor):
    """
    Update primary keys to include the partitioning columns before creating hypertables.
    This must be executed before creating TimescaleDB hypertables.
    """
    # Skip if not PostgreSQL or TimescaleDB is not available
    if not is_timescaledb_available():
        print("[WARNING] Skipping PK update: TimescaleDB not available or disabled")
        return
        
    # Environmental Reading PK update
    try:
        schema_editor.execute(
            "ALTER TABLE environmental_environmentalreading DROP CONSTRAINT IF EXISTS environmental_environmentalreading_pkey"
        )
        schema_editor.execute(
            "ALTER TABLE environmental_environmentalreading ADD CONSTRAINT environmental_environmentalreading_pkey PRIMARY KEY (id, reading_time)"
        )
        print("[OK] Updated EnvironmentalReading primary key")
    except Exception as e:
        print(f"[WARNING] Error updating EnvironmentalReading PK: {e}")
        
    # Weather Data PK update
    try:
        schema_editor.execute(
            "ALTER TABLE environmental_weatherdata DROP CONSTRAINT IF EXISTS environmental_weatherdata_pkey"
        )
        schema_editor.execute(
            "ALTER TABLE environmental_weatherdata ADD CONSTRAINT environmental_weatherdata_pkey PRIMARY KEY (id, timestamp)"
        )
        print("[OK] Updated WeatherData primary key")
    except Exception as e:
        print(f"[WARNING] Error updating WeatherData PK: {e}")


# Custom operations for TimescaleDB
def create_environmentalreading_hypertable(apps, schema_editor):
    """Create TimescaleDB hypertable for environmental readings"""
    # Skip if TimescaleDB is not available
    if not is_timescaledb_available():
        print("[WARNING] Skipping TimescaleDB operation: Create hypertable for environmental_environmentalreading on reading_time")
        return
        
    create_hypertable(
        schema_editor,
        'environmental_environmentalreading',
        'reading_time',
        if_not_exists=True,
        compression_params={
            'segmentby': 'container_id,parameter_id',
            'compress_after': '7 days'
        }
    )


def create_weatherdata_hypertable(apps, schema_editor):
    """Create TimescaleDB hypertable for weather data"""
    # Skip if TimescaleDB is not available
    if not is_timescaledb_available():
        print("[INFO] Skipping TimescaleDB operation: Create hypertable for environmental_weatherdata on timestamp")
        return
        
    create_hypertable(
        schema_editor,
        'environmental_weatherdata',
        'timestamp',
        if_not_exists=True,
        compression_params={
            'segmentby': 'area_id',
            'compress_after': '7 days'
        }
    )


# Migration noop for reverse operations that don't need to do anything
def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """
    Custom migration to set up TimescaleDB hypertables for time-series data.
    Modified to use conditional helpers that check if TimescaleDB is available.
    """

    dependencies = [
        ('environmental', '0001_initial'),
    ]

    operations = [
        # First update the primary keys
        migrations.RunPython(
            update_primary_keys,
            reverse_code=noop
        ),
        # Then create hypertables with compression using our helper functions
        migrations.RunPython(
            create_environmentalreading_hypertable,
            reverse_code=noop
        ),
        migrations.RunPython(
            create_weatherdata_hypertable,
            reverse_code=noop
        ),
    ]
