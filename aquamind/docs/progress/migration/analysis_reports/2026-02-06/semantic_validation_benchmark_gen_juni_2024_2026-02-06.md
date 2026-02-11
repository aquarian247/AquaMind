# Semantic Migration Validation Report

- Component key: `5DC4DA59-A891-4BBB-BB2E-0CC95C633F20`
- Batch: `Benchmark Gen. Juni 2024` (id=355)
- Populations: 359
- Window: 2024-06-13 07:33:41 → 2025-11-10 14:47:52

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 5212 | 5212 | 0.00 |
| Feeding kg | 1312139.56 | 1312139.56 | -0.00 |
| Mortality events | 6784 | 6649 | 135.00 |
| Mortality count | 535109 | 535109 | 0.00 |
| Mortality biomass kg | 0.00 | 13508.01 | -13508.01 |
| Culling events | 25 | 25 | 0.00 |
| Culling count | 137377 | 137377 | 0.00 |
| Culling biomass kg | 4242656.00 | 4242656.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 122 | 122 | 0.00 |
| Growth samples | 607 | 607 | 0.00 |
| Health journal entries | 0 | 0 | 0.00 |
| Lice samples | 0 | 0 | 0.00 |
| Lice data rows | 0 | 0 | 0.00 |
| Lice total count | 0 | 0 | 0.00 |
| Fish sampled (lice) | 0 | 0 | 0.00 |
| Environmental readings | n/a (sqlite) | 671654 | n/a |
| Harvest rows | 0 | 0 | 0.00 |
| Harvest events | n/a | 0 | n/a |
| Harvest count | 0 | 0 | 0.00 |
| Harvest live kg | 0.00 | 0.00 | 0.00 |
| Harvest gutted kg | 0.00 | 0.00 | 0.00 |

## Lifecycle Stage Sanity

- Mixed-batch composition rows: 0
- Known removal count (mortality + culling + escapes + harvest): 672486
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 0/4 bridge-aware (0.0%), 4/4 entry-window (100.0%).
- Assignment zero-count rows (population_count <= 0): 229 total, 123 bridge-classified, 106 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 87.
- Fishgroup classification: 123 temporary bridge fishgroups, 55 real stage-entry fishgroups, 123 temporary bridge populations.

| Stage | Entry population | Full summed population | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3500000 | 3500000 | 2024-06-13 | 2024-06-15 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3387493 | 3387493 | 2024-09-04 | 2024-09-06 | 12 | 12 | 0 | 12 | 12 |
| Parr | 562120 | 3003431 | 2024-12-05 | 2024-12-07 | 2 | 2 | 0 | 21 | 127 |
| Smolt | 229485 | 2966593 | 2025-02-07 | 2025-02-09 | 1 | 1 | 0 | 17 | 78 |
| Post-Smolt | 131378 | 2404963 | 2025-07-18 | 2025-07-20 | 1 | 1 | 0 | 41 | 103 |

- Transition deltas below use fishgroup bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 3500000 | 3387493 | -112507 | 12 | 0 | no | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 3387493 | 562120 | -2825373 | 2 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 2152887 |
| Parr -> Smolt | 562120 | 229485 | -332635 | 1 | 1 | yes | Entry window (no bridge path) | OK |
| Smolt -> Post-Smolt | 229485 | 131378 | -98107 | 1 | 0 | no | Entry window (incomplete linkage) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `242.0052`, `242.0053`, `242.0054`, `242.0055`, `242.0056`, `242.0057`, `242.0058`, `242.0059`, `242.0060`, `242.0061`
- Real stage-entry fishgroup examples: `242.0002`, `242.0003`, `242.0004`, `242.0005`, `242.0006`, `242.0007`, `242.0008`, `242.0009`, `242.0010`, `242.0011`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 359 | 359 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3500000 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | FAIL | Assignments with population_count <= 0 and not classified as temporary bridge: 106 (threshold: 2) |
- Overall gate result: FAIL (enforced)