#!/usr/bin/env python3
# flake8: noqa
"""Comprehensive migration verification report.

This script checks that all expected tables are populated after a migration run
and generates a detailed report on data coverage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aquamind.settings")
os.environ.setdefault("SKIP_CELERY_SIGNALS", "1")

from scripts.migration.safety import configure_migration_environment, assert_default_db_is_migration_db

configure_migration_environment()

import django

django.setup()
assert_default_db_is_migration_db()

from django.db import connection


def get_table_count(table_name: str) -> int:
    """Get the count of rows in a table."""
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        except Exception:
            return -1


def main() -> int:
    print("\n" + "=" * 70)
    print("COMPREHENSIVE MIGRATION VERIFICATION REPORT")
    print("=" * 70)

    # Define table categories
    must_have_tables = {
        "Infrastructure": [
            ("infrastructure_geography", "Geographic regions"),
            ("infrastructure_freshwaterstation", "FW stations"),
            ("infrastructure_hall", "Halls within stations"),
            ("infrastructure_area", "Sea areas"),
            ("infrastructure_container", "Tanks and pens"),
            ("infrastructure_containertype", "Container types"),
        ],
        "Batch Management": [
            ("batch_batch", "Batch records"),
            ("batch_batchcontainerassignment", "Container assignments"),
            ("batch_lifecyclestage", "Lifecycle stages (master)"),
            ("batch_species", "Species (master)"),
            ("batch_batchtransferworkflow", "Transfer workflows"),
            ("batch_transferaction", "Transfer actions"),
            ("batch_creationworkflow", "Creation workflows"),
            ("batch_creationaction", "Creation actions"),
            ("batch_mortalityevent", "Mortality events"),
        ],
        "Inventory": [
            ("inventory_feed", "Feed types (master)"),
            ("inventory_feedingevent", "Feeding events"),
        ],
        "Health": [
            ("health_treatment", "Treatments"),
            ("health_licecount", "Lice counts"),
            ("health_journalentry", "Journal entries"),
            ("health_mortalityreason", "Mortality reasons (master)"),
            ("health_vaccinationtype", "Vaccination types (master)"),
        ],
        "Environmental": [
            ("environmental_environmentalparameter", "Parameters (master)"),
            ("environmental_environmentalreading", "Sensor readings"),
        ],
        "Migration Support": [
            ("migration_support_externalidmap", "ID mappings"),
        ],
    }

    may_have_tables = [
        ("infrastructure_sensor", "Sensor metadata"),
        ("infrastructure_feedcontainer", "Feed containers"),
        ("batch_growthsample", "Growth samples"),
        ("batch_individualgrowthobservation", "Individual measurements"),
        ("health_healthsamplingevent", "Health sampling"),
        ("health_healthlabsample", "Lab samples"),
        ("inventory_feedpurchase", "Feed purchases"),
        ("inventory_feedcontainerstock", "Feed stock"),
        ("inventory_batchfeedingsummary", "Batch feeding summaries"),
        ("inventory_containerfeedingsummary", "Container feeding summaries"),
    ]

    # Scenario model tables (migrated separately from batch data)
    scenario_tables = {
        "Scenario Models": [
            ("scenario_temperatureprofile", "Temperature profiles"),
            ("scenario_temperaturereading", "Temperature readings"),
            ("scenario_tgcmodel", "TGC models"),
            ("scenario_fcrmodel", "FCR models"),
            ("scenario_fcrmodelstage", "FCR model stages"),
            ("scenario_mortalitymodel", "Mortality models"),
        ],
    }

    out_of_scope_prefixes = ["broodstock_", "planning_", "harvest_", "finance_", "historian_"]

    # Track results
    passed = 0
    failed = 0
    warnings = 0

    print("\n" + "-" * 70)
    print("MUST HAVE DATA (Core Migration)")
    print("-" * 70)

    for category, tables in must_have_tables.items():
        print(f"\n{category}:")
        for table_name, description in tables:
            count = get_table_count(table_name)
            if count > 0:
                status = "✓ PASS"
                passed += 1
            elif count == 0:
                status = "✗ FAIL"
                failed += 1
            else:
                status = "? ERROR"
                failed += 1
            print(f"  [{status}] {table_name:45} : {count:>8} rows  ({description})")

    print("\n" + "-" * 70)
    print("MAY HAVE DATA (Depending on Source)")
    print("-" * 70)

    for table_name, description in may_have_tables:
        count = get_table_count(table_name)
        if count > 0:
            status = "✓ PRESENT"
        elif count == 0:
            status = "○ EMPTY"
            warnings += 1
        else:
            status = "? ERROR"
        print(f"  [{status}] {table_name:45} : {count:>8} rows  ({description})")

    print("\n" + "-" * 70)
    print("SCENARIO MODELS (Master Data for Projections)")
    print("-" * 70)

    scenario_passed = 0
    scenario_empty = 0
    for category, tables in scenario_tables.items():
        print(f"\n{category}:")
        for table_name, description in tables:
            count = get_table_count(table_name)
            if count > 0:
                status = "✓ PRESENT"
                scenario_passed += 1
            elif count == 0:
                status = "○ EMPTY"
                scenario_empty += 1
            else:
                status = "? ERROR"
            print(f"  [{status}] {table_name:45} : {count:>8} rows  ({description})")

    # Scenario FK integrity checks
    print("\n  FK Integrity Checks:")
    with connection.cursor() as cursor:
        # Check TGCModel → TemperatureProfile FK
        cursor.execute("""
            SELECT COUNT(*) FROM scenario_tgcmodel tgc
            WHERE NOT EXISTS (
                SELECT 1 FROM scenario_temperatureprofile tp
                WHERE tp.profile_id = tgc.profile_id
            )
        """)
        orphan_tgc = cursor.fetchone()[0]
        if orphan_tgc == 0:
            print(f"    [✓] TGCModel → TemperatureProfile: All FKs valid")
        else:
            print(f"    [✗] TGCModel → TemperatureProfile: {orphan_tgc} orphaned records")

        # Check FCRModelStage → FCRModel FK
        cursor.execute("""
            SELECT COUNT(*) FROM scenario_fcrmodelstage fms
            WHERE NOT EXISTS (
                SELECT 1 FROM scenario_fcrmodel fm
                WHERE fm.model_id = fms.model_id
            )
        """)
        orphan_fcr_stage = cursor.fetchone()[0]
        if orphan_fcr_stage == 0:
            print(f"    [✓] FCRModelStage → FCRModel: All FKs valid")
        else:
            print(f"    [✗] FCRModelStage → FCRModel: {orphan_fcr_stage} orphaned records")

        # Check FCRModelStage → LifecycleStage FK
        cursor.execute("""
            SELECT COUNT(*) FROM scenario_fcrmodelstage fms
            WHERE NOT EXISTS (
                SELECT 1 FROM batch_lifecyclestage ls
                WHERE ls.id = fms.stage_id
            )
        """)
        orphan_fcr_ls = cursor.fetchone()[0]
        if orphan_fcr_ls == 0:
            print(f"    [✓] FCRModelStage → LifecycleStage: All FKs valid")
        else:
            print(f"    [✗] FCRModelStage → LifecycleStage: {orphan_fcr_ls} orphaned records")

    print("\n" + "-" * 70)
    print("OUT OF SCOPE (Should be empty or minimal)")
    print("-" * 70)

    out_of_scope_tables = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        all_tables = [row[0] for row in cursor.fetchall()]

    for table_name in sorted(all_tables):
        if any(table_name.startswith(prefix) for prefix in out_of_scope_prefixes):
            count = get_table_count(table_name)
            if count > 0:
                out_of_scope_tables.append((table_name, count))

    if out_of_scope_tables:
        for table_name, count in out_of_scope_tables:
            print(f"  [!] {table_name:45} : {count:>8} rows  (unexpected)")
    else:
        print("  All out-of-scope tables are empty (as expected)")

    # Per-batch analysis
    print("\n" + "-" * 70)
    print("PER-BATCH ANALYSIS")
    print("-" * 70)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                b.id,
                b.batch_number,
                b.status,
                b.lifecycle_stage_id,
                ls.name as lifecycle_stage_name,
                COUNT(DISTINCT bca.id) as assignment_count,
                COUNT(DISTINCT btw.id) as workflow_count
            FROM batch_batch b
            LEFT JOIN batch_lifecyclestage ls ON ls.id = b.lifecycle_stage_id
            LEFT JOIN batch_batchcontainerassignment bca ON bca.batch_id = b.id
            LEFT JOIN batch_batchtransferworkflow btw ON btw.batch_id = b.id
            GROUP BY b.id, b.batch_number, b.status, b.lifecycle_stage_id, ls.name
            ORDER BY b.batch_number
        """)
        batches = cursor.fetchall()

    print(f"\nTotal batches: {len(batches)}")
    print(f"\n{'Batch Number':<30} {'Status':<12} {'Stage':<12} {'Assign':<8} {'Workflows':<10}")
    print("-" * 80)

    for batch in batches:
        batch_id, batch_number, status, stage_id, stage_name, assign_count, workflow_count = batch
        print(f"{batch_number[:29]:<30} {status:<12} {(stage_name or 'N/A'):<12} {assign_count:<8} {workflow_count:<10}")

    # Check lifecycle stage coverage per batch
    print("\n" + "-" * 70)
    print("LIFECYCLE STAGE COVERAGE PER BATCH")
    print("-" * 70)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                b.batch_number,
                STRING_AGG(DISTINCT ls.name, ', ' ORDER BY ls.name) as stages
            FROM batch_batch b
            JOIN batch_batchcontainerassignment bca ON bca.batch_id = b.id
            JOIN batch_lifecyclestage ls ON ls.id = bca.lifecycle_stage_id
            GROUP BY b.batch_number
            ORDER BY b.batch_number
        """)
        stage_coverage = cursor.fetchall()

    for batch_number, stages in stage_coverage:
        stage_count = len(stages.split(", ")) if stages else 0
        print(f"  {batch_number[:40]:<40} : {stage_count}/6 stages - {stages}")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"\n  Core tables with data:      {passed} PASSED")
    print(f"  Core tables missing data:   {failed} FAILED")
    print(f"  Optional tables empty:      {warnings} WARNINGS")
    print(f"\n  Scenario models populated:  {scenario_passed}")
    print(f"  Scenario models empty:      {scenario_empty}")

    # Overall assessment
    print("\n" + "-" * 70)
    if failed == 0:
        print("✓ VERIFICATION PASSED - All required tables have data")
        return 0
    else:
        print(f"✗ VERIFICATION FAILED - {failed} required tables are empty")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
