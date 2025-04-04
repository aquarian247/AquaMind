#!/usr/bin/env python
"""
Script to run a specific SQL query on the AquaMind database.
"""
import psycopg2
from psycopg2.extras import RealDictCursor

def run_query(query):
    """Run a SQL query and print the results."""
    # Use the connection details from settings.py directly
    conn = psycopg2.connect(
        dbname='aquamind_db',
        user='postgres',
        password='aquapass12345',
        host='timescale-db',  # Using the host from the database container
        port='5432',
        cursor_factory=RealDictCursor
    )
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Fetch results
        results = cursor.fetchall()
        
        if results:
            # Get column names
            columns = list(results[0].keys())
            
            # Print header
            header = " | ".join(f"{col}" for col in columns)
            print(header)
            print("-" * len(header))
            
            # Print rows
            for row in results:
                row_values = []
                for col in columns:
                    value = row[col]
                    # Format value as string, truncate if too long
                    if value is None:
                        row_values.append("NULL")
                    else:
                        str_value = str(value)
                        if len(str_value) > 30:
                            str_value = str_value[:27] + "..."
                        row_values.append(str_value)
                
                print(" | ".join(row_values))
            
            print(f"\n{len(results)} row(s) returned")
        else:
            print("No results found")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Run the query for WeatherData table structure
    query = """SELECT column_name, data_type, is_nullable 
             FROM information_schema.columns 
             WHERE table_name = 'environmental_weatherdata' 
             ORDER BY ordinal_position;"""
    print(f"Running query: {query}\n")
    run_query(query)
