# AquaMind Test Data Generation Guide v6.0

**Last Updated:** 2025-11-21
**Status:** ✅ **PRODUCTION READY - Hybrid Weight-Aware Deterministic Scheduling**

**⚠️ THIS IS THE SINGLE SOURCE OF TRUTH FOR TEST DATA GENERATION**

---

## 🎯 PURPOSE

Generate **realistic, production-scale test data** that:
- **Saturates infrastructure** (65-70% utilization like real farm)
- **Spans 4-5 years** of operational history (auto-calculated from constraints)
- **Includes completed + active batches** (realistic pipeline)
- **Generates 50+ million events** (environmental, feeding, mortality, growth, health)

---

## 🚀 QUICK START

### Option A: Full Infrastructure Saturation (45 minutes)

```bash
cd /Users/aquarian247/Projects/AquaMind

# 1. One-time setup (if not already done - 2 minutes total)
python scripts/data_generation/01_initialize_scenario_master_data.py
python scripts/data_generation/01_initialize_finance_policies.py
python scripts/data_generation/01_initialize_health_parameters.py

# 2. Wipe operational data (fast with TRUNCATE)
psql aquamind_db -c "TRUNCATE TABLE batch_batch CASCADE; TRUNCATE TABLE inventory_feedpurchase CASCADE;"

# 3. Generate schedule (auto-calculates optimal batch count from constraints)
python scripts/data_generation/generate_batch_schedule.py \
  --years 4 --stagger 13 --saturation 0.85 \
  --output config/schedule_production.yaml

# 4. Execute schedule with parallel workers (45 minutes)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/schedule_production.yaml \
  --workers 14 --use-partitions \
  --log-dir scripts/data_generation/logs/production
```

**Expected Results:**
- **144 batches total** (72 per geography, auto-calculated from infrastructure constraints)
- **~120 completed batches** (full 900-day cycles)
- **~24 active batches** (various stages)
- **50+ million environmental readings**
- **8+ million feeding events**
- **3,000+ health sampling events** (monthly, 75 fish each)
- **225K+ fish observations** (75 per event)
- **2M+ health parameter scores** (9 per fish)
- **4,000+ treatments** (vaccinations + lice)
- **Finance facts + intercompany transactions**
- **5.2 years** of operational history
- **70% infrastructure utilization** (10 rings per batch)

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
- Each batch uses 10 containers per freshwater stage, 10 rings in Adult stage
- With 900-day lifecycle and 13-day stagger, containers are reused
- **Bottleneck:** Scotland sea rings (400 total, 10 per batch = max 34 concurrent Adult)
- **Auto-calculated optimal:** 72 batches per geography = 144 total
- **Constraint formula:** min(time_allows, infrastructure_allows) where infrastructure = (scotland_rings × saturation) / rings_per_batch

### The 7-Script System

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

#### **Script 1c: Initialize Finance Policies** (`01_initialize_finance_policies.py`)
**Purpose:** Initialize finance intercompany policies and dimension sites  
**Time:** 30 seconds  
**Creates:**
- DimCompany records for all geographies × subsidiaries
- DimSite records for all stations and areas (94 total)
- Intercompany policies (18 total): FW→FM (smolt), FM→LG (harvest)

**When to run:** Once after infrastructure, before batch generation

**Usage:**
```bash
python scripts/data_generation/01_initialize_finance_policies.py
```

**Critical:** Required for finance_project command to create IntercompanyTransaction records.

#### **Script 1d: Initialize Health Parameters** (`01_initialize_health_parameters.py`)
**Purpose:** Initialize health assessment parameters and scoring definitions  
**Time:** 15 seconds  
**Creates:**
- 9 health parameters (gill, eye, wounds, fin, body, swimming, appetite, mucous, color)
- Score definitions (0-3 scale) for each parameter with clinical descriptions

**When to run:** Once after infrastructure, before batch generation

**Usage:**
```bash
python scripts/data_generation/01_initialize_health_parameters.py
```

**Critical:** Required for health sampling events in test data.

#### **Script 3: Event Engine Core** (`03_event_engine_core.py`)
**Purpose:** Generate single batch with full lifecycle  
**Time:** 2-3 minutes per batch (with SKIP_CELERY_SIGNALS=1)  
**Features:**
- Day-by-day chronological event processing
- Environmental readings (6/day × 7 sensors × containers)
- Feeding events (2/day with FIFO consumption)
- Mortality (probabilistic, stage-specific rates)
- Growth samples (weekly)
- **Health sampling** (monthly, 75 fish, 9 parameters scored)
- **Vaccinations** (4 per batch: days 180, 210, 280, 310)
- **Lice treatments** (2 per batch, Adult stage sea cages only)
- Stage transitions every 90 days with transfer workflows
- **Scenario creation at Day 1** (760-day projection to realistic harvest weight ~6kg)
- **Scenario pinning** (sets batch.pinned_scenario for Growth Analysis)
- Auto feed reordering when stock < 20%
- Lice sampling (weekly in Adult stage)
- Finance integration (harvest facts for completed batches)
- **TGC Formula:** Industry-standard cube-root method with stage-specific values
- **Status management:** Sets COMPLETED status after harvest

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
- ~16 health sampling events (monthly, Post-Smolt/Adult)
- ~1,200 fish observations (75 per event)
- ~10,800 parameter scores (9 per fish)
- ~68 treatments (40 vaccinations + 28 lice treatments)
- 5 stage transitions with transfer workflows
- 1 scenario (pinned to batch)
- ~70 finance facts (if harvested)

#### **Script 4a: Schedule Generator** (`generate_batch_schedule.py`)
**Purpose:** Generate deterministic, conflict-free batch generation schedule  
**Time:** 30 seconds  
**Features:**
- ✅ Auto-calculates optimal batch count from time/infrastructure constraints
- ✅ Pre-allocates all containers (zero runtime conflicts)
- ✅ Validates schedule before execution
- ✅ Worker partitioning for parallel execution
- ✅ Weight-aware planning (accounts for harvest timing variation)

**Usage:**
```bash
# Auto-calculate from constraints (recommended)
python scripts/data_generation/generate_batch_schedule.py \
  --years 4 --stagger 13 --saturation 0.85 \
  --output config/schedule_production.yaml

# Or specify exact batch count
python scripts/data_generation/generate_batch_schedule.py \
  --batches 72 --stagger 13 --saturation 0.85 \
  --output config/schedule_production.yaml
```

#### **Script 4b: Schedule Executor** (`execute_batch_schedule.py`)
**Purpose:** Execute pre-planned schedule with parallel workers  
**Time:** 
- 20 batches: 10-15 minutes
- 144 batches: 45-60 minutes

**Features:**
- ✅ **Deterministic execution** (pre-allocated containers, no races)
- ✅ **Subprocess-based parallelization** (Django-safe)
- ✅ **Per-batch logging** (individual log files for debugging)
- ✅ **Zero race conditions** (all IDs deterministic)
- ✅ **Order-based stage lookups** (robust to name changes)

**Usage:**
```bash
# Execute with parallel workers and per-batch logging
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/schedule_production.yaml \
  --workers 14 --use-partitions \
  --log-dir scripts/data_generation/logs/production
```

**⚠️ CRITICAL:** Always use `SKIP_CELERY_SIGNALS=1` during test data generation to avoid 600x slowdown!

### v5.0 Improvements (2025-11-21)

**🐛 Fixed Issues:**
- **ImportError Fix:** Removed non-existent `BatchContainerAssignmentService` import
- **Celery Avoidance:** Engine skips Growth Analysis recompute when `SKIP_CELERY_SIGNALS=1`
- **Service Pattern:** Orchestrator uses `recompute_batch_assignments()` function instead of service class
- **Deterministic Station Assignment:** Pre-assigned stations eliminate race conditions
- **Ring Spread:** Sea transfers distribute evenly across all 20 rings per area

**✅ Success Rate:** 92.5% (37/40 batches) in recent test run
**🎯 Infrastructure Saturation:** >80% target achieved
**⚡ Performance:** No Celery overhead (600x faster than v4.0)

### ✅ v6.0: Hybrid Weight-Aware Deterministic Scheduler (IMPLEMENTED)

**🎯 Goal:** 100% success rate + realistic harvest variation through intelligent planning

**📋 Solution:** Enhanced deterministic scheduler with weight-based harvest modeling

**🔧 How It Works:**
1. **Weight-Based Planning:** Models harvest timing using TGC formula + random weight targets (4.5-6.5kg)
2. **Conservative Allocation:** Plans for worst-case duration (highest weight target) to prevent conflicts
3. **Deterministic Execution:** Uses same random seed for harvest targets across planning/execution
4. **Adaptive Saturation:** Containers freed early when batches harvest before planned end date

**✅ Perfect Compatibility:**
- **Planning:** Accounts for harvest randomness through worst-case modeling
- **Execution:** Uses identical weight targets for deterministic randomness
- **Result:** Conflict-free scheduling + realistic harvest variation

**🚀 Performance:**
- **100% success rate** (eliminated 7.5% failure rate)
- **14 parallel workers** (chronological partitioning prevents races)
- **Realistic variation:** Batches harvest at different weights/times
- **Higher utilization:** Early container freeing improves efficiency

**📊 Test Results:**
- Dry-run: ✅ Zero conflicts with weight-based modeling
- Execution: ✅ Deterministic harvest targets match between planning/execution
- Variation: ✅ Batches harvest at different times based on individual weight targets

**🎯 Commands:**
```bash
# Generate weight-aware schedule
python scripts/data_generation/generate_batch_schedule.py --batches 125 --output config/schedule_250.yaml

# Execute with deterministic harvest targets
python scripts/data_generation/execute_batch_schedule.py config/schedule_250.yaml --workers 14 --use-partitions
```

**✅ v6.0 Validation Results:**
- **100% success rate** (20/20 batches executed successfully)
- **Zero conflicts** (weight-aware planning prevents container contention)
- **Deterministic harvest targets** (planning and execution use identical random seeds)
- **Realistic variation** (different harvest times despite deterministic scheduling)

### ✅ v6.1: Production Hardening & Race Condition Elimination (2025-11-21)

**Status:** ✅ Production-ready, 144/144 batches (100% success), 88.7 minutes execution time

**Critical Fixes Applied:**
1. **Batch naming race condition:** Deterministic batch_id passed from schedule
2. **Workflow naming race conditions:** CRT-{batch_number}, TRF-{batch_number}-D{day} format
3. **Post-Smolt key mismatch:** Unified to 'post_smolt' (underscore)
4. **Adult transition sea schedule:** Added missing self.sea_schedule lookup
5. **Order-based stage lookups:** Replaced 56 hardcoded names with lifecycle_stage.order

**Key Technical Details:**

**Order-Based Stage Lookups:**
- All stage checks now use `lifecycle_stage.order` instead of hardcoded names
- Order: 1=Egg&Alevin, 2=Fry, 3=Parr, 4=Smolt, 5=Post-Smolt, 6=Adult
- Example: `if batch.lifecycle_stage.order == 6:` instead of `if batch.name == 'Adult':`
- Benefits: Robust to name changes, clearer progression logic, better for migrations

**Infrastructure Constraint Calculation:**
```python
# Time constraint
max_from_time = (years × 365) / (stagger × 2)  # 4 years, 13-day stagger = 112 batches/geo

# Infrastructure constraint (Scotland sea rings bottleneck)
rings_per_batch = 10  # Post-Smolt (10) → Adult (10) = 1:1 ratio
max_concurrent_adult = (400 × 0.85) / 10 = 34 concurrent Adult batches
batches_overlapping = 450 / 13 = 35 batches overlap in Adult stage

# Result: Infrastructure-limited (35 > 34)
# Actual: 72 batches/geo works with adaptive allocation
```

**Deterministic ID Strategy:**
- Batch numbers: Passed from schedule (FAR-2020-001, SCO-2025-072)
- Creation workflows: CRT-{batch_number} (e.g., CRT-FAR-2020-001)
- Transfer workflows: TRF-{batch_number}-D{day} (e.g., TRF-FAR-2020-001-D450)
- Eliminates all query-then-increment race conditions

**Result:** 100% stable, zero conflicts, ready for production use

### 🎯 **The Hybrid Approach: Why It Works**

**The Fundamental Tension Resolved:**

**❌ Old Problem:** Deterministic scheduling assumed fixed durations, but weight-based harvesting created unpredictable timing → container conflicts.

**✅ New Solution:** Weight-aware deterministic scheduling models harvest randomness during planning phase.

**How It Achieves Both:**

1. **Planning Phase (Conservative):**
   - Models harvest timing using TGC formula + random weight targets
   - Plans for worst-case scenario (highest weight target = longest duration)
   - Allocates containers with conflict detection → **100% deterministic success**

2. **Execution Phase (Realistic):**
   - Uses identical random weight targets as planning phase
   - Batches harvest at different times based on individual targets
   - Containers freed early when batches harvest before planned end → **higher utilization**

3. **Result:** **Predictable scheduling + realistic variation** in perfect harmony

**Example:**
- Batch A: Plans for 6.5kg target (500 days), actually harvests at 5.2kg (420 days)
- Batch B: Plans for 6.5kg target (500 days), actually harvests at 4.8kg (380 days)
- **No conflicts:** Planning accounted for maximum duration
- **Realistic variation:** Different harvest times despite deterministic planning

---

## 🎯 EXPECTED RESULTS

### Full Saturation (144 Batches, 72 per Geography) - AUTO-CALCULATED

**Batch Distribution:**
- **Total Batches:** 144 (auto-calculated from 4-year target + infrastructure constraints)
- **Completed/Harvested:** ~120 batches (>900 days old, full lifecycle)
- **Active Batches:** ~24 batches (various stages, partial data)
- **Geography Split:** 50/50 (72 Faroe + 72 Scotland)
- **Historical Span:** 5.2 years (2020-2025)

**Stage Distribution (Active Batches):**
- Egg&Alevin: ~4 batches
- Fry: ~4 batches
- Parr: ~4 batches
- Smolt: ~4 batches
- Post-Smolt: ~4 batches
- Adult: ~4 batches

**Data Volume:**
- **Environmental Readings:** ~50 million (6/day × 7 sensors × 10 containers × avg days)
- **Feeding Events:** ~8 million (2/day × 10 containers × feeding days)
- **Mortality Events:** ~800,000
- **Growth Samples:** ~400,000
- **Lice Counts:** ~50,000
- **Health Sampling Events:** ~3,000 (monthly, 75 fish)
- **Total Events:** ~60 million
- **Database Size:** 60-80 GB

**Container Utilization:**
- **Freshwater:** 65-70% utilized
- **Sea Rings:** 70% utilized (10 rings per batch, 144 batches)
- **Feed Inventory:** Continuously replenishing

**Constraint Calculation:**
- Time constraint: 4 years / 13-day stagger = 112 batches/geo possible
- Infrastructure constraint: 400 Scotland rings / 10 per batch = 34 concurrent Adult max
- With 450-day Adult stage: 450/13 = 35 batches overlap → infrastructure limited
- Result: 72 batches/geo = 144 total (fits within constraints)

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
| `01_initialize_scenario_master_data.py` | Scenario models + TGC | 30 sec | Once after infrastructure |
| `01_initialize_finance_policies.py` | Finance policies + DimSite | 30 sec | Once after infrastructure |
| `01_initialize_health_parameters.py` | Health parameters + scoring | 15 sec | Once after infrastructure |
| `03_event_engine_core.py` | Single batch generation | 2-3 min | Core engine (called by orchestrator) |
| `04_batch_orchestrator_parallel.py` | Multi-batch parallel generation | 1-2 hrs | Main production data generation |

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
- Auto-calculated from: `--years × 365 days` (default: 4 years = 1,460 days)
- With 13-day stagger: Spans 5.2 years (accounts for batch spread + buffer)
- For 72 batches/geo with 13-day stagger: Goes back to 2020-08-30
- Creates mix of completed + active batches

**Date-Bounded Execution:**
- Each batch runs: `min(900 days, days_since_start)`
- Old batches: Full 900-day cycle (completed, harvested)
- Recent batches: Partial cycle (active in various stages)

**Example (72 batches per geography with 13-day stagger):**
```
Batch 1:  Start 2020-08-30 → Duration 900 days → Completed ✅
Batch 60: Start 2022-11-25 → Duration 900 days → Completed ✅
Batch 65: Start 2023-08-15 → Duration 830 days → Active (Adult stage)
Batch 72: Start 2025-09-19 → Duration 63 days → Active (Fry)
```

**Infrastructure Constraint Formula:**
```python
# Time-based: How many batches fit in timespan?
max_from_time = (years × 365) / (stagger × 2)  # Divided by 2 for interleaved geos

# Infrastructure-based: Scotland sea rings are bottleneck
rings_per_batch = 10  # Post-Smolt (10) → Adult (10) = 1:1 ratio
max_concurrent_adult = (400 × saturation) / rings_per_batch
batches_would_overlap = adult_duration / stagger  # 450 / 13 = 35

# If overlap > capacity, infrastructure-limited
if batches_would_overlap > max_concurrent_adult:
    max_batches = max_concurrent_adult  # Infrastructure limit
else:
    max_batches = max_from_time  # Time limit

# For our setup: 35 overlap > 34 capacity → infrastructure-limited at 34 batches/geo
# But scheduler adjusts upward when testing shows it can fit more
```

### 2. Parallel Execution is I/O-Bound

**Don't expect 100% CPU utilization** - the bottleneck is:
- Database writes (Postgres transaction locks)
- Disk I/O (millions of records)
- Network overhead (if DB on remote host)

**Still provides 10-12x speedup** through concurrent I/O operations.

### 3. Growth Analysis Requires Scenarios

The Growth Assimilation Engine requires scenarios for TGC/mortality models:
- **Scenarios created at Day 1** with 760-day projection (reaches ~6kg harvest weight)
- Uses industry-standard cube-root TGC formula (Iwama & Tautz 1981)
- Stage-specific TGC values: Fry(2.25), Parr(2.75), Adult(3.1)
- Projects realistic S-curve growth avoiding theoretical weight caps
- All batches have scenarios immediately (no minimum age requirement)

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

### November 20, 2025 - Critical Bug Fixes & Feature Completion

**Problems Discovered:**
- 49 batches stuck in "PLANNED" status (should be COMPLETED/ACTIVE)
- 0 batches had pinned_scenario (scenarios existed but not pinned)
- 111 batches missing Growth Analysis data

**Root Cause:** Event engine didn't set status/pinning after batch operations

**Fixes Applied:**
1. `batch.status = 'COMPLETED'` after harvest (line ~1572)
2. `batch.pinned_scenario = scenario` after scenario creation (line ~1270)
3. Growth Analysis computed check improved (line ~1610)

**New Features Added:**
- Finance: Intercompany policies + DimSite creation
- Health: 9 parameters with monthly sampling (75 fish, 9 scores each)
- Treatments: 4 vaccinations + 2 lice treatments per batch

**Philosophy:** Test data scripts = migration prototypes. Fix at source, never backfill.

**Result:** All bugs fixed, health/finance fully integrated, 13 obsolete scripts removed.

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
# === WIPE DATA (Fast with SQL TRUNCATE) ===
psql aquamind_db -c "TRUNCATE TABLE batch_batch CASCADE; TRUNCATE TABLE inventory_feedpurchase CASCADE;"

# === ONE-TIME SETUP (Run once after infrastructure exists) ===
python scripts/data_generation/01_initialize_scenario_master_data.py   # TGC/temperature models
python scripts/data_generation/01_initialize_finance_policies.py       # Intercompany policies
python scripts/data_generation/01_initialize_health_parameters.py      # Health parameters

# === TEST GENERATION (20 batches) ===
# Step 1: Generate schedule
python scripts/data_generation/generate_batch_schedule.py \
  --batches 10 --stagger 30 --saturation 0.85 \
  --output config/test_20.yaml

# Step 2: Execute schedule (~10 minutes)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/test_20.yaml --workers 4 --use-partitions \
  --log-dir scripts/data_generation/logs/test

# === FULL PRODUCTION (144 batches, 5.2 years) ===
# Step 1: Generate schedule with auto-calculated batch count
python scripts/data_generation/generate_batch_schedule.py \
  --years 4 --stagger 13 --saturation 0.85 \
  --output config/schedule_production.yaml

# Step 2: Execute schedule (~45 minutes)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/schedule_production.yaml --workers 14 --use-partitions \
  --log-dir scripts/data_generation/logs/production

# === MANUAL BATCH (Standalone, for debugging) ===
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 --geography "Faroe Islands" --duration 200

# === VERIFICATION ===
python scripts/data_generation/verify_test_data.py
```

---

## 🎯 **READY FOR PRODUCTION - v4.0**

**Single Source of Truth** - Version 4.0  
**Last Updated:** 2025-11-20  
**Status:** All critical bugs fixed, health & finance integrated  
**Expected Data Volume:** 50M+ events for full saturation (includes health data)

**Key Improvements in v4.0:**
- ✅ All 3 root cause bugs fixed (status, pinning, Growth Analysis)
- ✅ Health monitoring: 9 parameters, monthly sampling, 75 fish
- ✅ Treatments: 4 vaccinations + 2 lice per batch
- ✅ Finance: Intercompany policies, DimSite, automatic projection
- ✅ Scripts cleaned: 13 obsolete scripts removed
- ✅ Migration-ready: No backfill scripts, all correct at source

**This guide contains everything needed for test data generation. No other documents required.**

---

## 🎯 **SUCCESS: v6.0 Hybrid Weight-Aware Deterministic Scheduling**

**Achieved:** 100% success rate with realistic harvest variation

**Solution:** Weight-aware deterministic pre-planning + execution-time harvest randomness

**Result:** Perfect balance of predictability and realism - the impossible made possible!

---

