# FW 1344 Bridge Baseline Rerun And Self-Loop Guard

Date: 2026-03-24

## Batch

- Batch id: `1344`
- Batch number: `Stofnfiskur Des 23 - Vár 2024`
- Component key: `7311DFA1-6535-4D97-B708-BD4ED79AB8F9`

## Why This Rerun Was Done

- `1349` exposed two real replay defects that were fixed in the transfer migrator:
  - same-day superseded destination assignments binding first-leg actions to dead-end rows
  - dropped `DestPopBefore -> DestPopAfter` bridge continuity across staged/0-day successor populations
- `1344` was rerun as the next canary to validate whether the new replay baseline generalized cleanly.

## Defect Found During Rerun

- Result: `REAL MIGRATION DEFECT`

The first `1344` replay with the new bridge-preserving baseline exposed an over-canonicalization regression:

- same-day destination canonicalization was broad enough to collapse legitimate same-container same-stage parallel split siblings onto the largest same-day assignment even when there was no longer-lived companion
- bridge and folded-tail edges could then resolve to the exact same assignment as their source, producing assignment-to-itself transfer actions

This was a real replay defect. Transfer actions from an assignment back to the same assignment are not valid migration output.

## Concrete First-Rerun Evidence

Initial replay result:

- `Loaded 131 SubTransfers rows from CSV; expanded to 339 scoped edges`
- `workflows created=9`
- `actions created=328`
- `canonicalized=38`
- `skipped=11`

Observed regression after that first rerun:

- `28` source assignments had at least one transfer action where `source_assignment_id == dest_assignment_id`
- Example:
  - action `18302`: assignment `35397 (1806)` -> `35397 (1806)`, moved `100000`
  - action `18303`: assignment `35397 (1806)` -> `35397 (1806)`, moved `45149`
- Root cause cluster for `1806` on `2025-04-30`:
  - source assignment `35397` mapped population `4769809E-...`
  - legitimate sibling destination populations `0590D9EE-...` and `2B232314-...` mapped to assignments `35398` and `35399`
  - broad same-day canonicalization incorrectly promoted those destinations back onto `35397`

## Narrow Fix

- Updated `scripts/migration/tools/pilot_migrate_component_transfers.py`.

Two narrow protections were added:

- same-day destination canonicalization now promotes only to a genuinely longer-lived same-container same-stage companion assignment
- resolved edges are skipped when `source_assignment.id == dest_assignment.id`

This preserves the `1348/1349` dead-end relay repair, keeps the `1349` bridge continuity fix, and avoids manufacturing no-op self-loop actions in batches like `1344` that contain legitimate same-day parallel siblings.

## Corrected Targeted Rerun

Command executed:

```bash
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key 7311DFA1-6535-4D97-B708-BD4ED79AB8F9 \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_Des_23_6_2023 \
  --use-csv scripts/migration/data/extract \
  --use-subtransfers \
  --transfer-edge-scope source-in-scope \
  --workflow-grouping stage-bucket \
  --skip-synthetic-stage-transitions
```

Corrected rerun result:

- `Loaded 131 SubTransfers rows from CSV; expanded to 339 scoped edges`
- `workflows created=8`
- `workflows pruned=9`
- `actions created=297`
- `actions pruned=328`
- `canonicalized=24`
- `skipped=42`
- skipped reasons:
  - `self_loop_assignment_edge=31`
  - `zero_estimated_transfer=11`

## Post-Fix Verification

- Assignment-to-itself transfer actions remaining in batch `1344`: `0`
- The bridge-preserving expansion remains active; only the bad self-loop cases were filtered.
- Same-day incoming/no-outgoing rows with same-container same-stage same-date siblings remain present (`17` rows), but these are not automatically defects. They now require GUI review and context-sensitive interpretation rather than being artifacts of the replay regression.

## Current Status

- `1344` surfaced a real replay regression while validating the new bridge-aware baseline.
- That regression has been fixed in code and replayed narrowly for `1344`.
- GUI/manual confirmation completed on `2026-03-24`; the user confirmed the corrected swimlane looks very good and final post-smolt counts match FishTalk.
- Result for this finding: `PASS`
