# FishTalk → AquaMind Migration (Canonical Guide + Status)

**Last updated:** 2026-01-20

This is the canonical runbook + status for the FishTalk → AquaMind migration. Best-practice guidance lives in `MIGRATION_BEST_PRACTICES.md`, field-level rules live in `DATA_MAPPING_DOCUMENT.md`, and environment/setup notes live in `ENV_SETUP.md`.

## 1) Purpose & Audience
- **Architect view:** scope, status, risks, and decisions.
- **Agent view:** runbook (commands, scripts, validation, and safety checks).

## 2) Documentation Map
- `MIGRATION_CANONICAL.md` — runbook + current status (this doc)
- `MIGRATION_BEST_PRACTICES.md` — data integrity, audit trail, idempotency, verification standards
- `DATA_MAPPING_DOCUMENT.md` — field-level mapping blueprint
- `ENV_SETUP.md` — environment and tooling setup
- `MIGRATION_FRAMEWORK_IMPLEMENTATION_SUMMARY.md` — framework background (historical context)

## 3) Critical Discovery: Project-Based Stitching

### Problem Identified (2026-01-20)

**FW-to-sea transfers stopped being recorded in FishTalk's `PublicTransfers` table since January 2023.**

- The most recent Smolt→Ongrowing transfer in PublicTransfers is from 2023-01-05
- BUT fish ARE reaching sea - 2,239 sea-stage populations exist since 2024
- The original stitching approach relied on PublicTransfers, explaining the batch fragmentation

**Root cause:** Silent failure in FishTalk (likely upgrade-related) broke the transfer recording ~2 years ago.

### Solution: Project-Based Stitching

Instead of relying on broken `PublicTransfers`, we now **stitch populations by FishTalk project identifiers**:

```
(ProjectNumber, InputYear, RunningNumber) → Logical Batch
```

This groups FW populations (Egg→Smolt) with their sea counterparts (Ongrowing→Harvest) because they share the same project tuple.

**New script:** `scripts/migration/tools/project_based_stitching_report.py`

## 4) Current Scope (10 Project-Based Batches)

**Active project batches (2026-01-20 migration):**

| Project Key | Populations | Stages | Status |
|------------|-------------|--------|--------|
| 1/24/27 | 34 | 5/6 (Egg&Alevin, Fry, Parr, Smolt, Adult) | ACTIVE |
| 1/24/20 | 43 | 5/6 | ACTIVE |
| 1/24/67 | 16 | 5/6 | ACTIVE |
| 1/24/45 | 35 | 5/6 | ACTIVE |
| 1/24/7 | 68 | 5/6 | ACTIVE |
| 1/24/80 | 10 | 5/6 | ACTIVE |
| 1/24/37 | 31 | 5/6 | ACTIVE |
| 1/24/17 | 56 | 5/6 | ACTIVE |
| 1/24/60 | 20 | 5/6 | ACTIVE |
| 1/24/21 | 44 | 5/6 | ACTIVE |

All batches span freshwater (Egg&Alevin, Fry, Parr, Smolt) through sea (Adult) stages.

## 5) Current Status (Summary)

**Latest migration run: 2026-01-20**

- **Batches migrated:** 10 active batches with complete FW→sea lifecycle
- **Container assignments:** 357 across FW tanks and sea pens
- **Transfer workflows:** 176 workflows with 219 actions
- **Operations data:** 10,753 mortality events, 7,119 feeding events
- **Health data:** 731 treatments, 2,098 lice counts, 125 journal entries
- **Infrastructure:** 192 containers, 33 areas, 46 halls, 33 FW stations
- **Verification:** 24/25 required tables populated (environmental readings skipped due to time)
- **Audit trail:** `scripts/migration/history.py` used in migration scripts

## 6) Safety Guardrails (Must Use)
- `scripts/migration/safety.py` forces the **default** DB to `aquamind_db_migr_dev` and aborts if misconfigured.
- Use `SKIP_CELERY_SIGNALS=1` for all migration scripts to avoid background tasks.

## 7) Runbook (Agent-Friendly)

### 7.0 Docker-based Migration Environment (GUI testing)

The migration preview stack runs Django + Node in Docker to resemble test/prod:

- **Backend (Django, migr_dev):** http://localhost:8001
- **Frontend (Node):** http://localhost:5002

Use this stack for GUI validation; avoid local `runserver`/`npm dev` when validating migration data.

### 7.1 Setup (once per environment)
```bash
PYTHONPATH=/path/to/AquaMind python scripts/migration/setup_master_data.py
```

### 7.1.1 Reusable wipe/reset (migration DB only)

Use this before a clean dry-run. It truncates migration data but keeps schema and auth tables.

```bash
PYTHONPATH=/path/to/AquaMind python scripts/migration/clear_migration_db.py
```

### 7.2 Generate project-based stitching report (RECOMMENDED)

This is the new approach that correctly links FW and sea populations:

```bash
python scripts/migration/tools/project_based_stitching_report.py --min-stages 4 --print-top 20
```

Output files in `scripts/migration/output/project_stitching/`:
- `project_batches.csv` - All batches meeting criteria
- `project_population_members.csv` - Populations grouped by project
- `recommended_batches.csv` - Top candidates for migration

### 7.2.1 Legacy stitching (component-based)

For reference only - this approach has limitations due to missing PublicTransfers data:

```bash
python scripts/migration/tools/population_stitching_report.py
```

### 7.3 Migrate a project-based batch end-to-end (RECOMMENDED)

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_project_batch.py \
  --project-key "1/24/27" \
  --skip-environmental  # Optional: skip slow environmental migration
```

This wrapper runs all migration scripts in sequence for a single project batch.

### 7.3.1 Migrate one component end-to-end (legacy)

```bash
python scripts/migration/tools/pilot_migrate_component.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_transfers.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_feeding.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_mortality.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_treatments.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_lice.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_health_journal.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_environmental.py --component-key <key>
```

### 7.4 Counts report (core + per-batch)
```bash
python scripts/migration/tools/migration_counts_report.py
```

### 7.5 Comprehensive verification report

```bash
python scripts/migration/tools/migration_verification_report.py
```

Checks all required tables have data and reports per-batch lifecycle stage coverage.

### 7.6 Validation (lint only for now)
```bash
python -m flake8 scripts/migration/tools/migration_counts_report.py
```

### 7.7 Migrate Scenario Models (TGC, FCR, Temperature)

Migrate growth model master data from FishTalk to enable AquaMind projections:

```bash
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_scenario_models.py
```

**What it migrates:**

| FishTalk Source | AquaMind Target | Rows |
|-----------------|-----------------|------|
| `TemperatureTables` | `TemperatureProfile` | 20 |
| `TemperatureTableEntries` | `TemperatureReading` | 240 |
| `GrowthModels` + `TGCTableEntries` | `TGCModel` | 120 |
| `GrowthModels` + `FCRTableEntries` | `FCRModel` + `FCRModelStage` | 8,639 entries |
| (synthetic) | `MortalityModel` | 3 defaults |

**Options:**
- `--dry-run` - Preview without database changes
- `--skip-temperature` - Skip temperature profile migration
- `--skip-tgc` - Skip TGC model migration
- `--skip-fcr` - Skip FCR model migration
- `--skip-mortality` - Skip mortality model creation

**Key transformation:** FCR entries in FishTalk are weight/temperature-based lookup tables. The migration aggregates these to stage-based FCR values using weight-to-stage mapping:

| Weight Range (g) | AquaMind Stage |
|-----------------|----------------|
| 0.0 - 0.5 | Egg&Alevin |
| 0.5 - 5.0 | Fry |
| 5.0 - 30.0 | Parr |
| 30.0 - 100.0 | Smolt |
| 100.0 - 500.0 | Post-Smolt |
| 500.0+ | Adult |

### 7.8 Expand Batch Migration (517 remaining batches)

After the initial 10-batch pilot, expand to all 527 batches with 5+ stages:

```bash
# Dry run first - see what would be migrated
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_batch_expansion.py \
  --min-stages 5 --limit 50 --dry-run

# Migrate next 50 batches (skip environmental for speed)
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_batch_expansion.py \
  --min-stages 5 --limit 50

# Migrate all remaining batches
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_batch_expansion.py \
  --min-stages 5
```

**Options:**
- `--min-stages N` - Minimum lifecycle stages (default: 5)
- `--limit N` - Maximum batches to migrate
- `--active-only` - Only migrate active batches
- `--include-environmental` - Include slow environmental data migration
- `--dry-run` - Preview without changes

### 7.9 Environmental Data Migration

Environmental data is slow to migrate. Run separately after batch expansion:

```bash
# For each migrated batch, run environmental migration
# This is typically done batch-by-batch due to volume
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_component_environmental.py \
  --component-key <component_key> \
  --report-dir scripts/migration/output/project_batch_migration/<project_key>
```

### 7.10 Post-Migration: Create Scenarios & Run Projections

After batch + scenario model migration, run post-processing for ACTIVE batches:

```bash
# Dry run first
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_post_batch_processing.py --dry-run

# Full run - creates scenarios, runs growth analysis, runs projections
PYTHONPATH=/path/to/AquaMind SKIP_CELERY_SIGNALS=1 \
  python scripts/migration/tools/pilot_migrate_post_batch_processing.py
```

**What it does:**
1. **Creates scenarios** for ACTIVE batches using migrated FT-TGC/FCR/Mortality models
2. **Pins projection runs** to active batches
3. **Runs Growth Analysis** - computes `ActualDailyAssignmentState`
4. **Runs Live Forward Projections** - computes `LiveForwardProjection` for dashboard

**Options:**
- `--skip-scenario-creation` - Skip scenario creation step
- `--skip-growth-analysis` - Skip growth analysis step
- `--skip-projections` - Skip live forward projections step

## 8) Data Sources & Mapping Notes (Architect-Friendly)

- **Batch + infra:** derived from project-based stitching using `(ProjectNumber, InputYear, RunningNumber)`.
- **Transfers:** transfer workflows/actions from FishTalk movement events (action_number uniqueness fixed).
- **Feeding/Mortality/Treatments/Lice/Journal:** migrated directly from FishTalk operational tables.
- **Environmental:** migrated from `Ext_SensorReadings_v2` and `Ext_DailySensorReadings_v2` (slow, often skipped).
- **Audit trail:** `save_with_history()`/`get_or_create_with_history()` apply `_history_user` + change reason.

**Stage mapping (FishTalk → AquaMind):**

| FishTalk Stage | AquaMind Stage |
|----------------|----------------|
| EGG, ALEVIN, SAC, GREEN EGG, EYE-EGG | Egg&Alevin |
| FRY | Fry |
| PARR | Parr |
| SMOLT (not POST/LARGE) | Smolt |
| POST-SMOLT, LARGE SMOLT | Post-Smolt |
| ONGROW, GROWER, GRILSE | Adult |

## 9) Current Counts Snapshot (2026-01-20)

```
[Core table counts]
batch_batch                        : 10
batch_batchcontainerassignment     : 357
batch_creationworkflow             : 10
batch_creationaction               : 10
batch_batchtransferworkflow        : 176
batch_transferaction               : 219
batch_mortalityevent               : 10753
inventory_feedingevent             : 7119
health_treatment                   : 731
health_licecount                   : 2098
health_journalentry                : 125
environmental_environmentalreading : 0 (skipped for speed)
infrastructure_sensor              : 0
infrastructure_container           : 192
infrastructure_area                : 33
infrastructure_hall                : 46
infrastructure_freshwaterstation   : 33
inventory_feedpurchase             : 0
inventory_feedcontainerstock       : 0
migration_support_externalidmap    : 21801
```

```
[Per-batch counts]
batch_number             | assignments | workflows | actions | feeding | mortality | treatments | lice | journal
------------------------ | ----------- | --------- | ------- | ------- | --------- | ---------- | ---- | -------
FT-23ECA7F8-24Q1-LHS     | 16          | 8         | 9       | 427     | 632       | 60         | 82   | 0
FT-275B48B5-24Q1-LHS     | 43          | 24        | 29      | 1615    | 0         | 0          | 0    | 0
FT-8F24E7BE-24Q1-LHS     | 35          | 19        | 24      | 1396    | 2742      | 150        | 425  | 10
FT-9F35C74F-NH-FEB-24    | 10          | 7         | 8       | 195     | 248       | 4          | 32   | 0
FT-A6417114-24Q1-LHS     | 56          | 29        | 39      | 1641    | 2673      | 193        | 598  | 57
FT-AA8AACFE-24Q1-LHS     | 68          | 22        | 28      | 1427    | 2334      | 201        | 545  | 41
FT-DF5F0436-24Q1-LHS     | 31          | 12        | 15      | 0       | 1433      | 104        | 332  | 17
FT-E04A249B-24Q1-LHS     | 34          | 22        | 26      | 0       | 0         | 0          | 0    | 0
FT-E71CBA7D-24Q1-LHS     | 20          | 8         | 10      | 418     | 691       | 19         | 84   | 0
FT-FA381BEE-24Q1-LHS     | 44          | 25        | 31      | 0       | 0         | 0          | 0    | 0
```

## 10) Verification Results (2026-01-20)

**Tables with required data:** 24/25 PASSED

| Category | Tables Verified |
|----------|----------------|
| Infrastructure | geography, freshwaterstation, hall, area, container, containertype |
| Batch Management | batch, batchcontainerassignment, lifecyclestage, species, batchtransferworkflow, transferaction, creationworkflow, creationaction, mortalityevent |
| Inventory | feed, feedingevent |
| Health | treatment, licecount, journalentry, mortalityreason, vaccinationtype |
| Environmental | environmentalparameter |
| Migration Support | externalidmap |

**Tables missing data:** 1 (environmental_environmentalreading - skipped for speed)

**Lifecycle stage coverage per batch:** All 10 batches have 5/6 stages (Adult, Egg&Alevin, Fry, Parr, Smolt)

## 11) Known Gaps / Out of Scope

- **Post-Smolt stage:** Not commonly tracked in FishTalk, so most batches show 5/6 stages.
- **Environmental readings:** Migration slow; skipped in this run but script is available.
- **Feed purchase/stock:** Data not available in current FishTalk scope.
- **Planning data (PlanScenario, PlannedActivities):** Stale/junk - DO NOT migrate (per MIGRATION_BEST_PRACTICES.md).
- **Broodstock data:** Not in scope for initial migration.
- **PublicTransfers data gap:** FW→sea transfers stopped being recorded in Jan 2023; project-based stitching bypasses this.

## 12) Next Steps

1. **Run scenario model migration:** Execute `pilot_migrate_scenario_models.py` to migrate TGC/FCR/Temperature master data.
2. **Create baseline scenarios:** After TGC/FCR migration, create scenarios for migrated batches and pin them.
3. **Run projections:** Generate `ActualDailyAssignmentState` and `LiveForwardProjection` data.
4. **Expand batch count:** Add more project batches (527 with 5+ stages available) as needed.
5. **Environmental data:** Run `pilot_migrate_component_environmental.py` for batches where sensor data is needed.
6. **Fresh FishTalk backup:** Current backup is from October 2025; refresh for final migration run.
7. **Production migration:** Define criteria for production readiness and create final migration plan.

## 13) Lessons Learned

1. **Project-based stitching is essential:** The PublicTransfers table in FishTalk has been broken since Jan 2023. Using `(ProjectNumber, InputYear, RunningNumber)` reliably links FW and sea populations.

2. **Environmental migration is slow:** Consider running it separately or for a subset of high-priority batches.

3. **Batch status correctly marked ACTIVE:** All migrated batches show correct status based on recent activity.

4. **Stage coverage is consistent:** All project-based batches show 5/6 lifecycle stages, spanning the full FW→sea journey.
