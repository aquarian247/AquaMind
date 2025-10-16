# AquaMind Test Data Generation - Implementation Plan

**Version:** 2.0  
**Date:** 2025-10-14  
**Status:** 🟡 In Progress

---

## Executive Summary

This plan creates a **chronologically-correct, gradually-transitioning** data generation system where:
- ✅ All events happen in temporal order (day-by-day)
- ✅ Lifecycle transitions are gradual (10 days, 1 container/day)
- ✅ Environmental readings 100% linked to batch assignments
- ✅ Single hall occupancy per batch (no mixing)
- ✅ FIFO feed inventory with automatic history tracking

---

## Infrastructure Overview

### Scotland
- **10 Freshwater Stations**: 5 halls × 10 containers = 500 containers + 50 silos
- **20 Sea Areas**: 20 rings × 3 barges = 400 rings + 60 barges
- **Total**: 900 operational + 110 feed containers

### Faroe Islands
- **12 Freshwater Stations**: 5 halls × 10 containers = 600 containers + 60 silos
- **22 Sea Areas**: 20 rings × 3 barges = 440 rings + 66 barges
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

**Script**: `01_bootstrap_infrastructure.py`  
**Status**: ⬜ Not Started

### Checklist

#### 1.1 Geographies
- [x] Scotland (exists)
- [ ] Faroe Islands

#### 1.2 Scotland (10 stations × 5 halls)
- [ ] S-FW-01: Halls A-E, containers, silo, sensors
- [ ] S-FW-02: Halls A-E, containers, silo, sensors
- [ ] S-FW-03: Halls A-E, containers, silo, sensors
- [ ] S-FW-04: Halls A-E, containers, silo, sensors
- [ ] S-FW-05: Halls A-E, containers, silo, sensors
- [ ] S-FW-06: Halls A-E, containers, silo, sensors
- [ ] S-FW-07: Halls A-E, containers, silo, sensors
- [ ] S-FW-08: Halls A-E, containers, silo, sensors
- [ ] S-FW-09: Halls A-E, containers, silo, sensors
- [ ] S-FW-10: Halls A-E, containers, silo, sensors

#### 1.3 Scotland Sea (20 areas)
- [ ] S-SEA-01 to S-SEA-20: 20 rings + 3 barges each

#### 1.4 Faroe Islands (12 stations × 5 halls)
- [ ] FI-FW-01 to FI-FW-12: Same pattern as Scotland

#### 1.5 Faroe Islands Sea (22 areas)
- [ ] FI-SEA-01 to FI-SEA-22: 20 rings + 3 barges each

**Validation SQL**:
```sql
-- Expected counts
SELECT COUNT(*) FROM infrastructure_geography; -- 2
SELECT COUNT(*) FROM infrastructure_freshwaterstation; -- 22
SELECT COUNT(*) FROM infrastructure_hall; -- 110
SELECT COUNT(*) FROM infrastructure_container WHERE hall_id IS NOT NULL; -- 1100
SELECT COUNT(*) FROM infrastructure_area; -- 42
SELECT COUNT(*) FROM infrastructure_container WHERE area_id IS NOT NULL; -- 840
SELECT COUNT(*) FROM infrastructure_feedcontainer; -- 236
SELECT COUNT(*) FROM infrastructure_sensor; -- ~14,000
```

---

## Phase 2: Master Data Initialization

**Script**: `02_initialize_master_data.py`  
**Status**: ⬜ Not Started

### Checklist

#### 2.1 Species & Stages
- [ ] Atlantic Salmon species
- [ ] 6 Lifecycle stages (90 days each, Adult 400 days)

#### 2.2 Environmental Parameters (7 total)
- [ ] Dissolved Oxygen (%, 80-100% safe)
- [ ] CO2 (mg/L, <15 safe)
- [ ] pH (pH, 6.5-8.5 safe)
- [ ] Temperature (°C, 4-16 freshwater)
- [ ] NO2 (mg/L, <0.1 safe)
- [ ] NO3 (mg/L, <50 safe)
- [ ] NH4 (mg/L, <0.02 safe)

#### 2.3 Feed Types (6 total)
- [ ] Starter 0.5mm (Fry, 50% protein)
- [ ] Starter 1.0mm (Parr, 48% protein)
- [ ] Grower 2.0mm (Smolt, 45% protein)
- [ ] Grower 3.0mm (Post-Smolt, 43% protein)
- [ ] Finisher 4.5mm (Adult early, 40% protein)
- [ ] Finisher 6.0mm (Adult late, 38% protein)

#### 2.4 Initial Feed Inventory
- [ ] FeedPurchase records (236 total, dated -30 days)
- [ ] FeedContainerStock records (FIFO setup)
  - Silos: 5,000 kg each
  - Barges: 25,000 kg each

#### 2.5 Health Master Data
- [ ] 9 Health parameters (Gill, Eye, Wounds, Fin, Body, Swimming, Appetite, Mucous, Color)
- [ ] 7 Mortality reasons
- [ ] 5 Sample types
- [ ] 3 Vaccination types

#### 2.6 Test Users
- [ ] System Admin, Operator, Veterinarian, Manager

**Validation SQL**:
```sql
SELECT COUNT(*) FROM batch_lifecyclestage; -- 6
SELECT COUNT(*) FROM environmental_environmentalparameter; -- 7
SELECT COUNT(*) FROM inventory_feed; -- 6
SELECT COUNT(*) FROM inventory_feedpurchase; -- 236
SELECT COUNT(*) FROM inventory_feedcontainerstock; -- 236
SELECT COUNT(*) FROM health_healthparameter; -- 9
```

---

## Phase 3: Chronological Event Engine

**Script**: `03_chronological_event_engine.py`  
**Status**: ⬜ Not Started

### 3.1 Command Line Interface
```bash
python 03_chronological_event_engine.py \
    --start-date 2024-01-01 \
    --eggs 3500000 \
    --geography "Faroe Islands" \
    --batch-name "FI-2024-001"
```

### 3.2 Daily Event Schedule

**Each day processes in chronological order:**

| Time | Event | Frequency |
|------|-------|-----------|
| 06:00 | Morning environmental readings | All containers |
| 08:00 | Morning feeding | Fry-Adult stages |
| 10:00 | Mid-morning environmental | All containers |
| 13:00 | Mortality check | All assignments |
| 16:00 | Afternoon feeding | Fry-Adult stages |
| 18:00 | Evening environmental | All containers |
| 20:00 | Growth update (TGC) | All assignments |
| Monthly | Health journal entry | ~1/30 probability |
| Stage-based | Gradual transition | Days 90, 180, 270, 360, 450 |

### 3.3 Gradual Transition Logic

**10-day gradual transition** (1 container/day):

**Day 1-10**: Move containers sequentially from Hall X to Hall Y
- Day 1: Container 1 moves
- Day 2: Container 2 moves
- ...
- Day 10: Container 10 moves

**Special case (Post-Smolt → Adult)**:
- 10 tanks → 20 rings (split 1:2)
- Day 1: Tank 1 → Ring 1 + Ring 2 (50% population each)
- Day 10: Tank 10 → Ring 19 + Ring 20

**During transition (days 1-10)**:
- Batch has active assignments in BOTH stages
- All events (feeding, environmental, mortality) occur for both

### 3.4 Key Algorithms

**TGC Growth**:
```python
# W_final^(1/3) = W_initial^(1/3) + (TGC × temp × days)
final_weight_cbrt = initial_weight_cbrt + (tgc * avg_temp * days)
final_weight = final_weight_cbrt ** 3
```

**FIFO Feed Consumption**:
```python
# Consume oldest feed first, track costs automatically
stock_entries = FeedContainerStock.objects.filter(
    feed_container=silo,
    quantity_kg__gt=0
).order_by('purchase_date', 'created_at')
```

**Environmental Linkage** (CRITICAL FIX):
```python
EnvironmentalReading.objects.create(
    container=assignment.container,
    batch=assignment.batch,  # ALWAYS link to batch
    # ...other fields
)
```

### 3.5 Progress Tracking

Script maintains JSON progress file:
```json
{
  "batch_id": 123,
  "current_date": "2024-03-15",
  "days_processed": 74,
  "current_stage": "Fry",
  "transition_state": null,
  "events_created": {
    "environmental_readings": 7400,
    "feeding_events": 1480,
    "mortality_events": 12,
    "growth_samples": 10
  }
}
```

**Resume capability**: Re-run script picks up from last successful day.

---

## Phase 4: Data Purge Utility

**Script**: `04_purge_event_data.py`  
**Status**: ⬜ Not Started

### 4.1 What Gets Deleted
- [ ] Batches (`batch_batch`)
- [ ] Container assignments (`batch_batchcontainerassignment`)
- [ ] Transfers (`batch_batchtransfer`)
- [ ] Mortality events (`batch_mortalityevent`)
- [ ] Growth samples (`batch_growthsample`)
- [ ] Feeding events (`inventory_feedingevent`)
- [ ] Feed summaries (`inventory_batchfeedingsummary`, `inventory_containerfeedingsummary`)
- [ ] Environmental readings (`environmental_environmentalreading`)
- [ ] Health records (`health_*`)
- [ ] Feed stock movements (reset to initial)
- [ ] All history tables (auto-cascade)

### 4.2 What Gets Preserved
- [x] Geographies, Areas, Stations
- [x] Halls, Containers, Container Types
- [x] Sensors, Feed Containers
- [x] Lifecycle Stages, Species
- [x] Feed Types
- [x] Environmental Parameters
- [x] Health Parameters, Mortality Reasons, Sample Types

### 4.3 Usage
```bash
# Dry run (shows what would be deleted)
python 04_purge_event_data.py --dry-run

# Actual purge (requires confirmation)
python 04_purge_event_data.py --confirm

# Reset feed inventory to initial state
python 04_purge_event_data.py --confirm --reset-inventory
```

---

## Progress Tracking

### Overall Status
- [ ] Phase 1: Bootstrap Infrastructure
- [ ] Phase 2: Master Data Initialization
- [ ] Phase 3: Chronological Event Engine
- [ ] Phase 4: Data Purge Utility

### Session Log

**Session 1 (2025-10-14)**:
- Created implementation plan
- Status: Planning complete, ready to implement

---

## Validation Queries

After each phase, run validation:

```sql
-- Phase 1 Validation
SELECT 
    'Containers' as type,
    COUNT(*) as count,
    900 + 1040 as expected
FROM infrastructure_container
UNION ALL
SELECT 'Feed Containers', COUNT(*), 236 FROM infrastructure_feedcontainer
UNION ALL
SELECT 'Sensors', COUNT(*), 14000 FROM infrastructure_sensor;

-- Phase 2 Validation
SELECT 
    'Lifecycle Stages' as type,
    COUNT(*) as count,
    6 as expected
FROM batch_lifecyclestage
UNION ALL
SELECT 'Env Parameters', COUNT(*), 7 FROM environmental_environmentalparameter
UNION ALL
SELECT 'Feed Types', COUNT(*), 6 FROM inventory_feed;

-- Phase 3 Validation (after batch generation)
SELECT 
    'Batch Assignments' as type,
    COUNT(*) as count
FROM batch_batchcontainerassignment
WHERE batch_id = <batch_id>
UNION ALL
SELECT 
    'Environmental Readings',
    COUNT(*)
FROM environmental_environmentalreading
WHERE batch_id = <batch_id>
UNION ALL
SELECT 
    'Feeding Events',
    COUNT(*)
FROM inventory_feedingevent
WHERE batch_id = <batch_id>;

-- Verify environmental linkage (MUST be 100%)
SELECT 
    COUNT(*) FILTER (WHERE batch_id IS NOT NULL) * 100.0 / COUNT(*) as linkage_percent
FROM environmental_environmentalreading;
-- Expected: 100.00
```

---

## Next Steps

1. **Implement Phase 1**: Create `01_bootstrap_infrastructure.py`
2. **Run Phase 1**: Execute script, validate with SQL
3. **Implement Phase 2**: Create `02_initialize_master_data.py`
4. **Run Phase 2**: Execute script, validate
5. **Implement Phase 3**: Create `03_chronological_event_engine.py`
6. **Test Phase 3**: Generate one batch, validate environmental linkage
7. **Implement Phase 4**: Create `04_purge_event_data.py`
8. **Final Test**: Full cycle (generate → validate → purge → regenerate)
