# UAT Test Data Generation - Implementation Plan

**Created:** 2026-01-12
**Status:** In Progress
**Author:** Claude (AI Assistant)

---

## 1. Problem Statement

### The Time Perspective Challenge

AquaMind manages salmon batches with lifecycles spanning ~800-900 days. For User Acceptance Testing (UAT), this creates a fundamental problem:

1. **Real-time testing is impractical**: Testers cannot wait 2+ years to validate end-to-end workflows
2. **Speedrun limitation**: Compressing lifecycle to 2-4 weeks produces sparse, unrealistic data
3. **Random stage distribution**: Standard test data generation creates batches with arbitrary lifecycle positions

### What UAT Needs

- **Equal stage representation**: 8-10 active batches per lifecycle stage
- **Near-transition positioning**: Batches at critical workflow trigger points (Day ~85-90, ~175-180, etc.)
- **Substantial intra-stage data**: 60-80+ days of accumulated events within current stage
- **Fresh data**: Extending to TODAY for live forward projection testing

---

## 2. Solution: "Lifecycle Ladder" Distribution

### Concept

Instead of time-based staggering (batches starting X days apart), position batches at specific **lifecycle day targets** calculated backwards from today:

```
start_date = TODAY - target_day_number
```

This ensures each batch is at the exact lifecycle position we need for UAT on the day of testing.

### Target Distribution (per geography)

| Lifecycle Stage | Day Range | Target Positions | Purpose |
|-----------------|-----------|------------------|---------|
| **Egg & Alevin** | 1-90 | Day 30, 55, 75, 87, 90 | Early/mid/pre-transition |
| **Fry** | 91-180 | Day 110, 135, 160, 178 | Early/mid/near-transition |
| **Parr** | 181-270 | Day 200, 230, 250, 268 | Early/mid/near-transition |
| **Smolt** | 271-360 | Day 290, 320, 355 | Early/mid/FW→Sea critical |
| **Post-Smolt** | 361-450 | Day 380, 410, 445 | Early/mid/near-Adult |
| **Adult** | 451-900 | Day 500, 600, 700, 780, 820, 850 | Growth/pre-harvest/harvest-ready |
| **Completed** | >900 | Historical batches | Full lifecycle baseline |

**Total: ~136 batches** (68 per geography)
- ~56 strategically positioned active batches
- ~80 completed batches for historical data

---

## 3. Implementation Components

### 3.1 New Script: `generate_uat_schedule.py`

**Purpose**: Generate a deterministic schedule with batches at specific lifecycle positions

**Key Features**:
- Define `UAT_LIFECYCLE_TARGETS` with day positions and purposes
- Calculate `start_date = TODAY - day_number` for each target
- Allocate containers using existing conflict detection logic
- Include completed batches for historical depth
- Support geography-balanced distribution

**Output**: `config/schedule_uat.yaml`

### 3.2 New Script: `verify_uat_coverage.py`

**Purpose**: Validate that generated data has proper stage distribution for UAT

**Key Features**:
- Count active batches per lifecycle stage
- Identify batches near stage transition points
- Check for data freshness (events up to today)
- Report coverage gaps

### 3.3 Documentation Update: `test_data_generation_guide_v6.md`

**Purpose**: Add UAT approach as Option D alongside existing options

**Additions**:
- New section: "Option D: UAT-Optimized Distribution"
- Lifecycle ladder concept explanation
- Usage instructions
- Expected results

---

## 4. Critical Features to Test (from PRD Analysis)

### Tier 1: Core Lifecycle & Transitions

| Feature | Stage Positions Needed |
|---------|----------------------|
| Stage transitions (Egg→Fry→Parr→Smolt→Post-Smolt→Adult) | Day 85-90, 175-180, 265-270, 355-360, 445-450 |
| Transfer Workflows (especially FW→Sea) | Day 350-360 (Smolt→Post-Smolt) |
| Live Forward Projection | Active batches with fresh data |
| Growth Analysis (4-line chart) | 60+ days per stage |
| Harvest Planning | Adult batches Day 780-850 |

### Tier 2: Operational Planning

| Feature | Data Requirements |
|---------|------------------|
| PlannedActivity variance tracking | Mix of on-time/overdue activities |
| Health Sampling (9 parameters) | Monthly events in Post-Smolt/Adult |
| Vaccinations/Treatments | Post-Smolt and Adult batches |

### Tier 3: Executive & Financial

| Feature | Data Requirements |
|---------|------------------|
| Executive Dashboard (3 tiers) | PLANNED/PROJECTED/NEEDS_PLANNING mix |
| Intercompany Finance | FW→Sea transfers crossing subsidiaries |
| Harvest Facts | Completed batches with harvests |

---

## 5. Technical Design

### 5.1 UAT Lifecycle Targets Structure

```python
UAT_LIFECYCLE_TARGETS = [
    # Egg & Alevin (Stage 1, Order 1) - 5 positions
    {"day": 30,  "stage_order": 1, "purpose": "mid_stage"},
    {"day": 55,  "stage_order": 1, "purpose": "mid_stage"},
    {"day": 75,  "stage_order": 1, "purpose": "pre_transition"},
    {"day": 87,  "stage_order": 1, "purpose": "transition_ready"},
    {"day": 90,  "stage_order": 1, "purpose": "transition_imminent"},
    
    # Fry (Stage 2, Order 2) - 4 positions
    {"day": 110, "stage_order": 2, "purpose": "early_stage"},
    {"day": 135, "stage_order": 2, "purpose": "mid_stage"},
    {"day": 160, "stage_order": 2, "purpose": "mid_stage"},
    {"day": 178, "stage_order": 2, "purpose": "transition_ready"},
    
    # Parr (Stage 3, Order 3) - 4 positions
    {"day": 200, "stage_order": 3, "purpose": "early_stage"},
    {"day": 230, "stage_order": 3, "purpose": "mid_stage"},
    {"day": 250, "stage_order": 3, "purpose": "mid_stage"},
    {"day": 268, "stage_order": 3, "purpose": "transition_ready"},
    
    # Smolt (Stage 4, Order 4) - 3 positions (FW→Sea critical!)
    {"day": 290, "stage_order": 4, "purpose": "early_stage"},
    {"day": 320, "stage_order": 4, "purpose": "mid_stage"},
    {"day": 355, "stage_order": 4, "purpose": "transition_ready_critical"},
    
    # Post-Smolt (Stage 5, Order 5) - 3 positions
    {"day": 380, "stage_order": 5, "purpose": "early_stage"},
    {"day": 410, "stage_order": 5, "purpose": "mid_stage"},
    {"day": 445, "stage_order": 5, "purpose": "transition_ready"},
    
    # Adult (Stage 6, Order 6) - 6 positions (harvest critical)
    {"day": 500, "stage_order": 6, "purpose": "early_adult"},
    {"day": 600, "stage_order": 6, "purpose": "mid_adult"},
    {"day": 700, "stage_order": 6, "purpose": "late_adult"},
    {"day": 780, "stage_order": 6, "purpose": "pre_harvest"},
    {"day": 820, "stage_order": 6, "purpose": "harvest_threshold"},
    {"day": 850, "stage_order": 6, "purpose": "harvest_ready"},
]
```

### 5.2 Schedule Generation Algorithm

```python
def generate_uat_schedule():
    today = date.today()
    schedule = []
    
    # 1. Generate strategically positioned active batches
    for geo in ["Faroe Islands", "Scotland"]:
        for i, target in enumerate(UAT_LIFECYCLE_TARGETS):
            start_date = today - timedelta(days=target['day'])
            batch = plan_batch(
                geo=geo,
                start_date=start_date,
                duration=target['day'],  # Runs exactly to today
                batch_index=i,
                purpose=target['purpose']
            )
            schedule.append(batch)
    
    # 2. Generate completed batches for historical depth
    # Start from oldest date (5+ years ago) with wider stagger
    historical_start = today - timedelta(days=5*365)
    for geo in ["Faroe Islands", "Scotland"]:
        for i in range(40):  # ~40 completed batches per geo
            start_date = historical_start + timedelta(days=i * 30)
            duration = 900  # Full lifecycle
            batch = plan_batch(geo, start_date, duration, ...)
            schedule.append(batch)
    
    return schedule
```

### 5.3 Container Allocation Strategy

Reuse existing logic from `generate_batch_schedule.py`:
- Independent hall allocation per stage
- Conflict detection via occupancy tracking
- Sea ring allocation with fallback sizes

---

## 6. Execution Workflow

```bash
# 1. Wipe operational data
echo "DELETE" | python scripts/data_generation/00_wipe_operational_data.py --confirm

# 2. Initialize master data (if needed)
python scripts/data_generation/01_initialize_scenario_master_data.py
python scripts/data_generation/01_initialize_finance_policies.py
python scripts/data_generation/01_initialize_health_parameters.py
python scripts/data_generation/01_initialize_activity_templates.py

# 3. Generate UAT-optimized schedule
python scripts/data_generation/generate_uat_schedule.py \
  --output config/schedule_uat.yaml

# 4. Execute schedule (~45-60 min)
SKIP_CELERY_SIGNALS=1 python scripts/data_generation/execute_batch_schedule.py \
  config/schedule_uat.yaml \
  --workers 14 --use-partitions \
  --log-dir scripts/data_generation/logs/uat

# 5. Run Growth Analysis (~8-10 min)
python scripts/data_generation/run_growth_analysis_optimized.py --workers 4

# 6. Seed Planned Activities
python scripts/data_generation/seed_planned_activities.py

# 7. Verify UAT coverage
python scripts/data_generation/verify_uat_coverage.py
```

---

## 7. Expected Results

| Metric | Expected Value |
|--------|----------------|
| **Total Batches** | ~136 (68 per geography) |
| **Active Batches** | ~56 (28 per geography) |
| **Completed Batches** | ~80 (40 per geography) |
| **Batches per Active Stage** | 6-10 |
| **Batches at Transition Points** | 3-4 per boundary |
| **Batches near Harvest** | 6 (Day 780-850) |
| **Data Freshness** | Up to TODAY |
| **Total Generation Time** | ~55-70 minutes |

---

## 8. Files to Create/Modify

### New Files
- `scripts/data_generation/generate_uat_schedule.py`
- `scripts/data_generation/verify_uat_coverage.py`
- `aquamind/docs/progress/uat_test_data/UAT_TEST_DATA_IMPLEMENTATION_PLAN.md` (this file)

### Modified Files
- `aquamind/docs/database/test_data_generation/test_data_generation_guide_v6.md` (add Option D)

---

## 9. Success Criteria

- [ ] `generate_uat_schedule.py` creates valid schedule with lifecycle ladder distribution
- [ ] Schedule passes validation (zero container conflicts)
- [ ] Execution completes with 100% success rate
- [ ] `verify_uat_coverage.py` confirms:
  - [ ] 6-10 batches per active lifecycle stage
  - [ ] 3-4 batches at each transition boundary
  - [ ] Data extends to today's date
  - [ ] All 6 lifecycle stages represented in active batches
- [ ] Documentation updated in test_data_generation_guide_v6.md
