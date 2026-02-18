# Semantic Migration Validation Report

- Component key: `7B085E67-2317-483C-A01E-007DDECB8269`
- Batch: `Stofnfiskur Septembur 2023` (id=474)
- Populations: 403
- Window: 2023-09-08 08:43:33 → 2024-12-18 18:11:44

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 4475 | 4475 | 0.00 |
| Feeding kg | 1161610.14 | 1161610.15 | -0.00 |
| Mortality events | 6043 | 5913 | 130.00 |
| Mortality count | 567402 | 567402 | 0.00 |
| Mortality biomass kg | 0.00 | 15592.09 | -15592.09 |
| Culling events | 30 | 30 | 0.00 |
| Culling count | 245655 | 245655 | 0.00 |
| Culling biomass kg | 4908966.73 | 4908966.73 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 36 | 36 | 0.00 |
| Growth samples | 502 | 502 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 813057
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 70 total, 45 bridge-classified, 25 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 114.
- Fishgroup classification: 128 temporary bridge fishgroups, 65 real stage-entry fishgroups, 128 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 3466253 | 0 | 3466253 | 3466253 | 1.0 | 1.0 | 2023-09-08 | 2023-09-10 | 39 | 39 | 0 | 39 | 39 |
| Fry | 3358496 | 0 | 3358496 | 3358496 | 1.0 | 1.0 | 2023-11-29 | 2023-12-01 | 12 | 12 | 0 | 12 | 12 |
| Parr | 1864274 | 0 | 4061669 | 13886273 | 7.45 | 3.42 | 2024-02-14 | 2024-02-16 | 8 | 8 | 6 | 85 | 117 |
| Smolt | 581459 | 0 | 3068323 | 11460482 | 19.71 | 3.74 | 2024-05-17 | 2024-05-19 | 4 | 4 | 6 | 75 | 78 |
| Post-Smolt | 276975 | 0 | 2538464 | 6708272 | 24.22 | 2.64 | 2024-07-26 | 2024-07-28 | 2 | 2 | 4 | 122 | 157 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1155414 | 88878 | -1066536 | 12 | 12 | yes | Bridge-aware (linked sources: 13); lineage graph fallback used | WARN: stage drop exceeds total known removals by 253479 |
| Fry -> Parr | 59251 | 59251 | 0 | 8 | 8 | yes | Bridge-aware (linked sources: 8); lineage graph fallback used | OK |
| Parr -> Smolt | 1864274 | 581459 | -1282815 | 4 | 4 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 469758 |
| Smolt -> Post-Smolt | 47745 | 8797 | -38948 | 2 | 2 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `233.0042`, `233.0052`, `233.0053`, `233.0054`, `233.0055`, `233.0056`, `233.0057`, `233.0058`, `233.0059`, `233.0060`
- Real stage-entry fishgroup examples: `233.0002`, `233.0003`, `233.0004`, `233.0005`, `233.0006`, `233.0007`, `233.0008`, `233.0009`, `233.0010`, `233.0011`
- Bridge fishgroups excluded from stage-entry windows: `233.0042`, `233.0059`, `233.0063`, `233.0065`, `233.0073`, `233.0074`, `233.0146`, `233.0147`, `233.0148`, `233.0150`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 403 | 403 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 3466253 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 104

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 39 | Hatchery:39 | S24 Strond:39 |
| SourcePopBefore -> SourcePopAfter | 65 | Hatchery:65 | S24 Strond:65 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 104 | 0 | Hatchery:104 | S24 Strond:104 | Unknown:104 |
| Reachable outside descendants | 219 | 0 | Hatchery:219 | S24 Strond:219 | Unknown:219 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)