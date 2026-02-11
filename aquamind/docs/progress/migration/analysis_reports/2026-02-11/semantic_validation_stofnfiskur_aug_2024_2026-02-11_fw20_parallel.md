# Semantic Migration Validation Report

- Component key: `D3FB15A0-71E5-4EEE-8CAE-39C7BE1DD484`
- Batch: `Stofnfiskur Aug 2024` (id=416)
- Populations: 183
- Window: 2024-08-08 16:57:08 → 2025-12-29 16:00:56

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1864 | 1864 | 0.00 |
| Feeding kg | 320240.35 | 320240.35 | 0.00 |
| Mortality events | 4883 | 4320 | 563.00 |
| Mortality count | 250518 | 250518 | 0.00 |
| Mortality biomass kg | 0.00 | 3143.18 | -3143.18 |
| Culling events | 8 | 8 | 0.00 |
| Culling count | 233185 | 233185 | 0.00 |
| Culling biomass kg | 5296112.00 | 5296112.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 334 | 334 | 0.00 |
| Growth samples | 16 | 16 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 483703
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 35 total, 30 bridge-classified, 0 same-stage superseded-zero, 4 short-lived orphan-zero, 0 no-count-evidence-zero, 1 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 70.
- Fishgroup classification: 61 temporary bridge fishgroups, 46 real stage-entry fishgroups, 61 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1586912 | 0 | 1586912 | 1586912 | 1.0 | 1.0 | 2024-08-08 | 2024-08-10 | 5 | 5 | 0 | 5 | 5 |
| Fry | 1509134 | 0 | 1771901 | 2574212 | 1.71 | 1.45 | 2024-10-17 | 2024-10-19 | 30 | 30 | 0 | 40 | 44 |
| Parr | 1172608 | 0 | 1728915 | 7352205 | 6.27 | 4.25 | 2025-01-24 | 2025-01-26 | 8 | 8 | 5 | 82 | 99 |
| Smolt | 303184 | 0 | 1299177 | 2173934 | 7.17 | 1.67 | 2025-06-14 | 2025-06-16 | 1 | 1 | 1 | 12 | 22 |
| Post-Smolt | 108488 | 378166 | 502101 | 502101 | 4.63 | 1.0 | 2025-08-11 | 2025-08-13 | 2 | 2 | 0 | 9 | 13 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1628460 | 1628460 | 0 | 30 | 30 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |
| Fry -> Parr | 936362 | 413826 | -522536 | 8 | 8 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | WARN: stage drop exceeds total known removals by 38833 |
| Parr -> Smolt | 256782 | 119603 | -137179 | 1 | 1 | yes | Bridge-aware (linked sources: 7) | OK |
| Smolt -> Post-Smolt | 119603 | 110166 | -9437 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `244.0023`, `244.0025`, `244.0029`, `244.0031`, `244.0050`, `244.0051`, `244.0057`, `244.0058`, `244.0059`, `244.0063`
- Real stage-entry fishgroup examples: `244.0002`, `244.0003`, `244.0004`, `244.0005`, `244.0006`, `244.0007`, `244.0008`, `244.0009`, `244.0010`, `244.0011`
- Bridge fishgroups excluded from stage-entry windows: `244.0050`, `244.0051`, `244.0057`, `244.0058`, `244.0059`, `244.0124`

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
| Fry | 142490 |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 77

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 24 | Hatchery:24 | S16 Glyvradalur:24 |
| SourcePopBefore -> SourcePopAfter | 49 | Hatchery:49 | S16 Glyvradalur:49 |
| DestPopBefore -> DestPopAfter | 7 | Hatchery:7 | S16 Glyvradalur:7 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 77 | 0 | Hatchery:77 | S16 Glyvradalur:77 | Unknown:77 |
| Reachable outside descendants | 124 | 0 | Hatchery:124 | S16 Glyvradalur:124 | Unknown:124 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 8; latest holder in selected component: 8; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E01 | A8588434-EC8A-48D5-A7BB-9CB1AE614928 | `D9A84BC2-5497-44DB-AB26-F318E801C026` | `D9A84BC2-5497-44DB-AB26-F318E801C026` | yes | 143164 | 51676.8 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E02 | FC172B8F-B999-468E-A079-A0E9380D1E13 | `527E2031-CD42-4E0B-B989-44B4AC8EDD64` | `527E2031-CD42-4E0B-B989-44B4AC8EDD64` | yes | 138351 | 58835.1 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E03 | A8D42A0F-9BDE-4EF9-BFE9-B2A6FED2F91B | `CF2272D0-6A4A-4F21-83D9-677231409AFA` | `CF2272D0-6A4A-4F21-83D9-677231409AFA` | yes | 139102 | 33218.4 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E04 | 3783BBEC-FBF4-4894-9C26-18D02559FB87 | `9BEB44BF-67B9-4900-B751-FF9733644E83` | `9BEB44BF-67B9-4900-B751-FF9733644E83` | yes | 139265 | 55349.0 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E05 | 4CE72C8A-9115-4EFF-AE82-88CEBF27C4D3 | `48B9D58F-D968-458E-8EE1-640C257E68E9` | `48B9D58F-D968-458E-8EE1-640C257E68E9` | yes | 101429 | 27163.9 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E06 | EBF0F34D-40F7-4D69-8EAC-ECE71F5CB499 | `9F092F70-888C-4EBA-B0D1-6A2907BE3FEF` | `9F092F70-888C-4EBA-B0D1-6A2907BE3FEF` | yes | 101134 | 43907.4 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E07 | B64B9CB2-A0E0-442C-9A51-E943A338F71E | `E7E143C7-80BE-45F5-A05E-25214C8544AA` | `E7E143C7-80BE-45F5-A05E-25214C8544AA` | yes | 143120 | 32106.9 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |
| E08 | 25C6068A-E480-45C9-8CC2-AAE6F566354C | `47CFB669-2460-433E-9D62-6A75B39D8E69` | `47CFB669-2460-433E-9D62-6A75B39D8E69` | yes | 143852 | 29610.6 | 2025-10-31 00:00:00 | S16 Glyvradalur | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)