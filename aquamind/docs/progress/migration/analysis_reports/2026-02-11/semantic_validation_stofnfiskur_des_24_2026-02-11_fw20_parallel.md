# Semantic Migration Validation Report

- Component key: `A538947B-1EDB-4165-AE2A-09B806B640F2`
- Batch: `Stofnfiskur Des 24` (id=413)
- Populations: 106
- Window: 2024-12-11 11:40:51 → 2026-02-11 02:09:13.924948

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2197 | 2197 | 0.00 |
| Feeding kg | 90126.31 | 90126.31 | -0.00 |
| Mortality events | 2236 | 2133 | 103.00 |
| Mortality count | 468516 | 468516 | 0.00 |
| Mortality biomass kg | 0.00 | 1837.63 | -1837.63 |
| Culling events | 29 | 29 | 0.00 |
| Culling count | 261901 | 261901 | 0.00 |
| Culling biomass kg | 10576350.70 | 10576350.70 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 27 | 27 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 730417
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 44 total, 14 bridge-classified, 0 same-stage superseded-zero, 12 short-lived orphan-zero, 15 no-count-evidence-zero, 3 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 24.
- Fishgroup classification: 27 temporary bridge fishgroups, 31 real stage-entry fishgroups, 27 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1721436 | 0 | 1721436 | 1721436 | 1.0 | 1.0 | 2024-12-11 | 2024-12-13 | 12 | 12 | 0 | 12 | 12 |
| Fry | 1274157 | 0 | 1274157 | 1274157 | 1.0 | 1.0 | 2025-03-05 | 2025-03-07 | 12 | 12 | 0 | 12 | 12 |
| Parr | 659520 | 0 | 1698674 | 4251319 | 6.45 | 2.5 | 2025-05-30 | 2025-06-01 | 4 | 4 | 4 | 31 | 51 |
| Smolt | 88926 | 88926 | 317946 | 371322 | 4.18 | 1.17 | 2025-09-24 | 2025-09-26 | 3 | 3 | 4 | 7 | 19 |
| Post-Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1761814 | 293636 | -1468178 | 12 | 12 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | WARN: stage drop exceeds total known removals by 737761 |
| Fry -> Parr | 146817 | 146817 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 119291 | 89285 | -30006 | 3 | 3 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 88926 | 0 | -88926 | 0 | 0 | no | Entry window (no entry populations) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `244.0025`, `244.0026`, `244.0028`, `244.0029`, `244.0030`, `244.0031`, `244.0033`, `244.0034`, `244.0037`, `244.0038`
- Real stage-entry fishgroup examples: `244.0002`, `244.0003`, `244.0004`, `244.0005`, `244.0006`, `244.0007`, `244.0008`, `244.0009`, `244.0010`, `244.0011`
- Bridge fishgroups excluded from stage-entry windows: `244.0028`, `244.0029`, `244.0030`, `244.0031`, `244.0063`, `244.0064`, `244.0065`, `244.0067`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 106 | 106 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1761814 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 35

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 23 | Hatchery:23 | S03 Norðtoftir:23 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 35 | 0 | Hatchery:35 | S03 Norðtoftir:35 | Unknown:35 |
| Reachable outside descendants | 49 | 0 | Hatchery:49 | S03 Norðtoftir:49 | Unknown:49 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 3; latest holder in selected component: 3; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 1102 | BCCB7934-E4FC-4495-849D-CA7EE606F261 | `0FAF2D76-4976-4FD0-81B8-4BE34239BE77` | `0FAF2D76-4976-4FD0-81B8-4BE34239BE77` | yes | 120997 | 12991.0 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1106 | 42921283-E0D8-44B7-9680-530FB044B9CF | `E0345455-485F-4AE9-A0DA-C48206C42F0D` | `E0345455-485F-4AE9-A0DA-C48206C42F0D` | yes | 103552 | 12705.2 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |
| 1107 | 3C05AA57-1A44-48DC-A76F-F55EE0446C57 | `296AB7B3-A3E2-4688-A078-D7F5ED096754` | `296AB7B3-A3E2-4688-A078-D7F5ED096754` | yes | 94550 | 12498.3 | 2025-10-31 00:00:00 | S03 Norðtoftir | Hatchery |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)