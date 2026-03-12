# Stofnfiskur Mars 2023 Operation Ledger

Created: `2026-03-06`

This report converts the manual FishTalk swimlane observations for `Stofnfiskur Mars 2023` into an operation-led ledger anchored on the latest readonly evidence artifacts.

## Source artifacts

- Manual swimlane evidence: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_manual_ft_swimlane_evidence_2026-03-06.json`
- Readonly sales linkage scoring: `scripts/migration/output/fwsea_readonly_candidate_package_20260305_103924/fwsea_sales_linkage_scoring_20260305_readonly.csv`
- Readonly sales directional parity: `scripts/migration/output/fwsea_readonly_candidate_package_20260305_103924/fwsea_sales_directional_parity_20260305_readonly.csv`
- Input stitching population members: `scripts/migration/output/input_stitching/full_lifecycle_population_members_*.csv`

## Join method

For each manual swimlane sell-off event:

1. Match the readonly sales row on:
   - `SourceSite = S24 Strond`
   - source container
   - sale date
   - fish count
   - destination site name
2. Resolve the paired marine-side input via `InternalDelivery` using the existing readonly sales linkage/parity extracts:
   - `SalesOperationID`
   - `InputOperationID`
   - `InputStartTime`
   - `TargetContainers`
3. Resolve the destination population representation by exact match on:
   - `org_unit_name = TargetSites`
   - `container_name = TargetContainers`
   - `start_time = InputStartTime`

The flat ledger is persisted in:

- `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_operation_ledger_2026-03-06.csv`

## Findings

- Manual swimlane events processed: `43`
- Manual events with at least one operation match: `43/43`
- Manual events with a unique operation match: `43/43`
- Residual operation ambiguity: `0/43`
- Flat ledger rows written: `48`
  - The row count exceeds `43` because some manual events map to more than one population-member representation.

## Destination split

- Direct non-mixed lineage:
  - `A18 Hov`: `6` events, `581,702` fish
  - `A63 Árnafjørður`: `14` events, `565,597` fish
  - `A06 Argir`: `12` events, `463,741` fish
  - `A47 Gøtuvík`: `3` events, `145,111` fish
- Mixed successor lineage via `Stofnfiskur Juni 2023`:
  - `A25 Gøtuvík`: `6` events, `195,332` fish
  - `A47 Gøtuvík`: `2` events, `49,438` fish

## Interpretation

- The local evidence supports a split-lineage model for `Stofnfiskur Mars 2023`.
- Some fish move directly from `Stofnfiskur Mars 2023` into marine-side inputs.
- Some fish are first mixed into `Stofnfiskur Juni 2023` and then sold into marine-side inputs under the successor identity.
- This cohort should not be forced into a single `<fw batch> -> <sea batch>` mapping.
- FishTalk destination-side swimlane evidence for `A06 Argir / 06` (Official ID `A-06;01088`) shows seven input actions on `2024-06-19`, including two distinct `35,926` inputs from `S24 Strond`.
- Same-day mortality entries of `15`, `10`, `13`, `10`, `15`, and `655` reconcile the post-input start count exactly: `205,660` input minus `718` mortality equals `204,942`.
- That makes the two `35,926` transfer/input pairs internally consistent source truth for container `06`, even though the input-start times in the extract are oddly spaced.
- The earlier provisional `Stofnfiskur Mars 2023 -> Vár 2023 / A71 Funningsfjørður` candidate is not supported by the manual swimlane evidence captured so far.

## Important caveats

- `A25 Gøtuvík` `S09` and `S11` inputs appear twice in the current lifecycle population-member artifacts:
  - once under `Stofnfiskur Juni 2023|2|2023`
  - once under `Summar 2024|1|2024`
- These look like duplicate lifecycle representations of the same marine-side inputs, not separate destination operations. The CSV keeps both representations visible instead of collapsing them.
- One `A47 Gøtuvík` row (`2024-07-09 16:41:01`) is currently named `N05 S24 SF JUL 24 (MAR/JUN 24)` in the population-members artifact. That naming should be treated as a representation anomaly pending source validation.

## Next use

This ledger is the right basis for a targeted migration rule for `Stofnfiskur Mars 2023`:

- direct marine continuations should be migrated from the exact sale/input pairs in the direct lineage rows
- mixed `G1` and `G3` continuations should be routed through `Stofnfiskur Juni 2023` successor lineage rather than treated as direct `Mars -> sea` mappings
- `A06 / 06` should be treated as a real seven-input marine ingress sequence, not as a duplicated extract artifact
