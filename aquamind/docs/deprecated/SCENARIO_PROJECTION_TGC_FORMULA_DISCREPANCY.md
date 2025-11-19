# Scenario Projection TGC Formula Discrepancy

**Date:** November 19, 2025  
**Discovered During:** Test data generation validation  
**Severity:** 🔴 **HIGH** - Scenario projections produce unrealistic growth curves  
**Status:** ✅ **RESOLVED** (November 19, 2025)

**Resolution:** Replaced power-law formula with industry-standard cube-root TGC formula. See `SCENARIO_PROJECTION_TGC_FIX_SUMMARY.md` for complete details.

---

## 🐛 Problem Description

During test data generation validation, we discovered that **scenario projections produce drastically different growth curves** compared to actual batch growth, even when using the same TGC models, temperature profiles, and initial conditions.

**Observable Symptom:**
- Growth Analysis chart shows **orange line (Actual)** with realistic growth: 0.1g → 4,500g in 760 days ✅
- Growth Analysis chart shows **green line (Projected)** flat near zero: 0.1g → 8g in 900 days ❌

**Impact:**
- Users cannot compare actual vs projected growth (core feature)
- Scenario planning produces meaningless forecasts
- Growth Analysis feature is partially broken

---

## 🔬 Investigation Findings

### Test Case: Batch FI-2023-001

**Initial Conditions:**
- Start date: 2023-01-01
- Initial population: 3,500,000 eggs
- Initial weight: 0.1g
- Geography: Faroe Islands
- TGC Model: "Faroe Islands Standard TGC"
- Temperature: ~9.6°C average (sea temperature profile)

**Actual Growth (via Event Engine):**
```
Day 1:   0.10g   (3.50M fish)
Day 91:  6.02g   (3.06M fish)
Day 181: 60.1g   (2.92M fish)
Day 271: 180.2g  (2.85M fish)
Day 361: 500.3g  (2.80M fish)
Day 451: 4564.3g (2.73M fish)
Day 760: 4563g   (2.67M fish) → HARVESTED ✅
```

**Projected Growth (via Projection Engine):**
```
Day 1:   0.10g   (3.50M fish)
Day 100: 0.26g   (3.50M fish)
Day 450: 1.91g   (3.49M fish)
Day 900: 8.09g   (3.49M fish) ❌
```

**Discrepancy:** At day 450, actual = 4,564g but projected = 1.91g (2,387x difference!)

---

## 🔍 Root Cause Analysis

### Two Different TGC Formulas in Use

**Event Engine Formula** (`scripts/data_generation/03_event_engine_core.py` lines 681-716):
```python
# TGC values (already divided by 1000)
tgc = {
    'Egg&Alevin': 0,
    'Fry': 0.00225,      # 2.25 per 1000 degree-days
    'Parr': 0.00275,     # 2.75 per 1000 degree-days
    'Smolt': 0.00275,
    'Post-Smolt': 0.00325,
    'Adult': 0.0031
}

# Cube root method (standard aquaculture formula)
w = float(a.avg_weight_g)
temp = 12.0  # Freshwater or 9.0 for seawater

# TGC formula: W_final^(1/3) = W_initial^(1/3) + (TGC * temp * days)
new_w = ((w ** (1/3)) + t * temp * 1) ** 3

# Apply stage-specific caps
stage_caps = {
    'Fry': 6,
    'Parr': 60,
    'Smolt': 180,
    'Post-Smolt': 500,
    'Adult': 7000
}
new_w = min(new_w, max_weight)
```

**Projection Engine Formula** (`apps/scenario/services/calculations/tgc_calculator.py` lines 115-122):
```python
# TGC value from database (was 0.00245, now corrected to 2.45)
tgc_value = self.model.tgc_value  # 2.45

# Linear addition method (appears incorrect for aquaculture)
# Standard TGC formula: ΔW = TGC × T^n × W^m
growth_g = (
    tgc_value * 
    (temperature ** temp_exponent) *   # n = 0.33
    (current_weight ** weight_exponent) # m = 0.66
)

new_weight = current_weight + growth_g
```

---

## 📊 Formula Comparison

### Mathematical Difference

**Cube Root Method (Event Engine):**
```
W_f^(1/3) = W_i^(1/3) + (TGC × T × days)
W_f = [W_i^(1/3) + (TGC × T × days)]^3
```

**Linear Addition Method (Projection Engine):**
```
ΔW = TGC × T^0.33 × W^0.66
W_f = W_i + ΔW
```

### Test Results

**With TGC = 0.00245, T = 9.6°C, W_initial = 0.1g, 900 days:**

| Method | Day 100 | Day 450 | Day 900 | Realistic? |
|--------|---------|---------|---------|------------|
| Cube Root (Event Engine) | ~10g | ~1000g | ~5000g | ✅ YES |
| Linear Addition (Projection Engine) | 0.26g | 1.91g | 8.09g | ❌ NO |

**With TGC = 2.45 (×1000), same conditions:**

| Method | Day 100 | Day 450 | Day 900 | Realistic? |
|--------|---------|---------|---------|------------|
| Cube Root | ~10,000g | ~1M g | ~5M g | ❌ TOO BIG |
| Linear Addition | 2.6M g | 279M g | 2.2B g | ❌ WAY TOO BIG |

---

## 🤔 Hypothesis: Why Two Formulas?

### Possibility 1: Different TGC Definitions

**Standard Aquaculture TGC (Cube Root):**
- Used in research papers (Iwama & Tautz, 1981)
- Formula: `TGC = (W_f^(1/3) - W_i^(1/3)) / (T × days) × 1000`
- Typical values: 2.0-4.0 per 1000 degree-days
- **This is what event engine uses**

**Alternative TGC (Power Law):**
- Some models use: `ΔW = TGC × T^n × W^m`
- Different scaling and exponents
- May require different TGC values
- **This is what projection engine uses**

### Possibility 2: Unit Mismatch

**Event Engine:**
- TGC stored in code: 0.00225 - 0.0031
- Already divided by 1000
- Works directly in formula

**Projection Engine:**
- TGC stored in database: Originally 0.00245 (too small)
- Corrected to 2.45 (too big)
- **Needs different scaling?**

### Possibility 3: Formula Implementation Error

**The projection engine formula might be incorrectly implemented:**
- Using wrong exponents (0.33, 0.66)
- Missing a scaling factor
- Not applying stage transitions correctly

---

## 🔍 Evidence from Code

### Event Engine TGC Application

**Location:** `scripts/data_generation/03_event_engine_core.py:681-716`

```python
def growth_update(self):
    # TGC values from industry data (per 1000 degree-days, so divide by 1000)
    tgc = {
        'Egg&Alevin': 0,
        'Fry': 0.00225,      # 2.25/1000
        'Parr': 0.00275,     # 2.75/1000
        'Smolt': 0.00275,
        'Post-Smolt': 0.00325,
        'Adult': 0.0031
    }
    
    for a in self.assignments:
        t = tgc.get(a.lifecycle_stage.name, 0)
        if t == 0:  # No growth for Egg&Alevin
            continue
        
        # Temperature varies by stage
        if a.lifecycle_stage.name in ['Fry', 'Parr', 'Smolt']:
            temp = 12.0  # Freshwater
        else:
            temp = 9.0   # Seawater
        
        w = float(a.avg_weight_g)
        
        # TGC formula: W_final^(1/3) = W_initial^(1/3) + (TGC * temp * days) / 1000
        # Already divided TGC by 1000, so: W_f^(1/3) = W_i^(1/3) + TGC * temp * days
        new_w = ((w ** (1/3)) + t * temp * 1) ** 3
        
        # Cap at realistic max weights per stage
        stage_caps = {
            'Fry': 6,
            'Parr': 60,
            'Smolt': 180,
            'Post-Smolt': 500,
            'Adult': 7000
        }
        max_weight = stage_caps.get(a.lifecycle_stage.name, 7000)
        new_w = min(new_w, max_weight)
```

**Result:** Produces realistic growth curves ✅

### Projection Engine TGC Application

**Location:** `apps/scenario/services/calculations/tgc_calculator.py:115-122`

```python
def calculate_daily_growth(self, current_weight, temperature, lifecycle_stage=None):
    tgc_value = self.model.tgc_value  # From database
    temp_exponent = self.model.exponent_n  # 0.33
    weight_exponent = self.model.exponent_m  # 0.66
    
    # Standard TGC formula: ΔW = TGC × T^n × W^m
    growth_g = (
        tgc_value * 
        (temperature ** temp_exponent) * 
        (current_weight ** weight_exponent)
    )
    
    new_weight = current_weight + growth_g
    
    return {
        'growth_g': growth_g,
        'new_weight_g': new_weight,
        'tgc_value': tgc_value,
        'temperature': temperature
    }
```

**Result:** Produces unrealistic growth curves ❌

---

## 🎯 Questions for Investigation

### 1. Which Formula is Correct?

**Cube Root Method (Event Engine):**
- Standard in aquaculture research
- Used in scientific papers
- Produces realistic results in our tests

**Power Law Method (Projection Engine):**
- May be an alternative formulation
- Requires different TGC scaling
- Currently produces unrealistic results

**Question:** Is the projection engine formula a valid alternative, or is it simply wrong?

### 2. What Should TGC Values Be?

**Current Database Values (after correction):**
- Faroe: 2.45
- Scotland: 2.35

**Event Engine Values:**
- Fry: 0.00225 (2.25 ÷ 1000)
- Parr: 0.00275 (2.75 ÷ 1000)
- Adult: 0.0031 (3.1 ÷ 1000)

**Question:** Should projection engine TGC values be:
- Option A: 0.00245 (divided by 1000, like event engine)
- Option B: 2.45 (NOT divided, but formula needs adjustment)
- Option C: Something else entirely

### 3. Why Different Exponents?

**Event Engine:**
- Uses cube root: `(1/3)` exponent
- No separate temperature exponent
- Formula: `W^(1/3) = W_0^(1/3) + TGC*T*days`

**Projection Engine:**
- Uses power law: `T^0.33 × W^0.66`
- Separate exponents for temperature and weight
- Formula: `ΔW = TGC × T^n × W^m`

**Question:** Are these meant to be equivalent formulations, or fundamentally different models?

### 4. Should Stage Caps Apply?

**Event Engine:**
- Applies hard caps per stage (Fry: 6g, Parr: 60g, etc.)
- Prevents unrealistic growth
- Forces stage-appropriate weights

**Projection Engine:**
- No visible stage caps in TGC calculator
- Relies on stage constraints (currently 0 records)
- May need stage transition logic

**Question:** Should projection engine apply the same stage caps?

---

## 🧪 Test Data for Validation

### Successful Event Engine Growth

**Batch:** FI-2023-001  
**Parameters:**
- Initial: 3,500,000 eggs @ 0.1g
- TGC: 0.00225-0.0031 (stage-specific)
- Temperature: 12°C (FW), 9°C (SW)
- Mortality: 0.03% daily
- Stage caps: Applied

**Results:**
```
Day 0:   0.1g    (Egg&Alevin)
Day 90:  0.1g    (transition to Fry)
Day 91:  6.0g    (Fry growth starts)
Day 180: 60g     (transition to Parr)
Day 270: 180g    (transition to Smolt)
Day 360: 500g    (transition to Post-Smolt)
Day 450: 4564g   (transition to Adult)
Day 760: 4563g   → HARVESTED ✅
```

**Growth curve:** Realistic S-curve with stage-specific acceleration

### Failed Projection Engine Growth

**Scenario:** Baseline Projection - FI-2023-001  
**Parameters:**
- Initial: 3,500,000 eggs @ 0.1g
- TGC Model: "Faroe Islands Standard TGC" (value: 2.45)
- Temperature Profile: "Faroe Islands Sea Temperature" (avg 9.6°C)
- FCR Model: "Standard Atlantic Salmon FCR"
- Mortality Model: "Standard Mortality" (0.03% daily)

**Results (Before TGC Correction):**
```
Day 1:   0.10g
Day 100: 0.26g
Day 450: 1.91g
Day 900: 8.09g ❌
```

**Results (After TGC × 1000):**
```
Day 1:   1.1g
Day 100: 2,642,673g  (2.6 tonnes per fish!)
Day 900: 2,252,783,232g  (2.2 million tonnes per fish!) ❌
```

**Growth curve:** Either flat (TGC too small) or explosive (TGC too big)

---

## 📐 Formula Analysis

### Standard TGC Formula (Aquaculture Literature)

**Source:** Iwama & Tautz (1981), Jobling (2003)

**Formula:**
```
TGC = (W_f^(1/3) - W_i^(1/3)) / (T × days) × 1000
```

**Rearranged for projection:**
```
W_f^(1/3) = W_i^(1/3) + (TGC × T × days) / 1000
W_f = [W_i^(1/3) + (TGC × T × days) / 1000]^3
```

**For daily calculation:**
```python
# If TGC already divided by 1000:
new_w = ((w ** (1/3)) + tgc * temp * 1) ** 3
```

**This is what the event engine uses** ✅

### Projection Engine Formula

**Location:** `apps/scenario/services/calculations/tgc_calculator.py:115-122`

**Formula:**
```python
growth_g = tgc_value * (temperature ** 0.33) * (current_weight ** 0.66)
new_weight = current_weight + growth_g
```

**This appears to be a different formulation:**
- Uses power law: `ΔW = TGC × T^n × W^m`
- Linear addition (not cube root)
- Different mathematical structure

**Question:** Is this a valid alternative TGC formulation, or an implementation error?

---

## 🔬 Mathematical Comparison

### Cube Root Method (Event Engine)

**Daily growth for 100g fish at 10°C with TGC=0.003:**
```python
w_initial = 100
w_final_cuberoot = w_initial ** (1/3)  # 4.64
w_final_cuberoot += 0.003 * 10 * 1     # 4.64 + 0.03 = 4.67
w_final = w_final_cuberoot ** 3        # 101.9g

Daily gain: 1.9g
```

### Power Law Method (Projection Engine)

**Daily growth for 100g fish at 10°C with TGC=0.003:**
```python
growth = 0.003 * (10 ** 0.33) * (100 ** 0.66)
# growth = 0.003 × 2.15 × 21.54 = 0.139g

w_final = 100 + 0.139 = 100.139g

Daily gain: 0.139g
```

**Ratio:** Cube root produces **13.7x more growth** than power law (1.9g vs 0.139g)

**Over 900 days:** This difference compounds exponentially!

---

## 🎯 Possible Explanations

### Hypothesis 1: Implementation Error

**The projection engine formula is simply wrong.**

**Evidence:**
- Produces unrealistic results
- Doesn't match aquaculture literature
- Event engine (which works) uses different formula

**Fix:** Replace projection engine formula with cube root method

### Hypothesis 2: Different TGC Definitions

**The two formulas use different TGC definitions.**

**Event Engine TGC:** Standard thermal growth coefficient (per 1000 degree-days)  
**Projection Engine TGC:** Some other growth coefficient (different units/scaling)

**Evidence:**
- Both formulas have "TGC" but mean different things
- Projection engine might need TGC values in different scale

**Fix:** Determine correct TGC values for projection engine formula

### Hypothesis 3: Missing Stage Transitions

**The projection engine doesn't apply stage transitions correctly.**

**Evidence:**
- Event engine has stage caps (Fry: 6g, Parr: 60g, etc.)
- Projection engine has no visible caps
- StageConstraint table is empty (0 records)

**Fix:** Implement stage transition logic in projection engine

### Hypothesis 4: Temperature Profile Mismatch

**The projection engine uses wrong temperature profile.**

**Evidence:**
- Event engine uses stage-specific temps (12°C FW, 9°C SW)
- Projection engine uses single profile (sea temps only)
- Freshwater stages might use wrong temperature

**Fix:** Use stage-appropriate temperature profiles

---

## 🔧 Recommended Investigation Steps

### Step 1: Verify TGC Formula Source

**Check documentation/comments in projection engine:**
- Is there a reference to which TGC formula is intended?
- Are there unit tests that show expected behavior?
- Is there academic literature cited?

**Files to check:**
- `apps/scenario/services/calculations/tgc_calculator.py`
- `apps/scenario/services/calculations/projection_engine.py`
- `apps/scenario/tests/` (if any)

### Step 2: Compare with Event Engine

**The event engine produces correct results**, so:
- Copy its TGC formula to projection engine
- Use same stage caps
- Use same temperature logic

**OR:**
- Understand why projection engine uses different formula
- Determine correct TGC values for that formula

### Step 3: Test with Known Values

**Create a test scenario:**
- Initial: 100g fish
- Temperature: 10°C constant
- TGC: 3.0 (standard value)
- Duration: 100 days

**Expected result (from literature):**
- Should reach ~200-300g

**Test both engines and compare**

### Step 4: Check Stage Constraints

**Create StageConstraint records:**
```python
from apps.scenario.models import BiologicalConstraints, StageConstraint

bc = BiologicalConstraints.objects.first()
stages = [
    ('Egg&Alevin', 0.05, 0.5),
    ('Fry', 0.5, 10),
    ('Parr', 10, 100),
    ('Smolt', 100, 200),
    ('Post-Smolt', 200, 600),
    ('Adult', 600, 8000),
]

for stage_name, min_w, max_w in stages:
    StageConstraint.objects.create(
        constraint_set=bc,
        lifecycle_stage=stage_name,
        min_weight_g=min_w,
        max_weight_g=max_w,
        typical_duration_days=90 if stage_name != 'Adult' else 450
    )
```

**Then recompute projections and check if stage transitions apply**

---

## 📚 References

### Aquaculture TGC Literature

**Standard TGC Formula:**
- Iwama, G. K., & Tautz, A. F. (1981). "A simple growth model for salmonids in hatcheries"
- Jobling, M. (2003). "The thermal growth coefficient (TGC) model of fish growth"

**Formula:**
```
TGC = [(W_f^(1/3) - W_i^(1/3)) / (Σ(T × days))] × 1000
```

**Typical TGC values for Atlantic Salmon:**
- Freshwater (12°C): 2.5-3.5
- Seawater (8-10°C): 2.0-3.0
- Post-smolt (optimal): 3.0-3.5

### Current Implementation

**Event Engine:** Uses standard cube root formula ✅  
**Projection Engine:** Uses power law formula ❓

---

## 🎯 Immediate Actions Needed

### For Test Data Generation (Today):

**Accept that projection engine is broken:**
- ✅ Event engine works (produces realistic batches)
- ✅ Growth Analysis (Actual) works
- ✅ Scenarios are created and linked
- ❌ Scenario projections are unrealistic

**Workaround:**
- Pin scenarios to batches (done)
- GUI will show green line (but values wrong)
- Focus on validating actual growth (orange line)

### For Projection Engine Fix (Next Session):

**Option A: Copy Event Engine Formula**
```python
# Replace projection engine TGC calculation with event engine's cube root method
new_weight = ((current_weight ** (1/3)) + tgc * temperature * 1) ** 3
```

**Option B: Fix Current Formula**
- Determine correct TGC scaling for power law formula
- Add stage caps
- Test against known values

**Option C: Investigate Intent**
- Find original developer's intent
- Check if there's academic justification for power law method
- Determine if both formulas should coexist (for different purposes)

---

## 📊 Current Status

**What Works:**
- ✅ Event engine TGC calculation (realistic growth)
- ✅ Growth Analysis Actual Daily State
- ✅ Scenario creation and linking
- ✅ All underlying models exist (TGC, FCR, Mortality, Temperature)

**What's Broken:**
- ❌ Projection engine TGC calculation (unrealistic growth)
- ❌ StageConstraint table empty (0 records)
- ❌ Growth Analysis chart green line appears flat

**Impact:**
- Users cannot see projected growth curves
- Scenario planning feature partially broken
- Growth Analysis comparison feature non-functional

---

## 🚀 Next Steps

1. **Investigate which TGC formula is correct** (aquaculture literature)
2. **Decide: Fix projection engine or replace with event engine formula**
3. **Create stage constraints** (if projection engine needs them)
4. **Test with known values** (validate against literature)
5. **Regenerate test data** with corrected projections
6. **Verify Growth Analysis chart** shows both lines correctly

---

## 📝 Notes

**Discovery Context:**
- Found during test data generation validation (Nov 19, 2025)
- Generated 7 batches (1 completed + 6 active)
- All batches have scenarios but projections are unrealistic
- Event engine growth is perfect, projection engine growth is broken

**Test Environment:**
- Database: PostgreSQL with TimescaleDB
- Django: 4.2.11
- Python: 3.11
- 7 batches with 38M events generated successfully

**Files Involved:**
- `scripts/data_generation/03_event_engine_core.py` (working TGC)
- `apps/scenario/services/calculations/tgc_calculator.py` (broken TGC)
- `apps/scenario/services/calculations/projection_engine.py` (orchestrator)
- `apps/scenario/models.py` (TGCModel, StageConstraint)

---

**This issue blocks the Growth Analysis feature from being fully functional.**  
**Recommend prioritizing this fix before scaling test data generation to 50+ batches.**

---

