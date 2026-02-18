# Semantic Migration Validation Report

- Component key: `A61AA1A5-768D-487F-BB62-04C8B23B9FD7`
- Batch: `SF SEP 23` (id=508)
- Populations: 65
- Window: 2023-09-20 15:43:56 → 2024-08-26 15:45:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 888 | 888 | 0.00 |
| Feeding kg | 41787.32 | 41787.32 | 0.00 |
| Mortality events | 1822 | 1239 | 583.00 |
| Mortality count | 84598 | 84598 | 0.00 |
| Mortality biomass kg | 0.00 | 1333.75 | -1333.75 |
| Culling events | 370 | 370 | 0.00 |
| Culling count | 151387 | 151387 | 0.00 |
| Culling biomass kg | 2318350.54 | 2318352.24 | -1.70 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 93 | 93 | 0.00 |
| Growth samples | 67 | 67 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 235985
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/2 bridge-aware (0.0%), 2/2 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 1 total, 1 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 25.
- Fishgroup classification: 7 temporary bridge fishgroups, 24 real stage-entry fishgroups, 10 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 803969 | 0 | 1584211 | 4653866 | 5.79 | 2.94 | 2023-09-20 | 2023-09-22 | 23 | 23 | 0 | 56 | 57 |
| Parr | 430391 | 0 | 774129 | 872175 | 2.03 | 1.13 | 2024-07-18 | 2024-07-20 | 1 | 1 | 1 | 4 | 4 |
| Smolt | 82450 | 0 | 341603 | 424053 | 5.14 | 1.24 | 2024-07-11 | 2024-07-13 | 2 | 2 | 2 | 4 | 4 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Parr | 803969 | 430391 | -373578 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 137593 |
| Parr -> Smolt | 430391 | 82450 | -347941 | 2 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 111956 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0029`, `234.0035`, `234.0040`, `234.0041`, `234.0043`, `234.0049`, `234.0052`
- Real stage-entry fishgroup examples: `234.0001`, `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`
- Bridge fishgroups excluded from stage-entry windows: `234.0002`, `234.0003`, `234.0006`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 65 | 65 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 719431 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 29

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 22 | FreshWater:22 | FW24 KinlochMoidart:22 |
| SourcePopBefore -> SourcePopAfter | 7 | FreshWater:7 | FW24 KinlochMoidart:7 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 29 | 0 | FreshWater:29 | FW24 KinlochMoidart:29 | Unknown:29 |
| Reachable outside descendants | 33 | 0 | FreshWater:33 | FW24 KinlochMoidart:33 | Unknown:33 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)