"""
Migration to properly handle TimescaleDB operations in a way that's compatible with testing.
This migration consolidates and fixes TimescaleDB-specific operations from previous migrations.
"""
from django.db import migrations

from apps.environmental.migrations_helpers import (
    is_timescaledb_available,
    run_timescale_sql,
    create_hypertable,
    set_compression
)


def update_primary_keys(apps, schema_editor):
    """
    Update primary keys to include the partitioning columns,
    which is required for TimescaleDB hypertables.
    """
    # Skip if not PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        print("Skipping PK update: Not PostgreSQL")
        return

    # Environmental Reading PK update
    run_timescale_sql(
        schema_editor,
        """
        DO $$
        BEGIN
            -- For EnvironmentalReading
            IF EXISTS (
                SELECT FROM pg_constraint 
                WHERE conname = 'environmental_environmentalreading_pkey'
            ) THEN
                ALTER TABLE environmental_environmentalreading 
                DROP CONSTRAINT environmental_environmentalreading_pkey;
                
                ALTER TABLE environmental_environmentalreading 
                ADD CONSTRAINT environmental_environmentalreading_pkey 
                PRIMARY KEY (id, reading_time);
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error updating EnvironmentalReading PK: %', SQLERRM;
        END $$;
        """,
        description="Update EnvironmentalReading primary key"
    )

    # Weather Data PK update
    run_timescale_sql(
        schema_editor,
        """
        DO $$
        BEGIN
            -- For WeatherData
            IF EXISTS (
                SELECT FROM pg_constraint 
                WHERE conname = 'environmental_weatherdata_pkey'
            ) THEN
                ALTER TABLE environmental_weatherdata 
                DROP CONSTRAINT environmental_weatherdata_pkey;
                
                ALTER TABLE environmental_weatherdata 
                ADD CONSTRAINT environmental_weatherdata_pkey 
                PRIMARY KEY (id, timestamp);
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error updating WeatherData PK: %', SQLERRM;
        END $$;
        """,
        description="Update WeatherData primary key"
    )


def setup_environmentalreading_hypertable(apps, schema_editor):
    """Set up TimescaleDB hypertable for EnvironmentalReading"""
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


def setup_weatherdata_hypertable(apps, schema_editor):
    """Set up TimescaleDB hypertable for WeatherData"""
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


def noop(apps, schema_editor):
    """No operation for reverse migrations"""
    pass


class Migration(migrations.Migration):
    """
    Migration to properly configure TimescaleDB hypertables with appropriate
    conditional handling to support both PostgreSQL and SQLite testing.
    """

    dependencies = [
        ('environmental', '0004_test_timescaledb_hypertable_setup'),
    ]

    operations = [
        # First update primary keys conditionally
        migrations.RunPython(
            update_primary_keys,
            reverse_code=noop
        ),
        
        # Then set up hypertables conditionally
        migrations.RunPython(
            setup_environmentalreading_hypertable,
            reverse_code=noop
        ),
        migrations.RunPython(
            setup_weatherdata_hypertable,
            reverse_code=noop
        ),
    ]
