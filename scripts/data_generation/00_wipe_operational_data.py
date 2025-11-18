#!/usr/bin/env python3
"""
Selective Operational Data Wipe

Deletes ONLY operational/transactional data while preserving foundational infrastructure.
Use this for fast test data regeneration cycles without recreating entire database.

PRESERVES (Foundational):
- Geographies, Areas, Stations, Halls, Containers, Sensors
- Feed types, Feed container infrastructure
- Lifecycle stages, Species
- Environmental parameters
- Health parameters, Lice types, Mortality reasons, Vaccination types
- User accounts and profiles
- Product grades
- Finance dimensions (companies, sites, policies)
- Scenario models (TGC, FCR, Mortality, Temperature profiles)

DELETES (Operational/Transactional):
- Batches and all batch-related data (assignments, transfers, workflows)
- Feed purchases, feed stock, feeding events
- Environmental readings, Weather data
- Health records (journal entries, lab samples, treatments, lice counts)
- Mortality events, Growth samples
- Harvest events and lots
- Finance facts (harvest facts, intercompany transactions)
- Scenarios (but not models)
- Audit history for deleted records

Usage:
    python scripts/data_generation/00_wipe_operational_data.py
    python scripts/data_generation/00_wipe_operational_data.py --confirm
"""

import os
import sys
import django
import argparse

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from django.db import connection
from apps.batch.models import (
    Batch, BatchContainerAssignment, MortalityEvent, GrowthSample,
    BatchTransferWorkflow, TransferAction,
    BatchCreationWorkflow, CreationAction
)
from apps.inventory.models import (
    FeedingEvent, FeedPurchase, FeedContainerStock
)
from apps.environmental.models import (
    EnvironmentalReading, WeatherData
)
from apps.health.models import (
    JournalEntry, LiceCount, HealthLabSample, Treatment,
    HealthSamplingEvent, IndividualFishObservation, FishParameterScore
)
from apps.harvest.models import (
    HarvestEvent, HarvestLot
)
from apps.finance.models import (
    FactHarvest, IntercompanyTransaction, NavExportBatch, NavExportLine
)
from apps.scenario.models import (
    Scenario, ScenarioProjection
)


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def delete_operational_data():
    """
    Delete all operational/transactional data in correct order.
    Uses raw SQL for history tables to avoid FK constraints.
    """
    
    print_section("DELETING OPERATIONAL DATA")
    
    # Track total records deleted
    total_deleted = 0
    
    # Define deletion order (respects FK constraints)
    deletions = [
        # Finance facts (no FK dependencies)
        ("Finance NAV Export Lines", NavExportLine.objects.all()),
        ("Finance NAV Export Batches", NavExportBatch.objects.all()),
        ("Finance Harvest Facts", FactHarvest.objects.all()),
        ("Finance Intercompany Transactions", IntercompanyTransaction.objects.all()),
        
        # Harvest (depends on batches)
        ("Harvest Lots", HarvestLot.objects.all()),
        ("Harvest Events", HarvestEvent.objects.all()),
        
        # Scenarios (but not models - keep TGC, FCR, Mortality, Temperature profiles)
        ("Scenario Projections", ScenarioProjection.objects.all()),
        ("Scenarios", Scenario.objects.all()),
        
        # Health records (depend on batches/assignments)
        ("Health Fish Parameter Scores", FishParameterScore.objects.all()),
        ("Health Individual Fish Observations", IndividualFishObservation.objects.all()),
        ("Health Sampling Events", HealthSamplingEvent.objects.all()),
        ("Health Treatments", Treatment.objects.all()),
        ("Health Lice Counts", LiceCount.objects.all()),
        ("Health Lab Samples", HealthLabSample.objects.all()),
        ("Health Journal Entries", JournalEntry.objects.all()),
        
        # Environmental time-series data (massive tables)
        ("Weather Data", WeatherData.objects.all()),
        ("Environmental Readings", EnvironmentalReading.objects.all()),
        
        # Feed/Inventory (depend on batches/assignments)
        ("Feeding Events", FeedingEvent.objects.all()),
        ("Feed Container Stock", FeedContainerStock.objects.all()),
        ("Feed Purchases", FeedPurchase.objects.all()),
        
        # Batch-related (cascading deletes in correct order)
        ("Batch Growth Samples", GrowthSample.objects.all()),
        ("Batch Mortality Events", MortalityEvent.objects.all()),
        ("Batch Transfer Actions", TransferAction.objects.all()),
        ("Batch Transfer Workflows", BatchTransferWorkflow.objects.all()),
        ("Batch Creation Actions", CreationAction.objects.all()),
        ("Batch Creation Workflows", BatchCreationWorkflow.objects.all()),
        ("Batch Container Assignments", BatchContainerAssignment.objects.all()),
        ("Batches", Batch.objects.all()),
    ]
    
    for name, queryset in deletions:
        count = queryset.count()
        if count > 0:
            queryset.delete()
            total_deleted += count
            print(f"✓ Deleted {count:,} {name}")
        else:
            print(f"  Skipped {name} (empty)")
    
    # Delete audit history for operational models
    print_section("CLEANING AUDIT HISTORY")
    
    history_tables = [
        'batch_historicalbatch',
        'batch_historicalbatchcontainerassignment',
        'batch_historicalbatchtransferworkflow',
        'batch_historicaltransferaction',
        'batch_historicalbatchcreationworkflow',
        'batch_historicalcreationaction',
        'inventory_historicalfeedcontainerstock',
        'inventory_historicalfeedingevent',
        'health_historicaljournalentry',
    ]
    
    history_deleted = 0
    with connection.cursor() as cursor:
        for table in history_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute(f"DELETE FROM {table}")
                    history_deleted += count
                    print(f"✓ Cleaned {count:,} records from {table}")
                else:
                    print(f"  Skipped {table} (empty)")
            except Exception as e:
                print(f"  ⚠ Could not clean {table}: {e}")
    
    total_deleted += history_deleted
    
    print_section("WIPE COMPLETE")
    print(f"Total records deleted: {total_deleted:,}")
    print(f"\nFoundational data PRESERVED:")
    print(f"  ✓ Infrastructure (geographies, areas, stations, halls, containers)")
    print(f"  ✓ Feed types and feed containers")
    print(f"  ✓ Lifecycle stages, species, environmental parameters")
    print(f"  ✓ Health parameters, lice types, mortality reasons")
    print(f"  ✓ User accounts and profiles")
    print(f"  ✓ Product grades, finance dimensions")
    print(f"  ✓ Scenario models (TGC, FCR, Mortality, Temperature profiles)")
    print(f"\nDatabase is ready for fresh operational data generation!")


def verify_preserved_data():
    """Verify foundational data still exists after wipe"""
    print_section("VERIFYING PRESERVED DATA")
    
    from apps.infrastructure.models import (
        Geography, Area, FreshwaterStation, Hall, Container, Sensor, FeedContainer
    )
    from apps.inventory.models import Feed
    from apps.batch.models import LifeCycleStage, Species
    from apps.environmental.models import EnvironmentalParameter
    from apps.health.models import HealthParameter, LiceType, MortalityReason
    from apps.harvest.models import ProductGrade
    from apps.finance.models import DimCompany, DimSite, IntercompanyPolicy
    from apps.scenario.models import TGCModel, FCRModel, MortalityModel, TemperatureProfile
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    checks = [
        ("Geographies", Geography.objects.count(), 2),
        ("Areas", Area.objects.count(), 20),
        ("Freshwater Stations", FreshwaterStation.objects.count(), 10),
        ("Halls", Hall.objects.count(), 50),
        ("Containers", Container.objects.count(), 1500),
        ("Feed Containers", FeedContainer.objects.count(), 200),
        ("Sensors", Sensor.objects.count(), 1000),
        ("Lifecycle Stages", LifeCycleStage.objects.count(), 6),
        ("Species", Species.objects.count(), 1),
        ("Feed Types", Feed.objects.count(), 6),
        ("Environmental Parameters", EnvironmentalParameter.objects.count(), 5),
        ("Health Parameters", HealthParameter.objects.count(), 5),
        ("Lice Types", LiceType.objects.count(), 10),
        ("Mortality Reasons", MortalityReason.objects.count(), 5),
        ("Product Grades", ProductGrade.objects.count(), 5),
        ("Users", User.objects.count(), 1),
        ("TGC Models", TGCModel.objects.count(), 1),
        ("FCR Models", FCRModel.objects.count(), 1),
        ("Mortality Models", MortalityModel.objects.count(), 1),
    ]
    
    all_good = True
    for name, actual, expected_min in checks:
        status = "✓" if actual >= expected_min else "⚠"
        print(f"{status} {name}: {actual:,} (expected ≥ {expected_min})")
        if actual < expected_min:
            all_good = False
    
    # Verify operational data is gone
    print(f"\nVerifying operational data deleted:")
    operational_checks = [
        ("Batches", Batch.objects.count(), 0),
        ("Assignments", BatchContainerAssignment.objects.count(), 0),
        ("Feeding Events", FeedingEvent.objects.count(), 0),
        ("Feed Purchases", FeedPurchase.objects.count(), 0),
        ("Environmental Readings", EnvironmentalReading.objects.count(), 0),
        ("Scenarios", Scenario.objects.count(), 0),
    ]
    
    for name, actual, expected in operational_checks:
        status = "✓" if actual == expected else "✗"
        print(f"{status} {name}: {actual:,} (expected {expected})")
        if actual != expected:
            all_good = False
    
    if all_good:
        print(f"\n✅ All checks passed! Database is clean and ready.")
    else:
        print(f"\n⚠️  Some checks failed. Review output above.")
    
    return all_good


def main():
    parser = argparse.ArgumentParser(
        description='Selective wipe of operational data (preserves infrastructure)'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually execute the wipe (otherwise dry-run)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  Selective Operational Data Wipe".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    if not args.confirm:
        print_section("DRY RUN MODE")
        print("This script will delete ALL operational data:")
        print("  - Batches and all related data")
        print("  - Feed purchases, stock, and feeding events")
        print("  - Environmental readings and weather data")
        print("  - Health records, treatments, and observations")
        print("  - Harvest events and lots")
        print("  - Finance facts and transactions")
        print("  - Scenarios (but not models)")
        print("  - Audit history for deleted records")
        print()
        print("Foundational data will be PRESERVED:")
        print("  ✓ Infrastructure, feed types, parameters, models")
        print()
        print("To execute, run:")
        print("  python scripts/data_generation/00_wipe_operational_data.py --confirm")
        return 0
    
    try:
        # Confirm one more time
        print_section("⚠️  FINAL CONFIRMATION")
        print("You are about to DELETE all operational data.")
        print("This action CANNOT be undone.")
        print()
        response = input("Type 'DELETE' to confirm: ")
        
        if response != 'DELETE':
            print("\n❌ Wipe cancelled.")
            return 1
        
        # Execute wipe
        delete_operational_data()
        
        # Verify
        verify_preserved_data()
        
        print_section("✅ WIPE SUCCESSFUL")
        print("You can now run test data generation scripts:")
        print()
        print("  # Single test batch (15 min)")
        print("  python scripts/data_generation/03_event_engine_core.py \\")
        print("    --start-date 2025-01-01 --eggs 3500000 \\")
        print("    --geography 'Faroe Islands' --duration 200")
        print()
        print("  # Full 20-batch generation (sequential, 8-12 hours)")
        print("  python scripts/data_generation/04_batch_orchestrator.py \\")
        print("    --execute --batches 20")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during wipe: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

