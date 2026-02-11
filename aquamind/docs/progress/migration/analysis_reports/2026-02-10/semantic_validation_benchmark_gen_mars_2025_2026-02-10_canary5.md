# Semantic Migration Validation Report

- Component key: `CE636015-595A-44BD-AB37-03B4018FBA4A`
- Batch: `Benchmark Gen. Mars 2025` (id=377)
- Populations: 252
- Window: 2025-03-12 12:20:55 → 2026-02-10 20:56:30.496313

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1962 | 1962 | 0.00 |
| Feeding kg | 89461.27 | 89461.27 | -0.00 |
| Mortality events | 2759 | 2715 | 44.00 |
| Mortality count | 906275 | 906275 | 0.00 |
| Mortality biomass kg | 0.00 | 588.27 | -588.27 |
| Culling events | 17 | 17 | 0.00 |
| Culling count | 73532 | 73532 | 0.00 |
| Culling biomass kg | 1478216.00 | 1478216.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 16 | 16 | 0.00 |
| Growth samples | 210 | 210 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 979807
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/4 bridge-aware (25.0%), 3/4 entry-window (75.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 1
- Assignment zero-count rows (population_count <= 0): 165 total, 62 bridge-classified, 1 same-stage superseded-zero, 57 short-lived orphan-zero, 45 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 54.
- Fishgroup classification: 81 temporary bridge fishgroups, 62 real stage-entry fishgroups, 81 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3293331 | 0 | 3293331 | 3293331 | 1.0 | 1.0 | 2025-03-12 | 2025-03-14 | 39 | 39 | 0 | 39 | 39 |
| Fry | 2817176 | 0 | 3249556 | 3249556 | 1.15 | 1.0 | 2025-06-04 | 2025-06-06 | 12 | 12 | 2 | 14 | 48 |
| Parr | 3280531 | 0 | 4050392 | 6048117 | 1.84 | 1.49 | 2025-08-25 | 2025-08-27 | 11 | 11 | 11 | 34 | 98 |
| Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 65 |
| Post-Smolt | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 2 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 3293331 | 2817176 | -476155 | 12 | 12 | yes | Entry window (incomplete linkage) | OK |
| Fry -> Parr | 3500200 | 3500200 | 0 | 11 | 11 | yes | Bridge-aware (linked sources: 12); lineage graph fallback used | OK |
| Parr -> Smolt | 3280531 | 0 | -3280531 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 2300724 |
| Smolt -> Post-Smolt | 0 | 0 | 0 | 0 | 0 | no | Entry window (no entry populations) | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `251.0040`, `251.0042`, `251.0043`, `251.0044`, `251.0045`, `251.0046`, `251.0047`, `251.0048`, `251.0049`, `251.0050`
- Real stage-entry fishgroup examples: `251.0002`, `251.0003`, `251.0004`, `251.0005`, `251.0006`, `251.0007`, `251.0008`, `251.0009`, `251.0010`, `251.0011`
- Bridge fishgroups excluded from stage-entry windows: `251.0055`, `251.0067`, `251.0088`, `251.0092`, `251.0099`, `251.0100`, `251.0101`, `251.0102`, `251.0106`, `251.0109`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 252 | 252 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 18

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 18 | Hatchery:18 | S24 Strond:18 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 18 | 0 | Hatchery:18 | S24 Strond:18 | Unknown:18 |
| Reachable outside descendants | 56 | 0 | Hatchery:56 | S24 Strond:56 | Unknown:56 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | FAIL | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, and short-lived orphan-zero rows: 45 (threshold: 2) |
- Overall gate result: FAIL (enforced)