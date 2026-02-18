# Semantic Migration Validation Report

- Component key: `B884F78F-1E92-49C0-AE28-39DFC2E18C01`
- Batch: `Stofnfiskur S-21 nov23` (id=466)
- Populations: 288
- Window: 2023-11-08 07:17:34 → 2025-05-27 15:16:58

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 3737 | 3737 | 0.00 |
| Feeding kg | 354572.55 | 354572.55 | -0.00 |
| Mortality events | 3992 | 3276 | 716.00 |
| Mortality count | 451689 | 451689 | 0.00 |
| Mortality biomass kg | 0.00 | 3136.80 | -3136.80 |
| Culling events | 39 | 39 | 0.00 |
| Culling count | 64436 | 64436 | 0.00 |
| Culling biomass kg | 2448681.05 | 2448681.05 | 0.00 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 25 | 25 | 0.00 |
| Growth samples | 0 | 0 | 0.00 |
| Health journal entries | 3 | 3 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 516125
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 4/4 bridge-aware (100.0%), 0/4 entry-window (0.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 2
- Assignment zero-count rows (population_count <= 0): 73 total, 72 bridge-classified, 1 same-stage superseded-zero, 0 short-lived orphan-zero, 0 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 134.
- Fishgroup classification: 165 temporary bridge fishgroups, 24 real stage-entry fishgroups, 165 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1510219 | 0 | 1510219 | 1510219 | 1.0 | 1.0 | 2023-11-08 | 2023-11-10 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1425831 | 0 | 1631013 | 1631013 | 1.14 | 1.0 | 2024-02-14 | 2024-02-16 | 6 | 6 | 1 | 7 | 12 |
| Parr | 1117340 | 0 | 1571394 | 8605894 | 7.7 | 5.48 | 2024-05-16 | 2024-05-18 | 5 | 5 | 4 | 139 | 186 |
| Smolt | 258077 | 0 | 1300467 | 2652879 | 10.28 | 2.04 | 2024-08-21 | 2024-08-23 | 3 | 3 | 2 | 28 | 35 |
| Post-Smolt | 156715 | 0 | 1298899 | 1752748 | 11.18 | 1.35 | 2024-12-16 | 2024-12-18 | 3 | 3 | 4 | 34 | 48 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1510219 | 1510219 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1510219 | 1510219 | 0 | 5 | 5 | yes | Bridge-aware (linked sources: 6); lineage graph fallback used | OK |
| Parr -> Smolt | 369192 | 369192 | 0 | 3 | 3 | yes | Bridge-aware (linked sources: 8) | OK |
| Smolt -> Post-Smolt | 322655 | 199240 | -123415 | 3 | 3 | yes | Bridge-aware (linked sources: 2); lineage graph fallback used | OK |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `235.0009`, `235.0010`, `235.0011`, `235.0012`, `235.0013`, `235.0014`, `235.0020`, `235.0021`, `235.0022`, `235.0023`
- Real stage-entry fishgroup examples: `235.0002`, `235.0003`, `235.0004`, `235.0005`, `235.0006`, `235.0007`, `235.0008`, `235.0015`, `235.0016`, `235.0017`
- Bridge fishgroups excluded from stage-entry windows: `235.0011`, `235.0023`, `235.0025`, `235.0031`, `235.0034`, `235.0100`, `235.0106`, `235.0231`, `235.0239`, `235.0240`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 288 | 288 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Estimated Outflow To Populations Outside Selected Component

- Conservative estimate from SubTransfers propagation (component-population sources only). This means outside the selected stitched population set, not necessarily another station:
| Source stage | Estimated transferred count to populations outside selected component |
| --- | ---: |
| Parr | 0 |

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 52

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 2 | Hatchery:2 | S21 Viðareiði:2 |
| SourcePopBefore -> SourcePopAfter | 50 | Hatchery:50 | S21 Viðareiði:50 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 52 | 0 | Hatchery:52 | S21 Viðareiði:52 | Unknown:52 |
| Reachable outside descendants | 129 | 0 | Hatchery:129 | S21 Viðareiði:129 | Unknown:129 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)