# Semantic Migration Validation Report

- Component key: `1636C683-E8F2-476D-BC21-0170CA7DCEE8`
- Batch: `Benchmark Gen. Desembur 2024` (id=463)
- Populations: 221
- Window: 2024-12-18 08:52:25 → 2026-02-12 12:16:04.155404

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2889 | 0 | 2889.00 |
| Feeding kg | 297524.43 | 0.00 | 297524.43 |
| Mortality events | 3832 | 0 | 3832.00 |
| Mortality count | 1246577 | 0 | 1246577.00 |
| Mortality biomass kg | 0.00 | 0.00 | 0.00 |
| Culling events | 16 | 0 | 16.00 |
| Culling count | 85367 | 0 | 85367.00 |
| Culling biomass kg | 4488182.00 | 0.00 | 4488182.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 0 | 22.00 |
| Growth samples | 301 | 0 | 301.00 |
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

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 1331944
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 67 total, 37 bridge-classified, 0 same-stage superseded-zero, 12 short-lived orphan-zero, 18 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 36.
- Fishgroup classification: 72 temporary bridge fishgroups, 64 real stage-entry fishgroups, 72 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3504525 | 0 | 3504525 | 3504525 | 1.0 | 1.0 | 2024-12-18 | 2024-12-20 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3196671 | 0 | 3196671 | 3196671 | 1.0 | 1.0 | 2025-03-05 | 2025-03-07 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1656072 | 0 | 3304902 | 8003804 | 4.83 | 2.42 | 2025-05-26 | 2025-05-28 | 7 | 7 | 10 | 50 | 80 |
| Smolt | 180955 | 2095172 | 2305507 | 4429292 | 24.48 | 1.92 | 2025-07-26 | 2025-07-28 | 3 | 3 | 3 | 40 | 44 |
| Post-Smolt | 411541 | 0 | 854079 | 854079 | 2.08 | 1.0 | 2025-10-23 | 2025-10-25 | 3 | 3 | 0 | 6 | 39 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1168167 | 89859 | -1078308 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | OK |
| Fry -> Parr | 66984 | 64241 | -2743 | 7 | 7 | yes | Bridge-aware (linked sources: 9); lineage graph fallback used | OK |
| Parr -> Smolt | 12011 | 6722 | -5289 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 180955 | 411541 | 230586 | 3 | 3 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `244.0046`, `244.0052`, `244.0053`, `244.0054`, `244.0055`, `244.0056`, `244.0057`, `244.0058`, `244.0059`, `244.0060`
- Real stage-entry fishgroup examples: `244.0002`, `244.0003`, `244.0004`, `244.0005`, `244.0006`, `244.0007`, `244.0008`, `244.0009`, `244.0010`, `244.0011`
- Bridge fishgroups excluded from stage-entry windows: `244.0065`, `244.0066`, `244.0083`, `244.0084`, `244.0085`, `244.0087`, `244.0089`, `244.0095`, `244.0096`, `244.0097`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 221 | 221 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3504525 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 73

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 34 | Hatchery:34 | S24 Strond:34 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 73 | 0 | Hatchery:73 | S24 Strond:73 | Unknown:73 |
| Reachable outside descendants | 138 | 0 | Hatchery:138 | S24 Strond:138 | Unknown:138 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 12; latest holder in selected component: 12; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E01 | C4499F00-8E16-45BC-9F5E-8C906481D404 | `A0E6CD66-F8F0-44FC-8611-03BB5D7D691D` | `A0E6CD66-F8F0-44FC-8611-03BB5D7D691D` | yes | 205955 | 29868.0 | 2025-10-28 08:45:58 | S24 Strond | Hatchery |
| E02 | BE5CEE98-7AE2-45AE-8A33-6FC66D026184 | `040913B5-7C51-4A1D-9B93-86B9289D03EA` | `040913B5-7C51-4A1D-9B93-86B9289D03EA` | yes | 178029 | 13092.5 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| E03 | DCB0590A-7BE2-4390-8034-381B1807BB1B | `E890468A-3212-48FA-88E8-F7DA47E9EF1D` | `E890468A-3212-48FA-88E8-F7DA47E9EF1D` | yes | 182541 | 24407.1 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| E04 | 3A14973C-4A4B-403C-B560-6D84A0C8840C | `9A0D562C-F437-4F98-86A3-685B27D1C9E0` | `9A0D562C-F437-4F98-86A3-685B27D1C9E0` | yes | 215533 | 36385.8 | 2025-10-23 15:38:05 | S24 Strond | Hatchery |
| E05 | 7A0A32F7-54F0-4584-A846-3F09436A206E | `1F400610-DFED-4AB1-BD5C-AE27E15A8236` | `1F400610-DFED-4AB1-BD5C-AE27E15A8236` | yes | 214916 | 39536.8 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| E06 | B70AA132-33BD-4A0C-A98E-A85AEB17232F | `8E34C366-DEBD-4BAF-9013-C675A3E2D3B6` | `8E34C366-DEBD-4BAF-9013-C675A3E2D3B6` | yes | 197294 | 26736.8 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F01 | CDD6125F-9D9C-45AB-B777-D73DF74D9200 | `9C157A10-0001-4EF9-92C4-1CCAC82C244E` | `9C157A10-0001-4EF9-92C4-1CCAC82C244E` | yes | 196141 | 26816.2 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F02 | E646C3B6-6F9E-48A8-9AC0-FF13703A331A | `24D937C7-FF45-4124-BD68-85E9233644E3` | `24D937C7-FF45-4124-BD68-85E9233644E3` | yes | 211495 | 30787.3 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F03 | C7106986-70AD-4CB5-A2DE-3AB3ED3B6577 | `1B8198DA-FA9F-41B8-A90F-7222D739646A` | `1B8198DA-FA9F-41B8-A90F-7222D739646A` | yes | 219147 | 29946.9 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F04 | 35E67C93-6A2E-4CA1-9307-03EF27A379BA | `2F0255FE-681F-4D53-B318-21CA3661878A` | `2F0255FE-681F-4D53-B318-21CA3661878A` | yes | 37925 | 4146.57 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F05 | 279C2E24-7E02-4ADC-93DF-9458AFBA4B3F | `B2268464-E947-45FB-BA98-5FD2BA95CE21` | `B2268464-E947-45FB-BA98-5FD2BA95CE21` | yes | 205739 | 31048.9 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| F06 | B2275C36-1B48-495C-AB04-603265976A17 | `DE4D7654-2708-4D07-BDDC-CAEE1146F588` | `DE4D7654-2708-4D07-BDDC-CAEE1146F588` | yes | 209186 | 34146.8 | 2025-10-22 15:32:56 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (advisory)