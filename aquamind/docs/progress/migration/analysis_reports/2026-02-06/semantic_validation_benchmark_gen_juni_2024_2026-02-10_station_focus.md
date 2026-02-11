# Semantic Migration Validation Report

- Component key: `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`
- Batch: `Benchmark Gen. Juni 2024` (id=370)
- Populations: 359
- Window: 2024-06-13 07:33:41 → 2025-11-10 14:47:52

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 5212 | 5212 | 0.00 |
| Feeding kg | 1312139.56 | 1312139.56 | -0.00 |
| Mortality events | 6784 | 6649 | 135.00 |
| Mortality count | 535109 | 535109 | 0.00 |
| Mortality biomass kg | 0.00 | 13508.01 | -13508.01 |
| Culling events | 25 | 25 | 0.00 |
| Culling count | 137377 | 137377 | 0.00 |
| Culling biomass kg | 4242656.00 | 4242656.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 122 | 122 | 0.00 |
| Growth samples | 607 | 607 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 672486
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 75 total, 65 bridge-classified, 6 same-stage superseded-zero, 4 short-lived orphan-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 87.
- Fishgroup classification: 123 temporary bridge fishgroups, 67 real stage-entry fishgroups, 123 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3387493 | 0 | 3387493 | 3387493 | 1.0 | 1.0 | 2024-06-13 | 2024-06-15 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3067661 | 0 | 3067661 | 3067661 | 1.0 | 1.0 | 2024-09-04 | 2024-09-06 | 12 | 12 | 0 | 12 | 12 |
| Parr | 2879144 | 0 | 4031711 | 11211209 | 3.89 | 2.78 | 2024-12-04 | 2024-12-06 | 9 | 9 | 4 | 71 | 127 |
| Smolt | 531460 | 0 | 3566911 | 10048836 | 18.91 | 2.82 | 2025-02-05 | 2025-02-07 | 3 | 3 | 0 | 73 | 78 |
| Post-Smolt | 407372 | 1619290 | 2503456 | 5170561 | 12.69 | 2.07 | 2025-05-15 | 2025-05-17 | 4 | 4 | 4 | 89 | 103 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1166664 | 89748 | -1076916 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | WARN: stage drop exceeds total known removals by 404430 |
| Fry -> Parr | 89748 | 89748 | 0 | 9 | 9 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 17428 | 16744 | -684 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 18955 | 12947 | -6008 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0052`, `242.0053`, `242.0054`, `242.0055`, `242.0056`, `242.0057`, `242.0058`, `242.0059`, `242.0060`, `242.0061`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0008`, `242.0009`, `242.0010`, `242.0011`
- Bridge fishgroups excluded from stage-entry windows: `242.0060`, `242.0073`, `242.0074`, `242.0076`, `242.0235`, `242.0238`, `242.0239`, `242.0240`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 359 | 359 | 100.0 | 0 | 0 | 0 |
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
- Direct external destination populations (any role): 100

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 61 | Hatchery:61 | S24 Strond:61 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 100 | 0 | Hatchery:100 | S24 Strond:100 | Unknown:100 |
| Reachable outside descendants | 227 | 0 | Hatchery:227 | S24 Strond:227 | Unknown:227 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 13; latest holder in selected component: 4; latest holder outside selected component: 9; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| G1 | 6073D1BB-0651-461C-AFF6-925927E49552 | `953DDF31-4999-4E2D-A5DB-CC54AEFC82F0` | `953DDF31-4999-4E2D-A5DB-CC54AEFC82F0` | yes | 128885 | 64865.7 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| G2 | 657402E3-3500-466C-86D5-DC1C767A3A70 | `20CA0F57-C8E8-4DF2-A20A-63EB3578EFF2` | `20CA0F57-C8E8-4DF2-A20A-63EB3578EFF2` | yes | 135678 | 49261.2 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| G3 | 01CB4CBE-E9C6-4200-8A5F-5F095B388D71 | `7D9B9688-50DD-4F8B-B413-797F0D8B85E1` | `7D9B9688-50DD-4F8B-B413-797F0D8B85E1` | yes | 126967 | 35670.3 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| G4 | 59951ABF-8516-489D-8C11-6B5A8BABAE83 | `9A6A06A5-9269-40EF-8DB6-EA4F4F95FC62` | `9A6A06A5-9269-40EF-8DB6-EA4F4F95FC62` | yes | 112143 | 55705.1 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| H1 | D306600C-5EE9-4FD5-A9CC-278C501212D0 | `5822CA5F-6E6A-4315-B9DB-B3A1C69B87B8` | `336383E4-EF6E-4D6D-A7E6-E25A9B14FFF9` | no | 132142 | 20511.3 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| H2 | 64D0225A-59C0-424E-96CC-8A2674E5D6E5 | `9AE8E7A9-78BF-40AD-8191-2C4151F7654F` | `A8AF5595-F89E-4853-8356-6DFF8B3562E5` | no | 146691 | 31505.0 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| H3 | 5025C727-D163-497A-9C14-5BBFC6736B97 | `8B92DF8E-4919-4EBE-AB25-834ECC817B56` | `4B57C78A-2273-4168-9581-5A66EE2AE8EA` | no | 158411 | 22031.9 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| H4 | D581DCDB-5F4F-4423-A6D1-3E872E1E9C2E | `0AC0BB0E-350D-498D-AFD3-E41DDC923750` | `C55327FC-14CC-4F30-A286-959E5D29487E` | no | 151985 | 26189.9 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I1 | 6D5F9BAE-166A-4A37-B5FD-42565AFA9256 | `9C056EFE-ABEB-4CB6-9D02-57694E4301F3` | `314C5F71-77B2-44C6-8A99-DDE87D052E78` | no | 116402 | 27347.5 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I2 | 59E1DAC8-9F21-4ADB-9161-DD5350184421 | `838F9B75-1167-4702-8168-1482CEA71AAA` | `3573964B-BA05-4A20-9E20-C335BD535DEC` | no | 142751 | 24165.7 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| I4 | BEF81AF4-5599-4ACC-B23B-FBB5FF71D17E | `C6FF2F10-F58E-4856-A740-771DB298952C` | `64C26E67-4E0F-4A45-8A18-B049A228C605` | no | 118854 | 27221.0 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J2 | 3BFCC01C-BCA1-4472-A53D-48CA4DDAFFF2 | `D299B3C5-AADF-4D8B-AA7B-D335E9903116` | `B7D18F12-0C9D-4FB1-9E82-A7DC602F8905` | no | 126467 | 53347.5 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |
| J3 | A3E66323-A9A1-4C9A-9A0D-3088BA90D8BE | `C528DC3E-D76D-4FAC-958D-F78AA5BA716D` | `8B346474-FAB0-4E75-AB4E-364DF6B1D1D0` | no | 126223 | 44061.7 | 2025-10-31 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, and short-lived orphan-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)