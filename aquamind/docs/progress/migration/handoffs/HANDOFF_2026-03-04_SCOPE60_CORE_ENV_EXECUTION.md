# Scope-60 Core + Environmental Residual Execution (2026-03-04)

## What was executed

1. **Unblocked scope-60 keyspace for core replay**
   - Refreshed stitching-critical FishTalk extracts:
     - `ext_inputs`, `populations`, `population_stages`, `production_stages`,
       `containers`, `org_units`, `grouped_organisation`, `input_projects`, `sub_transfers`
   - Rebuilt input stitching with `--min-populations 1` into canonical `input_stitching`.
   - Re-ran core dry-run probe for full scope-60 key file:
     - `Batches attempted: 60`
     - `Failures: 0`

2. **Applied scope-60 core/health residuals (feed-inventory + environmental skipped)**
   - Run directory:
     - `scripts/migration/output/fw_scope60_core_health_apply_20260303_171300/`
   - Sliced execution:
     - `keys_slice1` success
     - `keys_slice2` initially had 1 failed key:
       - `Bakkafrost S-21 jan 25|1|2025`
       - Root cause: duplicate `batch_number` unique constraint on `batch_batch.batch_number`
     - `keys_slice3..keys_slice6` success
   - Remediation for failed key:
     - Added component-key reuse logic by existing `batch_number` mapping.
     - Re-ran failed key successfully (`11/11 scripts completed`).

3. **Applied scope-60 environmental residuals (environmental-only mode)**
   - Added `--only-environmental` mode to `pilot_migrate_input_batch.py`.
   - Initial attempt failed fast (signature mismatch regression), then fixed.
   - Retry run completed:
     - `scripts/migration/output/fw_scope60_environmental_only_apply_20260303_214716/scope60_environmental_only_retry.log`
     - `Batches attempted: 60`
     - `Failures: 0`


## Code changes made

### `scripts/migration/tools/pilot_migrate_input_batch.py`

- Added `PopulationComponent` map reuse by existing `batch_number`:
  - Prevents duplicate-batch-number failure on idempotent replays.
- Added `--only-environmental` flag:
  - Runs only `pilot_migrate_component_environmental.py` while retaining preflight + component scope generation.
- Added script selection helper (`is_script_enabled`) used by dry-run and execution path.
- Added argument propagation for `--only-environmental` in `--scope-file` mode.
- Added validation:
  - reject `--only-environmental` with `--skip-environmental`.
- Updated `load_input_batch_info(...)` signature to accept `use_csv` (compatibility for caller path).


## Verification evidence

### Core/health run evidence

- Consolidated slice summary:
  - `scripts/migration/output/fw_scope60_core_health_apply_20260303_171300/core_health_slice_summary.json`
- Failed-key remediation log:
  - `scripts/migration/output/fw_scope60_core_health_apply_20260303_171300/debug_Bakkafrost_S21_jan25_apply_after_patch.log`

### Environmental run evidence

- Retry execution log:
  - `scripts/migration/output/fw_scope60_environmental_only_apply_20260303_214716/scope60_environmental_only_retry.log`
- Duration stats:
  - `scripts/migration/output/fw_scope60_environmental_only_apply_20260303_214716/environmental_run_stats.json`


## Count deltas

### Core/health pass delta (baseline -> post core/health)

- Source:
  - `scripts/migration/output/fw_scope60_core_health_apply_20260303_171300/count_deltas_migr_dev.json`
- Notable deltas:
  - `batch_batch`: `+42`
  - `batch_creationworkflow`: `+42`
  - `batch_batchtransferworkflow`: `+181`
  - `inventory_feedingevent`: `+79,713`
  - `batch_mortalityevent`: `+101,165`
  - `health_treatment`: `+1,326`
  - `health_journalentry`: `+452`

### Environmental pass delta (env baseline -> post env)

- Source:
  - `scripts/migration/output/fw_scope60_environmental_only_apply_20260303_214716/environmental_count_delta.json`
- Delta:
  - `environmental_environmentalreading`: `+1,114,956`

### Overall baseline -> final (core/health + env)

- Source:
  - `scripts/migration/output/fw_scope60_core_health_apply_20260303_171300/overall_delta_from_baseline_to_final.json`


## Current residual status

- **Feed/infra lineage scope-60:** completed previously (0 unresolved stores after OrgUnit fallback).
- **Core/health residual scope-60:** completed (all 60 keys processed; 1 transient failure remediated and replayed successfully).
- **Environmental residual scope-60:** completed (all 60 keys processed; 0 failures).


## Risks / notes

- Extract preflight warning persists:
  - `operation_stage_changes` max date lagging horizon by ~4 days.
  - Guard currently allows this lag and run completed with no hard preflight failure.
- High environmental `updated` activity is expected idempotent upsert behavior; count delta here confirms substantial net materialization (+1,114,956).


## Freeze-readiness snapshot

- Scope-60 residual execution for **core + health + environmental + feed/infra** is now execution-complete with evidence artifacts.
- Next recommended step is freeze-grade verification (parity and integrity checks) before final freeze sign-off.


## Exact next-step commands

```bash
# 1) Inspect slice + remediation summaries
python3 - <<'PY'
import json, pathlib
run = pathlib.Path("scripts/migration/output/fw_scope60_core_health_apply_20260303_171300")
print((run / "core_health_slice_summary.json").read_text()[:4000])
print((run / "count_deltas_migr_dev.json").read_text()[:4000])
PY

# 2) Inspect environmental completion + delta
python3 - <<'PY'
import pathlib
run = pathlib.Path("scripts/migration/output/fw_scope60_environmental_only_apply_20260303_214716")
print((run / "environmental_run_stats.json").read_text()[:4000])
print((run / "environmental_count_delta.json").read_text()[:4000])
PY

# 3) Re-run dry-run gate for full 60 keyspace (sanity)
python3 scripts/migration/tools/pilot_migrate_input_batch.py \
  --scope-file scripts/migration/output/fw_scope60_feed_infra_extract_descendants_20260303_131729/scope_batch_keys_for_replay.csv \
  --use-csv scripts/migration/data/extract \
  --skip-environmental \
  --skip-feed-inventory \
  --expand-subtransfer-descendants \
  --transfer-edge-scope internal-only \
  --allow-station-mismatch \
  --dry-run
```
