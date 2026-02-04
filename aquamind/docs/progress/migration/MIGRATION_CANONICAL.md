# FishTalk → AquaMind Migration (Canonical Guide + Status)

**Last updated:** 2026-02-03

This is the canonical runbook + status for the FishTalk → AquaMind migration. Best-practice guidance lives in `MIGRATION_BEST_PRACTICES.md`, field-level rules live in `DATA_MAPPING_DOCUMENT.md`, and environment/setup notes live in `ENV_SETUP.md`.

---

## 1) Purpose & Audience

- **Architect view:** scope, status, risks, and decisions.
- **Agent view:** runbook (commands, scripts, validation, and safety checks).

## 2) Documentation Map

| Document | Purpose |
|----------|---------|
| `MIGRATION_CANONICAL.md` | Runbook + current status (this doc) |
| `MIGRATION_LESSONS_LEARNED.md` | What works vs. what doesn't (read before migrating) |
| `MIGRATION_BEST_PRACTICES.md` | Data integrity, audit trail, idempotency standards |
| `DATA_MAPPING_DOCUMENT.md` | Field-level mapping blueprint |
| `ENV_SETUP.md` | Environment and tooling setup |
| `docs/prd.md` | Full AquaMind product requirements |
| `docs/database/data_model.md` | Complete 161-table schema reference |
| `docs/user_guides/planning_and_workflows_primer.md` | Operational core integration guide |

---

## 2.1 Batch Workflow Mapping (Quick Reference)

- **Stage transitions are represented as transfer workflows** (`batch_batchtransferworkflow` + `batch_transferaction`), but **UI stage charts are derived from assignments**, not workflows.
- **Assignments (`batch_batchcontainerassignment`) are created per PopulationID**; transfers create workflow actions, and **synthetic lifecycle transitions** are generated from assignment stages.
- **UI stage order depends on assignment ordering**; backend now orders batch‑filtered assignments by `lifecycle_stage.order` (fix applied 2026‑02‑03).
- For FishTalk migration specifics (SubTransfers usage, synthetic transitions, and conservation-based counts), see `DATA_MAPPING_DOCUMENT.md` → sections **3.2** and **3.4**.
- Product intent and schema grounding live in `docs/prd.md` (3.1.2 / 3.1.2.1) and `docs/database/data_model.md`.

---

## 3) Critical Discovery: Input-Based Stitching (Ext_Inputs_v2)

### Problem Identified (2026-01-20 → 2026-01-22)

- **PublicTransfers is broken** since Jan 2023, so FW→Sea handoffs are not recorded there.
- **Project tuples are administrative** and can span multiple biological year-classes.

### Solution: Input-Based Stitching

Use **`Ext_Inputs_v2`** to identify biological batches:

```
Batch Key = InputName + InputNumber + YearClass
```

**Key findings:**
- `Ext_Inputs_v2` tracks egg deliveries — the true biological origin.
- **InputName changes at FW→Sea**, so sea-phase batches have their own InputName identity.
- Sea-phase batches (e.g., "Summar 2024") are valid for sea analytics, even if FW history is separate.

### Transfer Workflows (within-environment)
- Use **SubTransfers** for transfers and stage transitions (recommended for 2020+).
- **PublicTransfers is legacy only** (pre-2020; broken since 2023).
- FW→Sea linking still needs explicit logic. **Best candidates to explore:**
  - `Ext_Populations_v2.PopulationName` (includes Supplier/Station/Month/Year + YearClass)
  - `PopulationLink` (if populated in this DB)
  - **Activity Explorer “Input” (GUI):** appears to encode FW unit → Sea unit moves with `TransportCarrier` / trip / compartment metadata. CSV extracts now include `TransportCarrier`, `TransportMethods`, `Ext_Transporters_v2` (2026‑02‑04), but there is **no** join path from `InternalDelivery`/`Operations` to these transport tables, and trip/compartment tables are still missing (if they exist).

---

## 4) Current Migration Status

**Latest migration run: 2026-02-03 (current migration DB)**

**Note:** The migration DB was wiped via `clear_migration_db.py` before this run, so earlier runs (e.g., 2026-01-22 sea batches) are no longer present in `aquamind_db_migr_dev`.

**Key change (2026‑02‑02):** Population counts now use **conservation-based propagation** (Ext_Inputs_v2 + SubTransfers) with **same‑stage suppression** to prevent double‑counting across intra‑stage transfers. This corrected stage totals in the UI without changing frontend logic.
**Key change (2026‑02‑03):** Assignment list ordering is now **lifecycle‑stage ordered** when filtering by batch, so stage charts reflect biological progression without UI changes.

### 4.1 Run Summary

- **Input-based batch migrated (CSV mode, environmental skipped):**
  - `Bakkafrost feb 2024|1|2024` (24 populations selected after restricted full‑lifecycle stitching)
- **Full‑lifecycle (heuristic) settings:** `--include-fw-batch 'Bakkafrost feb 2024|1|2024' --max-fw-batches 1 --max-pre-smolt-batches 0 --heuristic-fw-sea --heuristic-min-score 70`
- **Transfers:** 3 stage workflows / 20 actions (synthetic transitions only; **SubTransfers edges = 0** for this component).
- **Feed inventory:** not re-run after the last wipe (kept empty to focus on batch accuracy).

### 4.2 Counts (migration_counts_report.py, 2026-02-03)

| Category | Count | Notes |
|----------|-------|-------|
| **Batches migrated** | 1 | Input-based heuristic test batch |
| **Container assignments** | 24 | Populations in selected full lifecycle |
| **Transfer workflows** | 3 | Synthetic lifecycle transitions |
| **Transfer actions** | 20 | From synthetic transitions |
| **Mortality events** | 720 | CSV extracts |
| **Feeding events** | 263 | CSV extracts |
| **Environmental readings** | 0 | Skipped (`--skip-environmental`) |
| **Infrastructure containers** | 24 | Tanks created from populations |
| **FW stations / halls** | 1 / 3 | Created from container hierarchy |
| **Feed purchases** | 0 | Not re-run after last wipe |
| **Feed container stock** | 0 | Not re-run after last wipe |
| **ExternalIdMap entries** | 1,145 | Idempotent source mapping |

### 4.3 Tables with Data (current DB)

| Domain | Tables with Data | Notes |
|--------|-----------------|-------|
| Batch Management | batch, assignments, transfers, mortality | Synthetic transitions only |
| Infrastructure | containers, halls, FW stations | No sea areas, no sensors |
| Inventory | feeding events only | Feed inventory not re-run |
| Health | mortalityreason only | Treatments/lice/journal not migrated |
| Environmental | none | Environmental migration skipped |
| Migration Support | ExternalIdMap | Populated for all migrated rows |

### 4.4 Expected Empty (Current Run)
- Feed inventory tables (`inventory_feedpurchase`, `inventory_feedcontainerstock`) (not re-run)
- `health_treatment`, `health_licecount`, `health_journalentry` (SQL-only scripts not run)
- `environmental_environmentalreading` (skipped)
- Sea-only tables: `infrastructure_area`, `infrastructure_sensor`

## 5) ETL Optimization (Bulk Extract + CSV Mode)

### 5.1 The Problem

Per-batch SQL extraction via `docker exec sqlcmd` was extremely slow (~200ms overhead per query). With 50+ queries per batch × 527 batches, the original migration took 20+ hours.

### 5.2 The Solution

Bulk extract all FishTalk data to CSV files once, then migrate using in-memory CSV lookups.

#### Step 1: Extract FishTalk Data to CSV

```bash
# Extract all tables (runs once, ~20-30 minutes)
PYTHONPATH=/path/to/AquaMind \
  python scripts/migration/tools/bulk_extract_fishtalk.py \
  --output scripts/migration/data/extract/

# List available tables
python scripts/migration/tools/bulk_extract_fishtalk.py --list-tables

# Extract specific tables only
python scripts/migration/tools/bulk_extract_fishtalk.py \
  --tables populations,containers,status_values

# Feed inventory extracts (use sa profile if reader isn't provisioned)
python scripts/migration/tools/bulk_extract_fishtalk.py \
  --tables feed_suppliers,feed_types,feed_stores,feed_deliveries \
  --sql-profile fishtalk
```

#### Extracted Data Volumes

| Table | Rows | File Size | Notes |
|-------|------|-----------|-------|
| populations.csv | 350K | 25MB | All FishTalk populations |
| containers.csv | 17K | 1MB | Tank/pen definitions |
| org_units.csv | 4K | 200KB | Organization hierarchy |
| status_values.csv | 7M | 538MB | Population snapshots over time |
| mortality_actions.csv | 4.7M | ~300MB | Mortality events with causes |
| feeding_actions.csv | 4.7M | ~300MB | Feeding events with feed types |
| daily_sensor_readings.csv | 60M | 5.0GB | Daily aggregates → `is_manual=True` |
| time_sensor_readings.csv | 50M+ | 5.9GB | Time-series → `is_manual=False` |
| transfer_operations.csv | - | 5.9MB | Transfer operation metadata |
| transfer_edges.csv | - | 37MB | Population transfer links |

**Total extracted: ~12GB of CSV data**

#### Step 2: Run Migration with CSV Mode

CSV mode is supported by:
- `pilot_migrate_component.py`
- `pilot_migrate_component_transfers.py`
- `pilot_migrate_component_feeding.py`
- `pilot_migrate_component_mortality.py`
- `pilot_migrate_component_environmental.py`

SQL-only (no `--use-csv` yet):
- `pilot_migrate_component_treatments.py`
- `pilot_migrate_component_lice.py`
- `pilot_migrate_component_health_journal.py`
- `pilot_migrate_component_feed_inventory.py`
- `pilot_migrate_feed_inventory.py`

```bash
# Migrate component using pre-extracted CSV data
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component.py \
  --component-key <key> \
  --report-dir scripts/migration/output/project_batch_migration/<project> \
  --use-csv scripts/migration/data/extract/

# Same for other scripts
python scripts/migration/tools/pilot_migrate_component_mortality.py \
  --component-key <key> --use-csv scripts/migration/data/extract/

python scripts/migration/tools/pilot_migrate_component_feeding.py \
  --component-key <key> --use-csv scripts/migration/data/extract/

python scripts/migration/tools/pilot_migrate_component_environmental.py \
  --component-key <key> --use-csv scripts/migration/data/extract/

python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key <key> --use-csv scripts/migration/data/extract/
```

### 5.3 Environmental Data: is_manual Distinction

**Critical:** When importing environmental readings:
- `Ext_DailySensorReadings_v2` (daily aggregates) → `is_manual=True`
- `Ext_SensorReadings_v2` (time-series) → `is_manual=False`

This distinction allows AquaMind to:
1. Prefer time-series data for accurate TGC/thermal unit calculations
2. Fall back to daily aggregates where time-series is missing
3. Maintain data provenance for audit trails

### 5.4 Performance Comparison

| Approach | FishTalk Queries | Migration Time |
|----------|-----------------|----------------|
| Live SQL (per-batch) | ~50,000 | 20+ hours |
| ETL (CSV mode) | ~20 (one-time extraction) | 2-3 hours |

**Speedup: 7-10x faster migration with identical data fidelity.**

### 5.5 Environmental SQLite Index (Parallel-Friendly)

CSV mode is fast but large environmental files (5–6GB each) become memory-bound when run in parallel.
To enable **16+ workers** without loading entire CSVs per process, build a SQLite index for
`daily_sensor_readings.csv` and `time_sensor_readings.csv`:

```bash
# Build a compact, indexed SQLite store (one-time)
python scripts/migration/tools/build_environmental_sqlite.py \
  --input-dir scripts/migration/data/extract/ \
  --output-path scripts/migration/data/extract/environmental_readings.sqlite \
  --replace
```

Then run environmental migration with **parallel workers**:

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_environmental_all.py \
  --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite \
  --workers 16
```

---

## 6) Safety Guardrails (Must Use)

- `scripts/migration/safety.py` forces the **default** DB to `aquamind_db_migr_dev` and aborts if misconfigured.
- Use `SKIP_CELERY_SIGNALS=1` for all migration scripts to avoid background tasks.
- All writes must use `save_with_history()` or `get_or_create_with_history()` to populate audit trails.
- Every migrated row tracked in `ExternalIdMap` to prevent duplicates on replay.

---

## 7) Runbook (Agent-Friendly)

### 7.0 Docker-based Migration Environment (GUI testing)

The migration preview stack runs Django + Node in Docker to resemble test/prod:

- **Backend (Django, migr_dev):** http://localhost:8001
- **Frontend (Node):** http://localhost:5002

Use this stack for GUI validation; avoid local `runserver`/`npm dev` when validating migration data.

### 7.0.1 FishTalk DB Access (Docker + SQL Profiles)

- Ensure Docker Desktop is running and the `sqlserver` container is up (`docker ps`).
- The FishTalk database in the container is `FISHTALK` (case-insensitive in SQL Server).
- SQL profiles (see `scripts/migration/config.py`):
  - `fishtalk_readonly` → login `fishtalk_reader` (default for most scripts)
  - `fishtalk` → login `sa` (use if permissions fail or reader user is missing)
- If `fishtalk_reader` login exists but cannot open the DB, create the DB user + grant read access:

```sql
USE FISHTALK;
CREATE USER fishtalk_reader FOR LOGIN fishtalk_reader;
ALTER ROLE db_datareader ADD MEMBER fishtalk_reader;
```

- Quick connectivity test:

```bash
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -C -S localhost,1433 -U fishtalk_reader -P 'FishtalkReader#2025' -d FISHTALK \
  -Q "SELECT TOP 1 name FROM sys.tables"
```

### 7.1 Setup (once per environment)

```bash
PYTHONPATH=/path/to/AquaMind python scripts/migration/setup_master_data.py
```

### 7.1.1 Reusable wipe/reset (migration DB only)

Use this before a clean dry-run. It truncates migration data but keeps schema and auth tables.

```bash
PYTHONPATH=/path/to/AquaMind python scripts/migration/clear_migration_db.py
```

### 7.2 Generate input-based stitching report

```bash
python scripts/migration/tools/input_based_stitching_report.py \
  --output-dir scripts/migration/output/input_stitching
```

Output files in `scripts/migration/output/input_stitching/`:
- `input_batches.csv` - All input-based batches
- `input_population_members.csv` - Populations grouped by input batch
- `recommended_batches.csv` - Top candidates for migration

### 7.3 Migrate an input-based batch end-to-end

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_input_batch.py \
  --batch-key "Vár 2024|1|2024" \
  --use-csv scripts/migration/data/extract/ \
  --skip-environmental  # Optional: skip slow environmental migration
```

This wrapper runs all migration scripts in sequence for a single input batch.

### 7.3.1 Legacy: project-based stitching (deprecated)

```bash
python scripts/migration/legacy/tools/project_based_stitching_report.py --min-stages 4 --print-top 20  # deprecated

PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/legacy/tools/pilot_migrate_project_batch.py \
  --project-key "1/24/27" \
  --skip-environmental
```

### 7.4 Migrate individual components (with CSV mode)

```bash
# Core batch + infrastructure
python scripts/migration/tools/pilot_migrate_component.py \
  --component-key <key> --use-csv scripts/migration/data/extract/

# Transfers (use SubTransfers for 2020+)
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key <key> --use-csv scripts/migration/data/extract/ --use-subtransfers

# Operations
python scripts/migration/tools/pilot_migrate_component_feeding.py \
  --component-key <key> --use-csv scripts/migration/data/extract/
python scripts/migration/tools/pilot_migrate_component_mortality.py \
  --component-key <key> --use-csv scripts/migration/data/extract/

# Health
python scripts/migration/tools/pilot_migrate_component_treatments.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_lice.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_health_journal.py --component-key <key>

# Environmental (slowest - run last)
python scripts/migration/tools/pilot_migrate_component_environmental.py \
  --component-key <key> --use-csv scripts/migration/data/extract/
```

### 7.4.1 Environmental at scale (parallel, recommended)

```bash
# Build SQLite index once
python scripts/migration/tools/build_environmental_sqlite.py \
  --input-dir scripts/migration/data/extract/ \
  --output-path scripts/migration/data/extract/environmental_readings.sqlite \
  --replace

# Parallel run across all project batches
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_environmental_all.py \
  --use-sqlite scripts/migration/data/extract/environmental_readings.sqlite \
  --workers 16
```

### 7.5 Verification & Reports

```bash
# Counts report (core + per-batch)
python scripts/migration/tools/migration_counts_report.py

# Comprehensive verification report
python scripts/migration/tools/migration_verification_report.py
```

### 7.6 Migrate Scenario Models (TGC, FCR, Temperature)

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_scenario_models.py
```

### 7.7 Post-Migration: Create Scenarios & Run Projections

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_post_batch_processing.py
```

---

## 8) Data Sources & Mapping

### 8.1 FishTalk → AquaMind Stage Mapping

| FishTalk Stage | AquaMind Stage |
|----------------|----------------|
| EGG, ALEVIN, SAC, GREEN EGG, EYE-EGG | Egg&Alevin |
| FRY | Fry |
| PARR | Parr |
| SMOLT (not POST/LARGE) | Smolt |
| POST-SMOLT, LARGE SMOLT | Post-Smolt |
| ONGROW, GROWER, GRILSE | Adult |

### 8.2 Key Entity Mappings

| FishTalk Entity | AquaMind Entity | Notes |
|-----------------|-----------------|-------|
| Populations + Ext_Inputs_v2 | Batch | Input-based (InputName + InputNumber + YearClass); InputName changes at FW→Sea |
| Containers | Container | 1:1 mapping with OrgUnit hierarchy |
| PublicStatusValues | BatchContainerAssignment | Population/biomass snapshots (prefer non-zero after start) |
| Ext_SensorReadings_v2 | EnvironmentalReading | Time-series (is_manual=False) |
| Ext_DailySensorReadings_v2 | EnvironmentalReading | Daily aggregates (is_manual=True) |
| Mortality + MortalityCauses | MortalityEvent + MortalityReason | Full cause categorization |
| Feeding + FeedTypes | FeedingEvent + Feed | With feed specifications |
| Operations + Treatments | Treatment | Health treatments |
| LiceCount | LiceCount | Sea lice monitoring |

### 8.3 Audit Trail Implementation

All migration writes use:
- `save_with_history(obj, user=migration_user, reason="FishTalk migration")` 
- `get_or_create_with_history(...)` for idempotent creates

This populates django-simple-history tables automatically. See `MIGRATION_BEST_PRACTICES.md` for details.

---

## 9) AquaMind Table Coverage Analysis

### 9.1 Complete Table Inventory (161 tables)

| App | Total Tables | With Data | Key Migration Tables |
|-----|-------------|-----------|---------------------|
| batch | 27 | 14 | batch, batchcontainerassignment, mortalityevent, batchtransferworkflow, transferaction |
| broodstock | 20 | 0 | (Out of scope) |
| health | 25 | 6 | treatment, licecount, journalentry, mortalityreason |
| infrastructure | 16 | 8 | container, hall, area, freshwaterstation, sensor |
| inventory | 12 | 6 | feed, feedingevent, feedpurchase |
| environmental | 8 | 2 | environmentalparameter, environmentalreading |
| scenario | 15 | 6 | tgcmodel, fcrmodel, temperatureprofile |
| harvest | 8 | 0 | (Future operations) |
| finance | 12 | 0 | (Runtime transactions) |
| planning | 3 | 0 | (Created fresh in AquaMind) |
| users | 3 | 3 | user, userprofile |
| auth/admin | 7 | 3 | Standard Django tables |
| historian | 3 | 0 | Historian config |
| migration_support | 1 | 1 | externalidmap |

### 9.2 Tables That Should Have Data Post-Migration

**Expected populated after a complete migration run:**

1. **Core Batch Data** (batch app)
   - `batch_batch` - Fish batches
   - `batch_batchcontainerassignment` - Container assignments
   - `batch_lifecyclestage` - Stage definitions (master data)
   - `batch_species` - Species definitions (master data)
   - `batch_batchcreationworkflow` - Creation workflows
   - `batch_creationaction` - Creation actions
   - `batch_batchtransferworkflow` - Transfer workflows
   - `batch_transferaction` - Transfer actions
   - `batch_mortalityevent` - Mortality events

2. **Infrastructure** (infrastructure app)
   - `infrastructure_geography` - Geographies
   - `infrastructure_area` - Sea areas
   - `infrastructure_freshwaterstation` - FW stations
   - `infrastructure_hall` - Halls in FW stations
   - `infrastructure_container` - All containers
   - `infrastructure_containertype` - Container types
   - `infrastructure_sensor` - Sensors
   - `infrastructure_feedcontainer` - Feed containers

3. **Inventory** (inventory app)
   - `inventory_feed` - Feed types
   - `inventory_feedingevent` - Feeding events
   - `inventory_feedpurchase` - Feed purchases (if available)
   - `inventory_feedcontainerstock` - FIFO stock

4. **Health** (health app)
   - `health_mortalityreason` - Mortality reasons
   - `health_treatment` - Treatments
   - `health_vaccinationtype` - Vaccination types
   - `health_licecount` - Lice counts
   - `health_journalentry` - Health journal

5. **Environmental** (environmental app)
   - `environmental_environmentalparameter` - Parameter types
   - `environmental_environmentalreading` - Sensor readings

6. **Scenario Models** (scenario app)
   - `scenario_tgcmodel` + `scenario_tgcmodelstage`
   - `scenario_fcrmodel` + `scenario_fcrmodelstage`
   - `scenario_temperatureprofile` + `scenario_temperaturereading`
   - `scenario_mortalitymodel`

7. **Audit History** (all *_historical* tables)
   - Auto-populated via django-simple-history

### 9.3 Tables That Remain Empty (Expected)

- **Broodstock** (20 tables) - Out of scope for production migration
- **Harvest** (8 tables) - Future harvest operations
- **Finance** (12 tables) - Runtime intercompany transactions
- **Planning** (3 tables) - Created fresh in AquaMind
- **Growth Samples** - Computed by assimilation engine
- **Daily States / Projections** - Computed post-migration

---

## 10) Known Issues & Gaps

### 10.1 Data Gaps in FishTalk

| Issue | Impact | Mitigation |
|-------|--------|------------|
| PublicTransfers broken since Jan 2023 | FW→sea transfers not recorded for active cohorts | Current backup shows FW→Sea edges only in 2010–2014 (no 2023+); active FW→Sea linking remains pending without a new report |
| Post-Smolt stage rarely tracked | Most batches show 5/6 stages | Acceptable - reflects FishTalk practice |
| Feed purchase data sparse | Limited FIFO cost tracking | Optional - not blocking |
| FishTalk backup from 2026‑01‑22 | Missing data after backup | Refresh backup before final migration |

### 10.2 Performance Considerations

| Issue | Solution |
|-------|----------|
| Environmental migration slow | Use `--use-csv` mode with pre-extracted CSVs |
| Parallel env migration becomes memory-bound | Build SQLite index + `--use-sqlite` (see 5.5, 7.4.1) |
| Large batch count (527+) | ETL approach reduces from 20h to 2-3h |
| Status values table (7M rows) | Pandas DataFrame with filtered loading |

### 10.3 Not Migrated (By Design)

- **Scenario/Planning data from FishTalk** - Stale/junk data (see MIGRATION_BEST_PRACTICES.md)
- **Broodstock data** - Out of scope for initial go-live
- **Historical growth samples** - Will be back-filled by assimilation if needed

### 10.4 Environment Prerequisites

- **Growth analysis requires TimescaleDB**: `batch_actualdailyassignmentstate` is a hypertable; ensure the Timescale extension is preloaded in `aquamind_db_migr_dev` before running post‑migration processing.

---

## 11) Lessons Learned

### 11.1 Technical Lessons

1. **Input-based stitching is essential:** `Ext_Inputs_v2` is the biological batch key; InputName changes at FW→Sea.

2. **ETL approach is 7-10x faster:** Bulk CSV extraction eliminates the ~200ms overhead per SQL query. Essential for 500+ batch migrations.

3. **Environmental data needs `is_manual` distinction:** Daily aggregates (`is_manual=True`) vs time-series (`is_manual=False`) is critical for accurate TGC calculations.

4. **Audit trail via django-simple-history works well:** All 20+ historical tables auto-populated correctly with user attribution and change reasons.

5. **ExternalIdMap provides idempotency:** Enables safe replay without duplicates.

### 11.2 Process Lessons

1. **Validate with dry-run first:** All scripts support `--dry-run` for safe preview.

2. **Monitor CPU during parallel migrations:** Avoid running many Python processes simultaneously - can cause laptop thermal issues.

3. **Clear migration DB between full runs:** Use `clear_migration_db.py` for clean slate.

4. **GUI validation essential:** Use Docker preview stack (localhost:8001/5002) to verify data appears correctly in UI.

### 11.3 Data Quality Lessons

1. **FishTalk data quality varies:** Some batches have complete data, others are sparse. Migration handles gracefully.

2. **Stage mapping requires normalization:** FishTalk stage names are inconsistent; normalize before mapping.

3. **Container grouping from OrgUnit hierarchy:** FishTalk's Ext_GroupedOrganisation_v2 provides site/area/company context.

---

## 12) Next Steps

### 12.1 Immediate (Pre-Production)

1. **Complete environmental data migration** - Run for all 527 batches using CSV mode
2. **Run scenario model migration** - Execute `pilot_migrate_scenario_models.py`
3. **Create baseline scenarios** - For active batches, create scenarios and pin them
4. **Run growth assimilation** - Generate `ActualDailyAssignmentState` data
5. **Run live forward projections** - Populate `LiveForwardProjection` for dashboard
6. **GUI validation** - Verify all data appears correctly in frontend

### 12.2 Before Go-Live

1. **Refresh FishTalk backup** - Current backup is from October 2025; need recent data
2. **Final migration run** - Clean slate with fresh backup
3. **Production DB setup** - Configure `aquamind_db_prod` with same schema
4. **User training** - Ensure operators understand AquaMind workflows

### 12.3 Post Go-Live

1. **Monitor growth assimilation** - Verify daily state computation works correctly
2. **Track variance reports** - Compare planned vs actual outcomes
3. **Expand to broodstock** - Phase 2/3 when ready

---

## 13) Key Files Reference

### Migration Scripts

| Script | Purpose |
|--------|---------|
| `scripts/migration/tools/bulk_extract_fishtalk.py` | ETL extraction to CSV |
| `scripts/migration/tools/etl_loader.py` | CSV data loader with caching |
| `scripts/migration/tools/pilot_migrate_component.py` | Core batch migration |
| `scripts/migration/tools/pilot_migrate_component_*.py` | Domain-specific migrations |
| `scripts/migration/legacy/tools/pilot_migrate_project_batch.py` | End-to-end batch migration (deprecated) |
| `scripts/migration/tools/pilot_migrate_scenario_models.py` | TGC/FCR/Temperature migration |
| `scripts/migration/tools/pilot_migrate_post_batch_processing.py` | Post-migration processing |
| `scripts/migration/tools/migration_counts_report.py` | Verification counts |
| `scripts/migration/tools/migration_verification_report.py` | Full verification |

### Data Directories

| Directory | Contents |
|-----------|----------|
| `scripts/migration/data/extract/` | Pre-extracted CSV files (~12GB) |
| `scripts/migration/output/project_batch_migration/` | Per-batch migration outputs |
| `scripts/migration/output/population_stitching/` | Stitching reports |

### Configuration

| File | Purpose |
|------|---------|
| `scripts/migration/safety.py` | DB safety enforcement |
| `scripts/migration/history.py` | Audit trail helpers |
| `scripts/migration/extractors/base.py` | SQL extraction base class |

---

**End of Document**
