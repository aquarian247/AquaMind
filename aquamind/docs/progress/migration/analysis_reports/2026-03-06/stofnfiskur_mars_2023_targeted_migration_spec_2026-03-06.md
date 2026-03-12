# Stofnfiskur Mars 2023 Targeted Migration Spec

Created: `2026-03-06`

This spec converts the `Stofnfiskur Mars 2023` operation ledger into a migration decision package that can be used for a targeted FW->Sea apply.

## Decision

Use a split-lineage, operation-led migration for `Stofnfiskur Mars 2023`.

- Do not model this cohort as one FW batch continuing into one sea batch.
- Direct non-mixed sell-off should apply from the exact sale/input pairs recorded in the operation ledger.
- Mixed `G1` and `G3` sell-off should route through `Stofnfiskur Juni 2023` successor lineage, but the marine-side apply target should remain the canonical sea component, not a duplicate FW-side representation.
- FishTalk destination-side swimlane for `A06 Argir / 06` (Official ID `A-06;01088`) shows seven input actions on `2024-06-19`, including two distinct `35,926` inputs from `S24 Strond`.
- Same-day mortality entries of `15`, `10`, `13`, `10`, `15`, and `655` reconcile the post-input start count exactly: `205,660` input minus `718` mortality equals `204,942`.
- That makes both `35,926` ingress rows real source-truth events for container `06`, not an extract duplicate.

## Canonical apply groups

### 1. Direct Mars -> Vár 2024

- Apply component: `Vár 2024|1|2024`
- Target sites: `A18 Hov`, `A63 Árnafjørður`, `A06 Argir`
- Ready event ids: `D01, D02, D03, D04, D05, D06, D07, D08, D09, D10, D11, D12, D13, D14, D15, D16, D17, D18, D19, D20, D21, D22, D23, D24, D25, D26A, D26B, D27, D28, D29, D30, D31`
- Ready fish count: `1,611,040`

### 2. Direct Mars -> Summar 2024

- Apply component: `Summar 2024|1|2024`
- Target site: `A47 Gøtuvík`
- Ready event ids: `D32, D33, D34`
- Ready fish count: `145,111`

### 3. Mixed successor via Juni -> Summar 2024

- Successor lineage: `Stofnfiskur Juni 2023`
- Canonical marine apply component: `Summar 2024|1|2024`
- Target sites: `A25 Gøtuvík`, `A47 Gøtuvík`
- Ready event ids: `M01, M02, M03, M04, M05, M06, M07, M08`
- Ready fish count: `244,770`

## Blockers

- No unresolved manual blockers remain for this cohort.

## Representation rules

- `A25 Gøtuvík` `S09` and `S11` appear in both `Summar 2024|1|2024` and `Stofnfiskur Juni 2023|2|2023` lifecycle-member artifacts.
- Treat `Summar 2024|1|2024` as the canonical marine apply target.
- Treat `Stofnfiskur Juni 2023|2|2023` as duplicate lineage evidence, not as a second marine apply target.
- Keep the `M05` operation pair, but note that the current population-member artifact names it `N05 S24 SF JUL 24 (MAR/JUN 24)`. That is a naming anomaly to verify later, not a reason to discard the deterministic operation pair.

## Explicit rejections

- Reject the earlier provisional `Stofnfiskur Mars 2023 -> Vár 2023 / A71 Funningsfjørður` idea.
- Reject any migration plan that compresses `Stofnfiskur Mars 2023` into a single `<fw batch> -> <sea batch>` mapping.

## Operational basis

The deterministic anchors are:

- `InternalDelivery(SalesOperationID, InputOperationID)` for the sale-to-input pairing
- sales-side action metadata for site/ring/customer semantics
- exact `TargetSites + TargetContainers + InputStartTime` join into the input-stitching population-member artifacts

## Files

- Spec JSON: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_targeted_migration_spec_2026-03-06.json`
- Operation ledger CSV: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_operation_ledger_2026-03-06.csv`
- Manual swimlane evidence JSON: `aquamind/docs/progress/migration/analysis_reports/2026-03-06/stofnfiskur_mars_2023_manual_ft_swimlane_evidence_2026-03-06.json`
