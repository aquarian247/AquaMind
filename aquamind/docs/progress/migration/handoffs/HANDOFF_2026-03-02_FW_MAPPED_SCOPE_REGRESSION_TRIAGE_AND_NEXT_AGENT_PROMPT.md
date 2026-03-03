# HANDOFF 2026-03-02 - FW mapped-scope replay completed, regression triage required

## Why this handoff exists
- User requested takeover because migration quality appears regressed versus ~2 weeks ago.
- Main concerns:
  1. More batches appear stuck in one lifecycle stage.
  2. `MIX-*` batches now greatly outnumber normal batches.
  3. Need to know whether A/B/C/D issue taxonomy has regressed.

## Execution completed in this session
- Re-ran focused FW scope (mapped Faroese + FW22/FW13) from clean `migr_dev`.
- Original monolithic scope run stalled; switched to chunked replay (4 x 5 batches), all successful.

### Replay chain run (chunked)
1. `python3 scripts/migration/clear_migration_db.py`
2. `python3 scripts/migration/setup_master_data.py`
3. `python3 scripts/migration/tools/pilot_migrate_health_master_data.py --use-csv scripts/migration/data/extract`
4. `python3 scripts/migration/tools/pilot_migrate_input_batch.py --scope-file <chunkN.csv> --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --expand-subtransfer-descendants --transfer-edge-scope internal-only` (N=1..4)
5. `python3 scripts/migration/tools/pilot_backfill_transfer_mix_events.py`
6. `python3 scripts/migration/tools/migration_counts_report.py`
7. `python3 scripts/migration/tools/migration_verification_report.py`

## Current state snapshot (post-run)
- Scope replay: `20/20` attempted, `0` failures.
- Backfill summary:
  - scanned actions: `280`
  - qualified mix actions: `169`
  - mix events created: `169`
  - mix event components written: `473`
- Core counts:
  - `batch_batch=189`
  - `batch_transferaction=280`
  - `batch_batchcontainerassignment=569`
  - `migration_support_externalidmap=4137`
- Verification completed (no stall), but reports expected/known missing required tables in this profile:
  - `infrastructure_area=0`
  - `health_licecount=0`
  - `health_journalentry=0`
  - `environmental_environmentalreading=0`

## Regression signals observed

### 1) MIX batch proliferation is very high
- From counts report:
  - `MIX-*` batches: `169`
  - non-`MIX` batches: `20`
  - ratio: ~`8.45:1`
- This is currently consistent with backfill implementation behavior: one synthetic mixed batch per qualified mixed transfer action (`MIX-FTA-<action_id>`), not necessarily random data corruption.

### 2) Lifecycle coverage looks regressed
- Verification stage-coverage section shows:
  - all batches: `177/189` one-stage (`93.7%`)
  - `MIX-*` only: `169/169` one-stage (`100%`)
  - non-`MIX` only: `8/20` one-stage (`40%`)
- Non-`MIX` one-stage batches include:
  - `24Q1 LHS ex-LC`
  - `AquaGen juni 25`
  - `Bakkafrost S-21 okt 25`
  - `Benchmark Gen. Septembur 2024`
  - `SF nov 2025`
  - `Stofnfiskur Aug 23`
  - `Stofnfiskur Juni 24`
  - `Stofnfiskur S21 okt 25`

### 3) Specific contradiction to investigate
- `Stofnfiskur Juni 24` appears in verification table as current stage `Parr`, but stage coverage still reports `1/6 stages - Egg&Alevin`.
- This likely indicates stage-history materialization/reporting mismatch, not only UI.

## A/B/C/D status right now
- Last known fixed-source row-recheck board (2026-02-28 artifact) was:
  - `A=0, B=39, C=3, D=0`
  - Source: `scripts/migration/output/fw_b_class_row_recheck_pathb_fw78_migrdb_20260228_204846.json`
- Fresh A/B/C/D recompute was attempted via:
  - `python3 scripts/migration/tools/migration_pilot_regression_check.py`
- Current run is blocked by missing `ExternalIdMap` rows for 5 components, so fresh taxonomy numbers are **not currently computable**:
  - `FA8EA452-AFE1-490D-B236-0150415B6E6F`
  - `B884F78F-1E92-49C0-AE28-39DFC2E18C01`
  - `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`
  - `81AC7D6F-3C81-4F36-9875-881C828F62E3`
  - `251B661F-E0A6-4AD0-9B59-40A6CE1ADC86`
- Therefore:
  - **A/B/C/D is unknown for current state**
  - known gate tooling is currently partially broken on this DB snapshot

## Artifacts produced this session
- `scripts/migration/output/focus_mapped_clear_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_setup_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_health_master_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_scope_chunk1_20260302_132906.txt`
- `scripts/migration/output/focus_mapped_scope_chunk2_20260302_132906.txt`
- `scripts/migration/output/focus_mapped_scope_chunk3_20260302_132906.txt`
- `scripts/migration/output/focus_mapped_scope_chunk4_20260302_132906.txt`
- `scripts/migration/output/focus_mapped_backfill_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_counts_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_counts_all_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_verification_20260302_132906_chunked.txt`
- `scripts/migration/output/focus_mapped_regression_20260302_140122.txt`
- `aquamind/docs/progress/migration/analysis_reports/2026-02-06/semantic_validation_pilot_cohort_2026-03-02.md`

## Immediate priorities for next agent
1. Restore ability to compute current A/B/C/D board (fix missing `ExternalIdMap` blockers first).
2. Separate expected one-stage `MIX-*` behavior from true non-`MIX` lifecycle-history regression.
3. Deep-trace `Stofnfiskur Juni 24` stage-history mismatch (`Parr` now but `Egg&Alevin` coverage only).
4. Decide whether mix backfill policy is too aggressive for freeze parity (e.g. scope/date/batch filters) versus expected by design.

## Suggested first command block for takeover
```bash
cd /Users/aquarian247/Projects/AquaMind
export PYTHONPATH="/Users/aquarian247/Projects/AquaMind"

# 1) Confirm current post-run state quickly
python3 scripts/migration/tools/migration_counts_report.py --prefix ""
python3 scripts/migration/tools/migration_verification_report.py

# 2) Re-run regression gate and capture blockers
stamp=$(date +%Y%m%d_%H%M%S)
python3 scripts/migration/tools/migration_pilot_regression_check.py \
  > "scripts/migration/output/focus_mapped_regression_retry_${stamp}.txt" 2>&1 || true

# 3) If still blocked, resolve missing ExternalIdMap entries for the five component keys above,
#    then rerun migration_pilot_regression_check.py to recover fresh A/B/C/D taxonomy.
```

## Decision risk statement
- Migration execution is back on track operationally (no stall with chunking), but quality gate confidence is incomplete until A/B/C/D can be recomputed on the current DB and non-`MIX` one-stage regressions are explained or fixed.
