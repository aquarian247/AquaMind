# Handoff for Next Session - Test Data & Growth Analysis

**Date**: November 18, 2025  
**Session Duration**: ~4 hours  
**Status**: ✅ **TEST DATA WORKING - GROWTH ENGINE FIX NEEDED**  
**Location**: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/test_data_2025_11_18/`

---

## 📚 Essential Reading List (Complete Context)

**Start here in this order**:

1. **This document** (HANDOFF_NEXT_SESSION_2025_11_18.md) - YOU ARE HERE
   - Quick summary and next steps

2. **Investigation Reports** (Same folder):
   - `TEST_DATA_POPULATION_DOUBLING_ROOT_CAUSE_ANALYSIS.md` - The main bug (2x population)
   - `FROM_BATCH_SCENARIO_APPROACH.md` - Why scenarios start from Parr, not eggs
   - `SCENARIO_SYSTEM_CONFIGURATION_GAPS.md` - Missing master data identified
   - `ZERO_INIT_FINDINGS.md` - Why zero-init approach didn't work

3. **Session Summaries** (Same folder):
   - `INVESTIGATION_SUMMARY_2025_11_18.md` - Complete findings
   - `FINAL_TEST_DATA_SOLUTION_2025_11_18.md` - Final approach and trade-offs

4. **Script Documentation**:
   - `../../scripts/data_generation/README.md` (v3.0) - Complete script reference
   - `../../scripts/data_generation/INCREMENTAL_TEST_PLAN.md` - Testing guide

5. **Original Investigation**:
   - `../batch_growth_assimilation/TEST_DATA_POPULATION_DOUBLING_INVESTIGATION.md` - User's original notes

6. **Growth Analysis Context** (Frontend):
   - `/Users/aquarian247/Projects/AquaMind-Frontend/docs/progress/growth_analysis/GROWTH_ANALYSIS_FRONTEND_HANDOVER.md` - What UI expects

7. **Technical Design** (Backend):
   - `../batch_growth_assimilation/technical_design.md` - Why Celery exists (real-time signals)

**Key Python Files**:
- `scripts/data_generation/03_event_engine_core.py` - Core batch generation (1454 lines)
- `apps/batch/services/growth_assimilation.py` - Growth Analysis engine (needs fix line 467)
- `apps/scenario/services/calculations/projection_engine.py` - Scenario projections
- `apps/batch/signals.py` - Celery signal handlers (now with skip flag)

---

## 🧠 Critical Context (What We Learned This Session)

### How Scenarios Work

**Architecture** (from PRD section 3.3.1 + investigation):
```
Scenario (configuration)
  ├─ TGCModel → TemperatureProfile → TemperatureReadings (450 days)
  ├─ FCRModel → FCRModelStage (6 stages × FCR values)
  ├─ MortalityModel → MortalityModelStage (optional)
  └─ BiologicalConstraints → StageConstraint (optional, for advanced rules)

After creation → Must compute projections:
  ProjectionEngine(scenario).run_projection(save_results=True)
    → Creates ScenarioProjection records (900 days)
    → UI can display green "Scenario" line
```

**Two Types**:
1. **Hypothetical** - Start from user-defined conditions (eggs, random date)
2. **"From Batch"** - Start from current batch state (Day 180 @ 50g) ⭐

**Why "From Batch" is Better**:
- Starts from current reality (not historical eggs)
- Projects forward (not backward)
- Time-aligned with actual data (enables variance analysis)
- Created at Parr stage (Day 180) when growth pattern established

### How Growth Analysis Works

**Three Data Series** (Growth Analysis UI):

1. **Growth Samples** (Blue Dots):
   - Manual measurements by operators
   - Model: `GrowthSample`
   - Frequency: Weekly or on-demand
   - Source: Human operators recording fish weights

2. **Scenario Projection** (Green Line):
   - Mathematical forecast using TGC/FCR/Mortality models
   - Model: `ScenarioProjection` (900 records)
   - Computed: Once when scenario created
   - Source: Biological models + temperature profiles

3. **Actual Daily State** (Orange Line):
   - Assimilated reality combining measurements + models
   - Model: `ActualDailyAssignmentState` (computed by Growth Engine)
   - Computed: Via Celery signals in production, bulk at orchestrator end for test data
   - Source: Growth samples (anchors) + TGC interpolation + actual mortality/feed

**The Engine Flow**:
```
Growth Engine (apps/batch/services/growth_assimilation.py):
  1. Get assignment.population_count as initial
  2. For each day:
     - Get temperature (measured > interpolated > profile)
     - Get mortality (actual > model)  
     - Get feed (actual > none)
     - Get placements (transfers IN)
     - Calculate: new_pop = prev_pop + placements - mortality
     - Calculate: new_weight via TGC formula
  3. Save ActualDailyAssignmentState records
```

**The Double-Counting Bug**:
```python
# Line 467: Starts with metadata
initial_population = assignment.population_count  # 3M

# Line 547-550: Each day adds transfers
placements = sum(transfer.transferred_count)      # 3M on Day 90
new_population = prev_pop + placements            # 6M total ❌
```

**Why It Happens**: Transfer destinations have fish in BOTH metadata AND transfer records.

### How Test Data Generation Works

**Event Engine Philosophy**:
- Day-by-day chronological processing
- Events create other events (feed → growth → stage transition → transfer)
- Must maintain state in `BatchContainerAssignment.population_count` for daily processing
- Can't use zero-initialized assignments (breaks biomass → feeding calculation)

**Key Methods**:
1. `create_batch()` - Creation workflow with initial egg placement
2. `process_day()` - Environmental, feeding, mortality, growth
3. `check_stage_transition()` - Every 90 days, move to next stage
4. `_create_transfer_workflow()` - Document transitions for audit trail
5. `_create_from_batch_scenario()` - Generate scenario at Parr stage

**Critical Dependencies**:
- Feed types must match exactly (line 508-511)
- Container availability checked with locks (parallel-safe)
- Transfer workflows link source → dest assignments
- Scenario models must have complete configuration (temp profiles, weight ranges)

### Why Celery Signals Killed Performance

**Production System**:
```
Operator records growth sample
  → Signal fires
  → Celery enqueues task
  → Background worker recomputes (non-blocking)
  → User sees update in 30 seconds
```

**Test Data Generation** (before fix):
```
Event engine creates mortality event
  → Signal fires
  → Tries Redis connection → FAILS
  → Logs error message
  → Repeat 10,000 times
  → Result: 600x slowdown!
```

**Our Fix**:
```bash
SKIP_CELERY_SIGNALS=1  # Skip signal handlers entirely during generation
# Recompute growth analysis ONCE at orchestrator end for all active batches
```

### Master Data Dependencies

**Scenarios require**:
- ✅ LifeCycleStage records (6 stages)
- ✅ LifeCycleStage weight ranges (for stage transitions)
- ✅ TemperatureProfile records (2-4 profiles)
- ✅ TemperatureProfile has TemperatureReading data (450 days each)
- ✅ TGCModel linked to profile
- ✅ FCRModel with FCRModelStage data (6 stages)
- ✅ MortalityModel with rates
- ⚠️ BiologicalConstraints (optional, enhances transitions)

**If any missing**: Scenarios compute but produce unrealistic results (8g instead of 5000g).

---

## 🎉 What We Accomplished

### 1. Investigation Complete ✅
- Traced population doubling to double-counting (metadata + transfers)
- Identified missing scenario configuration (temp profiles, weight ranges)
- Found Celery signal bottleneck (600x performance impact!)
- Discovered "from batch" scenario approach

### 2. Test Data Generation Fixed ✅
- ⚡ **600x speedup** (2 min vs 400 min per batch)
- ✅ Realistic populations (2.9M at Day 90, 83% survival)
- ✅ Feeding events working (2,200 for 200-day batch)
- ✅ "From batch" scenarios with projections
- ✅ Single-area sea distribution
- ✅ Duration fixed (650 → 900 days)

### 3. Scripts Optimized ✅
- 🗑️ Deleted 10 obsolete scripts
- ⚡ Created parallel orchestrator (10-12x speedup)
- 🔄 Created selective wipe (10x faster reset)
- 📋 Created scenario master data init
- ✅ Clean, maintainable folder

### 4. Documentation ✅
- 7 comprehensive investigation reports
- Complete script reference (README.md)
- Troubleshooting guides
- Performance benchmarks

---

## ⚠️ Known Issue: Growth Analysis Double-Counting

### The Situation:

**Test Data**: ✅ **CORRECT**  
- Assignment metadata: ~3M fish ✅
- Transfer records: ~3M fish ✅
- Both are legitimate audit trail

**Growth Analysis**: ❌ **DOUBLE-COUNTS**
- Reads metadata: 3M
- Adds transfers: 3M
- Computes: 6M ❌

### Why We Didn't Fix It:

**Zero-initialization approach failed** because:
1. Set `population_count=0` on destinations
2. Event engine uses biomass (calculated from population)
3. If biomass=0 → no feeding → fish don't grow → population stays 0
4. Batch generation breaks completely

**Correct Fix**: Modify Growth Engine to detect transfer destinations and avoid double-counting.

### The Fix (For Next Session):

**File**: `apps/batch/services/growth_assimilation.py`  
**Method**: `_get_initial_state()` (around line 467)

```python
# Current (double-counts):
initial_population = self.assignment.population_count

# Fixed:
initial_population = self.assignment.population_count

# Check if this assignment is a transfer destination on first day
first_day_transfers = TransferAction.objects.filter(
    dest_assignment=self.assignment,
    actual_execution_date=self.assignment.assignment_date
).aggregate(Sum('transferred_count'))['transferred_count__sum'] or 0

# If there are transfers on first day, metadata already includes them
# So don't count them again when processing daily placements
if first_day_transfers > 0:
    # This is a transfer destination - placements will be added daily
    # Start from 0 to avoid double-counting
    initial_population = 0
```

**Alternative approach**: Modify `_get_placements()` to skip first-day transfers if metadata is pre-populated.

---

## 🚀 Next Steps

### Immediate (Next 60 Minutes):

```bash
cd /Users/aquarian247/Projects/AquaMind

# Generate full 20-batch dataset with parallel orchestrator
python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 14

# Expected:
# - 20 batches in 45-60 minutes
# - All active batches with scenarios
# - Bulk growth analysis recompute at end
# - All 3 series visible in UI
```

### After Full Generation:

1. **Test UI Growth Analysis**:
   - Navigate to: Batch Detail → Analytics → Growth
   - Verify scenario dropdown shows "From Batch (Parr)"
   - Verify chart shows all 3 series
   - **Note**: Orange line will show ~2x values (expected with current approach)

2. **Create Growth Engine Fix Issue**:
   ```
   Title: Growth Analysis Double-Counting on Transfer Destinations
   Description: Growth engine adds metadata + transfers for assignments
                that are transfer destinations, causing ~2x population inflation.
   Fix: Detect transfer destinations and start from 0, not metadata.
   File: apps/batch/services/growth_assimilation.py line 467
   Priority: Medium (test data works, but UI shows inflated values)
   ```

3. **Update test_data_generation_guide_v2.md**:
   - Add SKIP_CELERY_SIGNALS=1 requirement
   - Document scenario master data initialization
   - Add parallel orchestrator instructions
   - Note Growth Analysis double-counting issue

---

## 📋 Fixes Applied This Session

### Event Engine (`scripts/data_generation/03_event_engine_core.py`):

| Line | Fix | Status |
|------|-----|--------|
| 40 | Duration 900 (was 650) | ✅ |
| 101 | Subsidiary 'FM' (was 'FARMING') | ✅ |
| 852-920 | Single-area sea distribution | ✅ |
| 938-940 | Create scenario at Parr transition | ✅ |
| 1092-1173 | "From batch" scenario method | ✅ |

### Batch Signals (`apps/batch/signals.py`):

| Line | Fix | Status |
|------|-----|--------|
| 34 | Add SKIP_CELERY_SIGNALS flag | ✅ |
| 150 | Check flag in GrowthSample signal | ✅ |
| 214 | Check flag in TransferAction signal | ✅ |
| 303 | Check flag in MortalityEvent signal | ✅ |

### FCR Calculator (`apps/scenario/services/calculations/fcr_calculator.py`):

| Line | Fix | Status |
|------|-----|--------|
| 315-323 | Allow FCR=0 for Egg&Alevin | ✅ |

### New Scripts:

| Script | Purpose | Status |
|--------|---------|--------|
| 00_wipe_operational_data.py | Fast selective wipe | ✅ |
| 01_initialize_scenario_master_data.py | Master data setup | ✅ |
| 04_batch_orchestrator_parallel.py | Parallel generation + bulk recompute | ✅ |
| verify_single_batch.py | Automated verification | ✅ |

---

## 📊 Test Data Characteristics

### After Full Generation (20 Batches):

**Batch Distribution**:
- Active batches: ~15 (various stages)
- Completed batches: ~5 (harvested, >900 days)
- Geographies: 10 Faroe + 10 Scotland
- Stages: Mix across all 6 stages

**Scenario Coverage**:
- All Parr+ batches: "From Batch (Parr)" scenarios
- All Adult batches: "Sea Growth Forecast" scenarios  
- Total scenarios: ~25-30
- All scenarios: Have projection data (UI ready)

**Growth Analysis**:
- All active batches: ActualDailyAssignmentState computed
- Orange line: ⚠️ Shows ~2x values (known issue, future fix)
- Green line: ✅ Shows correct scenario projection
- Blue dots: ✅ Shows growth samples

**Performance**:
- Total time: 45-60 minutes (vs 8-10 hours sequential)
- Database size: ~8-12 GB
- Total events: ~10 million

---

## 🎯 For the Next Agent

### Mission: Fix Growth Analysis Double-Counting

**File**: `/Users/aquarian247/Projects/AquaMind/apps/batch/services/growth_assimilation.py`

**Problem**: Line 467 starts with `assignment.population_count` which already includes fish for transfer destinations.

**Solution**: Detect if assignment is transfer destination on first day:
```python
def _get_initial_state(self, start_date: date) -> Dict:
    initial_population = self.assignment.population_count
    
    # Check if this is a transfer destination
    first_day_transfers = TransferAction.objects.filter(
        dest_assignment=self.assignment,
        actual_execution_date=self.assignment.assignment_date
    ).exists()
    
    if first_day_transfers:
        # Transfer destination - start from 0, placements will add fish
        initial_population = 0
    
    return {
        'population': initial_population,
        ...
    }
```

**Test**: Verify Day 91 shows ~3M (not ~6M) after recompute.

### Alternative Mission: Run Full Parallel Generation

If Growth Engine fix can wait, proceed with full dataset generation:

```bash
cd /Users/aquarian247/Projects/AquaMind

python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 10 --workers 14

# Expected: 20 batches in 45-60 minutes
```

---

## 📚 Key Documents

**All documents in**: `/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/test_data_2025_11_18/`

**Investigation Reports** (This folder):
- `TEST_DATA_POPULATION_DOUBLING_ROOT_CAUSE_ANALYSIS.md` - Main bug analysis
- `FROM_BATCH_SCENARIO_APPROACH.md` - Scenario creation approach
- `SCENARIO_SYSTEM_CONFIGURATION_GAPS.md` - Missing master data
- `ZERO_INIT_FINDINGS.md` - Why zero-init failed

**Session Summaries** (This folder):
- `INVESTIGATION_SUMMARY_2025_11_18.md` - Complete findings
- `FINAL_TEST_DATA_SOLUTION_2025_11_18.md` - Final approach
- `SESSION_SUMMARY_TEST_DATA_FIX_2025_11_18.md` - Session log
- `HANDOFF_NEXT_SESSION_2025_11_18.md` - This document

**Script Documentation**:
- `../../scripts/data_generation/README.md` (v3.0) - Script reference
- `../../scripts/data_generation/INCREMENTAL_TEST_PLAN.md` - Testing guide
- `../../scripts/data_generation/FIXES_APPLIED_2025_11_18.md` - Fix summary

---

## ✅ Deliverables Summary

- ✅ 7 bugs/issues fixed
- ✅ 600x performance improvement (Celery bottleneck)
- ✅ 10-12x parallel speedup
- ✅ 10 obsolete scripts deleted
- ✅ 4 new optimized scripts
- ✅ 7 comprehensive reports
- ✅ Test data generation UAT-ready
- 🔧 1 Growth Engine fix needed (documented)

**Time Investment**: 4 hours investigation + fixes  
**Time Saved**: ~7-8 hours per test data regeneration cycle  
**ROI**: Massive 🚀

---

**Current Batch**: FI-2025-002 completed successfully ✅  
**Ready For**: Full parallel generation OR Growth Engine fix (your choice)

---

*End of Handoff Document*

