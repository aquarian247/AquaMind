# Migration Handover Document - 2026-01-22 (Session 2)

## 🎯 Goal: Complete Migration of an Active Sea Batch

**Objective:** Migrate a single active sea batch with ALL associated data:
- ✅ Batch & Container Assignments
- ✅ Creation Workflow (egg input)
- ✅ Transfer Workflows (all movements)
- ✅ Mortality Events
- ✅ Feeding Events
- ✅ Treatments
- ✅ Lice Counts
- ⏳ Environmental Data (if time permits)

**Hardware:** MacBook with 128GB RAM - can handle large in-memory operations or use SQLite indexing.

---

## 📊 Session Progress Summary

### ✅ Completed This Session

1. **Implemented Input-Based Stitching**
   - Added `Ext_Inputs_v2` extraction to `bulk_extract_fishtalk.py`
   - Created `input_based_stitching_report.py` 
   - Generated `input_batches.csv` with 1,142 valid batches

2. **Created Input Batch Migration Wrapper**
   - `pilot_migrate_input_batch.py` - orchestrates full batch migration
   - Generates component-style CSVs from input batch data
   - Calls all component migration scripts sequentially

3. **Partial Migration of "Summar 2024|1|2024"**
   - 116 assignments, 42 containers, 4 sea areas
   - 109 transfer actions, 581 mortality events
   - 45 treatments, 97 lice counts
   - Feeding: 0 (data mismatch - needs investigation)

4. **MAJOR DISCOVERY: Supplier Codes & Naming Conventions**

| Abbreviation | Supplier | Primary Station(s) |
|--------------|----------|-------------------|
| **BM** | Benchmark Genetics | S24 Strond |
| **BF** | Bakkafrost | S08 Gjógv, S21 Viðareiði |
| **SF** | Stofnfiskur | S03 Norðtoftir, S16 Glyvradalur |
| **AG** | AquaGen | S03 Norðtoftir |

5. **CRITICAL FINDING: InputName Changes at FW→Sea Transition**
   - When fish transfer from freshwater to sea, a **new PopulationID** is created
   - The **InputName in Ext_Inputs_v2 also changes** (e.g., "Benchmark Gen. Juni 2024" → "Vár 2024")
   - This means sea-phase batches have their own InputName identity

---

## 🐟 Recommended Batches for Full Migration

### Option 1: Summar 2024 (Partially Done)

```
Batch Key: Summar 2024|1|2024
Populations: 116
Fish Count: 4.5M
Sea Areas: A11 Hvannasund S, A21 Hvannasund S, A25 Gøtuvík, A47 Gøtuvík
Time Span: 379 days (Jun 2024 - Jul 2025)
Status: Partially migrated (missing feeding data)
```

### Option 2: Vár 2024 (Not Started)

```
Batch Key: Vár 2024|1|2024
Populations: 98
Fish Count: 5.6M
Sea Areas: A06 Argir, A18 Hov, A04 Lambavík, A13 Borðoyavík, A63 Árnafjørður
Time Span: 458 days (Feb 2024 - May 2025)
Status: Available, larger than Summar 2024
```

### Option 3: Heyst 2024 (Fresh Start)

```
Batch Key: Heyst 2024|1|2024
Populations: ~90+
Sea Areas: A15 Tvøroyri, A23 Hvalba, A71 Funningsfjørður
Time Span: Active as of Oct 2025
Status: Available
```

---

## 📋 Next Session Tasks

### Task 1: Fix Feeding Data Migration

The feeding migration skipped all 351 rows for Summar 2024. Investigate:

```bash
# Check feeding data structure
head -5 scripts/migration/data/extract/feeding_actions.csv

# Check if PopulationIDs match
# The feeding_actions.csv may use different container/population references
```

**Likely Issue:** Feeding data is keyed by ContainerID, not PopulationID. Need to match containers in the batch's assignments.

### Task 2: Complete Summar 2024 Migration

```bash
# Current state check
PYTHONPATH=/path/to/AquaMind python -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aquamind.settings')
import django; django.setup()
from apps.batch.models import Batch, MortalityEvent
from apps.inventory.models import FeedingEvent
from apps.health.models import Treatment, LiceCount
b = Batch.objects.using('migr_dev').first()
print(f'Mortality: {MortalityEvent.objects.using(\"migr_dev\").count()}')
print(f'Feeding: {FeedingEvent.objects.using(\"migr_dev\").count()}')
print(f'Treatments: {Treatment.objects.using(\"migr_dev\").count()}')
print(f'Lice: {LiceCount.objects.using(\"migr_dev\").count()}')
"
```

### Task 3: Migrate Another Batch (Vár 2024)

```bash
# Wipe and start fresh
PYTHONPATH=/path/to/AquaMind python scripts/migration/clear_migration_db.py
PYTHONPATH=/path/to/AquaMind python scripts/migration/setup_master_data.py

# Migrate Vár 2024
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024"
```

### Task 4: Handle Large Data Volumes

For batches with millions of feeding/mortality records, use SQLite indexing:

```bash
# Build SQLite index for large CSVs (one-time)
python scripts/migration/tools/build_environmental_sqlite.py \
  --input-dir scripts/migration/data/extract/ \
  --output-path scripts/migration/data/extract/environmental_readings.sqlite \
  --replace

# Or for feeding data specifically, consider creating a similar index:
# python scripts/migration/tools/build_feeding_sqlite.py ...
```

**Memory Strategy:** With 128GB RAM, can load full CSVs in memory. Use `--use-csv` mode for all component scripts.

---

## 🔑 Key Files Reference

### Migration Scripts

| Script | Purpose |
|--------|---------|
| `pilot_migrate_input_batch.py` | **NEW** - Orchestrates full input-based batch migration |
| `input_based_stitching_report.py` | **NEW** - Generates input_batches.csv |
| `pilot_migrate_component.py` | Core batch/assignment migration |
| `pilot_migrate_component_transfers.py` | Transfer workflows |
| `pilot_migrate_component_mortality.py` | Mortality events |
| `pilot_migrate_component_feeding.py` | Feeding events |
| `pilot_migrate_component_treatments.py` | Treatment records |
| `pilot_migrate_component_lice.py` | Lice counts |

### Output Directories

| Path | Contents |
|------|----------|
| `scripts/migration/output/input_stitching/` | Input-based batch analysis |
| `scripts/migration/output/input_batch_migration/` | Per-batch migration outputs |
| `scripts/migration/data/extract/` | Extracted CSVs from FishTalk |

### Documentation Updated This Session

| File | Changes |
|------|---------|
| `FISHTALK_SCHEMA_ANALYSIS.md` | Section 8: Batch Naming Conventions |
| `DATA_MAPPING_DOCUMENT.md` | Sections 3.0.0.1-3.0.0.4: Supplier codes, naming |

---

## 🔌 Database Connection

```bash
# FishTalk SQL Server (Docker)
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P '2).nV(Ze2TZ8' -d FishTalk -C -Q "SELECT ..."

# AquaMind Migration DB
PYTHONPATH=/path/to/AquaMind python manage.py shell
# Then use .using('migr_dev') for all queries
```

---

## ⚠️ Known Issues & Workarounds

### 1. Feeding Data Mismatch
- `feeding_actions.csv` (890MB) didn't match Summar 2024 populations
- **Workaround:** Investigate container ID mapping in feeding script

### 2. InputName Changes at FW→Sea
- Fish at S24 Strond = "Benchmark Gen. Juni 2024"
- Same fish at sea = "Vár 2024" or "Summar 2024"
- **Implication:** Sea batches are independent units for analytics

### 3. Environmental Data Timeout
- Environmental migration timed out (large dataset)
- **Workaround:** Use SQLite index per section 5.5 of MIGRATION_CANONICAL.md

### 4. Mixed Batches
- Some sea populations have mixed inputs (e.g., "BF/BM Mai 2024")
- **Implication:** Use `batch_batchcomposition` table to track source batches

---

## 📊 Current migr_dev State

```
=== Summar 2024 Migration Status ===

Batch: FT-BA711B17-S03 (ACTIVE)

CORE DATA:
  Assignments: 116
  Containers: 42
  Sea Areas: 4 (A11, A21, A25, A47 - all Gøtuvík/Hvannasund)

TRANSFERS:
  Transfer Workflows: 1
  Transfer Actions: 109

BIOLOGICAL DATA:
  Mortality Events: 581
  Feeding Events: 0 ❌ (needs fix)
  Treatments: 45
  Lice Counts: 97

TRACEABILITY:
  External ID Mappings: 995
```

---

## 🎯 Success Criteria for Next Session

A "complete" batch migration should have:

| Data Type | Expected | Notes |
|-----------|----------|-------|
| Batch | 1 | With correct status and lifecycle stage |
| Assignments | 50-150 | Per population in batch |
| Creation Workflow | 1 | With creation actions |
| Transfer Workflows | 1-5 | Per lifecycle transition + redistributions |
| Transfer Actions | 50-200 | Individual fish movements |
| Mortality Events | 100-1000+ | Daily mortality records |
| Feeding Events | 1000-10000+ | Daily feeding records |
| Treatments | 10-100 | Medical/chemical treatments |
| Lice Counts | 50-500 | Weekly lice monitoring |
| Environmental | Optional | Temperature/oxygen readings |

---

**Document Created:** 2026-01-22 (Session 2)  
**Status:** Ready for next session  
**Priority:** Fix feeding data migration, then complete a full batch
