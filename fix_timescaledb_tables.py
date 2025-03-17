#!/usr/bin/env python
"""
Script to fix TimescaleDB tables that might be missing or incorrectly configured.
This script will:
1. Check if tables exist
2. Create missing tables if needed
3. Configure TimescaleDB hypertables properly
"""
import os
import sys
import psycopg2
from psycopg2 import sql

# Add the project root to the Python path
sys.path.append('/workspaces/AquaMind')

# Set up environment for TimescaleDB operations
os.environ['USE_TIMESCALEDB_TESTING'] = 'true'


def get_db_connection():
    """Get a connection to the database."""
    conn = psycopg2.connect(
        dbname='aquamind_db',
        user='postgres',
        password='aquapass12345',
        host='timescale-db',
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


def create_weatherdata_table(cursor):
    """Create the environmental_weatherdata table if it doesn't exist."""
    print("Creating environmental_weatherdata table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environmental_weatherdata (
            id BIGSERIAL NOT NULL,
            area_id INTEGER NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            temperature NUMERIC(5,2) NULL,
            wind_speed NUMERIC(6,2) NULL,
            wind_direction INTEGER NULL,
            precipitation NUMERIC(6,2) NULL,
            wave_height NUMERIC(5,2) NULL,
            wave_period NUMERIC(5,2) NULL,
            wave_direction INTEGER NULL,
            cloud_cover INTEGER NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT environmental_weatherdata_pkey PRIMARY KEY (id, timestamp),
            CONSTRAINT environmental_weatherdata_area_id_fkey 
                FOREIGN KEY (area_id) REFERENCES infrastructure_area (id) 
                ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
        );
        
        -- Create index on area_id and timestamp
        CREATE INDEX IF NOT EXISTS environmental_weatherdata_area_timestamp_idx
        ON environmental_weatherdata (area_id, timestamp);
    """)
    print("✅ environmental_weatherdata table created successfully")


def setup_weatherdata_hypertable(cursor):
    """Set up the environmental_weatherdata table as a TimescaleDB hypertable."""
    print("Setting up environmental_weatherdata as a hypertable...")
    
    # Create hypertable
    cursor.execute("""
        SELECT create_hypertable(
            'environmental_weatherdata', 
            'timestamp',
            if_not_exists => TRUE
        );
    """)
    print("✅ environmental_weatherdata hypertable created successfully")
    
    # Enable compression
    cursor.execute("""
        ALTER TABLE environmental_weatherdata SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'area_id'
        );
    """)
    print("✅ Compression enabled for environmental_weatherdata")
    
    # Add compression policy
    try:
        cursor.execute("""
            SELECT add_compression_policy(
                'environmental_weatherdata', 
                INTERVAL '7 days',
                if_not_exists => TRUE
            );
        """)
        print("✅ Compression policy added for environmental_weatherdata")
    except psycopg2.errors.UndefinedParameter:
        # Older versions of TimescaleDB might not support if_not_exists
        try:
            cursor.execute("""
                SELECT add_compression_policy(
                    'environmental_weatherdata', 
                    INTERVAL '7 days'
                );
            """)
            print("✅ Compression policy added for environmental_weatherdata")
        except Exception as e:
            print(f"⚠️ Could not add compression policy: {e}")


def check_environmentalreading_hypertable(cursor):
    """Check and fix the environmental_environmentalreading hypertable if needed."""
    if not check_table_exists(cursor, 'environmental_environmentalreading'):
        print("⚠️ environmental_environmentalreading table does not exist!")
        return
    
    if not check_hypertable_exists(cursor, 'environmental_environmentalreading'):
        print("Setting up environmental_environmentalreading as a hypertable...")
        
        # First ensure primary key includes the time column
        try:
            cursor.execute("""
                DO $$
                BEGIN
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
            """)
        except Exception as e:
            print(f"⚠️ Could not update primary key: {e}")
        
        # Create hypertable
        cursor.execute("""
            SELECT create_hypertable(
                'environmental_environmentalreading', 
                'reading_time',
                if_not_exists => TRUE
            );
        """)
        print("✅ environmental_environmentalreading hypertable created successfully")
        
        # Enable compression
        cursor.execute("""
            ALTER TABLE environmental_environmentalreading SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'container_id,parameter_id'
            );
        """)
        print("✅ Compression enabled for environmental_environmentalreading")
        
        # Add compression policy
        try:
            cursor.execute("""
                SELECT add_compression_policy(
                    'environmental_environmentalreading', 
                    INTERVAL '7 days',
                    if_not_exists => TRUE
                );
            """)
            print("✅ Compression policy added for environmental_environmentalreading")
        except psycopg2.errors.UndefinedParameter:
            # Older versions of TimescaleDB might not support if_not_exists
            try:
                cursor.execute("""
                    SELECT add_compression_policy(
                        'environmental_environmentalreading', 
                        INTERVAL '7 days'
                    );
                """)
                print("✅ Compression policy added for environmental_environmentalreading")
            except Exception as e:
                print(f"⚠️ Could not add compression policy: {e}")
    else:
        print("✅ environmental_environmentalreading is already a hypertable")


def main():
    """Main function to fix TimescaleDB tables."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Checking TimescaleDB extension...")
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';")
        timescale = cursor.fetchone()
        if timescale:
            print(f"✅ TimescaleDB version: {timescale[1]}")
        else:
            print("❌ TimescaleDB extension is not installed!")
            return
        
        # Check and fix environmental_weatherdata table
        if not check_table_exists(cursor, 'environmental_weatherdata'):
            print("❌ environmental_weatherdata table does not exist")
            create_weatherdata_table(cursor)
            setup_weatherdata_hypertable(cursor)
        elif not check_hypertable_exists(cursor, 'environmental_weatherdata'):
            print("⚠️ environmental_weatherdata exists but is not a hypertable")
            setup_weatherdata_hypertable(cursor)
        else:
            print("✅ environmental_weatherdata is already a hypertable")
        
        # Check and fix environmental_environmentalreading hypertable
        check_environmentalreading_hypertable(cursor)
        
        # Verify tables are now properly set up
        print("\nVerifying TimescaleDB hypertables...")
        cursor.execute("""
            SELECT table_name, schema_name
            FROM _timescaledb_catalog.hypertable
            ORDER BY table_name;
        """)
        hypertables = cursor.fetchall()
        
        if hypertables:
            print(f"Found {len(hypertables)} hypertables:")
            for table, schema in hypertables:
                print(f"  - {schema}.{table}")
        else:
            print("No hypertables found in the database.")
        
        cursor.close()
        conn.close()
        print("\nTimescaleDB tables check and fix completed.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
