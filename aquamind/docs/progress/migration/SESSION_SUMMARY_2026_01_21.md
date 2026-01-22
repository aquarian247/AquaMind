# Session Summary (2026-01-21)

## Overview
This session focused on migration architecture and data correctness issues observed in the UI (container assignments, workflow counts, feed inventory) plus performance scaling for environmental migration.

## Major Changes (Code + Runbook)
- Added a **SQLite-indexed environmental path** to avoid loading 5–6GB CSVs per worker:
  - `scripts/migration/tools/build_environmental_sqlite.py`
  - `scripts/migration/tools/etl_loader.py` (SQLite query support)
  - `scripts/migration/tools/pilot_migrate_component_environmental.py` (supports `--use-sqlite`)
  - `scripts/migration/tools/pilot_migrate_environmental_all.py` (supports `--workers`, `--use-sqlite`)
- Updated the runbook: `docs/progress/migration/MIGRATION_CANONICAL.md`
  - Added SQLite workflow for parallel environmental runs
  - Added performance note for parallel runs
  - Added TimescaleDB prerequisite note for growth analysis

## Data Corrections Applied (Targeted Batch: id=257)
**Batch:** `FT-B0604D6B-24Q1-LHS` (component `B0604D6B-46AE-4F09-9FAE-00B62F550F18`)

### 1) Active container assignments
**Problem:** 24 active containers, all lifecycle stages present as "active".  
**Root cause:** migration logic used the earliest stage and a 365‑day activity window, leaving many historical assignments active.

**Fix in `pilot_migrate_component.py`:**
- Batch stage now derives from the **latest** population in the component.
- Added `--assignment-active-window-days` (default 30).
- Active assignments are **clamped to the current stage**.

**Result (batch 257 re-run):**
- Before: 347 assignments, 24 active
- After: 347 assignments, **2 active** (Adult), batch stage corrected to **Adult**.

### 2) Feed containers & stock
**Problem:** feed purchases existed, but **no feed containers or stock**.  
**Root cause:** `pilot_migrate_feed_inventory.py` was not idempotent when purchases already existed without `ExternalIdMap`; it skipped creating containers/stock.

**Fix in `pilot_migrate_feed_inventory.py`:**
- Reuse existing purchases when `ExternalIdMap` is missing.
- Create `FeedContainer` + `FeedContainerStock` idempotently.

**Result (global migration run):**
- `infrastructure_feedcontainer`: **167**
- `inventory_feedcontainerstock`: **21,167**
- `inventory_feedpurchase`: **21,163** (unchanged)

## Workflow Explosion and Long Duration Phenomenon
### Background
FishTalk stopped recording FW→sea transfers around 2023. We stitch by project tuple `(ProjectNumber, InputYear, RunningNumber)` instead of `PublicTransfers`. This is correct for batch identity, but **stage timings can be spread across many populations**.

### Original Workflow Explosion
**Root cause:** `pilot_migrate_component_transfers.py` created **one lifecycle workflow per population stage change** using `PopulationProductionStages`, causing hundreds of workflows for a single batch.

**Fix applied:**
- Lifecycle workflows consolidated to **one workflow per batch stage transition**.
- Actions generated per destination assignment (container) in the new stage.
- Old stage transition workflows are deleted for the component before rebuilding.

**Result (batch 257):**
- Lifecycle workflows: **4** (no Post‑Smolt in data)
- Container redistribution workflows: **14** (from `PublicTransfers`)

### Long Duration in Lifecycle Workflows
Example: `http://localhost:5002/transfer-workflows/6287` (Egg→Fry)
- Workflow dates: **2025-03-04 → 2025-10-03**
- Actions: **5**, dates match the Fry assignment window
- Egg assignments for this batch are **2024-07-17 → 2024-09-30**
- Fry assignments are **2025-03-04 → 2025-10-03**

**Why it looks wrong:**  
We infer lifecycle transitions from **assignment timing** within a stitched batch. When project-based stitching aggregates populations whose stage starts are months apart, the resulting lifecycle workflow spans that entire window. This is a data artifact of stitching, not an API bug.

### Hypotheses for long durations
1. **Project tuple grouping includes multiple cohorts** that entered Fry at very different times.
2. **Stage events are sparse/incomplete** for many populations (many have only one stage in `PopulationProductionStages`), so assignment timing becomes the only signal.
3. **FishTalk upgrade (2023) broke FW→sea linking**, so the stitched batch covers longer time spans by design.

### Suggested Fixes (choose one)
1. **Cohort split**: split a stitched batch into multiple batches when stage gaps exceed a threshold (e.g., >120 days).
   - Pro: lifecycles look realistic.
   - Con: changes batch identity and totals (bigger migration change).
2. **Clamp workflow duration**: keep all actions but set workflow start/end to a short window (e.g., min action date + 90 days).
   - Pro: minimal data changes; UI looks sane.
   - Con: dates become “presentation adjusted.”
3. **Windowed workflows**: split lifecycle workflows into time windows (e.g., per quarter).
   - Pro: preserves identity while reducing extremes.
   - Con: more workflows (but still far fewer than per-population).

## Commands Run (Targeted)
- Re-run component migration for batch 257 with fixed assignment logic:
  - `pilot_migrate_component.py --component-key B0604D6B-46AE-4F09-9FAE-00B62F550F18 --report-dir scripts/migration/output/project_batch_migration/1_24_1 --use-csv scripts/migration/data/extract/ --assignment-active-window-days 30`
- Re-run transfers for batch 257:
  - `pilot_migrate_component_transfers.py --component-key B0604D6B-46AE-4F09-9FAE-00B62F550F18 --report-dir scripts/migration/output/project_batch_migration/1_24_1`
- Feed inventory migration (global):
  - `pilot_migrate_feed_inventory.py`

## Notes / Gotchas
- **TimescaleDB required** for growth analysis (`ActualDailyAssignmentState`).
- **Transfer workflow UI** expects filtered `batch` in API query; unfiltered results show all 1445 workflows.
- **Environmental migration** is now safe to run in parallel with SQLite index.
