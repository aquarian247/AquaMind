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
    try:
        conn = psycopg2.connect(
            dbname='aquamind_db',
            user='postgres',
            password='adminpass1234',
            host='localhost', 
            port='5432'
        )
        print("✓ Successfully connected to the database.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"× Error connecting to the database: {e}")
        print("× Please check your connection details and database status.")
        sys.exit(1)
    except Exception as e:
        print(f"× Unexpected error: {e}")
        sys.exit(1)

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
        
        for col_name, data_type, is_nullable, default, max_length in columns:
            nullable = "YES" if is_nullable == "YES" else "NO"
            default_str = str(default)[:18] + "..." if default and len(str(default)) > 20 else default or 'None'
            print(f"  Column: {col_name}")
            print(f"    Type: {data_type}")
            print(f"    Nullable: {nullable}")
            print(f"    Default: {default_str}")
            if max_length:
                print(f"    Max Length: {max_length}")
            print("")

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
        
        fkeys = cursor.fetchall()
        
        if fkeys:
            print(f"\nForeign Keys for {table}:")
            print("-" * 80)
            
            for col, ftable, fcol in fkeys:
                print(f"  {col} -> {ftable}.{fcol}")

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
                i.relname, a.attnum
        """, (table,))
        
        indexes = cursor.fetchall()
        
        if indexes:
            print(f"\nIndexes for {table}:")
            print("-" * 80)
            
            current_index = ""
            for idx_name, column, is_unique in indexes:
                if idx_name != current_index:
                    current_index = idx_name
                    unique_str = "(UNIQUE)" if is_unique else ""
                    print(f"  Index: {idx_name} {unique_str}")
                    print(f"    Column: {column}")
                else:
                    print(f"    Column: {column}")

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
        
        print("✓ TimescaleDB extension is installed.")
        
        # Try to query TimescaleDB hypertables - first check if catalog tables exist
        try:
            # Query TimescaleDB hypertables
            cursor.execute("""
                SELECT 
                    t.table_name,
                    t.schema_name,
                    d.column_name as time_dimension
                FROM 
                    _timescaledb_catalog.hypertable t
                JOIN 
                    _timescaledb_catalog.dimension d ON t.id = d.hypertable_id
                ORDER BY 
                    t.table_name, d.column_name
            """)
            
            hypertables = cursor.fetchall()
            
            if hypertables:
                print(f"\nFound {len(hypertables)} hypertable dimensions:")
                print("-" * 80)
                
                current_table = ""
                for table, schema, dim_col in hypertables:
                    if table != current_table:
                        current_table = table
                        print(f"\nHypertable: {table} (Schema: {schema})")
                        print(f"  Dimension Column: {dim_col}")
                    else:
                        print(f"  Dimension Column: {dim_col}")
            else:
                print("\nNo hypertables found in the database.")
                
        except psycopg2.errors.UndefinedTable:
            # Try using the information schema view instead (available in newer TimescaleDB versions)
            try:
                cursor.execute("""
                    SELECT 
                        hypertable_name,
                        hypertable_schema,
                        'N/A' as dimension_column
                    FROM 
                        timescaledb_information.hypertables
                    ORDER BY 
                        hypertable_name
                """)
                
                hypertables = cursor.fetchall()
                
                if hypertables:
                    print(f"\nFound {len(hypertables)} hypertables (using information schema):")
                    print("-" * 80)
                    
                    for table, schema, _ in hypertables:
                        print(f"Hypertable: {table} (Schema: {schema})")
                else:
                    print("\nNo hypertables found in the database.")
            except Exception as e:
                print(f"Could not query hypertables using information schema: {e}")
                print("The database may be using a different TimescaleDB schema or version.")
        
    except Exception as e:
        print(f"Error inspecting TimescaleDB hypertables: {e}")
        print("This may occur if the database is not PostgreSQL with TimescaleDB.")

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
