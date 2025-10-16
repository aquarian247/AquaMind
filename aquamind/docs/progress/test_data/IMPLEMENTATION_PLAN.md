# AquaMind Test Data Generation - Implementation Plan

**Version:** 2.0  
**Date:** 2025-10-14  
**Status:** 🟡 In Progress  
**Location:** `/aquamind/docs/progress/test_data/`

---

## Executive Summary

This plan creates a **chronologically-correct, gradually-transitioning** data generation system where:
- ✅ All events happen in temporal order (day-by-day)
- ✅ Lifecycle transitions are gradual (10 days, 1 container/day)
- ✅ Environmental readings 100% linked to batch assignments
- ✅ Single hall occupancy per batch (no mixing)
- ✅ FIFO feed inventory with automatic history tracking
- ✅ Multi-station support for distributed batch generation

---

## Infrastructure Overview

### Scotland
- **10 Freshwater Stations** (S-FW-01 to S-FW-10): 5 halls × 10 containers = 500 containers + 50 silos
- **20 Sea Areas** (S-SEA-01 to S-SEA-20): 20 rings × 3 barges = 400 rings + 60 barges
- **Total**: 900 operational + 110 feed containers

### Faroe Islands
- **12 Freshwater Stations** (FI-FW-01 to FI-FW-12): 5 halls × 10 containers = 600 containers + 60 silos
- **22 Sea Areas** (FI-SEA-01 to FI-SEA-22): 20 rings × 3 barges = 440 rings + 66 barges
- **Total**: 1,040 operational + 126 feed containers

### Container Mapping
| Stage | Hall | Type | Count | Split |
|-------|------|------|-------|-------|
| Egg/Alevin | A | Trays | 10 | → 10 |
| Fry | B | Small Tanks | 10 | → 10 |
| Parr | C | Medium Tanks | 10 | → 10 |
| Smolt | D | Large Tanks | 10 | → 10 |
| Post-Smolt | E | Pre-Transfer | 10 | → 20 |
| Adult | Sea | Rings | 20 | Final |

---

## Phase 1: Bootstrap Infrastructure

**Script**: `scripts/data_generation/01_bootstrap_infrastructure.py`  
**Status**: ✅ Ready to Run  
**Duration**: ~5-10 minutes

### Checklist

#### 1.1 Geographies
- [x] Scotland (exists)
- [ ] Faroe Islands

#### 1.2 Scotland (10 stations × 5 halls)
- [ ] S-FW-01: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-02: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-03: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-04: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-05: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-06: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-07: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-08: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-09: Halls A-E, 50 containers, silo, 350 sensors
- [ ] S-FW-10: Halls A-E, 50 containers, silo, 350 sensors

#### 1.3 Scotland Sea (20 areas)
- [ ] S-SEA-01 to S-SEA-20: 20 rings + 3 barges each (80 sensors/area)

#### 1.4 Faroe Islands (12 stations × 5 halls)
- [ ] FI-FW-01 to FI-FW-12: Same pattern as Scotland

#### 1.5 Faroe Islands Sea (22 areas)
- [ ] FI-SEA-01 to FI-SEA-22: 20 rings + 3 barges each

### Run Command
```bash
cd /Users/aquarian247/Projects/AquaMind
python scripts/data_generation/01_bootstrap_infrastructure.py
```

### Validation SQL
```sql
-- Expected counts
SELECT COUNT(*) FROM infrastructure_geography; -- 2
SELECT COUNT(*) FROM infrastructure_freshwaterstation; -- 22
SELECT COUNT(*) FROM infrastructure_hall; -- 110
SELECT COUNT(*) FROM infrastructure_container WHERE hall_id IS NOT NULL; -- 1100
SELECT COUNT(*) FROM infrastructure_area; -- 42
SELECT COUNT(*) FROM infrastructure_container WHERE area_id IS NOT NULL; -- 840
SELECT COUNT(*) FROM infrastructure_feedcontainer; -- 236
SELECT COUNT(*) FROM infrastructure_sensor; -- ~11,000
```

**Phase 1 Complete**: [ ] (Date: _________)

---

## Phase 2: Master Data Initialization

**Script**: `scripts/data_generation/02_initialize_master_data.py`  
**Status**: ⬜ Not Started  
**Duration**: ~1-2 minutes

### Checklist

#### 2.1 Species & Stages
- [ ] Atlantic Salmon species
- [ ] 6 Lifecycle stages (Egg/Alevin, Fry, Parr, Smolt, Post-Smolt, Adult)
  - Duration: 90 days each (Adult: 400 days)

#### 2.2 Environmental Parameters (7 total)
- [ ] Dissolved Oxygen (%, safe: 80-100%, critical: <30%)
- [ ] CO2 (mg/L, safe: <15, critical: >25)
- [ ] pH (pH, safe: 6.5-8.5, critical: <6.0 or >9.0)
- [ ] Temperature (°C, freshwater: 4-16, seawater: 6-18)
- [ ] NO2 (mg/L, safe: <0.1, critical: >0.5)
- [ ] NO3 (mg/L, safe: <50, critical: >100)
- [ ] NH4 (mg/L, safe: <0.02, critical: >0.1)

#### 2.3 Feed Types (6 total)
- [ ] Starter 0.5mm (Fry, Protein: 50%, Fat: 18%, Carb: 20%)
- [ ] Starter 1.0mm (Parr, Protein: 48%, Fat: 18%, Carb: 22%)
- [ ] Grower 2.0mm (Smolt, Protein: 45%, Fat: 20%, Carb: 23%)
- [ ] Grower 3.0mm (Post-Smolt, Protein: 43%, Fat: 22%, Carb: 23%)
- [ ] Finisher 4.5mm (Adult early, Protein: 40%, Fat: 24%, Carb: 24%)
- [ ] Finisher 6.0mm (Adult late, Protein: 38%, Fat: 26%, Carb: 24%)

#### 2.4 Initial Feed Inventory
- [ ] 236 FeedPurchase records (dated -30 days from today)
  - Cost per kg: €1.80-2.80 (varies by feed type)
  - Supplier rotation: 3-4 major suppliers
- [ ] 236 FeedContainerStock records (FIFO setup)
  - Silos: 5,000 kg each × 110 = 550,000 kg
  - Barges: 25,000 kg each × 126 = 3,150,000 kg
  - **Total**: 3,700,000 kg initial inventory

#### 2.5 Health Master Data
- [ ] 9 Health parameters (Gill, Eye, Wounds, Fin, Body, Swimming, Appetite, Mucous, Color)
- [ ] 7 Mortality reasons (Natural, Disease, Stress, Handling, Predation, Environmental, Unknown)
- [ ] 5 Sample types (Blood, Tissue, Gill, Kidney, Fecal)
- [ ] 3 Vaccination types (IPN, VHS, Multi-component)

#### 2.6 Test Users
- [ ] System Admin (username: system_admin)
- [ ] Farm Operator (username: operator_01)
- [ ] Veterinarian (username: vet_01)
- [ ] Manager (username: manager_01)

### Run Command
```bash
python scripts/data_generation/02_initialize_master_data.py
```

### Validation SQL
```sql
SELECT COUNT(*) FROM batch_species; -- 1
SELECT COUNT(*) FROM batch_lifecyclestage; -- 6
SELECT COUNT(*) FROM environmental_environmentalparameter; -- 7
SELECT COUNT(*) FROM inventory_feed; -- 6
SELECT COUNT(*) FROM inventory_feedpurchase; -- 236
SELECT COUNT(*) FROM inventory_feedcontainerstock; -- 236
SELECT COUNT(*) FROM health_healthparameter; -- 9
SELECT COUNT(*) FROM auth_user WHERE username LIKE '%_01' OR username = 'system_admin'; -- 4
```

**Phase 2 Complete**: [ ] (Date: _________)

---

## Phase 3: Chronological Event Engine

**Script**: `scripts/data_generation/03_chronological_event_engine.py`  
**Status**: ⬜ Not Started  
**Duration**: ~30-60 minutes per batch (850 days simulated)

### 3.1 Command Line Interface

```bash
python scripts/data_generation/03_chronological_event_engine.py \
    --start-date 2024-01-01 \
    --eggs 3500000 \
    --geography "Faroe Islands" \
    --station "FI-FW-01" \
    --sea-area "FI-SEA-01" \
    --batch-name "FI-2024-001"

# Alternative: Auto-select available station and sea area
python scripts/data_generation/03_chronological_event_engine.py \
    --start-date 2024-01-01 \
    --eggs 3500000 \
    --geography "Scotland" \
    --batch-name "SCO-2024-001"
    # Script will automatically select first available station/area
```

### 3.2 Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--start-date` | Yes | Batch start date | `2024-01-01` |
| `--eggs` | Yes | Initial egg count | `3500000` |
| `--geography` | Yes | Geography name | `"Faroe Islands"` or `"Scotland"` |
| `--station` | No | Specific freshwater station | `"FI-FW-01"` (auto-select if omitted) |
| `--sea-area` | No | Specific sea area | `"FI-SEA-01"` (auto-select if omitted) |
| `--batch-name` | No | Batch identifier | `"FI-2024-001"` (auto-generate if omitted) |
| `--resume` | No | Resume from progress file | Flag (no value) |

**Station/Area Selection Logic:**
- If `--station` specified: Use that station (error if unavailable)
- If not specified: Auto-select first available station with all halls free
- If `--sea-area` specified: Use that area (error if insufficient rings)
- If not specified: Auto-select first area with 20+ free rings

### 3.3 Daily Event Schedule

**Each day processes in chronological order:**

| Time | Event | Frequency | Stages |
|------|-------|-----------|--------|
| 06:00 | Morning environmental readings | Daily | All |
| 08:00 | Morning feeding | 1-4× daily | Fry-Adult |
| 10:00 | Mid-morning environmental | Daily | All |
| 13:00 | Mortality check & registration | Daily | All |
| 16:00 | Afternoon feeding | 1-4× daily | Fry-Adult |
| 18:00 | Evening environmental | Daily | All |
| 20:00 | Growth update (TGC) | Daily | All |
| Monthly | Health journal entry | ~1/month | All |
| Weekly | Growth sample | Weekly | All |
| Stage-end | Gradual transition start | 5× lifecycle | All |

**Feeding Frequency by Stage:**
- Egg/Alevin: None
- Fry: 4× daily (6am, 10am, 2pm, 6pm)
- Parr: 4× daily
- Smolt: 3× daily (6am, 12pm, 6pm)
- Post-Smolt: 2× daily (8am, 4pm)
- Adult: 2× daily (8am, 4pm)

### 3.4 Gradual Transition Logic

**10-day gradual transition** (1 container/day):

**Standard Transition (e.g., Fry → Parr)**:
- Day 1: Container 1 moves from Hall B to Hall C
- Day 2: Container 2 moves
- ...
- Day 10: Container 10 moves
- Result: 10 containers in new hall

**Special case (Post-Smolt → Adult)**:
- 10 tanks → 20 rings (split 1:2 ratio)
- Day 1: Tank 1 → Ring 1 + Ring 2 (50% population each)
- Day 2: Tank 2 → Ring 3 + Ring 4
- ...
- Day 10: Tank 10 → Ring 19 + Ring 20
- Result: 20 rings in sea area

**During transition (days 1-10)**:
- Batch has active assignments in BOTH stages
- All daily events occur for containers in both locations
- Environmental readings, feeding, mortality checks for all active assignments

### 3.5 Key Algorithms

**TGC Growth Calculation**:
```python
# Thermal Growth Coefficient: W_final^(1/3) = W_initial^(1/3) + (TGC × temp × days)
initial_cbrt = initial_weight_g ** (1/3)
growth_increment = tgc_coefficient * avg_temp_celsius * days
final_cbrt = initial_cbrt + growth_increment
final_weight_g = final_cbrt ** 3

# TGC values by stage:
# Fry: 2.2, Parr: 2.7, Smolt: 2.9, Post-Smolt: 3.2, Adult: 3.0
```

**FIFO Feed Consumption**:
```python
# Consume oldest feed first, track costs automatically
stock_entries = FeedContainerStock.objects.filter(
    feed_container=silo,
    feed_purchase__feed=feed_type,
    quantity_kg__gt=0
).order_by('purchase_date', 'created_at')  # FIFO order

for stock in stock_entries:
    consumed = min(stock.quantity_kg, remaining_needed)
    cost = consumed * stock.cost_per_kg
    stock.quantity_kg -= consumed
    stock.save()  # Auto-creates history entry
```

**Environmental Linkage** (CRITICAL FIX):
```python
# EVERY environmental reading MUST link to active batch
EnvironmentalReading.objects.create(
    reading_time=datetime_with_hour,
    sensor=sensor,
    parameter=parameter,
    value=value,
    container=assignment.container,
    batch=assignment.batch,  # CRITICAL: Always populated
    is_manual=False
)
```

**Mortality Calculation**:
```python
# Stage-based daily mortality rates (stochastic)
base_rates = {
    'Egg/Alevin': 0.0015,  # 0.15% daily (~13.5% cumulative)
    'Fry': 0.0005,         # 0.05% daily (~4.5% cumulative)
    'Parr': 0.0003,        # 0.03% daily (~2.7% cumulative)
    'Smolt': 0.0002,       # 0.02% daily (~1.8% cumulative)
    'Post-Smolt': 0.00015, # 0.015% daily (~1.35% cumulative)
    'Adult': 0.0001,       # 0.01% daily (~4% over 400 days)
}

# Apply environmental stress multipliers and Poisson distribution
expected_mortality = population * base_rate * temp_stress * oxygen_stress
actual_mortality = np.random.poisson(expected_mortality)
```

### 3.6 Progress Tracking

**Progress File**: `aquamind/docs/progress/test_data/batch_{batch_id}_progress.json`

```json
{
  "batch_id": 123,
  "batch_name": "FI-2024-001",
  "geography": "Faroe Islands",
  "station": "FI-FW-01",
  "sea_area": "FI-SEA-01",
  "start_date": "2024-01-01",
  "current_date": "2024-03-15",
  "days_processed": 74,
  "total_days": 850,
  "current_stage": "Fry",
  "transition_state": null,
  "events_created": {
    "environmental_readings": 7400,
    "feeding_events": 1480,
    "mortality_events": 12,
    "growth_samples": 10,
    "health_journals": 2
  },
  "current_metrics": {
    "population": 3387500,
    "avg_weight_g": 1.5,
    "biomass_kg": 5081.25
  },
  "last_checkpoint": "2024-03-14T20:00:00Z"
}
```

**Resume Capability**: 
- Script saves progress every 10 days
- Re-run with `--resume` flag picks up from last checkpoint
- Idempotent: Safe to re-run same day multiple times

### 3.7 Output Summary

**Per batch generation (3.5M eggs, 850 days):**
- ~17,850 Environmental readings (7 params × 3 readings/day × 850 days)
- ~6,800 Feeding events (2-4 per day, stage-dependent)
- ~850 Mortality checks (1 per day)
- ~120 Growth samples (weekly)
- ~28 Health journal entries (monthly)
- ~60 Container assignments (10 per stage × 6 stages)
- 5 Batch transfers (stage transitions)
- **Total**: ~25,708 events + history entries

### 3.8 Multi-Batch Strategy

**For realistic operations (40-50 active batches):**

```bash
# Generate batches across different stations with staggered start dates
for i in {1..10}; do
    python scripts/data_generation/03_chronological_event_engine.py \
        --start-date $(date -d "2024-01-01 +$((i*30)) days" +%Y-%m-%d) \
        --eggs 3500000 \
        --geography "Faroe Islands" \
        --station "FI-FW-$(printf '%02d' $i)" \
        --batch-name "FI-2024-$(printf '%03d' $i)"
done
```

### Run Command Examples
```bash
# Example 1: Specific station and area
python scripts/data_generation/03_chronological_event_engine.py \
    --start-date 2024-01-01 \
    --eggs 3500000 \
    --geography "Faroe Islands" \
    --station "FI-FW-01" \
    --sea-area "FI-SEA-01" \
    --batch-name "FI-2024-001"

# Example 2: Auto-select (finds first available)
python scripts/data_generation/03_chronological_event_engine.py \
    --start-date 2024-02-01 \
    --eggs 3200000 \
    --geography "Scotland" \
    --batch-name "SCO-2024-001"

# Example 3: Resume interrupted batch
python scripts/data_generation/03_chronological_event_engine.py \
    --batch-name "FI-2024-001" \
    --resume
```

### Validation SQL
```sql
-- After batch generation, verify linkage
SET @batch_id = 123;  -- Replace with actual batch ID

SELECT 
    'Batch Assignments' as metric,
    COUNT(*) as count,
    60 as expected  -- 10 per stage × 6 stages
FROM batch_batchcontainerassignment
WHERE batch_id = @batch_id

UNION ALL

SELECT 
    'Environmental Readings',
    COUNT(*),
    17850  -- Approximate
FROM environmental_environmentalreading
WHERE batch_id = @batch_id

UNION ALL

SELECT 
    'Feeding Events',
    COUNT(*),
    6800  -- Approximate
FROM inventory_feedingevent
WHERE batch_id = @batch_id;

-- CRITICAL: Verify 100% environmental linkage
SELECT 
    COUNT(*) FILTER (WHERE batch_id IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) as linkage_percent
FROM environmental_environmentalreading;
-- MUST BE: 100.00
```

**Phase 3 Complete**: [ ] (Date: _________)

---

## Phase 4: Data Purge Utility

**Script**: `scripts/data_generation/04_purge_event_data.py`  
**Status**: ⬜ Not Started  
**Duration**: ~2-5 minutes

### 4.1 What Gets Deleted
- [ ] All batches (`batch_batch`)
- [ ] Container assignments (`batch_batchcontainerassignment`)
- [ ] Transfers (`batch_batchtransfer`)
- [ ] Mortality events (`batch_mortalityevent`)
- [ ] Growth samples (`batch_growthsample`)
- [ ] Feeding events (`inventory_feedingevent`)
- [ ] Feed summaries (`inventory_batchfeedingsummary`, `inventory_containerfeedingsummary`)
- [ ] Environmental readings (`environmental_environmentalreading`)
- [ ] Health records (all `health_*` event tables)
- [ ] Feed stock movements (resets to initial state)
- [ ] All history tables (automatic cascade via django-simple-history)

### 4.2 What Gets Preserved
- [x] Geographies, Areas, Stations, Halls
- [x] Containers, Container Types
- [x] Sensors, Feed Containers
- [x] Lifecycle Stages, Species
- [x] Feed Types, Feed Purchases (initial)
- [x] Environmental Parameters
- [x] Health Parameters, Mortality Reasons, Sample Types, Vaccination Types
- [x] Users

### 4.3 Usage

```bash
# Dry run (shows what would be deleted, no actual deletion)
python scripts/data_generation/04_purge_event_data.py --dry-run

# Purge specific batch
python scripts/data_generation/04_purge_event_data.py --batch-id 123 --confirm

# Purge all event data
python scripts/data_generation/04_purge_event_data.py --all --confirm

# Reset feed inventory to initial state after purge
python scripts/data_generation/04_purge_event_data.py --all --confirm --reset-inventory
```

### 4.4 Safety Features
- Requires explicit `--confirm` flag
- Shows detailed deletion plan before execution
- Confirms master data preservation
- Validates infrastructure integrity after purge

### Run Command
```bash
# Recommended: Always dry-run first
python scripts/data_generation/04_purge_event_data.py --dry-run

# Then confirm
python scripts/data_generation/04_purge_event_data.py --all --confirm
```

**Phase 4 Complete**: [ ] (Date: _________)

---

## Progress Tracking

### Overall Status
- [ ] Phase 1: Bootstrap Infrastructure
- [ ] Phase 2: Master Data Initialization
- [ ] Phase 3: Chronological Event Engine
- [ ] Phase 4: Data Purge Utility

### Session Log

**Session 1 (2025-10-14 11:30)**:
- Created implementation plan
- Implemented Phase 1 script
- Added station/area parameter support
- Status: Phase 1 ready for execution

**Session 2** (Date: _________):
- 

---

## Quick Reference

### File Locations
```
AquaMind/
├── scripts/data_generation/
│   ├── 01_bootstrap_infrastructure.py
│   ├── 02_initialize_master_data.py
│   ├── 03_chronological_event_engine.py
│   └── 04_purge_event_data.py
└── aquamind/docs/progress/test_data/
    ├── IMPLEMENTATION_PLAN.md (this file)
    ├── batch_{id}_progress.json (per batch)
    └── session_log.md
```

### Execution Order
```bash
# 1. Bootstrap (one time)
python scripts/data_generation/01_bootstrap_infrastructure.py

# 2. Initialize (one time)
python scripts/data_generation/02_initialize_master_data.py

# 3. Generate batches (multiple times, different stations)
python scripts/data_generation/03_chronological_event_engine.py \
    --start-date YYYY-MM-DD \
    --eggs 3500000 \
    --geography "Geography Name" \
    --station "Station-ID" \
    --batch-name "Batch-Name"

# 4. Purge when needed
python scripts/data_generation/04_purge_event_data.py --all --confirm
```

### Key Validation Checkpoints
1. **After Phase 1**: Verify container counts match expected (1,940 operational, 236 feed)
2. **After Phase 2**: Verify master data counts (7 env params, 6 feed types, etc.)
3. **After Phase 3**: Verify 100% environmental linkage to batches
4. **After Phase 4**: Verify infrastructure preserved, events deleted

---

## Next Actions

**Immediate (Session 1)**:
1. ✅ Create implementation plan
2. ✅ Implement Phase 1 script
3. ⬜ Run Phase 1 and validate
4. ⬜ Implement Phase 2 script

**Next Session**:
1. Implement Phase 3 script (event engine)
2. Implement Phase 4 script (purge utility)
3. Full end-to-end test
4. Multi-batch generation test
