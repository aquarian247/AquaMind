# Semantic Migration Validation Report

- Component key: `829BEAC3-83F0-47F7-AFC3-140AE3A234ED`
- Batch: `Bakkafrost S-21 okt 25` (id=472)
- Populations: 13
- Window: 2025-10-28 13:17:54 → 2026-02-16 15:31:17.099730

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 15 | 15 | 0.00 |
| Mortality count | 4068 | 4068 | 0.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 0 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 4068
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 4 total, 4 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 5.
- Fishgroup classification: 4 temporary bridge fishgroups, 9 real stage-entry fishgroups, 4 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 999995 | 0 | 999995 | 999995 | 1.0 | 1.0 | 2025-10-28 | 2025-10-30 | 5 | 5 | 0 | 5 | 5 |
| Fry | 892811 | 892811 | 892811 | 892811 | 1.0 | 1.0 | 2026-01-21 | 2026-01-23 | 4 | 4 | 0 | 4 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 999995 | 999995 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 5) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `255.0007`, `255.0008`, `255.0009`, `255.0010`
- Real stage-entry fishgroup examples: `255.0001`, `255.0002`, `255.0003`, `255.0004`, `255.0005`, `255.0006`, `255.0011`, `255.0012`, `255.0013`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 13 | 13 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 1

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | S21 Viðareiði:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 1 | 0 | Hatchery:1 | S21 Viðareiði:1 | Unknown:1 |
| Reachable outside descendants | 3 | 0 | Hatchery:3 | S21 Viðareiði:3 | Unknown:3 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 4; latest holder in selected component: 4; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 5M 1 | 6D03C708-F022-439C-8066-EAAE53638A17 | `A1E42C83-3A66-4F92-9694-4BC6AAA14E7F` | `A1E42C83-3A66-4F92-9694-4BC6AAA14E7F` | yes | 202650 | 40.53 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| 5M 2 | 9AA02FBA-608A-48BB-9083-C0F496AA3382 | `3887CDC4-88F3-4796-BDAC-23EEC33A5ACE` | `3887CDC4-88F3-4796-BDAC-23EEC33A5ACE` | yes | 234095 | 46.82 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| 5M 3 | 058A71B2-26EC-441F-99F9-D4B1E4FC5A1E | `D1456A8C-12A5-4162-AFBA-0D24C22F99F0` | `D1456A8C-12A5-4162-AFBA-0D24C22F99F0` | yes | 241469 | 48.29 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| 5M 4 | A3F1B6F4-B818-4034-A8AA-CA527AB749E2 | `2E77E978-D81C-41E7-8290-9F47A14AB08F` | `2E77E978-D81C-41E7-8290-9F47A14AB08F` | yes | 214597 | 42.92 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)