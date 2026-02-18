# Semantic Migration Validation Report

- Component key: `EE3B4977-A418-40DF-865F-19F399972770`
- Batch: `Bakkafrost feb 2024` (id=520)
- Populations: 157
- Window: 2024-02-07 08:35:28 → 2025-07-03 18:03:40

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1593 | 1593 | 0.00 |
| Feeding kg | 295980.93 | 295980.93 | 0.00 |
| Mortality events | 5597 | 3972 | 1625.00 |
| Mortality count | 412404 | 412404 | 0.00 |
| Mortality biomass kg | 0.00 | 2656.56 | -2656.56 |
| Culling events | 28 | 28 | 0.00 |
| Culling count | 395157 | 395157 | 0.00 |
| Culling biomass kg | 7326658.97 | 7326658.97 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 276 | 276 | 0.00 |
| Growth samples | 33 | 33 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 807561
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 2/4 bridge-aware (50.0%), 2/4 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 5 total, 5 bridge-classified, 0 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 60.
- Fishgroup classification: 37 temporary bridge fishgroups, 23 real stage-entry fishgroups, 37 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1440000 | 0 | 1440000 | 1440000 | 1.0 | 1.0 | 2024-02-07 | 2024-02-09 | 4 | 4 | 0 | 4 | 4 |
| Fry | 187979 | 0 | 2886137 | 4336345 | 23.07 | 1.5 | 2024-02-07 | 2024-02-09 | 8 | 8 | 0 | 59 | 59 |
| Parr | 1502466 | 0 | 2128343 | 9156901 | 6.09 | 4.3 | 2024-07-25 | 2024-07-27 | 7 | 7 | 0 | 65 | 70 |
| Smolt | 483058 | 0 | 1006153 | 1776961 | 3.68 | 1.77 | 2025-01-15 | 2025-01-17 | 2 | 2 | 3 | 12 | 12 |
| Post-Smolt | 142642 | 0 | 580742 | 754526 | 5.29 | 1.3 | 2025-03-04 | 2025-03-06 | 2 | 2 | 0 | 12 | 12 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1440000 | 187979 | -1252021 | 8 | 0 | no | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 444460 |
| Fry -> Parr | 187979 | 1502466 | 1314487 | 7 | 7 | yes | Entry window (incomplete linkage) | WARN: positive delta under incomplete linkage fallback |
| Parr -> Smolt | 283951 | 283951 | 0 | 2 | 2 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 154982 | 142642 | -12340 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `241.0071`, `241.0072`, `241.0073`, `241.0074`, `241.0075`, `241.0076`, `241.0078`, `241.0079`, `241.0081`, `241.0082`
- Real stage-entry fishgroup examples: `241.0001`, `241.0002`, `241.0003`, `241.0004`, `241.0005`, `241.0006`, `241.0007`, `241.0008`, `241.0009`, `241.0010`
- Bridge fishgroups excluded from stage-entry windows: `241.0117`, `241.0119`, `241.0120`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 157 | 157 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 501918 |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 72

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 36 | Hatchery:36 | S16 Glyvradalur:36 |
| SourcePopBefore -> SourcePopAfter | 36 | Hatchery:36 | S16 Glyvradalur:36 |
| DestPopBefore -> DestPopAfter | 4 | Hatchery:4 | S16 Glyvradalur:4 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 72 | 0 | Hatchery:72 | S16 Glyvradalur:72 | Unknown:72 |
| Reachable outside descendants | 102 | 0 | Hatchery:102 | S16 Glyvradalur:102 | Unknown:102 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 1) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)