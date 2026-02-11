# Semantic Migration Validation Report

- Component key: `65370D45-A30A-4810-B8F0-06FE2DB4A001`
- Batch: `Benchmark Gen. Septembur 2024` (id=436)
- Populations: 162
- Window: 2024-09-18 11:20:02 → 2026-01-10 10:20:49

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2076 | 2076 | 0.00 |
| Feeding kg | 329102.94 | 329102.94 | 0.00 |
| Mortality events | 3190 | 3149 | 41.00 |
| Mortality count | 2432125 | 2432125 | 0.00 |
| Mortality biomass kg | 0.00 | 7844.28 | -7844.28 |
| Culling events | 7 | 7 | 0.00 |
| Culling count | 84878 | 84878 | 0.00 |
| Culling biomass kg | 5615642.60 | 5615642.60 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 14 | 14 | 0.00 |
| Growth samples | 241 | 241 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 2517003
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 38 total, 19 bridge-classified, 1 same-stage superseded-zero, 17 short-lived orphan-zero, 1 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 32.
- Fishgroup classification: 30 temporary bridge fishgroups, 62 real stage-entry fishgroups, 30 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3397931 | 0 | 3397931 | 3397931 | 1.0 | 1.0 | 2024-09-18 | 2024-09-20 | 39 | 39 | 0 | 39 | 39 |
| Fry | 1140159 | 0 | 1140159 | 1140159 | 1.0 | 1.0 | 2024-12-12 | 2024-12-14 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1114943 | 0 | 2071497 | 5290869 | 4.75 | 2.55 | 2025-02-11 | 2025-02-13 | 3 | 3 | 2 | 30 | 50 |
| Smolt | 375991 | 0 | 1416200 | 2870295 | 7.63 | 2.03 | 2025-06-17 | 2025-06-19 | 4 | 4 | 3 | 26 | 26 |
| Post-Smolt | 522388 | 893764 | 1100976 | 1536218 | 2.94 | 1.4 | 2025-09-24 | 2025-09-26 | 4 | 4 | 3 | 17 | 35 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1166664 | 89744 | -1076920 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | OK |
| Fry -> Parr | 89744 | 89744 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 39133 | 29190 | -9943 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 44660 | 41895 | -2765 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0042`, `243.0052`, `243.0053`, `243.0054`, `243.0055`, `243.0056`, `243.0057`, `243.0059`, `243.0061`, `243.0062`
- Real stage-entry fishgroup examples: `243.0001`, `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`
- Bridge fishgroups excluded from stage-entry windows: `243.0056`, `243.0059`, `243.0094`, `243.0095`, `243.0096`, `243.0126`, `243.0127`, `243.0128`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 162 | 162 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500000 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 69

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 30 | Hatchery:30 | S24 Strond:30 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 69 | 0 | Hatchery:69 | S24 Strond:69 | Unknown:69 |
| Reachable outside descendants | 110 | 0 | Hatchery:110 | S24 Strond:110 | Unknown:110 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 8; latest holder in selected component: 8; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| I1 | 6D5F9BAE-166A-4A37-B5FD-42565AFA9256 | `314C5F71-77B2-44C6-8A99-DDE87D052E78` | `314C5F71-77B2-44C6-8A99-DDE87D052E78` | yes | 116402 | 27347.5 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I2 | 59E1DAC8-9F21-4ADB-9161-DD5350184421 | `3573964B-BA05-4A20-9E20-C335BD535DEC` | `3573964B-BA05-4A20-9E20-C335BD535DEC` | yes | 142751 | 24165.7 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I3 | C637A5E2-53CA-4B79-96AC-36ED5380E328 | `CAB53F6C-189F-4C27-A167-159CF0FA04AC` | `CAB53F6C-189F-4C27-A167-159CF0FA04AC` | yes | 122002 | 33987.1 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I4 | BEF81AF4-5599-4ACC-B23B-FBB5FF71D17E | `64C26E67-4E0F-4A45-8A18-B049A228C605` | `64C26E67-4E0F-4A45-8A18-B049A228C605` | yes | 118854 | 27221.0 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J1 | C0D63A28-8E98-47CF-9271-CB58CBA7F240 | `3CCCDBED-60FC-4DCC-9F2F-D887CB1E314F` | `3CCCDBED-60FC-4DCC-9F2F-D887CB1E314F` | yes | 129631 | 62284.8 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J2 | 3BFCC01C-BCA1-4472-A53D-48CA4DDAFFF2 | `B7D18F12-0C9D-4FB1-9E82-A7DC602F8905` | `B7D18F12-0C9D-4FB1-9E82-A7DC602F8905` | yes | 126467 | 53347.5 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J3 | A3E66323-A9A1-4C9A-9A0D-3088BA90D8BE | `8B346474-FAB0-4E75-AB4E-364DF6B1D1D0` | `8B346474-FAB0-4E75-AB4E-364DF6B1D1D0` | yes | 126223 | 44061.7 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J4 | 5795805D-A47F-43FC-BC2F-3CD520C89062 | `3A0C5EF3-F6AE-4169-B3E3-CDAAF036A315` | `3A0C5EF3-F6AE-4169-B3E3-CDAAF036A315` | yes | 140106 | 43933.1 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)