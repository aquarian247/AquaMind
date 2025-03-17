#!/usr/bin/env python
"""
Script to fix the migration state after a failed migration.
"""
import psycopg2

def fix_migration_state():
    """Connect to the database and fix the migration state."""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname='aquamind_db',
            user='postgres',
            password='aquapass12345',
            host='timescale-db',
            port='5432'
        )
        
        # Set autocommit mode to avoid transaction issues
        conn.autocommit = True
        
        cursor = conn.cursor()
        
        # Check if the migration has been recorded
        cursor.execute("""
            SELECT * FROM django_migrations 
            WHERE app = 'environmental' AND name = '0004_test_timescaledb_hypertable_setup'
        """)
        
        if cursor.fetchone():
            print("Migration 0004_test_timescaledb_hypertable_setup is already recorded.")
        else:
            # Record the migration as applied
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('environmental', '0004_test_timescaledb_hypertable_setup', NOW())
            """)
            print("Recorded migration 0004_test_timescaledb_hypertable_setup as applied.")
        
        # Check if the next migration has been recorded
        cursor.execute("""
            SELECT * FROM django_migrations 
            WHERE app = 'environmental' AND name = '0005_fix_timescaledb_integration'
        """)
        
        if cursor.fetchone():
            print("Migration 0005_fix_timescaledb_integration is already recorded.")
        else:
            # Record the migration as applied
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('environmental', '0005_fix_timescaledb_integration', NOW())
            """)
            print("Recorded migration 0005_fix_timescaledb_integration as applied.")
        
        # Check if hypertables are properly set up
        cursor.execute("""
            SELECT * FROM _timescaledb_catalog.hypertable 
            WHERE table_name = 'environmental_environmentalreading'
        """)
        
        if cursor.fetchone():
            print("Hypertable for environmental_environmentalreading exists.")
        else:
            print("WARNING: Hypertable for environmental_environmentalreading does not exist!")
        
        cursor.execute("""
            SELECT * FROM _timescaledb_catalog.hypertable 
            WHERE table_name = 'environmental_weatherdata'
        """)
        
        if cursor.fetchone():
            print("Hypertable for environmental_weatherdata exists.")
        else:
            print("WARNING: Hypertable for environmental_weatherdata does not exist!")
        
        conn.close()
        print("Migration state fixed successfully.")
        return True
    except Exception as e:
        print(f"Error fixing migration state: {e}")
        return False

if __name__ == "__main__":
    fix_migration_state()
