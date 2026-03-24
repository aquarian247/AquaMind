# FW 1348 Same-Stage Superseded Destination Trace Fix

Date: 2026-03-24

## Batch

- Batch id: `1348`
- Batch number: `Stofnfiskur S-21 feb24 - Vár 2024`
- Component key: `BC782146-C921-4AD1-8021-0E1ED2228D7C`

## Manual Finding

- AquaMind swimlane highlight from `R1`-`R4` appeared to stop at the `R -> 5M` step instead of continuing through the downstream `A*`, `B*`, `D*`, `C*`, and `E*` fanout seen in FishTalk.
- `R6` showed downstream movement, but the user reported it still looked incomplete from the GUI.

## Classification

- Result: `REAL MIGRATION DEFECT`

This was not benign bridge residue. The migrated transfer graph for `1348` was anchoring several first-leg `Egg&Alevin -> Fry` actions on zero-suppressed same-day `5M` destination assignments that had no downstream transfer actions attached.

## Concrete Pre-Fix Evidence

- `R1`..`R5` first-leg transfer actions were bound to these destination assignments:
  - `R1 -> 35810 (5M 1)` with `population_count = 0`, `assignment_date = 2024-05-23`, `departure_date = 2024-05-23`
  - `R2 -> 35811 (5M 2)` with `population_count = 0`
  - `R3 -> 35812 (5M 3)` with `population_count = 0`
  - `R4 -> 35813 (5M 4)` with `population_count = 0`
  - `R5 -> 35814 (5M 5)` with `population_count = 0`
- Those zero rows had no downstream transfer actions.
- The same containers also had longer-lived same-day companion assignments with the real merged totals and downstream fanout:
  - `35820 (5M 1)` population `238986`
  - `35821 (5M 2)` population `244096`
  - `35822 (5M 3)` population `239546`
  - `35823 (5M 4)` population `243322`
  - `35824 (5M 5)` population `244959`
- `ExternalIdMap` evidence showed the exact `DestPop` rows for `R1`..`R5` mapped to zero-baseline assignments:
  - `A05228E2-1F8C-4404-B894-C39A8A87F891 -> 35810` with `baseline_population_count = 0`
  - `12607D58-E064-4FFF-874C-152410C9B65C -> 35811` with `baseline_population_count = 0`
  - `6C99DC8C-F0AA-4C6C-92EC-B658B070FA1A -> 35812` with `baseline_population_count = 0`
  - `977405E0-512D-463C-91D7-C98E353A7B4A -> 35813` with `baseline_population_count = 0`
  - `B25C1375-A0D3-41C6-9790-C5816F114FB1 -> 35814` with `baseline_population_count = 0`
- The surviving companion `DestPop` rows in the same containers carried the real downstream lineage:
  - `3065261B-8BD1-4987-BEE7-B41D2DD43882 -> 35820`
  - `3AA04ED9-823F-4FDA-B1AD-743109754E3D -> 35821`
  - `80CE5745-1D05-451E-B43A-9A34C241A3BE -> 35823`
  - `476BF3BF-0C61-44B7-B26A-F6C22341D5CC -> 35824`

## Exact Cause

- `scripts/migration/tools/pilot_migrate_component.py` intentionally zero-suppresses short same-container same-stage superseded relay populations.
- `scripts/migration/tools/pilot_migrate_component_transfers.py` then resolved `DestPop` directly through:
  - cached `assignment_by_pop`, or
  - exact `Populations` `ExternalIdMap`
- That meant transfer replay preserved the exact zero-suppressed destination assignment binding even when the same container/stage had a same-day longer-lived companion assignment that actually carried the downstream lineage.
- Result: stage-level semantics still passed, but container-level traceability from `R1`..`R5` broke in the GUI because the first-leg actions terminated on dead-end relay rows.

## Narrow Fix

- Updated `scripts/migration/tools/pilot_migrate_component_transfers.py`.
- Added `canonicalize_same_stage_superseded_assignment(...)`.
- Replay now promotes a destination assignment only when all of the following are true:
  - same batch,
  - same container,
  - same lifecycle stage,
  - same assignment date as the transfer operation,
  - resolved destination row is zero-count and same-day closed,
  - a longer-lived companion assignment exists in that same container/stage/date.
- The exact `Populations` assignment map is left untouched; only transfer replay destination binding is canonicalized.
- The canonicalization is applied in both:
  - direct reuse of `assignment_by_pop`
  - fallback destination resolution paths

## Targeted Rerun

Command executed:

```bash
python scripts/migration/tools/pilot_migrate_component_transfers.py \
  --component-key BC782146-C921-4AD1-8021-0E1ED2228D7C \
  --report-dir scripts/migration/output/input_batch_migration/Stofnfiskur_S-21_feb24_1_2024 \
  --use-csv scripts/migration/data/extract \
  --use-subtransfers \
  --transfer-edge-scope source-in-scope \
  --workflow-grouping stage-bucket \
  --skip-synthetic-stage-transitions
```

Rerun result:

- `workflows created=7`
- `workflows pruned=7`
- `actions created=248`
- `actions pruned=248`
- `canonicalized=59`
- `skipped=0`

## Post-Fix Verification

### First-leg destination bindings

- `R1 -> 35820 (5M 1)` instead of `35810`
- `R2 -> 35821 (5M 2)` instead of `35811`
- `R3 -> 35822 (5M 3)` instead of `35812`
- `R4 -> 35823 (5M 4)` instead of `35813`
- `R5 -> 35824 (5M 5)` instead of `35814`
- `R6 -> 35815 (5M 6)` unchanged

### Immediate downstream fanout from the corrected `5M` roots

- `R1` root now continues from `5M 1` to `A05`, `B10`, `A01`
- `R2` root now continues from `5M 2` to `A05`, `A01`, `B10`
- `R3` root now continues from `5M 3` to `A01`, `A03`, `B11`
- `R4` root now continues from `5M 4` to `B11`, `A03`, `A01`
- `R5` root now continues from `5M 5` to `A03`, `B09`, `A01`
- `R6` root continues from `5M 6` to `B09`, `A05`, `A01`

### Transitive descendant reachability after rerun

- `R1`: `26` descendant containers
- `R2`: `26` descendant containers
- `R3`: `25` descendant containers
- `R4`: `25` descendant containers
- `R5`: `23` descendant containers
- `R6`: `42` descendant containers

### Residual zero rows

- The zero-suppressed relay assignments remain in assignment history for auditability:
  - `35810`, `35811`, `35812`, `35813`, `35814`
- After rerun, none of those rows are used as destination assignments by transfer actions in batch `1348`.

## Current Status

- `1348` contained a real migration traceability defect.
- The narrow transfer-replay fix has been applied and replayed in `migr_dev`.
- Database-side verification now matches the expected `R -> 5M -> downstream fanout` structure.
- GUI/manual confirmation completed on `2026-03-24`; the user confirmed the swimlane now looks correct from egg to fry.
- Result for this finding: `PASS`
