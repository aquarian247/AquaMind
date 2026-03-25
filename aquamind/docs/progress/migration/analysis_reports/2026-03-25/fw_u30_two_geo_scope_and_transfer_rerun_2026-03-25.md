# FW U30 Two-Geography Scope And Transfer Rerun (2026-03-25)

## Scope Basis

- Goal for this pass: stay FW-only, broaden to all FW batches `<30 months` from backup cutoff `2026-01-22`, classify the queue across both geographies, rerun only the eligible transfer-bearing rows, and keep FW->Sea paused.
- Mechanical source inputs:
  - `scripts/migration/output/input_stitching/input_batches.csv`
  - `scripts/migration/output/input_stitching/input_population_members.csv`
  - current `input_batch_migration/*` report dirs
  - current `migr_dev` `ExternalIdMap` state
- Applied scope rule:
  - strict FW-only = `is_valid=True`, `earliest_start >= 2023-07-22`, and `aquamind_stages ⊆ {Egg&Alevin,Fry,Parr,Smolt}`
- Geography was derived from member-site policy heuristics from `DATA_MAPPING_DOCUMENT.md` because the stitched `geographies` field is still stale/`Unknown` for much of the current FW scope.
- Important rerun prerequisite discovered during execution:
  - `input_batch_migration` report-dir presence is not sufficient for transfer replay;
  - rerun also requires a `FishTalk / PopulationComponent / <component_key>` `ExternalIdMap` row in `migr_dev`.

## Classification Result

- Strict FW-only `<30 months` scope: `161`
  - Faroe Islands: `64`
  - Scotland: `97`
- Strict classification:
  - eligible: `58`
  - manual reconstruction exceptions: `4`
  - blocked: `99`
- Blocked reason split:
  - missing `input_batch_migration` report dir: `47`
  - missing `ExternalIdMap` for `PopulationComponent`: `52`
- Replay-candidate subset under the older “exclude singleton `{Egg&Alevin}` / `{Fry}` signatures” rule: `76`
  - eligible: `26`
  - manual: `2`
  - blocked: `48`
- That older replay subset is not sufficient by itself for this broadened pass:
  - eligible transfer-bearing rows in the full strict scope: `52`
  - eligible transfer-bearing rows inside the older replay subset: `23`
  - additional strict-only early-stage transfer-bearing rows: `29`

## Manual Reconstruction Exceptions

- `Gjógv/Fiskaaling mars 2023|5|2023`
  - Faroe Islands
  - stages: `Fry`
  - raw SubTransfers: `6`
  - reason: creation actions land on Parr assignments, not Egg&Alevin
- `Stofnfiskur feb 2025|1|2025`
  - Faroe Islands
  - stages: `Egg&Alevin, Fry`
  - raw SubTransfers: `98`
  - reason: guarded creation repair still leaves the batch materially below creation total
- `Benchmark Gen. Mars 2025|1|2025`
  - Faroe Islands
  - stages: `Egg&Alevin`
  - raw SubTransfers: `199`
  - reason: guarded creation repair still leaves the batch materially below creation total
- `24Q1 LHS ex-LC|13|2023`
  - Scotland
  - stages: `Parr`
  - raw SubTransfers: `15`
  - reason: creation actions land on Parr assignments, not Egg&Alevin

## Queue Execution

### 1. Initial queue attempt exposed a new concrete blocker

- First queue attempt used the report-ready rows before checking `PopulationComponent` maps.
- Result:
  - `Bakkafrost Juli 2023|3|2023` reran cleanly
  - `Bakkafrost S-21 aug23|4|2023` failed immediately with:
    - `Missing ExternalIdMap for PopulationComponent BCD6C51F-044C-436C-A07B-302E4C129156`
- Interpretation:
  - this was not a new transfer-baseline defect;
  - it was a queue-classification defect.
- Action taken:
  - broadened-scope builder was hardened to require `PopulationComponent` map presence before classifying a row as rerunnable.

### 2. Filtered eligible transfer-bearing rerun

- Final rerun queue size: `52`
  - Faroe Islands: `41`
  - Scotland: `11`
- Execution result: `52/52` succeeded, `0` failed.
- Runtime window:
  - started: `2026-03-25T09:34:29.510897+00:00`
  - finished: `2026-03-25T09:43:36.871879+00:00`

## Artifacts

- Scope builder outputs:
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.json`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.md`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.strict.csv`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.replay.csv`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.transfer_queue.csv`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.manual.csv`
  - `scripts/migration/output/fw_u30_two_geo_scope_20260325.blocked.csv`
- Initial queue attempt showing the `PopulationComponent` map blocker:
  - `scripts/migration/output/fw_u30_transfer_rerun_20260325/run_summary.json`
  - `scripts/migration/output/fw_u30_transfer_rerun_20260325/logs/002_Bakkafrost_S-21_aug23_4_2023.log`
- Final filtered rerun summary:
  - `scripts/migration/output/fw_u30_transfer_rerun_20260325_filtered/run_summary.json`
  - per-batch logs under `scripts/migration/output/fw_u30_transfer_rerun_20260325_filtered/logs/`

## Stop Point

- FW-only broadened queue is now documented with explicit eligible/manual/blocked separation across both geographies.
- Eligible transfer-bearing FW rows have been rerun on the corrected transfer baseline.
- Manual exceptions remain explicitly excluded from bulk rerun.
- FW->Sea remains paused.
