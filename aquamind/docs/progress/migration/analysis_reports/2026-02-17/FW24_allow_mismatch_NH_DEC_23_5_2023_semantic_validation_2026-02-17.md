# Semantic Migration Validation Report

- Component key: `B8D51B2B-BA3C-4965-B8E7-07780F57F199`
- Batch: `NH DEC 23` (id=509)
- Populations: 68
- Window: 2023-12-27 12:36:47 → 2025-05-16 12:00:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 937 | 937 | 0.00 |
| Feeding kg | 102297.35 | 102297.35 | -0.00 |
| Mortality events | 1584 | 1557 | 27.00 |
| Mortality count | 279806 | 279806 | 0.00 |
| Mortality biomass kg | 0.00 | 26076.46 | -26076.46 |
| Culling events | 394 | 394 | 0.00 |
| Culling count | 422614 | 422614 | 0.00 |
| Culling biomass kg | 39806553.96 | 39806553.97 | -0.01 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 105 | 105 | 0.00 |
| Growth samples | 43 | 43 | 0.00 |
| Health journal entries | 48 | 48 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 702420
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/1 bridge-aware (100.0%), 0/1 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 6 total, 5 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 26.
- Fishgroup classification: 12 temporary bridge fishgroups, 25 real stage-entry fishgroups, 12 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 816000 | 0 | 1283888 | 4666483 | 5.72 | 3.63 | 2023-12-27 | 2023-12-29 | 24 | 24 | 0 | 56 | 62 |
| Parr | 431538 | 0 | 745917 | 1292186 | 2.99 | 1.73 | 2024-11-08 | 2024-11-10 | 1 | 1 | 2 | 6 | 6 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Parr | 111110 | 111110 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 3) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `232.0002`, `232.0003`, `235.0029`, `235.0033`, `235.0040`, `235.0041`, `235.0043`, `235.0047`, `235.0048`, `235.0049`
- Real stage-entry fishgroup examples: `232.0004`, `235.0002`, `235.0003`, `235.0004`, `235.0005`, `235.0006`, `235.0007`, `235.0008`, `235.0009`, `235.0010`
- Bridge fishgroups excluded from stage-entry windows: `232.0002`, `232.0003`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 68 | 68 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 734694 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 30

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 22 | FreshWater:22 | FW24 KinlochMoidart:22 |
| SourcePopBefore -> SourcePopAfter | 8 | FreshWater:8 | FW24 KinlochMoidart:8 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 30 | 0 | FreshWater:30 | FW24 KinlochMoidart:30 | Unknown:30 |
| Reachable outside descendants | 30 | 0 | FreshWater:30 | FW24 KinlochMoidart:30 | Unknown:30 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)