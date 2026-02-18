# Semantic Migration Validation Report

- Component key: `E8FE9380-69EE-4D31-864D-0387E9880FB5`
- Batch: `SF MAY 24` (id=485)
- Populations: 148
- Window: 2024-05-30 11:02:43 → 2025-09-09 17:00:00

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1817 | 1817 | 0.00 |
| Feeding kg | 401435.75 | 401435.75 | 0.00 |
| Mortality events | 3605 | 3529 | 76.00 |
| Mortality count | 555677 | 555677 | 0.00 |
| Mortality biomass kg | 0.00 | 74538.25 | -74538.25 |
| Culling events | 1067 | 1067 | 0.00 |
| Culling count | 659869 | 659869 | 0.00 |
| Culling biomass kg | 65752323.89 | 65752323.82 | 0.07 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 79 | 79 | 0.00 |
| Growth samples | 123 | 123 | 0.00 |
| Health journal entries | 232 | 232 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1215546
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 3 total, 3 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 45.
- Fishgroup classification: 22 temporary bridge fishgroups, 78 real stage-entry fishgroups, 22 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 2182000 | 0 | 2200360 | 2213644 | 1.01 | 1.01 | 2024-05-30 | 2024-06-01 | 65 | 65 | 0 | 67 | 67 |
| Fry | 723212 | 0 | 723212 | 723212 | 1.0 | 1.0 | 2024-09-10 | 2024-09-12 | 8 | 8 | 0 | 8 | 8 |
| Parr | 1413974 | 0 | 2758957 | 9282485 | 6.56 | 3.36 | 2024-11-25 | 2024-11-27 | 3 | 3 | 2 | 52 | 55 |
| Post-Smolt | 106210 | 0 | 1566712 | 2257602 | 21.26 | 1.44 | 2025-05-06 | 2025-05-08 | 2 | 2 | 0 | 18 | 18 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 2182000 | 723212 | -1458788 | 8 | 8 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 243242 |
| Fry -> Parr | 190551 | 190551 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 6) | OK |
| Parr -> Post-Smolt | 105418 | 19295 | -86123 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `246.0076`, `246.0078`, `246.0080`, `246.0082`, `246.0087`, `246.0093`, `246.0094`, `246.0098`, `246.0099`, `246.0101`
- Real stage-entry fishgroup examples: `246.0002`, `246.0003`, `246.0004`, `246.0005`, `246.0006`, `246.0007`, `246.0008`, `246.0009`, `246.0012`, `246.0013`
- Bridge fishgroups excluded from stage-entry windows: `246.0080`, `246.0082`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 148 | 148 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1973059 |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 75

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 60 | Hatchery:60 | FW22 Applecross:60 |
| SourcePopBefore -> SourcePopAfter | 15 | Hatchery:15 | FW22 Applecross:15 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 75 | 0 | Hatchery:75 | FW22 Applecross:75 | Unknown:75 |
| Reachable outside descendants | 86 | 0 | Hatchery:86 | FW22 Applecross:86 | Unknown:86 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)