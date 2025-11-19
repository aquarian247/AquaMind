# Incremental Test Plan - Event Engine Fixes

**Date**: November 18, 2025  
**Issue**: #112 - Test Data Population Doubling  
**Fixes Applied**:
1. ✅ Population doubling (lines 843, 913): `population_count=0`
2. ✅ Duration default (line 40): `650` → `900`
3. ✅ Single-area distribution (lines 852-920)
4. ✅ Initial scenario creation (line 432)

---

## Phase 1: Verify Single Batch (15 minutes)

### Step 1.1: Wipe Operational Data

```bash
cd /Users/aquarian247/Projects/AquaMind

# Wipe operational data (preserves infrastructure)
python scripts/data_generation/00_wipe_operational_data.py --confirm
# Type 'DELETE' when prompted
```

**Expected Output**:
```
✓ Deleted X Batches
✓ Deleted X Assignments
✓ Deleted X Feeding Events
...
✓ All checks passed! Database is clean and ready.
```

### Step 1.2: Generate Single Test Batch

```bash
# Generate 200-day batch (Egg&Alevin → Fry → Parr)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 \
  --eggs 3500000 \
  --geography "Faroe Islands" \
  --duration 200
```

**Expected Output**:
```
✓ Created scenario: Planned Growth - FI-2025-001
  Initial: 3,500,000 eggs @ 0.1g
  Duration: 900 days (full lifecycle)
  
→ Stage Transition: Egg&Alevin → Fry
  → Moved to FI-FW-01-Hall-B (10 containers)
  ✓ Transfer workflow: TRF-2025-001 (10 actions)
  
→ Stage Transition: Fry → Parr
  → Moved to FI-FW-01-Hall-C (10 containers)
  ✓ Transfer workflow: TRF-2025-002 (10 actions)

Complete!
Feeding: 1,800+ (should be >1,000) ✅
Scenarios: 1 (should be ≥1) ✅
Transfer Workflows: 2 ✅
```

### Step 1.3: Verify Population Fix

```bash
python manage.py shell -c "
from apps.batch.models import Batch, BatchContainerAssignment
from apps.batch.services.growth_assimilation import ActualDailyAssignmentState
from datetime import timedelta

batch = Batch.objects.latest('created_at')
print(f'Batch: {batch.batch_number}')
print()

# Check Day 90 transition (Egg&Alevin → Fry)
day_90 = batch.start_date + timedelta(days=90)
arriving = BatchContainerAssignment.objects.filter(
    batch=batch,
    assignment_date=day_90
)

print('Day 90 Transfer (Egg&Alevin → Fry):')
print(f'  Arriving assignments: {arriving.count()}')

if arriving.exists():
    sample = arriving.first()
    print(f'  Sample assignment metadata: {sample.population_count:,}')
    print(f'  Expected: 0 (fixed!)' if sample.population_count == 0 else f'  ❌ STILL HAS PRE-POPULATED COUNT!')
    
print()
print('✅ PASS: population_count = 0' if arriving.exists() and arriving.first().population_count == 0 else '❌ FAIL: Fix not working')
"
```

**Expected Output**:
```
Batch: FI-2025-001

Day 90 Transfer (Egg&Alevin → Fry):
  Arriving assignments: 10
  Sample assignment metadata: 0
  Expected: 0 (fixed!)

✅ PASS: population_count = 0
```

### Step 1.4: Verify Scenario Creation

```bash
python manage.py shell -c "
from apps.batch.models import Batch
from apps.scenario.models import Scenario

batch = Batch.objects.latest('created_at')
scenarios = Scenario.objects.filter(batch=batch)

print(f'Batch: {batch.batch_number}')
print(f'Scenarios: {scenarios.count()}')

if scenarios.exists():
    for s in scenarios:
        print(f'  - {s.name}')
        print(f'    Duration: {s.duration_days} days')
        print(f'    Initial: {s.initial_count:,} @ {s.initial_weight}g')
    print()
    print('✅ PASS: Batch has scenario for growth analysis')
else:
    print('❌ FAIL: No scenarios found')
"
```

**Expected Output**:
```
Batch: FI-2025-001
Scenarios: 1
  - Planned Growth - FI-2025-001
    Duration: 900 days
    Initial: 3,500,000 @ 0.1g

✅ PASS: Batch has scenario for growth analysis
```

### Step 1.5: Verify Single-Area Distribution

```bash
python manage.py shell -c "
from apps.batch.models import Batch

batch = Batch.objects.latest('created_at')

# Get sea assignments (should be in single area)
sea_assignments = batch.batch_assignments.filter(
    lifecycle_stage__name='Adult'
)

if sea_assignments.exists():
    areas = set(a.container.area.name for a in sea_assignments)
    print(f'Adult stage assignments:')
    print(f'  Containers: {sea_assignments.count()}')
    print(f'  Areas: {len(areas)}')
    for area in sorted(areas):
        count = sea_assignments.filter(container__area__name=area).count()
        print(f'    - {area}: {count} containers')
    print()
    print('✅ PASS: Single area distribution' if len(areas) == 1 else f'⚠️  WARNING: Batch spans {len(areas)} areas')
else:
    print('○ No Adult stage yet (batch too young)')
"
```

---

## Phase 2: Parallel Execution Test (45-60 minutes)

### Step 2.1: Dry Run Parallel Orchestrator

```bash
# See what would be generated
python scripts/data_generation/04_batch_orchestrator_parallel.py --batches 10
```

**Expected Output**:
```
INFRASTRUCTURE CAPACITY ANALYSIS
================================
Faroe Islands:
  Freshwater Containers: 900
  Sea Containers: 460
  Total: 1360

Scotland:
  Freshwater Containers: 750
  Sea Containers: 400
  Total: 1150

TOTAL INFRASTRUCTURE: 2510 containers

GENERATING BATCH SCHEDULE (10 per geography)
============================================
Strategy: 30-day stagger creates completed + active batches
Start: 2024-XX-XX (X years ago)
Today: 2025-11-18
Stagger: Every 30 days

...

Total Batches Scheduled: 20
Active: 15 | Completed: 5

To execute with parallel processing:
  python scripts/data_generation/04_batch_orchestrator_parallel.py \
    --execute --batches 10 --workers 14
```

### Step 2.2: Execute Parallel Generation (Small Test)

```bash
# Generate 4 batches (2 per geography) - 5 minutes
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 2 --workers 4
```

**Monitor Progress**:
```bash
# In another terminal, watch batch creation
watch -n 10 'python manage.py shell -c "
from apps.batch.models import Batch
print(f\"Batches: {Batch.objects.count()}/4\")
print(f\"Latest: {Batch.objects.latest(\"created_at\").batch_number if Batch.objects.exists() else \"None\"}\")
"'
```

### Step 2.3: Verify Parallel Results

```bash
python manage.py shell -c "
from apps.batch.models import Batch, BatchContainerAssignment
from apps.scenario.models import Scenario

print('='*80)
print('PARALLEL EXECUTION VERIFICATION')
print('='*80)

batches = Batch.objects.all()
print(f'\nTotal Batches: {batches.count()}')

for batch in batches:
    # Check scenarios
    scenarios = Scenario.objects.filter(batch=batch).count()
    
    # Check sea area distribution
    adult_assignments = batch.batch_assignments.filter(lifecycle_stage__name='Adult')
    areas = set(a.container.area.name for a in adult_assignments) if adult_assignments.exists() else set()
    
    print(f'\n{batch.batch_number}:')
    print(f'  Stage: {batch.lifecycle_stage.name}')
    print(f'  Scenarios: {scenarios} {\"✅\" if scenarios > 0 else \"❌\"}')
    print(f'  Sea areas: {len(areas)} {\"✅\" if len(areas) <= 1 else \"⚠️ \"}')

print()
print('✅ All batches verified' if all(
    Scenario.objects.filter(batch=b).exists() for b in batches
) else '❌ Some batches missing scenarios')
"
```

---

## Phase 3: Full Parallel Generation (45-60 minutes)

### Step 3.1: Wipe and Generate 20 Batches

```bash
cd /Users/aquarian247/Projects/AquaMind

# Wipe operational data
python scripts/data_generation/00_wipe_operational_data.py --confirm
# Type 'DELETE'

# Generate 20 batches in parallel (10 per geography)
time python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 14
```

**Expected Timeline**:
```
Start:     00:00
Workers:   14 parallel processes
Progress:  Every ~3-4 minutes a batch completes
Complete:  ~45-60 minutes
Speedup:   ~10-12x vs sequential (8-10 hours)
```

### Step 3.2: Verify Full Dataset

```bash
python manage.py shell -c "
from apps.batch.models import Batch, BatchContainerAssignment
from apps.scenario.models import Scenario
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading

print('='*80)
print('FULL DATASET VERIFICATION')
print('='*80)

# Batch counts
total_batches = Batch.objects.count()
active_batches = Batch.objects.filter(status='ACTIVE').count()

print(f'\nBatches:')
print(f'  Total: {total_batches} (expected: 20)')
print(f'  Active: {active_batches}')

# Stage distribution
from apps.batch.models import LifeCycleStage
for stage in LifeCycleStage.objects.order_by('order'):
    count = Batch.objects.filter(lifecycle_stage=stage).count()
    print(f'  {stage.name}: {count} batches')

# Scenario verification
batches_with_scenarios = Batch.objects.filter(scenario__isnull=False).distinct().count()
print(f'\nScenarios:')
print(f'  Batches with scenarios: {batches_with_scenarios}/{total_batches}')
print(f'  Total scenarios: {Scenario.objects.count()}')

# Event counts
print(f'\nEvents:')
print(f'  Feeding: {FeedingEvent.objects.count():,}')
print(f'  Environmental: {EnvironmentalReading.objects.count():,}')
print(f'  Assignments: {BatchContainerAssignment.objects.count():,}')

# Single-area verification
multi_area_batches = 0
for batch in Batch.objects.filter(lifecycle_stage__name='Adult'):
    adult_assignments = batch.batch_assignments.filter(lifecycle_stage__name='Adult')
    areas = set(a.container.area.name for a in adult_assignments)
    if len(areas) > 1:
        multi_area_batches += 1
        print(f'  ⚠️  {batch.batch_number} spans {len(areas)} areas: {areas}')

print(f'\nSingle-Area Distribution:')
print(f'  Adult batches with multi-area: {multi_area_batches}')
print(f'  Expected: 0 (all batches in single area)')

print()
print('✅ FULL DATASET VERIFIED' if batches_with_scenarios == total_batches and multi_area_batches == 0 else '⚠️  REVIEW ISSUES ABOVE')
"
```

---

## Phase 4: Growth Analysis UI Test

### Step 4.1: Recompute Growth Analysis

```bash
python manage.py shell -c "
from apps.batch.models import Batch
from apps.batch.services.growth_assimilation import GrowthAssimilationService

# Pick a batch in Parr or later stage (Day 180+)
batch = Batch.objects.filter(
    lifecycle_stage__order__gte=3  # Parr or later
).first()

if not batch:
    print('No batches in Parr+ stage yet')
else:
    print(f'Recomputing: {batch.batch_number}')
    print(f'Stage: {batch.lifecycle_stage.name}')
    
    # Recompute growth analysis
    service = GrowthAssimilationService()
    result = service.recompute_batch_daily_states(batch.id)
    
    print(f'✓ Recomputed {result[\"states_created\"]} states')
"
```

### Step 4.2: Test Growth Analysis API

```bash
# Get API token
TOKEN=$(python manage.py shell -c "
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
token, _ = Token.objects.get_or_create(user=user)
print(token.key)
")

# Get batch with scenario
BATCH_ID=$(python manage.py shell -c "
from apps.batch.models import Batch
from apps.scenario.models import Scenario
batch = Batch.objects.filter(scenario__isnull=False).first()
print(batch.id if batch else '')
")

# Test combined growth data API
curl -s "http://localhost:8000/api/v1/batch/batches/${BATCH_ID}/combined-growth-data/" \
  -H "Authorization: Token ${TOKEN}" \
  | python -m json.tool | head -50
```

**Expected JSON**:
```json
{
  "batch_id": 1,
  "batch_number": "FI-2025-001",
  "scenario": {
    "id": 1,
    "name": "Planned Growth - FI-2025-001",
    ...
  },
  "growth_samples": [...],
  "scenario_projection": [...],
  "actual_daily_states": [...],
  ...
}
```

### Step 4.3: Verify Population Fix in UI

```bash
# Check Day 91 population
python manage.py shell -c "
from apps.batch.models import Batch
from apps.batch.services.growth_assimilation import ActualDailyAssignmentState

batch = Batch.objects.latest('created_at')

# Day 91 (first full Fry day)
day_91_states = ActualDailyAssignmentState.objects.filter(
    batch=batch,
    day_number=91
)

if day_91_states.exists():
    total_pop = sum(s.population for s in day_91_states)
    print(f'Day 91 Population: {total_pop:,}')
    print(f'Expected: ~3,000,000 (not ~6,000,000)')
    print(f'Ratio: {total_pop / 3000000:.2f}x')
    print()
    
    if 2800000 < total_pop < 3200000:
        print('✅ PASS: Population doubling FIXED!')
    else:
        print(f'❌ FAIL: Population still wrong ({total_pop:,})')
else:
    print('○ No Day 91 states yet (batch too young)')
"
```

**Success Criteria**:
- ✅ Day 91 population: 2.8M - 3.2M (not ~6M)
- ✅ Batch has scenario
- ✅ Feeding events > 1,000
- ✅ Transfer workflows created

---

## Phase 5: Performance Benchmarking

### Sequential vs Parallel Comparison

**Sequential** (for reference - don't run):
```bash
# Would take: 20 batches × 25 min = 500 minutes (8.3 hours)
```

**Parallel** (actual):
```bash
time python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 14
```

**Expected Performance**:
```
Workers: 14
Batches: 20
Time: 45-60 minutes
Speedup: 10-12x
CPU Usage: 70-85% across all cores
```

---

## Troubleshooting

### Issue: "Insufficient available containers"

**Cause**: Infrastructure saturated from previous run

**Fix**:
```bash
python scripts/data_generation/00_wipe_operational_data.py --confirm
```

### Issue: Batch still has multi-area distribution

**Cause**: Round-robin not working or areas exhausted

**Check**:
```bash
python manage.py shell -c "
from apps.infrastructure.models import Area
from apps.batch.models import Batch, BatchContainerAssignment

batch = Batch.objects.filter(lifecycle_stage__name='Adult').first()
if batch:
    assignments = batch.batch_assignments.filter(lifecycle_stage__name='Adult')
    for a in assignments[:3]:
        print(f'{a.container.name} → Area: {a.container.area.name}')
"
```

### Issue: Population still doubled after fix

**Cause**: Old batch data OR fix not applied

**Check**:
```bash
# Verify fix applied
grep "population_count=0" /Users/aquarian247/Projects/AquaMind/scripts/data_generation/03_event_engine_core.py

# Should show TWO lines (freshwater + sea)
```

**Fix**: Wipe and regenerate

### Issue: Parallel workers crash or hang

**Cause**: Database connection exhaustion or memory pressure

**Check**:
```bash
# Check DB connections
psql -d aquamind_db -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check memory
top -l 1 | grep PhysMem
```

**Fix**: Reduce workers
```bash
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 8  # More conservative
```

---

## Success Criteria Summary

### After Single Batch Test:
- [ ] Population doubling fixed (Day 91 ≈ 3M, not 6M)
- [ ] Scenario created and linked to batch
- [ ] Single area distribution (Adult stage)
- [ ] Feeding events > 1,000
- [ ] Transfer workflows created

### After Parallel Test:
- [ ] All batches generated successfully
- [ ] All batches have scenarios
- [ ] All Adult batches in single area
- [ ] Time < 60 minutes for 20 batches
- [ ] No container conflicts or errors

### After UI Test:
- [ ] Growth Analysis page loads
- [ ] Three series visible (Samples, Scenario, Actual)
- [ ] No population spikes at transfer days
- [ ] Realistic FCR values (0.9-3.0)
- [ ] Variance analysis shows meaningful data

---

## Next Steps After Verification

1. **Update test data guide** with new scripts
2. **Document parallel orchestrator** in README
3. **Add performance benchmarks** to documentation
4. **Create CI/CD integration** for test data regeneration
5. **Add automated quality checks** (population ranges, FCR values, etc.)

---

**End of Incremental Test Plan**

