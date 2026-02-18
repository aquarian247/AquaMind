# Semantic Migration Validation Report

- Component key: `2FE768F3-CB5B-4731-BD3E-3BC69F073898`
- Batch: `Bakkafrost Okt 2023` (id=519)
- Populations: 174
- Window: 2023-10-27 14:50:02 → 2025-04-11 16:05:21

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 2027 | 2027 | 0.00 |
| Feeding kg | 368454.83 | 368454.83 | 0.00 |
| Mortality events | 5534 | 5045 | 489.00 |
| Mortality count | 401240 | 401240 | 0.00 |
| Mortality biomass kg | 0.00 | 3076.05 | -3076.05 |
| Culling events | 13 | 13 | 0.00 |
| Culling count | 391734 | 391734 | 0.00 |
| Culling biomass kg | 5724651.00 | 5724651.00 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 591 | 591 | 0.00 |
| Growth samples | 15 | 15 | 0.00 |
| Health journal entries | 2 | 2 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 792974
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 3/4 bridge-aware (75.0%), 1/4 entry-window (25.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 23 total, 22 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 72.
- Fishgroup classification: 53 temporary bridge fishgroups, 35 real stage-entry fishgroups, 53 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1399996 | 0 | 1399996 | 1399996 | 1.0 | 1.0 | 2023-10-27 | 2023-10-29 | 4 | 4 | 0 | 4 | 4 |
| Fry | 1395260 | 0 | 1702573 | 1832758 | 1.31 | 1.08 | 2024-01-16 | 2024-01-18 | 24 | 24 | 0 | 29 | 29 |
| Parr | 501335 | 0 | 1618385 | 8845687 | 17.64 | 5.47 | 2024-04-16 | 2024-04-18 | 4 | 4 | 0 | 93 | 115 |
| Smolt | 135385 | 0 | 987342 | 2471305 | 18.25 | 2.5 | 2024-08-29 | 2024-08-31 | 1 | 1 | 2 | 17 | 18 |
| Post-Smolt | 117951 | 0 | 590638 | 590638 | 5.01 | 1.0 | 2024-12-27 | 2024-12-29 | 2 | 2 | 0 | 8 | 8 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1399996 | 1399996 | 0 | 24 | 24 | yes | Bridge-aware (linked sources: 4); lineage graph fallback used | OK |
| Fry -> Parr | 1395260 | 501335 | -893925 | 4 | 4 | yes | Entry window (incomplete linkage) | WARN: stage drop exceeds total known removals by 100951 |
| Parr -> Smolt | 90309 | 89288 | -1021 | 1 | 1 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |
| Smolt -> Post-Smolt | 124577 | 117951 | -6626 | 2 | 2 | yes | Bridge-aware (linked sources: 1); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0040`, `234.0041`, `234.0042`, `234.0043`, `234.0044`, `234.0045`, `234.0046`, `234.0047`, `234.0048`, `234.0049`
- Real stage-entry fishgroup examples: `234.0001`, `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`
- Bridge fishgroups excluded from stage-entry windows: `234.0104`, `234.0107`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 174 | 174 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Fry | 131250 |
| Parr | 41241 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 64

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 21 | Hatchery:21 | S16 Glyvradalur:21 |
| SourcePopBefore -> SourcePopAfter | 41 | Hatchery:41 | S16 Glyvradalur:41 |
| DestPopBefore -> DestPopAfter | 6 | Hatchery:6 | S16 Glyvradalur:6 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 64 | 0 | Hatchery:64 | S16 Glyvradalur:64 | Unknown:64 |
| Reachable outside descendants | 101 | 0 | Hatchery:101 | S16 Glyvradalur:101 | Unknown:101 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)