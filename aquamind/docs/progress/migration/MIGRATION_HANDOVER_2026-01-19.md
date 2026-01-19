# Migration Handover (2026-01-19)

## Purpose
This handover captures the **current FishTalk → AquaMind migration state** after the 15‑component pilot expansion, with emphasis on what is already achieved, how it was achieved, and what remains for a full migration dry‑run. The next session should focus on resolving lifecycle/workflow gaps and defining full dry‑run readiness.

## Where to Start (Read These First)
1. `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md` (current runbook + status)
2. `aquamind/docs/progress/migration/MIGRATION_BEST_PRACTICES.md` (data integrity + audit trail standards)
3. `aquamind/docs/progress/migration/DATA_MAPPING_DOCUMENT.md` (field mapping blueprint)
4. `scripts/migration/tools/migration_counts_report.py` (verification reporting)
5. `scripts/migration/clear_migration_db.py` (wipe/reset for clean runs)

## Current Scope (15 Components)

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

## Environment & Safety
- **Project root:** `/Users/aquarian247/Projects/AquaMind`
- **Migration DB safety:** `scripts/migration/safety.py` enforces `aquamind_db_migr_dev`.
- **Background tasks:** run migration scripts with `SKIP_CELERY_SIGNALS=1`.
- **GUI migration preview stack (Docker):**
  - Backend: http://localhost:8001
  - Frontend: http://localhost:5002
  - Start: `docker compose -f docker-compose.migr-preview.yml up --build`

## What Was Achieved (This Session)

### ✅ Migration Coverage
All 15 components were migrated end‑to‑end:
- **Infrastructure + batch creation**
- **Transfers** (workflow/action numbering collision fixed)
- **Operational data:** feeding, mortality, treatments, lice, health journal
- **Environmental readings:** migrated from `Ext_SensorReadings_v2` + `Ext_DailySensorReadings_v2`
- **Feed inventory:** `FeedReceptions` + `FeedReceptionBatches` → `FeedPurchase`,
  `FeedStore` + `FeedStoreUnitAssignment` → `FeedContainer` + `FeedContainerStock`

### ✅ Audit Trail Compliance
`scripts/migration/history.py` is used across migration scripts to ensure `django-simple-history` records include `_history_user` and change reasons.

### ✅ RBAC Restored
`system_admin` profile was restored to `ADMIN` + `ALL` geography/subsidiary.
Script: `scripts/migration/tools/fix_system_admin_rbac.py`

### ✅ Verification / Reporting
`scripts/migration/tools/migration_counts_report.py` now includes per‑batch inventory counts
using `ExternalIdMap` metadata to map feed purchases and stock to the originating component.

### ✅ Reusable Wipe Script
Use `scripts/migration/clear_migration_db.py` to reset the migration DB between runs (keeps schema and auth tables).

## Current Counts Snapshot (Post‑Run)
Use the report script for live counts (these are representative, not guaranteed current):

```
python scripts/migration/tools/migration_counts_report.py
```

As of the last verified run:
- **batch_batch:** 15
- **batch_batchcontainerassignment:** 93
- **batch_transferaction:** 80
- **inventory_feedingevent:** 2,429
- **batch_mortalityevent:** 3,348
- **health_treatment:** 364
- **health_licecount:** 1,150
- **health_journalentry:** 200
- **environmental_environmentalreading:** 92,118
- **inventory_feedpurchase:** 1
- **inventory_feedcontainerstock:** 1

Note: feed inventory coverage is sparse because FishTalk `FeedStoreUnitAssignment` exists for only **one** of the 15 component containers.

## Verification Checklist (After Each Run)

1. **Counts report:**
   ```
   python scripts/migration/tools/migration_counts_report.py
   ```
2. Confirm:
   - `batch_batch` and `batch_batchcontainerassignment` > 0
   - `batch_transferaction` populated for components with transfers
   - Environmental readings > 0
   - Feed inventory counts present where assignments exist
   - `migration_support_externalidmap` increases after each run
3. GUI validation:
   - Login as `system_admin` and confirm full nav access
   - Review batch list, assignments, operational tabs, environmental charts

## Known Gaps / Limitations
- **Feed inventory coverage**: only 1 of 15 components has FeedStore assignments in FishTalk.
- **Environmental data types**: weather/photoperiod/stage transition not migrated. But these are not in scope, so not a problem. 
- **Full dry‑run readiness**: close, but further documentation & best‑practice consolidation still needed. Some issues remain with the latest 15 batch dryrun, e.g. all batches are marked as "Completed", even the 9 batches that are supposed to be active. The transfer workflows for the batches are all of type "Container Redistribution" instead of the expected "Lifecycle Stage Transition", which is somewhat of a mystery: if we look at batch ID = 10 we can see that it is in stage "Adult"/the last stage even though it only has 3 "Container Redistribution" transfer worflows completed instead of the expected 5 (egg/alevin -> fry -> parr -> smolt -> post-smolt -> adult, is the expected). There is more sleuth work necessary. We must identify how stage transitions are registeres in fishtalk. We already have a mapping of stages in fishtalk to aquamind so this should be possible. Another issue is that the batch creation in fishtalk is much simpler than the batch creation workflow in aquamind, so I cannot see any "Batch Creation" workflows in aquamind. 

## Suggested Next Steps (Next Session)
1. Investigate lifecycle status mismatches (all batches marked **Completed**, workflow type shows **Container Redistribution** instead of lifecycle stage transitions).
2. Confirm how stage transitions are registered in FishTalk and reconcile the stage mapping (start with batch ID 10 as the reference case).
3. Decide how to represent **batch creation** in AquaMind (synthesize workflows vs document their absence).
4. Define “full dry‑run ready” criteria for leadership and add a reconciliation checklist against FishTalk source counts.
5. Optional: add a post‑wipe script that re‑applies `system_admin` RBAC to avoid future lockouts.
6. Optional: decide whether feed purchase/stock data should be included before expanding scope (FW→sea components).

## Key Scripts (Reference)
- `scripts/migration/clear_migration_db.py` (wipe/reset)
- `scripts/migration/tools/migration_counts_report.py` (verification)
- `scripts/migration/tools/pilot_migrate_component*.py` (core migrations)
- `scripts/migration/tools/pilot_migrate_component_environmental.py`
- `scripts/migration/tools/pilot_migrate_component_feed_inventory.py`
- `scripts/migration/tools/fix_system_admin_rbac.py`

## Notes for the Next Agent
The migration is **promising and stable** for the 15‑batch pilot. The goal for the next session is **documentation and best‑practice synthesis and remaining issues identification**, not necessarily new code. Focus on preserving runbook clarity, validation rigor, and migration repeatability.
