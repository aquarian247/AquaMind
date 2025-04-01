#!/usr/bin/env python
"""
Script to set up TimescaleDB tables for the AquaMind project.
This script handles the setup of TimescaleDB hypertables for PostgreSQL v17.
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """Get a connection to the database."""
    conn = psycopg2.connect(
        dbname='aquamind_db',
        user='postgres',
        password='adminpass1234',
        host='localhost',
        port='5432'
    )
    # Set autocommit mode to avoid transaction issues
    conn.autocommit = True
    return conn

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def check_hypertable_exists(cursor, table_name):
    """Check if a table is configured as a TimescaleDB hypertable."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM _timescaledb_catalog.hypertable
            WHERE table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def setup_environmental_reading_hypertable(cursor):
    """Set up the environmental_environmentalreading table as a TimescaleDB hypertable."""
    print("Setting up environmental_environmentalreading as a hypertable...")
    
    # First check if the table exists
    if not check_table_exists(cursor, 'environmental_environmentalreading'):
        print("⚠️ environmental_environmentalreading table does not exist!")
        return
    
    # Check if it's already a hypertable
    if check_hypertable_exists(cursor, 'environmental_environmentalreading'):
        print("✅ environmental_environmentalreading is already a hypertable")
        return
    
    # 1. Drop the default primary key constraint if it exists
    try:
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'environmental_environmentalreading_pkey' 
                        AND table_name = 'environmental_environmentalreading' 
                        AND table_schema = 'public') THEN
                    EXECUTE 'ALTER TABLE public.environmental_environmentalreading DROP CONSTRAINT environmental_environmentalreading_pkey;';
                    RAISE NOTICE 'Dropped default PK constraint for environmental_environmentalreading';
                END IF;
            END $$;
        """)
        print("✅ Dropped default PK constraint for environmental_environmentalreading (if it existed)")
    except Exception as e:
        print(f"⚠️ Error dropping PK constraint: {e}")
    
    # 2. Set the composite primary key
    try:
        cursor.execute("""
            ALTER TABLE public.environmental_environmentalreading 
            ADD PRIMARY KEY (reading_time, sensor_id);
        """)
        print("✅ Set composite primary key for environmental_environmentalreading")
    except Exception as e:
        print(f"⚠️ Error setting composite PK: {e}")
    
    # 3. Create the hypertable
    try:
        cursor.execute("""
            SELECT create_hypertable(
                'environmental_environmentalreading', 
                'reading_time',
                partitioning_column => 'sensor_id',
                number_partitions => 16,
                chunk_time_interval => INTERVAL '7 days',
                if_not_exists => TRUE
            );
        """)
        print("✅ Created hypertable for environmental_environmentalreading")
    except Exception as e:
        print(f"⚠️ Error creating hypertable: {e}")
    
    # 4. Enable compression (optional but recommended for time-series data)
    try:
        cursor.execute("""
            ALTER TABLE environmental_environmentalreading SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'sensor_id,parameter_id'
            );
        """)
        print("✅ Enabled compression for environmental_environmentalreading")
    except Exception as e:
        print(f"⚠️ Error enabling compression: {e}")
    
    # 5. Add compression policy (optional)
    try:
        cursor.execute("""
            SELECT add_compression_policy(
                'environmental_environmentalreading', 
                INTERVAL '7 days',
                if_not_exists => TRUE
            );
        """)
        print("✅ Added compression policy for environmental_environmentalreading")
    except Exception as e:
        print(f"⚠️ Error adding compression policy: {e}")

def setup_weather_data_hypertable(cursor):
    """Set up the environmental_weatherdata table as a TimescaleDB hypertable."""
    print("Setting up environmental_weatherdata as a hypertable...")
    
    # First check if the table exists
    if not check_table_exists(cursor, 'environmental_weatherdata'):
        print("⚠️ environmental_weatherdata table does not exist!")
        return
    
    # Check if it's already a hypertable
    if check_hypertable_exists(cursor, 'environmental_weatherdata'):
        print("✅ environmental_weatherdata is already a hypertable")
        return
    
    # 1. Drop the default primary key constraint if it exists
    try:
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'environmental_weatherdata_pkey' 
                        AND table_name = 'environmental_weatherdata' 
                        AND table_schema = 'public') THEN
                    EXECUTE 'ALTER TABLE public.environmental_weatherdata DROP CONSTRAINT environmental_weatherdata_pkey;';
                    RAISE NOTICE 'Dropped default PK constraint for environmental_weatherdata';
                END IF;
            END $$;
        """)
        print("✅ Dropped default PK constraint for environmental_weatherdata (if it existed)")
    except Exception as e:
        print(f"⚠️ Error dropping PK constraint: {e}")
    
    # 2. Set the composite primary key
    try:
        cursor.execute("""
            ALTER TABLE public.environmental_weatherdata 
            ADD PRIMARY KEY (timestamp, area_id);
        """)
        print("✅ Set composite primary key for environmental_weatherdata")
    except Exception as e:
        print(f"⚠️ Error setting composite PK: {e}")
    
    # 3. Create the hypertable
    try:
        cursor.execute("""
            SELECT create_hypertable(
                'environmental_weatherdata', 
                'timestamp',
                partitioning_column => 'area_id',
                number_partitions => 16,
                chunk_time_interval => INTERVAL '1 month',
                if_not_exists => TRUE
            );
        """)
        print("✅ Created hypertable for environmental_weatherdata")
    except Exception as e:
        print(f"⚠️ Error creating hypertable: {e}")
    
    # 4. Enable compression (optional but recommended for time-series data)
    try:
        cursor.execute("""
            ALTER TABLE environmental_weatherdata SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'area_id'
            );
        """)
        print("✅ Enabled compression for environmental_weatherdata")
    except Exception as e:
        print(f"⚠️ Error enabling compression: {e}")
    
    # 5. Add compression policy (optional)
    try:
        cursor.execute("""
            SELECT add_compression_policy(
                'environmental_weatherdata', 
                INTERVAL '30 days',
                if_not_exists => TRUE
            );
        """)
        print("✅ Added compression policy for environmental_weatherdata")
    except Exception as e:
        print(f"⚠️ Error adding compression policy: {e}")

def main():
    """Main function to set up TimescaleDB tables."""
    print("Setting up TimescaleDB tables for AquaMind...")
    
    try:
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if TimescaleDB extension is installed
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ TimescaleDB extension is installed (version: {result[1]})")
        else:
            print("⚠️ TimescaleDB extension is not installed!")
            print("Please install TimescaleDB and run 'CREATE EXTENSION IF NOT EXISTS timescaledb;'")
            return 1
        
        # Set up hypertables
        setup_environmental_reading_hypertable(cursor)
        setup_weather_data_hypertable(cursor)
        
        print("✅ TimescaleDB setup completed successfully!")
        return 0
    
    except Exception as e:
        print(f"❌ Error setting up TimescaleDB: {e}")
        return 1
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    sys.exit(main())
