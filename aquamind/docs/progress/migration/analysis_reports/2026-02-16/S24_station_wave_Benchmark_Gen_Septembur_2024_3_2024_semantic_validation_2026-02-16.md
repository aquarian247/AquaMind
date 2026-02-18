# Semantic Migration Validation Report

- Component key: `65370D45-A30A-4810-B8F0-06FE2DB4A001`
- Batch: `Benchmark Gen. Septembur 2024` (id=478)
- Populations: 162
- Window: 2024-09-18 11:20:02 → 2026-01-10 10:20:49

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2076 | 2076 | 0.00 |
| Feeding kg | 329102.94 | 329102.94 | 0.00 |
| Mortality events | 3190 | 3149 | 41.00 |
| Mortality count | 2432125 | 2432125 | 0.00 |
| Mortality biomass kg | 0.00 | 7844.20 | -7844.20 |
| Culling events | 7 | 7 | 0.00 |
| Culling count | 84878 | 84878 | 0.00 |
| Culling biomass kg | 5615642.60 | 5615642.60 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 14 | 14 | 0.00 |
| Growth samples | 241 | 241 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 2517003
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 21 total, 19 bridge-classified, 2 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 41.
- Fishgroup classification: 30 temporary bridge fishgroups, 62 real stage-entry fishgroups, 30 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500000 | 0 | 3500000 | 3500000 | 1.0 | 1.0 | 2024-09-18 | 2024-09-20 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3397931 | 0 | 3397931 | 3397931 | 1.0 | 1.0 | 2024-12-12 | 2024-12-14 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1130923 | 0 | 2093734 | 5356780 | 4.74 | 2.56 | 2025-02-11 | 2025-02-13 | 3 | 3 | 2 | 31 | 50 |
| Smolt | 378666 | 0 | 1461837 | 2954008 | 7.8 | 2.02 | 2025-06-17 | 2025-06-19 | 4 | 4 | 3 | 26 | 26 |
| Post-Smolt | 523907 | 0 | 1114256 | 1752635 | 3.35 | 1.57 | 2025-09-24 | 2025-09-26 | 4 | 4 | 3 | 33 | 35 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1166664 | 89744 | -1076920 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | OK |
| Fry -> Parr | 89744 | 89744 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 39133 | 29190 | -9943 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 44660 | 41895 | -2765 | 4 | 4 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `243.0042`, `243.0052`, `243.0053`, `243.0054`, `243.0055`, `243.0056`, `243.0057`, `243.0059`, `243.0061`, `243.0062`
- Real stage-entry fishgroup examples: `243.0001`, `243.0002`, `243.0003`, `243.0004`, `243.0005`, `243.0006`, `243.0007`, `243.0008`, `243.0009`, `243.0010`
- Bridge fishgroups excluded from stage-entry windows: `243.0056`, `243.0059`, `243.0094`, `243.0095`, `243.0096`, `243.0126`, `243.0127`, `243.0128`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 162 | 162 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500000 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 69

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 30 | Hatchery:30 | S24 Strond:30 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 69 | 0 | Hatchery:69 | S24 Strond:69 | Unknown:69 |
| Reachable outside descendants | 110 | 0 | Hatchery:110 | S24 Strond:110 | Unknown:110 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)