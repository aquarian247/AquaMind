# AquaMind Test Data Generation Guide

**Last Updated:** 2025-10-14  
**Version:** 1.0  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Phase Scripts](#phase-scripts)
5. [Running the Scripts](#running-the-scripts)
6. [Data Cleanup](#data-cleanup)
7. [Troubleshooting](#troubleshooting)
8. [Performance Notes](#performance-notes)

---

## Overview

The AquaMind test data generation system creates realistic, chronologically-correct aquaculture data spanning multiple years. The system generates:

- **Infrastructure**: Geographies, stations, halls, containers, sensors, feed systems
- **Master Data**: Species, lifecycle stages, environmental parameters, feed types
- **Batch Operations**: Complete lifecycle tracking (Egg → Fry → Parr → Smolt → Post-Smolt → Adult)
- **Environmental Data**: 6 readings/day/sensor with batch linkage
- **Feed Management**: FIFO consumption with automatic reordering
- **Health Data**: Mortality events, growth samples, journal entries
- **Audit Trails**: Complete historical tracking via django-simple-history

**Total Events per 650-day batch:** ~300,000 events

---

## Architecture

### Multi-Phase Approach

The data generation follows a 4-phase approach:

```
Phase 1: Infrastructure
  ├─ Geographies (Faroe Islands, Scotland)
  ├─ Freshwater Stations (5 per geography)
  ├─ Halls (5 per station: A-E)
  ├─ Containers (10 per hall)
  ├─ Sensors (7 types per container)
  ├─ Sea Areas (3 per geography)
  ├─ Sea Cages (30 per area)
  └─ Feed Systems (silos, barges)

Phase 2: Master Data
  ├─ Species (Atlantic Salmon)
  ├─ Lifecycle Stages (6 stages)
  ├─ Environmental Parameters (7 types)
  ├─ Feed Types (6 types by stage)
  ├─ Initial Feed Inventory
  └─ System User

Phase 3: Event Engine (THE CORE)
  ├─ Batch Creation
  ├─ Daily Event Processing:
  │   ├─ Environmental Readings (6/day, bulk insert)
  │   ├─ Feeding Events (2/day)
  │   ├─ Mortality Checks (probabilistic)
  │   ├─ Growth Updates (TGC-based)
  │   ├─ Stage Transitions (every 90 days)
  │   └─ Feed Auto-Reordering (FIFO)
  └─ Historical Audit Trail

Phase 4: Dashboards (Future)
  └─ Multi-batch parallel generation
```

### Key Design Principles

1. **Chronological Correctness**: Events occur in strict temporal order
2. **Batch Isolation**: Each batch operates independently
3. **FIFO Inventory**: Feed consumed oldest-first with cost tracking
4. **Realistic Growth**: TGC (Thermal Growth Coefficient) based calculations
5. **Stage Transitions**: Automatic progression through lifecycle stages
6. **Audit Trail**: All changes tracked via django-simple-history

---

## Prerequisites

### System Requirements

- **Python**: 3.11+
- **Django**: 4.2+
- **PostgreSQL**: 14+
- **RAM**: 8GB minimum (16GB+ recommended for large batches)
- **Storage**: ~500MB per 650-day batch

### Database Setup

Ensure migrations are applied:

```bash
cd /Users/aquarian247/Projects/AquaMind
python manage.py migrate
```

### Environment Variables

```bash
export DJANGO_SETTINGS_MODULE='aquamind.settings'
export PYTHONPATH=/Users/aquarian247/Projects/AquaMind
```

---

## Phase Scripts

### Phase 1: Bootstrap Infrastructure

**Location:** `scripts/data_generation/01_bootstrap_infrastructure.py`

**Purpose:** Creates all physical and logical infrastructure (one-time setup)

**Features:**
- Idempotent (safe to run multiple times)
- Creates 1,100+ containers
- Sets up 2 geographies (Faroe Islands, Scotland)
- Configures sensors and feed systems

**Runtime:** ~5-10 seconds

---

### Phase 2: Initialize Master Data

**Location:** `scripts/data_generation/02_initialize_master_data.py`

**Purpose:** Sets up species, stages, parameters, and initial feed inventory

**Features:**
- Idempotent (safe to run multiple times)
- Creates lifecycle stages (Egg&Alevin → Fry → Parr → Smolt → Post-Smolt → Adult)
- Initializes feed inventory (10 tonnes per silo)
- Sets **realistic feed container capacities:**
  - Fry/Parr Halls (A-C): 10-15 tonnes
  - Smolt Halls (D): 20 tonnes
  - Post-Smolt Halls (E): 30 tonnes
  - Sea Cages: 50 tonnes (barge silos)

**Runtime:** ~10-15 seconds

---

### Phase 3: Chronological Event Engine

**Location:** `scripts/data_generation/03_event_engine_core.py`

**Purpose:** Generates day-by-day batch lifecycle events

**Features:**
- **Batch Creation:** Auto-incrementing batch numbers
- **Stage Transitions:** Automatic every 90 days
- **Environmental Readings:** 6/day × 7 sensors × 10 containers = 420/day
- **Feeding Events:** 2/day (morning & afternoon) with FIFO consumption
- **Mortality Events:** Probabilistic based on stage-specific rates
- **Growth Updates:** Daily TGC-based weight calculations
- **Feed Auto-Reorder:** Triggers when stock < 20% capacity (3-day delivery)
- **Audit Trail:** All changes tracked in history tables

**Performance:** 
- 200-day batch: ~3-5 minutes
- 650-day batch: ~15-25 minutes
- Uses bulk inserts (500 records/batch) for optimal performance

**Parameters:**

```bash
--start-date YYYY-MM-DD  # Batch start date
--eggs INTEGER           # Initial egg count (default: 3,500,000)
--geography STRING       # "Faroe Islands" or "Scotland"
--duration INTEGER       # Number of days to simulate (default: 650)
```

**Runtime:** ~20-30 minutes for 650-day batch

---

## Running the Scripts

### Fresh Start (Recommended First Run)

```bash
cd /Users/aquarian247/Projects/AquaMind

# Step 1: Clean existing data (if any)
python scripts/data_generation/cleanup_batch_data.py

# Step 2: Setup infrastructure (one-time)
python scripts/data_generation/01_bootstrap_infrastructure.py

# Step 3: Initialize master data (one-time)
python scripts/data_generation/02_initialize_master_data.py

# Step 4: Generate batch data (repeatable)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2024-01-03 \
  --eggs 3500000 \
  --geography "Faroe Islands" \
  --duration 650
```

### Generate Additional Batches

```bash
# Generate a second batch (different start date)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2024-03-01 \
  --eggs 3200000 \
  --geography "Scotland" \
  --duration 500

# Generate a third batch (different geography)
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2024-06-15 \
  --eggs 3800000 \
  --geography "Faroe Islands" \
  --duration 700
```

### Generate Historical Data Ending Today

To create a batch that ends exactly today:

```python
from datetime import date, timedelta
start_date = date.today() - timedelta(days=650)
print(f"--start-date {start_date}")
```

```bash
# Example: 650-day batch ending today
python scripts/data_generation/03_event_engine_core.py \
  --start-date 2024-01-03 \
  --eggs 3500000 \
  --geography "Faroe Islands" \
  --duration 650
```

---

## Data Cleanup

### Cleanup Script

**Location:** `scripts/data_generation/cleanup_batch_data.py`

**Purpose:** Removes all batch-related data while preserving infrastructure

**What it deletes:**
- ✓ Batches
- ✓ Batch Container Assignments
- ✓ Environmental Readings
- ✓ Feeding Events
- ✓ Mortality Events
- ✓ Growth Samples
- ✓ Journal Entries
- ✓ Feed Purchases (AUTO-*)
- ✓ Feed Container Stock
- ✓ Historical records (django-simple-history)

**What it preserves:**
- ✓ Infrastructure (stations, halls, containers, sensors)
- ✓ Master data (species, stages, parameters, feeds)
- ✓ Geographies

**Usage:**

```bash
python scripts/data_generation/cleanup_batch_data.py
```

**Runtime:** ~5-10 seconds

### Manual SQL Cleanup (Advanced)

```sql
-- Delete all batch data
DELETE FROM batch_mortalityevent;
DELETE FROM batch_growthsample;
DELETE FROM environmental_environmentalreading;
DELETE FROM inventory_feedingevent;
DELETE FROM health_journalentry;
DELETE FROM batch_batchcontainerassignment;
DELETE FROM batch_batch;

-- Delete auto-generated feed purchases
DELETE FROM inventory_feedpurchase WHERE batch_number LIKE 'AUTO-%';

-- Delete feed stock
DELETE FROM inventory_feedcontainerstock;

-- Delete historical records
DELETE FROM batch_historicalbatch;
DELETE FROM batch_historicalbatchcontainerassignment;
DELETE FROM batch_historicalmortalityevent;
DELETE FROM environmental_historicalenvironmentalreading;
DELETE FROM inventory_historicalfeedingevent;
```

### Full Reset (Nuclear Option)

To completely reset including infrastructure:

```bash
# Drop and recreate database
dropdb aquamind_db
createdb aquamind_db

# Run migrations
python manage.py migrate

# Re-run Phase 1 & 2
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py
```

---

## Troubleshooting

### Common Issues

#### Issue: `IntegrityError: duplicate key value violates unique constraint`

**Cause:** Batch number already exists  
**Solution:** The script auto-increments batch numbers. If this occurs, delete the existing batch or the cleanup script will handle it.

```python
from apps.batch.models import Batch
Batch.objects.filter(batch_number='FI-2024-001').delete()
```

---

#### Issue: `NameError: name 'User' is not defined`

**Cause:** Missing User model import  
**Solution:** Already fixed in current version. Ensure `User = get_user_model()` is present after imports.

---

#### Issue: `DataError: numeric field overflow`

**Cause:** Growth calculation exceeds Decimal precision  
**Solution:** Already fixed. TGC values are divided by 1000 and max weight is capped at 6kg.

---

#### Issue: Feed containers overfilled (>100% capacity)

**Cause:** Feed container capacity too small for consumption rate  
**Solution:** Run Phase 2 with updated capacities (already fixed in v1.0):
- Freshwater halls: 10-30 tonnes
- Sea cages: 50 tonnes

---

#### Issue: Too many feed purchases (thousands instead of dozens)

**Cause:** Small silo capacity + high consumption at adult stage  
**Solution:** Use realistic capacities (see Phase 2 notes). Adult fish at 6kg eat ~16t/day, so 50t silos last 3 days.

---

#### Issue: Stage transitions not occurring

**Cause:** Stage name mismatch (Egg/Alevin vs Egg&Alevin)  
**Solution:** Already fixed. Stage durations use "Egg&Alevin" (ampersand) to match database.

---

#### Issue: Environmental readings not linked to batch (orphaned)

**Cause:** Missing batch parameter in EnvironmentalReading creation  
**Solution:** Already fixed. All readings now include `batch=self.batch`.

---

### Verification Queries

```sql
-- Check batch progress
SELECT 
    b.batch_number,
    b.lifecycle_stage_id,
    ls.name as stage,
    COUNT(DISTINCT er.id) as env_readings,
    COUNT(DISTINCT fe.id) as feeding_events
FROM batch_batch b
LEFT JOIN batch_lifecyclestage ls ON b.lifecycle_stage_id = ls.id
LEFT JOIN environmental_environmentalreading er ON er.batch_id = b.id
LEFT JOIN inventory_feedingevent fe ON fe.batch_id = b.id
WHERE b.batch_number LIKE 'FI-2024-%'
GROUP BY b.batch_number, b.lifecycle_stage_id, ls.name;

-- Check feed inventory levels
SELECT 
    fc.name,
    fc.capacity_kg / 1000 as capacity_tonnes,
    COALESCE(SUM(fcs.quantity_kg), 0) / 1000 as current_tonnes,
    ROUND(COALESCE(SUM(fcs.quantity_kg), 0) / fc.capacity_kg * 100, 1) as pct_full
FROM infrastructure_feedcontainer fc
LEFT JOIN inventory_feedcontainerstock fcs ON fcs.feed_container_id = fc.id
GROUP BY fc.id, fc.name, fc.capacity_kg
ORDER BY fc.name
LIMIT 20;

-- Check for orphaned readings
SELECT COUNT(*) as orphaned_readings
FROM environmental_environmentalreading
WHERE batch_id IS NULL;

-- Check audit trail activity
SELECT 
    'Batch' as model,
    COUNT(*) as history_records
FROM batch_historicalbatch
UNION ALL
SELECT 
    'Assignment',
    COUNT(*)
FROM batch_historicalbatchcontainerassignment
UNION ALL
SELECT 
    'Mortality',
    COUNT(*)
FROM batch_historicalmortalityevent;
```

---

## Performance Notes

### Optimization Strategies

1. **Bulk Inserts**: Environmental readings use `bulk_create()` with batch_size=500
2. **Minimal Queries**: Assignments fetched once per day and cached
3. **Index Usage**: Primary keys and foreign keys automatically indexed
4. **Connection Pooling**: Django's default connection handling is sufficient

### Expected Performance (M4 Max, 128GB RAM)

| Operation | Duration |
|-----------|----------|
| Phase 1 (Infrastructure) | 5-10 seconds |
| Phase 2 (Master Data) | 10-15 seconds |
| Phase 3 (200-day batch) | 3-5 minutes |
| Phase 3 (650-day batch) | 20-30 minutes |
| Cleanup Script | 5-10 seconds |

### Database Size

| Duration | Events | DB Size |
|----------|--------|---------|
| 200-day batch | ~90,000 | ~150 MB |
| 650-day batch | ~300,000 | ~500 MB |
| 10 batches (650 days each) | ~3M | ~5 GB |

### Memory Usage

- **Script Peak**: ~500 MB
- **PostgreSQL**: ~2-4 GB for active queries
- **Total System**: ~8 GB comfortable, 16GB+ recommended for multiple batches

---

## Data Validation

### Post-Generation Checks

After running Phase 3, verify data quality:

```bash
python scripts/data_generation/verify_data_integrity.py
```

**Expected Results:**
- ✓ Data completeness: 100%
- ✓ Orphaned readings: 0
- ✓ Feed containers: Within capacity
- ✓ Stage transitions: 6 stages completed
- ✓ Survival rate: 70-85%
- ✓ Audit trails: Active

---

## Advanced Usage

### Multiple Concurrent Batches

To simulate realistic farm operations with 40-50 active batches:

```bash
# Use a loop to stagger batch starts
for i in {1..50}; do
  START_DATE=$(date -v-$((RANDOM % 1000))d +%Y-%m-%d)
  python scripts/data_generation/03_event_engine_core.py \
    --start-date $START_DATE \
    --eggs 3500000 \
    --geography "Faroe Islands" \
    --duration 650 &
done
wait
```

**Note:** Running 50 concurrent processes will consume significant resources. Recommended: 5-10 concurrent batches max.

---

## Future Enhancements (Phase 4)

Planned features for future versions:

- [ ] Multi-batch parallel generation with facility scheduling
- [ ] Grace period enforcement (14-21 days between facility uses)
- [ ] Gradual stage transitions (10 days, 1 container/day)
- [ ] Sea water transfer logistics
- [ ] Harvest event generation
- [ ] Financial data (cost tracking, revenue)
- [ ] External supplier integration
- [ ] Internal broodstock management
- [ ] Disease outbreak simulations

---

## Support

For issues or questions:

1. Check this guide first
2. Review the troubleshooting section
3. Examine the script output for specific error messages
4. Check the database using verification queries

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-14 | Initial production release |
| | | - Fixed stage transition bug (ampersand vs slash) |
| | | - Fixed feed capacity issues (realistic sizes) |
| | | - Fixed batch linkage (0 orphaned readings) |
| | | - Added bulk insert optimization |
| | | - Complete audit trail support |

---

## Quick Reference

### Essential Commands

```bash
# Complete fresh start
python scripts/data_generation/cleanup_batch_data.py
python scripts/data_generation/01_bootstrap_infrastructure.py
python scripts/data_generation/02_initialize_master_data.py
python scripts/data_generation/03_event_engine_core.py --start-date 2024-01-03 --eggs 3500000 --geography "Faroe Islands" --duration 650

# Generate another batch
python scripts/data_generation/03_event_engine_core.py --start-date 2024-03-01 --eggs 3200000 --geography "Scotland" --duration 500

# Clean up and start over
python scripts/data_generation/cleanup_batch_data.py
```

---

**End of Guide**
