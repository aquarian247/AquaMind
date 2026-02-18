# Semantic Migration Validation Report

- Component key: `1A7421E3-6F19-4BEC-8749-00EC01B61CB7`
- Batch: `SF JUN 25` (id=497)
- Populations: 56
- Window: 2025-06-05 10:30:00 → 2026-01-22 23:59:59.999999 (uncapped end 2026-02-16 18:25:40.964624, cap 2026-01-22 23:59:59.999999)

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 120 | 120 | 0.00 |
| Feeding kg | 672.99 | 672.99 | 0.00 |
| Mortality events | 1478 | 1453 | 25.00 |
| Mortality count | 72989 | 72989 | 0.00 |
| Mortality biomass kg | 0.00 | 24.11 | -24.11 |
| Culling events | 202 | 201 | 1.00 |
| Culling count | 1165974 | 1165974 | 0.00 |
| Culling biomass kg | 11658.40 | 11658.37 | 0.03 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 4 | 4 | 0.00 |
| Growth samples | 12 | 12 | 0.00 |
| Health journal entries | 2 | 2 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1238963
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 1 total, 1 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 4.
- Fishgroup classification: 1 temporary bridge fishgroups, 52 real stage-entry fishgroups, 1 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1637150 | 245495 | 1653378 | 1898873 | 1.16 | 1.15 | 2025-06-05 | 2025-06-07 | 50 | 50 | 0 | 53 | 53 |
| Fry | 286259 | 0 | 286259 | 286259 | 1.0 | 1.0 | 2025-08-28 | 2025-08-30 | 2 | 2 | 0 | 2 | 3 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1637150 | 286259 | -1350891 | 2 | 2 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 111928 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `252.0052`
- Real stage-entry fishgroup examples: `252.0002`, `252.0003`, `252.0004`, `252.0005`, `252.0006`, `252.0007`, `252.0008`, `252.0009`, `252.0010`, `252.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 56 | 56 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1575483 |
| Fry | 23143 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 51

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 49 | Hatchery:48, Unknown:1 | FW22 Applecross:48, Unknown:1 |
| SourcePopBefore -> SourcePopAfter | 2 | Hatchery:2 | FW22 Applecross:2 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 51 | 0 | Hatchery:50, Unknown:1 | FW22 Applecross:50, Unknown:1 | Unknown:51 |
| Reachable outside descendants | 51 | 0 | Hatchery:50, Unknown:1 | FW22 Applecross:50, Unknown:1 | Unknown:51 |

### Active Container Latest Holder Evidence

- For each currently active migrated assignment container, this shows the latest non-zero status holder in source data.
- Containers checked: 2; latest holder in selected component: 2; latest holder outside selected component: 0; unknown latest holder: 0.

| Container | Source container id | Component population | Latest holder population | Latest holder in selected component | Latest count | Latest biomass kg | Latest status time | Site | Prod stage |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| 16DB6DDE-49CD-4A4F-BD0F-C50FA604C2F2 | 16DB6DDE-49CD-4A4F-BD0F-C50FA604C2F2 | `A80237F6-7643-4D2E-ABC9-912020847B72` | `A80237F6-7643-4D2E-ABC9-912020847B72` | yes | 108679 | 3759.81 | 2026-01-22 00:00:00 | Unknown | Unknown |
| F88E1BFA-2FD4-49A3-9422-746AD1B5502C | F88E1BFA-2FD4-49A3-9422-746AD1B5502C | `2F0DEE2B-63A2-4C72-8A80-41E2863A6A3B` | `2F0DEE2B-63A2-4C72-8A80-41E2863A6A3B` | yes | 136816 | 3019.16 | 2026-01-22 00:00:00 | Unknown | Unknown |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)