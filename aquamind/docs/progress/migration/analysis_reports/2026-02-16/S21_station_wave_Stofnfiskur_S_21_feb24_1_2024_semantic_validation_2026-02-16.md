# Semantic Migration Validation Report

- Component key: `BC782146-C921-4AD1-8021-0E1ED2228D7C`
- Batch: `Stofnfiskur S-21 feb24` (id=467)
- Populations: 253
- Window: 2024-02-21 10:00:35 → 2025-08-13 17:38:09

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3418 | 3418 | 0.00 |
| Feeding kg | 288478.52 | 288478.52 | 0.00 |
| Mortality events | 3890 | 3159 | 731.00 |
| Mortality count | 314374 | 314374 | 0.00 |
| Mortality biomass kg | 0.00 | 2454.91 | -2454.91 |
| Culling events | 99 | 99 | 0.00 |
| Culling count | 161574 | 161574 | 0.00 |
| Culling biomass kg | 2162567.31 | 2162567.32 | -0.01 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 26 | 26 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 475948
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 64 total, 63 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 107.
- Fishgroup classification: 104 temporary bridge fishgroups, 26 real stage-entry fishgroups, 104 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501655 | 0 | 1501655 | 1501655 | 1.0 | 1.0 | 2024-02-21 | 2024-02-23 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1481684 | 0 | 1481684 | 1481684 | 1.0 | 1.0 | 2024-05-23 | 2024-05-25 | 6 | 6 | 0 | 6 | 11 |
| Parr | 252997 | 0 | 1185836 | 6417342 | 25.37 | 5.41 | 2024-08-23 | 2024-08-25 | 3 | 3 | 0 | 108 | 151 |
| Smolt | 170884 | 0 | 1152104 | 2098342 | 12.28 | 1.82 | 2024-11-18 | 2024-11-20 | 2 | 2 | 1 | 21 | 25 |
| Post-Smolt | 341385 | 0 | 1101719 | 2163164 | 6.34 | 1.96 | 2025-04-01 | 2025-04-03 | 8 | 8 | 6 | 47 | 59 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501655 | 1501655 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 494253 | 494253 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |
| Parr -> Smolt | 345470 | 345470 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 3) | OK |
| Smolt -> Post-Smolt | 688523 | 655819 | -32704 | 8 | 8 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0008`, `241.0009`, `241.0010`, `241.0011`, `241.0012`, `241.0019`, `241.0020`, `241.0021`, `241.0025`, `241.0026`
- Real stage-entry fishgroup examples: `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0013`, `241.0014`, `241.0015`, `241.0016`
- Bridge fishgroups excluded from stage-entry windows: `241.0097`, `241.0183`, `241.0184`, `241.0185`, `241.0194`, `241.0196`, `241.0198`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 253 | 253 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 8532 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 49

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |
| SourcePopBefore -> SourcePopAfter | 47 | Hatchery:47 | S21 Viðareiði:47 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 49 | 0 | Hatchery:49 | S21 Viðareiði:49 | Unknown:49 |
| Reachable outside descendants | 129 | 0 | Hatchery:129 | S21 Viðareiði:129 | Unknown:129 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)