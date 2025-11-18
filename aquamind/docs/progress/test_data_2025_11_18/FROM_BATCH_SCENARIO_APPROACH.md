# "From Batch" Scenario Approach for Growth Analysis

**Date**: November 18, 2025  
**Issue**: #112 - Growth Analysis Scenario Integration  
**Insight**: User suggestion to use "from batch" instead of "hypothetical" scenarios

---

## 🎯 The Breakthrough Insight

**Problem**: Scenarios starting from eggs (0.1g) at batch start date don't provide meaningful growth analysis comparison.

**Solution**: Use "from batch" scenarios that start from **current batch state** and project **forward**.

---

## ❌ Old Approach (Hypothetical Scenario)

### What We Were Doing:

```python
# At batch creation (Day 0):
Scenario.objects.create(
    name="Planned Growth - FI-2025-001",
    start_date=batch.start_date,     # Historical (e.g., Jan 1, 2025)
    initial_count=3,500,000,          # Eggs
    initial_weight=0.1,               # Egg weight
    duration_days=900                 # Full lifecycle
)
```

### Why It Didn't Work:

1. **Starts from eggs** (0.1g) - requires 900 days to reach harvest weight
2. **Historical start date** - projects from the past, not the present
3. **Weight-based stage transitions** - gets stuck in early stages (8.4g at Day 900)
4. **Not comparable** - batch is at Day 180 (50g), scenario shows Day 180 at 0.5g (different trajectories!)

### Result:

```
Growth Analysis Chart:
  Actual (orange):   Day 180 @ 50g ✅
  Scenario (green):  Day 180 @ 0.5g ❌ (meaningless comparison!)
```

---

## ✅ New Approach ("From Batch" Scenario)

### What We're Now Doing:

```python
# At Parr stage transition (Day 180):
current_pop = sum(a.population_count for a in assignments)  # e.g., 2,900,000
current_weight = assignments[0].avg_weight_g                 # e.g., 50g

Scenario.objects.create(
    name="From Batch (Parr) - FI-2025-001",
    start_date=current_date,          # TODAY (e.g., June 30, 2025)
    initial_count=current_pop,        # Current population (not eggs!)
    initial_weight=float(current_weight),  # Current weight (not 0.1g!)
    duration_days=720,                # Remaining lifecycle (900 - 180)
    batch=batch
)
```

### Why This Works:

1. **Starts from current state** (50g at Parr) - realistic growth trajectory
2. **Projects forward** - "where will this batch be in 6 months?"
3. **Time-aligned** - scenario Day 0 = batch Day 180
4. **Meaningful comparison** - both lines start from same point, diverge based on performance

### Result:

```
Growth Analysis Chart (both lines start at same point):
  Actual (orange):   Day 180 @ 50g → Day 450 @ 480g (actual performance)
  Scenario (green):  Day 180 @ 50g → Day 450 @ 500g (planned trajectory)
  
Variance Analysis:
  Current variance: -20g (-4.0%) ← Batch underperforming
```

---

## 📊 Comparison: Old vs New

### Old (Hypothetical from Eggs):

| Metric | Value | Issue |
|--------|-------|-------|
| Start point | Eggs (0.1g) | Not current state |
| Start date | Batch creation | Historical |
| Duration | 900 days | Full lifecycle from past |
| Final weight | 8.4g @ Day 900 | Unrealistic (stuck in early stages) |
| UI value | Low | Can't compare actual vs planned |

### New (From Batch at Parr):

| Metric | Value | Benefit |
|--------|-------|---------|
| Start point | Current (50g) | Matches actual state |
| Start date | Today | Forward-looking |
| Duration | 720 days | Remaining lifecycle |
| Final weight | ~5000g @ Day 720 | Realistic harvest weight |
| UI value | High | Meaningful variance analysis |

---

## 🎬 When Scenarios Are Created

### Trigger Point: Parr Stage Transition (Day 180)

**Why Parr?**
- Batch has established growth pattern (3 stages complete)
- Significant time remaining (720 days to harvest)
- Critical decision point (planning for sea transfer at Day 270)
- Meaningful baseline for performance comparison

**What Happens:**
```
Day 180: Fry → Parr transition
  1. Close Fry assignments
  2. Create Parr assignments  
  3. Create transfer workflow
  4. 🆕 Create "from batch" scenario:
     - Initial: 2,900,000 fish @ 50g
     - Project: 720 days to harvest
     - Compute: 720 projection records
  5. Update batch stage to Parr
```

### Additional Scenario: Adult Stage (Day 450)

**Sea transition scenario** already uses "from batch" approach (line 1175):
- Starts from Post-Smolt population and weight
- Projects 450 days in Adult stage
- Gives forecast for sea farming operations

### Result: Multiple Scenarios Per Batch

Each batch will have:
1. **"From Batch (Parr)"** - Created at Day 180, projects to harvest
2. **"Sea Growth Forecast"** - Created at Day 450, projects Adult stage only

Users can compare:
- Actual performance vs mid-lifecycle forecast (Parr scenario)
- Sea-stage performance vs sea-specific forecast (Adult scenario)

---

## 🧪 Test Data Benefits

### For 200-Day Test Batch:

```
Day 0-90:   Egg&Alevin (no scenario yet)
Day 91-180: Fry (no scenario yet)
Day 181-200: Parr:
  ✅ "From Batch (Parr)" scenario created at Day 180
  ✅ Projects 720 days forward (to Day 900)
  ✅ UI shows green line from Day 180 onward
  ✅ Variance analysis compares Days 181-200
```

### For Full 900-Day Batch:

```
Day 0-180:   Early stages (no scenario)
Day 180-450: "From Batch (Parr)" scenario active
  ✅ Shows mid-lifecycle forecast
  
Day 450-900: "Sea Growth Forecast" scenario added
  ✅ Shows two scenarios (can toggle in UI)
  ✅ Compare Parr forecast vs Adult forecast
```

---

## 🎨 UI Impact

### Growth Analysis Chart - Before:

```
No scenario line (empty projections) ❌
```

### Growth Analysis Chart - After:

```
Blue dots:   Growth samples (actual measurements)
Orange line: Actual Daily States (assimilated reality)
Green line:  Scenario Projection (from batch @ Parr) ✅
  - Starts at Day 180 (current batch state)
  - Projects to Day 900 (expected harvest)
  - Enables variance analysis
```

### Variance Analysis - Before:

```
No scenario → no variance calculation ❌
```

### Variance Analysis - After:

```
Current Variance:  -4.2g (-2.1%) ← Batch slightly underperforming
Average Variance:  +1.8g (+0.9%) ← Overall tracking well
Maximum Variance:  -15.3g on Day 350 ← Significant dip, investigate
```

---

## 📋 Implementation Summary

### Changes Made:

1. **Removed** initial scenario creation at batch start (Day 0)
2. **Added** from-batch scenario creation at Parr transition (Day 180)
3. **Updated** `_create_from_batch_scenario()` method to use current state
4. **Kept** sea transition scenario (already using from-batch approach)

### Files Modified:

- `scripts/data_generation/03_event_engine_core.py`:
  - Line 431: Removed `_create_initial_scenario()` call
  - Lines 938-940: Added Parr-stage scenario creation
  - Lines 1092-1173: New `_create_from_batch_scenario()` method
  - Lines 1175-1204: Updated sea scenario with projection computation

---

## ✅ Expected Outcomes

### After Regenerating Test Data:

1. **Batches < Day 180**: No scenario (too early for meaningful forecast)
2. **Batches at Day 180+**: "From Batch (Parr)" scenario with 720-day projection
3. **Batches at Day 450+**: Both Parr and Adult scenarios
4. **Growth Analysis UI**: All 3 series visible (Samples, Scenario, Actual)
5. **Variance Analysis**: Meaningful comparisons showing performance gaps

### Projection Quality:

- Starting from 50g (not 0.1g) → stage transitions work correctly
- 720 days Parr→Adult growth → realistic final weight (~5000g)
- Time-aligned with actual data → accurate variance calculations

---

## 🚀 Next Steps

### Immediate:
1. ✅ "From batch" approach implemented
2. [ ] Kill current batch generation (still using old approach)
3. [ ] Wipe operational data
4. [ ] Regenerate with new approach
5. [ ] Verify scenario appears in UI at Day 180+

### Testing Workflow:

```bash
# 1. Wipe and prepare
python scripts/data_generation/00_wipe_operational_data.py --confirm
python scripts/data_generation/01_initialize_scenario_master_data.py

# 2. Generate batch that reaches Parr (200 days minimum)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2025-01-01 --eggs 3500000 \
  --geography "Faroe Islands" --duration 200

# 3. Verify scenario created at Day 180
python manage.py shell -c "
from apps.batch.models import Batch
from apps.scenario.models import Scenario, ScenarioProjection

batch = Batch.objects.latest('created_at')
scenarios = Scenario.objects.filter(batch=batch)

for s in scenarios:
    print(f'Scenario: {s.name}')
    print(f'  Start date: {s.start_date}')
    print(f'  Initial: {s.initial_count:,} @ {s.initial_weight}g')
    print(f'  Projections: {ScenarioProjection.objects.filter(scenario=s).count()}')
"
```

**Expected**: "From Batch (Parr) - FI-2025-001" with ~50g initial weight and 720 projections.

---

## 💡 Why This Is Better

### For Farm Managers:

**Question**: "Is this batch on track to hit our harvest targets?"

**Old Answer**: Compare current batch (Day 450, 400g) vs hypothetical eggs (Day 450, 1.9g) ❌ Meaningless

**New Answer**: Compare current batch (Day 450, 400g) vs projected trajectory from Parr (Day 450, 420g) ✅ Shows -20g variance

### For Operational Planning:

**Old**: "We planned to grow a batch from eggs to 5000g in 900 days" (too generic)

**New**: "At Parr stage, we expect to reach 5000g in 720 days. Currently tracking 4% below plan." (actionable!)

### For UAT Testing:

**Old**: Scenarios didn't appear or showed meaningless data

**New**: Scenarios appear at Day 180+, show realistic growth, enable variance analysis

---

**Status**: ✅ **"From Batch" approach implemented**  
**Next**: Regenerate test data and verify UI displays correctly  
**Confidence**: 🟢 **High** - This matches user expectations and API patterns

---

*End of From Batch Scenario Approach Document*

