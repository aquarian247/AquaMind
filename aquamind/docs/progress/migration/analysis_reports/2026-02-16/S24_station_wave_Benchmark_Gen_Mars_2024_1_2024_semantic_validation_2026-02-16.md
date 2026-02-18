# Semantic Migration Validation Report

- Component key: `79EB0F5F-4762-4F9B-9117-172E4905B03B`
- Batch: `Benchmark Gen. Mars 2024` (id=476)
- Populations: 256
- Window: 2024-03-13 16:00:05 → 2025-07-10 15:44:53

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4140 | 4140 | 0.00 |
| Feeding kg | 1001616.45 | 1001616.45 | -0.00 |
| Mortality events | 5525 | 5402 | 123.00 |
| Mortality count | 1424517 | 1424517 | 0.00 |
| Mortality biomass kg | 0.00 | 5921.52 | -5921.52 |
| Culling events | 14 | 14 | 0.00 |
| Culling count | 103277 | 103277 | 0.00 |
| Culling biomass kg | 2513519.00 | 2513519.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 20 | 20 | 0.00 |
| Growth samples | 470 | 470 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 1527794
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 4
- Assignment zero-count rows (population_count <= 0): 39 total, 31 bridge-classified, 8 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 61.
- Fishgroup classification: 88 temporary bridge fishgroups, 68 real stage-entry fishgroups, 88 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3501779 | 0 | 3501779 | 3501779 | 1.0 | 1.0 | 2024-03-13 | 2024-03-15 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3365522 | 0 | 3365522 | 3365522 | 1.0 | 1.0 | 2024-06-06 | 2024-06-08 | 12 | 12 | 0 | 12 | 12 |
| Parr | 2211595 | 0 | 2829997 | 6644651 | 3.0 | 2.35 | 2024-08-27 | 2024-08-29 | 9 | 9 | 12 | 37 | 62 |
| Smolt | 669800 | 0 | 2309973 | 5877097 | 8.77 | 2.54 | 2024-12-01 | 2024-12-03 | 5 | 5 | 0 | 46 | 50 |
| Post-Smolt | 448712 | 0 | 2382179 | 4610246 | 10.27 | 1.94 | 2025-01-29 | 2025-01-31 | 3 | 3 | 10 | 83 | 93 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1167265 | 89797 | -1077468 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | OK |
| Fry -> Parr | 89797 | 89797 | 0 | 9 | 9 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 28638 | 28533 | -105 | 5 | 5 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 41629 | 15797 | -25832 | 3 | 3 | yes | Bridge-aware (linked sources: 5); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0052`, `241.0053`, `241.0054`, `241.0055`, `241.0056`, `241.0057`, `241.0058`, `241.0059`, `241.0060`, `241.0061`
- Real stage-entry fishgroup examples: `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0008`, `241.0009`, `241.0010`, `241.0011`
- Bridge fishgroups excluded from stage-entry windows: `241.0053`, `241.0055`, `241.0059`, `241.0060`, `241.0061`, `241.0062`, `241.0063`, `241.0072`, `241.0074`, `241.0075`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 256 | 256 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3501779 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 79

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 40 | Hatchery:40 | S24 Strond:40 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 79 | 0 | Hatchery:79 | S24 Strond:79 | Unknown:79 |
| Reachable outside descendants | 164 | 0 | Hatchery:164 | S24 Strond:164 | Unknown:164 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)