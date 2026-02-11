# Semantic Migration Validation Report

- Component key: `D8EEC9E7-59AA-41A8-9D26-0BD881B510FC`
- Batch: `AquaGen Mars 25` (id=426)
- Populations: 68
- Window: 2025-03-19 16:32:24 → 2026-02-11 11:04:46.136153

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1726 | 1726 | 0.00 |
| Feeding kg | 29697.49 | 29697.49 | 0.00 |
| Mortality events | 1794 | 1780 | 14.00 |
| Mortality count | 246502 | 246502 | 0.00 |
| Mortality biomass kg | 0.00 | 330.33 | -330.33 |
| Culling events | 21 | 21 | 0.00 |
| Culling count | 123250 | 123250 | 0.00 |
| Culling biomass kg | 997881.40 | 997881.40 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
| Growth samples | 12 | 12 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 369752
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 41 total, 14 bridge-classified, 0 same-stage superseded-zero, 6 short-lived orphan-zero, 18 no-count-evidence-zero, 3 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 12.
- Fishgroup classification: 16 temporary bridge fishgroups, 21 real stage-entry fishgroups, 16 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1707791 | 0 | 1707791 | 1707791 | 1.0 | 1.0 | 2025-03-19 | 2025-03-21 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1452793 | 0 | 1452793 | 1452793 | 1.0 | 1.0 | 2025-06-06 | 2025-06-08 | 12 | 12 | 0 | 12 | 12 |
| Parr | 704884 | 1375277 | 1375277 | 1983622 | 2.81 | 1.44 | 2025-09-12 | 2025-09-14 | 4 | 4 | 2 | 10 | 43 |
| Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1751479 | 1452793 | -298686 | 12 | 12 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |
| Fry -> Parr | 725761 | 704884 | -20877 | 4 | 4 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 704884 | 0 | -704884 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 335132 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0018`, `251.0019`, `251.0020`, `251.0021`, `251.0022`, `251.0023`, `251.0026`, `251.0027`, `251.0030`, `251.0031`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`
- Bridge fishgroups excluded from stage-entry windows: `251.0022`, `251.0023`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 68 | 68 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Count Provenance

- Populations where assignment count came from status snapshot fallback (conserved transfer count was zero):
| Stage | Population count from fallback |
| --- | ---: |
| Fry | 1452793 |
| Parr | 1375277 |

| PopulationID | Stage | Assignment count | Status snapshot count |
| --- | --- | ---: | ---: |
| `6BEA111E-A50C-443C-A847-12C2B3068843` | Parr | 264826 | 295701 |
| `63949491-F5E0-4B6C-8CB3-FEDDB5050CC8` | Parr | 261856 | 273242 |
| `180E5F4C-A6D5-43B4-9918-3F6EF7771F4B` | Parr | 228779 | 233504 |
| `BD1F835A-F3F2-43D8-A8B0-1DA618B74FC2` | Parr | 211637 | 228924 |
| `8239BE8A-228F-4785-8872-436C888C2A3E` | Parr | 206523 | 208051 |

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1751479 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 17

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 5 | Hatchery:5 | S03 Norðtoftir:5 |
| SourcePopBefore -> SourcePopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 17 | 0 | Hatchery:17 | S03 Norðtoftir:17 | Unknown:17 |
| Reachable outside descendants | 28 | 0 | Hatchery:28 | S03 Norðtoftir:28 | Unknown:28 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 6; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 801 | C0F3B240-CC70-4476-893A-D411FB51E61C | `BD1F835A-F3F2-43D8-A8B0-1DA618B74FC2` | `BD1F835A-F3F2-43D8-A8B0-1DA618B74FC2` | yes | 227329 | 4590.97 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 802 | 6CC24621-030E-4352-98EC-B59A9945B35B | `180E5F4C-A6D5-43B4-9918-3F6EF7771F4B` | `180E5F4C-A6D5-43B4-9918-3F6EF7771F4B` | yes | 230317 | 6923.25 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 803 | 35F54316-EB0D-43C9-A6C1-D805018AD9D4 | `63949491-F5E0-4B6C-8CB3-FEDDB5050CC8` | `63949491-F5E0-4B6C-8CB3-FEDDB5050CC8` | yes | 272311 | 4984.12 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 804 | 684837F1-02C2-4759-9EFA-E25E996CE25A | `8239BE8A-228F-4785-8872-436C888C2A3E` | `8239BE8A-228F-4785-8872-436C888C2A3E` | yes | 207464 | 6836.48 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 805 | 968B5094-265D-4ECB-ACDE-CD72467CB995 | `6BEA111E-A50C-443C-A847-12C2B3068843` | `6BEA111E-A50C-443C-A847-12C2B3068843` | yes | 294826 | 5963.79 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 806 | BA09C565-3DF5-4CB9-A55C-BD7FD1D26378 | `9A4A7A49-04A3-47E4-9F15-33968F3D9B9C` | `9A4A7A49-04A3-47E4-9F15-33968F3D9B9C` | yes | 203896 | 6777.63 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)