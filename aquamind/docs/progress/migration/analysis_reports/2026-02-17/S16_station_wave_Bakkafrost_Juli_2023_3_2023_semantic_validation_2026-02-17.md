# Semantic Migration Validation Report

- Component key: `137882DD-6162-4987-9D06-185FED4A5510`
- Batch: `Bakkafrost Juli 2023` (id=518)
- Populations: 142
- Window: 2023-07-27 15:01:53 → 2024-12-19 17:12:56

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 1871 | 1871 | 0.00 |
| Feeding kg | 336569.75 | 336569.75 | -0.00 |
| Mortality events | 4801 | 4373 | 428.00 |
| Mortality count | 190653 | 190653 | 0.00 |
| Mortality biomass kg | 0.00 | 2637.91 | -2637.91 |
| Culling events | 12 | 12 | 0.00 |
| Culling count | 513005 | 513005 | 0.00 |
| Culling biomass kg | 7142028.00 | 7142028.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 442 | 442 | 0.00 |
| Growth samples | 13 | 13 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 703658
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 19 total, 18 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 57.
- Fishgroup classification: 50 temporary bridge fishgroups, 41 real stage-entry fishgroups, 50 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1407994 | 0 | 1407994 | 1407994 | 1.0 | 1.0 | 2023-07-27 | 2023-07-29 | 4 | 4 | 0 | 4 | 4 |
| Fry | 1407994 | 0 | 1407994 | 1407994 | 1.0 | 1.0 | 2023-10-23 | 2023-10-25 | 24 | 24 | 0 | 24 | 24 |
| Parr | 1282729 | 0 | 1739133 | 6918747 | 5.39 | 3.98 | 2024-01-10 | 2024-01-12 | 7 | 7 | 0 | 71 | 85 |
| Smolt | 251672 | 0 | 826122 | 1476913 | 5.87 | 1.79 | 2024-06-22 | 2024-06-24 | 2 | 2 | 2 | 11 | 15 |
| Post-Smolt | 345950 | 0 | 667335 | 892940 | 2.58 | 1.34 | 2024-08-20 | 2024-08-22 | 4 | 4 | 0 | 13 | 14 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1407994 | 1407994 | 0 | 24 | 24 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Fry -> Parr | 1407994 | 1282729 | -125265 | 7 | 7 | yes | Entry window (incomplete linkage) | OK |
| Parr -> Smolt | 545292 | 234694 | -310598 | 2 | 2 | yes | Bridge-aware (linked sources: 6) | OK |
| Smolt -> Post-Smolt | 345950 | 345950 | 0 | 4 | 4 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `233.0037`, `233.0038`, `233.0039`, `233.0040`, `233.0041`, `233.0045`, `233.0047`, `233.0048`, `233.0050`, `233.0051`
- Real stage-entry fishgroup examples: `233.0002`, `233.0003`, `233.0004`, `233.0005`, `233.0006`, `233.0007`, `233.0008`, `233.0009`, `233.0010`, `233.0011`
- Bridge fishgroups excluded from stage-entry windows: `233.0080`, `233.0085`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 142 | 142 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 132000 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 53

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 17 | Hatchery:17 | S16 Glyvradalur:17 |
| SourcePopBefore -> SourcePopAfter | 36 | Hatchery:36 | S16 Glyvradalur:36 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 53 | 0 | Hatchery:53 | S16 Glyvradalur:53 | Unknown:53 |
| Reachable outside descendants | 84 | 0 | Hatchery:84 | S16 Glyvradalur:84 | Unknown:84 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)