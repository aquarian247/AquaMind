# Semantic Migration Validation Report

- Component key: `3C2D4475-F0D2-4DCA-A2B1-0F00378EE82D`
- Batch: `StofnFiskur S-21 apr 25` (id=470)
- Populations: 109
- Window: 2025-04-09 13:32:47 → 2026-02-16 15:26:20.052874

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
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 39 total, 37 bridge-classified, 2 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 51.
- Fishgroup classification: 60 temporary bridge fishgroups, 21 real stage-entry fishgroups, 60 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501500 | 0 | 1501500 | 1501500 | 1.0 | 1.0 | 2025-04-09 | 2025-04-11 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1501500 | 0 | 1501500 | 1501500 | 1.0 | 1.0 | 2025-07-11 | 2025-07-13 | 6 | 6 | 0 | 6 | 6 |
| Parr | 523026 | 0 | 751071 | 2545491 | 4.87 | 3.39 | 2025-10-14 | 2025-10-16 | 6 | 6 | 4 | 49 | 82 |
| Smolt | 200965 | 608971 | 739496 | 801157 | 3.99 | 1.08 | 2026-01-06 | 2026-01-08 | 2 | 2 | 2 | 8 | 14 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501500 | 1501500 | 0 | 6 | 6 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1501500 | 1501500 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 559103 | 559103 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 7) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0014`, `252.0015`, `252.0016`, `252.0017`, `252.0019`, `252.0020`, `252.0022`, `252.0023`, `252.0024`, `252.0026`
- Real stage-entry fishgroup examples: `252.0001`, `252.0002`, `252.0003`, `252.0004`, `252.0005`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`
- Bridge fishgroups excluded from stage-entry windows: `252.0017`, `252.0019`, `252.0020`, `252.0024`, `252.0055`, `252.0078`

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
- Direct external destination populations (any role): 30

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 5 | Hatchery:5 | S21 Viðareiði:5 |
| SourcePopBefore -> SourcePopAfter | 25 | Hatchery:25 | S21 Viðareiði:25 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 30 | 0 | Hatchery:30 | S21 Viðareiði:30 | Unknown:30 |
| Reachable outside descendants | 49 | 0 | Hatchery:49 | S21 Viðareiði:49 | Unknown:49 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 4; latest holder in selected component: 4; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| C10 | B81F1605-2AC3-4655-8D66-BFF7FD555A24 | `EAB203F1-F3BE-4B45-B6D6-5910745DFF98` | `EAB203F1-F3BE-4B45-B6D6-5910745DFF98` | yes | 100316 | 6954.24 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| C11 | 67FE3B9C-EE00-4F46-A0E9-2C51B2422C5D | `A8991730-0411-4582-A083-5669646D4194` | `A8991730-0411-4582-A083-5669646D4194` | yes | 100649 | 6077.97 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D7 | A83B0B29-E139-47A7-A466-EBB7A1086755 | `1CF3134E-F486-4A66-BFFE-7ABFAE863031` | `1CF3134E-F486-4A66-BFFE-7ABFAE863031` | yes | 100443 | 5315.05 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |
| D8 | C7648C65-ACCA-4A43-92FB-EE3BDC3BC024 | `81551EBB-FF53-4442-9169-D147B3E09865` | `81551EBB-FF53-4442-9169-D147B3E09865` | yes | 101726 | 5816.04 | 2026-01-22 00:00:00 | S21 Viðareiði | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)