# Semantic Migration Validation Report

- Component key: `F7D08CC6-083F-4CB4-9271-ECABFA6D3F2C`
- Batch: `StofnFiskur okt. 2024` (id=465)
- Populations: 222
- Window: 2024-10-02 08:01:52 → 2026-01-10 09:09:32

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3116 | 3116 | 0.00 |
| Feeding kg | 40389.39 | 40389.39 | -0.00 |
| Mortality events | 2686 | 2479 | 207.00 |
| Mortality count | 35624 | 35624 | 0.00 |
| Mortality biomass kg | 0.00 | 469.67 | -469.67 |
| Culling events | 18 | 18 | 0.00 |
| Culling count | 168136 | 168136 | 0.00 |
| Culling biomass kg | 8475287.60 | 8475287.60 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 10 | 10 | 0.00 |
| Growth samples | 68 | 68 | 0.00 |
| Health journal entries | 1 | 1 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 203760
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/4 bridge-aware (50.0%), 2/4 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 68 total, 68 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 113.
- Fishgroup classification: 85 temporary bridge fishgroups, 20 real stage-entry fishgroups, 85 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 400520 | 0 | 400520 | 400520 | 1.0 | 1.0 | 2024-10-02 | 2024-10-04 | 1 | 1 | 0 | 1 | 1 |
| Fry | 390647 | 0 | 791167 | 1214453 | 3.11 | 1.54 | 2024-12-29 | 2024-12-31 | 12 | 12 | 0 | 92 | 92 |
| Parr | 158458 | 530442 | 867012 | 1581358 | 9.98 | 1.82 | 2025-04-01 | 2025-04-03 | 1 | 1 | 1 | 37 | 97 |
| Smolt | 99517 | 0 | 129574 | 261187 | 2.62 | 2.02 | 2025-08-07 | 2025-08-09 | 5 | 5 | 1 | 15 | 20 |
| Post-Smolt | 100112 | 0 | 172937 | 383193 | 3.83 | 2.22 | 2025-06-23 | 2025-06-25 | 1 | 1 | 0 | 9 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 400520 | 400520 | 0 | 12 | 12 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Parr | 390647 | 158458 | -232189 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 28429 |
| Parr -> Smolt | 245762 | 109692 | -136070 | 5 | 5 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 99517 | 100112 | 595 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0038`, `243.0039`, `243.0040`, `243.0041`, `243.0042`, `243.0044`, `243.0045`, `243.0046`, `243.0047`, `243.0048`
- Real stage-entry fishgroup examples: `243.0002`, `243.0014`, `243.0016`, `243.0018`, `243.0020`, `243.0022`, `243.0024`, `243.0026`, `243.0028`, `243.0030`
- Bridge fishgroups excluded from stage-entry windows: `243.0062`, `243.0168`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 222 | 222 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 19

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 11 | Hatchery:11 | S08 Gjógv:11 |
| SourcePopBefore -> SourcePopAfter | 8 | Hatchery:8 | S08 Gjógv:8 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 19 | 0 | Hatchery:19 | S08 Gjógv:19 | Unknown:19 |
| Reachable outside descendants | 70 | 0 | Hatchery:70 | S08 Gjógv:70 | Unknown:70 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 6; latest holder in selected component: 0; latest holder outside selected component: 6; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E01 | 723D1867-FC4F-4926-9241-0CC42DCEE66C | `47EB2337-843C-4CBC-924D-81D20A136DD9` | `7C216969-5683-425A-8985-800873DEA681` | no | 23200 | 1322.4 | 2026-01-12 16:26:50 | S08 Gjógv | Hatchery |
| E02 | 1B045DF6-5955-46D1-A50D-CC5DAD809AF4 | `0B7C2705-1D44-4FBA-BA2F-21E520C15748` | `A8F51C3F-7563-42F2-BB94-8871ED91BF0E` | no | 1949 | 111.09 | 2026-01-13 17:07:18 | S08 Gjógv | Hatchery |
| F03 | 299B9886-CD7B-4AA3-ADCB-C1CDFEAECB5B | `C5B2BD66-AA09-40D5-B021-3019BC56C453` | `7B0189C8-C5B9-4CB1-972C-2116E74EA02F` | no | 855 | 48.73 | 2025-12-18 00:00:00 | S08 Gjógv | Hatchery |
| R2 | 619D2305-4084-4906-8EC9-679AB3A38675 | `5A6376AA-F54F-4D78-919E-667735B628DB` | `4FFC5FCA-BB32-4B05-ABD3-08631FC145EC` | no | 59245 | 2562.43 | 2026-01-12 10:26:18 | S08 Gjógv | Hatchery |
| R3 | 2899207F-73F3-46CD-82D1-5569AAFF016A | `C643B963-C5D6-48EC-84C0-AC119B06B6FB` | `6923CCFC-8004-4AF5-B9FF-DBBA5B3C19E1` | no | 31508 | 1666.33 | 2026-01-22 00:00:00 | S08 Gjógv | Hatchery |
| Skiljing | 7F3DFBBD-E1A8-4CA5-A895-22C48C976481 | `0AC83AE6-A706-4C83-99AD-D63A4308DDDC` | `87E6285A-9D82-4654-8906-246B4E9F5959` | no | 295360 | 1990.48 | 2025-08-21 14:43:55 | S08 Gjógv | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (advisory)