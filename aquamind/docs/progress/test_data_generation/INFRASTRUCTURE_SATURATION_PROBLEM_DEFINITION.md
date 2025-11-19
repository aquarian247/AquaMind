# Infrastructure Saturation Optimization Problem

**Goal:** Achieve 85% container occupancy at any given moment in time

---

## 📊 Problem Definition

### Given:
```
Total Containers: 2,017
  - Freshwater: 1,157 containers (12 Faroe + 10 Scotland stations × 5 halls × 10 containers)
  - Sea: 860 rings (23 Faroe + 20 Scotland areas × 20 rings)

Target Occupancy: 85% × 2,017 = 1,714 containers occupied simultaneously
```

### Batch Lifecycle:
```
Stage           Duration    Containers/Batch
-------------------------------------------
Egg&Alevin      90 days     10 (Hall-A)
Fry             90 days     10 (Hall-B)
Parr            90 days     10 (Hall-C)
Smolt           90 days     10 (Hall-D)
Post-Smolt      90 days     10 (Hall-E)
Adult           450 days    X rings (variable: 10-20)
-------------------------------------------
Total           900 days    50 FW + X sea
```

### Current Results (250 batches, 30-day stagger):
```
Instantaneous Occupancy at Any Moment:
  
  Freshwater:
    - Batches per stage: 90 days ÷ 30 stagger = 3 batches
    - Stages: 5
    - Total batches: 3 × 5 = 15 batches in freshwater
    - Containers: 15 batches × 10 = 150 containers occupied
    - Saturation: 150 / 1,157 = 13% ❌
  
  Sea:
    - Batches in Adult: 450 days ÷ 30 stagger = 15 batches
    - Rings per batch: 20 (if using full area)
    - Containers: 15 batches × 20 = 300 rings occupied
    - Saturation: 300 / 860 = 35% ❌
  
  Total Instantaneous:
    - Occupied: 150 + 300 = 450 containers
    - Saturation: 450 / 2,017 = 22% ❌
    - Target: 1,714 (85%)
    - Gap: 1,264 containers under-utilized
```

---

## 🎯 Optimization Variables

### Variable 1: Stagger Interval (Currently 30 days)

**Impact on Overlap:**
```
Stagger = 30 days:
  - Batches in 90-day stage: 90 ÷ 30 = 3 simultaneous
  - Batches in 450-day stage: 450 ÷ 30 = 15 simultaneous

Stagger = 15 days:
  - Batches in 90-day stage: 90 ÷ 15 = 6 simultaneous (2× overlap)
  - Batches in 450-day stage: 450 ÷ 15 = 30 simultaneous (2× overlap)
  
Stagger = 10 days:
  - Batches in 90-day stage: 90 ÷ 10 = 9 simultaneous (3× overlap)
  - Batches in 450-day stage: 450 ÷ 10 = 45 simultaneous (3× overlap)
```

**Trade-off:** Shorter stagger = more overlap = higher saturation, BUT need more total batches

### Variable 2: Containers per Batch (Currently 10 FW, 20 sea)

**Freshwater (Fixed by Hall Capacity):**
- Each hall has 10 containers
- Batch must use entire hall (operational reality)
- **Cannot change** without infrastructure redesign

**Sea (Flexible):**
- Each area has 20 rings
- Batch could use 10-20 rings (biomass-dependent)
- **Can optimize** based on batch size

### Variable 3: Total Number of Batches

**To reach 1,714 containers occupied:**

**Freshwater requirement:**
```
Target FW occupied: 1,714 × (1,157/2,017) = 983 containers
Containers per batch: 10
Batches per stage: 983 ÷ 10 ÷ 5 stages = 19.7 batches per stage
```

**This means:**
- Need ~20 batches per FW stage simultaneously
- With 90-day stages: 20 batches × 30-day stagger = 600 days of stagger ❌ IMPOSSIBLE
- OR: Reduce stagger to 90 ÷ 20 = 4.5 days ✅

**Sea requirement:**
```
Target sea occupied: 1,714 × (860/2,017) = 731 rings
Rings per batch: 20 (full area)
Batches in Adult: 731 ÷ 20 = 37 batches simultaneously

With 450-day Adult stage: 37 batches × 30-day stagger = 1,110 days ❌ IMPOSSIBLE
OR: Reduce stagger to 450 ÷ 37 = 12 days ✅
```

### Variable 4: Stage Durations (Currently 90+450 = 900 total)

**Could extend stages:**
```
If Egg&Alevin = 120 days (instead of 90):
  - More overlap in Hall-A
  - But unrealistic biologically

If Adult = 600 days (instead of 450):
  - More batches in sea simultaneously
  - More realistic (some farms go 2+ years to harvest)
```

---

## 🧮 Mathematical Constraints

### The Core Equation:

```
Instantaneous_Occupancy = Σ (Batches_in_Stage × Containers_per_Stage)

For each stage:
  Batches_in_Stage = Stage_Duration ÷ Stagger_Interval
  
Total:
  Occupancy = Σ(Stage_Duration[i] ÷ Stagger × Containers[i])
```

### To Achieve 85% (1,714 containers):

**Option A: Reduce Stagger to 12 days**
```
FW stages (90 days each):
  - 90 ÷ 12 = 7.5 batches per stage
  - 5 stages × 7.5 = 37.5 batches in FW
  - 37.5 × 10 = 375 FW containers occupied

Sea stage (450 days):
  - 450 ÷ 12 = 37.5 batches in Adult
  - 37.5 × 20 rings = 750 rings occupied
  
Total: 375 + 750 = 1,125 containers (56% - still not 85%!)
```

**Option B: Reduce Stagger to 5 days + Increase Adult Duration to 600 days**
```
FW stages (90 days each):
  - 90 ÷ 5 = 18 batches per stage
  - 5 stages × 18 = 90 batches in FW
  - 90 × 10 = 900 FW containers occupied (78% ✅)

Sea stage (600 days):
  - 600 ÷ 5 = 120 batches in Adult
  - BUT: Only 860 rings ÷ 20 = 43 full-area slots
  - Need to pack more: 120 ÷ 43 = 2.8 batches per area
  - Use 7 rings per batch: 120 × 7 = 840 rings occupied (98% ✅)

Total: 900 + 840 = 1,740 containers (86% ✅✅✅)
```

**Option C: Adjust Infrastructure (Add More FW, Reduce Sea)**
```
Current: 1,157 FW + 860 sea
Bottleneck: Sea fills up first at high saturation

Rebalance: 1,500 FW + 500 sea
  - More halls (realistic for land-based operations)
  - Fewer sea areas (some farms are primarily land-based)
```

---

## 🎯 Recommended Solution

### Phase 1: Keep Infrastructure As-Is

**Why:** Infrastructure represents realistic salmon farm (mix of FW + sea)

### Phase 2: Optimize Stagger + Ring Allocation

**Approach:**
1. **Reduce stagger to 12 days** (instead of 30)
   - More batches overlapping
   - 37 batches in Adult simultaneously
   
2. **Adjust ring allocation:**
   - First 23 batches: 20 rings each (full areas)
   - Next 14 batches: Need to pack (use 10-12 rings)
   - Dynamic allocation based on available space

3. **Result:**
   - Sea: 37 × avg 18 rings = 666 rings occupied (77%)
   - FW: 7 × 5 × 10 = 350 containers occupied (30%)
   - Total: ~1,016 containers (50% - better but not 85%)

### Phase 3: Extend Adult Stage Duration

**Biological rationale:** Some farms harvest at 24+ months

```
Adult stage: 600 days (instead of 450)
  - 600 ÷ 12 = 50 batches simultaneously
  - 50 × 16 avg rings = 800 rings (93% sea saturation ✅)
  - FW stays same: 350 containers
  - Total: 1,150 containers (57%)
```

---

## ❓ THE FUNDAMENTAL CONSTRAINT

**To achieve 85% saturation, we need one of:**

1. **Much shorter stagger** (5-10 days) = Unrealistic operationally
2. **Much longer stages** (extend Adult to 700+ days) = Some farms do this
3. **More batches per container** (impossible - container holds 1 batch at a time)
4. **Different infrastructure balance** (more FW capacity relative to sea)

**Question for optimization:**
- Is 85% saturation a hard requirement?
- Or is 50-60% acceptable (more realistic for actual operations)?
- Should we extend Adult stage to 600-700 days (biologically reasonable)?

---

## 🧮 Optimization Problem Statement (For Another AI)

**Given:**
```python
Infrastructure:
  FW_containers = 1,157  # Fixed (50 containers × 23 halls)
  Sea_rings = 860        # Fixed (20 rings × 43 areas)
  Total = 2,017

Batch Lifecycle:
  stages = [
    {'name': 'Egg&Alevin', 'duration': 90, 'containers': 10},
    {'name': 'Fry', 'duration': 90, 'containers': 10},
    {'name': 'Parr', 'duration': 90, 'containers': 10},
    {'name': 'Smolt', 'duration': 90, 'containers': 10},
    {'name': 'Post-Smolt', 'duration': 90, 'containers': 10},
    {'name': 'Adult', 'duration': adult_duration, 'containers': rings_per_batch}
  ]
  
  # Each batch progresses through stages sequentially
  # Each container can only host 1 batch at a time
```

**Variables to Optimize:**
```python
stagger_days: int          # Days between batch starts (current: 30)
adult_duration: int        # Days in Adult stage (current: 450, can extend to 600-900)
rings_per_batch: int       # Rings allocated per batch (current: 20, can reduce to 10-18)
total_batches: int         # Number of batches to generate
```

**Objective Function:**
```python
# Maximize instantaneous occupancy
def calculate_instantaneous_occupancy(stagger, adult_duration, rings_per_batch, total_batches):
    fw_occupancy = 0
    for stage in fw_stages:  # 5 stages × 90 days each
        batches_in_stage = stage['duration'] / stagger
        fw_occupancy += batches_in_stage * 10
    
    sea_occupancy = (adult_duration / stagger) * rings_per_batch
    
    total_occupancy = fw_occupancy + sea_occupancy
    saturation = total_occupancy / 2017
    
    return saturation

# Find: stagger, adult_duration, rings_per_batch, total_batches
# Such that: saturation ≈ 0.85
# Subject to:
#   - 5 ≤ stagger ≤ 30 (operational realism)
#   - 450 ≤ adult_duration ≤ 900 (biological limits)
#   - 8 ≤ rings_per_batch ≤ 20 (area capacity)
#   - total_batches ≤ freshwater_capacity (bottleneck check)
```

**Constraint Check:**
```python
# Freshwater bottleneck
max_simultaneous_fw_batches = 0
for stage in fw_stages:
    max_simultaneous_fw_batches += stage['duration'] / stagger

fw_capacity = 1157 / 10  # 115.7 halls available
if max_simultaneous_fw_batches > fw_capacity:
    return "Infeasible - freshwater bottleneck"

# Sea bottleneck
simultaneous_adult_batches = adult_duration / stagger
sea_capacity = 860 / rings_per_batch  # Available slots
if simultaneous_adult_batches > sea_capacity:
    return "Infeasible - sea bottleneck"
```

---

## 🎯 Quick Solutions to Explore

### Solution 1: Stagger = 12 days, Adult = 600 days
```python
stagger = 12
adult_duration = 600

FW occupancy:
  - Batches per stage: 90 / 12 = 7.5
  - Total FW: 7.5 × 5 stages × 10 = 375 containers

Sea occupancy:
  - Batches in Adult: 600 / 12 = 50
  - With 20 rings: 50 × 20 = 1,000 rings (EXCEEDS 860!) ❌
  - With 17 rings: 50 × 17 = 850 rings (99% ✅)

Total: 375 + 850 = 1,225 containers (61%)
```

### Solution 2: Stagger = 8 days, Adult = 540 days
```python
stagger = 8
adult_duration = 540

FW occupancy:
  - Batches per stage: 90 / 8 = 11.25
  - Total FW: 11.25 × 5 × 10 = 562 containers (49% ✅)

Sea occupancy:
  - Batches in Adult: 540 / 8 = 67.5
  - With 20 rings: 67.5 × 20 = 1,350 rings (EXCEEDS 860!) ❌
  - With 12 rings: 67.5 × 12 = 810 rings (94% ✅)

Total: 562 + 810 = 1,372 containers (68%)
```

### Solution 3: Stagger = 6 days, Adult = 480 days
```python
stagger = 6
adult_duration = 480

FW occupancy:
  - Batches per stage: 90 / 6 = 15
  - Total FW: 15 × 5 × 10 = 750 containers (65% ✅)

Sea occupancy:
  - Batches in Adult: 480 / 6 = 80
  - With 20 rings: 80 × 20 = 1,600 rings (EXCEEDS 860!) ❌
  - With 10 rings: 80 × 10 = 800 rings (93% ✅)

Total: 750 + 800 = 1,550 containers (77%)
```

### Solution 4: Stagger = 5 days, Adult = 450 days, Mixed Ring Allocation
```python
stagger = 5
adult_duration = 450

FW occupancy:
  - Batches per stage: 90 / 5 = 18
  - Total FW: 18 × 5 × 10 = 900 containers (78% ✅)

Sea occupancy:
  - Batches in Adult: 450 / 5 = 90
  - Available capacity: 860 rings
  - Average rings needed: 860 / 90 = 9.6 rings/batch
  - Use mix of 8-12 rings per batch (biomass-based)
  - Total: 860 rings (100% ✅)

Total: 900 + 860 = 1,760 containers (87% ✅✅✅)
```

---

## 🏆 RECOMMENDED: Solution 4

**Parameters:**
```yaml
stagger_days: 5
adult_duration_days: 450
rings_per_batch: 8-12 (variable, average 9.6)
total_batches: 450 (90 batches × 5-day stagger in Adult stage)
```

**Results:**
- ✅ 87% saturation (exceeds 85% target!)
- ✅ Freshwater: 78% (well-balanced)
- ✅ Sea: 100% (fully utilized)
- ✅ Biologically realistic (450-day Adult is standard)
- ✅ Operationally feasible (5-day stagger for high-volume farm)

**Computation:**
- 450 batches × avg 2.5 min/batch ÷ 14 workers = ~80 minutes generation
- Database: ~150 GB (450 batches)
- Events: ~140M environmental, ~25M feeding

---

## 🔧 Implementation Requirements

**Schedule Planner Updates:**
1. Support configurable stagger (5-30 days)
2. Variable ring allocation (8-20 based on availability)
3. Biomass-aware allocation (large batches → more rings)
4. Validate constraints (no exceeding capacity)

**Infrastructure Consideration:**
- Current infrastructure is PERFECT for 87% saturation! ✅
- No changes needed
- Just need smarter scheduling

---

## ⚠️ Operational Realism Check

**5-day stagger means:**
- New batch every 5 days
- 6 batches per month
- 72 batches per year
- High-volume operation (realistic for large integr

ated farm)

**Comparison to industry:**
- Small farm: 30-60 day stagger (low volume)
- Medium farm: 15-30 day stagger
- Large farm: 5-15 day stagger ✅ (our target)
- Industrial scale: 1-5 day stagger

**Verdict:** 5-day stagger is aggressive but realistic for large operation

---

## 📊 Summary Table

| Solution | Stagger | Adult Days | Rings/Batch | FW Sat | Sea Sat | Total Sat | Feasible? |
|----------|---------|------------|-------------|--------|---------|-----------|-----------|
| Current  | 30 days | 450 | 20 | 13% | 35% | 22% | ✅ Yes, low |
| Solution 1 | 12 days | 600 | 17 | 32% | 99% | 61% | ✅ Yes |
| Solution 2 | 8 days | 540 | 12 | 49% | 94% | 68% | ✅ Yes |
| Solution 3 | 6 days | 480 | 10 | 65% | 93% | 77% | ✅ Yes |
| **Solution 4** | **5 days** | **450** | **9.6** | **78%** | **100%** | **87%** | ✅ **BEST** |

---

## 🎯 Next Steps

**1. Update Schedule Planner:**
- Add `--stagger` parameter (default: 5)
- Add `--adult-duration` parameter (default: 450)
- Implement variable ring allocation (8-12 rings)
- Validate capacity constraints

**2. Generate Test Schedule:**
```bash
python generate_batch_schedule.py \
  --stagger 5 \
  --adult-duration 450 \
  --output config/schedule_87pct_saturation.yaml \
  --dry-run
```

**3. Verify Saturation:**
- Should show ~1,760 containers allocated
- 87% saturation
- Zero conflicts

**4. If Validated, Execute:**
- 450 batches with 5-day stagger
- Variable ring allocation
- 100% success rate (schedule-based)

---

**This is the optimization problem clearly stated. Solution 4 achieves 87% with realistic parameters!**

---

