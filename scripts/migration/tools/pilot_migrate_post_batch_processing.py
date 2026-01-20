#!/usr/bin/env python3
# flake8: noqa
"""Post-batch migration processing: create scenarios, run growth analysis, and forward projections.

This script runs AFTER batch data migration is complete:
1. Creates scenarios for ACTIVE batches using migrated TGC/FCR/Mortality models
2. Pins scenarios to active batches
3. Runs Growth Analysis (ActualDailyAssignmentState computation)
4. Runs Live Forward Projections

Usage:
    # Dry run - see what would be processed
    python pilot_migrate_post_batch_processing.py --dry-run

    # Full run - all steps
    python pilot_migrate_post_batch_processing.py

    # Skip growth analysis (if already done)
    python pilot_migrate_post_batch_processing.py --skip-growth-analysis

    # Only run projections
    python pilot_migrate_post_batch_processing.py --skip-scenario-creation --skip-growth-analysis
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

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

from django.db import transaction, models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.batch.models import Batch, BatchContainerAssignment
from apps.scenario.models import (
    Scenario, TGCModel, FCRModel, MortalityModel, 
    ProjectionRun, ScenarioProjection
)
from apps.migration_support.models import ExternalIdMap
from scripts.migration.history import save_with_history

User = get_user_model()


def get_migration_user():
    """Get the migration user for audit trail."""
    user = User.objects.filter(username="system_admin").first()
    if not user:
        user = User.objects.filter(is_superuser=True).first()
    return user


def get_default_models():
    """Get default TGC, FCR, and Mortality models for scenario creation."""
    # Prefer FishTalk-migrated models
    tgc_model = TGCModel.objects.filter(name__startswith="FT-TGC-").first()
    if not tgc_model:
        tgc_model = TGCModel.objects.first()
    
    fcr_model = FCRModel.objects.filter(name__startswith="FT-FCR-").first()
    if not fcr_model:
        fcr_model = FCRModel.objects.first()
    
    mortality_model = MortalityModel.objects.filter(name__startswith="FT-Mortality-Standard").first()
    if not mortality_model:
        mortality_model = MortalityModel.objects.first()
    
    return tgc_model, fcr_model, mortality_model


def get_batch_initial_conditions(batch) -> tuple:
    """Get actual initial conditions from batch's first assignments.
    
    Returns (initial_count, initial_weight_g) from earliest assignment data.
    Falls back to reasonable defaults if data unavailable.
    """
    from apps.batch.models import BatchContainerAssignment
    
    # Get earliest assignments for this batch
    first_assignments = BatchContainerAssignment.objects.filter(
        batch=batch,
        assignment_date=batch.start_date
    )
    
    if not first_assignments.exists():
        # Fall back to earliest assignment regardless of date
        first_assignments = BatchContainerAssignment.objects.filter(
            batch=batch
        ).order_by('assignment_date')[:5]
    
    total_population = 0
    total_biomass_kg = 0
    
    for assign in first_assignments:
        if assign.population_count:
            total_population += assign.population_count
        if assign.biomass_kg:
            total_biomass_kg += float(assign.biomass_kg)
    
    # Calculate initial weight from biomass
    if total_population > 0 and total_biomass_kg > 0:
        initial_weight_g = (total_biomass_kg * 1000) / total_population
    else:
        # Default for early stage fish (Egg/Alevin ~0.1g, Fry ~1g)
        initial_weight_g = 0.5
    
    # Use actual population or reasonable default
    initial_count = total_population if total_population > 0 else 100000
    
    return initial_count, initial_weight_g


def create_scenarios_for_active_batches(dry_run: bool = False) -> dict:
    """Create scenarios for ACTIVE batches that don't have one."""
    print("\n" + "-" * 70)
    print("STEP 1: CREATE SCENARIOS FOR ACTIVE BATCHES")
    print("-" * 70)
    
    user = get_migration_user()
    tgc_model, fcr_model, mortality_model = get_default_models()
    
    if not all([tgc_model, fcr_model, mortality_model]):
        print("[ERROR] Missing required models (TGC, FCR, or Mortality)")
        print(f"  TGC: {tgc_model}")
        print(f"  FCR: {fcr_model}")
        print(f"  Mortality: {mortality_model}")
        return {"success": False, "error": "Missing models"}
    
    print(f"Using models:")
    print(f"  TGC: {tgc_model.name}")
    print(f"  FCR: {fcr_model.name}")
    print(f"  Mortality: {mortality_model.name}")
    
    # Get active batches without scenarios
    active_batches = Batch.objects.filter(status="ACTIVE")
    batches_needing_scenarios = active_batches.filter(
        models.Q(scenarios__isnull=True) | 
        models.Q(pinned_projection_run__isnull=True)
    ).distinct()
    
    total_active = active_batches.count()
    need_scenario = batches_needing_scenarios.count()
    
    print(f"\nActive batches: {total_active}")
    print(f"Needing scenarios: {need_scenario}")
    
    if dry_run:
        print("\n[DRY RUN] Would create scenarios for:")
        for batch in batches_needing_scenarios[:10]:
            initial_count, initial_weight = get_batch_initial_conditions(batch)
            print(f"  - {batch.batch_number} (pop={initial_count:,}, wt={initial_weight:.1f}g)")
        if need_scenario > 10:
            print(f"  ... and {need_scenario - 10} more")
        return {"success": True, "dry_run": True, "batches_found": need_scenario}
    
    created = 0
    pinned = 0
    errors = []
    
    for batch in batches_needing_scenarios:
        try:
            with transaction.atomic():
                # Check if scenario already exists
                existing_scenario = batch.scenarios.first()
                
                if not existing_scenario:
                    # Get actual initial conditions from migrated data
                    initial_count, initial_weight = get_batch_initial_conditions(batch)
                    
                    # Create new scenario with actual batch data
                    scenario = Scenario(
                        name=f"Migration Scenario - {batch.batch_number}",
                        start_date=batch.start_date,
                        duration_days=900,  # Standard lifecycle
                        initial_count=initial_count,
                        genotype="Atlantic Salmon",
                        supplier="FishTalk Migration",
                        initial_weight=initial_weight,
                        tgc_model=tgc_model,
                        fcr_model=fcr_model,
                        mortality_model=mortality_model,
                        batch=batch,
                        created_by=user,
                    )
                    scenario.save()
                    created += 1
                else:
                    scenario = existing_scenario
                
                # Create or get projection run
                projection_run = scenario.projection_runs.first()
                if not projection_run:
                    projection_run = ProjectionRun.objects.create(
                        scenario=scenario,
                        run_number=1,
                        label="Migration Baseline",
                        created_by=user,
                        parameters_snapshot={
                            "tgc_model": tgc_model.name,
                            "fcr_model": fcr_model.name,
                            "mortality_model": mortality_model.name,
                        },
                    )
                
                # Pin to batch
                if batch.pinned_projection_run != projection_run:
                    batch.pinned_projection_run = projection_run
                    batch.save(update_fields=["pinned_projection_run"])
                    pinned += 1
                    
        except Exception as e:
            errors.append({"batch": batch.batch_number, "error": str(e)})
    
    print(f"\nResults:")
    print(f"  Scenarios created: {created}")
    print(f"  Projection runs pinned: {pinned}")
    print(f"  Errors: {len(errors)}")
    
    if errors[:3]:
        print("\nSample errors:")
        for e in errors[:3]:
            print(f"  {e['batch']}: {e['error'][:80]}")
    
    return {
        "success": len(errors) == 0,
        "scenarios_created": created,
        "runs_pinned": pinned,
        "errors": len(errors),
    }


def run_growth_analysis(workers: int = 4, dry_run: bool = False) -> dict:
    """Run growth analysis (ActualDailyAssignmentState computation)."""
    print("\n" + "-" * 70)
    print("STEP 2: RUN GROWTH ANALYSIS")
    print("-" * 70)
    
    # Get batches with scenarios
    batches_with_scenarios = Batch.objects.filter(
        models.Q(pinned_projection_run__isnull=False) |
        models.Q(scenarios__isnull=False)
    ).distinct()
    
    count = batches_with_scenarios.count()
    print(f"Batches with scenarios: {count}")
    
    if dry_run:
        print("\n[DRY RUN] Would run growth analysis for all batches with scenarios")
        return {"success": True, "dry_run": True, "batches_found": count}
    
    # Import the optimized growth analysis
    from apps.batch.services.growth_assimilation_optimized import recompute_batch_assignments_optimized
    
    processed = 0
    total_states = 0
    errors = []
    start_time = time.time()
    
    for i, batch in enumerate(batches_with_scenarios, 1):
        try:
            result = recompute_batch_assignments_optimized(
                batch_id=batch.id,
                start_date=batch.start_date,
                end_date=batch.actual_end_date if batch.status == "COMPLETED" else None,
            )
            
            processed += 1
            states = result.get("total_rows_created", 0) + result.get("total_rows_updated", 0)
            total_states += states
            
            if i % 20 == 0:
                print(f"  [{i}/{count}] Processed {processed} batches, {total_states:,} states")
                
        except Exception as e:
            errors.append({"batch": batch.batch_number, "error": str(e)})
    
    elapsed = time.time() - start_time
    
    print(f"\nResults:")
    print(f"  Batches processed: {processed}")
    print(f"  States created/updated: {total_states:,}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"  Errors: {len(errors)}")
    
    return {
        "success": len(errors) == 0,
        "batches_processed": processed,
        "states_created": total_states,
        "elapsed_seconds": elapsed,
        "errors": len(errors),
    }


def run_live_forward_projections(dry_run: bool = False) -> dict:
    """Run live forward projections for active batches."""
    print("\n" + "-" * 70)
    print("STEP 3: RUN LIVE FORWARD PROJECTIONS")
    print("-" * 70)
    
    from apps.batch.models import LiveForwardProjection
    from apps.batch.services.live_projection_engine import LiveProjectionEngine
    
    computed_date = timezone.now().date()
    print(f"Computed date: {computed_date}")
    
    # Get active assignments for active batches with pinned scenarios
    active_assignments = BatchContainerAssignment.objects.filter(
        is_active=True,
        batch__status="ACTIVE",
    ).filter(
        models.Q(batch__pinned_projection_run__isnull=False) |
        models.Q(batch__scenarios__isnull=False)
    ).select_related(
        "batch__pinned_projection_run__scenario__tgc_model__profile",
        "batch__pinned_projection_run__scenario__mortality_model",
        "container"
    ).distinct()
    
    count = active_assignments.count()
    print(f"Active assignments to process: {count}")
    
    if dry_run:
        print("\n[DRY RUN] Would compute projections for all active assignments")
        return {"success": True, "dry_run": True, "assignments_found": count}
    
    processed = 0
    skipped = 0
    total_rows = 0
    errors = []
    start_time = time.time()
    
    for i, assignment in enumerate(active_assignments, 1):
        try:
            engine = LiveProjectionEngine(assignment)
            result = engine.compute_and_store(computed_date=computed_date)
            
            if result.get("success"):
                processed += 1
                total_rows += result.get("rows_created", 0)
            else:
                skipped += 1
                if result.get("error"):
                    errors.append({
                        "assignment_id": assignment.id,
                        "error": result["error"],
                    })
            
            if i % 50 == 0:
                print(f"  [{i}/{count}] Processed {processed}, {total_rows:,} rows")
                
        except Exception as e:
            errors.append({"assignment_id": assignment.id, "error": str(e)})
    
    elapsed = time.time() - start_time
    
    # Verify
    total_live = LiveForwardProjection.objects.filter(computed_date=computed_date).count()
    
    print(f"\nResults:")
    print(f"  Assignments processed: {processed}")
    print(f"  Assignments skipped: {skipped}")
    print(f"  Total rows created: {total_rows:,}")
    print(f"  LiveForwardProjection records today: {total_live:,}")
    print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"  Errors: {len(errors)}")
    
    return {
        "success": True,
        "assignments_processed": processed,
        "rows_created": total_rows,
        "elapsed_seconds": elapsed,
        "errors": len(errors),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Post-batch migration processing: scenarios, growth analysis, projections"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without running",
    )
    parser.add_argument(
        "--skip-scenario-creation",
        action="store_true",
        help="Skip scenario creation step",
    )
    parser.add_argument(
        "--skip-growth-analysis",
        action="store_true",
        help="Skip growth analysis step",
    )
    parser.add_argument(
        "--skip-projections",
        action="store_true",
        help="Skip live forward projections step",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of workers for growth analysis (default: 4)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    print("\n" + "=" * 70)
    print("POST-BATCH MIGRATION PROCESSING")
    print("=" * 70)
    
    if args.dry_run:
        print("[DRY RUN MODE]")
    
    results = {}
    
    # Step 1: Create scenarios
    if not args.skip_scenario_creation:
        results["scenarios"] = create_scenarios_for_active_batches(dry_run=args.dry_run)
    else:
        print("\n[SKIP] Scenario creation")
    
    # Step 2: Growth analysis
    if not args.skip_growth_analysis:
        results["growth_analysis"] = run_growth_analysis(
            workers=args.workers,
            dry_run=args.dry_run,
        )
    else:
        print("\n[SKIP] Growth analysis")
    
    # Step 3: Live forward projections
    if not args.skip_projections:
        results["projections"] = run_live_forward_projections(dry_run=args.dry_run)
    else:
        print("\n[SKIP] Live forward projections")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for step, result in results.items():
        if result.get("dry_run"):
            status = "DRY RUN"
        elif result.get("success"):
            status = "SUCCESS"
        else:
            status = "ERROR"
        print(f"  {step}: {status}")
    
    all_success = all(r.get("success", False) or r.get("dry_run", False) for r in results.values())
    
    if all_success:
        print("\n[SUCCESS] Post-batch migration processing completed!")
        return 0
    else:
        print("\n[WARNING] Some steps had errors")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
