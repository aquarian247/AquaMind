# FW Wave 1 Transfer Rerun Result

Date: 2026-03-06

## Scope

Wave 1 reran `pilot_migrate_component_transfers.py` only for the four FW canaries identified in the hardening queue:

- `1344` `Stofnfiskur Des 23 - Vár 2024`
- `1348` `Stofnfiskur S-21 feb24 - Vár 2024`
- `1349` `Stofnfiskur S-21 juni24 - Summar 2024`
- `1352` `Stofnfiskur desembur 2023 - Vár 2024`

## Why transfer-only

This wave targeted one specific defect class:

- old FW runs had replayed transfer workflows with `internal-only` applied before root-source SubTransfers expansion,
- that dropped sibling split legs on transfer-rich FW cohorts,
- the fix is isolated to `pilot_migrate_component_transfers.py`.

For this reason, Wave 1 did **not** rerun:

- environmental readings,
- lice counts,
- feeding, mortality, treatment, or other event pilots,
- full `pilot_migrate_input_batch.py` end-to-end pipelines.

That was intentional. Replaying the rest of the pipeline would not improve this defect class and would only widen the write surface.

FW-specific note:

- `pilot_migrate_component_lice.py` is not useful for these FW batches. Freshwater cohorts naturally have no sea-lice sample history.

## Commands executed

Template used on all four canaries:

```bash
PYTHONPATH=/Users/aquarian247/Projects/AquaMind \
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key <component_key> \
  --report-dir <input_batch_migration_dir> \
  --use-subtransfers \
  --use-csv /Users/aquarian247/Projects/AquaMind/scripts/migration/data/extract \
  --workflow-grouping stage-bucket \
  --transfer-edge-scope internal-only \
  --skip-synthetic-stage-transitions
```

Reason for keeping `internal-only` on Wave 1:

- these are repairs on already-migrated FW-only batches,
- the goal was to restore missing in-scope split legs without widening batch scope to external destinations.

## Result summary

| Batch ID | Batch Number | Replay outcome | Post-rerun DB state |
|---|---|---|---|
| `1344` | `Stofnfiskur Des 23 - Vár 2024` | `workflows created=0, updated=7; actions created=0, updated=121, skipped=10` | `7` transfer workflows, `121` transfer actions |
| `1348` | `Stofnfiskur S-21 feb24 - Vár 2024` | `workflows created=1, updated=6; actions created=127, updated=109, skipped=0` | `7` transfer workflows, `236` transfer actions |
| `1349` | `Stofnfiskur S-21 juni24 - Summar 2024` | `workflows created=1, updated=6; actions created=112, updated=132, skipped=0` | `7` transfer workflows, `244` transfer actions |
| `1352` | `Stofnfiskur desembur 2023 - Vár 2024` | `workflows created=1, updated=7; actions created=154, updated=128, skipped=12` | `8` transfer workflows, `282` transfer actions |

Notes:

- `1348` action creation count (`127`) exactly matched the hardening-queue missing split-leg count.
- `1349` action creation count (`112`) exactly matched the hardening-queue missing split-leg count.
- `1344` had already been transfer-rerun once during the S03 investigation, so this Wave 1 rerun was mostly updates, not new creates.
- `1352` remains larger and noisier; `12` edges were still skipped due to `zero_estimated_transfer`.

## Log files

- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_wave1_1344_transfer_rerun.log`
- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_wave1_1348_transfer_rerun.log`
- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_wave1_1349_transfer_rerun.log`
- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/fw_wave1_1352_transfer_rerun.log`

## Interpretation

- Wave 1 succeeded mechanically.
- The transfer split-loss patch is now exercised on both the known S03 canary (`1344`) and the repaired S21/S24 canaries.
- This does **not** prove full FW correctness yet.
- It does prove that a full-pipeline rerun is not required for this defect class.

## Next move

- Validate `1344` and `1352` in AquaMind first, because they are the most informative canaries:
  - `1344` is the manually verified S03 split case,
  - `1352` is the repaired S24 case with the largest transfer surface.
- If those look clean, proceed to the `17` mapped-scope transfer reruns from `fw_hardening_queue_2026-03-06.md`.
- Keep `1116`, `1133`, `1329`, and `1330` out of the bulk rerun path until their FW reconstruction strategy is defined.
