# Semantic Migration Validation Report

- Component key: `5EB7F4A5-E96F-46BF-964F-05101C02B502`
- Batch: `SF AUG 23` (id=501)
- Populations: 120
- Window: 2023-08-02 17:35:02 → 2024-09-11 23:59:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2795 | 2795 | 0.00 |
| Feeding kg | 66117.05 | 66117.05 | 0.00 |
| Mortality events | 4200 | 3813 | 387.00 |
| Mortality count | 155840 | 155840 | 0.00 |
| Mortality biomass kg | 0.00 | 4850.32 | -4850.32 |
| Culling events | 78 | 78 | 0.00 |
| Culling count | 238015 | 238015 | 0.00 |
| Culling biomass kg | 1558130.84 | 1558130.84 | -0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 189 | 189 | 0.00 |
| Growth samples | 419 | 419 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 393855
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/2 bridge-aware (100.0%), 0/2 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 8 total, 8 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 51.
- Fishgroup classification: 24 temporary bridge fishgroups, 52 real stage-entry fishgroups, 27 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1230241 | 0 | 1230241 | 1230241 | 1.0 | 1.0 | 2023-08-02 | 2023-08-04 | 32 | 32 | 0 | 32 | 32 |
| Fry | 1032741 | 0 | 1661013 | 4565695 | 4.42 | 2.75 | 2023-10-20 | 2023-10-22 | 20 | 20 | 0 | 70 | 78 |
| Parr | 284671 | 0 | 1481247 | 2019987 | 7.1 | 1.36 | 2024-06-05 | 2024-06-07 | 1 | 1 | 1 | 10 | 10 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 999571 | 884236 | -115335 | 20 | 20 | yes | Bridge-aware (linked sources: 26); lineage graph fallback used | OK |
| Fry -> Parr | 69452 | 69452 | 0 | 1 | 1 | yes | Bridge-aware (direct edge linkage; linked sources: 1) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `2315.0055`, `2315.0065`, `2315.0067`, `2315.0069`, `2315.0070`, `2315.0071`, `2315.0072`, `2315.0075`, `2315.0076`, `2315.0078`
- Real stage-entry fishgroup examples: `2315.0002`, `2315.0003`, `2315.0004`, `2315.0005`, `2315.0006`, `2315.0007`, `2315.0008`, `2315.0009`, `2315.0010`, `2315.0011`
- Bridge fishgroups excluded from stage-entry windows: `2315.0002`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 120 | 120 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 595899 |
| Fry | 226930 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 68

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 34 | Hatchery:34 | FW21 Couldoran:31, FW22 Applecross:3 |
| SourcePopBefore -> SourcePopAfter | 34 | Hatchery:34 | FW21 Couldoran:34 |
| DestPopBefore -> DestPopAfter | 3 | Hatchery:3 | FW22 Applecross:2, FW21 Couldoran:1 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 68 | 0 | Hatchery:68 | FW21 Couldoran:65, FW22 Applecross:3 | Unknown:68 |
| Reachable outside descendants | 74 | 0 | Hatchery:74 | FW21 Couldoran:71, FW22 Applecross:3 | Unknown:74 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)