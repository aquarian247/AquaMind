#!/usr/bin/env python
"""
Script to check if environmental_weatherdata table exists in the database
and create it if necessary for testing.
"""
import os
import sys
import django
from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

# Get database connection parameters from Django settings
db_settings = settings.DATABASES['default']
print(f"Connecting to database: {db_settings['NAME']}")

# Connect to the database
try:
    conn = psycopg2.connect(
        dbname=db_settings['NAME'],
        user=db_settings['USER'],
        password=db_settings['PASSWORD'],
        host=db_settings['HOST'],
        port=db_settings['PORT']
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    print("Connection successful!")
    
    # Check if environmental_weatherdata table exists
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'environmental_weatherdata'
        );
    """)
    table_exists = cursor.fetchone()[0]
    
    if table_exists:
        print("environmental_weatherdata table exists!")
        
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'environmental_weatherdata';
        """)
        columns = cursor.fetchall()
        print("\nColumns in environmental_weatherdata:")
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
    else:
        print("environmental_weatherdata table does not exist!")
        
        # Show all tables in the database
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        print("\nAvailable tables in database:")
        for table in tables:
            print(f"  {table[0]}")
    
    # Check if Django migrations table exists and show applied migrations
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'django_migrations'
        );
    """)
    migrations_table_exists = cursor.fetchone()[0]
    
    if migrations_table_exists:
        print("\nChecking applied migrations:")
        cursor.execute("""
            SELECT app, name 
            FROM django_migrations 
            WHERE app = 'environmental' 
            ORDER BY applied;
        """)
        migrations = cursor.fetchall()
        if migrations:
            for migration in migrations:
                print(f"  {migration[0]}.{migration[1]}")
        else:
            print("  No environmental migrations found!")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
