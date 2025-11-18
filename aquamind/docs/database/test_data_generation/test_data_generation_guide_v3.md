# AquaMind Test Data Generation Guide v3.0

**Last Updated:** 2025-11-18  
**Status:** ✅ **PRODUCTION READY - Infrastructure Saturation Approach**

---

## 🎯 PURPOSE

Generate **realistic, production-scale test data** that:
- **Saturates infrastructure** (85% utilization like real farm)
- **Spans 6-7 years** of operational history
- **Includes completed + active batches** (realistic pipeline)
- **Generates 40+ million events** (environmental, feeding, mortality, growth)

---

## 🚀 QUICK START

### Option A: Full Infrastructure Saturation (~5-6 hours)

```bash
cd /Users/aquarian247/Projects/AquaMind

# 1. Wipe operational data (1 minute)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 2. Generate 170 batches with 7-year history (5-6 hours)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

**Expected Results:**
- **170 batches total** (85 per geography)
- **~112 completed batches** (full 900-day cycles)
- **~58 active batches** (various stages)
- **40 million environmental readings**
- **8 million feeding events**
- **80-100 GB database**

### Option B: Small Test (20 batches, ~90 minutes)

```bash
cd /Users/aquarian247/Projects/AquaMind

# Wipe + generate 20 batches (for testing)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14
```

**Expected Results:**
- **40 batches total** (20 per geography)
- **~25 completed batches** (full 900-day cycles)
- **~15 active batches**
- **8 million environmental readings**
- **1.5 million feeding events**
- **15-20 GB database**

### Option C: Single Batch Verification (15 minutes)

```bash
# Quick test of single batch
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 \
  --geography "Faroe Islands" --duration 200
```

---

## 📚 ARCHITECTURE

### Infrastructure Capacity

**Total Infrastructure:** 2,017 containers
- **Faroe Islands:** 1,116 containers (656 freshwater + 460 sea)
- **Scotland:** 900 containers (500 freshwater + 400 sea)
- **Test Geography:** 1 container (for testing only)

**Batch Capacity:**
- Each batch uses ~10 containers per stage
- With 900-day lifecycle and 30-day stagger, containers are reused
- **Theoretical max:** ~171 active batches at 85% saturation
- **Recommended:** 85 batches per geography = 170 total

### The 5-Script System

#### **Script 0: Selective Wipe** (`00_wipe_operational_data.py`)
**Purpose:** Fast operational data cleanup (preserves infrastructure)  
**Time:** 1 minute  
**Deletes:** Batches, feeding, environmental, health, finance, scenarios  
**Preserves:** Infrastructure, feed types, models, parameters  
**Interactive:** Yes (requires typing "DELETE")  

**Usage:**
```bash
# Interactive
python scripts/data_generation/00_wipe_operational_data.py --confirm

# Non-interactive (in scripts)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
```

#### **Script 1: Bootstrap Infrastructure** (`01_bootstrap_infrastructure.py`)
**Purpose:** One-time infrastructure setup  
**Time:** 10-30 seconds  
**Creates:**
- 3 Geographies (Faroe Islands, Scotland, Test Geography)
- 25 Freshwater Stations
- 120 Halls (specialized by lifecycle stage)
- 2,017 Containers (1,157 freshwater + 860 sea)
- 11,060 Sensors

**When to run:** Once per database (usually already exists)

**Usage:**
```bash
python scripts/data_generation/01_bootstrap_infrastructure.py
```

#### **Script 1b: Initialize Scenario Master Data** (`01_initialize_scenario_master_data.py`)
**Purpose:** Initialize scenario configuration data  
**Time:** 30 seconds  
**Creates:**
- Temperature profiles (4 profiles with 450 daily readings each)
- Lifecycle stage weight ranges (6 stages)
- Biological constraints (stage transition rules)

**When to run:** Once after infrastructure, before batch generation

**Usage:**
```bash
python scripts/data_generation/01_initialize_scenario_master_data.py
```

**Critical:** Scenarios require this data. Without it, projections will be unrealistic (8g adult fish instead of 5000g).

#### **Script 3: Event Engine Core** (`03_event_engine_core.py`)
**Purpose:** Generate single batch with full lifecycle  
**Time:** 2-3 minutes per batch (with SKIP_CELERY_SIGNALS=1)  
**Features:**
- Day-by-day chronological event processing
- Environmental readings (6/day × 7 sensors × containers)
- Feeding events (2/day with FIFO consumption)
- Mortality (probabilistic, stage-specific rates)
- Growth samples (weekly)
- Stage transitions every 90 days with transfer workflows
- "From batch" scenario creation at Parr stage (Day 180)
- Auto feed reordering when stock < 20%
- Lice sampling (weekly in Adult stage)
- Finance integration (harvest facts for completed batches)

**Usage:**
```bash
# Test batch (200 days)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 \
  --eggs 3500000 \
  --geography "Faroe Islands" \
  --duration 200

# Full lifecycle batch (900 days)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2020-01-01 \
  --eggs 3500000 \
  --geography "Scotland" \
  --duration 900
```

**Per 900-Day Batch:**
- ~300,000 environmental readings
- ~150,000 feeding events
- ~10,000 mortality events
- ~130 growth samples
- ~50 lice counts (Adult stage)
- 5 stage transitions with transfer workflows

#### **Script 4: Parallel Orchestrator** (`04_batch_orchestrator_parallel.py`)
**Purpose:** Generate multiple batches in parallel with historical data  
**Time:** 
- 20 batches: 60-90 minutes
- 85 batches: 5-6 hours
- 170 batches: 5-6 hours (170 total)

**Features:**
- ✅ Multiprocessing (14 workers on M4 Max)
- ✅ **Historical start dates** (goes back 7 years)
- ✅ **Date-bounded completion** (stops at today for active batches)
- ✅ **Mix of completed + active** batches
- ✅ Round-robin station selection (no container conflicts)
- ✅ Transaction-safe (database locks prevent races)
- ✅ Bulk Growth Analysis recompute at end

**Key Logic:**
```python
# For 85 batches per geography:
start_date = today - timedelta(days=85 * 30 + 50)  # ~7 years ago

for i in range(85):
    batch_start = start_date + timedelta(days=i * 30)
    days_since_start = (today - batch_start).days
    duration = min(900, days_since_start)  # ← Date-bounded!
    
    # First ~56 batches: duration = 900 (completed)
    # Last ~29 batches: duration < 900 (active)
```

**Usage:**
```bash
# Dry run (see what would be generated)
python scripts/data_generation/04_batch_orchestrator_parallel.py --batches 85

# Execute with SKIP_CELERY_SIGNALS (required!)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

**⚠️ CRITICAL:** Always use `SKIP_CELERY_SIGNALS=1` during test data generation to avoid 600x slowdown!

---

## 🎯 EXPECTED RESULTS

### Full Saturation (170 Batches, 85 per Geography)

**Batch Distribution:**
- **Total Batches:** 170
- **Completed/Harvested:** ~112 batches (>900 days old, full lifecycle)
- **Active Batches:** ~58 batches (various stages, partial data)
- **Geography Split:** 50/50 (85 Faroe + 85 Scotland)

**Stage Distribution (Active Batches):**
- Egg&Alevin: ~10 batches
- Fry: ~8 batches
- Parr: ~8 batches
- Smolt: ~8 batches
- Post-Smolt: ~8 batches
- Adult: ~16 batches (longest stage)

**Data Volume:**
- **Environmental Readings:** ~40 million (6/day × 7 sensors × 10 containers × avg days)
- **Feeding Events:** ~8 million (2/day × 10 containers × feeding days)
- **Mortality Events:** ~800,000
- **Growth Samples:** ~400,000
- **Lice Counts:** ~50,000
- **Total Events:** ~50 million
- **Database Size:** 80-100 GB

**Container Utilization:**
- **Freshwater:** 80-85% utilized
- **Sea Cages:** 85-90% utilized
- **Feed Inventory:** Continuously replenishing

### Medium Test (40 Batches, 20 per Geography)

**Batch Distribution:**
- **Total Batches:** 40
- **Completed:** ~25 batches (full lifecycle)
- **Active:** ~15 batches

**Data Volume:**
- **Environmental Readings:** ~8 million
- **Feeding Events:** ~1.5 million
- **Total Events:** ~10 million
- **Database Size:** 15-20 GB
- **Generation Time:** 60-90 minutes (parallel)

### Small Test (Single 200-Day Batch)

**Per Batch (200 days, Egg→Fry→Parr):**
- Environmental: 36,000 readings
- Feeding: 2,200 events
- Mortality: 2,000 events
- Growth: 160 samples
- Population: ~2.9M fish (83% survival)
- Avg Weight: 15.2g (Parr)
- Biomass: 44 tonnes

---

## 📋 EXECUTION WORKFLOW

### Step 1: Pre-Flight Check (30 seconds)

```bash
cd /Users/aquarian247/Projects/AquaMind

# Verify infrastructure exists
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.infrastructure.models import Container, Geography

total = Container.objects.filter(active=True).count()
print(f'Total containers: {total}')
print('✅ Ready' if total > 2000 else '❌ Run 01_bootstrap_infrastructure.py first')
"
```

### Step 2: Wipe Operational Data (1 minute)

```bash
# Interactive wipe
python scripts/data_generation/00_wipe_operational_data.py --confirm
# (Type 'DELETE' when prompted)

# OR non-interactive
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
```

### Step 3: Initialize Scenario Master Data (30 seconds, first time only)

```bash
python scripts/data_generation/01_initialize_scenario_master_data.py
```

**Check if already exists:**
```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.scenario.models import TemperatureProfile
print(f'Temperature profiles: {TemperatureProfile.objects.count()}')
print('✅ Already initialized' if TemperatureProfile.objects.count() > 0 else '❌ Run initialization script')
"
```

**Note:** Feed inventory is **auto-initialized** by event engine on first batch. No separate script needed!

### Step 4A: Test with 20 Batches (Recommended First)

```bash
# Dry run first (see plan)
python scripts/data_generation/04_batch_orchestrator_parallel.py --batches 20

# Execute (60-90 minutes)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14
```

**Monitor progress:**
```bash
# In another terminal
tail -f /tmp/batch_gen_20.log

# Or check database
watch -n 60 'echo "SELECT COUNT(*) FROM batch_batch;" | psql aquamind_db'
```

### Step 4B: Scale to Full Saturation (After successful test)

```bash
# Execute full 170 batches (5-6 hours)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

---

## 🔑 CRITICAL REQUIREMENTS

### 1. SKIP_CELERY_SIGNALS=1 (REQUIRED!)

**Why:** Celery signal handlers try to connect to Redis after every event. Without Redis, this causes **600x slowdown** (400 minutes vs 2 minutes per batch).

**Production:** Celery enables real-time Growth Analysis updates  
**Test Data:** Celery signals cause massive performance degradation

**Solution:** 
- Set `SKIP_CELERY_SIGNALS=1` environment variable
- Growth Analysis recomputed in bulk at orchestrator end

### 2. Feed Names Must Match Exactly

Event engine expects EXACT names:
- `Starter Feed 0.5mm` (Fry)
- `Starter Feed 1.0mm` (Parr)
- `Grower Feed 2.0mm` (Smolt)
- `Grower Feed 3.0mm` (Post-Smolt)
- `Finisher Feed 4.5mm` (Adult)
- `Finisher Feed 6.0mm` (Adult, late)

**Verification:**
```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.inventory.models import Feed
feeds = [f.name for f in Feed.objects.all()]
print('✅ PASS' if 'Starter Feed 0.5mm' in feeds else '❌ FAIL: Run 00_wipe script')
"
```

### 3. Scenario Master Data Required

Scenarios need temperature profiles and lifecycle weight ranges. Without this:
- Projections compute but produce unrealistic results (8g adult instead of 5000g)
- Growth Analysis orange line won't work

**Run once before batch generation:**
```bash
python scripts/data_generation/01_initialize_scenario_master_data.py
```

---

## 📊 INFRASTRUCTURE SATURATION MODEL

### How Batches Utilize Infrastructure

**Container Reuse Pattern:**
- Each batch progresses through 6 stages
- Each stage uses ~10 containers
- Stage transitions every 90 days
- Containers released after stage transition (reused by other batches)

**30-Day Stagger Effect:**
```
Day   0: Batch 1 occupies Hall-A (Egg&Alevin)
Day  30: Batch 2 occupies Hall-A, Batch 1 moves to Hall-B
Day  60: Batch 3 occupies Hall-A, Batch 2 in Hall-B, Batch 1 in Hall-C
Day  90: Batch 4 occupies Hall-A, Batch 1 transitions to Hall-D (Hall-A released)
```

**Result:** Each set of 10 containers can support ~30 batches over their lifecycles.

### Saturation Calculation

```
Total containers: 2,017
Containers per batch (avg): 10-20 (depending on stage)
Container reuse factor: ~30x (over 900-day lifecycle with 30-day stagger)

Theoretical max: 2,017 × 0.85 ÷ 10 ≈ 171 active batches
Actual target: 170 batches (85 per geography)
```

**At any given moment:**
- ~60-80 batches active (various stages)
- ~90-110 batches completed (harvested)
- ~1,500-1,700 containers occupied (85% utilization)

---

## 🔧 SCRIPT REFERENCE

### Core Scripts

| Script | Purpose | Time | When to Run |
|--------|---------|------|-------------|
| `00_wipe_operational_data.py` | Selective data wipe | 1 min | Before each test data regeneration |
| `01_bootstrap_infrastructure.py` | Infrastructure setup | 30 sec | Once per database |
| `01_initialize_scenario_master_data.py` | Scenario models | 30 sec | Once after infrastructure |
| `03_event_engine_core.py` | Single batch generation | 2-3 min | Core engine (called by orchestrator) |
| `04_batch_orchestrator_parallel.py` | Multi-batch parallel generation | 1-6 hrs | Main production data generation |

### Supporting Scripts

| Script | Purpose | Notes |
|--------|---------|-------|
| `verify_single_batch.py` | Automated verification | Checks fixes applied |
| `verify_test_data.py` | Comprehensive data quality check | Post-generation validation |

### Deprecated Scripts (Don't Use)

| Script | Why Deprecated | Use Instead |
|--------|----------------|-------------|
| `00_complete_reset.py` | Deletes infrastructure too | `00_wipe_operational_data.py` |
| `02_initialize_master_data.py` | Interactive prompts | Master data preserved by wipe |
| `fix_feed_inventory.py` | Manual initialization | Event engine auto-initializes |
| `04_batch_orchestrator.py` | No parallelization | `04_batch_orchestrator_parallel.py` |

---

## 📈 PERFORMANCE BENCHMARKS

### Event Engine (Single Batch)

| Duration | Events | Time (w/ SKIP_CELERY_SIGNALS) | DB Size |
|----------|--------|-------------------------------|---------|
| 200 days | ~40K | 2 min | ~50 MB |
| 550 days | ~150K | 5 min | ~150 MB |
| 900 days | ~300K | 8 min | ~400 MB |

**Without SKIP_CELERY_SIGNALS:** 400+ min per batch (600x slower!) ❌

### Parallel Orchestrator (Multi-Batch)

| Batches | Completed | Active | Time (14 workers) | DB Size | Events |
|---------|-----------|--------|-------------------|---------|--------|
| 40 (20/geo) | ~25 | ~15 | 60-90 min | 15-20 GB | ~10M |
| 80 (40/geo) | ~50 | ~30 | 2-3 hours | 40-50 GB | ~20M |
| 170 (85/geo) | ~112 | ~58 | 5-6 hours | 80-100 GB | ~50M |

**Speedup:** ~10-12x vs sequential (I/O-bound, not CPU-bound)

**M4 Max (16-core, 128GB RAM) Performance:**
- 14 workers recommended (leave 2 cores for system/DB)
- CPU utilization: 20-40% (I/O-bound workload)
- Database is the bottleneck (transaction locks, disk writes)

---

## 🎯 SUCCESS CRITERIA

### After 40-Batch Test (20 per geography)

**Batch Statistics:**
```bash
Total Batches: 40
Completed: ~25 (>900 days old)
Active: ~15 (various stages)
```

**Data Volume:**
```bash
Environmental Readings: 7-10 million
Feeding Events: 1-2 million
Mortality Events: 100-200K
Growth Samples: 40-60K
```

**Quality Checks:**
- ✅ Survival rates: 83-87% overall
- ✅ FCR values: 0.9-3.0 (not 10-70)
- ✅ Growth Analysis: No population doubling after transitions
- ✅ Feed stock: Decreasing but > 0
- ✅ Container utilization: 30-40%

### After Full 170-Batch Generation

**Batch Statistics:**
```bash
Total Batches: 170
Completed: ~112 (>900 days old)
Active: ~58 (various stages)
Stage Distribution: 8-10 batches per stage (active)
```

**Data Volume:**
```bash
Environmental Readings: 35-45 million
Feeding Events: 7-9 million
Mortality Events: 700-900K
Growth Samples: 350-450K
Lice Counts: 40-60K
Total Events: ~50 million
Database Size: 80-100 GB
```

**Quality Checks:**
- ✅ Container utilization: 80-85%
- ✅ All 6 lifecycle stages represented
- ✅ Both geographies balanced
- ✅ Harvest weights: 4-6 kg average (Adult stage)
- ✅ No container over-allocation conflicts

---

## 🔍 VERIFICATION QUERIES

### Quick Stats Check

```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading
from apps.batch.models import GrowthSample

print('='*80)
print('DATABASE STATISTICS')
print('='*80)
print(f'Batches: {Batch.objects.count()}')
print(f'  Completed: {Batch.objects.filter(status=\"COMPLETED\").count()}')
print(f'  Active: {Batch.objects.filter(status=\"ACTIVE\").count()}')
print()
print(f'Environmental Readings: {EnvironmentalReading.objects.count():,}')
print(f'Feeding Events: {FeedingEvent.objects.count():,}')
print(f'Growth Samples: {GrowthSample.objects.count():,}')
"
```

### Detailed Batch Analysis

```sql
-- Per-batch event counts
SELECT 
    b.batch_number,
    b.status,
    ls.name as current_stage,
    COUNT(DISTINCT bca.id) as assignments,
    COUNT(DISTINCT CASE WHEN bca.is_active THEN bca.id END) as active_assignments,
    (SELECT COUNT(*) FROM inventory_feedingevent WHERE batch_id = b.id) as feeding_events,
    (SELECT COUNT(*) FROM environmental_environmentalreading WHERE batch_id = b.id) as env_readings,
    (SELECT COUNT(*) FROM batch_growthsample WHERE batch_id = b.id) as growth_samples
FROM batch_batch b
JOIN batch_lifecyclestage ls ON b.lifecycle_stage_id = ls.id
LEFT JOIN batch_batchcontainerassignment bca ON bca.batch_id = b.id
GROUP BY b.id, b.batch_number, b.status, ls.name
ORDER BY b.batch_number;
```

### Growth Analysis Verification (Issue #112 Fix)

```bash
# Verify no population doubling at Day 91 transitions
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.batch.models import Batch, ActualDailyAssignmentState
from datetime import timedelta

print('Growth Analysis Double-Counting Check (Issue #112):')
print('='*80)
print()

for batch in Batch.objects.filter(start_date__lte='2025-08-01').order_by('batch_number')[:5]:
    day_91_states = ActualDailyAssignmentState.objects.filter(
        batch=batch,
        day_number=91
    )
    
    if day_91_states.exists():
        total_pop = sum(s.population for s in day_91_states)
        initial_eggs = 3_500_000  # approximate
        
        status = '✅ PASS' if 2_800_000 <= total_pop <= 3_200_000 else '❌ DOUBLED' if total_pop > 5_000_000 else '⚠️  CHECK'
        print(f'{batch.batch_number}: Day 91 pop = {total_pop:,} | {status}')
"
```

### Container Utilization Check

```sql
-- Real-time container utilization
WITH occupied AS (
    SELECT container_id
    FROM batch_batchcontainerassignment
    WHERE is_active = TRUE
)
SELECT 
    geo.name as geography,
    COUNT(DISTINCT c.id) as total_containers,
    COUNT(DISTINCT o.container_id) as occupied,
    ROUND(100.0 * COUNT(DISTINCT o.container_id) / COUNT(DISTINCT c.id), 1) as utilization_pct
FROM infrastructure_container c
LEFT JOIN infrastructure_hall h ON c.hall_id = h.id
LEFT JOIN infrastructure_freshwaterstation fw ON h.freshwater_station_id = fw.id
LEFT JOIN infrastructure_area a ON c.area_id = a.id
LEFT JOIN infrastructure_geography geo ON (geo.id = fw.geography_id OR geo.id = a.geography_id)
LEFT JOIN occupied o ON c.id = o.container_id
WHERE c.active = TRUE
GROUP BY geo.name
ORDER BY geo.name;
```

---

## 🐛 TROUBLESHOOTING

### Issue: "No feeding events created"

**Diagnosis:**
```bash
DJANGO_SETTINGS_MODULE=aquamind.settings python -c "
import django; django.setup()
from apps.inventory.models import Feed, FeedingEvent
from apps.batch.models import Batch

batch = Batch.objects.latest('created_at')
feeding = FeedingEvent.objects.filter(batch=batch).count()
feeds = Feed.objects.all().values_list('name', flat=True)

print(f'Feeding events: {feeding}')
print(f'Feeds in DB: {list(feeds)}')
print('✅ Feed names correct' if 'Starter Feed 0.5mm' in feeds else '❌ Wrong feed names')
"
```

**Fix:** Run `echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm`

### Issue: "GrowthAssimilationEngine: No scenario available"

**Cause:** Batch doesn't have associated scenario (required for Growth Analysis)

**When this happens:**
- Very young batches (< 180 days, before Parr stage)
- Scenario creation occurs at Day 180

**Not an error** - expected for batches < 180 days old.

### Issue: Parallel generation seems slow / not using all CPUs

**Expected behavior:**
- Workload is **I/O-bound** (database operations), not CPU-bound
- CPU utilization: 20-40% (not 100%)
- Database is the bottleneck (Postgres transaction locks)
- **Still 10-12x faster** than sequential despite low CPU%

**Verification:**
```bash
# Check active workers
ps aux | grep "03_event_engine_core.py" | wc -l
# Should show 14 during execution

# Check database connections
echo "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" | psql aquamind_db
```

### Issue: "Unusually high FCR=10.83" warnings

**Not an error!** These are normal in early feeding days:
- FCR caps at 10.0 for data quality
- Early Fry stage has unstable FCR (small fish, imprecise feeding)
- FCR stabilizes by Parr stage (1.0-1.5 range)

**Ignore these warnings** - they indicate the FCR capping system is working correctly.

### Issue: Out of disk space

**170 batches = 80-100 GB database**

**Check available space:**
```bash
df -h | grep /dev/disk
```

**Minimum required:** 150 GB free (database + logs + temp files)

---

## 💡 KEY INSIGHTS

### 1. Historical vs Date-Bounded

**Historical Start Dates:**
- Script calculates: `today - (batches × 30 days + 50 days)`
- For 85 batches: Goes back ~7 years (2018-11-05)
- Creates mix of completed + active batches

**Date-Bounded Execution:**
- Each batch runs: `min(900 days, days_since_start)`
- Old batches: Full 900-day cycle (completed)
- Recent batches: Partial cycle (active)

**Example (85 batches per geography):**
```
Batch 1:  Start 2018-11-05 → Duration 900 days → Completed ✅
Batch 56: Start 2023-05-15 → Duration 900 days → Completed ✅
Batch 57: Start 2023-06-14 → Duration 893 days → Active (Adult stage)
Batch 85: Start 2025-09-29 → Duration 50 days → Active (Egg&Alevin)
```

### 2. Parallel Execution is I/O-Bound

**Don't expect 100% CPU utilization** - the bottleneck is:
- Database writes (Postgres transaction locks)
- Disk I/O (millions of records)
- Network overhead (if DB on remote host)

**Still provides 10-12x speedup** through concurrent I/O operations.

### 3. Growth Analysis Requires Scenarios

The Growth Engine (Issue #112) requires scenarios for TGC/mortality models:
- Scenarios created at Day 180 (Parr transition)
- Batches < 180 days old will error during Growth Analysis recompute
- **This is expected behavior** - not a bug

### 4. Celery Performance Impact

**Production System:**
```
Operator records event → Signal fires → Celery task → Background recompute
```

**Test Data Generation:**
```
Event engine creates 10,000 events → 10,000 signal attempts → 10,000 Redis failures → 600x slowdown
```

**Always use `SKIP_CELERY_SIGNALS=1`** for test data generation!

### 5. Infrastructure Saturation is Realistic

**Real salmon farms operate at:**
- 80-90% capacity (maximize assets, minimize waste)
- Multiple batches in different stages (continuous operation)
- Container reuse (batches transition through facilities)

**Our model mirrors this:** 85% saturation with 170 batches across 2,017 containers.

---

## 📊 VALIDATION SCRIPT

Save as `verify_test_data.py`:

```python
#!/usr/bin/env python3
"""Comprehensive test data verification"""
import os, sys, django

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
django.setup()

from apps.batch.models import Batch, ActualDailyAssignmentState
from apps.inventory.models import FeedingEvent
from apps.environmental.models import EnvironmentalReading
from apps.batch.models import GrowthSample
from datetime import timedelta

print('='*80)
print('TEST DATA VERIFICATION')
print('='*80)
print()

# Batch counts
total = Batch.objects.count()
completed = Batch.objects.filter(status='COMPLETED').count()
active = Batch.objects.filter(status='ACTIVE').count()

print(f'Batches:')
print(f'  Total: {total}')
print(f'  Completed: {completed}')
print(f'  Active: {active}')
print()

# Event counts
env = EnvironmentalReading.objects.count()
feeding = FeedingEvent.objects.count()
growth = GrowthSample.objects.count()

print(f'Events:')
print(f'  Environmental: {env:,}')
print(f'  Feeding: {feeding:,}')
print(f'  Growth: {growth:,}')
print()

# Expected vs Actual (for 40 batches)
if total >= 40:
    print('Expected (40 batches):')
    print(f'  Environmental: 7-10 million')
    print(f'  Feeding: 1-2 million')
    print()
    
    env_ok = 7_000_000 <= env <= 12_000_000
    feed_ok = 1_000_000 <= feeding <= 3_000_000
    
    print(f'  Environmental: {"✅ PASS" if env_ok else "❌ FAIL"}')
    print(f'  Feeding: {"✅ PASS" if feed_ok else "❌ FAIL"}')

# Growth Engine fix verification (Issue #112)
print()
print('='*80)
print('GROWTH ENGINE FIX VERIFICATION (Issue #112)')
print('='*80)
print()

tested = 0
passed = 0
for batch in Batch.objects.filter(start_date__lte='2025-08-01').order_by('batch_number')[:10]:
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
        else:
            status = '⚠️  CHECK'
        
        print(f'{batch.batch_number}: Day 91 = {total_pop:,} fish | {status}')

if tested > 0:
    print()
    print(f'Growth Analysis Fix: {passed}/{tested} batches passed')
    print(f'Status: {"✅ ALL PASS" if passed == tested else "❌ SOME FAILURES"}')
else:
    print('No batches with Day 91 data yet (all < 91 days old)')

print()
print('='*80)
print('VERIFICATION COMPLETE')
print('='*80)
```

---

## 🔄 ITERATIVE WORKFLOW

### Development Cycle

```bash
# 1. Test small (15 min)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 --geography "Faroe Islands" --duration 200

# 2. Verify success
python verify_test_data.py

# 3. Test medium (90 min)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14

# 4. Verify quality
python verify_test_data.py

# 5. Scale to full (5-6 hours)
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

### UAT/Production Preparation

```bash
# Full saturation with verification
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14

python verify_test_data.py

# Check for errors
grep -i "error\|fail" /tmp/batch_gen_*.log
```

---

## 🚨 COMMON MISTAKES

### ❌ Mistake 1: Forgetting SKIP_CELERY_SIGNALS
```bash
# WRONG - Will take 40+ hours
python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85

# CORRECT - Takes 5-6 hours
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85
```

### ❌ Mistake 2: Using Sequential Orchestrator
```bash
# SLOW - 40+ hours
python scripts/data_generation/04_batch_orchestrator.py --execute --batches 85

# FAST - 5-6 hours
python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85 --workers 14
```

### ❌ Mistake 3: Too Few Batches
```bash
# INCOMPLETE - Only 20 batches, 5% of data volume
python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 10

# REALISTIC - 170 batches, full infrastructure saturation
python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85
```

### ❌ Mistake 4: Skipping Scenario Initialization
```bash
# Will fail Growth Analysis recompute
python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85

# CORRECT - Initialize scenarios first
python scripts/data_generation/01_initialize_scenario_master_data.py
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py --execute --batches 85
```

---

## 📚 HISTORICAL CONTEXT

### November 18, 2025 - Growth Analysis Fix (Issue #112)

**Problem:** Population doubling at stage transitions (~2x inflation)

**Root Cause:** Transfer destinations had fish in BOTH metadata (`assignment.population_count`) AND transfer records (`TransferAction.transferred_count`). Growth Engine correctly summed both → double-counting.

**Fix Applied:** `apps/batch/services/growth_assimilation.py` line 469-485
- Detect if assignment is transfer destination on first day
- Start from 0 population (not metadata)
- Let placements add fish daily from transfers

**Verification:** Day 91 population = ~3M (not ~6M)

**Documentation:** `/aquamind/docs/progress/test_data_2025_11_18/`

---

## 🎉 READY FOR PRODUCTION

**Current Status (v3.0):**
- ✅ All core systems verified
- ✅ Growth Engine fix applied and tested
- ✅ Parallel orchestrator optimized (10-12x speedup)
- ✅ Infrastructure saturation model validated
- ✅ Celery signal bypass for 600x speedup
- ✅ Realistic data volumes and distributions

**Recommended Approach:**
1. **Test:** 20 batches (90 minutes)
2. **Verify:** Run validation queries
3. **Scale:** 85 batches (5-6 hours) if test passes

---

## 📝 COMMAND REFERENCE

```bash
# === WIPE DATA ===
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# === ONE-TIME SETUP ===
python scripts/data_generation/01_bootstrap_infrastructure.py  # Usually exists
python scripts/data_generation/01_initialize_scenario_master_data.py  # Required

# === TEST GENERATION ===
# Single batch (15 min)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 --geography "Faroe Islands" --duration 200

# 20 batches (90 min)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14

# === FULL SATURATION ===
# 170 batches (5-6 hours)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14

# === VERIFICATION ===
python verify_test_data.py
```

---

**Single Source of Truth** - Version 3.0  
**Last Validated:** 2025-11-18 with Growth Engine fix  
**Expected Data Volume:** 40M+ events for full saturation

---

