# FW 1349 Same-Stage Superseded Destination Trace Fix

Date: 2026-03-24

## Batch

- Batch id: `1349`
- Batch number: `Stofnfiskur S-21 juni24 - Summar 2024`
- Component key: `36D7DE38-D6C9-4CB7-9FF7-64273124A605`

## Manual Finding

- AquaMind swimlane highlight showed `R1`-`R5` with no visible downstream fanout.
- `R6` appeared to capture broad downstream fanout by itself, masking missing traceability from the other `R` lanes.

## Classification

- Result: `REAL MIGRATION DEFECT`

This was not benign bridge residue. Transfer replay for `1349` was anchoring all six `R -> 5M` first-leg actions on short same-day relay assignments that had no downstream transfer actions attached, even though each `5M` container also had a longer-lived same-day companion assignment carrying the real downstream lineage.

## Concrete Pre-Fix Evidence

### First-leg destination bindings before rerun

- `R1 -> 36192 (5M 1)` with `population_count = 196663`, `assignment_date = 2024-08-30`, `departure_date = 2024-08-30`, downstream actions `0`
- `R2 -> 36193 (5M 2)` with `population_count = 216773`, downstream actions `0`
- `R3 -> 36194 (5M 3)` with `population_count = 220176`, downstream actions `0`
- `R4 -> 36195 (5M 4)` with `population_count = 0`, downstream actions `0`
- `R5 -> 36196 (5M 5)` with `population_count = 0`, downstream actions `0`
- `R6 -> 36197 (5M 6)` with `population_count = 0`, downstream actions `0`

### Same-container companion assignments with surviving lineage

- `36203 (5M 1)` population `229568`, downstream to `B08`, `A01`, `A03`
- `36204 (5M 2)` population `249678`, downstream to `A03`, `B08`, `A01`
- `36205 (5M 3)` population `253076`, downstream to `A05`, `B04`, `A03`, `A01`
- `36206 (5M 4)` population `240938`, downstream to `A01`, `A05`, `B04`
- `36208 (5M 5)` population `242027`, downstream to `A05`, `A01`, `B10`
- `36207 (5M 6)` population `252148`, downstream to `A05`, `B10`, `A01`

The defect class matches `1348`, but `1349` proves the bad relay destination rows are not limited to zero-suppressed populations. In this batch, the dead-end same-day relay rows for `5M 1` through `5M 3` still retained non-zero counts.

## Exact Cause

- `scripts/migration/tools/pilot_migrate_component.py` can leave short same-container same-stage relay rows in assignment history when FishTalk emits a same-day relay handoff into a longer-lived companion assignment in the same container.
- `scripts/migration/tools/pilot_migrate_component_transfers.py` was previously resolving `DestPop` through exact assignment identity only.
- That preserved the dead-end relay destination binding even when the same container/stage/day had a longer-lived companion assignment that carried the real downstream lineage.
- Result: stage-level semantics still passed, but GUI traceability from `R1`-`R6` broke because the first-leg action terminated on a dead-end relay row.

## Generalized Fix

- Updated `scripts/migration/tools/pilot_migrate_component_transfers.py`.
- `canonicalize_same_stage_superseded_assignment(...)` now promotes same-day superseded relay destinations to the best same-container same-stage companion assignment for that date, whether the dead-end relay row is zero-count or non-zero.
- Canonicalization is applied whenever transfer replay resolves a destination assignment, including:
  - direct reuse of `assignment_by_pop`
  - scoped destination-assignment external maps
  - fallback `Populations` external maps
  - synthetic destination resolution

This is a transfer-replay fix only. Assignment history remains intact for auditability; the change is that transfer actions now bind to the surviving companion assignment that actually carries downstream lineage.

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

- `workflows created=7`
- `workflows pruned=7`
- `actions created=262`
- `actions pruned=262`
- `canonicalized=66`
- `skipped=0`

## Post-Fix Verification

### First-leg destination bindings

- `R1 -> 36203 (5M 1)` instead of `36192`
- `R2 -> 36204 (5M 2)` instead of `36193`
- `R3 -> 36205 (5M 3)` instead of `36194`
- `R4 -> 36206 (5M 4)` instead of `36195`
- `R5 -> 36208 (5M 5)` instead of `36196`
- `R6 -> 36207 (5M 6)` instead of `36197`

### Immediate downstream fanout from corrected `5M` roots

- `R1` root now continues from `5M 1` to `B08`, `A01`, `A03`
- `R2` root now continues from `5M 2` to `A03`, `B08`, `A01`
- `R3` root now continues from `5M 3` to `A05`, `B04`, `A03`, `A01`
- `R4` root now continues from `5M 4` to `A01`, `A05`, `B04`
- `R5` root now continues from `5M 5` to `A05`, `A01`, `B10`
- `R6` root now continues from `5M 6` to `A05`, `B10`, `A01`

### Transitive descendant reachability after rerun

- `R1`: `6` descendant containers
- `R2`: `6` descendant containers
- `R3`: `42` descendant containers
- `R4`: `35` descendant containers
- `R5`: `37` descendant containers
- `R6`: `37` descendant containers

### Residual dead-end relay rows

- The superseded same-day relay assignments remain in assignment history for auditability:
  - `36192`, `36193`, `36194`, `36195`, `36196`, `36197`
- After rerun, none of those rows are used as source or destination assignments by transfer actions in batch `1349`.

## Current Status

- `1349` contained the same real transfer-traceability defect family as `1348`.
- The transfer migrator now handles this defect family for same-day same-container same-stage superseded relay destinations, regardless of whether the dead-end relay row retained a non-zero count.
- Database-side verification now matches the expected `R -> 5M -> downstream fanout` structure for all six `R` lanes.
- Follow-up GUI review on `2026-03-24` found an additional downstream bridge-continuity defect beyond the initial `R -> 5M` repair.
- See `fw_1349_dest_before_bridge_continuity_fix_2026-03-24.md` for the second targeted rerun and verification.
- GUI/manual confirmation is still required before marking this finding `PASS`.
