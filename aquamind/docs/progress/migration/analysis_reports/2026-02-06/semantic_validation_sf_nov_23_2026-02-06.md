# Semantic Migration Validation Report

- Component key: `FA8EA452-AFE1-490D-B236-0150415B6E6F`
- Batch: `SF NOV 23` (id=354)
- Populations: 130
- Window: 2023-11-16 15:11:07 → 2024-12-30 15:28:33

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1723 | 1723 | 0.00 |
| Feeding kg | 171029.18 | 171029.18 | 0.00 |
| Mortality events | 2837 | 2719 | 118.00 |
| Mortality count | 572964 | 572964 | 0.00 |
| Mortality biomass kg | 0.00 | 40402.66 | -40402.66 |
| Culling events | 709 | 709 | 0.00 |
| Culling count | 422531 | 422531 | 0.00 |
| Culling biomass kg | 23168970.19 | 23168970.15 | 0.04 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 140 | 140 | 0.00 |
| Growth samples | 159 | 159 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 306128 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 995495
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/3 bridge-aware (66.7%), 1/3 entry-window (33.3%).
- Assignment zero-count rows (population_count <= 0): 13 total, 12 bridge-classified, 1 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 44.
- Fishgroup classification: 32 temporary bridge fishgroups, 64 real stage-entry fishgroups, 32 temporary bridge populations.

| Stage | Entry population | Full summed population | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1676462 | 1710947 | 2023-11-16 | 2023-11-18 | 52 | 52 | 0 | 54 | 54 |
| Fry | 506626 | 506626 | 2024-02-05 | 2024-02-07 | 8 | 8 | 0 | 8 | 8 |
| Parr | 1123982 | 7451303 | 2024-05-07 | 2024-05-09 | 3 | 3 | 0 | 51 | 64 |
| Post-Smolt | 173939 | 494032 | 2024-10-24 | 2024-10-26 | 1 | 1 | 1 | 4 | 4 |

- Transition deltas below use fishgroup bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1676462 | 506626 | -1169836 | 8 | 8 | yes | Entry window (no bridge path) | WARN: stage drop exceeds total known removals by 174341 |
| Fry -> Parr | 391510 | 391510 | 0 | 3 | 3 | yes | Fishgroup bridge-aware (linked sources: 6) | OK |
| Parr -> Post-Smolt | 271029 | 271029 | 0 | 1 | 1 | yes | Fishgroup bridge-aware (linked sources: 2) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `235.0055`, `235.0064`, `235.0065`, `235.0067`, `235.0072`, `235.0073`, `235.0074`, `235.0075`, `235.0076`, `235.0077`
- Real stage-entry fishgroup examples: `235.0001`, `235.0002`, `235.0003`, `235.0004`, `235.0005`, `235.0006`, `235.0007`, `235.0008`, `235.0009`, `235.0010`
- Bridge fishgroups excluded from stage-entry windows: `235.0127`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 130 | 130 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1605410 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 and not classified as temporary bridge: 1 (threshold: 2) |
- Overall gate result: PASS (enforced)