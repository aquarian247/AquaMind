# Semantic Migration Validation Report

- Component key: `7B7E162F-72EC-42E9-B32A-953264EAC124`
- Batch: `BF mars 2025` (id=420)
- Populations: 202
- Window: 2025-03-11 23:21:22 → 2026-02-11 02:36:34.278159

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4158 | 4158 | 0.00 |
| Feeding kg | 6551.25 | 6551.25 | 0.00 |
| Mortality events | 3641 | 2537 | 1104.00 |
| Mortality count | 25168 | 25168 | 0.00 |
| Mortality biomass kg | 0.00 | 23.28 | -23.28 |
| Culling events | 32 | 32 | 0.00 |
| Culling count | 103251 | 103251 | 0.00 |
| Culling biomass kg | 2389676.30 | 2389676.30 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 12 | 12 | 0.00 |
| Growth samples | 86 | 86 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 128419
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 99 total, 20 bridge-classified, 0 same-stage superseded-zero, 46 short-lived orphan-zero, 22 no-count-evidence-zero, 11 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 24.
- Fishgroup classification: 21 temporary bridge fishgroups, 38 real stage-entry fishgroups, 21 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 313336 | 0 | 313336 | 313336 | 1.0 | 1.0 | 2025-03-11 | 2025-03-13 | 1 | 1 | 0 | 1 | 1 |
| Fry | 333012 | 0 | 394129 | 457928 | 1.38 | 1.16 | 2025-05-27 | 2025-05-29 | 34 | 34 | 0 | 96 | 113 |
| Parr | 97709 | 302395 | 397025 | 397025 | 4.06 | 1.0 | 2025-09-30 | 2025-10-02 | 2 | 2 | 1 | 4 | 75 |
| Post-Smolt | 189596 | 0 | 192825 | 192825 | 1.02 | 1.0 | 2025-08-21 | 2025-08-23 | 1 | 1 | 0 | 2 | 13 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 313336 | 333012 | 19676 | 34 | 14 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Fry -> Parr | 80508 | 6453 | -74055 | 2 | 2 | yes | Bridge-aware (linked sources: 8); lineage graph fallback used | OK |
| Parr -> Post-Smolt | 10018 | 6453 | -3565 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0037`, `252.0057`, `252.0058`, `252.0059`, `252.0060`, `252.0061`, `252.0062`, `252.0063`, `252.0064`, `252.0065`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `252.0005`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`, `252.0011`
- Bridge fishgroups excluded from stage-entry windows: `252.0037`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 202 | 202 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 9792 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 37

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 33 | Hatchery:33 | S08 Gjógv:33 |
| SourcePopBefore -> SourcePopAfter | 4 | Hatchery:4 | S08 Gjógv:4 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 37 | 0 | Hatchery:37 | S08 Gjógv:37 | Unknown:37 |
| Reachable outside descendants | 117 | 0 | Hatchery:117 | S08 Gjógv:117 | Unknown:117 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| R1 | ECFA2444-362C-4381-A763-88B83A599FB5 | `BC2B362C-D5DF-4BC0-8003-CDE02CCA8449` | `BC2B362C-D5DF-4BC0-8003-CDE02CCA8449` | yes | 108791 | 3740.9 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |
| R3 | 2899207F-73F3-46CD-82D1-5569AAFF016A | `5C7923FC-45C8-4E09-B7F3-32AC7576F913` | `5C7923FC-45C8-4E09-B7F3-32AC7576F913` | yes | 94743 | 3342.79 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |
| Skiljing | 7F3DFBBD-E1A8-4CA5-A895-22C48C976481 | `87E6285A-9D82-4654-8906-246B4E9F5959` | `87E6285A-9D82-4654-8906-246B4E9F5959` | yes | 295360 | 1990.48 | 2025-08-21 14:43:55 | S08 Gjógv | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)