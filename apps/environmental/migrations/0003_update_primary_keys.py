"""
Migration to update primary keys for TimescaleDB compatibility.
This migration is conditionally applied only in PostgreSQL environments.
"""
from django.db import migrations, connection


def update_primary_keys_if_postgres(apps, schema_editor):
    """
    Update primary keys for TimescaleDB compatibility, but only if using PostgreSQL.
    This function makes the migration compatible with SQLite for testing.
    """
    # Skip if not PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        print("Skipping primary key updates for TimescaleDB - not using PostgreSQL")
        return
    
    # Update EnvironmentalReading primary key
    try:
        schema_editor.execute(
            """
            -- First drop the existing constraint
            ALTER TABLE environmental_environmentalreading 
                DROP CONSTRAINT IF EXISTS environmental_environmentalreading_pkey;
            
            -- Then create a new composite primary key
            ALTER TABLE environmental_environmentalreading 
                ADD CONSTRAINT environmental_environmentalreading_pkey 
                PRIMARY KEY (id, reading_time);
            """
        )
        print("✓ Successfully updated EnvironmentalReading primary key")
    except Exception as e:
        print(f"⚠ Error updating EnvironmentalReading primary key: {e}")
    
    # Update WeatherData primary key
    try:
        schema_editor.execute(
            """
            -- First drop the existing constraint
            ALTER TABLE environmental_weatherdata 
                DROP CONSTRAINT IF EXISTS environmental_weatherdata_pkey;
            
            -- Then create a new composite primary key
            ALTER TABLE environmental_weatherdata 
                ADD CONSTRAINT environmental_weatherdata_pkey 
                PRIMARY KEY (id, timestamp);
            """
        )
        print("✓ Successfully updated WeatherData primary key")
    except Exception as e:
        print(f"⚠ Error updating WeatherData primary key: {e}")


def revert_primary_keys_if_postgres(apps, schema_editor):
    """
    Revert primary keys to original state, but only if using PostgreSQL.
    """
    # Skip if not PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        print("Skipping primary key reversion for TimescaleDB - not using PostgreSQL")
        return
    
    # Revert EnvironmentalReading primary key
    try:
        schema_editor.execute(
            """
            -- First drop the composite primary key
            ALTER TABLE environmental_environmentalreading 
                DROP CONSTRAINT IF EXISTS environmental_environmentalreading_pkey;
            
            -- Then create a simple id-only primary key
            ALTER TABLE environmental_environmentalreading 
                ADD CONSTRAINT environmental_environmentalreading_pkey 
                PRIMARY KEY (id);
            """
        )
    except Exception as e:
        print(f"⚠ Error reverting EnvironmentalReading primary key: {e}")
    
    # Revert WeatherData primary key
    try:
        schema_editor.execute(
            """
            -- First drop the composite primary key
            ALTER TABLE environmental_weatherdata 
                DROP CONSTRAINT IF EXISTS environmental_weatherdata_pkey;
            
            -- Then create a simple id-only primary key
            ALTER TABLE environmental_weatherdata 
                ADD CONSTRAINT environmental_weatherdata_pkey 
                PRIMARY KEY (id);
            """
        )
    except Exception as e:
        print(f"⚠ Error reverting WeatherData primary key: {e}")


class Migration(migrations.Migration):
    """
    Migration to update the primary key structure for TimescaleDB hypertables.
    TimescaleDB requires that the partitioning column be part of the primary key.
    
    This migration is conditionally applied only in PostgreSQL environments to
    ensure compatibility with SQLite for testing.
    """

    dependencies = [
        ('environmental', '0002_create_timescaledb_hypertables'),
    ]

    operations = [
        # Use RunPython with conditional execution instead of direct RunSQL
        migrations.RunPython(
            update_primary_keys_if_postgres,
            reverse_code=revert_primary_keys_if_postgres
        ),
    ]
