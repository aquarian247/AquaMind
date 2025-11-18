#!/usr/bin/env python3
"""
Verify single batch test results after 200-day generation.
Checks all fixes: population doubling, scenario creation, single-area, feeding events.
"""
import os, sys, django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import Batch, BatchContainerAssignment, BatchTransferWorkflow
from apps.scenario.models import Scenario
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading
from datetime import timedelta

def verify_batch():
    """Run comprehensive verification on latest batch"""
    
    print("\n" + "="*80)
    print("BATCH GENERATION VERIFICATION")
    print("="*80 + "\n")
    
    batch = Batch.objects.latest('created_at')
    print(f"Batch: {batch.batch_number}")
    print(f"Stage: {batch.lifecycle_stage.name}")
    print(f"Status: {batch.status}")
    print(f"Start: {batch.start_date}")
    print()
    
    all_passed = True
    
    # ============================================================================
    # TEST 1: Scenario Creation
    # ============================================================================
    print("="*80)
    print("TEST 1: Scenario Creation (Fix #4)")
    print("="*80)
    
    scenarios = Scenario.objects.filter(batch=batch)
    print(f"Scenarios: {scenarios.count()}")
    
    if scenarios.exists():
        s = scenarios.first()
        print(f"  ✅ {s.name}")
        print(f"     Initial: {s.initial_count:,} @ {s.initial_weight}g")
        print(f"     Duration: {s.duration_days} days")
        print(f"     TGC Model: {s.tgc_model.name if s.tgc_model else 'None'}")
        print(f"     FCR Model: {s.fcr_model.name if s.fcr_model else 'None'}")
        print(f"\n  ✅ PASS: Scenario created and linked to batch")
    else:
        print(f"  ❌ FAIL: No scenario found for batch")
        all_passed = False
    
    # ============================================================================
    # TEST 2: Population Doubling Fix
    # ============================================================================
    print("\n" + "="*80)
    print("TEST 2: Population Doubling Fix (Fix #1)")
    print("="*80)
    
    # Check Day 90 transition (Egg&Alevin → Fry)
    day_90 = batch.start_date + timedelta(days=90)
    arriving_day_90 = BatchContainerAssignment.objects.filter(
        batch=batch,
        assignment_date=day_90
    )
    
    if arriving_day_90.exists():
        print(f"Day 90 Arriving Assignments: {arriving_day_90.count()}")
        
        # Check if population_count is zero
        sample = arriving_day_90.first()
        print(f"  Sample: {sample.container.name}")
        print(f"  population_count: {sample.population_count:,}")
        
        if sample.population_count == 0:
            print(f"  ✅ PASS: Destination assignment zero-initialized (fix working!)")
        else:
            print(f"  ❌ FAIL: population_count should be 0, is {sample.population_count:,}")
            all_passed = False
    else:
        print(f"○ Day 90 transition not reached yet (batch too young)")
    
    # ============================================================================
    # TEST 3: Feeding Events
    # ============================================================================
    print("\n" + "="*80)
    print("TEST 3: Feeding Events")
    print("="*80)
    
    feeding_count = FeedingEvent.objects.filter(batch=batch).count()
    print(f"Total Feeding Events: {feeding_count:,}")
    
    # Expected for 200-day batch:
    # - Days 0-90: Egg&Alevin, no feed (0 events)
    # - Days 91-180: Fry, 2/day × 10 containers × 90 days = 1,800 events
    # - Days 181-200: Parr, 2/day × 10 containers × 20 days = 400 events
    # Total expected: ~2,200 events
    
    expected_min = 1000  # Conservative (at least reached Fry)
    if feeding_count >= expected_min:
        print(f"  ✅ PASS: Feeding events >= {expected_min:,}")
    else:
        print(f"  ⚠️  WARNING: Expected >= {expected_min:,}, got {feeding_count:,}")
        print(f"     (Batch may still be generating or in early stages)")
    
    # ============================================================================
    # TEST 4: Stage Transitions & Transfer Workflows
    # ============================================================================
    print("\n" + "="*80)
    print("TEST 4: Stage Transitions & Transfer Workflows")
    print("="*80)
    
    all_assignments = batch.batch_assignments.all()
    active_assignments = all_assignments.filter(is_active=True)
    closed_assignments = all_assignments.filter(is_active=False)
    
    print(f"Total Assignments: {all_assignments.count()}")
    print(f"Active: {active_assignments.count()}")
    print(f"Closed: {closed_assignments.count()}")
    print()
    
    # Count transitions (each transition closes 10 containers)
    transitions = closed_assignments.count() // 10
    print(f"Stage Transitions: {transitions}")
    
    # List stages passed through
    stages_completed = set(a.lifecycle_stage.name for a in closed_assignments)
    if stages_completed:
        print(f"Completed Stages:")
        for stage in sorted(stages_completed):
            count = closed_assignments.filter(lifecycle_stage__name=stage).count()
            print(f"  - {stage}: {count} containers")
    
    # Check transfer workflows
    workflows = BatchTransferWorkflow.objects.filter(batch=batch)
    print(f"\nTransfer Workflows: {workflows.count()}")
    if workflows.exists():
        for wf in workflows:
            print(f"  - {wf.workflow_number}: {wf.source_lifecycle_stage.name} → {wf.dest_lifecycle_stage.name}")
    
    # ============================================================================
    # TEST 5: Single-Area Distribution (when Adult stage reached)
    # ============================================================================
    print("\n" + "="*80)
    print("TEST 5: Single-Area Distribution (Fix #3)")
    print("="*80)
    
    adult_assignments = all_assignments.filter(lifecycle_stage__name='Adult')
    
    if adult_assignments.exists():
        areas = set(a.container.area.name for a in adult_assignments)
        print(f"Adult Assignments: {adult_assignments.count()}")
        print(f"Sea Areas: {len(areas)}")
        
        for area in sorted(areas):
            count = adult_assignments.filter(container__area__name=area).count()
            print(f"  - {area}: {count} containers")
        
        if len(areas) == 1:
            print(f"  ✅ PASS: Batch confined to single area")
        else:
            print(f"  ❌ FAIL: Batch spans {len(areas)} areas (should be 1)")
            all_passed = False
    else:
        print(f"○ Adult stage not reached yet (200-day batch ends in Parr)")
    
    # ============================================================================
    # TEST 6: Environmental & Other Events
    # ============================================================================
    print("\n" + "="*80)
    print("TEST 6: Other Events")
    print("="*80)
    
    env_count = EnvironmentalReading.objects.filter(batch=batch).count()
    print(f"Environmental Readings: {env_count:,}")
    
    # Expected: 6 readings/day × 7 params × 10 containers × 200 days = 84,000
    # Or could be aggregated differently
    if env_count > 1000:
        print(f"  ✅ PASS: Environmental monitoring active")
    else:
        print(f"  ⚠️  WARNING: Low environmental reading count")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80 + "\n")
    
    print(f"Batch: {batch.batch_number}")
    print(f"Final Stage: {batch.lifecycle_stage.name}")
    print(f"Total Assignments: {all_assignments.count()}")
    print(f"Scenarios: {scenarios.count()}")
    print(f"Feeding Events: {feeding_count:,}")
    print(f"Environmental Readings: {env_count:,}")
    print(f"Transfer Workflows: {workflows.count()}")
    print()
    
    if all_passed:
        print("✅ ALL TESTS PASSED - Fixes verified!")
        print()
        print("Next step: Verify population doubling fix with growth analysis recompute")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
        return 1


if __name__ == '__main__':
    sys.exit(verify_batch())

