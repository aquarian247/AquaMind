#!/usr/bin/env python
"""
Test SQL Server connection defined in migration_config.json.
Useful for both FishTalk and AVEVA profiles.
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

import pyodbc

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')

CONFIG_MODULE_PATH = SCRIPT_DIR / 'config.py'
spec = importlib.util.spec_from_file_location('migration_config_module', CONFIG_MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load migration config helper at {CONFIG_MODULE_PATH}")
config_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = config_module
spec.loader.exec_module(config_module)
get_sqlserver_config = config_module.get_sqlserver_config


def test_connection(conn_key: str) -> bool:
    """Test SQL Server database connection and run basic queries."""
    sql_config = get_sqlserver_config(conn_key)

    print("=" * 80)
    print("SQL Server Connection Test")
    print("=" * 80)

    try:
        conn_str = sql_config.to_odbc_string()
        print(f"Connecting to: {sql_config.server}:{sql_config.port} ({conn_key})")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print("✅ Connected successfully!\n")
        print("Testing basic queries...")

        cursor.execute("SELECT @@VERSION as version")
        version = cursor.fetchone()[0][:100] + "..."
        print(f"✅ SQL Server Version: {version}")

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
            except Exception as e:  # pragma: no cover - inspection utility
                print(f"❌ {table}: Not found or error - {str(e)[:50]}...")

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
        print("1. Check if the Docker container for this profile is running")
        print(f"2. Verify connection details for '{conn_key}' in migration_config.json")
        print("3. Ensure Microsoft ODBC Driver 18 for SQL Server is installed")
        print("4. Check firewall settings")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Verify connectivity to the FishTalk SQL Server instance.")
    parser.add_argument(
        "--conn-key",
        default="fishtalk_readonly",
        help="Connection profile defined in migration_config.json (default: fishtalk_readonly)",
    )
    success = test_connection(parser.parse_args().conn_key)
    sys.exit(0 if success else 1)
