# Semantic Migration Validation Report

- Component key: `E84F1BB3-E175-4B25-84AC-15614864DD75`
- Batch: `Stofnfiskur S-21 juni24` (id=468)
- Populations: 265
- Window: 2024-06-12 12:55:24 → 2025-11-25 18:22:47

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3717 | 3717 | 0.00 |
| Feeding kg | 357739.61 | 357739.61 | 0.00 |
| Mortality events | 4182 | 3476 | 706.00 |
| Mortality count | 243553 | 243553 | 0.00 |
| Mortality biomass kg | 0.00 | 3436.54 | -3436.54 |
| Culling events | 195 | 195 | 0.00 |
| Culling count | 223082 | 223082 | 0.00 |
| Culling biomass kg | 3895655.96 | 3895656.02 | -0.06 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 156 | 156 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 466635
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 69 total, 66 bridge-classified, 3 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 128.
- Fishgroup classification: 137 temporary bridge fishgroups, 28 real stage-entry fishgroups, 137 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1507478 | 0 | 1507478 | 1507478 | 1.0 | 1.0 | 2024-06-12 | 2024-06-14 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1467435 | 0 | 2101047 | 2101047 | 1.43 | 1.0 | 2024-08-30 | 2024-09-01 | 6 | 6 | 3 | 9 | 12 |
| Parr | 997561 | 0 | 1240634 | 7066298 | 7.08 | 5.7 | 2024-12-09 | 2024-12-11 | 6 | 6 | 4 | 121 | 177 |
| Smolt | 78961 | 0 | 916615 | 1606383 | 20.34 | 1.75 | 2025-02-27 | 2025-03-01 | 1 | 1 | 0 | 20 | 25 |
| Post-Smolt | 410704 | 0 | 982336 | 1737146 | 4.23 | 1.77 | 2025-07-08 | 2025-07-10 | 8 | 8 | 5 | 39 | 44 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1507478 | 1507478 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1507478 | 1507478 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 134909 | 134909 | 0 | 1 | 1 | yes | Bridge-aware (linked sources: 2) | OK |
| Smolt -> Post-Smolt | 629156 | 498575 | -130581 | 8 | 8 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0008`, `242.0009`, `242.0010`, `242.0011`, `242.0012`, `242.0013`, `242.0020`, `242.0021`, `242.0022`, `242.0023`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0014`, `242.0015`, `242.0016`, `242.0017`
- Bridge fishgroups excluded from stage-entry windows: `242.0008`, `242.0009`, `242.0010`, `242.0023`, `242.0024`, `242.0030`, `242.0031`, `242.0218`, `242.0219`, `242.0220`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 265 | 265 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 1591 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 55

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 4 | Hatchery:4 | S21 Viðareiði:4 |
| SourcePopBefore -> SourcePopAfter | 51 | Hatchery:51 | S21 Viðareiði:51 |
| DestPopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 55 | 0 | Hatchery:55 | S21 Viðareiði:55 | Unknown:55 |
| Reachable outside descendants | 116 | 0 | Hatchery:116 | S21 Viðareiði:116 | Unknown:116 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)