# Semantic Migration Validation Report

- Component key: `B52612BD-F18B-48A4-BF21-12B5FC246803`
- Batch: `Bakkafrost S-21 jan 25` (id=464)
- Populations: 183
- Window: 2025-01-06 15:08:04 → 2026-02-16 12:49:52.673329

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 872 | 872 | 0.00 |
| Feeding kg | 26861.00 | 26861.00 | 0.00 |
| Mortality events | 1606 | 1459 | 147.00 |
| Mortality count | 451404 | 451404 | 0.00 |
| Mortality biomass kg | 0.00 | 477.91 | -477.91 |
| Culling events | 35 | 35 | 0.00 |
| Culling count | 196725 | 196725 | 0.00 |
| Culling biomass kg | 3805417.90 | 3805417.90 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
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

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 648129
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/3 bridge-aware (100.0%), 0/3 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 66 total, 65 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 91.
- Fishgroup classification: 98 temporary bridge fishgroups, 19 real stage-entry fishgroups, 98 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501093 | 0 | 1501093 | 1501093 | 1.0 | 1.0 | 2025-01-06 | 2025-01-08 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1389877 | 0 | 1389877 | 1389877 | 1.0 | 1.0 | 2025-04-02 | 2025-04-04 | 6 | 6 | 0 | 6 | 12 |
| Parr | 992557 | 0 | 1366172 | 5453302 | 5.49 | 3.99 | 2025-07-07 | 2025-07-09 | 5 | 5 | 0 | 89 | 147 |
| Smolt | 99754 | 764982 | 798168 | 1132303 | 11.35 | 1.42 | 2025-10-09 | 2025-10-11 | 1 | 1 | 2 | 15 | 17 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501093 | 1501093 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1501093 | 1501093 | 0 | 5 | 5 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 175165 | 175165 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 3) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0008`, `251.0009`, `251.0010`, `251.0011`, `251.0012`, `251.0013`, `251.0020`, `251.0021`, `251.0022`, `251.0026`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0014`, `251.0015`, `251.0016`, `251.0017`
- Bridge fishgroups excluded from stage-entry windows: `251.0077`, `251.0078`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 183 | 183 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 46

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 4 | Hatchery:4 | S21 Viðareiði:4 |
| SourcePopBefore -> SourcePopAfter | 42 | Hatchery:42 | S21 Viðareiði:42 |
| DestPopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 46 | 0 | Hatchery:46 | S21 Viðareiði:46 | Unknown:46 |
| Reachable outside descendants | 84 | 0 | Hatchery:84 | S21 Viðareiði:84 | Unknown:84 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 7; latest holder in selected component: 7; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C12 | EB1EF487-8816-45EF-95FE-B5E69EE0F520 | `9104535D-ED59-414B-AB2A-91230BC4BBFA` | `9104535D-ED59-414B-AB2A-91230BC4BBFA` | yes | 99754 | 13813.9 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D1 | 79FC9DFE-ABC2-4E15-AEB2-184BAE21ACB4 | `E2CCF882-96DC-4BAE-B041-038211291B62` | `E2CCF882-96DC-4BAE-B041-038211291B62` | yes | 100419 | 14194.1 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D2 | 8C7617F2-BD10-462A-9EFC-714049DD6F33 | `A63B3748-9946-4D91-B63A-06CE5CC5A8F6` | `A63B3748-9946-4D91-B63A-06CE5CC5A8F6` | yes | 80659 | 5579.91 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D3 | EABFFD0C-D735-4A03-8FAB-D0A5B9F263E7 | `8CC87AFE-AC81-499C-84D6-B0D7EF4AE869` | `8CC87AFE-AC81-499C-84D6-B0D7EF4AE869` | yes | 102842 | 11837.2 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D4 | 4A2D7673-1B25-4A91-8262-2B9DF397D763 | `86E8B32B-1404-400F-A08C-613B1056F6B4` | `86E8B32B-1404-400F-A08C-613B1056F6B4` | yes | 99222 | 8393.81 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D5 | A1D1A57B-1269-408B-9A85-F9F886025A69 | `A8B2808F-8D88-432D-8305-395054A7181E` | `A8B2808F-8D88-432D-8305-395054A7181E` | yes | 103716 | 13885.1 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D6 | 931106E8-6C21-4513-8DDA-3ACAF801F76D | `4E8EAE3C-FA4C-4AE9-9EE6-5C17083581D7` | `4E8EAE3C-FA4C-4AE9-9EE6-5C17083581D7` | yes | 99386 | 11920.9 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (advisory)