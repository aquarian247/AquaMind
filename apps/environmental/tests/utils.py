"""
Test utilities for the environmental app.
"""
from django.db import connection


def setup_timescaledb_test_tables():
    """
    Set up TimescaleDB hypertables for testing.
    
    Since Django's test framework recreates all tables from models for each test run,
    we need to manually set up the hypertables with proper constraints for TimescaleDB.
    """
    with connection.cursor() as cursor:
        # Check if environmental_environmentalreading is a table but not a hypertable
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'environmental_environmentalreading'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Check if it's already a hypertable
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM _timescaledb_catalog.hypertable
                    WHERE hypertable_name = 'environmental_environmentalreading'
                );
            """)
            is_hypertable = cursor.fetchone()[0]
            
            if not is_hypertable:
                # First, drop the primary key constraint
                cursor.execute("""
                    ALTER TABLE environmental_environmentalreading 
                    DROP CONSTRAINT environmental_environmentalreading_pkey;
                """)
                
                # Create a new primary key that includes the partitioning column
                cursor.execute("""
                    ALTER TABLE environmental_environmentalreading 
                    ADD CONSTRAINT environmental_environmentalreading_pkey 
                    PRIMARY KEY (id, reading_time);
                """)
                
                # Create the hypertable
                cursor.execute("""
                    SELECT create_hypertable(
                        'environmental_environmentalreading', 
                        'reading_time',
                        if_not_exists => TRUE
                    );
                """)
                
                # Set up compression
                cursor.execute("""
                    ALTER TABLE environmental_environmentalreading SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'container_id,parameter_id'
                    );
                """)
                
                # Add compression policy
                cursor.execute("""
                    SELECT add_compression_policy(
                        'environmental_environmentalreading', 
                        INTERVAL '7 days',
                        if_not_exists => TRUE
                    );
                """)
        
        # Now check and set up WeatherData
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'environmental_weatherdata'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Check if it's already a hypertable
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM _timescaledb_catalog.hypertable
                    WHERE hypertable_name = 'environmental_weatherdata'
                );
            """)
            is_hypertable = cursor.fetchone()[0]
            
            if not is_hypertable:
                # First, drop the primary key constraint
                cursor.execute("""
                    ALTER TABLE environmental_weatherdata 
                    DROP CONSTRAINT environmental_weatherdata_pkey;
                """)
                
                # Create a new primary key that includes the partitioning column
                cursor.execute("""
                    ALTER TABLE environmental_weatherdata 
                    ADD CONSTRAINT environmental_weatherdata_pkey 
                    PRIMARY KEY (id, timestamp);
                """)
                
                # Create the hypertable
                cursor.execute("""
                    SELECT create_hypertable(
                        'environmental_weatherdata', 
                        'timestamp',
                        if_not_exists => TRUE
                    );
                """)
                
                # Set up compression
                cursor.execute("""
                    ALTER TABLE environmental_weatherdata SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'area_id'
                    );
                """)
                
                # Add compression policy
                cursor.execute("""
                    SELECT add_compression_policy(
                        'environmental_weatherdata', 
                        INTERVAL '7 days',
                        if_not_exists => TRUE
                    );
                """)
