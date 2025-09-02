#!/usr/bin/env python
"""
Database Wipe Script for AquaMind

Clears all data except users and their authentication data.
Use this to start fresh with data generation.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from scripts.data_generation.orchestrator.checkpoint_manager import CheckpointManager


def wipe_database():
    """Wipe all data except users and auth tables."""

    print("🧹 Starting database wipe...")

    # Tables to KEEP (user-related)
    keep_tables = [
        'auth_user',
        'auth_group',
        'auth_permission',
        'auth_user_groups',
        'auth_user_user_permissions',
        'auth_group_permissions',
        'users_userprofile',
    ]

    # Tables to WIPE (all app data)
    wipe_tables = [
        # Infrastructure
        'infrastructure_geography',
        'infrastructure_area',
        'infrastructure_freshwaterstation',
        'infrastructure_hall',
        'infrastructure_containertype',
        'infrastructure_container',
        'infrastructure_sensor',
        'infrastructure_feedcontainer',

        # Batch management
        'batch_species',
        'batch_lifecyclestage',
        'batch_batch',
        'batch_batchcontainerassignment',
        'batch_batchcomposition',
        'batch_batchtransfer',
        'batch_mortalityevent',
        'batch_growthsample',
        'batch_batchhistory',

        # Environmental
        'environmental_environmentalparameter',
        'environmental_environmentalreading',
        'environmental_photoperioddata',
        'environmental_weatherdata',
        'environmental_stagetransitionenvironmental',

        # Health
        'health_journalentry',
        'health_healthparameter',
        'health_healthsamplingevent',
        'health_individualfishobservation',
        'health_fishparameterscore',
        'health_mortalityreason',
        'health_mortalityrecord',
        'health_licecount',
        'health_vaccinationtype',
        'health_treatment',
        'health_sampletype',
        'health_healthlabsample',

        # Inventory/Feed
        'inventory_feed',
        'inventory_feedpurchase',
        'inventory_feedstock',
        'inventory_feedingevent',
        'inventory_feedcontainerstock',
        'inventory_batchfeedingsummary',

        # Operational
        'operational_operationalparameter',
        'operational_operationalreading',

        # Scenario
        'scenario_temperatureprofile',
        'scenario_temperaturereading',
        'scenario_tgcmodel',
        'scenario_fcrmodel',
        'scenario_fcrmodelstage',
        'scenario_mortalitymodel',
        'scenario_scenario',
        'scenario_scenariomodelchange',
        'scenario_scenarioprojection',

        # Broodstock (if exists)
        'broodstock_broodstockfish',
        'broodstock_fishmovement',
        'broodstock_breedingplan',
        'broodstock_breedingtraitpriority',
        'broodstock_breedingpair',
        'broodstock_eggproduction',
        'broodstock_eggsupplier',
        'broodstock_externaleggbatch',
        'broodstock_batchparentage',
        'broodstock_maintenancetask',

        # Historical tables
        'batch_historicalbatch',
        'infrastructure_historicalcontainer',
        'inventory_historicalfeedstock',
    ]

    with connection.cursor() as cursor:
        # Disable foreign key checks temporarily
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")

        # Wipe all data tables
        for table in wipe_tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                print(f"✓ Cleared {table}")
            except Exception as e:
                print(f"⚠ Could not clear {table}: {e}")

        # Re-enable foreign key checks
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")

    print("✓ Database tables cleared successfully!")


def wipe_checkpoints():
    """Clear all checkpoint files."""

    print("📁 Clearing checkpoint files...")

    # Use checkpoint manager to clear all checkpoints
    checkpoint_manager = CheckpointManager()
    checkpoint_manager.clear_all_checkpoints()

    # Also manually clear any remaining checkpoint files
    checkpoint_dir = Path("scripts/data_generation/checkpoints")
    if checkpoint_dir.exists():
        for file in checkpoint_dir.glob("*.json"):
            file.unlink()
            print(f"✓ Deleted {file}")

    print("✓ All checkpoint files cleared!")


def wipe_reports():
    """Clear all report files."""

    print("📊 Clearing report files...")

    report_dirs = [
        "scripts/data_generation/reports",
        "scripts/data_generation/checkpoints",
    ]

    for report_dir in report_dirs:
        dir_path = Path(report_dir)
        if dir_path.exists():
            for file in dir_path.glob("*.json"):
                file.unlink()
                print(f"✓ Deleted {file}")
            for file in dir_path.glob("*.md"):
                file.unlink()
                print(f"✓ Deleted {file}")

    print("✓ All report files cleared!")


def main():
    """Main wipe function."""

    print("🚨 AQUAMIND DATABASE WIPE")
    print("=" * 50)
    print("⚠️  WARNING: This will delete ALL data except users!")
    print("⚠️  Checkpoints and reports will also be cleared.")
    print()

    # Confirm with user
    response = input("Are you sure you want to wipe the database? (type 'YES' to confirm): ")
    if response != 'YES':
        print("❌ Wipe cancelled.")
        return

    print("\n🔄 Starting wipe process...\n")

    try:
        # Step 1: Wipe database tables
        wipe_database()

        # Step 2: Clear checkpoints
        wipe_checkpoints()

        # Step 3: Clear reports
        wipe_reports()

        print("\n" + "=" * 50)
        print("✅ DATABASE WIPE COMPLETE!")
        print("✅ Users and authentication data preserved")
        print("✅ All app data cleared")
        print("✅ Checkpoints cleared")
        print("✅ Reports cleared")
        print("\n🎯 Ready for fresh data generation!")

    except Exception as e:
        print(f"\n❌ ERROR during wipe: {e}")
        print("🔄 You may need to restore from backup!")
        sys.exit(1)


if __name__ == '__main__':
    main()

