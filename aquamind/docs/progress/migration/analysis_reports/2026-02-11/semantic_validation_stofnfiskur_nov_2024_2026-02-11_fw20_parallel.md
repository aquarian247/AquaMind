# Semantic Migration Validation Report

- Component key: `94B7E42D-16B1-4CD8-A361-1E99D04E8612`
- Batch: `Stofnfiskur Nov 2024` (id=417)
- Populations: 138
- Window: 2024-11-20 14:02:24 → 2026-02-11 02:19:15.062518

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1033 | 1033 | 0.00 |
| Feeding kg | 92044.92 | 92044.92 | 0.00 |
| Mortality events | 3022 | 2652 | 370.00 |
| Mortality count | 513904 | 513904 | 0.00 |
| Mortality biomass kg | 0.00 | 2384.15 | -2384.15 |
| Culling events | 4 | 4 | 0.00 |
| Culling count | 141370 | 141370 | 0.00 |
| Culling biomass kg | 2095435.00 | 2095435.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 12 | 12 | 0.00 |
| Growth samples | 10 | 10 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 655274
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/4 bridge-aware (0.0%), 4/4 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 33 total, 13 bridge-classified, 5 same-stage superseded-zero, 5 short-lived orphan-zero, 8 no-count-evidence-zero, 2 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 46.
- Fishgroup classification: 53 temporary bridge fishgroups, 22 real stage-entry fishgroups, 53 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1777006 | 0 | 1777006 | 1777006 | 1.0 | 1.0 | 2024-11-20 | 2024-11-22 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1335972 | 0 | 1335972 | 1335972 | 1.0 | 1.0 | 2025-02-06 | 2025-02-08 | 8 | 8 | 0 | 8 | 8 |
| Parr | 1149547 | 0 | 1906718 | 9960382 | 8.66 | 5.22 | 2025-05-05 | 2025-05-07 | 8 | 8 | 3 | 81 | 98 |
| Smolt | 113086 | 358777 | 567180 | 1941685 | 17.17 | 3.42 | 2025-09-06 | 2025-09-08 | 1 | 1 | 4 | 11 | 21 |
| Post-Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 6 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1777006 | 1335972 | -441034 | 8 | 7 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 1335972 | 1149547 | -186425 | 8 | 7 | no | Entry window (incomplete linkage) | OK |
| Parr -> Smolt | 1149547 | 113086 | -1036461 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 381187 |
| Smolt -> Post-Smolt | 113086 | 0 | -113086 | 0 | 0 | no | Entry window (no entry populations) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `245.0014`, `245.0015`, `245.0017`, `245.0023`, `245.0024`, `245.0027`, `245.0036`, `245.0039`, `245.0040`, `245.0041`
- Real stage-entry fishgroup examples: `245.0002`, `245.0003`, `245.0004`, `245.0005`, `245.0006`, `245.0007`, `245.0008`, `245.0009`, `245.0010`, `245.0011`
- Bridge fishgroups excluded from stage-entry windows: `245.0014`, `245.0023`, `245.0024`, `245.0073`, `245.0076`, `245.0080`, `245.0083`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 138 | 138 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 172959 |
| Parr | 66825 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `837D3C86-17D7-407F-952D-996CAAD15322` | Fry | 172959 | 222572 |
| `8DECE7C7-6748-4CDF-8AE9-5C898C33625C` | Parr | 66825 | 66825 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 87520 |
| Fry | 131097 |
| Parr | 95 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 61

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 11 | Hatchery:11 | S16 Glyvradalur:11 |
| SourcePopBefore -> SourcePopAfter | 45 | Hatchery:45 | S16 Glyvradalur:45 |
| DestPopBefore -> DestPopAfter | 8 | Hatchery:8 | S16 Glyvradalur:8 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 61 | 0 | Hatchery:61 | S16 Glyvradalur:61 | Unknown:61 |
| Reachable outside descendants | 81 | 0 | Hatchery:81 | S16 Glyvradalur:81 | Unknown:81 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| D01 | A149E1A7-5A9B-4993-88B0-CEAD2E7C9A28 | `4C5B8F35-D05E-4D5D-A178-FAACE3FB518F` | `4C5B8F35-D05E-4D5D-A178-FAACE3FB518F` | yes | 289884 | 28562.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| D02 | B35798D6-0CEC-4877-AE42-22701F31DEF4 | `D8FBB9EE-B66B-4872-B569-10897A4BA24C` | `D8FBB9EE-B66B-4872-B569-10897A4BA24C` | yes | 297322 | 43773.1 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| D03 | 1C86F107-5D9C-405A-BEFE-8357A3C01352 | `B7D4C17D-F84A-4678-92E4-86116D9C8291` | `B7D4C17D-F84A-4678-92E4-86116D9C8291` | yes | 249404 | 17979.7 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)