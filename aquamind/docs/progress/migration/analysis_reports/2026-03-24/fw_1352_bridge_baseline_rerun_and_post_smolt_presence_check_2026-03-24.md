# FW 1352 Bridge Baseline Rerun And Post-Smolt Presence Check

Date: 2026-03-24

## Batch

- Batch id: `1352`
- Batch number: `Stofnfiskur desembur 2023 - Vár 2024`
- Component key: `EF6EC682-7532-43DF-8D6B-1441ABFF504E`

## Why This Rerun Was Done

- `1348` and `1349` exposed two real replay defects that were fixed in the transfer migrator:
  - same-day superseded destination assignments binding actions onto dead-end rows
  - dropped `DestPopBefore -> DestPopAfter` bridge continuity across staged/0-day successor populations
- `1352` was rerun as the last FW canary to validate the corrected replay baseline before any broader FW decision.

## Targeted Rerun

Command executed:

```bash
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key EF6EC682-7532-43DF-8D6B-1441ABFF504E \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_desembur_2023_4_2023 \
  --use-csv scripts/migration/data/extract \
  --use-subtransfers \
  --transfer-edge-scope source-in-scope \
  --workflow-grouping stage-bucket \
  --skip-synthetic-stage-transitions
```

Rerun result:

- `Loaded 294 SubTransfers rows from CSV; expanded to 956 scoped edges`
- `workflows created=8`
- `workflows pruned=7`
- `actions created=900`
- `actions pruned=756`
- `canonicalized=41`
- `skipped=56`
- skipped reasons:
  - `self_loop_assignment_edge=18`
  - `zero_estimated_transfer=38`

## Post-Rerun Structural Verification

- Assignment-to-itself transfer actions remaining in batch `1352`: `0`
- Transfer actions still targeting same-day superseded destination assignments: `0`
- Same-day incoming/no-outgoing sibling rows remaining: `40`

The known `1348/1349` replay defect family is not present after the corrected `1352` rerun.

## Manual Observation Investigated

- Observation: the AquaMind GUI appeared to end around Hall `F`, making it look like Hall `J` and later post-smolt activity were not migrated.
- Result: `NOT A MIGRATION DEFECT`

This observation is contradicted by both the source extract and the migrated replay data.

## Concrete Evidence That Post-Smolt Was Migrated

Source extract evidence:

- The component report extract includes Hall `J` population rows, for example:
  - `J1` starting `2024-11-20 13:16:49`
  - `J2` starting `2024-11-20 13:16:49`
  - `J3` starting `2024-11-27 11:53:05`
  - `J4` starting `2024-11-27 11:53:05`

Migrated `migr_dev` evidence:

- Batch `1352` now has `118` `Post-Smolt` assignments across:
  - `G2`, `G3`
  - `H1`, `H2`, `H3`, `H4`
  - `I1`, `I2`, `I3`, `I4`
  - `J1`, `J2`, `J3`, `J4`
- Incoming transfer actions into `Post-Smolt` assignments: `148`
- Incoming transfer actions specifically into Hall `J`: `36`
- Outgoing transfer actions from Hall `J`: `26`

Concrete migrated Hall `J` arrivals on `2024-11-20` include:

- action `18855`: `F03 -> J1`, moved `74811`
- action `18856`: `F03 -> J2`, moved `81192`
- action `18857`: `E05 -> J2`, moved `65247`
- action `18858`: `E05 -> J1`, moved `59469`
- action `18859`: `E06 -> J4`, moved `63193`
- action `18861`: `E06 -> J3`, moved `70124`
- action `18862`: `F02 -> J3`, moved `62788`
- action `18863`: `F02 -> J4`, moved `55225`

Hall `J` also continues through later post-smolt bridge/successor actions, so the lifecycle does not terminate at the first Hall `J` arrival.

## Current Status

- GUI/manual review completed on `2026-03-24`; the user confirmed `1352` otherwise looks very good.
- The “ends at Hall `F`” observation is not supported by the migration data. The migrated batch includes Hall `J` and later post-smolt activity.
- From the migration replay standpoint, `1352` is `PASS`.
- If Hall `J` still does not render in the AquaMind GUI, the next investigation belongs to the history API / traceability UI layer rather than the FW transfer migrator.
