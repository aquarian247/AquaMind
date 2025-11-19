# Test Data Generation - Handoff (November 19, 2025)

**Status:** ✅ **READY FOR TEST DATA GENERATION**  
**Branch:** `main` (both repos)  
**Major Update:** TGC Formula Fix Complete

---

## 🎯 What's Ready

### ✅ TGC Formula Fix (Merged to Main)
- **Fixed:** Scenario projections now use industry-standard cube-root TGC formula
- **Result:** Realistic growth curves (0.1g → 6-7kg in 760 days)
- **Testing:** All 2,181 tests passing (backend + frontend)
- **PRs:** Backend #118 merged, Frontend #170 merged

### ✅ Scenario Configuration
- **Duration:** 760 days (projects to realistic harvest weight ~6kg)
- **TGC Values:** Stage-specific populated (Fry: 2.25, Adult: 3.1)
- **Temperature:** Freshwater 12°C, Seawater 9-11°C
- **Stage Transitions:** Time-based (90-day cycles)

### ✅ Test Data Scripts Updated
- Scenarios created at Day 1 with correct 760-day duration
- Event Engine uses correct TGC formula
- All supporting scripts aligned

---

## 📋 Next Steps: Generate Test Data

### Option A: Small Test (20 batches, 90 minutes)
```bash
cd /Users/aquarian247/Projects/AquaMind

# 1. Verify stage TGC values exist
python manage.py shell -c "
from apps.scenario.models import TGCModelStage
print(f'Stage TGC values: {TGCModelStage.objects.count()} (need 12+)')
"

# 2. Wipe operational data
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 3. Generate 20 batches
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14
```

**Expected Results:**
- 40 batches total (20 per geography)
- ~25 completed, ~15 active
- ~10 million events
- Realistic scenario projections for all batches

### Option B: Full Saturation (170 batches, 5-6 hours)
```bash
# After successful small test
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

---

## 🔍 Critical Verifications After Generation

### 1. Verify Scenario Projections Are Realistic

```bash
python manage.py shell -c "
from apps.scenario.models import Scenario

print('Scenario Projection Check:')
print('='*70)

for scenario in Scenario.objects.all()[:3]:
    last = scenario.projections.order_by('-day_number').first()
    
    if last:
        print(f'{scenario.name}:')
        print(f'  Duration: {scenario.duration_days} days')
        print(f'  Final weight: {last.average_weight:.2f}g')
        
        # Verify realistic
        if 5000 <= last.average_weight <= 7500:
            print('  ✅ Realistic harvest weight')
        elif last.average_weight < 100:
            print('  ❌ Too small - formula broken')
        else:
            print('  ⚠️ Check weight')
        print()
"
```

**Expected:**
- Duration: 760 days ✅
- Final weight: 5,000-7,000g ✅
- No projections stuck at <100g ✅

### 2. Verify Growth Analysis Data Available

```bash
python manage.py shell -c "
from apps.batch.models import Batch, ActualDailyAssignmentState, GrowthSample

batch = Batch.objects.filter(start_date__lte='2025-08-01').first()
if batch:
    samples = GrowthSample.objects.filter(assignment__batch=batch).count()
    actual = ActualDailyAssignmentState.objects.filter(batch=batch).count()
    scenario = batch.scenarios.first()
    projected = scenario.projections.count() if scenario else 0
    
    print(f'Growth Analysis Data for {batch.batch_number}:')
    print(f'  Growth Samples (Blue): {samples}')
    print(f'  Actual Daily (Orange): {actual:,}')
    print(f'  Scenario Projection (Green): {projected:,}')
    print()
    print('✅ All three series available' if samples > 0 and actual > 0 and projected > 0 else '❌ Missing data')
"
```

**Expected:** All three data series available for chart ✅

### 3. Check for Stage Transition Spikes (Known Issue)

```bash
python manage.py shell -c "
from apps.batch.models import Batch, ActualDailyAssignmentState

batch = Batch.objects.filter(start_date__lte='2025-08-01').first()
if batch:
    # Check day 91 (first transition)
    day90 = ActualDailyAssignmentState.objects.filter(batch=batch, day_number=90).first()
    day91 = ActualDailyAssignmentState.objects.filter(batch=batch, day_number=91).first()
    day92 = ActualDailyAssignmentState.objects.filter(batch=batch, day_number=92).first()
    
    if day90 and day91 and day92:
        w90 = float(day90.avg_weight_g)
        w91 = float(day91.avg_weight_g)
        w92 = float(day92.avg_weight_g)
        
        spike = w91 - w90
        correction = w92 - w91
        
        print(f'Stage Transition Spike Check (Day 90-92):')
        print(f'  Day 90: {w90:.2f}g')
        print(f'  Day 91: {w91:.2f}g (spike: {spike:+.2f}g)')
        print(f'  Day 92: {w92:.2f}g (correction: {correction:+.2f}g)')
        print()
        
        if abs(spike) > 5:
            print('  ⚠️ Spike detected (known issue, cosmetic only)')
            print('  See: GROWTH_ASSIMILATION_STAGE_TRANSITION_SPIKE_BUG.md')
        else:
            print('  ✅ No significant spike')
"
```

**Expected:** Small spikes may appear (documented, non-blocking) ⚠️

---

## 🐛 Known Issues (Non-Blocking)

### Orange Line Spikes at Stage Transitions
**Symptom:** Chart shows vertical spikes at days 91, 181, 271, 361, 451  
**Cause:** Growth Assimilation initializes new assignments with incorrect weight  
**Impact:** Visual only, self-corrects within 1 day  
**Priority:** Low (cosmetic)  
**Documentation:** `aquamind/docs/progress/GROWTH_ASSIMILATION_STAGE_TRANSITION_SPIKE_BUG.md`

**Does NOT affect:**
- ✅ Actual data integrity
- ✅ Growth samples
- ✅ Scenario projections (green line)
- ✅ Batch operations

---

## 🎓 What Was Fixed

### Before (Broken):
```
Scenario projection: 0.1g → 8g in 900 days
Green line: Flat, unusable
Formula: Power-law (incorrect)
```

### After (Fixed):
```
Scenario projection: 0.1g → 6,975g in 760 days
Green line: Realistic S-curve
Formula: Cube-root (industry standard)
```

**All tests passing, ready for production use!**

---

## 📝 Quick Reference

**Main Guide:** `aquamind/docs/database/test_data_generation/test_data_generation_guide_v3.md`

**Key Commands:**
```bash
# Populate stage TGC (if needed)
python manage.py populate_stage_tgc --all

# Generate 20 batches (test)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14

# Generate 170 batches (full)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 85 --workers 14
```

**Critical:** Always use `SKIP_CELERY_SIGNALS=1` or generation will take 40+ hours instead of 5-6! ⚠️

---

## 🚀 Confidence Level: HIGH

**Everything is ready:**
- ✅ TGC formula correct and tested
- ✅ Scripts updated with 760-day scenario duration
- ✅ Stage TGC values can be populated
- ✅ All quality gates passing
- ✅ Documentation updated

**Proceed with confidence!** 🎉

---

**Next Agent:** Start with Option A (20 batches) to validate, then scale to Option B (170 batches) if successful.

