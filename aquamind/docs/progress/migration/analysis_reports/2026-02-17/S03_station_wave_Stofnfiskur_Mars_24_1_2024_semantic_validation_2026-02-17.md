# Semantic Migration Validation Report

- Component key: `C33E2439-9E6C-4E77-88C8-0594223563AD`
- Batch: `Stofnfiskur Mars 24` (id=536)
- Populations: 128
- Window: 2024-03-06 13:29:58 → 2025-09-03 14:21:49

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3666 | 3666 | 0.00 |
| Feeding kg | 316199.13 | 316199.13 | -0.00 |
| Mortality events | 3609 | 3086 | 523.00 |
| Mortality count | 487890 | 487890 | 0.00 |
| Mortality biomass kg | 0.00 | 970.25 | -970.25 |
| Culling events | 32 | 32 | 0.00 |
| Culling count | 76941 | 76941 | 0.00 |
| Culling biomass kg | 1470478.45 | 1470478.45 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 20 | 20 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 564831
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 21 total, 20 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 48.
- Fishgroup classification: 50 temporary bridge fishgroups, 33 real stage-entry fishgroups, 50 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1761755 | 0 | 1761755 | 1761755 | 1.0 | 1.0 | 2024-03-06 | 2024-03-08 | 10 | 10 | 0 | 10 | 10 |
| Fry | 1717886 | 0 | 1717886 | 1734856 | 1.01 | 1.01 | 2024-05-16 | 2024-05-18 | 12 | 12 | 0 | 19 | 19 |
| Parr | 1222757 | 0 | 1555076 | 4155371 | 3.4 | 2.67 | 2024-08-06 | 2024-08-08 | 6 | 6 | 2 | 29 | 47 |
| Smolt | 302890 | 0 | 1277946 | 1813647 | 5.99 | 1.42 | 2024-12-17 | 2024-12-19 | 3 | 3 | 3 | 22 | 24 |
| Post-Smolt | 271071 | 0 | 1348035 | 2513424 | 9.27 | 1.86 | 2025-04-04 | 2025-04-06 | 2 | 2 | 4 | 27 | 28 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1761755 | 354920 | -1406835 | 12 | 12 | yes | Bridge-aware (linked sources: 10); lineage graph fallback used | WARN: stage drop exceeds total known removals by 842004 |
| Fry -> Parr | 354920 | 349779 | -5141 | 6 | 6 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 106179 | 89892 | -16287 | 3 | 3 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 79712 | 79712 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0024`, `241.0025`, `241.0026`, `241.0027`, `241.0028`, `241.0029`, `241.0031`, `241.0032`, `241.0034`, `241.0035`
- Real stage-entry fishgroup examples: `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0008`, `241.0009`, `241.0010`, `241.0011`
- Bridge fishgroups excluded from stage-entry windows: `241.0028`, `241.0029`, `241.0071`, `241.0072`, `241.0074`, `241.0101`, `241.0102`, `241.0103`, `241.0104`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 128 | 128 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1761755 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 53

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 10 | Hatchery:10 | S03 Norðtoftir:10 |
| SourcePopBefore -> SourcePopAfter | 43 | Hatchery:43 | S03 Norðtoftir:43 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 53 | 0 | Hatchery:53 | S03 Norðtoftir:53 | Unknown:53 |
| Reachable outside descendants | 64 | 0 | Hatchery:64 | S03 Norðtoftir:64 | Unknown:64 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)