"""
A migration specifically to handle TimescaleDB hypertable creation during testing.
Modified to conditionally skip operations when not using PostgreSQL.
"""
from django.db import migrations
from apps.environmental.migrations_helpers import (
    is_timescaledb_available,
    create_hypertable,
    set_compression,
    run_timescale_sql
)


def create_hypertables_if_postgres(apps, schema_editor):
    """
    Create hypertables only if using PostgreSQL with TimescaleDB.
    This ensures compatibility with SQLite for testing.
    """
    # Skip if not PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        print("Skipping TimescaleDB hypertable setup - not using PostgreSQL")
        return
    
    # Check if TimescaleDB is actually available
    if not is_timescaledb_available():
        print("Skipping TimescaleDB hypertable setup - TimescaleDB not available")
        return
    
    # Set up EnvironmentalReading hypertable
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
    
    # Set up WeatherData hypertable
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


# No-op function for reversing operations (nothing to do)
def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """
    Custom migration for setting up TimescaleDB hypertables in the test environment.
    Modified to skip operations when not using PostgreSQL to ensure SQLite compatibility.
    """

    dependencies = [
        ('environmental', '0003_update_primary_keys'),
    ]

    operations = [
        # Use a single RunPython operation with conditional checks
        migrations.RunPython(
            create_hypertables_if_postgres,
            reverse_code=noop
        ),
    ]
