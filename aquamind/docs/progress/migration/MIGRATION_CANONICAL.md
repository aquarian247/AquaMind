# FishTalk → AquaMind Migration (Canonical Guide + Status)

**Last updated:** 2026-01-19

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

## 3) Current Scope (15 Components)

**Active components**
- `6DD18F69-7E87-49E0-AEC3-A1A08BF21543`
- `04BA2F0E-AF69-4FF0-88C2-0D9B6FE6FA81`
- `D31330BF-8C1E-4629-B4D6-92757B8F8026`
- `ADB084F5-FB3A-480C-8C01-47219C99D73C`
- `1DB47077-F68E-40AA-A775-659A4D3DC5C6`
- `6E3B731F-DBFF-4B43-9063-D9AED34EE9CA`
- `0EEF86D7-056F-4DCC-B3A5-4591E5F493AC`
- `3A06FDA0-853F-44E3-9794-F683EC13CFF3`
- `25A7302B-52A2-40F4-8338-1B4CE9A8DB78`

**Completed components**
- `027AB5BB-FDFA-4613-84F5-07DEAFC2BF76`
- `63467AE1-FC41-49B1-AB5D-5D7DF983C580`
- `82214D2A-D43F-4514-B18C-5C9FF264E749`
- `14F4DDB7-5592-4531-AE40-A2FC743DBAF9`
- `038A576C-3959-4D06-8C6A-44C45DE5E7C7`
- `055BD5E5-FC43-42E8-B2D2-738B34DAEDEE`

## 4) Current Status (Summary)
- **Batches + infrastructure migrated:** 15 batches, 93 assignments, 41 containers, 15 areas/halls/stations.
- **Operations:** transfers, feeding, mortality, treatments, lice, and journal entries migrated.
- **Environmental:** `Ext_SensorReadings_v2` + `Ext_DailySensorReadings_v2` migrated into `environmental_environmentalreading`.
- **Audit trail:** `scripts/migration/history.py` used in migration scripts; history user/reason set on creates/updates.

## 5) Safety Guardrails (Must Use)
- `scripts/migration/safety.py` forces the **default** DB to `aquamind_db_migr_dev` and aborts if misconfigured.
- Use `SKIP_CELERY_SIGNALS=1` for all migration scripts to avoid background tasks.

## 6) Runbook (Agent-Friendly)

### 6.0 Docker-based Migration Environment (GUI testing)

The migration preview stack runs Django + Node in Docker to resemble test/prod:

- **Backend (Django, migr_dev):** http://localhost:8001
- **Frontend (Node):** http://localhost:5002

Use this stack for GUI validation; avoid local `runserver`/`npm dev` when validating migration data.

### 6.1 Setup (once per environment)
```
python scripts/migration/setup_master_data.py
```

### 6.1.1 Reusable wipe/reset (migration DB only)

Use this before a clean dry-run. It truncates migration data but keeps schema and auth tables.

```
python scripts/migration/clear_migration_db.py
```

### 6.2 Generate stitching report
```
python scripts/migration/tools/population_stitching_report.py
```

### 6.3 Migrate one component end-to-end
```
python scripts/migration/tools/pilot_migrate_component.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_transfers.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_feeding.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_mortality.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_treatments.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_lice.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_health_journal.py --component-key <key>
python scripts/migration/tools/pilot_migrate_component_environmental.py --component-key <key>
```

### 6.4 Counts report (core + per-batch)
```
python scripts/migration/tools/migration_counts_report.py
```

### 6.4.1 Verification after a migration run

```
python scripts/migration/tools/migration_counts_report.py
```

Look for:
- Non-zero `batch_batch`, `batch_batchcontainerassignment`, `batch_transferaction`
- Environmental readings populated
- Feed inventory counts present where FeedStore assignments exist
- `migration_support_externalidmap` increasing after each run

### 6.5 Validation (lint only for now)
```
python -m flake8 scripts/migration/tools/migration_counts_report.py
```

## 7) Data Sources & Mapping Notes (Architect-Friendly)
- **Batch + infra:** derived from stitched components (population_stitching_report).
- **Transfers:** transfer workflows/actions from FishTalk movement events (action_number uniqueness fixed).
- **Feeding/Mortality/Treatments/Lice/Journal:** migrated directly from FishTalk operational tables.
- **Environmental:** migrated from `Ext_SensorReadings_v2` and `Ext_DailySensorReadings_v2`.
- **Audit trail:** `save_with_history()`/`get_or_create_with_history()` apply `_history_user` + change reason.

## 8) Current Counts Snapshot (2026-01-17)

```
[Core table counts]
batch_batch                        : 15
batch_batchcontainerassignment     : 93
batch_batchtransferworkflow        : 42
batch_transferaction               : 80
batch_mortalityevent               : 3348
inventory_feedingevent             : 2429
health_treatment                   : 364
health_licecount                   : 1150
health_journalentry                : 200
environmental_environmentalreading : 92118
infrastructure_sensor              : 255
infrastructure_container           : 41
infrastructure_area                : 15
infrastructure_hall                : 15
infrastructure_freshwaterstation   : 15
inventory_feedpurchase             : 0
inventory_feedcontainerstock       : 0
migration_support_externalidmap    : 103498
```

```
[Per-batch counts]
batch_number | assignments | workflows | actions | feeding | mortality | treatments | lice | journal | environmental
------------ | ----------- | --------- | ------- | ------- | --------- | ---------- | ---- | ------- | -------------
FT-027AB5BB-FO-Gen-3 | 24 | 11 | 23 | 0 | 15 | 0 | 0 | 0 | 5204
FT-038A576C-Rogn-aug--2023 | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 812
FT-04BA2F0E-MW_AG-24-Q1 | 26 | 15 | 27 | 1266 | 1533 | 157 | 804 | 200 | 74572
FT-055BD5E5-Rogn-aug--2023 | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 768
FT-0EEF86D7-23-S21-SF-JUN-25--FEB-24 | 7 | 3 | 6 | 126 | 218 | 22 | 34 | 0 | 637
FT-14F4DDB7-N15-S24-SF-OKT-22 | 3 | 1 | 2 | 383 | 519 | 67 | 116 | 0 | 2393
FT-1DB47077-20-S24-SF-JUN-25--MAR-24 | 9 | 4 | 8 | 130 | 270 | 23 | 35 | 0 | 667
FT-25A7302B-20-S21-S24-APR-MAI-24--NOV-22-MAR-23 | 8 | 4 | 7 | 385 | 515 | 69 | 125 | 0 | 5856
FT-3A06FDA0-SF-SEP-24 | 1 | 0 | 0 | 12 | 13 | 3 | 0 | 0 | 71
FT-63467AE1-FO-Gen-3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 296
FT-6DD18F69-AX_NH-23-Q4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9
FT-6E3B731F-24-S21-SF-JUN-25--FEB-24 | 5 | 2 | 4 | 127 | 226 | 23 | 36 | 0 | 631
FT-82214D2A-BF--Fiskaaling--okt--2023 | 1 | 0 | 0 | 0 | 38 | 0 | 0 | 0 | 152
FT-ADB084F5-AX_NH-23-Q4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10
FT-D31330BF-AX_NH-23-Q4 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 40
```

## 9) Known Gaps / Out of Scope
- Scenario/planning/broodstock not in this pilot.
- `inventory_feedpurchase` and `inventory_feedcontainerstock` remain empty for this scope; verify if FishTalk purchase data should be included.
- Weather/photoperiod/stage-transition environmental data not migrated.

## 10) Next Steps
1. Investigate lifecycle status mismatches (batches marked **Completed**, workflows showing **Container Redistribution** vs stage transitions).
2. Confirm how stage transitions are registered in FishTalk and reconcile stage mapping (start with batch ID 10).
3. Decide how to represent **batch creation** in AquaMind (synthesize workflows vs document absence).
4. Define “full dry‑run ready” criteria plus a reconciliation checklist against FishTalk source counts.
5. Validate GUI using the migration preview environment; if anomalies appear, re-run `migration_counts_report.py` for the affected batch and inspect linked assignments/actions.
6. After gaps are resolved and validation passes, consider expanding scope (including FW→sea components) and whether to include feed purchase/stock data.
