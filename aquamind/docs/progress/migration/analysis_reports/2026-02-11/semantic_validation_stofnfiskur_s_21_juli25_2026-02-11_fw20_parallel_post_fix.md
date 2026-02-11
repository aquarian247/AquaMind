# Semantic Migration Validation Report

- Component key: `0D5E2166-55AD-4469-B1E4-30A70B22FB72`
- Batch: `StofnFiskur S-21 juli25` (id=435)
- Populations: 40
- Window: 2025-07-23 13:48:53 → 2026-02-11 11:32:05.749566

| Metric | FishTalk | AquaMind | Diff (FT - AM) |
| --- | ---: | ---: | ---: |
| Feeding events | 36 | 36 | 0.00 |
| Feeding kg | 55.98 | 55.98 | 0.00 |
| Mortality events | 200 | 193 | 7.00 |
| Mortality count | 118521 | 118521 | 0.00 |
| Mortality biomass kg | 0.00 | 2.78 | -2.78 |
| Culling events | 8 | 7 | 1.00 |
| Culling count | 11250 | 11250 | 0.00 |
| Culling biomass kg | 15.00 | 15.21 | -0.21 |
| Escape events | 0 | 0 | 0.00 |
| Escape count | 0 | 0 | 0.00 |
| Escape biomass kg | 0.00 | 0.00 | 0.00 |
| Treatments | 0 | 0 | 0.00 |
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
- Known removal count (mortality + culling + escapes + harvest): 129771
- Stage-entry window used for transition sanity: 2 day(s)
- Transition basis usage: 1/2 bridge-aware (50.0%), 1/2 entry-window (50.0%).
- Lineage fallback max depth: 14 hop(s).
- Bridge-aware transitions using lineage-graph fallback: 0
- Assignment zero-count rows (population_count <= 0): 26 total, 5 bridge-classified, 0 same-stage superseded-zero, 14 short-lived orphan-zero, 7 no-count-evidence-zero, 0 known-loss-depleted-zero, 0 non-bridge.
- Transfer actions with transferred_count <= 0: 0 of 7.
- Fishgroup classification: 6 temporary bridge fishgroups, 13 real stage-entry fishgroups, 6 temporary bridge populations.

| Stage | Entry population | Active population | Peak concurrent population | Full summed population | Full/entry ratio | Full/peak ratio | Entry date | Entry window end | Entry containers | Real entry fishgroups | Bridge fishgroups excluded | Non-zero assignments | Total assignments |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Egg&Alevin | 1395853 | 0 | 1395853 | 1395853 | 1.0 | 1.0 | 2025-07-23 | 2025-07-25 | 7 | 7 | 0 | 7 | 7 |
| Fry | 1371733 | 0 | 1567308 | 1567308 | 1.14 | 1.0 | 2025-10-22 | 2025-10-24 | 6 | 6 | 1 | 7 | 12 |
| Parr | 0 | 0 | 0 | 0 | - | - | - | - | 0 | 0 | 0 | 0 | 21 |

- Transition deltas below use bridge-aware linked source populations when available (counts prefer SubTransfer-conserved values, fallback to assignment counts); otherwise they fall back to stage entry-window populations.

| Transition | From population | To population | Delta | Entry populations | Linked destinations | Bridge-aware eligible | Basis | Sanity check |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Egg&Alevin -> Fry | 1501504 | 1501504 | 0 | 6 | 6 | yes | Bridge-aware (linked sources: 7) | OK |
| Fry -> Parr | 1371733 | 0 | -1371733 | 0 | 0 | no | Entry window (no entry populations) | WARN: stage drop exceeds total known removals by 1241962 |

### Fishgroup Classification Samples

- Temporary bridge fishgroup examples: `253.0008`, `253.0009`, `253.0010`, `253.0011`, `253.0012`, `253.0013`
- Real stage-entry fishgroup examples: `253.0002`, `253.0003`, `253.0004`, `253.0005`, `253.0006`, `253.0007`, `253.0014`, `253.0015`, `253.0016`, `253.0017`
- Bridge fishgroups excluded from stage-entry windows: `253.0008`

### Fishgroup Format Audit

- Tuple format check: `Fishgroup == InputYear + InputNumber + '.' + RunningNumber(4-digit)`
| Scope | Rows checked | Matched | Matched % | Outliers | Allowlisted outliers | Non-allowlisted outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Component | 40 | 40 | 100.0 | 0 | 0 | 0 |
| Global extract | 184234 | 184229 | 100.0 | 5 | 5 | 0 |
- Outlier allowlist patterns: `23|99|23999.000`

### Outside-Component Destination Evidence

- This evidence is derived from SubTransfers graph links and grouped-organisation context; it indicates destinations outside the selected stitched population set.
- Marine linkage evidence: NO
- Direct external destination populations (any role): 1

| SubTransfer role evidence | External edge count | Destination prod stages | Destination sites |
| --- | ---: | --- | --- |
| SourcePopBefore -> DestPopAfter | 0 | - | - |
| SourcePopBefore -> SourcePopAfter | 1 | Hatchery:1 | S21 Viðareiði:1 |
| DestPopBefore -> DestPopAfter | 0 | - | - |

| Destination set | Populations | Marine populations | By prod stage | By site | By site group |
| --- | ---: | ---: | --- | --- | --- |
| Direct external populations | 1 | 0 | Hatchery:1 | S21 Viðareiði:1 | Unknown:1 |
| Reachable outside descendants | 5 | 0 | Hatchery:5 | S21 Viðareiði:5 | Unknown:5 |

### Regression Gates

| Gate | Result | Details |
| --- | --- | --- |
| `no_positive_transition_delta_without_mixed_batch` | PASS | Positive stage transition deltas without mixed-batch composition rows: 0 (excluded incomplete-linkage fallback rows: 0) |
| `no_zero_count_transfer_actions` | PASS | Transfer actions with transferred_count <= 0: 0 |
| `non_bridge_zero_assignments_within_threshold` | PASS | Assignments with population_count <= 0 after excluding temporary bridge, same-stage superseded-zero, short-lived orphan-zero, no-count-evidence-zero, and known-loss-depleted-zero rows: 0 (threshold: 2) |
- Overall gate result: PASS (enforced)