# HANDOFF 2026-02-27 - FW transfer-active rerun, mix-backfill coverage blocker

## Scope
- Complete FW stabilization session to explicit go/no-go after mix-semantic integration.
- Build and execute a deterministic transfer-active scope rerun.
- Run transfer mix-event backfill coverage checks.
- Recompute FW fixed-source row-recheck board and residual ranking.

## Baseline reproduced
- Wave21 fixed-source baseline reference:
  - `scripts/migration/output/fw_b_class_row_recheck_wave21_next5_bucket2_no_internal_override_migrdb_20260226_120635.json`
  - baseline taxonomy: `A=0, B=14, C=3, D=0`

## Transfer-active scope execution (what was run)
- Deterministic scope artifacts:
  - `scripts/migration/output/fw_transfer_active_scope_v2_20260227_085607.json`
  - `scripts/migration/output/fw_transfer_active_scope_v2_20260227_085607.csv`
  - `scripts/migration/output/fw_transfer_active_scope_v2_20260227_085607.md`
  - `scripts/migration/output/fw_transfer_active_scope_v2_20260227_085607_selected_keys.txt`
- Clean rerun sequence executed:
  1. `python3 scripts/migration/clear_migration_db.py`
  2. `python3 scripts/migration/setup_master_data.py`
  3. `python3 scripts/migration/tools/pilot_migrate_health_master_data.py --use-csv scripts/migration/data/extract`
  4. `python3 scripts/migration/tools/input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching`
  5. 22-key rerun loop via `pilot_migrate_input_batch.py`
- Rerun artifact:
  - `scripts/migration/output/fw_transfer_active_full_rerun_20260227_085811.json`
  - `scripts/migration/output/fw_transfer_active_full_rerun_20260227_085811.md`
  - status: `all_succeeded=True` (22/22 commands exit 0)

## Core result (blocking evidence)
- Post-rerun transfer/mix counts remained zero:
  - `batch_batchtransferworkflow=0`
  - `batch_transferaction=0`
  - `batch_mix_event=0`
  - `batch_mix_event_component=0`
- Mix backfill command result (twice, unchanged):
  - `python3 scripts/migration/tools/pilot_backfill_transfer_mix_events.py`
  - summary: `Scanned actions: 0`, `Qualified mix actions: 0`
- Coverage artifact:
  - `scripts/migration/output/fw_transfer_mix_backfill_coverage_20260227_094457.json`
  - `scripts/migration/output/fw_transfer_mix_backfill_coverage_20260227_094457.md`

## Deterministic blocker confirmation
- Corrected feasibility artifact (pipeline-truth check):
  - `scripts/migration/output/fw_transfer_active_scope_v3_input_members_20260227_094548.json`
  - `scripts/migration/output/fw_transfer_active_scope_v3_input_members_20260227_094548.md`
  - `scripts/migration/output/fw_transfer_active_scope_v3_input_members_20260227_094548.csv`
- Result:
  - `total_batch_keys=1417`
  - `keys_with_internal_source_to_dest_edges=0` when evaluated against current `input_population_members.csv` sets used by `pilot_migrate_input_batch.py`
- Interpretation:
  - Under current input-members scope generation, no cohort can materialize `SourcePopBefore -> DestPopAfter` internal edges for transfer workflow creation.
  - Therefore transfer workflows/actions and mix-event backfill cannot be exercised by scope selection alone.

## External-edge evidence pack (for FT follow-up)
- `scripts/migration/output/fw_transfer_external_edge_samples_20260227_094632.json`
- `scripts/migration/output/fw_transfer_external_edge_samples_20260227_094632.md`
- Shows representative operations where `SourcePopBefore` is in cohort set but `DestPopAfter` is outside current cohort membership.

## Invariants and regressions
- `migration_counts_report` executed.
- `migration_verification_report` executed and failed required gates:
  - `batch_batchtransferworkflow=0`
  - `batch_transferaction=0`
  - `environmental_environmentalreading=0` (expected due skip-environmental profile used for this session)
- Regression tests:
  - `apps.batch.tests.test_workflow` -> PASS (`7`)
  - `apps.inventory.tests.test_fcr_service` -> PASS (`35`)
  - `apps.batch.tests apps.inventory.tests` -> PASS (`490`)

## FW fixed-source row-recheck (current migr db)
- Artifacts:
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_migrdb_20260227_094426.json`
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_migrdb_20260227_094426.md`
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_migrdb_20260227_094426.csv`
- Residual ranking:
  - `scripts/migration/output/fw_fishtalk_culprits_transfer_scope_top20_20260227_094426.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_transfer_scope_top20_20260227_094426.md`
- Current computed board (fixed source + wave21 rule stack):
  - `before_mismatch_rows=20`
  - `after_mismatch_rows=2`
  - taxonomy after: `A=0, B=0, C=2, D=0`
  - top residual: batch `90` (`24Q1 LHS ex-LC`), `2` rows (`C`)
- Note:
  - This row-recheck reflects current rerun scope state and fixed-source/rule reuse, but transfer-path coverage is still blocked (no transfer actions available).

## Go / No-go
- Decision: **FW not yet ready**.
- Rationale:
  1. Mandatory transfer-path validation remains unexecuted (`TransferAction=0`, `BatchMixEvent=0`).
  2. Mix lineage backfill cannot be validated without non-zero transfer actions.
  3. Verification gate fails required transfer tables.

## Precise next FT inspection questions
1. For FW cohorts (example samples in `fw_transfer_external_edge_samples_20260227_094632.*`), are `DestPopAfter` populations expected to belong to a different input-batch key than `SourcePopBefore`?
2. Is the intended migration truth that transfer workflows should include edges where source population is in cohort scope but destination population is outside current input-members scope?
3. For sampled operations, should destination-side lineage be pulled into cohort migration scope (descendant expansion), or should cross-scope transfer actions be materialized directly?

## Smallest deterministic next candidate
- Candidate:
  - Add an explicit transfer-scope mode to `pilot_migrate_component_transfers.py` that supports **source-in-scope to destination-out-of-scope** edges with deterministic telemetry (`created/updated/skipped by reason`), without schema changes.
- Acceptance criteria:
  1. `batch_batchtransferworkflow > 0`
  2. `batch_transferaction > 0`
  3. `pilot_backfill_transfer_mix_events.py` scans non-zero actions
  4. mix coverage artifact reports candidate/action parity and `allow_mixed` outcomes
  5. `A` remains `0`, no `C` expansion

## Files changed in this session
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-27_FW_TRANSFER_ACTIVE_SCOPE_RERUN_AND_MIX_COVERAGE_BLOCKER.md` (new)

