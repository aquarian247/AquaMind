# HANDOFF 2026-02-27 - FW transfer stage-bucket implementation and rerun

## Scope
- Implement deterministic transfer workflow migration rules agreed in-session:
  - source-in-scope SubTransfer edges (destination may be out-of-scope)
  - stage-bucket workflow grouping
  - skip stations/edges without hall-stage mapping
- Re-run full transfer-active FW scope on wiped DB.
- Re-run mix backfill coverage, fixed-source row-recheck, and regressions.

## Code changes
- Updated: `scripts/migration/tools/pilot_migrate_component_transfers.py`
  - Added transfer mode args:
    - `--transfer-edge-scope` (`source-in-scope` default, `internal-only`)
    - `--workflow-grouping` (`stage-bucket` default, `operation`)
  - SubTransfers selection now supports source-in-scope edges.
  - Stage-bucket workflow grouping introduced:
    - grouped by `component + station + workflow_type + source_stage + dest_stage`
    - deterministic workflow identifiers and numbers
  - Hall-stage classification via existing `stage_from_hall(...)` mapping.
  - Added destination assignment synthesis for out-of-scope destination populations when container mapping exists.
  - Added explicit skip-reason telemetry (e.g., missing hall-stage mapping, unmapped destination container).

## Full rerun execution
- Wipe/setup pipeline executed:
  1. `scripts/migration/clear_migration_db.py`
  2. `scripts/migration/setup_master_data.py`
  3. `scripts/migration/tools/pilot_migrate_health_master_data.py --use-csv scripts/migration/data/extract`
  4. `scripts/migration/tools/input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching`
  5. 22-key rerun loop using `pilot_migrate_input_batch.py`
- Rerun artifacts:
  - `scripts/migration/output/fw_transfer_active_full_rerun_post_stagebucket_20260227_121508.json`
  - `scripts/migration/output/fw_transfer_active_full_rerun_post_stagebucket_20260227_121508.md`
  - Result: `all_succeeded=True` (`22/22`)

## Transfer/mix coverage outcomes
- Post-rerun counts:
  - `batch_batchtransferworkflow=7`
  - `batch_transferaction=129`
  - `batch_mix_event=0`
  - `batch_mix_event_component=0`
- Per-batch transfer summary artifact:
  - `scripts/migration/output/fw_transfer_action_creation_summary_post_stagebucket_20260227_124158.csv`
  - `scripts/migration/output/fw_transfer_action_creation_summary_post_stagebucket_20260227_124158.md`
- `pilot_backfill_transfer_mix_events.py`:
  - `Scanned actions: 129`
  - `Qualified mix actions: 0`
  - `Mix events created: 0`
- Coverage artifacts:
  - `scripts/migration/output/fw_transfer_mix_backfill_coverage_post_stagebucket_20260227_121744.json`
  - `scripts/migration/output/fw_transfer_mix_backfill_coverage_post_stagebucket_20260227_121744.md`
- Interpretation:
  - Transfer path is now exercised (non-zero workflows/actions).
  - This scope still has zero container/date cross-batch co-location candidates, so mix-event materialization remains zero by evidence.

## Invariants + verification + tests
- `migration_counts_report` executed (transfer tables populated).
- `migration_verification_report` executed:
  - transfer tables now pass
  - single required failure remains: `environmental_environmentalreading=0` (expected with `--skip-environmental`)
- Regression suites:
  - `manage.py test --keepdb --noinput apps.batch.tests.test_workflow` -> PASS (`7`)
  - `manage.py test --keepdb --noinput apps.inventory.tests.test_fcr_service` -> PASS (`35`)
  - `manage.py test --keepdb --noinput apps.batch.tests apps.inventory.tests` -> PASS (`497`, `skipped=4`)

## Fixed-source row-recheck (post stage-bucket rerun)
- Artifacts:
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_post_stagebucket_migrdb_20260227_121856.json`
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_post_stagebucket_migrdb_20260227_121856.csv`
  - `scripts/migration/output/fw_b_class_row_recheck_transfer_scope_post_stagebucket_migrdb_20260227_121856.md`
- Residual ranking:
  - `scripts/migration/output/fw_fishtalk_culprits_transfer_scope_post_stagebucket_top20_20260227_121856.csv`
  - `scripts/migration/output/fw_fishtalk_culprits_transfer_scope_post_stagebucket_top20_20260227_121856.md`
- Board:
  - `before_mismatch_rows=20`
  - `after_mismatch_rows=2`
  - `delta=-18`
  - taxonomy after: `A=0, B=0, C=2, D=0`

## Consolidated report
- `scripts/migration/output/fw_stabilization_execution_report_post_stagebucket_20260227_124101.json`
- `scripts/migration/output/fw_stabilization_execution_report_post_stagebucket_20260227_124101.md`

## Go / No-go
- Decision: **FW not yet ready**.
- Rationale:
  1. Transfer path is fixed and exercised (`Workflow/Action > 0`), but mix-candidate actions remain `0` in this scope, so mix-event path remains unvalidated on positive cases.
  2. Residual board still has `C=2` (not expanded, but not closed).
  3. Marine continuation classification remains blocked until positive mix-candidate coverage is demonstrated or explicitly waived.

## Precise next FT inspection questions
1. Which FW cohorts in extract have destination-container occupancy with another batch at transfer timestamp (cross-batch co-location)?
2. Are there known FW stations with complete hall-stage mapping where these cross-batch co-location cases occur?
3. For audited examples, should destination co-location be represented as true mixing or as sequencing artifacts (no overlap)?

## Smallest deterministic next candidate
- Keep current transfer code unchanged.
- Build a **mix-positive candidate scope** from SubTransfers + container occupancy where:
  - `TransferAction` candidate exists
  - destination container has cross-batch overlap on transfer date
  - station has hall-stage mapping coverage
- Run minimal wiped rerun on that scope, then re-run backfill and verify:
  1. `candidate_mix_actions > 0`
  2. `batch_mix_event > 0`
  3. `batch_mix_event_component > 0`
  4. `allow_mixed=True` set for qualified actions
  5. `A=0`, no `C` expansion

## Files changed this session
- `scripts/migration/tools/pilot_migrate_component_transfers.py` (updated)
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-27_FW_TRANSFER_STAGE_BUCKET_IMPLEMENTATION_AND_RERUN.md` (new)

