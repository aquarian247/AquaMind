#!/usr/bin/env python3
"""
Comprehensive Test Data Verification
Validates data quality and volume after batch generation
"""
import os, sys, django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import Batch, ActualDailyAssignmentState, BatchContainerAssignment
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading
from apps.batch.models import GrowthSample, MortalityEvent
from apps.scenario.models import Scenario
from datetime import timedelta

def main():
    print('='*80)
    print('TEST DATA VERIFICATION REPORT')
    print('='*80)
    print()
    
    # === BATCH STATISTICS ===
    print('='*80)
    print('1. BATCH STATISTICS')
    print('='*80)
    print()
    
    total = Batch.objects.count()
    completed = Batch.objects.filter(status='COMPLETED').count()
    active = Batch.objects.filter(status='ACTIVE').count()
    planned = Batch.objects.filter(status='PLANNED').count()
    
    print(f'Total Batches: {total}')
    print(f'  Completed: {completed}')
    print(f'  Active: {active}')
    print(f'  Planned: {planned}')
    print()
    
    # Geography distribution
    geo_counts = {}
    for batch in Batch.objects.all():
        geo_code = batch.batch_number.split('-')[0]  # FI-2024-001 -> FI
        geo_counts[geo_code] = geo_counts.get(geo_code, 0) + 1
    
    for geo_code, count in sorted(geo_counts.items()):
        geo_name = 'Faroe Islands' if geo_code == 'FI' else 'Scotland' if geo_code == 'SCO' else geo_code
        print(f'  {geo_name}: {count} batches')
    print()
    
    # Stage distribution (active only)
    from apps.batch.models import LifeCycleStage
    print('Stage Distribution (Active Batches):')
    for stage in LifeCycleStage.objects.all().order_by('order'):
        count = Batch.objects.filter(lifecycle_stage=stage, status='ACTIVE').count()
        if count > 0:
            print(f'  {stage.name}: {count} batches')
    print()
    
    # === EVENT VOLUME ===
    print('='*80)
    print('2. EVENT VOLUME')
    print('='*80)
    print()
    
    env = EnvironmentalReading.objects.count()
    feeding = FeedingEvent.objects.count()
    growth = GrowthSample.objects.count()
    mortality = MortalityEvent.objects.count()
    scenarios = Scenario.objects.count()
    
    print(f'Environmental Readings: {env:,}')
    print(f'Feeding Events: {feeding:,}')
    print(f'Growth Samples: {growth:,}')
    print(f'Mortality Events: {mortality:,}')
    print(f'Scenarios: {scenarios:,}')
    print()
    
    # Expected vs Actual
    expected_ranges = {
        40: {
            'env': (7_000_000, 12_000_000),
            'feeding': (1_000_000, 3_000_000),
            'growth': (40_000, 80_000)
        },
        170: {
            'env': (35_000_000, 50_000_000),
            'feeding': (7_000_000, 10_000_000),
            'growth': (300_000, 500_000)
        }
    }
    
    # Find closest expected range
    if total >= 150:
        expected = expected_ranges[170]
        batch_type = '170-batch full saturation'
    elif total >= 30:
        expected = expected_ranges[40]
        batch_type = '40-batch medium test'
    else:
        expected = None
        batch_type = 'small test'
    
    if expected:
        print(f'Expected for {batch_type}:')
        print(f'  Environmental: {expected["env"][0]:,} - {expected["env"][1]:,}')
        print(f'  Feeding: {expected["feeding"][0]:,} - {expected["feeding"][1]:,}')
        print(f'  Growth: {expected["growth"][0]:,} - {expected["growth"][1]:,}')
        print()
        
        env_ok = expected['env'][0] <= env <= expected['env'][1]
        feed_ok = expected['feeding'][0] <= feeding <= expected['feeding'][1]
        growth_ok = expected['growth'][0] <= growth <= expected['growth'][1]
        
        print('Status:')
        print(f'  Environmental: {"✅ PASS" if env_ok else "❌ FAIL"}')
        print(f'  Feeding: {"✅ PASS" if feed_ok else "❌ FAIL"}')
        print(f'  Growth: {"✅ PASS" if growth_ok else "⚠️  WARN"}')
        print()
    
    # === GROWTH ENGINE FIX VERIFICATION (ISSUE #112) ===
    print('='*80)
    print('3. GROWTH ENGINE FIX (Issue #112)')
    print('='*80)
    print()
    print('Checking for population doubling at Day 91 transitions...')
    print()
    
    tested = 0
    passed = 0
    failed = []
    
    # Test batches old enough to have Day 91 data
    old_batches = Batch.objects.exclude(status='PLANNED').order_by('batch_number')
    
    for batch in old_batches[:20]:  # Test first 20
        day_91_states = ActualDailyAssignmentState.objects.filter(
            batch=batch,
            day_number=91
        )
        
        if day_91_states.exists():
            tested += 1
            total_pop = sum(s.population for s in day_91_states)
            
            if 2_800_000 <= total_pop <= 3_200_000:
                passed += 1
                status = '✅ PASS'
            elif total_pop > 5_000_000:
                status = '❌ DOUBLED'
                failed.append((batch.batch_number, total_pop))
            else:
                status = '⚠️  CHECK'
            
            print(f'  {batch.batch_number}: Day 91 = {total_pop:,} | {status}')
    
    print()
    if tested > 0:
        print(f'Results: {passed}/{tested} batches passed')
        if passed == tested:
            print(f'✅ ALL PASS - No population doubling detected')
        else:
            print(f'❌ FAILURES DETECTED:')
            for batch_num, pop in failed:
                print(f'  {batch_num}: {pop:,} fish (expected ~3M)')
    else:
        print('⚠️  No batches with Day 91 data yet')
        print('   (All batches < 91 days old or Growth Analysis not computed)')
    print()
    
    # === SAMPLE BATCH DETAIL ===
    print('='*80)
    print('4. SAMPLE BATCH ANALYSIS')
    print('='*80)
    print()
    
    if total > 0:
        # Find oldest batch (most complete)
        oldest = Batch.objects.filter(status__in=['ACTIVE', 'COMPLETED']).order_by('start_date').first()
        if oldest:
            print(f'Analyzing: {oldest.batch_number}')
            print(f'  Status: {oldest.status}')
            print(f'  Stage: {oldest.lifecycle_stage.name}')
            print(f'  Start: {oldest.start_date}')
            
            # Age
            from datetime import date
            age = (date.today() - oldest.start_date).days
            print(f'  Age: {age} days')
            print()
            
            # Events
            batch_feeding = FeedingEvent.objects.filter(batch=oldest).count()
            batch_env = EnvironmentalReading.objects.filter(batch=oldest).count()
            batch_growth = GrowthSample.objects.filter(assignment__batch=oldest).count()
            batch_mortality = MortalityEvent.objects.filter(batch=oldest).count()
            
            print(f'  Events:')
            print(f'    Environmental: {batch_env:,}')
            print(f'    Feeding: {batch_feeding:,}')
            print(f'    Growth: {batch_growth:,}')
            print(f'    Mortality: {batch_mortality:,}')
            print()
            
            # Current state
            active_assignments = BatchContainerAssignment.objects.filter(
                batch=oldest,
                is_active=True
            )
            total_pop = sum(a.population_count for a in active_assignments)
            avg_weight = sum(a.avg_weight_g for a in active_assignments) / len(active_assignments) if active_assignments.exists() else 0
            total_biomass = sum(a.biomass_kg for a in active_assignments)
            
            print(f'  Current State:')
            print(f'    Population: {total_pop:,} fish')
            print(f'    Avg Weight: {avg_weight:.1f}g')
            print(f'    Biomass: {total_biomass:,.1f}kg')
            print(f'    Containers: {active_assignments.count()}')
            print()
    
    # === CONTAINER UTILIZATION ===
    print('='*80)
    print('5. CONTAINER UTILIZATION')
    print('='*80)
    print()
    
    from apps.infrastructure.models import Container
    
    total_containers = Container.objects.filter(active=True).count()
    occupied = BatchContainerAssignment.objects.filter(
        is_active=True
    ).values('container').distinct().count()
    
    utilization = (occupied / total_containers * 100) if total_containers > 0 else 0
    
    print(f'Total Active Containers: {total_containers}')
    print(f'Containers in Use: {occupied}')
    print(f'Utilization: {utilization:.1f}%')
    print()
    
    if total >= 150:
        target = '80-85%'
    elif total >= 30:
        target = '30-40%'
    else:
        target = '<10%'
    
    print(f'Expected Utilization: {target}')
    print()
    
    # === SUMMARY ===
    print('='*80)
    print('VERIFICATION SUMMARY')
    print('='*80)
    print()
    
    checks_passed = []
    checks_failed = []
    
    # Check 1: Batch count
    if total >= 30:
        checks_passed.append('Batch count')
    else:
        checks_failed.append(f'Batch count ({total} < 30)')
    
    # Check 2: Event volume (if 40+ batches)
    if total >= 30:
        if expected:
            if env_ok:
                checks_passed.append('Environmental volume')
            else:
                checks_failed.append(f'Environmental volume ({env:,})')
            
            if feed_ok:
                checks_passed.append('Feeding volume')
            else:
                checks_failed.append(f'Feeding volume ({feeding:,})')
    
    # Check 3: Growth Engine fix
    if tested > 0 and passed == tested:
        checks_passed.append('Growth Engine fix (Issue #112)')
    elif tested > 0:
        checks_failed.append(f'Growth Engine fix ({passed}/{tested} passed)')
    
    # Check 4: Scenarios
    if scenarios > total * 0.5:  # At least 50% of batches have scenarios
        checks_passed.append(f'Scenarios ({scenarios} created)')
    elif scenarios > 0:
        checks_passed.append(f'Scenarios ({scenarios}, partial)')
    
    # Check 5: Container utilization
    if total >= 150 and 75 <= utilization <= 90:
        checks_passed.append(f'Container utilization ({utilization:.1f}%)')
    elif total >= 30 and 25 <= utilization <= 50:
        checks_passed.append(f'Container utilization ({utilization:.1f}%)')
    elif utilization > 0:
        checks_passed.append(f'Container utilization ({utilization:.1f}%, low volume test)')
    
    print('✅ PASSED:')
    for check in checks_passed:
        print(f'  - {check}')
    print()
    
    if checks_failed:
        print('❌ FAILED:')
        for check in checks_failed:
            print(f'  - {check}')
        print()
    
    # Final verdict
    print('='*80)
    if len(checks_failed) == 0:
        print('✅ ALL CHECKS PASSED - Test data quality verified!')
        print()
        if total < 150:
            print('💡 Next step: Scale to full saturation (85 batches per geography)')
            print('   SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \\')
            print('     --execute --batches 85 --workers 14')
        return 0
    else:
        print('⚠️  SOME CHECKS FAILED - Review output above')
        return 1

if __name__ == '__main__':
    sys.exit(main())

