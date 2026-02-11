# Semantic Migration Validation Report

- Component key: `3C2D4475-F0D2-4DCA-A2B1-0F00378EE82D`
- Batch: `StofnFiskur S-21 apr 25` (id=422)
- Populations: 109
- Window: 2025-04-09 13:32:47 → 2026-02-11 02:46:32.676197

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 205 | 205 | 0.00 |
| Feeding kg | 4831.40 | 4831.40 | 0.00 |
| Mortality events | 775 | 770 | 5.00 |
| Mortality count | 505289 | 505289 | 0.00 |
| Mortality biomass kg | 0.00 | 225.07 | -225.07 |
| Culling events | 22 | 22 | 0.00 |
| Culling count | 52889 | 52889 | 0.00 |
| Culling biomass kg | 719637.00 | 719637.00 | 0.00 |
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

- Mortality biomass note: FishTalk source biomass is zero/missing for this batch; AquaMind mortality biomass is derived from status/assignment context. This row is informational and is not a regression gate criterion.

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 558178
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 86 total, 8 bridge-classified, 0 same-stage superseded-zero, 50 short-lived orphan-zero, 13 no-count-evidence-zero, 15 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 8.
- Fishgroup classification: 12 temporary bridge fishgroups, 19 real stage-entry fishgroups, 12 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1426780 | 0 | 1426780 | 1426780 | 1.0 | 1.0 | 2025-04-09 | 2025-04-11 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1065010 | 0 | 1065010 | 1065010 | 1.0 | 1.0 | 2025-07-11 | 2025-07-13 | 6 | 6 | 0 | 6 | 6 |
| Parr | 676617 | 676617 | 770560 | 933733 | 1.38 | 1.21 | 2025-10-14 | 2025-10-16 | 6 | 6 | 4 | 10 | 82 |
| Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 14 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1426780 | 1065010 | -361770 | 6 | 6 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1501500 | 1501500 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 676617 | 0 | -676617 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 118439 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0014`, `252.0015`, `252.0016`, `252.0017`, `252.0019`, `252.0020`, `252.0022`, `252.0023`, `252.0024`, `252.0026`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `252.0005`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`, `252.0011`
- Bridge fishgroups excluded from stage-entry windows: `252.0017`, `252.0019`, `252.0020`, `252.0024`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 109 | 109 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1045275 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 12

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 5 | Hatchery:5 | S21 Viðareiði:5 |
| SourcePopBefore -> SourcePopAfter | 7 | Hatchery:7 | S21 Viðareiði:7 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 12 | 0 | Hatchery:12 | S21 Viðareiði:12 | Unknown:12 |
| Reachable outside descendants | 21 | 0 | Hatchery:21 | S21 Viðareiði:21 | Unknown:21 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| A01 | 1C4BC069-2B03-4038-9775-1FB3D8C8F915 | `C20D3FC2-A518-487B-B64D-DF20F230D374` | `C20D3FC2-A518-487B-B64D-DF20F230D374` | yes | 135512 | 965.18 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| A03 | 130A5DC0-F1D1-45A3-894C-935BCD0F46DB | `C82C7850-FD6F-43BD-8148-94B4EE004C52` | `C82C7850-FD6F-43BD-8148-94B4EE004C52` | yes | 92869 | 1114.93 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| A05 | 4EDA3C9E-DD86-4EB0-88B7-FC496F829F2D | `36257392-264D-4F30-8CA3-B9145F2B9715` | `36257392-264D-4F30-8CA3-B9145F2B9715` | yes | 75273 | 1053.05 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B05 | BB003B3F-FB6B-4986-BEBC-0CCBA310C92A | `57E13BAC-26E9-48E5-B8B9-5BDBD44E501A` | `57E13BAC-26E9-48E5-B8B9-5BDBD44E501A` | yes | 69658 | 1199.1 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B09 | 1F21A2B3-8C7A-45BD-8B02-9C6B2CF557CF | `6F99F95B-FE2A-4ACF-9B3C-8617757AE2D5` | `6F99F95B-FE2A-4ACF-9B3C-8617757AE2D5` | yes | 73162 | 1102.71 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |
| B10 | AA073C42-72C4-48E2-851E-F12650E119B5 | `FEE7CFD1-E835-4E3F-94B2-0DE5F9226520` | `FEE7CFD1-E835-4E3F-94B2-0DE5F9226520` | yes | 73366 | 1233.25 | 2025-10-31 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)