#!/usr/bin/env python
"""
Simple script to test database connection to TimescaleDB.
"""
import psycopg2
import sys

def test_db_connection():
    """Test connection to the TimescaleDB database."""
    try:
        conn = psycopg2.connect(
            dbname='aquamind_db',
            user='postgres',
            password='aquapass12345',
            host='timescale-db',
            port='5432'
        )
        print("✅ Connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL version: {version[0]}")
        
        # Check if TimescaleDB is installed
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';")
        timescale = cursor.fetchone()
        if timescale:
            print(f"✅ TimescaleDB version: {timescale[1]}")
        else:
            print("❌ TimescaleDB extension is not installed!")
            return False
        
        # Check for some key tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"✅ Found {len(tables)} tables in the database")
        if tables:
            print("Sample tables:")
            for i, (table,) in enumerate(tables[:5], 1):
                print(f"  - {table}")
            if len(tables) > 5:
                print(f"  ... and {len(tables) - 5} more")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    success = test_db_connection()
    if not success:
        sys.exit(1)
