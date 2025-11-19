# Scenario Projection Bug - Unrealistic Growth

**Date:** November 19, 2025  
**Status:** 🐛 **BLOCKING** - Projection engine producing unrealistic results  
**Impact:** Growth Analysis chart shows flat green line (scenario at 0g)

---

## 🐛 The Bug

**Symptom:**
- Scenario projections show **7-8g at day 900** (should be 5000-7000g)
- Growth Analysis chart: Green line (projection) appears flat/zero
- Orange line (actual) works perfectly and shows realistic growth

**Example:**
```
Scenario: FI-2023-001 (3.5M eggs @ 0.1g)
Day 1: 0.10g ✅
Day 100: 0.26g ❌ (should be ~10-20g)
Day 500: 2.35g ❌ (should be ~1000-2000g)
Day 900: 8.42g ❌ (should be ~5000-7000g)
```

---

## 🔍 Root Cause

**Projection Engine Issue:**
The `ProjectionEngine` in `apps/scenario/services/calculations/projection_engine.py` is:
1. Using TGC model (✅ exists, value = 0.00235)
2. Using temperature profile (✅ exists, 450 readings)
3. Using FCR model (✅ exists with stage values)
4. Using mortality model (✅ exists)

**But:**
- Stage constraints exist but have **0 stage_constraint records**
- Or: Projection engine not applying stage transitions correctly
- Or: TGC calculation formula is wrong

**Evidence:**
- Recomputing projections after initializing stage data still produces 7-8g
- All 7 scenarios have same issue
- Actual growth (via event engine) works perfectly (reaches 4500g)

---

## 💡 Comparison: Event Engine vs Projection Engine

**Event Engine (Working ✅):**
```python
# In 03_event_engine_core.py line 681-716
tgc = {
    'Egg&Alevin': 0,
    'Fry': 0.00225,
    'Parr': 0.00275,
    'Smolt': 0.00275,
    'Post-Smolt': 0.00325,
    'Adult': 0.0031
}

# TGC formula
w = float(a.avg_weight_g)
temp = 12.0  # Freshwater or 9.0 for seawater
new_w = ((w ** (1/3)) + t * temp * 1) ** 3

# Stage caps
stage_caps = {
    'Fry': 6,
    'Parr': 60,
    'Smolt': 180,
    'Post-Smolt': 500,
    'Adult': 7000
}
new_w = min(new_w, max_weight)
```

**Result:** Realistic growth (0.1g → 4500g in 760 days)

**Projection Engine (Broken ❌):**
```python
# In apps/scenario/services/calculations/projection_engine.py
# Uses TGC model from database
# Should apply same formula but produces 0.1g → 8g in 900 days
```

**Result:** Unrealistic growth (100x too slow!)

---

## 🎯 Immediate Action Plan

### Option 3: Recompute + Pin (Proof of Concept)

**Step 1: Check if stage constraints actually exist**
```python
from apps.scenario.models import StageConstraint
StageConstraint.objects.count()  # Should be 6
```

**Step 2: If missing, create them**
```python
# Run initialization again or manually create
```

**Step 3: Recompute projections**
```python
# Already tried - still produces 7-8g
# Projection engine itself is broken
```

**Step 4: Pin scenarios to batches**
```python
for batch in Batch.objects.all():
    scenario = Scenario.objects.filter(batch=batch).first()
    if scenario:
        batch.pinned_scenario = scenario
        batch.save(update_fields=['pinned_scenario'])
```

---

## 🔧 Recommended Path Forward

### **SHORT TERM (Today):**

**Accept that projection engine is broken**, but verify:
1. ✅ Growth Analysis **Actual Daily State** works (orange line) - **VERIFIED**
2. ✅ Scenarios are created and linked to batches - **VERIFIED**
3. ✅ Pinning mechanism exists - **VERIFIED**
4. ✅ API returns data (even if projection values wrong) - **NEEDS FIX**

**Pin the scenarios** so GUI can display them:
```bash
# Pin all scenarios to their batches
python manage.py shell << 'EOF'
from apps.batch.models import Batch
from apps.scenario.models import Scenario

for batch in Batch.objects.all():
    scenario = Scenario.objects.filter(batch=batch).first()
    if scenario and not batch.pinned_scenario:
        batch.pinned_scenario = scenario
        batch.save(update_fields=['pinned_scenario'])
        print(f"✅ Pinned {scenario.name} to {batch.batch_number}")
EOF
```

### **MEDIUM TERM (Next Session):**

**Option 2: Clean Regeneration**
1. Fix projection engine OR use event engine's TGC logic
2. Wipe operational data
3. Regenerate 7 batches with correct projections
4. Verify Growth Analysis chart shows both lines correctly
5. **THEN** scale to 50+ batches

---

## 🎓 Key Insight

**The test data generation script is working correctly!**
- Creates batches ✅
- Creates scenarios ✅
- Computes Growth Analysis ✅
- Calls projection engine ✅

**The projection engine itself is broken** (separate issue from test data generation).

**For migration scripts:** The test data generation logic is sound. The projection engine bug is a **scenario app issue**, not a test data generation issue.

---

## 📋 Current Status

**What Works:**
- ✅ Batch creation with realistic growth
- ✅ Growth Analysis (Actual Daily State)
- ✅ Scenario creation and linking
- ✅ API field name fixed (average_weight)

**What's Broken:**
- ❌ Projection engine produces unrealistic values
- ❌ Green line in chart appears flat/zero

**Next Decision Point:**
1. **Pin scenarios** (so GUI shows them, even if wrong values)
2. **Debug projection engine** (could take 1-2 hours)
3. **Move to Option 2** (clean regen after fixing projection)

**Your call!** 🎯

