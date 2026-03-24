# FW 1349 Dest-Before Bridge Continuity Fix

Date: 2026-03-24

## Batch

- Batch id: `1349`
- Batch number: `Stofnfiskur S-21 juni24 - Summar 2024`
- Component key: `36D7DE38-D6C9-4CB7-9FF7-64273124A605`

## Manual Finding

- After the initial `R -> 5M` destination-binding repair, the user confirmed egg-to-fry looked correct.
- A deeper traceability defect remained from `5M 1` onward:
  - `5M 1 -> A01` and `5M 1 -> A03` appeared only as short-lived arrivals in AquaMind
  - later expected fanout from those lanes was missing from the GUI trace
  - FishTalk shows those lanes continuing through staged/0-day successor populations and then redistributing to containers such as `B01`, `B02`, `A03`, and `A05`

## Classification

- Result: `REAL MIGRATION DEFECT`

This was not benign residue. FishTalk encodes explicit destination-lane continuity across staged/0-day successor populations, but transfer replay was dropping those bridge edges and keeping only root-source terminal edges. That preserved direct arrivals while disconnecting later downstream fanout for earlier contributors.

## Concrete Pre-Fix Evidence

### Migrated graph symptom in `migr_dev`

- `5M 1` assignment `36203` correctly transferred to:
  - `A01` assignment `36217`
  - `A03` assignment `36216`
  - `B08` assignment `36218`
- But the later outgoing actions were attached to successor assignments instead:
  - `A03` successor `36225` carried the `2025-01-29` fanout to `B13`, `B02`, `B09`
  - `A01` successors `36228` and `36239` carried the later continuation, including the `2025-02-07` fanout to `A03`, `A05`, `B13`
- Before this fix, `5M 1` only reached `6` descendant containers in the replayed action graph because the bridge between the short-lived arrivals and their successor assignments was missing.

### FishTalk source evidence

FishTalk explicitly carries the destination-lane lineage forward in `SubTransfers` / `transfer_edges`:

- Operation `3BEFCB5C-568F-4498-9C8E-5AC520F97DD6` includes:
  - `8627665F-3B66-4DD1-B369-12055769C3B6 -> 6F68F79C-5A3E-43D7-8E85-7BBBC95EE8FA`
  - `EAB26485-5528-4BDB-9315-7B2259E29919 -> CE3078A5-78AD-43C0-92D3-CB5A658BED40`
- Operation `B24A4304-7900-49C5-A7E5-27FC21459BCF` includes:
  - `CE3078A5-78AD-43C0-92D3-CB5A658BED40 -> 699DD9C5-2451-4EB2-9377-19D04C927E82`
- Operation `D8A4C71F-F7FA-427C-BA0E-29B42A78C035` includes:
  - `A3E6C48C-A787-43EC-B711-0D80B105F462 -> 93D05AAA-1A45-4FF1-ACB3-95191C086952`

Those are not speculative merges. They are explicit bridge edges in the FishTalk extract and should appear in replayed lineage.

## Exact Cause

- `scripts/migration/tools/pilot_migrate_component_transfers.py` expands `SubTransfers` into root-source conservation edges via `expand_subtransfer_rows_for_source_scope(...)`.
- That expansion preserved terminal root-source edges but dropped explicit `DestPopBefore -> DestPopAfter` bridge continuity edges from the same operation.
- As a result:
  - direct arrivals such as `5M 1 -> A03` were replayed
  - but the successor bridge `A03(old) -> A03(successor)` was missing
  - later fanout from the successor lane stayed disconnected from the earlier contributor in AquaMind

## Narrow Fix

- Updated `scripts/migration/tools/pilot_migrate_component_transfers.py`.
- `expand_subtransfer_rows_for_source_scope(...)` now preserves explicit `DestPopBefore -> DestPopAfter` bridge edges alongside the existing root-source terminal edges.
- Bridge edges are emitted only when:
  - `DestPopBefore` and `DestPopAfter` are both in-scope populations for the component
  - they are distinct populations
- These bridge edges are recorded as full-share continuity (`1.0`) because FishTalk re-materializes the destination lane as a successor population and the prior destination population fully rolls into that successor.

## Targeted Rerun

Command executed:

```bash
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key 36D7DE38-D6C9-4CB7-9FF7-64273124A605 \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_S-21_juni24_2_2024 \
  --use-csv scripts/migration/data/extract \
  --use-subtransfers \
  --transfer-edge-scope source-in-scope \
  --workflow-grouping stage-bucket \
  --skip-synthetic-stage-transitions
```

Rerun result:

- `Loaded 244 SubTransfers rows from CSV; expanded to 379 scoped edges`
- `workflows created=8`
- `workflows pruned=7`
- `actions created=375`
- `actions pruned=262`
- `canonicalized=68`
- `skipped=4`
- skipped reason: `zero_estimated_transfer=4`

## Post-Fix Verification

### Bridge edges now materialized in AquaMind

The previously missing bridge actions now exist in `migr_dev`, for example:

- `36216 (A03 2024-12-09) -> 36225 (A03 2024-12-10)` moved `137009`
- `36217 (A01 2024-12-09) -> 36228 (A01 2024-12-10)` moved `74401`
- `36228 (A01 2024-12-10) -> 36239 (A01 2024-12-11)` moved `132124`
- `36239 (A01 2024-12-11) -> 36255 (A03 2025-02-07)` moved `82856`
- `36239 (A01 2024-12-11) -> 36256 (A05 2025-02-07)` moved `78717`
- `36248 (B13 2025-01-29) -> 36251 (B01 2025-01-29)` moved `83463`

### `5M 1` lineage now reaches the expected later redistributions

Verified descendant paths from `5M 1` assignment `36203` now include:

- `5M 1 -> A03 -> A03(successor) -> B02`
  - assignment path: `36203 -> 36216 -> 36225 -> 36250`
- `5M 1 -> A03 -> A03(successor) -> B13 -> B01`
  - assignment path: `36203 -> 36216 -> 36225 -> 36248 -> 36251`
- `5M 1 -> A01 -> A01(successor) -> A01(successor) -> A03`
  - assignment path: `36203 -> 36217 -> 36228 -> 36239 -> 36255`
- `5M 1 -> A01 -> A01(successor) -> A01(successor) -> A05`
  - assignment path: `36203 -> 36217 -> 36228 -> 36239 -> 36256`

### Reachability improvement

- Before bridge fix: `5M 1` reached `6` descendant containers
- After bridge fix: `5M 1` reaches `43` descendant containers

## Current Status

- `1349` contained a second real transfer-traceability defect after the initial `R -> 5M` repair.
- The replay now preserves explicit FishTalk destination-lane bridge continuity across staged/0-day successor populations.
- Database-side verification now matches the expected `5M 1 -> A01/A03 -> later Parr redistributions` structure.
- GUI/manual confirmation is still required before marking `1349` `PASS`.
