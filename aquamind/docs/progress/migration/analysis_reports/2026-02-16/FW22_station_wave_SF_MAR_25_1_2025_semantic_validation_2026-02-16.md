# Semantic Migration Validation Report

- Component key: `232FE340-5BBE-4C3A-96A4-0CA91C0B181A`
- Batch: `SF MAR 25` (id=496)
- Populations: 128
- Window: 2025-03-27 09:39:19 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-16 18:24:30.064778, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 832 | 832 | 0.00 |
| Feeding kg | 16584.46 | 16584.46 | -0.00 |
| Mortality events | 2020 | 2012 | 8.00 |
| Mortality count | 268212 | 268212 | 0.00 |
| Mortality biomass kg | 0.00 | 1196.72 | -1196.72 |
| Culling events | 810 | 810 | 0.00 |
| Culling count | 315871 | 315871 | 0.00 |
| Culling biomass kg | 3677687.19 | 3677687.22 | -0.03 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 35 | 35 | 0.00 |
| Growth samples | 72 | 72 | 0.00 |
| Health journal entries | 14 | 14 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 584083
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 14 total, 13 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 34.
- Fishgroup classification: 25 temporary bridge fishgroups, 80 real stage-entry fishgroups, 25 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2320000 | 0 | 2392472 | 2392472 | 1.03 | 1.0 | 2025-03-27 | 2025-03-29 | 69 | 69 | 0 | 71 | 71 |
| Fry | 1589111 | 0 | 2377310 | 3838923 | 2.42 | 1.61 | 2025-06-30 | 2025-07-02 | 6 | 6 | 0 | 12 | 14 |
| Parr | 643090 | 0 | 2177675 | 3496395 | 5.44 | 1.61 | 2025-11-13 | 2025-11-15 | 3 | 3 | 4 | 25 | 30 |
| Smolt | 326620 | 838547 | 838547 | 838547 | 2.57 | 1.0 | 2025-12-11 | 2025-12-13 | 2 | 2 | 0 | 6 | 13 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2320000 | 1589111 | -730889 | 6 | 6 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 146806 |
| Fry -> Parr | 142998 | 142998 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Parr -> Smolt | 116663 | 85848 | -30815 | 2 | 2 | yes | Bridge-aware (linked sources: 4) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0078`, `251.0080`, `251.0082`, `251.0084`, `251.0087`, `251.0088`, `251.0089`, `251.0090`, `251.0091`, `251.0092`
- Real stage-entry fishgroup examples: `251.0001`, `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`
- Bridge fishgroups excluded from stage-entry windows: `251.0088`, `251.0090`, `251.0091`, `251.0092`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 128 | 128 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 2049694 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 70

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 61 | Hatchery:61 | FW22 Applecross:61 |
| SourcePopBefore -> SourcePopAfter | 9 | Hatchery:9 | FW22 Applecross:9 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 70 | 0 | Hatchery:70 | FW22 Applecross:70 | Unknown:70 |
| Reachable outside descendants | 77 | 0 | Hatchery:77 | FW22 Applecross:77 | Unknown:77 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| S05 | 9AC40E19-B41F-4C78-8284-2B867501ADC7 | `E9770E2D-EB91-4017-BF8D-23070AA865E7` | `E9770E2D-EB91-4017-BF8D-23070AA865E7` | yes | 108933 | 7939.83 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| S07 | 5D80C02D-DAD5-4AA8-AAA5-63C138DB428C | `B691673B-A848-47B2-8AD5-E72BEF63D299` | `B691673B-A848-47B2-8AD5-E72BEF63D299` | yes | 93087 | 4542.21 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| S2_A1 | 290C427E-CE19-4DA6-8319-9C185A5D27F0 | `8E29D16E-45EB-49E7-BECA-0583916F1CD1` | `8E29D16E-45EB-49E7-BECA-0583916F1CD1` | yes | 167879 | 9855.63 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| S2_A2 | A485F866-21D5-4F3A-B861-BC685BB5E917 | `1FA77ADD-564F-4B6F-9779-D193E1E89CD5` | `1FA77ADD-564F-4B6F-9779-D193E1E89CD5` | yes | 158741 | 9444.64 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| S2_B3 | 94489615-82BD-4ABA-A61E-66634815D0C8 | `0D6FE6F9-73CF-42A1-89F6-7ABE115D8E7F` | `0D6FE6F9-73CF-42A1-89F6-7ABE115D8E7F` | yes | 150190 | 7565.79 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |
| S2_B4 | B4C17EAA-A4F1-4FD5-86AE-6F0B1EA5230A | `23D12B8A-D5E2-4634-8ACC-64181326C212` | `23D12B8A-D5E2-4634-8ACC-64181326C212` | yes | 159717 | 8172.51 | 2026-01-22 00:00:00 | FW22 Applecross | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)