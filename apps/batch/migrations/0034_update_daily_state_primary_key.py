# Generated migration for batch growth assimilation - Issue #112
# Phase 2: Update primary key for TimescaleDB compatibility

from django.db import migrations


def update_primary_key_for_timescaledb(apps, schema_editor):
    """
    Update ActualDailyAssignmentState primary key to include date column.
    
    TimescaleDB requires the partitioning column to be part of the primary key.
    This migration updates the PK from (id) to (id, date) when using PostgreSQL.
    Skips for SQLite and other databases.
    """
    # Skip if not PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        print("[INFO] Skipping PK update - not using PostgreSQL")
        return
    
    # Drop existing primary key constraint
    schema_editor.execute("""
        ALTER TABLE batch_actualdailyassignmentstate 
        DROP CONSTRAINT IF EXISTS batch_actualdailyassignmentstate_pkey;
    """)
    
    # Create composite primary key (id, date)
    schema_editor.execute("""
        ALTER TABLE batch_actualdailyassignmentstate 
        ADD PRIMARY KEY (id, date);
    """)
    
    print("[OK] Updated ActualDailyAssignmentState primary key to (id, date)")


def revert_primary_key(apps, schema_editor):
    """Revert to simple (id) primary key."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    
    # Drop composite primary key
    schema_editor.execute("""
        ALTER TABLE batch_actualdailyassignmentstate 
        DROP CONSTRAINT IF EXISTS batch_actualdailyassignmentstate_pkey;
    """)
    
    # Restore simple primary key
    schema_editor.execute("""
        ALTER TABLE batch_actualdailyassignmentstate 
        ADD PRIMARY KEY (id);
    """)
    
    print("[OK] Reverted ActualDailyAssignmentState primary key to (id)")


class Migration(migrations.Migration):
    """
    Update primary key for ActualDailyAssignmentState to support TimescaleDB.
    
    TimescaleDB hypertables require the partitioning column to be part of the primary key.
    This migration updates the PK from (id) to (id, date).
    """

    dependencies = [
        ('batch', '0033_create_actual_daily_state_model'),
    ]

    operations = [
        migrations.RunPython(
            update_primary_key_for_timescaledb,
            reverse_code=revert_primary_key
        ),
    ]



