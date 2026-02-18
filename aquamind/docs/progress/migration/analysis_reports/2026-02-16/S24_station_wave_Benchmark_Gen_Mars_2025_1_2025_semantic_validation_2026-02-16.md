# Semantic Migration Validation Report

- Component key: `CE636015-595A-44BD-AB37-03B4018FBA4A`
- Batch: `Benchmark Gen. Mars 2025` (id=479)
- Populations: 252
- Window: 2025-03-12 12:20:55 → 2026-02-16 16:20:42.378542

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1962 | 1962 | 0.00 |
| Feeding kg | 89461.27 | 89461.27 | -0.00 |
| Mortality events | 2759 | 2715 | 44.00 |
| Mortality count | 906275 | 906275 | 0.00 |
| Mortality biomass kg | 0.00 | 587.96 | -587.96 |
| Culling events | 17 | 17 | 0.00 |
| Culling count | 73532 | 73532 | 0.00 |
| Culling biomass kg | 1478216.00 | 1478216.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 16 | 16 | 0.00 |
| Growth samples | 210 | 210 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 979807
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 67 total, 67 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 80.
- Fishgroup classification: 137 temporary bridge fishgroups, 55 real stage-entry fishgroups, 137 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500200 | 0 | 3500200 | 3500200 | 1.0 | 1.0 | 2025-03-12 | 2025-03-14 | 39 | 39 | 0 | 39 | 39 |
| Fry | 82902 | 0 | 5590607 | 6581543 | 79.39 | 1.18 | 2025-05-30 | 2025-06-01 | 1 | 1 | 0 | 37 | 48 |
| Parr | 2794369 | 0 | 4003092 | 8170410 | 2.92 | 2.04 | 2025-08-25 | 2025-08-27 | 11 | 11 | 13 | 63 | 98 |
| Smolt | 251581 | 0 | 2310826 | 5375075 | 21.37 | 2.33 | 2025-10-31 | 2025-11-02 | 3 | 3 | 6 | 44 | 65 |
| Post-Smolt | 206227 | 206227 | 375150 | 375150 | 1.82 | 1.0 | 2026-01-21 | 2026-01-23 | 1 | 1 | 1 | 2 | 2 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 89748 | 89748 | 0 | 1 | 1 | yes | Bridge-aware (direct edge linkage; linked sources: 1) | OK |
| Fry -> Parr | 3500200 | 3500200 | 0 | 11 | 11 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 895580 | 364835 | -530745 | 3 | 3 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 305904 | 277831 | -28073 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0040`, `251.0042`, `251.0043`, `251.0044`, `251.0045`, `251.0046`, `251.0047`, `251.0048`, `251.0049`, `251.0050`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`
- Bridge fishgroups excluded from stage-entry windows: `251.0088`, `251.0092`, `251.0095`, `251.0099`, `251.0100`, `251.0101`, `251.0102`, `251.0103`, `251.0106`, `251.0109`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 252 | 252 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 43

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 43 | Hatchery:43 | S24 Strond:43 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 43 | 0 | Hatchery:43 | S24 Strond:43 | Unknown:43 |
| Reachable outside descendants | 119 | 0 | Hatchery:119 | S24 Strond:119 | Unknown:119 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 1; latest holder in selected component: 1; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| I4 | BEF81AF4-5599-4ACC-B23B-FBB5FF71D17E | `67FE36B8-7DDE-4EAD-8601-7E268C614F28` | `67FE36B8-7DDE-4EAD-8601-7E268C614F28` | yes | 206227 | 27972.9 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)