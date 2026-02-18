# Semantic Migration Validation Report

- Component key: `F78C939E-6282-46E9-8219-0B38550AF4BF`
- Batch: `SF SEP 24` (id=486)
- Populations: 146
- Window: 2024-09-26 11:13:31 → 2025-10-15 17:00:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1636 | 1636 | 0.00 |
| Feeding kg | 241238.68 | 241238.68 | 0.00 |
| Mortality events | 2891 | 2869 | 22.00 |
| Mortality count | 535516 | 535516 | 0.00 |
| Mortality biomass kg | 0.00 | 31140.83 | -31140.83 |
| Culling events | 882 | 882 | 0.00 |
| Culling count | 392128 | 392128 | 0.00 |
| Culling biomass kg | 11090008.32 | 11090008.31 | 0.01 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 101 | 101 | 0.00 |
| Growth samples | 122 | 122 | 0.00 |
| Health journal entries | 23 | 23 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 927644
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/3 bridge-aware (33.3%), 2/3 entry-window (66.7%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 3 total, 3 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 41.
- Fishgroup classification: 29 temporary bridge fishgroups, 80 real stage-entry fishgroups, 29 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2182000 | 0 | 2195351 | 2195351 | 1.01 | 1.0 | 2024-09-26 | 2024-09-28 | 68 | 68 | 0 | 69 | 69 |
| Fry | 799651 | 0 | 799651 | 1345111 | 1.68 | 1.68 | 2024-12-16 | 2024-12-18 | 8 | 8 | 0 | 11 | 13 |
| Parr | 1450034 | 0 | 3018652 | 8724054 | 6.02 | 2.89 | 2025-03-10 | 2025-03-12 | 3 | 3 | 0 | 46 | 46 |
| Post-Smolt | 425099 | 0 | 1525919 | 3208684 | 7.55 | 2.1 | 2025-06-20 | 2025-06-22 | 1 | 1 | 2 | 17 | 18 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2182000 | 799651 | -1382349 | 8 | 8 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 454705 |
| Fry -> Parr | 799651 | 1450034 | 650383 | 3 | 3 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Parr -> Post-Smolt | 111640 | 74128 | -37512 | 1 | 1 | yes | Bridge-aware (linked sources: 4) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `247.0082`, `247.0083`, `247.0084`, `247.0090`, `247.0094`, `247.0098`, `247.0101`, `247.0102`, `247.0103`, `247.0104`
- Real stage-entry fishgroup examples: `247.0002`, `247.0003`, `247.0004`, `247.0005`, `247.0006`, `247.0007`, `247.0008`, `247.0009`, `247.0010`, `247.0011`
- Bridge fishgroups excluded from stage-entry windows: `247.0125`, `247.0127`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 146 | 146 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1988752 |
| Fry | 88884 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 74

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 65 | Hatchery:65 | FW22 Applecross:65 |
| SourcePopBefore -> SourcePopAfter | 9 | Hatchery:9 | FW22 Applecross:9 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 74 | 0 | Hatchery:74 | FW22 Applecross:74 | Unknown:74 |
| Reachable outside descendants | 89 | 0 | Hatchery:89 | FW22 Applecross:89 | Unknown:89 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)