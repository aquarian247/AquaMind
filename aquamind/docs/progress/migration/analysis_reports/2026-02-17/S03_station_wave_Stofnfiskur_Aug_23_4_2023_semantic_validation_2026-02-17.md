# Semantic Migration Validation Report

- Component key: `47F8F17B-6E80-48E2-9454-023FBFC9F9EF`
- Batch: `Stofnfiskur Aug 23` (id=532)
- Populations: 166
- Window: 2023-08-23 09:38:16 → 2024-12-30 09:59:12

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3320 | 3320 | 0.00 |
| Feeding kg | 467997.01 | 467997.01 | -0.00 |
| Mortality events | 3557 | 3187 | 370.00 |
| Mortality count | 247319 | 247319 | 0.00 |
| Mortality biomass kg | 0.00 | 3722.85 | -3722.85 |
| Culling events | 31 | 31 | 0.00 |
| Culling count | 115420 | 115420 | 0.00 |
| Culling biomass kg | 1850968.72 | 1850968.72 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 33 | 33 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 362739
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 21 total, 17 bridge-classified, 4 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 55.
- Fishgroup classification: 52 temporary bridge fishgroups, 31 real stage-entry fishgroups, 52 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1767975 | 0 | 1767975 | 1767975 | 1.0 | 1.0 | 2023-08-23 | 2023-08-25 | 12 | 12 | 0 | 12 | 12 |
| Fry | 1728350 | 0 | 1728350 | 1765134 | 1.02 | 1.02 | 2023-11-28 | 2023-11-30 | 10 | 10 | 0 | 15 | 15 |
| Parr | 607964 | 0 | 2008623 | 5897336 | 9.7 | 2.94 | 2024-02-07 | 2024-02-09 | 4 | 4 | 0 | 46 | 59 |
| Smolt | 248613 | 0 | 1360379 | 2670137 | 10.74 | 1.96 | 2024-06-07 | 2024-06-09 | 3 | 3 | 0 | 30 | 32 |
| Post-Smolt | 329968 | 0 | 1420944 | 3037411 | 9.21 | 2.14 | 2024-07-11 | 2024-07-13 | 2 | 2 | 2 | 42 | 48 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1767975 | 294662 | -1473313 | 10 | 10 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | WARN: stage drop exceeds total known removals by 1110574 |
| Fry -> Parr | 117864 | 117864 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Parr -> Smolt | 48969 | 35642 | -13327 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 33726 | 33726 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0016`, `234.0023`, `234.0024`, `234.0026`, `234.0027`, `234.0033`, `234.0038`, `234.0039`, `234.0041`, `234.0042`
- Real stage-entry fishgroup examples: `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`, `234.0011`
- Bridge fishgroups excluded from stage-entry windows: `23C.0005`, `23C.0006`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 166 | 166 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1767975 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 59

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 12 | Hatchery:12 | S03 Norðtoftir:12 |
| SourcePopBefore -> SourcePopAfter | 47 | Hatchery:47 | S03 Norðtoftir:47 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 59 | 0 | Hatchery:59 | S03 Norðtoftir:59 | Unknown:59 |
| Reachable outside descendants | 68 | 0 | Hatchery:68 | S03 Norðtoftir:68 | Unknown:68 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)