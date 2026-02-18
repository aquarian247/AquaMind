# Semantic Migration Validation Report

- Component key: `AE4B5246-AA42-48FF-A7AF-0610F3F55752`
- Batch: `SF MAY 24 3` (id=512)
- Populations: 110
- Window: 2024-05-09 08:05:03 → 2025-08-05 08:11:42

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1516 | 1516 | 0.00 |
| Feeding kg | 120285.75 | 120285.75 | 0.00 |
| Mortality events | 2210 | 2193 | 17.00 |
| Mortality count | 565333 | 565333 | 0.00 |
| Mortality biomass kg | 0.00 | 35774.93 | -35774.93 |
| Culling events | 538 | 537 | 1.00 |
| Culling count | 491533 | 491533 | 0.00 |
| Culling biomass kg | 6587876.48 | 6587876.37 | 0.11 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 99 | 99 | 0.00 |
| Growth samples | 103 | 103 | 0.00 |
| Health journal entries | 97 | 97 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1056866
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/1 bridge-aware (0.0%), 1/1 entry-window (100.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 3 total, 2 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 34.
- Fishgroup classification: 14 temporary bridge fishgroups, 50 real stage-entry fishgroups, 14 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1600205 | 0 | 2233085 | 2846049 | 1.78 | 1.27 | 2024-05-09 | 2024-05-11 | 49 | 49 | 0 | 59 | 59 |
| Parr | 475983 | 0 | 2181634 | 8334805 | 17.51 | 3.82 | 2024-11-08 | 2024-11-10 | 1 | 1 | 0 | 48 | 51 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Parr | 1600205 | 475983 | -1124222 | 1 | 1 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 67356 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0063`, `243.0064`, `243.0069`, `243.0070`, `243.0071`, `243.0072`, `243.0073`, `243.0075`, `243.0079`, `243.0083`
- Real stage-entry fishgroup examples: `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`, `243.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 110 | 110 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1478905 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 57

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 47 | FreshWater:47 | FW24 KinlochMoidart:47 |
| SourcePopBefore -> SourcePopAfter | 10 | FreshWater:10 | FW24 KinlochMoidart:10 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 57 | 0 | FreshWater:57 | FW24 KinlochMoidart:57 | Unknown:57 |
| Reachable outside descendants | 63 | 0 | FreshWater:63 | FW24 KinlochMoidart:63 | Unknown:63 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)