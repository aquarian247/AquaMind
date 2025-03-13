#!/usr/bin/env python
"""
Script to inspect the database schema of the AquaMind application.
Displays all tables, their columns, and relationships.
"""
import sys
import psycopg2
from decimal import Decimal

def get_db_connection():
    """Get a connection to the production database using direct connection details."""
    conn = psycopg2.connect(
        dbname='aquamind_db',
        user='postgres',
        password='aquapass12345',
        host='timescale-db', 
        port='5432'
    )
    return conn

def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def inspect_tables(conn):
    """Get all tables in the database."""
    print_section_header("DATABASE TABLES")
    
    cursor = conn.cursor()
    
    # Query to get all tables (excluding PostgreSQL system tables)
    cursor.execute("""
        SELECT 
            table_name 
        FROM 
            information_schema.tables 
        WHERE 
            table_schema='public' 
        ORDER BY 
            table_name
    """)
    
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} tables:\n")
    for i, (table,) in enumerate(tables, 1):
        print(f"{i}. {table}")
    
    return [table[0] for table in tables]

def inspect_table_columns(conn, tables):
    """Get detailed information about columns for each table."""
    print_section_header("TABLE COLUMNS")
    
    cursor = conn.cursor()
    
    for table in tables:
        print(f"\nTable: {table}")
        print("-" * 80)
        
        # Query to get column details
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM 
                information_schema.columns 
            WHERE 
                table_schema='public' AND 
                table_name=%s 
            ORDER BY 
                ordinal_position
        """, (table,))
        
        columns = cursor.fetchall()
        
        print(f"{'Column':<25} {'Type':<20} {'Nullable':<10} {'Default':<20} {'Max Length'}")
        print(f"{'-'*25} {'-'*20} {'-'*10} {'-'*20} {'-'*10}")
        
        for col_name, data_type, is_nullable, default, max_length in columns:
            nullable = "YES" if is_nullable == "YES" else "NO"
            default = str(default)[:18] + "..." if default and len(str(default)) > 20 else default
            print(f"{col_name:<25} {data_type:<20} {nullable:<10} {default or '':<20} {max_length or ''}")

def inspect_foreign_keys(conn, tables):
    """Get all foreign key relationships."""
    print_section_header("FOREIGN KEY RELATIONSHIPS")
    
    cursor = conn.cursor()
    
    for table in tables:
        # Query to get foreign key constraints
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
            WHERE
                tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name=%s
        """, (table,))
        
        foreign_keys = cursor.fetchall()
        
        if foreign_keys:
            print(f"\nForeign Keys for table: {table}")
            print(f"{'Column':<25} {'References Table':<25} {'References Column'}")
            print(f"{'-'*25} {'-'*25} {'-'*25}")
            
            for column, ref_table, ref_column in foreign_keys:
                print(f"{column:<25} {ref_table:<25} {ref_column}")

def inspect_indexes(conn, tables):
    """Get all indexes for the tables."""
    print_section_header("INDEXES")
    
    cursor = conn.cursor()
    
    for table in tables:
        # Query to get indexes
        cursor.execute("""
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique
            FROM
                pg_class t,
                pg_class i,
                pg_index ix,
                pg_attribute a
            WHERE
                t.oid = ix.indrelid
                AND i.oid = ix.indexrelid
                AND a.attrelid = t.oid
                AND a.attnum = ANY(ix.indkey)
                AND t.relkind = 'r'
                AND t.relname = %s
            ORDER BY
                t.relname,
                i.relname
        """, (table,))
        
        indexes = cursor.fetchall()
        
        if indexes:
            print(f"\nIndexes for table: {table}")
            print(f"{'Index Name':<35} {'Column':<25} {'Unique'}")
            print(f"{'-'*35} {'-'*25} {'-'*10}")
            
            for idx_name, column, is_unique in indexes:
                unique = "YES" if is_unique else "NO"
                print(f"{idx_name:<35} {column:<25} {unique}")

def inspect_hypertables(conn):
    """Identify TimescaleDB hypertables."""
    print_section_header("TIMESCALEDB HYPERTABLES")
    
    cursor = conn.cursor()
    
    try:
        # Check if TimescaleDB is installed
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if not cursor.fetchone():
            print("TimescaleDB extension is not installed in this database.")
            return
        
        # Query TimescaleDB hypertables - improved query that works with TimescaleDB
        cursor.execute("""
            SELECT 
                t.table_name,
                t.schema_name,
                d.column_name as time_dimension
            FROM 
                _timescaledb_catalog.hypertable t
            JOIN 
                _timescaledb_catalog.dimension d ON t.id = d.hypertable_id
            WHERE 
                d.column_type = 1
            ORDER BY 
                t.table_name
        """)
        
        hypertables = cursor.fetchall()
        
        if hypertables:
            print(f"Found {len(hypertables)} hypertables:\n")
            print(f"{'Table Name':<35} {'Schema':<15} {'Time Dimension'}")
            print(f"{'-'*35} {'-'*15} {'-'*20}")
            
            for table, schema, time_dim in hypertables:
                print(f"{table:<35} {schema:<15} {time_dim}")
        else:
            print("No TimescaleDB hypertables found in the database.")
            
    except Exception as e:
        print(f"Error inspecting hypertables: {e}")

def main():
    """Main function to inspect the database schema."""
    try:
        conn = get_db_connection()
        
        # Inspect database objects
        tables = inspect_tables(conn)
        inspect_table_columns(conn, tables)
        inspect_foreign_keys(conn, tables)
        inspect_indexes(conn, tables)
        inspect_hypertables(conn)
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
