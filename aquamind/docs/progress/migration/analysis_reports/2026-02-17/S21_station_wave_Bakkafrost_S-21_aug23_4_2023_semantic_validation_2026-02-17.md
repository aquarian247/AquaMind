# Semantic Migration Validation Report

- Component key: `BCD6C51F-044C-436C-A07B-302E4C129156`
- Batch: `Bakkafrost S-21 aug23` (id=551)
- Populations: 246
- Window: 2023-08-09 13:20:27 → 2025-02-12 11:16:18

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3558 | 3558 | 0.00 |
| Feeding kg | 274250.88 | 274250.88 | 0.00 |
| Mortality events | 4032 | 3400 | 632.00 |
| Mortality count | 374208 | 374208 | 0.00 |
| Mortality biomass kg | 0.00 | 2321.15 | -2321.15 |
| Culling events | 32 | 32 | 0.00 |
| Culling count | 135709 | 135709 | 0.00 |
| Culling biomass kg | 3945341.90 | 3945341.90 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 22 | 22 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 509917
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 3
- Assignment zero-count rows (population_count <= 0): 56 total, 53 bridge-classified, 3 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 119.
- Fishgroup classification: 117 temporary bridge fishgroups, 23 real stage-entry fishgroups, 117 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1501495 | 0 | 1501495 | 1501495 | 1.0 | 1.0 | 2023-08-09 | 2023-08-11 | 7 | 7 | 0 | 7 | 7 |
| Fry | 871721 | 0 | 871721 | 871721 | 1.0 | 1.0 | 2023-11-03 | 2023-11-05 | 6 | 6 | 0 | 6 | 6 |
| Parr | 540874 | 0 | 1864896 | 6445351 | 11.92 | 3.46 | 2024-02-01 | 2024-02-03 | 3 | 3 | 0 | 112 | 164 |
| Smolt | 175907 | 0 | 786488 | 1204403 | 6.85 | 1.53 | 2024-06-11 | 2024-06-13 | 2 | 2 | 0 | 17 | 20 |
| Post-Smolt | 293430 | 0 | 907340 | 2063879 | 7.03 | 2.27 | 2024-09-02 | 2024-09-04 | 5 | 5 | 8 | 48 | 49 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1282226 | 857923 | -424303 | 6 | 6 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Fry -> Parr | 310913 | 310913 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |
| Parr -> Smolt | 100317 | 100317 | 0 | 2 | 2 | yes | Bridge-aware (direct edge linkage; linked sources: 2) | OK |
| Smolt -> Post-Smolt | 203338 | 183799 | -19539 | 5 | 5 | yes | Bridge-aware (linked sources: 3); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `234.0014`, `234.0015`, `234.0016`, `234.0017`, `234.0018`, `234.0019`, `234.0023`, `234.0024`, `234.0025`, `234.0027`
- Real stage-entry fishgroup examples: `234.0002`, `234.0003`, `234.0004`, `234.0005`, `234.0006`, `234.0007`, `234.0008`, `234.0009`, `234.0010`, `234.0011`
- Bridge fishgroups excluded from stage-entry windows: `234.0199`, `234.0200`, `234.0202`, `234.0203`, `234.0208`, `234.0209`, `234.0210`, `234.0211`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 246 | 246 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Egg&Alevin | 1270857 |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 59

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 11 | Hatchery:11 | S21 Viðareiði:11 |
| SourcePopBefore -> SourcePopAfter | 48 | Hatchery:48 | S21 Viðareiði:48 |
| DestPopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 59 | 0 | Hatchery:59 | S21 Viðareiði:59 | Unknown:59 |
| Reachable outside descendants | 118 | 0 | Hatchery:118 | S21 Viðareiði:118 | Unknown:118 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)