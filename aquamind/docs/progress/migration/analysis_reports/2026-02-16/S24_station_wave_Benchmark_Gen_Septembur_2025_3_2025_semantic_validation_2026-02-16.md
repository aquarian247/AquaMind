# Semantic Migration Validation Report

- Component key: `1E996D42-BDB6-4E88-BFE2-026DC2086563`
- Batch: `Benchmark Gen Septembur 2025` (id=481)
- Populations: 60
- Window: 2025-09-10 09:02:51 → 2026-02-16 16:27:56.252295

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 0 | 0 | 0.00 |
| Feeding kg | 0.00 | 0.00 | 0.00 |
| Mortality events | 518 | 511 | 7.00 |
| Mortality count | 49794 | 49794 | 0.00 |
| Mortality biomass kg | 0.00 | 4.18 | -4.18 |
| Culling events | 0 | 0 | 0.00 |
| Culling count | 0 | 0 | 0.00 |
| Culling biomass kg | 0.00 | 0.00 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 49794
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 0 total, 0 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 1.
- Fishgroup classification: 0 temporary bridge fishgroups, 51 real stage-entry fishgroups, 0 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500200 | 0 | 3500200 | 3500200 | 1.0 | 1.0 | 2025-09-10 | 2025-09-12 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3352314 | 2961987 | 5520944 | 5520944 | 1.65 | 1.0 | 2025-12-03 | 2025-12-05 | 12 | 12 | 0 | 21 | 21 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1166726 | 89748 | -1076978 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | WARN: stage drop exceeds total known removals by 1027184 |

### Fishgroup Classification Samples

- Real stage-entry fishgroup examples: `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0008`, `253.0009`, `253.0010`, `253.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 60 | 60 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500200 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 40

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | S24 Strond:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 40 | 0 | Hatchery:40 | S24 Strond:40 | Unknown:40 |
| Reachable outside descendants | 58 | 0 | Hatchery:58 | S24 Strond:58 | Unknown:58 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 12; latest holder in selected component: 12; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| B01 | 311E8F88-82D1-4AF6-AB78-F1B4AB2BFDE2 | `454AC1AA-1052-41B6-9500-BACDD011E721` | `454AC1AA-1052-41B6-9500-BACDD011E721` | yes | 242678 | 295.08 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B02 | 9D84E007-7A38-4D72-AB81-1A6FC6968BB7 | `038D2DC6-08AA-427E-9982-73228002448C` | `038D2DC6-08AA-427E-9982-73228002448C` | yes | 243282 | 345.74 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B03 | 61ABDF56-84CD-40D2-B90C-5FF74D9DCDEE | `172384D4-5831-4614-A05E-1162B5FAEA62` | `172384D4-5831-4614-A05E-1162B5FAEA62` | yes | 245700 | 302.54 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B04 | 1F6ED682-F0CC-459E-9798-4D64C45C5791 | `50B46518-B1C4-4879-90D4-408EA495343C` | `50B46518-B1C4-4879-90D4-408EA495343C` | yes | 263329 | 353.39 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B05 | 37DA2A99-667D-4228-8405-BFD2773F9E3E | `A402C873-FC65-451A-BA8A-F5A0C4F772FF` | `A402C873-FC65-451A-BA8A-F5A0C4F772FF` | yes | 237880 | 312.02 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B06 | 63813753-13F9-41D4-AEB8-8004B4208484 | `A54678B7-8595-41EF-A3A4-E43AB9EBA7A6` | `A54678B7-8595-41EF-A3A4-E43AB9EBA7A6` | yes | 236718 | 314.49 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B07 | A5D4A0F7-0272-4ECA-94AF-20F8E26EC7DA | `A9D0C842-18C9-4565-AE97-8CC6CA9EA17B` | `A9D0C842-18C9-4565-AE97-8CC6CA9EA17B` | yes | 242981 | 343.34 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B08 | FF4CDBF9-FC18-4C1F-ABDA-132246AF24E3 | `064E2D67-A173-411A-A9A7-318CD93F66A3` | `064E2D67-A173-411A-A9A7-318CD93F66A3` | yes | 241002 | 332.7 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B09 | 3F6C9B79-6D9B-4079-81B0-8C3D19BF7291 | `F7BCB214-02E6-4D9F-A491-9A26F99EBEC5` | `F7BCB214-02E6-4D9F-A491-9A26F99EBEC5` | yes | 241849 | 300.49 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B10 | B4906B18-EB3A-4E20-8C02-C2EBCF0834E0 | `378A6020-0FC5-4F6C-B384-FBB0B78ECD7E` | `378A6020-0FC5-4F6C-B384-FBB0B78ECD7E` | yes | 241828 | 320.2 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |
| B11 | B8D06244-3A75-45D0-8A8E-66D1C3FA3D5E | `4E4F0BC5-ECDA-436E-B07D-342D8EBA9BFB` | `4E4F0BC5-ECDA-436E-B07D-342D8EBA9BFB` | yes | 136945 | 158.97 | 2026-01-20 13:58:44 | S24 Strond | Hatchery |
| B12 | 444DC0D7-61FE-401D-85DB-9E7F3C9EA23B | `ADCB0A25-B46D-404B-A04E-F7451E07ACF7` | `ADCB0A25-B46D-404B-A04E-F7451E07ACF7` | yes | 240412 | 320.74 | 2026-01-22 00:00:00 | S24 Strond | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)