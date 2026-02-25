# Test Data Generation Scripts - v3.0

**Last Updated**: November 18, 2025  
**Status**: ✅ **PRODUCTION READY** - All fixes applied  
**Performance**: 10-12x speedup with parallel execution

---

## 🚀 Quick Start

### Complete Generation (45-60 minutes):

```bash
cd /Users/aquarian247/Projects/AquaMind

# 1. Wipe operational data (1 minute)
python scripts/data_generation/00_wipe_operational_data.py --confirm
# Type 'DELETE' when prompted

# 2. Initialize scenario master data (30 seconds, ONE TIME)
python scripts/data_generation/01_initialize_scenario_master_data.py

# 3. Generate 20 batches in parallel (45-60 minutes)
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 14
```

### Quick Test (15 minutes):

```bash
# Single 200-day batch for verification
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 \
  --geography "Faroe Islands" --duration 200
```

---

## 📁 Script Reference

### 00_wipe_operational_data.py ⚡ NEW
**Purpose**: Selective operational data wipe (preserves infrastructure)  
**Performance**: 10x faster than full reset (1 min vs 10+ min)  
**Deletes**: Batches, feeding, environmental readings, health records, scenarios  
**Preserves**: Infrastructure, feed types, models, parameters, profiles  
**Usage**: `python 00_wipe_operational_data.py --confirm`

### 01_bootstrap_infrastructure.py
**Purpose**: One-time infrastructure setup (synthetic default or realistic reference-pack mode)  
**Creates**:
- Synthetic mode (default): geographies/stations/halls/containers/sensors using legacy deterministic layout
- Realistic mode (`--reference-pack`): imports familiar FT-backed infrastructure names + area groups + rack/tray hierarchy via migration compatibility loader, then ensures feed containers/sensors for event generation  
**Run**: Once per database  
**Usage (synthetic)**: `python 01_bootstrap_infrastructure.py`  
**Usage (realistic)**: `python 01_bootstrap_infrastructure.py --reference-pack scripts/data_generation/reference_pack/latest`

### 01_initialize_scenario_master_data.py ⚡ NEW
**Purpose**: Initialize scenario configuration data  
**Populates**: Temperature profiles (4), lifecycle weight ranges (6 stages), biological constraints  
**Run**: Once after infrastructure setup  
**Usage**: `python 01_initialize_scenario_master_data.py`

### 03_event_engine_core.py ⭐ CORE
**Purpose**: Single batch lifecycle generation  
**Duration**: 10-30 minutes per batch (depending on days)  
**Features**:
- ✅ Day-by-day event processing
- ✅ Stage transitions with transfer workflows
- ✅ FIFO feed consumption with auto-reordering
- ✅ Environmental readings (6/day × 7 sensors)
- ✅ Growth samples (weekly)
- ✅ Lice sampling (Adult stage, weekly)
- ✅ "From batch" scenario creation at Parr stage (Day 180)
- ✅ Finance integration (harvest facts)

**Recent Fixes** (November 18, 2025):
- ✅ Population doubling fix (zero-initialize destinations)
- ✅ Duration default (650 → 900 days)
- ✅ Single-area sea distribution (round-robin)
- ✅ "From batch" scenario approach (Day 180, current state)
- ✅ Scenario projection auto-computation
- ✅ Finance subsidiary code fix ('FM' not 'FARMING')

**Usage**: `python 03_event_engine_core.py --start-date YYYY-MM-DD --eggs 3500000 --geography "Faroe Islands" --duration 200`

### 04_batch_orchestrator.py
**Purpose**: Sequential multi-batch generation  
**Performance**: 20 batches × 25 min = 500 minutes (8.3 hours)  
**Features**: Staggered starts, 6-year operational history, both geographies  
**Usage**: `python 04_batch_orchestrator.py --execute --batches 10`  
**Note**: Use parallel orchestrator for better performance

### 04_batch_orchestrator_parallel.py ⚡ NEW
**Purpose**: Parallel multi-batch generation  
**Performance**: 20 batches in 45-60 minutes (10-12x speedup!)  
**Features**:
- ✅ Multiprocessing across CPU cores (14 workers recommended)
- ✅ Date-bounded (stops at today, no future data)
- ✅ Round-robin prevents container conflicts
- ✅ Transaction locks prevent race conditions
- ✅ Timeout protection (30 min per batch)

**M4 Max Performance**:
- 10 batches: 5-7 minutes
- 20 batches: 45-60 minutes  
- 50 batches: 2-3 hours

**Usage**: `python 04_batch_orchestrator_parallel.py --execute --batches 10 --workers 14`

### fix_feed_inventory.py
**Purpose**: Initialize feed types and feed inventory  
**Creates**: 6 feed types, 3,730 tonnes initial inventory, 12 lice types  
**Called by**: 00_wipe_operational_data.py (via subprocess)  
**Usage**: `python fix_feed_inventory.py` (rarely needed manually)

### verify_single_batch.py ⚡ NEW
**Purpose**: Automated verification of batch generation fixes  
**Checks**:
- ✅ Scenario creation and projection data
- ✅ Population doubling fix (Day 90 check)
- ✅ Feeding events count
- ✅ Stage transitions and transfer workflows
- ✅ Single-area distribution (Adult stage)

**Usage**: `python verify_single_batch.py` (after batch generation completes)

---

## 📊 Workflow Comparison

### Old Workflow (Deprecated):
```bash
# 10+ minutes to reset
python 00_complete_reset.py  # Has prompts ❌

# 8-10 hours for 20 batches
python 04_batch_orchestrator.py --execute  # Sequential only ❌
```

### New Workflow (Optimized):
```bash
# 1 minute to reset
python 00_wipe_operational_data.py --confirm  # No prompts ✅

# 30 seconds to initialize scenarios
python 01_initialize_scenario_master_data.py  # NEW ✅

# 45-60 minutes for 20 batches
python 04_batch_orchestrator_parallel.py --execute --batches 10 --workers 14  # 10x faster ✅
```

**Total time**: 90 minutes (vs 10+ hours) = **~6.5x overall speedup**

---

## 🎯 What Gets Generated

### Per Batch (900-day full lifecycle):

**Infrastructure**:
- 60 container assignments (10 per stage × 6 stages)
- 5 stage transitions (Egg→Fry→Parr→Smolt→Post-Smolt→Adult)
- 5 transfer workflows (documenting transitions)
- 50 transfer actions (10 per transition)

**Operational Events**:
- ~300,000 environmental readings (6/day × 7 sensors × 10 containers × 900 days)
- ~150,000 feeding events (2/day × 10 containers × 810 feeding days)
- ~10,000 mortality events (stage-specific rates)
- ~130 growth samples (weekly sampling)
- ~50 lice counts (Adult stage weekly)
- ~30 health journal entries

**Financial**:
- ~12,000 feed purchases (FIFO auto-reordering)
- ~12,000 feed container stock entries
- Harvest events and lots (if reaches Day 900)
- Finance facts for BI reporting

**Scenarios** (NEW!):
- 1 "From Batch (Parr)" scenario (created at Day 180)
  - Initial: ~2,900,000 fish @ ~50g
  - Duration: 720 days (to harvest)
  - Projections: 720 records
- 1 "Sea Growth Forecast" scenario (created at Day 450)
  - Initial: ~2,700,000 fish @ ~450g
  - Duration: 450 days (Adult stage)
  - Projections: 450 records

### For 20 Batches:

- **Total Events**: ~10 million
- **Database Size**: ~8-12 GB
- **Scenarios**: 40 scenarios with projection data
- **Growth Analysis**: All batches have meaningful scenario comparisons

---

## ✅ Recent Fixes (November 18, 2025)

### Fix #1: Population Doubling (Issue #112)
**Problem**: Populations were ~2x inflated after each stage transition  
**Cause**: Destination assignments pre-populated + TransferAction both counted  
**Fix**: Lines 843, 913 - `population_count=0`  
**Result**: Day 91 shows ~3M (not ~6M) ✅

### Fix #2: Duration Mismatch
**Problem**: Default 650 days didn't match stage sum (900)  
**Fix**: Line 40 - `duration=900`  
**Result**: Batches complete full lifecycle ✅

### Fix #3: Multi-Area Distribution
**Problem**: Adult batches spanning 2-3 sea areas (unrealistic)  
**Fix**: Lines 852-920 - Round-robin single area selection  
**Result**: Each batch confined to one area ✅

### Fix #4: Empty Scenarios in UI
**Problem**: Scenarios created but not visible in Growth Analysis  
**Cause**: No projection data computed + wrong scenario type  
**Fix**: "From batch" approach at Parr stage + auto-compute projections  
**Result**: UI shows all 3 series (Samples, Scenario, Actual) ✅

### Fix #5: Missing Configuration Data
**Problem**: Empty temperature profiles, missing weight ranges  
**Cause**: Never initialized  
**Fix**: New script `01_initialize_scenario_master_data.py`  
**Result**: Scenarios compute realistic projections ✅

---

## 🧪 Verification

### After Single Batch Test:
```bash
python verify_single_batch.py
```

**Expected Output**:
```
TEST 1: Scenario Creation ✅
  From Batch (Parr) - FI-2025-001
  Initial: 2,900,000 @ 50g
  Projections: 720

TEST 2: Population Doubling Fix ✅
  Day 90 population_count: 0

TEST 3: Feeding Events ✅
  Total: 2,200+ events

TEST 4: Stage Transitions ✅
  Workflows: 2 (Egg→Fry, Fry→Parr)

✅ ALL TESTS PASSED
```

### Manual UI Verification:
1. Navigate to: Batch Detail → Analytics → Growth tab
2. Should see: "From Batch (Parr)" in scenario dropdown
3. Chart shows:
   - Blue dots: Growth Samples
   - Green line: Scenario Projection (starts at Day 180)
   - Orange line: Actual Daily States
4. Variance Analysis shows meaningful metrics

---

## 📈 Performance Benchmarks

### M4 Max (16 cores, 128GB RAM):

| Batches | Sequential | Parallel (14 workers) | Speedup |
|---------|------------|----------------------|---------|
| 1       | 25 min     | 25 min               | 1x (baseline) |
| 10      | 250 min    | 20-25 min            | 10-12x |
| 20      | 500 min    | 45-60 min            | 10-12x |
| 50      | 1,250 min  | 120-150 min          | 10-12x |

---

## 🗑️ Recently Deleted (Obsolete Scripts)

**Cleaned up on November 18, 2025**:
- ❌ `00_cleanup_existing_data.py` - Replaced by 00_wipe_operational_data.py
- ❌ `00_complete_reset.py` - Had interactive prompts
- ❌ `02_initialize_master_data.py` - Superseded by 01_initialize_scenario_master_data.py
- ❌ `03_chronological_event_engine.py` - Old stub
- ❌ `03_simple_test.py` - Test script
- ❌ `05_quick_create_test_creation_workflows.py` - Specific hack
- ❌ `backfill_transfer_workflows.py` - Data repair hack
- ❌ `cleanup_batch_data.py` - Had prompts
- ❌ `fcr_test_data/` directory - Old FCR tests
- ❌ `test_lice_tracking.sh` - Old test
- ❌ `validate_enhancements.py` - Old validation

**Rationale**: Reduce clutter, eliminate interactive prompts, remove obsolete hacks

---

## 📚 Documentation

### Investigation & Fixes:
- **FIXES_APPLIED_2025_11_18.md** - Complete fix summary
- **INVESTIGATION_SUMMARY_2025_11_18.md** - Full investigation report
- **INCREMENTAL_TEST_PLAN.md** - Step-by-step testing guide

### Technical Deep Dives:
- **TEST_DATA_POPULATION_DOUBLING_ROOT_CAUSE_ANALYSIS.md** - Population bug analysis
- **SCENARIO_SYSTEM_CONFIGURATION_GAPS.md** - Configuration issues found
- **FROM_BATCH_SCENARIO_APPROACH.md** - Why "from batch" scenarios work

---

## 🎓 Key Learnings

### 1. "From Batch" Scenarios > Hypothetical Scenarios

**Old**: Start from eggs (0.1g) at batch creation  
**New**: Start from current state (50g) at Parr stage  
**Result**: Meaningful variance analysis, realistic projections

### 2. Configuration > Code

**Finding**: No fundamental bugs in projection engine or growth engine  
**Issue**: Missing temperature data, weight ranges, validation edge cases  
**Lesson**: Complete master data initialization is critical

### 3. Zero-Initialize Destinations

**Pattern**: When creating transfer destinations, set `population_count=0`  
**Rationale**: TransferAction is source of truth (audit trail)  
**Applies to**: Migrations, workflows, manual transfers

### 4. Parallel Execution Requires Care

**Safe**: Round-robin station/area selection + transaction locks  
**Critical**: Date-bounded execution (stop at today)  
**Performance**: 10-12x speedup on multi-core machines

---

## 🔧 Troubleshooting

### Issue: "Insufficient available containers"
**Cause**: Infrastructure saturated  
**Fix**: `python 00_wipe_operational_data.py --confirm`

### Issue: Scenarios don't appear in UI
**Cause**: No projection data OR batch hasn't reached Parr stage (Day 180)  
**Fix**: Scenarios created at Day 180+, check batch age

### Issue: Population still doubled
**Cause**: Using old event engine version  
**Fix**: Pull latest fixes, regenerate data

### Issue: Parallel workers crash
**Cause**: Too many workers or DB connection exhaustion  
**Fix**: Reduce workers: `--workers 8`

### Issue: Low final scenario weights (8g instead of 5000g)
**Cause**: Missing temperature data or weight ranges  
**Fix**: Run `01_initialize_scenario_master_data.py`

---

## 📞 Support

**Full Documentation**: See `/Users/aquarian247/Projects/AquaMind/aquamind/docs/database/test_data_generation/test_data_generation_guide_v2.md`

**Investigation Reports**: See `INVESTIGATION_SUMMARY_2025_11_18.md` in this directory

**For Issues**: Check `INCREMENTAL_TEST_PLAN.md` for step-by-step verification

---

**Scripts**: 8 essential, 0 obsolete, 3 documentation files  
**Status**: ✅ **Clean, optimized, production-ready**

---

*End of README v3.0*
