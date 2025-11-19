# Important Scenario Updates - November 19, 2025

**Status:** ✅ **COMPLETE** - Ready for test data generation

---

## 🎯 What Changed

### TGC Formula Fix
**Problem:** Scenario projections used incorrect power-law formula producing flat growth curves (0.1g → 8g in 900 days).

**Solution:** Replaced with industry-standard cube-root TGC formula (Iwama & Tautz 1981):
```
W_final^(1/3) = W_initial^(1/3) + (TGC/1000) × Temperature × Days
```

**Result:** Realistic growth curves (0.1g → 6-7kg in 760 days) ✅

### Scenario Duration Adjustment
**Changed:** Scenario projections from 900 days → **760 days**

**Reason:**
- Projects to realistic harvest weight (~6kg)
- Avoids hitting theoretical 8kg safety caps
- Matches industry practice (4-6kg harvest targets)

**Note:** Batches still run up to 900 days (harvest by weight, not time)

### Stage-Specific TGC Values
**Populated:** All TGC models now have stage-specific values:
- Egg&Alevin: 0.0 (no external feeding)
- Fry: 2.25
- Parr: 2.75
- Smolt: 2.75
- Post-Smolt: 3.25
- Adult: 3.1

**Command to populate:**
```bash
python manage.py populate_stage_tgc --all
```

### Temperature Management
**Freshwater stages (Egg→Smolt):** 12°C controlled  
**Seawater stages (Post-Smolt→Adult):** 9-11°C from profile

---

## 📋 Impact on Test Data Generation

### What's Different:
1. ✅ **Scenarios created at Day 1** (was: Day 180)
2. ✅ **Scenario duration: 760 days** (was: 900)
3. ✅ **Realistic growth projections** (was: flat/broken)
4. ✅ **Stage-specific TGC** (was: single value)

### What's the Same:
- ✅ Batch durations: Still 900 day maximum
- ✅ Batch harvest: Still by weight (~4.5kg around day 450-550)
- ✅ Event generation: Unchanged
- ✅ Infrastructure: Unchanged

### Growth Analysis Chart:
- 🟢 **Green line (Scenario):** Now shows realistic S-curve
- 🟠 **Orange line (Actual):** Unchanged (small spikes at transitions documented separately)
- 📊 **Blue dots (Samples):** Unchanged

---

## 🔧 Commands for Next Session

### Before Generating Test Data:

1. **Ensure stage TGC values populated:**
```bash
cd /Users/aquarian247/Projects/AquaMind

# Check if populated
python manage.py shell -c "
from apps.scenario.models import TGCModelStage
print(f'Stage TGC values: {TGCModelStage.objects.count()} records')
print('✅ Ready' if TGCModelStage.objects.count() >= 12 else '❌ Run populate command')
"

# If needed, populate
python manage.py populate_stage_tgc --all
```

2. **Wipe existing scenarios** (if regenerating):
```bash
# Scenarios have 900-day duration (old) → need regeneration
python manage.py shell -c "
from apps.scenario.models import Scenario
old_count = Scenario.objects.filter(duration_days=900).count()
if old_count > 0:
    print(f'⚠️ Found {old_count} scenarios with old duration (900 days)')
    print('Run wipe script to regenerate with correct 760-day duration')
"
```

3. **Generate test data normally:**
```bash
# Scenarios will be created automatically with correct 760-day duration
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/04_batch_orchestrator_parallel.py \
  --execute --batches 20 --workers 14
```

---

## ✅ Verification After Generation

### Check Scenario Projections:

```bash
python manage.py shell -c "
from apps.scenario.models import Scenario, ScenarioProjection

print('Scenario Check:')
print('='*70)

scenarios = Scenario.objects.all()[:3]
for scenario in scenarios:
    last_proj = scenario.projections.order_by('-day_number').first()
    
    if last_proj:
        print(f'{scenario.name}:')
        print(f'  Duration: {scenario.duration_days} days')
        print(f'  Final weight: {last_proj.average_weight:.2f}g')
        print(f'  Final temp: {last_proj.temperature:.1f}°C')
        print(f'  Stage: {last_proj.current_stage.name}')
        
        # Check if hit cap
        if last_proj.average_weight >= 7500:
            print('  ⚠️ Approaching cap')
        elif last_proj.average_weight >= 4000:
            print('  ✅ Realistic harvest weight')
        print()
"
```

**Expected Results:**
- Duration: 760 days ✅
- Final weight: 5,000-7,000g ✅
- Temperature: 9-11°C (seawater) ✅
- Stage: Adult ✅

---

## 🐛 Known Issues (Non-Blocking)

### Orange Line Spikes at Stage Transitions
**Issue:** Growth Analysis chart shows small spikes in Actual Daily State at days 91, 181, 271, etc.

**Cause:** Growth Assimilation Engine initializes new assignments with stage min weight instead of inheriting from previous assignment.

**Impact:** Visual only - self-corrects next day via growth sample anchors

**Status:** Documented in `aquamind/docs/progress/GROWTH_ASSIMILATION_STAGE_TRANSITION_SPIKE_BUG.md`

**Priority:** Low (cosmetic, doesn't affect operations)

---

## 📚 References

**TGC Formula Documentation:**
- `aquamind/docs/deprecated/SCENARIO_PROJECTION_TGC_FIX_SUMMARY.md` - Complete fix details
- `aquamind/docs/prd.md` Section 3.3.1 - Formula specification
- Management commands: `populate_stage_tgc.py`, `regenerate_projections.py`

**Growth Analysis:**
- `aquamind/docs/progress/GROWTH_ASSIMILATION_STAGE_TRANSITION_SPIKE_BUG.md` - Spike issue
- `aquamind/docs/progress/batch_growth_assimilation/` - Implementation phases

---

## ✅ Ready for Next Session

**Test data generation should work correctly with:**
- ✅ Realistic scenario projections (760 days)
- ✅ Correct TGC formula (cube-root)
- ✅ Stage-specific growth rates
- ✅ Growth Analysis charts with all three series visible

**No additional setup needed** - the TGC fix is merged to main and ready to use!

---

**Last Updated:** November 19, 2025 (Post TGC Formula Fix)  
**Next Action:** Run test data generation (20 or 85 batches)

