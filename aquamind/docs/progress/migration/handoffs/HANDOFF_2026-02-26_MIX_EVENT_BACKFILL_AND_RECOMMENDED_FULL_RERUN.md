# HANDOFF - 2026-02-26 - Mix Event Backfill + Recommended Full Rerun

## Scope

Implement migration-path support for container-scoped mix lineage models, run a clean wiped-db rerun, and verify regression tests.

## Code Changes

1. Added new mix-lineage backfill migration tool:
   - `scripts/migration/tools/pilot_backfill_transfer_mix_events.py`
   - Function:
     - Scans completed `TransferAction` rows.
     - Detects destination container/date cross-batch co-location.
     - Materializes:
       - `BatchMixEvent`
       - `BatchMixEventComponent`
       - `BatchComposition` fallback rows
     - Sets `TransferAction.allow_mixed=True` for qualified actions.
     - Optionally rewrites destination assignment lineage to mixed-assignment continuity (enabled by default; can be disabled via `--skip-assignment-rewrite`).
   - Notes:
     - Action-scoped idempotency via deterministic mixed batch number `MIX-FTA-<action_id>`.
     - Dry-run supported.

2. Updated migration DB wipe script for new mix tables:
   - `scripts/migration/clear_migration_db.py`
   - Added truncation targets:
     - `batch_batchmixevent`
     - `batch_batchmixeventcomponent`
     - `batch_historicalbatchmixevent`
     - `batch_historicalbatchmixeventcomponent`

3. Fixed full-rerun blocker in component migration:
   - `scripts/migration/tools/pilot_migrate_component.py`
   - Issue:
     - Marine `A*` site-code containers could enter freshwater container path and get skipped, causing `KeyError` during assignment materialization.
   - Fix:
     - Reclassify container bucket to `sea` for `A*` site codes before container creation path selection.

## Execution Runbook Performed

1. Wiped migration DB:
   - `python scripts/migration/clear_migration_db.py`
2. Seeded master data:
   - `python scripts/migration/setup_master_data.py`
   - `python scripts/migration/tools/pilot_migrate_health_master_data.py --use-csv scripts/migration/data/extract`
3. Rebuilt input stitching index:
   - `python scripts/migration/tools/input_based_stitching_report.py --output-dir scripts/migration/output/input_stitching`
4. Ran end-to-end migration loop (recommended scope):
   - Source list: `scripts/migration/output/input_stitching/recommended_batches.csv`
   - Per-batch command:
     - `python scripts/migration/tools/pilot_migrate_input_batch.py --batch-key <key> --use-csv scripts/migration/data/extract --migration-profile fw_default --skip-environmental --skip-feed-inventory`
5. Ran mix backfill:
   - `python scripts/migration/tools/pilot_backfill_transfer_mix_events.py`
6. Ran regression checks:
   - `python manage.py test apps.batch.tests.test_workflow --settings=aquamind.settings_ci`
   - `python manage.py test apps.inventory.tests.test_fcr_service --settings=aquamind.settings_ci`
   - `python manage.py test apps.batch.tests apps.inventory.tests --settings=aquamind.settings_ci`

## Results

- Recommended-scope migration loop completed successfully for all 5 recommended batch keys.
- Post-run counts:
  - `batch_batch`: 5
  - `batch_batchcontainerassignment`: 159
  - `batch_batchtransferworkflow`: 0
  - `batch_transferaction`: 0
  - `batch_batchmixevent`: 0
  - `batch_batchmixeventcomponent`: 0
- Mix-backfill scan observed no completed transfer actions in this scope; therefore no mix events/components were created in this run.
- Regression tests passed:
  - `Ran 7 tests ... OK`
  - `Ran 35 tests ... OK`
  - `Ran 487 tests ... OK`

## Artifacts

- `scripts/migration/output/full_rerun_recommended_mix_backfill_20260226_155123.json`
- `scripts/migration/output/full_rerun_recommended_mix_backfill_20260226_155123.md`

## Exact Files Changed

- `scripts/migration/tools/pilot_backfill_transfer_mix_events.py` (new)
- `scripts/migration/clear_migration_db.py`
- `scripts/migration/tools/pilot_migrate_component.py`
- `aquamind/docs/progress/migration/handoffs/HANDOFF_2026-02-26_MIX_EVENT_BACKFILL_AND_RECOMMENDED_FULL_RERUN.md` (new)

## Outstanding Follow-up

This run validates script integrity and regression stability, but does not exercise mix-event backfill behavior because no transfer actions were materialized in the recommended scope.

To fully validate mix semantics under historical transfers, run a broader migration scope that includes batches/components with non-zero SubTransfer edges, then re-run:

- `python scripts/migration/tools/pilot_backfill_transfer_mix_events.py`

and compare:

- mix candidate count vs. created `BatchMixEvent` count
- mix-event component percentages vs. destination co-location snapshots at action date
