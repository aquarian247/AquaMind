# Semantic Migration Validation Report

- Component key: `F7D08CC6-083F-4CB4-9271-ECABFA6D3F2C`
- Batch: `StofnFiskur okt. 2024` (id=412)
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
| Egg&Alevin | 390772 | 0 | 390772 | 390772 | 1.0 | 1.0 | 2024-10-02 | 2024-10-04 | 1 | 1 | 0 | 1 | 1 |
| Fry | 377691 | 0 | 777574 | 1190871 | 3.15 | 1.53 | 2024-12-29 | 2024-12-31 | 12 | 12 | 0 | 92 | 92 |
| Parr | 155797 | 0 | 556317 | 1466319 | 9.41 | 2.64 | 2025-04-01 | 2025-04-03 | 1 | 1 | 1 | 37 | 97 |
| Smolt | 98860 | 0 | 125696 | 222014 | 2.25 | 1.77 | 2025-08-07 | 2025-08-09 | 5 | 5 | 1 | 15 | 20 |
| Post-Smolt | 99746 | 172752 | 172752 | 398367 | 3.99 | 2.31 | 2025-06-23 | 2025-06-25 | 1 | 1 | 0 | 9 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 400520 | 400520 | 0 | 12 | 12 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Parr | 377691 | 155797 | -221894 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 18134 |
| Parr -> Smolt | 245762 | 109692 | -136070 | 5 | 5 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 98860 | 99746 | 886 | 1 | 0 | no | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |

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
- Containers checked: 4; latest holder in selected component: 4; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| T1 | 615478F5-62CD-4100-9F9B-955CC145F55F | `228CF760-0F35-402A-AEBC-F6EE3C26063D` | `228CF760-0F35-402A-AEBC-F6EE3C26063D` | yes | 37807 | 8509.8 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |
| T2 | 449002D1-9C9A-4198-810A-82463AF2E122 | `5F75D907-CA8A-4B56-94B7-0A8889F19122` | `5F75D907-CA8A-4B56-94B7-0A8889F19122` | yes | 39828 | 9416.86 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |
| T3 | 38AD50AA-F57C-4ED8-9A90-02D86667C113 | `23FAC392-A751-4541-9123-BB1ED1050598` | `23FAC392-A751-4541-9123-BB1ED1050598` | yes | 37449 | 5803.18 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |
| T4 | 2FE79468-E018-4DB5-A87A-A3CE811A4123 | `EE67DD06-0742-4289-81DC-94BCCF5B5D0A` | `EE67DD06-0742-4289-81DC-94BCCF5B5D0A` | yes | 35893 | 9514.68 | 2025-10-31 00:00:00 | S08 Gjógv | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)