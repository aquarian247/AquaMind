from django.db import migrations, connection

# Import our custom helper functions for TimescaleDB operations
from apps.environmental.migrations_helpers import (
    run_timescale_sql,
    create_hypertable,
    set_compression,
    is_timescaledb_available
)


# Custom operations for TimescaleDB
def create_environmentalreading_hypertable(apps, schema_editor):
    """Create TimescaleDB hypertable for environmental readings"""
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
        # Create hypertables with compression using our helper functions
        migrations.RunPython(
            create_environmentalreading_hypertable,
            reverse_code=noop
        ),
        migrations.RunPython(
            create_weatherdata_hypertable,
            reverse_code=noop
        ),
    ]
