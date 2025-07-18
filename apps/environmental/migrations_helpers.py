"""
Helper functions for handling TimescaleDB operations during migrations.

These helpers provide a way to conditionally skip TimescaleDB operations
when running in test mode with SQLite or when TimescaleDB is not available.
This ensures that migrations can run smoothly in all environments while still
properly configuring TimescaleDB in production.
"""
import os
import sys
from django.conf import settings
from django.db import connection


def is_timescaledb_available():
    """
    Check if TimescaleDB operations should be performed.
    
    This function checks various conditions to determine if TimescaleDB operations
    should be performed:
    1. Is the database PostgreSQL? (required for TimescaleDB)
    2. Is TimescaleDB explicitly disabled in settings?
    3. Are we running tests without TimescaleDB testing enabled?
    
    Returns:
        bool: True if TimescaleDB operations should be performed, False otherwise.
    """
    # Skip TimescaleDB operations when using SQLite or other non-PostgreSQL databases
    if connection.vendor != 'postgresql':
        return False
    
    # Skip if explicitly disabled in settings (check both setting names)
    if (hasattr(settings, 'USE_TIMESCALEDB') and not settings.USE_TIMESCALEDB) or        (hasattr(settings, 'TIMESCALE_ENABLED') and not settings.TIMESCALE_ENABLED):
        return False
    
    # Skip if running in test mode and not explicitly enabled via environment variable
    testing_mode = 'test' in sys.argv
    timescale_testing_enabled = os.environ.get('USE_TIMESCALEDB_TESTING', '').lower() == 'true'
    
    if testing_mode and not timescale_testing_enabled:
        return False
    
    # Verify that TimescaleDB extension is actually available
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
            return cursor.fetchone() is not None
    except Exception:
        # If the check fails, assume TimescaleDB is not available
        return False


def run_timescale_sql(schema_editor, sql, params=None, description="TimescaleDB operation"):
    """
    Run a SQL statement only if TimescaleDB is available.
    
    This function conditionally executes TimescaleDB-specific SQL statements only when
    TimescaleDB is available in the environment. If TimescaleDB is not available,
    the operation is skipped with a message.
    
    Args:
        schema_editor: The schema editor to use for executing SQL
        sql: The SQL statement to execute
        params: Optional parameters for the SQL statement
        description: Human-readable description of the operation for logging
    
    Returns:
        bool: True if the operation was executed, False if it was skipped
    """
    if is_timescaledb_available():
        try:
            schema_editor.execute(sql, params)
            print(f"[OK] Successfully executed: {description}")
            return True
        except Exception as e:
            print(f"[WARNING] TimescaleDB operation failed ({description}): {e}")
            return False
    else:
        print(f"[INFO] Skipping TimescaleDB operation: {description}")
        return False


def create_hypertable(schema_editor, table_name, time_column, if_not_exists=True, 
                     chunk_time_interval=None, compression_params=None):
    """
    Create a TimescaleDB hypertable for the specified table.
    
    This is a wrapper around the create_hypertable function that handles
    error checking and conditionally skips the operation if TimescaleDB
    is not available.
    
    Args:
        schema_editor: The schema editor to use
        table_name: The name of the table to convert to a hypertable
        time_column: The name of the time column to use for partitioning
        if_not_exists: Whether to use the if_not_exists option
        chunk_time_interval: Optional interval for chunks
        compression_params: Optional dict with compression settings
        
    Returns:
        bool: True if the hypertable was created, False otherwise
    """
    # Build the create_hypertable statement
    sql = f"""
        SELECT create_hypertable(
            '{table_name}', 
            '{time_column}',
            if_not_exists => {'TRUE' if if_not_exists else 'FALSE'}
        );
    """
    
    # Add chunk_time_interval if specified
    if chunk_time_interval:
        sql = sql.replace(');', f", chunk_time_interval => '{chunk_time_interval}');")
        
    
    success = run_timescale_sql(
        schema_editor, 
        sql, 
        description=f"Create hypertable for {table_name} on {time_column}"
    )
    
    # Set up compression if requested and hypertable creation was successful
    if success and compression_params:
        set_compression(schema_editor, table_name, compression_params)
    
    return success


def set_compression(schema_editor, table_name, compression_params):
    """
    Enable TimescaleDB compression for a hypertable.
    
    Args:
        schema_editor: The schema editor to use
        table_name: The name of the hypertable
        compression_params: Dict with compression settings:
                           - segmentby: comma-separated list of columns
                           - orderby: column to order by
                           - compress_after: interval after which to compress
    
    Returns:
        bool: True if compression was enabled, False otherwise
    """
    # Enable compression on the table
    sql = f"""
        ALTER TABLE {table_name} SET (
            timescaledb.compress
    """
    
    # Add segmentby parameter if provided
    if 'segmentby' in compression_params:
        sql += f",\ntimescaledb.compress_segmentby = '{compression_params['segmentby']}'"
    
    # Add orderby parameter if provided
    if 'orderby' in compression_params:
        sql += f",\ntimescaledb.compress_orderby = '{compression_params['orderby']}'"
    
    sql += "\n);"
    
    # Set up compression
    success = run_timescale_sql(
        schema_editor, 
        sql, 
        description=f"Enable compression for {table_name}"
    )
    
    # Add compression policy if requested and compression was successfully enabled
    if success and 'compress_after' in compression_params:
        interval = compression_params['compress_after']
        compression_policy_sql = f"""
            SELECT add_compression_policy('{table_name}', INTERVAL '{interval}');
        """
        run_timescale_sql(
            schema_editor, 
            compression_policy_sql, 
            description=f"Add compression policy for {table_name} after {interval}"
        )
    
    return success
