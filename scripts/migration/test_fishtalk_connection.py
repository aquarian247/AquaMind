#!/usr/bin/env python
"""
Test FishTalk Database Connection
Simple script to verify connection and explore schema
"""

import os
import sys
import json
import pyodbc
from datetime import datetime

# Add parent directory to path for Django imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

def load_config():
    """Load migration configuration"""
    config_path = os.path.join(os.path.dirname(__file__), 'migration_config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def test_connection():
    """Test FishTalk database connection and run basic queries"""
    config = load_config()

    print("=" * 80)
    print("FishTalk Database Connection Test")
    print("=" * 80)

    try:
        # Connect to FishTalk
        conn_str = (
            f"DRIVER={config['fishtalk']['driver']};"
            f"SERVER={config['fishtalk']['server']};"
            f"DATABASE={config['fishtalk']['database']};"
            f"UID={config['fishtalk']['uid']};"
            f"PWD={config['fishtalk']['pwd']};"
            f"PORT={config['fishtalk'].get('port', 1433)}"
        )

        print(f"Connecting to: {config['fishtalk']['server']}:{config['fishtalk'].get('port', 1433)}")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print("✅ Connected successfully!")
        print()

        # Test basic queries
        print("Testing basic queries...")

        # 1. Get database info
        cursor.execute("SELECT @@VERSION as version")
        version = cursor.fetchone()[0][:100] + "..."
        print(f"✅ SQL Server Version: {version}")

        # 2. List main tables we're interested in
        tables_of_interest = [
            'Populations', 'PlanPopulation', 'PlanContainer', 'PlanSite',
            'Feeding', 'HWFeeding', 'Mortality', 'UserSample',
            'PublicLiceSampleData', 'PublicWeightSamples', 'Project'
        ]

        print("\nChecking for key tables:")
        for table in tables_of_interest:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ {table}: {count:,} records")
            except Exception as e:
                print(f"❌ {table}: Not found or error - {str(e)[:50]}...")

        # 3. Sample data from Populations
        print("\nSample Populations data:")
        try:
            cursor.execute("""
                SELECT TOP 5
                    PopulationID, PopulationName,
                    StartTime, Status
                FROM Populations
                ORDER BY StartTime DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                print(f"  ID: {row[0]}, Name: {row[1]}, Start: {row[2]}, Status: {row[3]}")
        except Exception as e:
            print(f"❌ Error querying Populations: {e}")

        # 4. Sample PlanPopulation data
        print("\nSample PlanPopulation data:")
        try:
            cursor.execute("""
                SELECT TOP 5
                    PlanPopulationID, PopulationID,
                    Count, AvgWeight, Biomass
                FROM PlanPopulation
                ORDER BY PlanPopulationID DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                print(f"  PlanID: {row[0]}, PopID: {row[1]}, Count: {row[2]}, Weight: {row[3]}, Biomass: {row[4]}")
        except Exception as e:
            print(f"❌ Error querying PlanPopulation: {e}")

        # 5. Check for active batches
        print("\nActive batches summary:")
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_populations,
                    SUM(CASE WHEN pp.Status IN ('Active', 'Running', 'InProduction') THEN 1 ELSE 0 END) as active_populations
                FROM Populations p
                LEFT JOIN PublicPlanPopulation pp ON p.PopulationID = pp.PopulationID
            """)
            total, active = cursor.fetchone()
            print(f"  Total Populations: {total}")
            print(f"  Active Populations: {active}")
        except Exception as e:
            print(f"❌ Error getting batch summary: {e}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("✅ Connection test completed successfully!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check if FishTalk Docker container is running")
        print("2. Verify connection details in migration_config.json")
        print("3. Ensure ODBC driver is installed: 'ODBC Driver 17 for SQL Server'")
        print("4. Check firewall settings")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)








