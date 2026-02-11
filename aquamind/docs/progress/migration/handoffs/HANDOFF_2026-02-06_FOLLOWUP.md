# Migration Handoff (2026-02-06 Follow-up)

## Scope of this follow-up
- Continued FW validation focused on station fidelity and lifecycle-stage sanity.
- Investigated S21 and SF NOV 23 progression issues reported from GUI and FishTalk timeline charts.
- Updated validator to reduce false lifecycle increase alerts caused by in-stage redistribution inflation.

## What changed in code

### 1) Semantic stage sanity now uses stage-entry populations
File:
- `scripts/migration/tools/migration_semantic_validation_report.py`

Changes:
- Added `--stage-entry-window-days` (default `2`).
- Stage transition deltas now use **entry population** per stage:
  - first non-zero assignment date per stage,
  - within configurable window,
  - max-per-container dedupe.
- Full summed stage population is still reported as a secondary diagnostic.
- Existing mixed-batch exception remains in place for increase alerts.

Result:
- S21 false positive `Fry -> Parr` increase is removed in the updated report.

### 2) Station mismatch prevention documented and retained
Files (already changed before this follow-up, re-verified):
- `scripts/migration/tools/pilot_migrate_input_batch.py`
- `scripts/migration/tools/pilot_migrate_component.py`

Behavior:
- `--expected-site` enforces strict station identity.
- Input-batch preflight compares InputProjects, Ext_Inputs-derived sites, and selected member sites.
- Component script includes batch-name station-code guard (e.g., `S-21`).

### 3) Mortality replay behavior (re-verified)
Files (already changed before this follow-up):
- `scripts/migration/tools/pilot_migrate_component_mortality.py`
- `scripts/migration/tools/pilot_migrate_component_culling.py`
- `scripts/migration/tools/pilot_migrate_component_escapes.py`
- baseline metadata set in `scripts/migration/tools/pilot_migrate_component.py`

Behavior:
- Assignment population count is synchronized as:
  - `baseline_population_count - (mortality + culling + escapes totals)`
- Keeps replays idempotent and deterministic per mapped population.

## Reports regenerated (2026-02-06)
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_stofnfiskur_s21_nov23_2026-02-06.md`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_sf_nov_23_2026-02-06.md`

Key output highlights:
- **S21 (`Stofnfiskur S-21 nov23`)**
  - Stage sanity (entry-based):
    - Egg&Alevin -> Fry: `-272,818` (OK)
    - Fry -> Parr: `-65,711` (OK)
  - No artificial stage increase remains in this transition.

- **SF NOV 23 (`SF NOV 23|5|2023`)**
  - Stage sanity (entry-based) still shows:
    - Parr -> Post-Smolt: `+154,981` (ALERT)
  - This is still unresolved and is the primary current issue.

## Data/model clarifications captured in docs
- `outside component` in semantic reports means transfers to populations outside the selected stitched population set.
- `known removals` means mortality + culling + escapes + harvest counts.
- Hall mapping remains authoritative where FishTalk stage labels are noisy.

## Current unresolved problem
Need explicit classification of FishTalk short-lived bridge fishgroups versus real stage-entry fishgroups for problematic transitions (currently observed in SF NOV 23 progression).

## Next intended task (for next agent)
User plans to provide a **small fishgroupnumber -> container/time extract** for one problematic transition.

Next agent should:
1. Parse the provided extract and map fishgroupnumbers to migrated populations (or nearest transfer events by date/container).
2. Add a classifier in `migration_semantic_validation_report.py` that tags entries as:
   - `temporary_bridge_fishgroup`
   - `real_stage_entry_fishgroup`
3. Use classifier output in stage sanity to avoid counting temporary bridge fishgroups as stage-entry population.
4. Re-run semantic report for the target component and verify that transitions align with FishTalk chart evidence.

## Reproduction commands

S21 report:
```bash
python scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key B884F78F-1E92-49C0-AE28-39DFC2E18C01 \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_S-21_nov23_5_2023 \
  --use-csv scripts/migration/data/extract \
  --stage-entry-window-days 2 \
  --output aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_stofnfiskur_s21_nov23_2026-02-06.md
```

SF NOV 23 report:
```bash
python scripts/migration/tools/migration_semantic_validation_report.py \
  --component-key FA8EA452-AFE1-490D-B236-0150415B6E6F \
  --report-dir scripts/migration/output/input_batch_migration/SF_NOV_23_5_2023 \
  --use-csv scripts/migration/data/extract \
  --stage-entry-window-days 2 \
  --output aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_sf_nov_23_2026-02-06.md
```

## Notes for handoff continuity
- Keep FW and Sea unlinked (no FW->Sea linkage logic change in this follow-up).
- Keep docs factual; avoid inferred mappings without extract evidence.
- Use station guards (`--expected-site`) in verification runs to prevent accidental cross-station replay.

---

## 2026-02-09 Continuation Addendum

### A) SF NOV 23 bridge-aware stage transition resolved in semantic report
File:
- `scripts/migration/tools/migration_semantic_validation_report.py`

Result in report:
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_sf_nov_23_2026-02-06.md`
- `Parr -> Post-Smolt` changed from `+154,981 (ALERT)` to `0 (OK)` using fishgroup bridge-aware source linkage.

Classification evidence for the problematic transition:
- Temporary bridge fishgroup: `235.0127` (`4E1DC17B-900B-4A8F-BDCE-1516792EB6D5`)
- Real Post-Smolt entry fishgroup: `235.0001` (`C638A5E2-1EA3-4891-BFD1-7F316809852C`)
- Linked Parr source fishgroups: `235.0112`, `235.0128`

### B) Transfer workflow noise reduction (zero-count stage actions)
Files:
- `scripts/migration/tools/pilot_migrate_component_transfers.py`
- `scripts/migration/tools/pilot_migrate_input_batch.py`

Behavior:
- Added `pilot_migrate_component_transfers.py --skip-synthetic-stage-transitions`
  - Keeps transfer-edge-backed workflows/actions only.
  - Removes assignment-derived `PopulationStageTransitionAction` noise.
- `pilot_migrate_input_batch.py` now defaults to skipping synthetic stage transitions.
  - Use `--include-synthetic-stage-transitions` to restore legacy behavior.

Observed impact after transfer replay with `--skip-synthetic-stage-transitions`:
- SF NOV 23:
  - loaded SubTransfers edges: `44`
  - transfer actions after replay: `44`
  - zero-count actions: `0`
  - lifecycle workflows/actions: `15 / 15`
- S21:
  - loaded SubTransfers edges: `134`
  - transfer actions after replay: `134`
  - zero-count actions: `0`
  - lifecycle workflows/actions: `7 / 7`
