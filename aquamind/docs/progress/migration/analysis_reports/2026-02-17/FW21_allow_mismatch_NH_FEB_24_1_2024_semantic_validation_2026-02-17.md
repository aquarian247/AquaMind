# Semantic Migration Validation Report

- Component key: `A75471B6-FCB1-4719-8F63-0210AF14B4BE`
- Batch: `NH FEB 24` (id=503)
- Populations: 171
- Window: 2024-02-13 14:28:57 → 2025-01-22 15:14:35

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2777 | 2777 | 0.00 |
| Feeding kg | 34440.36 | 34440.36 | 0.00 |
| Mortality events | 3544 | 3062 | 482.00 |
| Mortality count | 434918 | 434918 | 0.00 |
| Mortality biomass kg | 0.00 | 1903.09 | -1903.09 |
| Culling events | 22 | 22 | 0.00 |
| Culling count | 1261785 | 1261785 | 0.00 |
| Culling biomass kg | 24258913.00 | 24258913.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 197 | 197 | 0.00 |
| Growth samples | 267 | 267 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1696703
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 24 total, 24 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 60.
- Fishgroup classification: 44 temporary bridge fishgroups, 61 real stage-entry fishgroups, 44 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1684530 | 0 | 3060984 | 8635703 | 5.13 | 2.82 | 2024-02-13 | 2024-02-15 | 55 | 55 | 0 | 129 | 153 |
| Fry | 33910 | 0 | 66353 | 107745 | 3.18 | 1.62 | 2024-06-25 | 2024-06-27 | 4 | 4 | 0 | 15 | 15 |
| Parr | 19620 | 0 | 19802 | 19802 | 1.01 | 1.0 | 2024-08-22 | 2024-08-24 | 2 | 2 | 0 | 3 | 3 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 4153 | 4153 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Fry -> Parr | 376 | 376 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0056`, `241.0057`, `241.0079`, `241.0080`, `241.0082`, `241.0083`, `241.0084`, `241.0086`, `241.0088`, `241.0089`
- Real stage-entry fishgroup examples: `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0008`, `241.0009`, `241.0010`, `241.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 171 | 171 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1184222 |
| Fry | 124 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 77

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 49 | Hatchery:43, Unknown:6 | FW21 Couldoran:43, BRS3 Geocrab:6 |
| SourcePopBefore -> SourcePopAfter | 28 | Hatchery:28 | FW21 Couldoran:28 |
| DestPopBefore -> DestPopAfter | 1 | Unknown:1 | BRS3 Geocrab:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 77 | 0 | Hatchery:71, Unknown:6 | FW21 Couldoran:71, BRS3 Geocrab:6 | Unknown:77 |
| Reachable outside descendants | 88 | 0 | Hatchery:82, Unknown:6 | FW21 Couldoran:82, BRS3 Geocrab:6 | Unknown:88 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)