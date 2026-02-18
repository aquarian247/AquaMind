# Semantic Migration Validation Report

- Component key: `533595CB-E74C-4357-8C66-2A1C8C81DC9E`
- Batch: `24Q1 LHS` (id=507)
- Populations: 79
- Window: 2023-08-02 20:59:09 → 2024-03-01 14:41:43

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1237 | 1237 | 0.00 |
| Feeding kg | 51422.90 | 51422.90 | -0.00 |
| Mortality events | 1358 | 1063 | 295.00 |
| Mortality count | 53702 | 53702 | 0.00 |
| Mortality biomass kg | 0.00 | 5058.16 | -5058.16 |
| Culling events | 131 | 131 | 0.00 |
| Culling count | 107995 | 107995 | 0.00 |
| Culling biomass kg | 7419605.31 | 7419605.30 | 0.01 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 75 | 75 | 0.00 |
| Growth samples | 59 | 59 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 161697
- Stage-entry window used for transition sanity: 2 day(s)
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 6 total, 5 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 32.
- Fishgroup classification: 27 temporary bridge fishgroups, 5 real stage-entry fishgroups, 29 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Parr | 636156 | 0 | 1389417 | 4733884 | 7.44 | 3.41 | 2023-08-02 | 2023-08-04 | 5 | 5 | 0 | 73 | 79 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0009`, `241.0012`, `241.0014`, `241.0022`, `241.0024`, `241.0026`, `241.0031`, `241.0035`, `241.0036`, `241.0037`
- Real stage-entry fishgroup examples: `241.0008`, `241.0010`, `241.0013`, `241.0016`, `241.0017`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 79 | 79 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 77536 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 25

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 7 | FreshWater:6, Hatchery:1 | FW24 KinlochMoidart:6, FW22 Applecross:1 |
| SourcePopBefore -> SourcePopAfter | 16 | FreshWater:16 | FW24 KinlochMoidart:16 |
| DestPopBefore -> DestPopAfter | 5 | FreshWater:4, Hatchery:1 | FW24 KinlochMoidart:4, FW22 Applecross:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 25 | 0 | FreshWater:24, Hatchery:1 | FW24 KinlochMoidart:24, FW22 Applecross:1 | Unknown:25 |
| Reachable outside descendants | 37 | 0 | FreshWater:36, Hatchery:1 | FW24 KinlochMoidart:36, FW22 Applecross:1 | Unknown:37 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)