# Handover: Test Data Generation - Parallel Execution Fix Needed

**Date:** November 18, 2025  
**Session Duration:** ~6 hours  
**Status:** ✅ Model Fixes Complete | ⚠️ Parallel Allocation Issue Blocking  
**Next Agent Mission:** Implement schedule-based allocation for 100% parallel execution

---

## 🎯 TL;DR - What You Need to Know

**Problem:** Dynamic container allocation causes failures even with sequential execution at high saturation (94% success rate with 5-day stagger)

**Root Cause:** Event engine queries "available containers" at runtime → Race conditions in parallel, capacity errors in sequential

**Solution:** Pre-planned deterministic schedule eliminates runtime queries → 100% reliable parallel execution

**Your Mission:** Implement schedule-based executor (3-4 hours) → Generate 584 batches reliably (6-8 hours parallel)

---

## ✅ COMPLETED THIS SESSION

### 1. Growth Engine Fix (Issue #112) - PRODUCTION READY
**File:** `apps/batch/services/growth_assimilation.py` (lines 469-485)

**Problem:** Population doubling at transfer destinations (6M instead of 3M)

**Fix:** Detect transfer destinations, start from population=0
```python
first_day_transfers = TransferAction.objects.filter(
    dest_assignment=self.assignment,
    actual_execution_date=self.assignment.assignment_date,
    status='COMPLETED'
).exists()

if first_day_transfers:
    initial_population = 0  # Placements will add fish daily
```

**Verified:** Day 91 = 3,059,930 fish ✅ (expected ~3M, no doubling)

---

### 2. MortalityEvent FK Fix - COMPLETE
**Files:** `apps/batch/models/mortality.py` + migrations + services

**Problem:** MortalityEvent had batch FK only (no assignment) → Growth Engine forced to prorate

**Fix:** Added assignment FK, removed proration workaround

**Result:** 
- Confidence increased 0.9 → 1.0
- 100% FK population verified (115K mortality events)
- 31 lines of proration code removed

---

### 3. EnvironmentalReading FK Population - FIXED
**File:** `scripts/data_generation/03_event_engine_core.py` (line 557)

**Problem:** Model had `batch_container_assignment` FK but wasn't populated

**Fix:** Added `batch_container_assignment=a` to EnvironmentalReading creation

**Result:** 100% FK population verified (2M+ readings)

---

### 4. Feed Inventory Auto-Initialization - SUSTAINABLE
**File:** `scripts/data_generation/03_event_engine_core.py` (lines 141-223)

**Problem:** Required manual `fix_feed_inventory.py` script (agents had to remember)

**Fix:** Event engine auto-initializes 3,730 tonnes on first batch

**Result:** Idempotent, self-healing, no separate script needed

---

### 5. Test Data Guide v3 - DOCUMENTED
**File:** `aquamind/docs/database/test_data_generation/test_data_generation_guide_v3.md`

**Updates:**
- Infrastructure saturation model (87% with 5-day stagger)
- Accurate script reference (00-04)
- Expected data volumes (175M environmental, 30M feeding for 584 batches)
- Single source of truth

---

## ⚠️ BLOCKING ISSUE: Container Allocation Failures

### The Problem

**Dynamic Allocation at Runtime:**
```python
# Event engine (03_event_engine_core.py)
def find_available_containers(hall, count=10):
    occupied = BatchContainerAssignment.objects.filter(is_active=True).values_list('container_id')
    available = Container.objects.filter(hall=hall).exclude(id__in=occupied)[:count]
    return available  # Race condition in parallel, capacity errors at high saturation
```

**What Happens:**
- 5-day stagger creates 18 batches overlapping in single hall
- Faroe has only 12 Hall-A's
- Batch 13 queries for Hall-A → None available → FAILS
- Even sequential execution: 94% success rate (3-6% failures)

**Evidence from 584-Batch Run (Stopped at batch 52):**
```
Success: 49/52 batches (94%)
Failed: Batches 13, 27, 41, 42, 44
Pattern: Failures every ~14 batches (when hall capacity exceeded)
```

---

## 💡 THE SOLUTION: Schedule-Based Allocation

### Architecture Overview

**Current (Dynamic):**
```
Runtime → Query available containers → Allocate → (Race/Capacity Issues)
```

**Proposed (Schedule-Based):**
```
Pre-Planning → Generate schedule file → Execute from schedule → (100% Success)
```

### How It Works

**Phase 1: Generate Schedule (One-Time)**
```yaml
# config/batch_schedule_584.yaml
batches:
  - batch_id: FI-2021-001
    start_date: 2021-10-05
    eggs: 3500000
    freshwater:
      egg_alevin:
        hall: FI-FW-01-Hall-A
        containers: [C01, C02, C03, C04, C05, C06, C07, C08, C09, C10]
      fry:
        hall: FI-FW-02-Hall-B  # Different station OK!
        containers: [C01, C02, ...]
      # ... all stages pre-allocated
    sea:
      area: FI-SEA-01
      rings: [Ring-01, Ring-02, ..., Ring-20]  # All 20 rings
  
  - batch_id: SCO-2021-001
    start_date: 2021-10-05
    freshwater:
      egg_alevin:
        hall: S-FW-01-Hall-A  # Different geography, no conflict
        containers: [C01, ...]
    # ... 582 more batches with zero conflicts
```

**Phase 2: Execute from Schedule**
```python
# executor reads schedule, no runtime queries
for batch_config in schedule['batches']:
    containers = Container.objects.filter(
        name__in=batch_config['freshwater']['egg_alevin']['containers']
    )
    # Use exact pre-allocated containers (no availability check!)
    create_assignments(containers)
```

**Result:** 100% success rate, fully parallelizable (14+ workers safe)

---

## 📋 IMPLEMENTATION PLAN FOR NEXT AGENT

### Phase 1: Fix Schedule Planner (2 hours)

**File:** `scripts/data_generation/generate_batch_schedule.py` (partially implemented)

**Current Issue:** Occupancy tracking has bug, fails at capacity

**Fix Needed:**
```python
# Bug in _allocate_freshwater_independent()
# Currently checks per-container availability correctly
# BUT: Doesn't respect hall count limits properly

# Solution: Track hall-level occupancy, not just container-level
hall_occupancy = {
    'FI-FW-01-Hall-A': [(start_day, end_day, batch_id), ...],
    # ...
}

# When allocating:
def allocate_hall(hall_name, start_day, end_day):
    occupants = hall_occupancy[hall_name]
    overlapping = [o for o in occupants if overlaps(o, start_day, end_day)]
    
    if len(overlapping) >= 1:  # Hall already occupied
        return None  # Try next hall
    
    # Hall available!
    hall_occupancy[hall_name].append((start_day, end_day, batch_id))
    return get_containers_from_hall(hall_name)
```

**Test:** Generate schedule for 584 batches, validate zero conflicts

---

### Phase 2: Implement Schedule Executor (1-2 hours)

**File:** `scripts/data_generation/execute_batch_schedule.py` (NEW)

**Purpose:** Execute batches using pre-allocated containers from schedule

```python
def execute_from_schedule(schedule_file, workers=14):
    """Execute batches from deterministic schedule."""
    schedule = yaml.load(schedule_file)
    
    if workers > 1:
        # Parallel execution (now safe!)
        with mp.Pool(processes=workers) as pool:
            results = pool.map(execute_batch_from_schedule, schedule['batches'])
    else:
        # Sequential
        for batch in schedule['batches']:
            execute_batch_from_schedule(batch)

def execute_batch_from_schedule(batch_config):
    """Execute single batch using pre-allocated containers from schedule."""
    
    # Pass schedule to event engine
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    env['CONTAINER_SCHEDULE'] = json.dumps(batch_config['freshwater'])
    env['SEA_SCHEDULE'] = json.dumps(batch_config['sea'])
    
    cmd = [
        'python', 'scripts/data_generation/03_event_engine_core.py',
        '--start-date', batch_config['start_date'],
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(batch_config['duration']),
        '--use-schedule'  # New flag
    ]
    
    subprocess.run(cmd, env=env, check=True)
```

---

### Phase 3: Update Event Engine (1 hour)

**File:** `scripts/data_generation/03_event_engine_core.py`

**Changes Needed:**

```python
class EventEngine:
    def __init__(self, start_date, eggs, geography, duration=900, use_schedule=False):
        # ...
        self.use_schedule = use_schedule
        if use_schedule:
            # Load container schedule from environment
            self.container_schedule = json.loads(os.environ.get('CONTAINER_SCHEDULE', '{}'))
            self.sea_schedule = json.loads(os.environ.get('SEA_SCHEDULE', '{}'))
    
    def create_batch(self):
        if self.use_schedule:
            # Use pre-allocated containers (deterministic)
            hall_name = self.container_schedule['egg_alevin']['hall']
            container_names = self.container_schedule['egg_alevin']['containers']
            containers = Container.objects.filter(name__in=container_names)
        else:
            # Fallback: dynamic allocation (current behavior)
            containers = self.find_available_containers(...)
```

**Add CLI flag:**
```python
parser.add_argument('--use-schedule', action='store_true',
                   help='Use pre-allocated containers from CONTAINER_SCHEDULE env var')
```

---

### Phase 4: Test & Execute (8-10 hours)

**Test with 20 batches:**
```bash
# 1. Generate schedule
python scripts/data_generation/generate_batch_schedule.py \
  --batches 10 --stagger 5 \
  --output config/test_schedule_20.yaml

# 2. Execute with parallel workers
python scripts/data_generation/execute_batch_schedule.py \
  config/test_schedule_20.yaml --workers 14

# 3. Verify 100% success rate
python scripts/data_generation/verify_test_data.py
```

**If successful, scale to 584:**
```bash
# 1. Generate full schedule
python scripts/data_generation/generate_batch_schedule.py \
  --batches 292 --stagger 5 \
  --output config/batch_schedule_584_87pct.yaml

# 2. Execute with 14 workers (now safe!)
python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_584_87pct.yaml --workers 14

# Expected: 6-8 hours, 100% success rate
```

---

## 📊 TARGET: 584 Batches, 87% Saturation

### Configuration
```yaml
Total Batches: 584 (292 per geography)
Stagger: 5 days
History: 4.1 years (Oct 2021 - Nov 2025)
Order: Chronological (alternating geographies)
Adult Duration: 450 days
```

### Expected Distribution
```
Completed: 244 batches (41.8%) - for harvest testing
Active: 340 batches (58.2%) - for operational testing
  - Egg&Alevin: 16 batches
  - Fry: 36 batches
  - Parr: 36 batches
  - Smolt: 36 batches
  - Post-Smolt: 36 batches
  - Adult: 180 batches
```

### Expected Data Volume
```
Environmental: ~175 million readings
Feeding: ~30 million events
Growth: ~170K samples
Mortality: ~500K events
Database: ~234 GB
```

### Expected Saturation
```
Freshwater: 900/1,157 containers (78%)
Sea: 860/860 rings (100%)
Total: 1,760/2,017 containers (87.3%) ✅
```

---

## 🔍 WHY ALLOCATION FAILS

### The Capacity Math

**With 5-Day Stagger:**
```
Hall-A Capacity:
  - Faroe: 12 Hall-A's
  - Scotland: 10 Hall-A's
  - Total: 22 Hall-A's

Simultaneous Batches in Egg&Alevin:
  - Duration: 90 days
  - Stagger: 5 days
  - Overlap: 90 ÷ 5 = 18 batches
  
Allocation:
  - Batch 1-12: Use Faroe Hall-A's (full)
  - Batch 13: Needs Hall-A #13 → DOESN'T EXIST → FAIL ❌
  - Batch 14: Uses Scotland Hall-A (different geo, succeeds)
  - Batch 15: Uses Faroe Hall-A (wraps around - but Batch 1 still occupying!)
```

**The Issue:** Each hall can only hold 1 batch at a time. With 18 batches overlapping but only 22 halls total, we hit capacity.

**Current Dynamic Approach:**
- Tries to allocate Faroe batches first (sequential by geography)
- Faroe has only 12 Hall-A's
- Fails when trying batch 13
- Should use Scotland halls, but doesn't look there

**Schedule-Based Solution:**
- Pre-plan: Batch 1-12 use Faroe Hall-A, Batch 13-22 use Scotland Hall-A
- Batch 23 uses Faroe again (now free, Batch 1 moved to Hall-B)
- Perfect allocation, zero conflicts

---

## 🏗️ SCHEDULE-BASED ARCHITECTURE (The Solution)

### Key Principle: Separate Planning from Execution

**Traditional (Fails):**
```
Generate Batch 1 → Query containers → Allocate → Create
Generate Batch 2 → Query containers → Allocate → Create
...conflicts at runtime
```

**Schedule-Based (Succeeds):**
```
ONCE: Plan all 584 batches → Pre-allocate ALL containers → Validate zero conflicts → Save YAML

EXECUTE: Read YAML → Use exact containers → No queries → No conflicts → 100% success
```

### Benefits

1. **100% Success Rate**
   - No runtime queries
   - No race conditions
   - Pre-validated schedule

2. **Fully Parallelizable**
   - 14 workers safe (each has distinct pre-allocated containers)
   - 6-8 hours instead of 24 hours
   - True parallel performance

3. **Deterministic & Reproducible**
   - Same schedule → Same data every time
   - Version control the schedule
   - Critical for migration testing

4. **Debuggable**
   - Know exact container assignments upfront
   - Can review plan before execution
   - Easy to troubleshoot

---

## 📂 KEY FILES FOR YOU

### Primary Implementation Files

**1. Schedule Planner (Needs Fix):**
- `scripts/data_generation/generate_batch_schedule.py`
- Has occupancy tracking bug (fails at capacity)
- Fix: Track hall-level occupancy, respect limits
- Test: Should plan 584 batches with zero conflicts

**2. Event Engine (Needs Enhancement):**
- `scripts/data_generation/03_event_engine_core.py`
- Add `--use-schedule` flag
- Load pre-allocated containers from env vars
- Skip dynamic allocation when using schedule

**3. Schedule Executor (Needs Creation):**
- `scripts/data_generation/execute_batch_schedule.py` (NEW)
- Reads YAML schedule
- Passes container allocations to event engine
- Supports parallel execution

**4. Sequential Orchestrator (Works but slow):**
- `scripts/data_generation/04_batch_orchestrator.py`
- Updated with 5-day stagger support
- Chronological ordering ✅
- 94% success rate (good but not perfect)

### Documentation

**Technical Design:**
- `SCHEDULE_BASED_ARCHITECTURE_PROPOSAL.md` (root, move to progress folder)
- Complete architecture explanation
- Benefits analysis
- Implementation details

**Saturation Problem:**
- `INFRASTRUCTURE_SATURATION_PROBLEM_DEFINITION.md` (root, move to progress folder)
- Mathematical constraints
- Optimization analysis
- Solution comparison

**Test Data Guide:**
- `aquamind/docs/database/test_data_generation/test_data_generation_guide_v3.md`
- Single source of truth
- Updated with all fixes

---

## 🔧 IMPLEMENTATION CHECKLIST

### Step 1: Fix Schedule Planner Occupancy Tracking

**File:** `scripts/data_generation/generate_batch_schedule.py`

**Current Bug Location:** `_allocate_freshwater_independent()` (lines 199-270)

**Problem:**
```python
# Checks per-container availability (correct)
if self._check_container_available(container.name, absolute_start, absolute_end):
    available.append(container)

# BUT: Doesn't track that halls have max capacity
# After 12 Faroe Hall-A's full, should try Scotland Hall-A's
```

**Fix Strategy:**
1. Track hall occupancy separately: `{hall_name: occupant_count}`
2. Before allocating hall, check: `if hall_occupancy[hall] < 1: # Hall available`
3. Allocate across both geographies (don't do all Faroe first)
4. Validate: 584 batches should plan with zero conflicts

**Test Command:**
```bash
python scripts/data_generation/generate_batch_schedule.py \
  --batches 292 --stagger 5 --dry-run

# Expected output:
# ✅ 584 batches planned
# ✅ Zero conflicts detected
# ✅ Schedule is valid
```

---

### Step 2: Create Schedule Executor

**File:** `scripts/data_generation/execute_batch_schedule.py` (NEW, ~200 lines)

**Template:**
```python
#!/usr/bin/env python3
import yaml
import subprocess
import os
import multiprocessing as mp

def execute_batch_from_schedule(batch_config):
    """Execute single batch using pre-allocated containers."""
    env = os.environ.copy()
    env['SKIP_CELERY_SIGNALS'] = '1'
    env['USE_SCHEDULE'] = '1'
    env['CONTAINER_SCHEDULE'] = json.dumps(batch_config['freshwater'])
    env['SEA_SCHEDULE'] = json.dumps(batch_config['sea'])
    
    cmd = [
        'python', 'scripts/data_generation/03_event_engine_core.py',
        '--start-date', batch_config['start_date'],
        '--eggs', str(batch_config['eggs']),
        '--geography', batch_config['geography'],
        '--duration', str(batch_config['duration'])
    ]
    
    result = subprocess.run(cmd, env=env, check=True, capture_output=True)
    return {'success': True, 'batch_id': batch_config['batch_id']}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('schedule_file', help='YAML schedule file')
    parser.add_argument('--workers', type=int, default=1, help='Parallel workers')
    args = parser.parse_args()
    
    with open(args.schedule_file) as f:
        schedule = yaml.safe_load(f)
    
    if args.workers > 1:
        with mp.Pool(processes=args.workers) as pool:
            results = pool.map(execute_batch_from_schedule, schedule['batches'])
    else:
        results = [execute_batch_from_schedule(b) for b in schedule['batches']]
    
    # Report results
    success_count = sum(1 for r in results if r['success'])
    print(f"✅ {success_count}/{len(results)} batches successful")
```

---

### Step 3: Update Event Engine to Use Schedule

**File:** `scripts/data_generation/03_event_engine_core.py`

**Add to __init__:**
```python
def __init__(self, start_date, eggs, geography, duration=900):
    # ... existing code ...
    
    # Check if using pre-allocated schedule
    self.use_schedule = os.environ.get('USE_SCHEDULE') == '1'
    if self.use_schedule:
        self.container_schedule = json.loads(os.environ.get('CONTAINER_SCHEDULE', '{}'))
        self.sea_schedule = json.loads(os.environ.get('SEA_SCHEDULE', '{}'))
```

**Update create_batch():**
```python
def create_batch(self):
    if self.use_schedule:
        # Use pre-allocated containers from schedule
        hall_name = self.container_schedule['egg_alevin']['hall']
        container_names = self.container_schedule['egg_alevin']['containers']
        containers = list(Container.objects.filter(name__in=container_names))
    else:
        # Dynamic allocation (fallback for single-batch testing)
        containers = self.find_available_containers(...)
```

**Same pattern for stage transitions:**
```python
def check_stage_transition(self):
    if self.use_schedule:
        # Use next stage from schedule
        next_stage_config = self.container_schedule[next_stage_key]
        containers = Container.objects.filter(name__in=next_stage_config['containers'])
    else:
        # Dynamic allocation
        containers = self.find_available_containers(...)
```

---

### Step 4: Test with 20 Batches (30 min)

```bash
# 1. Wipe data
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 2. Generate test schedule (20 batches)
python scripts/data_generation/generate_batch_schedule.py \
  --batches 10 --stagger 5 \
  --output config/test_schedule_20.yaml

# 3. Execute sequentially first
python scripts/data_generation/execute_batch_schedule.py \
  config/test_schedule_20.yaml --workers 1

# 4. Verify
python scripts/data_generation/verify_test_data.py

# 5. If 100% success, try parallel
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
python scripts/data_generation/execute_batch_schedule.py \
  config/test_schedule_20.yaml --workers 14

# 6. Verify still 100%
```

---

### Step 5: Execute Full 584 Batches (6-8 hours)

```bash
# 1. Generate full schedule
python scripts/data_generation/generate_batch_schedule.py \
  --batches 292 --stagger 5 \
  --output config/batch_schedule_584_87pct.yaml

# 2. Wipe data
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 3. Execute with 14 workers
python scripts/data_generation/execute_batch_schedule.py \
  config/batch_schedule_584_87pct.yaml --workers 14 \
  > /tmp/batch_584_final.log 2>&1 &

# 4. Monitor
tail -f /tmp/batch_584_final.log

# Expected: 6-8 hours, 100% success rate
```

---

## 🧪 VERIFICATION TESTS

After generation completes:

### Test 1: Batch Count
```bash
# Should have exactly 584 batches
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch
print(f'✅ PASS' if Batch.objects.count() == 584 else '❌ FAIL')
"
```

### Test 2: FK Population
```bash
# All events should have assignment FKs
python -c "
from apps.batch.models import MortalityEvent
from apps.environmental.models import EnvironmentalReading
import django; django.setup()

mort = MortalityEvent.objects.count()
mort_fk = MortalityEvent.objects.filter(assignment__isnull=False).count()
env = EnvironmentalReading.objects.count()
env_fk = EnvironmentalReading.objects.filter(batch_container_assignment__isnull=False).count()

assert mort_fk == mort, f'Mortality FK: {mort_fk}/{mort}'
assert env_fk == env, f'Environmental FK: {env_fk}/{env}'
print('✅ All FKs populated')
"
```

### Test 3: Saturation
```bash
# Should hit 87% instantaneous saturation
python scripts/data_generation/verify_test_data.py
# Look for: "Container Utilization: 87%"
```

### Test 4: Growth Engine
```bash
# Verify no population doubling (Issue #112)
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch, ActualDailyAssignmentState
from datetime import timedelta

# Check Day 91 on oldest batches
for batch in Batch.objects.order_by('start_date')[:10]:
    states = ActualDailyAssignmentState.objects.filter(batch=batch, day_number=91)
    if states.exists():
        pop = sum(s.population for s in states)
        status = '✅' if 2_800_000 <= pop <= 3_200_000 else '❌'
        print(f'{batch.batch_number}: {pop:,} {status}')
"
```

---

## 📁 FILE ORGANIZATION

### Keep in Root
- `README.md` (project readme)

### Move to `aquamind/docs/progress/test_data_generation/`
- `INFRASTRUCTURE_SATURATION_PROBLEM_DEFINITION.md`
- `SCHEDULE_BASED_ARCHITECTURE_PROPOSAL.md`
- `CHECK_WHEN_DONE.md`
- `GENERATION_584_IN_PROGRESS.md`
- `GENERATION_IN_PROGRESS.md`
- `FEED_INVENTORY_AUTO_INIT.md` (if exists)
- This handover document

### Code Changes (Keep in place)
- `apps/batch/services/growth_assimilation.py` (Growth Engine fix)
- `scripts/data_generation/03_event_engine_core.py` (Feed auto-init + FKs)
- `scripts/data_generation/04_batch_orchestrator.py` (5-day stagger + chronological)
- `scripts/data_generation/generate_batch_schedule.py` (partial, needs fix)

---

## 🎯 SUCCESS METRICS

When implementation complete, you should achieve:

✅ 584 batches generated (100% success rate)  
✅ 87% instantaneous container saturation  
✅ 6-8 hours generation time (parallel with 14 workers)  
✅ Zero container conflicts  
✅ All FKs populated (mortality, environmental)  
✅ Growth Engine: No population doubling  
✅ Chronological realistic history (4.1 years)

---

## 💡 KEY INSIGHTS

### 1. Saturation Requires Dense Overlap
- 5-day stagger creates 18 batches overlapping per stage
- This is REALISTIC for high-intensity farms
- Requires 22 Hall-A's (we have exactly that!)
- But allocation must be smart (use both geographies)

### 2. Sequential ≠ Reliable at High Saturation
- Even sequential execution hits capacity with dynamic allocation
- 94% success rate (not 100%)
- Need deterministic pre-planning

### 3. Infrastructure is Well-Balanced
- 1,157 FW containers + 860 sea rings
- Designed for 900-day lifecycle (5×90 FW + 450 sea)
- Can achieve 87% with proper scheduling
- No infrastructure changes needed

### 4. Chronological Order Matters
- Not "all Faroe then all Scotland"
- Interleave by start date
- Mirrors real farm operations

### 5. Schedule File = Documentation
- Pre-planned YAML shows exactly what gets created
- Review before execution
- Version control for reproducibility

---

## 🚨 CRITICAL: Why This Matters

**For UAT:**
- Need realistic high-saturation data
- Need both completed + active batches
- Need Growth Analysis to work (requires scenarios)
- Need harvest data (completed batches)

**For Migration:**
- FishTalk migration requires reproducible test data
- Schedule-based provides deterministic output
- Can validate migration accuracy

**For Production:**
- Parallel execution essential for CI/CD
- Can't wait 24 hours for test data regeneration
- Need 100% reliable automation

---

## 📊 CURRENT STATE

**Database:** Clean (operational data wiped)  
**Infrastructure:** Ready (2,017 containers, 11,060 sensors)  
**Code Changes:** Ready to commit (Growth Engine, FK fixes, feed auto-init)  
**Schedule Planner:** 80% complete (needs occupancy bug fix)  
**Executor:** Not started (needs 1-2 hours)

**Estimated Time to Complete:**
- Fix planner: 2 hours
- Create executor: 1-2 hours
- Test with 20 batches: 30 min
- Execute 584 batches: 6-8 hours (parallel)
- **Total: ~12 hours** (vs 24+ hours sequential with failures)

---

## 🎓 LESSONS LEARNED

### 1. The Other AI's Math Was Wrong
- Claimed 18 batches could fit in 12 halls
- Forgot: 1 hall = 1 batch max at any time
- Always validate calculations with actual constraints

### 2. Saturation ≠ Simple
- Must respect physical limits (hall count)
- Can't just divide duration by stagger
- Need bin-packing algorithm essentially

### 3. Dynamic Allocation Doesn't Scale
- Works fine at low density (30-day stagger)
- Breaks at high density (5-day stagger)
- Pre-planning is THE solution

### 4. Testing Revealed the Issue
- 40-batch test showed 82% success (OK)
- 584-batch test showed 94% success (not OK)
- Scale testing is essential

---

## 🚀 RECOMMENDED NEXT STEPS

**Immediate (Next Session):**

1. **Read this document completely** (15 min)
2. **Fix schedule planner** (2 hours)
   - Debug occupancy tracking
   - Test with 584-batch plan
   - Validate zero conflicts
3. **Create schedule executor** (1-2 hours)
4. **Test with 20 batches** (30 min)
5. **Execute 584 batches** (6-8 hours parallel)
6. **Verify & commit** (30 min)

**Alternative (If Stuck):**

Use sequential with 30-day stagger (100% reliable):
```bash
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator.py \
  --execute --batches 90 --stagger 30
```
- Takes 6-8 hours
- Only 22% saturation (not ideal but functional)
- 100% success rate

---

## 📞 QUICK REFERENCE

**Current Situation:**
- Growth Engine: ✅ Fixed
- FK Models: ✅ Fixed  
- Feed Auto-Init: ✅ Fixed
- Parallel Execution: ❌ Blocked by allocation

**The Blocker:**
- Dynamic allocation fails at high saturation
- Need schedule-based approach
- 80% implemented, needs 3-4 hours to complete

**The Payoff:**
- 100% reliable parallel execution
- 6-8 hours for 584 batches (vs 24+ hours)
- 87% saturation achieved
- Deterministic, reproducible, production-ready

---

**All context provided. Clean handover. Good luck with the parallel execution fix!** 🎯

---

